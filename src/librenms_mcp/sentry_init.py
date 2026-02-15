"""
Optional Sentry integration for error tracking and monitoring.
"""

import logging
import os

from librenms_mcp.utils import parse_bool

logger = logging.getLogger(__name__)


def init_sentry() -> bool:
    """
    Initialize Sentry SDK if available and configured.

    Returns:
        bool: True if Sentry was successfully initialized, False otherwise.

    Note:
        This function will silently return False if sentry-sdk is not installed
        or if SENTRY_DSN is not configured.
    """
    sentry_dsn = os.getenv("SENTRY_DSN")

    if not sentry_dsn:
        # Sentry is not configured
        return False

    try:
        import sentry_sdk
        from sentry_sdk.integrations.mcp import MCPIntegration
    except ImportError:
        logger.warning(
            "Sentry SDK not installed but SENTRY_DSN is configured. "
            "To enable Sentry monitoring, install it with: uv sync --extra sentry "
        )
        return False

    try:
        # Parse configuration from environment variables
        traces_sample_rate = float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "1.0"))
        send_default_pii = parse_bool(
            os.getenv("SENTRY_SEND_DEFAULT_PII"), default=True
        )
        environment: str | None = os.getenv("SENTRY_ENVIRONMENT")
        release: str | None = os.getenv("SENTRY_RELEASE")
        profile_session_sample_rate = float(
            os.getenv("SENTRY_PROFILE_SESSION_SAMPLE_RATE", "1.0")
        )
        profile_lifecycle_str = os.getenv("SENTRY_PROFILE_LIFECYCLE", "trace")
        # Ensure profile_lifecycle is a valid literal value
        profile_lifecycle: str = (
            "manual" if profile_lifecycle_str == "manual" else "trace"
        )
        enable_logs = parse_bool(os.getenv("SENTRY_ENABLE_LOGS"), default=True)

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
            send_default_pii=send_default_pii,
            environment=environment,
            release=release,
            profile_session_sample_rate=profile_session_sample_rate,
            profile_lifecycle=profile_lifecycle,
            enable_logs=enable_logs,
            integrations=[
                MCPIntegration(),
            ],
        )

        logger.info(
            f"Sentry monitoring enabled"
            f"(traces_sample_rate={traces_sample_rate}, "
            f"environment={environment or 'default'})"
        )
        return True

    except Exception as e:
        logger.error(f"Failed to initialize Sentry: {e}", exc_info=True)
        return False
