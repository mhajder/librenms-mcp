"""Guards for how the client reports responses it cannot decode."""

import os
import subprocess
import sys

import httpx2
import pytest

from librenms_mcp.librenms_client import LibreNMSClient
from librenms_mcp.librenms_client import get_transport_config_from_env
from librenms_mcp.models import LibreNMSConfig


@pytest.fixture
def mock_client():
    """Yield a client whose transport is scripted per test.

    LibreNMSClient is a singleton, so the class state is reset around each test
    rather than leaking an instance into the others.
    """

    def build(handler) -> LibreNMSClient:
        client = LibreNMSClient(
            LibreNMSConfig(librenms_url="https://nms.invalid", token="t")
        )
        client.client = httpx2.AsyncClient(
            base_url=client.base_url, transport=httpx2.MockTransport(handler)
        )
        return client

    LibreNMSClient._instance = None
    LibreNMSClient._initialized = False
    try:
        yield build
    finally:
        LibreNMSClient._instance = None
        LibreNMSClient._initialized = False


@pytest.mark.asyncio
async def test_non_json_body_reports_the_status_code(mock_client):
    """A proxy error page must not surface as a bare JSON decode error."""
    client = mock_client(
        lambda _request: httpx2.Response(502, text="<html>502 Bad Gateway</html>")
    )

    with pytest.raises(RuntimeError, match="HTTP 502"):
        await client.get("devices")

    await client.close()


@pytest.mark.asyncio
async def test_librenms_json_errors_are_returned_not_raised(mock_client):
    """LibreNMS reports its own errors as JSON, which is more useful than the code."""
    client = mock_client(
        lambda _request: httpx2.Response(
            404, json={"status": "error", "message": "Device foo not found"}
        )
    )

    assert await client.get("devices/foo") == {
        "status": "error",
        "message": "Device foo not found",
    }

    await client.close()


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, "stdio"),
        ("", "stdio"),
        ("stdio", "stdio"),
        ("SSE", "sse"),
        ("http", "http"),
        ("streamable-http", "http"),
    ],
)
def test_transport_type_accepts_known_values(monkeypatch, raw, expected):
    if raw is None:
        monkeypatch.delenv("MCP_TRANSPORT", raising=False)
    else:
        monkeypatch.setenv("MCP_TRANSPORT", raw)
    assert get_transport_config_from_env().transport_type == expected


def test_unknown_transport_type_stops_main(tmp_path):
    """A typo must not silently fall back to stdio and never bind the port.

    It is rejected in main() rather than at import, because `fastmcp run`
    imports the module but chooses the transport itself.
    """
    env = {
        **os.environ,
        "LIBRENMS_URL": "https://nms.invalid",
        "LIBRENMS_TOKEN": "t",
        "MCP_TRANSPORT": "websocket",
    }
    code = "import librenms_mcp.server as s; s.main()"
    proc = subprocess.run(  # noqa: S603
        [sys.executable, "-c", code],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert proc.returncode == 1
    assert "Unknown MCP_TRANSPORT 'websocket'" in proc.stderr


def test_unknown_transport_type_does_not_break_import(monkeypatch):
    monkeypatch.setenv("MCP_TRANSPORT", "websocket")
    assert get_transport_config_from_env().transport_type == "websocket"


def test_blank_http_port_uses_default(monkeypatch):
    monkeypatch.setenv("MCP_TRANSPORT", "http")
    monkeypatch.setenv("MCP_HTTP_PORT", "")
    assert get_transport_config_from_env().http_port == 8000


def test_http_host_is_stripped_like_the_healthcheck_reads_it(monkeypatch):
    monkeypatch.setenv("MCP_HTTP_HOST", " 0.0.0.0 ")
    assert get_transport_config_from_env().http_host == "0.0.0.0"  # noqa: S104
