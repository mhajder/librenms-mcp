"""Tests for outbound User-Agent configuration and header injection."""

import httpx2
import pytest

from librenms_mcp.librenms_client import DEFAULT_USER_AGENT
from librenms_mcp.librenms_client import LibreNMSClient
from librenms_mcp.librenms_client import get_librenms_config_from_env
from librenms_mcp.models import LibreNMSConfig


def test_env_user_agent_defaults_and_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LIBRENMS_URL", "https://nms.invalid")
    monkeypatch.setenv("LIBRENMS_TOKEN", "t")
    monkeypatch.delenv("LIBRENMS_USER_AGENT", raising=False)

    assert get_librenms_config_from_env().user_agent is None

    monkeypatch.setenv("LIBRENMS_USER_AGENT", "  custom-librenms/1.0  ")
    assert get_librenms_config_from_env().user_agent == "custom-librenms/1.0"

    monkeypatch.setenv("LIBRENMS_USER_AGENT", "   ")
    assert get_librenms_config_from_env().user_agent is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("configured", "expected"),
    [
        (None, DEFAULT_USER_AGENT),
        ("custom-librenms/1.0", "custom-librenms/1.0"),
    ],
)
async def test_outbound_requests_send_user_agent(
    monkeypatch: pytest.MonkeyPatch, configured: str | None, expected: str
) -> None:
    seen: list[str | None] = []
    real_async_client = httpx2.AsyncClient

    def handler(request: httpx2.Request) -> httpx2.Response:
        seen.append(request.headers.get("User-Agent"))
        return httpx2.Response(200, json={"status": "ok", "devices": []})

    def patched_async_client(*args, **kwargs):
        kwargs["transport"] = httpx2.MockTransport(handler)
        return real_async_client(*args, **kwargs)

    monkeypatch.setattr(httpx2, "AsyncClient", patched_async_client)

    LibreNMSClient._instance = None
    LibreNMSClient._initialized = False
    try:
        client = LibreNMSClient(
            LibreNMSConfig(
                librenms_url="https://nms.invalid",
                token="t",
                user_agent=configured,
            )
        )
        async with client:
            await client.get("devices")
        await client.close()
    finally:
        LibreNMSClient._instance = None
        LibreNMSClient._initialized = False

    assert seen == [expected]
