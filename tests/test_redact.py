"""Tests for SNMP credential redaction in LibreNMS responses."""

import httpx2
import pytest
from fastmcp import Client
from fastmcp import FastMCP

from librenms_mcp.librenms_client import LibreNMSClient
from librenms_mcp.librenms_client import get_librenms_config_from_env
from librenms_mcp.models import LibreNMSConfig
from librenms_mcp.redact import REDACTED
from librenms_mcp.redact import redact_credentials
from librenms_mcp.tools import register_tools

CONFIG = LibreNMSConfig(librenms_url="https://nms.invalid", token="t")
DEVICE = {
    "device_id": 1,
    "hostname": "rtr1.example.net",
    "community": "s3cret-community",
    "authname": "snmpuser",
    "authpass": "s3cret-auth",
    "cryptopass": "s3cret-crypto",
    "authalgo": "SHA",
    "snmpver": "v3",
}


def test_redacts_set_credentials_at_any_depth_and_keeps_unset_ones():
    body = {"status": "ok", "devices": [DEVICE, {**DEVICE, "community": None}]}
    redacted = redact_credentials(body)
    first, second = redacted["devices"]
    assert first["authpass"] == first["cryptopass"] == first["community"] == REDACTED
    assert first["authname"] == REDACTED
    assert second["community"] is None
    assert first["authalgo"] == "SHA"
    assert first["snmpver"] == "v3"
    assert body["devices"][0]["authpass"] == "s3cret-auth"  # input left untouched


async def _call(tool: str, args: dict, config: LibreNMSConfig) -> str:
    """Call a tool against a LibreNMS that returns DEVICE; return the result text."""
    LibreNMSClient._instance = None
    LibreNMSClient._initialized = False
    client = LibreNMSClient(config)
    client.client = httpx2.AsyncClient(
        base_url=client.base_url,
        transport=httpx2.MockTransport(
            lambda _: httpx2.Response(200, json={"status": "ok", "devices": [DEVICE]})
        ),
    )
    mcp = FastMCP("test")
    register_tools(mcp, config)
    try:
        async with Client(mcp) as mcp_client:
            result = await mcp_client.call_tool(tool, args)
    finally:
        LibreNMSClient._instance = None
        LibreNMSClient._initialized = False
    return result.content[0].text


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("tool", "args"),
    [("device_get", {"hostname": "rtr1.example.net"}), ("devices_list", {})],
)
async def test_device_tools_never_return_credentials(tool, args):
    text = await _call(tool, args, CONFIG)
    assert "rtr1.example.net" in text
    assert "s3cret" not in text


@pytest.mark.asyncio
async def test_redaction_can_be_turned_off():
    config = CONFIG.model_copy(update={"redact_snmp_credentials": False})
    text = await _call("device_get", {"hostname": "rtr1.example.net"}, config)
    assert "s3cret-auth" in text
    assert REDACTED not in text


@pytest.mark.parametrize(("raw", "expected"), [(None, True), ("false", False)])
def test_redact_snmp_credentials_setting(monkeypatch, raw, expected):
    monkeypatch.setenv("LIBRENMS_URL", "https://nms.invalid")
    monkeypatch.setenv("LIBRENMS_TOKEN", "t")
    if raw is None:
        monkeypatch.delenv("REDACT_SNMP_CREDENTIALS", raising=False)
    else:
        monkeypatch.setenv("REDACT_SNMP_CREDENTIALS", raw)
    assert get_librenms_config_from_env().redact_snmp_credentials is expected
