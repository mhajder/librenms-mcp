"""Tests for SNMP credential redaction in LibreNMS responses."""

import json
from contextlib import asynccontextmanager

import httpx2
import pytest
from fastmcp import Client
from fastmcp import FastMCP

from librenms_mcp.librenms_client import LibreNMSClient
from librenms_mcp.librenms_client import LibreNMSHTTPError
from librenms_mcp.librenms_client import get_librenms_config_from_env
from librenms_mcp.models import LibreNMSConfig
from librenms_mcp.redact import REDACTED
from librenms_mcp.redact import redact_credentials
from librenms_mcp.redact import redact_text
from librenms_mcp.tools import register_tools

CONFIG = LibreNMSConfig(librenms_url="https://nms.invalid", token="t")
OFF = CONFIG.model_copy(update={"redact_snmp_credentials": False})
DEVICE = {
    "device_id": 1,
    "hostname": "rtr1.example.net",
    "sysName": "rtr1",
    "community": "s3cret-community",
    "authname": "snmpuser",
    "authpass": "s3cret-auth",
    "cryptopass": "s3cret-crypto",
    "authalgo": "SHA",
    "snmpver": "v3",
}
SNMP_SERVICE = {
    "service_id": 7,
    "device_id": 1,
    "service_type": "snmp",
    "service_param": "-C s3cret-community -o 1.3.6.1.2.1.1.3.0",
}


def _answer(request: httpx2.Request) -> httpx2.Response:
    """Answer like LibreNMS: device rows for devices, an snmp service for services."""
    if request.url.path.startswith("/api/v0/services"):
        return httpx2.Response(
            200, json={"status": "ok", "services": [[dict(SNMP_SERVICE)]]}
        )
    return httpx2.Response(200, json={"status": "ok", "devices": [dict(DEVICE)]})


@asynccontextmanager
async def _librenms(handler, config: LibreNMSConfig = CONFIG):
    """Install a LibreNMSClient singleton on a scripted transport, then close it."""
    LibreNMSClient._instance = None
    LibreNMSClient._initialized = False
    client = LibreNMSClient(config)
    client.client = httpx2.AsyncClient(
        base_url=client.base_url, transport=httpx2.MockTransport(handler)
    )
    try:
        yield client
    finally:
        await client.close()
        LibreNMSClient._instance = None
        LibreNMSClient._initialized = False


@pytest.fixture(scope="module")
def tools_server() -> FastMCP:
    """Register every tool once for the module (about half a second each time).

    Redaction reads the client singleton's config, so one server serves both
    settings.
    """
    mcp = FastMCP("test")
    register_tools(mcp, CONFIG)
    return mcp


def test_redacts_device_credentials_in_place_and_keeps_unset_ones():
    body = {"status": "ok", "devices": [dict(DEVICE), {**DEVICE, "community": None}]}
    assert redact_credentials(body) is body
    first, second = body["devices"]
    assert first["authpass"] == first["cryptopass"] == first["community"] == REDACTED
    assert first["authname"] == REDACTED
    assert second["community"] is None
    assert first["authalgo"] == "SHA"
    assert first["snmpver"] == "v3"


def test_leaves_community_fields_outside_device_records():
    """A BGP or routing community is not a credential."""
    body = {
        "status": "ok",
        "bgp_sessions": [{"bgpPeerIdentifier": "10.0.0.1", "community": "65000:100"}],
        "nested": {"device": dict(DEVICE)},
    }
    redact_credentials(body)
    assert body["bgp_sessions"][0]["community"] == "65000:100"
    assert body["nested"]["device"]["community"] == REDACTED


@pytest.mark.parametrize(
    ("param", "expected"),
    [
        ("-C s3cret -o 1.3.6.1.2.1.1.3.0", f"-C {REDACTED} -o 1.3.6.1.2.1.1.3.0"),
        ("-Cs3cret -o sysUpTime.0", f"-C{REDACTED} -o sysUpTime.0"),
        ("--community=s3cret -o x", f"--community={REDACTED} -o x"),
        (
            "-P 3 -L authPriv -U user -a SHA -A 's3 cret' -x AES -X s3cret",
            f"-P 3 -L authPriv -U {REDACTED} -a SHA -A {REDACTED} -x AES -X {REDACTED}",
        ),
        (
            "--secname user --authpasswd=s3cret",
            f"--secname {REDACTED} --authpasswd={REDACTED}",
        ),
        # -c is the critical threshold, not the community.
        ("-c 10 -w 5", "-c 10 -w 5"),
    ],
)
def test_redacts_check_snmp_credentials_in_service_param(param, expected):
    body = {"services": [[{**SNMP_SERVICE, "service_param": param}]]}
    redact_credentials(body)
    assert body["services"][0][0]["service_param"] == expected


def test_leaves_other_service_types_alone():
    """check_http's -C is a certificate age and -A a user agent."""
    service = {**SNMP_SERVICE, "service_type": "http", "service_param": "-C 30 -A bot"}
    redact_credentials({"services": [service]})
    assert service["service_param"] == "-C 30 -A bot"


@pytest.mark.parametrize(
    "text",
    [
        json.dumps({"status": "ok", "devices": [DEVICE]}),
        # A proxy cut the body short inside the value.
        '{"devices":[{"device_id":1,"community":"s3cret-comm',
        '{"authpass": "s3cret \\" quoted"}',
    ],
)
def test_redact_text_scrubs_raw_json(text):
    scrubbed = redact_text(text)
    assert "s3cret" not in scrubbed
    assert REDACTED in scrubbed


def _notice_then_json(_request: httpx2.Request) -> httpx2.Response:
    """A PHP notice before the JSON makes the body undecodable."""
    body = "Deprecated: something in api_functions.inc.php\n" + json.dumps(
        {"status": "ok", "devices": [DEVICE]}
    )
    return httpx2.Response(200, text=body)


def _error_without_message(_request: httpx2.Request) -> httpx2.Response:
    """A non-2xx JSON body without a message is quoted as text."""
    return httpx2.Response(500, json={"devices": [DEVICE]})


@pytest.mark.asyncio
@pytest.mark.parametrize("handler", [_notice_then_json, _error_without_message])
async def test_error_messages_never_quote_credentials(handler):
    async with _librenms(handler) as client:
        with pytest.raises(LibreNMSHTTPError) as raised:
            await client.get("devices", raise_for_status=True)
    assert "s3cret" not in str(raised.value)
    assert "s3cret" not in json.dumps(raised.value.body)


@pytest.mark.asyncio
async def test_error_messages_quote_credentials_when_turned_off():
    async with _librenms(_notice_then_json, OFF) as client:
        with pytest.raises(LibreNMSHTTPError, match="s3cret-community"):
            await client.get("devices")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("tool", "args"),
    [
        ("device_get", {"hostname": "rtr1.example.net"}),
        ("devices_list", {}),
        ("services_list", {}),
    ],
)
async def test_tools_never_return_credentials(tools_server, tool, args):
    async with _librenms(_answer), Client(tools_server) as mcp_client:
        result = await mcp_client.call_tool(tool, args)
    text = result.content[0].text
    assert REDACTED in text
    assert "s3cret" not in text


@pytest.mark.asyncio
async def test_redaction_can_be_turned_off(tools_server):
    async with _librenms(_answer, OFF), Client(tools_server) as mcp_client:
        result = await mcp_client.call_tool(
            "device_get", {"hostname": "rtr1.example.net"}
        )
    text = result.content[0].text
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
