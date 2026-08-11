"""Guards for how the client reports responses it cannot decode."""

import httpx
import pytest

from librenms_mcp.librenms_client import LibreNMSClient
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
        client.client = httpx.AsyncClient(
            base_url=client.base_url, transport=httpx.MockTransport(handler)
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
        lambda _request: httpx.Response(502, text="<html>502 Bad Gateway</html>")
    )

    with pytest.raises(RuntimeError, match="HTTP 502"):
        await client.get("devices")

    await client.close()


@pytest.mark.asyncio
async def test_librenms_json_errors_are_returned_not_raised(mock_client):
    """LibreNMS reports its own errors as JSON, which is more useful than the code."""
    client = mock_client(
        lambda _request: httpx.Response(
            404, json={"status": "error", "message": "Device foo not found"}
        )
    )

    assert await client.get("devices/foo") == {
        "status": "error",
        "message": "Device foo not found",
    }

    await client.close()
