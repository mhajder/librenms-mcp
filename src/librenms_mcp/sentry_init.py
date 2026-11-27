"""
Optional Sentry integration for error tracking and monitoring.
"""

import logging
import os
from typing import TYPE_CHECKING

from librenms_mcp.utils import env_bool
from librenms_mcp.utils import env_float
from librenms_mcp.utils import env_str

if TYPE_CHECKING:
    from sentry_sdk.types import DataCollectionUserOptions

logger = logging.getLogger(__name__)

# Header, cookie and query names that identify the caller, from the
# sentry-sdk 3.x migration guide's stand-in for send_default_pii=False.
_IDENTIFYING_TERMS = ["forwarded", "-ip", "remote-", "via", "-user"]


def _data_collection(send_default_pii: bool) -> "DataCollectionUserOptions":
    """
    Build sentry-sdk 3.x ``data_collection`` from the SENTRY_SEND_DEFAULT_PII flag.

    sentry-sdk 3.x dropped ``send_default_pii`` and collects user identity,
    MCP tool arguments and results, HTTP bodies and stack frame variables by
    default. Opting out has to be spelled out per category; opting in keeps
    the SDK defaults except for stack frame variables.
    """
    if send_default_pii:
        # The default (True) sends frame locals unfiltered, so a password or
        # token held in a local goes out as-is. Denylist mode replaces locals
        # with secret-looking names (password, token, key, ...) by
        # [Filtered], as 2.x did.
        return {"stack_frame_variables": {"mode": "denylist", "terms": []}}
    return {
        "user_info": False,
        # Over the HTTP transports, request bodies are MCP calls carrying tool
        # arguments: device hostnames and IP addresses, and on device adds the
        # SNMP community or SNMPv3 username and passphrases.
        "http_bodies": [],
        "graphql": {"document": False, "variables": False},
        "gen_ai": {"inputs": False, "outputs": False},
        "mcp": {"inputs": False, "outputs": False},
        "database_query_data": False,
        "queues": False,
        "http_headers": {
            "request": {"mode": "denylist", "terms": _IDENTIFYING_TERMS},
        },
        # 2.x sent no cookies at all without send_default_pii; a denylist
        # would still ship every cookie whose name looks harmless.
        "cookies": {"mode": "off"},
        "url_query_params": {"mode": "denylist", "terms": _IDENTIFYING_TERMS},
        # A tool's arguments are locals of its frame, so an exception would
        # otherwise ship device hostnames and IP addresses, and device_add's
        # payload with its SNMP credentials.
        "stack_frame_variables": False,
    }


def _sample_rate(name: str, default: float) -> float:
    """
    Read a Sentry sample rate, which must lie between 0.0 and 1.0.

    Raises:
        ValueError: If the variable is not a number in that range.
    """
    rate = env_float(name, default)
    if not 0.0 <= rate <= 1.0:
        raise ValueError(f"{name} must be between 0.0 and 1.0, got {rate}")
    return rate


def init_sentry() -> bool:
    """
    Initialize Sentry SDK if available and configured.

    Returns:
        bool: True if Sentry was successfully initialized, False otherwise.

    Note:
        This function will silently return False if sentry-sdk is not installed
        or if SENTRY_DSN is not configured.
    """
    # Whitespace-only counts as unset, like the other blank settings.
    sentry_dsn = env_str("SENTRY_DSN")

    if not sentry_dsn:
        # Sentry is not configured
        return False

    try:
        import sentry_sdk
        from sentry_sdk.integrations.logging import LoggingIntegration
        from sentry_sdk.integrations.mcp import MCPIntegration
    except ImportError:
        logger.warning(
            "Sentry SDK not installed but SENTRY_DSN is configured. "
            "To enable Sentry monitoring, install it with: uv sync --extra sentry "
        )
        return False

    try:
        # Parse configuration from environment variables
        traces_sample_rate = _sample_rate("SENTRY_TRACES_SAMPLE_RATE", 1.0)
        # Off by default: with PII on, MCPIntegration attaches tool inputs and
        # outputs to events, and those include device configs and SNMP secrets.
        send_default_pii = env_bool("SENTRY_SEND_DEFAULT_PII", default=False)
        environment = env_str("SENTRY_ENVIRONMENT")
        release = env_str("SENTRY_RELEASE")
        # Off unless asked for: profiling costs CPU and Sentry quota.
        profile_session_sample_rate = _sample_rate(
            "SENTRY_PROFILE_SESSION_SAMPLE_RATE", 0.0
        )
        profile_lifecycle_str = os.getenv("SENTRY_PROFILE_LIFECYCLE", "trace")
        # Ensure profile_lifecycle is a valid literal value
        profile_lifecycle: str = (
            "manual" if profile_lifecycle_str == "manual" else "trace"
        )
        # Log lines carry LibreNMS request URLs with device hostnames and IP
        # addresses, so Sentry Logs follow the PII choice unless set explicitly.
        enable_logs = env_bool("SENTRY_ENABLE_LOGS", default=send_default_pii)

        # Get package version for default release
        if not release:
            from importlib.metadata import PackageNotFoundError
            from importlib.metadata import version

            try:
                release = version("librenms-mcp")
            except PackageNotFoundError:
                release = None

        # Initialize Sentry
        sentry_sdk.init(
            dsn=sentry_dsn,
            traces_sample_rate=traces_sample_rate,
            data_collection=_data_collection(send_default_pii),
            environment=environment,
            release=release,
            profile_session_sample_rate=profile_session_sample_rate,
            profile_lifecycle=profile_lifecycle,
            integrations=[
                MCPIntegration(),
                # sentry-sdk 3.x no longer enables this by default, and its
                # event_level now defaults to off. Keep the 2.x behaviour:
                # logged errors become events, and SENTRY_ENABLE_LOGS decides
                # whether records are also sent as Sentry logs.
                LoggingIntegration(
                    level=logging.INFO if enable_logs else None,
                    event_level=logging.ERROR,
                ),
            ],
        )

        logger.info(
            f"Sentry monitoring enabled "
            f"(traces_sample_rate={traces_sample_rate}, "
            f"environment={environment or 'default'})"
        )
        return True

    except Exception as e:
        logger.error(f"Failed to initialize Sentry: {e}", exc_info=True)
        return False
