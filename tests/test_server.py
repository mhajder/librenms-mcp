"""In-process tests for server.py's module-level setup and main().

server.py configures everything at import time, so each test imports a fresh
copy under a controlled environment. The subprocess tests in
test_client_errors.py and test_healthcheck.py run the same module end to end,
but coverage does not see them.
"""

import importlib
import importlib.metadata
import logging
import sys
from unittest.mock import MagicMock

import dotenv
import pytest
from fastmcp.server.auth.providers.jwt import StaticTokenVerifier
from fastmcp.server.middleware.rate_limiting import SlidingWindowRateLimitingMiddleware
from fastmcp.server.transforms.search import BM25SearchTransform
from fastmcp.server.transforms.search import RegexSearchTransform

MODULE = "librenms_mcp.server"

SERVER_ENV_VARS = (
    "LIBRENMS_URL",
    "LIBRENMS_TOKEN",
    "LIBRENMS_VERIFY_SSL",
    "LIBRENMS_TIMEOUT",
    "READ_ONLY_MODE",
    "DISABLED_TAGS",
    "RATE_LIMIT_ENABLED",
    "RATE_LIMIT_MAX_REQUESTS",
    "RATE_LIMIT_WINDOW_MINUTES",
    "TOOL_SEARCH_ENABLED",
    "TOOL_SEARCH_STRATEGY",
    "TOOL_SEARCH_MAX_RESULTS",
    "LOG_LEVEL",
    "MCP_TRANSPORT",
    "MCP_HTTP_HOST",
    "MCP_HTTP_PORT",
    "MCP_HTTP_BEARER_TOKEN",
    "SENTRY_DSN",
)


@pytest.fixture
def load_server(monkeypatch):
    """Import a fresh server module with only the given environment."""
    for name in SERVER_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    # The repository's real .env must not leak into the tests.
    monkeypatch.setattr(dotenv, "load_dotenv", lambda *_args, **_kwargs: False)
    original = sys.modules.get(MODULE)

    def factory(**env: str):
        env.setdefault("LIBRENMS_URL", "https://nms.invalid")
        env.setdefault("LIBRENMS_TOKEN", "t")
        for name, value in env.items():
            monkeypatch.setenv(name, value)
        sys.modules.pop(MODULE, None)
        module = importlib.import_module(MODULE)
        monkeypatch.setattr(module.mcp, "run", MagicMock())
        return module

    yield factory
    if original is None:
        sys.modules.pop(MODULE, None)
    else:
        sys.modules[MODULE] = original


async def tool_names(module) -> set[str]:
    return {tool.name for tool in await module.mcp.list_tools()}


@pytest.mark.asyncio
async def test_health_route_answers_ok(load_server):
    server = load_server()

    response = await server.health(MagicMock())

    assert response.status_code == 200
    assert response.body == b"ok"


@pytest.mark.asyncio
async def test_all_tools_are_exposed_by_default(load_server):
    server = load_server()
    names = await tool_names(server)

    assert {"device_get", "device_delete", "alerts_get", "bills_list"} <= names
    assert "search_tools" not in names
    assert server.LNMS_CONFIG.librenms_url == "https://nms.invalid"
    assert server.mcp.auth is None


@pytest.mark.asyncio
async def test_read_only_mode_hides_write_tools(load_server, caplog):
    caplog.set_level(logging.INFO)
    server = load_server(READ_ONLY_MODE="true")
    tools = await server.mcp.list_tools()

    names = {tool.name for tool in tools}
    assert {"device_get", "alerts_get", "port_graph"} <= names
    assert names.isdisjoint({"device_delete", "alert_acknowledge", "device_add"})
    # Every tool left is one that cannot change LibreNMS.
    assert all("read-only" in tool.tags for tool in tools)
    assert all(tool.annotations.read_only_hint for tool in tools)
    assert "Read-only mode is enabled" in caplog.text


@pytest.mark.asyncio
async def test_disabled_tags_hide_matching_tools(load_server, caplog):
    caplog.set_level(logging.INFO)
    names = await tool_names(load_server(DISABLED_TAGS="bills, alert"))

    assert names.isdisjoint({"bills_list", "bill_delete", "alerts_get"})
    # Alerting is split into three tags; only "alert" was disabled.
    assert {"alert_rules_list", "alert_templates_list", "device_get"} <= names
    assert "Disabled tags configured" in caplog.text


@pytest.mark.asyncio
async def test_read_only_mode_and_disabled_tags_combine(load_server):
    names = await tool_names(load_server(READ_ONLY_MODE="true", DISABLED_TAGS="ports"))

    assert "device_get" in names
    assert names.isdisjoint({"ports_list", "port_graph", "device_delete"})


@pytest.mark.parametrize(
    ("strategy", "transform"),
    [("bm25", BM25SearchTransform), ("regex", RegexSearchTransform)],
)
@pytest.mark.asyncio
async def test_tool_search_replaces_the_tool_list(
    load_server, caplog, strategy, transform
):
    caplog.set_level(logging.INFO)
    server = load_server(
        TOOL_SEARCH_ENABLED="true",
        TOOL_SEARCH_STRATEGY=strategy,
        TOOL_SEARCH_MAX_RESULTS="3",
    )

    [search] = [t for t in server.mcp.transforms if isinstance(t, transform)]
    assert search._max_results == 3
    assert await tool_names(server) == {"search_tools", "call_tool"}
    assert f"Tool search is enabled - strategy={strategy}, max_results=3" in (
        caplog.text
    )


def test_tool_search_is_off_by_default(load_server):
    server = load_server()

    assert not any(
        isinstance(t, BM25SearchTransform | RegexSearchTransform)
        for t in server.mcp.transforms
    )


def test_rate_limiting_adds_middleware(load_server, caplog):
    caplog.set_level(logging.INFO)
    server = load_server(
        RATE_LIMIT_ENABLED="true",
        RATE_LIMIT_MAX_REQUESTS="5",
        RATE_LIMIT_WINDOW_MINUTES="2",
    )

    [limiter] = [
        m
        for m in server.mcp.middleware
        if isinstance(m, SlidingWindowRateLimitingMiddleware)
    ]
    assert (limiter.max_requests, limiter.window_seconds) == (5, 120)
    assert "Rate limiting is enabled" in caplog.text


def test_rate_limiting_is_off_by_default(load_server):
    server = load_server()

    assert not any(
        isinstance(m, SlidingWindowRateLimitingMiddleware)
        for m in server.mcp.middleware
    )


def test_unknown_log_level_falls_back_to_info(load_server, caplog):
    load_server(LOG_LEVEL="chatty")

    assert "Unknown LOG_LEVEL 'CHATTY' - falling back to INFO" in caplog.text


@pytest.mark.parametrize("level", [" debug ", "", "   "])
def test_lowercase_or_blank_log_level_is_accepted(load_server, caplog, level):
    """Blank means unset (INFO), as for every other setting: no warning."""
    load_server(LOG_LEVEL=level)

    assert "Unknown LOG_LEVEL" not in caplog.text


def test_version_comes_from_the_package_metadata(load_server, monkeypatch):
    asked = []

    def version(name: str) -> str:
        asked.append(name)
        return "9.8.7"

    monkeypatch.setattr(importlib.metadata, "version", version)

    server = load_server()

    # The distribution name from pyproject.toml, or the lookup always fails.
    assert asked == ["librenms-mcp"]
    assert server.__version__ == "9.8.7"
    assert server.mcp.version == "9.8.7"


def test_version_falls_back_when_package_is_not_installed(load_server, monkeypatch):
    def missing(_name):
        raise importlib.metadata.PackageNotFoundError

    monkeypatch.setattr(importlib.metadata, "version", missing)

    assert load_server().__version__ == "0.0.1"


@pytest.mark.parametrize(
    ("env", "message"),
    [
        ({"LIBRENMS_URL": ""}, "LIBRENMS_URL environment variable is required"),
        (
            {"TOOL_SEARCH_ENABLED": "true", "TOOL_SEARCH_STRATEGY": "regx"},
            "TOOL_SEARCH_STRATEGY must be 'bm25' or 'regex'",
        ),
        ({"MCP_TRANSPORT": "http", "MCP_HTTP_PORT": "auto"}, "MCP_HTTP_PORT"),
    ],
)
def test_invalid_configuration_is_logged_and_raised(load_server, caplog, env, message):
    with pytest.raises(ValueError, match=message):
        load_server(**env)

    assert f"Invalid configuration: {message}" in caplog.text


def test_bearer_token_enables_auth(load_server):
    auth = load_server(MCP_HTTP_BEARER_TOKEN=" secret ").mcp.auth

    assert isinstance(auth, StaticTokenVerifier)
    assert auth.tokens == {
        "secret": {"client_id": "authenticated-client", "scopes": ["read", "write"]}
    }


@pytest.mark.parametrize("transport", [None, "stdio", " STDIO "])
def test_main_runs_stdio_by_default(load_server, caplog, transport):
    caplog.set_level(logging.INFO)
    env = {} if transport is None else {"MCP_TRANSPORT": transport}
    server = load_server(**env)

    server.main()

    server.mcp.run.assert_called_once_with()
    assert "Starting LibreNMS MCP Server at https://nms.invalid" in caplog.text
    assert "Using STDIO transport" in caplog.text
    assert "WITHOUT authentication" not in caplog.text


@pytest.mark.parametrize(
    ("transport", "expected", "label"),
    [
        ("http", "http", "Streamable"),
        ("streamable-http", "http", "Streamable"),
        ("sse", "sse", "SSE"),
    ],
)
def test_main_runs_http_transports_on_the_configured_address(
    load_server, caplog, transport, expected, label
):
    caplog.set_level(logging.INFO)
    server = load_server(
        MCP_TRANSPORT=transport,
        MCP_HTTP_HOST="[::1]",
        MCP_HTTP_PORT="9001",
        MCP_HTTP_BEARER_TOKEN="secret",
    )

    server.main()

    server.mcp.run.assert_called_once_with(transport=expected, host="::1", port=9001)
    assert f"Using HTTP {label} transport on ::1:9001" in caplog.text
    assert f"Bearer token authentication enabled for {label} transport" in (caplog.text)
    assert "WITHOUT authentication" not in caplog.text


@pytest.mark.parametrize("transport", ["http", "sse"])
def test_main_warns_when_http_runs_without_a_token(load_server, caplog, transport):
    caplog.set_level(logging.INFO)
    server = load_server(MCP_TRANSPORT=transport)

    server.main()

    server.mcp.run.assert_called_once_with(
        transport=transport, host="127.0.0.1", port=8000
    )
    assert "WITHOUT authentication" in caplog.text
    assert "Bearer token authentication enabled" not in caplog.text


def test_main_rejects_an_unknown_transport(load_server, caplog):
    server = load_server(MCP_TRANSPORT="websocket")

    with pytest.raises(SystemExit) as exc:
        server.main()

    assert exc.value.code == 1
    assert (
        "Unknown MCP_TRANSPORT 'websocket'. Valid values: "
        "stdio, sse, http, streamable-http"
    ) in caplog.text
    server.mcp.run.assert_not_called()
