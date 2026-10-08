"""Guards for how the client reports responses it cannot decode."""

import os
import subprocess
import sys

import httpx2
import pytest

from librenms_mcp.librenms_client import LibreNMSClient
from librenms_mcp.librenms_client import LibreNMSHTTPError
from librenms_mcp.librenms_client import _build_path
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

    assert await client.get("devices", "foo") == {
        "status": "error",
        "message": "Device foo not found",
    }

    await client.close()


@pytest.mark.asyncio
async def test_get_raw_keeps_the_librenms_error_message(mock_client):
    """Graph errors must explain themselves, not just report the status code."""
    client = mock_client(
        lambda _request: httpx2.Response(
            404, json={"status": "error", "message": "Device foo not found"}
        )
    )

    with pytest.raises(LibreNMSHTTPError, match="Device foo not found") as exc:
        await client.get_raw("devices", "foo", "device_bits")
    assert exc.value.status_code == 404

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


@pytest.mark.asyncio
async def test_get_raw_reports_redirects(mock_client):
    """A redirect is not followed, so it must not be mistaken for a graph."""
    client = mock_client(
        lambda _request: httpx2.Response(
            302, headers={"location": "https://sso.invalid/login"}, text="<html/>"
        )
    )

    with pytest.raises(LibreNMSHTTPError, match=r"redirected to https://sso\.invalid"):
        await client.get_raw("devices", "sw1", "device_bits")

    await client.close()


@pytest.mark.parametrize(
    ("segments", "expected"),
    [
        (("devices",), "devices"),
        (("devices", "core1", "ports"), "devices/core1/ports"),
        (("bills", 5, "history"), "bills/5/history"),
        (("devices", "core1/discover"), "devices/core1%2Fdiscover"),
        (("devices", "sw#1", "ports", "Te2/7"), "devices/sw%231/ports/Te2%2F7"),
        # A pre-joined path passed by mistake stays one segment: a 404, not
        # a request to a different endpoint.
        (("devices/core1/discover",), "devices%2Fcore1%2Fdiscover"),
    ],
)
def test_build_path_encodes_every_segment(segments, expected):
    assert _build_path(segments) == expected


@pytest.mark.parametrize("segments", [(), ("devices", ".."), ("devices", "")])
def test_build_path_rejects_empty_and_dot_segments(segments):
    with pytest.raises(ValueError, match="segment"):
        _build_path(segments)


@pytest.mark.asyncio
async def test_request_refuses_traversal_without_sending(mock_client):
    sent = []
    client = mock_client(lambda request: sent.append(request) or httpx2.Response(200))

    with pytest.raises(ValueError, match="Invalid path segment"):
        await client.delete("devices", "..")
    assert sent == []

    await client.close()


@pytest.mark.asyncio
async def test_framework_errors_are_marked_as_errors(mock_client):
    """A 401 body has only a message; callers rely on status == 'error'."""
    client = mock_client(
        lambda _request: httpx2.Response(401, json={"message": "Unauthenticated."})
    )

    assert await client.get("devices") == {
        "status": "error",
        "message": "Unauthenticated.",
    }

    await client.close()


@pytest.mark.asyncio
async def test_request_reports_redirects(mock_client):
    """JSON tools must name the redirect target, not report an empty body."""
    client = mock_client(
        lambda _request: httpx2.Response(
            301, headers={"location": "https://nms.invalid/api/v0/devices"}
        )
    )

    with pytest.raises(RuntimeError, match=r"HTTP 301.*redirected to https://"):
        await client.get("devices")

    await client.close()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("response", "from_librenms"),
    [
        (
            httpx2.Response(
                404, json={"status": "error", "message": "Port Te2/99 not found"}
            ),
            True,
        ),
        (httpx2.Response(404, text="<html>Not Found</html>"), False),
        # An API gateway answering in JSON is still not LibreNMS.
        (httpx2.Response(404, json={"message": "no Route matched"}), False),
    ],
)
async def test_get_raw_tells_librenms_errors_from_proxy_errors(
    mock_client, response, from_librenms
):
    client = mock_client(lambda _request: response)

    with pytest.raises(LibreNMSHTTPError) as exc:
        await client.get_raw("devices", "sw1", "ports", "Te2/99", "bits")
    assert exc.value.from_librenms is from_librenms

    await client.close()


@pytest.mark.asyncio
async def test_raise_for_status_keeps_the_normalized_body(mock_client):
    client = mock_client(
        lambda _request: httpx2.Response(401, json={"message": "Unauthenticated."})
    )

    with pytest.raises(LibreNMSHTTPError) as exc:
        await client.get("devices", raise_for_status=True)
    assert exc.value.status_code == 401
    assert exc.value.from_librenms is False
    assert exc.value.body == {"status": "error", "message": "Unauthenticated."}

    await client.close()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("response", "expected"),
    [
        (
            httpx2.Response(503, json=["upstream", "down"]),
            {"status": "error", "message": "HTTP 503", "body": ["upstream", "down"]},
        ),
        (
            httpx2.Response(503, json={"status": 503, "message": "Unavailable"}),
            {"status": "error", "message": "Unavailable", "upstream_status": 503},
        ),
        (
            httpx2.Response(502, json={"detail": "bad gateway"}),
            {"status": "error", "detail": "bad gateway", "message": "HTTP 502"},
        ),
    ],
)
async def test_every_error_body_is_marked(mock_client, response, expected):
    """Callers check status == 'error'; a gateway's body must not pass as success."""
    client = mock_client(lambda _request: response)

    assert await client.get("devices") == expected

    await client.close()


@pytest.mark.asyncio
async def test_request_reports_redirect_target_even_with_json_body(mock_client):
    client = mock_client(
        lambda _request: httpx2.Response(
            302,
            headers={"location": "https://sso.invalid/login"},
            json={"message": "Found"},
        )
    )

    with pytest.raises(LibreNMSHTTPError, match=r"redirected to https://sso\.invalid"):
        await client.get("devices")

    await client.close()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("response", "hinted"),
    [
        (httpx2.Response(404, text="<html>Not Found</html>"), True),
        # LibreNMS's own answer is not a proxy problem.
        (httpx2.Response(404, json={"status": "error", "message": "Not found"}), False),
    ],
)
async def test_encoded_slash_404_explains_the_proxy_setting(
    mock_client, response, hinted
):
    client = mock_client(lambda _request: response)

    with pytest.raises(LibreNMSHTTPError) as exc:
        await client.get_raw("ports", "search", "ifName", "Te2/7")
    assert ("AllowEncodedSlashes NoDecode" in str(exc.value)) is hinted

    await client.close()


def test_http_host_is_stripped_like_the_healthcheck_reads_it(monkeypatch):
    monkeypatch.setenv("MCP_HTTP_HOST", " 0.0.0.0 ")
    assert get_transport_config_from_env().http_host == "0.0.0.0"  # noqa: S104


@pytest.mark.asyncio
async def test_proxy_400_for_encoded_slash_is_hinted(mock_client):
    """Tomcat and newer Traefik reject %2F with 400 rather than 404."""
    client = mock_client(lambda _request: httpx2.Response(400, text="Bad Request"))

    with pytest.raises(LibreNMSHTTPError, match="AllowEncodedSlashes") as exc:
        await client.get_raw("devices", "sw1", "ports", "Te2/7", "port_bits")
    assert exc.value.status_code == 400

    await client.close()


@pytest.mark.asyncio
async def test_returned_error_body_carries_the_encoded_slash_hint(mock_client):
    """Most tools return the body instead of raising; the hint must be in it."""
    client = mock_client(
        lambda _request: httpx2.Response(404, json={"message": "Not Found"})
    )

    body = await client.get("ports", "search", "Gi0/1")
    assert body["status"] == "error"
    assert "AllowEncodedSlashes NoDecode" in body["hint"]

    await client.close()


@pytest.mark.asyncio
async def test_librenms_ok_body_on_error_status_is_left_as_is(mock_client):
    """api_success_noresult can pair status 'ok' with a 4xx; that is LibreNMS."""
    client = mock_client(
        lambda _request: httpx2.Response(
            404, json={"status": "ok", "message": "No results", "count": 0}
        )
    )

    assert await client.get("ports", "search", "Gi0/1") == {
        "status": "ok",
        "message": "No results",
        "count": 0,
    }
    with pytest.raises(LibreNMSHTTPError) as exc:
        await client.get("ports", "search", "Gi0/1", raise_for_status=True)
    assert exc.value.from_librenms is True
    assert "AllowEncodedSlashes" not in str(exc.value)

    await client.close()


@pytest.mark.asyncio
async def test_raise_for_status_keeps_raw_origin_and_normalized_body(mock_client):
    client = mock_client(
        lambda _request: httpx2.Response(503, json={"status": 503, "message": "Down"})
    )

    with pytest.raises(LibreNMSHTTPError) as exc:
        await client.get("devices", raise_for_status=True)
    assert exc.value.from_librenms is False
    assert exc.value.body == {
        "status": "error",
        "message": "Down",
        "upstream_status": 503,
    }

    await client.close()
