#!/usr/bin/env python3
"""
LibreNMS MCP Server

Provides a Model Context Protocol (MCP) server exposing tools that interact with the LibreNMS API.
"""

import logging
import os
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version

from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp import settings
from fastmcp.server.auth.providers.jwt import StaticTokenVerifier
from fastmcp.server.middleware.rate_limiting import SlidingWindowRateLimitingMiddleware
from fastmcp.server.transforms.search import BM25SearchTransform
from fastmcp.server.transforms.search import RegexSearchTransform
from starlette.requests import Request
from starlette.responses import PlainTextResponse

from librenms_mcp.librenms_client import get_librenms_config_from_env
from librenms_mcp.librenms_client import get_transport_config_from_env
from librenms_mcp.sentry_init import init_sentry
from librenms_mcp.tools import register_tools
from librenms_mcp.utils import HEALTH_PATH
from librenms_mcp.utils import HTTP_TRANSPORTS
from librenms_mcp.utils import VALID_TRANSPORTS
from librenms_mcp.utils import transport_help

# Load environment variables
load_dotenv()

# Configure FastMCP defaults
settings.show_server_banner = False
settings.check_for_updates = "off"

# Configure logging. An unknown or lowercase LOG_LEVEL must not take the server
# down, so resolve it leniently and fall back to INFO.
_requested_log_level = os.getenv("LOG_LEVEL", "INFO").strip().upper()
_resolved_log_level = logging.getLevelNamesMapping().get(_requested_log_level)
logging.basicConfig(
    level=_resolved_log_level if _resolved_log_level is not None else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize optional Sentry monitoring. This runs after logging is configured
# so that its "enabled" message is not dropped.
init_sentry()

if _resolved_log_level is None:
    logger.warning(
        "Unknown LOG_LEVEL %r - falling back to INFO. Valid values: %s",
        _requested_log_level,
        ", ".join(logging.getLevelNamesMapping()),
    )

# Get package version
try:
    __version__ = version("librenms-mcp")
except PackageNotFoundError:
    __version__ = "0.0.1"

try:
    LNMS_CONFIG = get_librenms_config_from_env()
    TRANSPORT_CONFIG = get_transport_config_from_env()
except Exception as e:
    logger.error(f"Invalid configuration: {e}")
    raise

# Create auth provider if bearer token is configured
auth_provider = None
if getattr(TRANSPORT_CONFIG, "http_bearer_token", None):
    bearer_token = TRANSPORT_CONFIG.http_bearer_token
    if bearer_token:  # Type narrowing: ensures bearer_token is str, not None
        auth_provider = StaticTokenVerifier(
            tokens={
                bearer_token: {
                    "client_id": "authenticated-client",
                    "scopes": ["read", "write"],
                }
            }
        )

# Initialize FastMCP server
mcp = FastMCP(
    name="LibreNMS MCP Server",
    version=__version__,
    instructions=(
        "This MCP server exposes tools for interacting with the LibreNMS API, supporting both read and write operations if not in read-only mode."
    ),
    auth=auth_provider,
)


@mcp.custom_route(HEALTH_PATH, methods=["GET"], include_in_schema=False)
async def health(_request: Request) -> PlainTextResponse:
    """Liveness probe for the HTTP transports.

    Answering proves the server handles requests, which a TCP connect does not:
    the kernel completes the handshake even while the event loop is stuck. It
    deliberately does not call LibreNMS, so an outage there does not get a
    healthy MCP server restarted. FastMCP serves custom routes outside the
    bearer-token auth, so the container healthcheck needs no token.
    """
    return PlainTextResponse("ok")


# Register all tools
register_tools(mcp, LNMS_CONFIG)


def configure_component_visibility() -> None:
    """Apply server-level visibility transforms for read-only and disabled tags."""

    disabled_tags = getattr(LNMS_CONFIG, "disabled_tags", set())
    read_only_mode = getattr(LNMS_CONFIG, "read_only_mode", False)

    if read_only_mode:
        logger.info("Read-only mode is enabled - restricting to read-only components")
        mcp.enable(tags={"read-only"}, only=True)

    if disabled_tags:
        logger.info(
            "Disabled tags configured: %s - disabling matching components",
            disabled_tags,
        )
        mcp.disable(tags=disabled_tags)


def configure_tool_search() -> None:
    """Apply the optional FastMCP tool-search transform."""

    if not getattr(LNMS_CONFIG, "tool_search_enabled", False):
        return

    strategy = getattr(LNMS_CONFIG, "tool_search_strategy", "bm25")
    max_results = getattr(LNMS_CONFIG, "tool_search_max_results", 5)

    if strategy == "regex":
        mcp.add_transform(RegexSearchTransform(max_results=max_results))
    else:
        mcp.add_transform(BM25SearchTransform(max_results=max_results))

    logger.info(
        "Tool search is enabled - strategy=%s, max_results=%s",
        strategy,
        max_results,
    )


configure_component_visibility()
configure_tool_search()

# Optional rate limiting
if getattr(LNMS_CONFIG, "rate_limit_enabled", False):
    logger.info("Rate limiting is enabled - applying middleware")
    mcp.add_middleware(
        SlidingWindowRateLimitingMiddleware(
            max_requests=LNMS_CONFIG.rate_limit_max_requests,
            window_minutes=LNMS_CONFIG.rate_limit_window_minutes,
        )
    )


def main():
    # Basic validation
    if not all([LNMS_CONFIG.librenms_url, LNMS_CONFIG.token]):
        logger.error(
            "Missing required LibreNMS configuration (LIBRENMS_URL or LIBRENMS_TOKEN). Check your .env file."
        )
        raise SystemExit(1)

    if TRANSPORT_CONFIG.transport_type not in VALID_TRANSPORTS:
        logger.error(
            "Unknown MCP_TRANSPORT %r. Valid values: %s",
            TRANSPORT_CONFIG.transport_type,
            transport_help(),
        )
        raise SystemExit(1)

    if (
        TRANSPORT_CONFIG.transport_type in HTTP_TRANSPORTS
        and not TRANSPORT_CONFIG.http_bearer_token
    ):
        logger.warning(
            "WARNING: MCP_HTTP_BEARER_TOKEN is not set. The MCP server will run WITHOUT authentication. "
            "Ensure the server is not exposed to untrusted networks (e.g. bind to 127.0.0.1 instead of 0.0.0.0)."
        )

    logger.info(f"Starting LibreNMS MCP Server at {LNMS_CONFIG.librenms_url} ...")

    # Choose transport based on configuration
    if TRANSPORT_CONFIG.transport_type == "sse":
        logger.info(
            f"Using HTTP SSE transport on {TRANSPORT_CONFIG.http_host}:{TRANSPORT_CONFIG.http_port}"
        )
        if TRANSPORT_CONFIG.http_bearer_token:
            logger.info("Bearer token authentication enabled for SSE transport")

        # Run with HTTP SSE transport
        mcp.run(
            transport="sse",
            host=TRANSPORT_CONFIG.http_host,
            port=TRANSPORT_CONFIG.http_port,
        )
    elif TRANSPORT_CONFIG.transport_type == "http":
        logger.info(
            f"Using HTTP Streamable transport on {TRANSPORT_CONFIG.http_host}:{TRANSPORT_CONFIG.http_port}"
        )
        if TRANSPORT_CONFIG.http_bearer_token:
            logger.info("Bearer token authentication enabled for Streamable transport")

        # Run with HTTP Streamable transport
        mcp.run(
            transport="http",
            host=TRANSPORT_CONFIG.http_host,
            port=TRANSPORT_CONFIG.http_port,
        )
    else:
        logger.info("Using STDIO transport")
        mcp.run()


if __name__ == "__main__":
    main()
