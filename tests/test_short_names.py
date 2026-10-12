"""Tests for ShortHostnameMiddleware (RESOLVE_SHORT_HOSTNAMES)."""

from urllib.parse import unquote

import httpx2
import pytest
from fastmcp import Client
from fastmcp import FastMCP
from fastmcp.server.transforms.search import BM25SearchTransform

from librenms_mcp.librenms_client import LibreNMSClient
from librenms_mcp.librenms_client import get_librenms_config_from_env
from librenms_mcp.models import LibreNMSConfig
from librenms_mcp.short_names import ShortHostnameMiddleware
from librenms_mcp.short_names import is_short_name
from librenms_mcp.tools import register_tools

CONFIG = LibreNMSConfig(librenms_url="https://nms.invalid", token="t")
FQDN = "rtr1.dc1.example.net"

# Search hits carry SNMP credentials; they must never reach an error message.
DEVICES = [
    {"device_id": 1, "hostname": FQDN, "sysName": "rtr1", "community": "secret"},
    {"device_id": 2, "hostname": "rtr10.dc1.example.net", "sysName": "rtr10"},
    {"device_id": 3, "hostname": "sw1.dc1.example.net", "authpass": "secret"},
    {"device_id": 4, "hostname": "sw1.dc2.example.net", "authpass": "secret"},
]


def _librenms(request: httpx2.Request) -> httpx2.Response:
    """A LibreNMS that knows DEVICES by stored hostname or ID only."""
    parts = request.url.path.split("/")
    if parts[3:] == ["devices"] and request.url.params.get("type") == "hostname":
        query = request.url.params["query"]
        hits = [d for d in DEVICES if query.lower() in str(d["hostname"])]
        return httpx2.Response(200, json={"status": "ok", "devices": hits})
    if request.method == "GET" and len(parts) == 5 and parts[3] == "devices":
        name = unquote(parts[4])
        found = [d for d in DEVICES if name in (d["hostname"], str(d["device_id"]))]
        if not found:
            return httpx2.Response(
                404,
                json={"status": "error", "message": f"Device {name} does not exist"},
            )
        return httpx2.Response(200, json={"status": "ok", "devices": found})
    return httpx2.Response(200, json={"status": "ok", "bgp_sessions": [], "logs": []})


@pytest.fixture(scope="module")
def tools_server() -> FastMCP:
    mcp = FastMCP("test")
    register_tools(mcp, CONFIG)
    mcp.add_middleware(ShortHostnameMiddleware(CONFIG))
    return mcp


@pytest.fixture
def server(tools_server):
    LibreNMSClient._instance = None
    LibreNMSClient._initialized = False
    requests: list[httpx2.Request] = []
    state = {"handler": _librenms}

    def transport(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        return state["handler"](request)

    def set_handler(handler) -> None:
        state["handler"] = handler

    client = LibreNMSClient(CONFIG)
    client.client = httpx2.AsyncClient(
        base_url=client.base_url, transport=httpx2.MockTransport(transport)
    )
    try:
        yield tools_server, requests, set_handler
    finally:
        LibreNMSClient._instance = None
        LibreNMSClient._initialized = False


def _is_search(request: httpx2.Request) -> bool:
    return request.url.params.get("type") == "hostname"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("rtr1", True),
        ("RTR1", True),
        (FQDN, False),
        ("10.0.0.1", False),
        ("468", False),
        ("", False),
        (None, False),
        (468, False),
    ],
)
def test_is_short_name(value, expected):
    assert is_short_name(value) is expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("tool", "args", "expected_url"),
    [
        # The query-param case: the device check and the filter must both get
        # the FQDN, or LibreNMS drops the unknown filter and lists every device.
        ("bgp_sessions", {"hostname": "rtr1"}, f"/api/v0/bgp?hostname={FQDN}"),
        ("logs_eventlog", {"hostname": "RTR1"}, f"/api/v0/logs/eventlog/{FQDN}"),
        ("device_get", {"hostname": "rtr1"}, f"/api/v0/devices/{FQDN}"),
        (
            "arp_search",
            {"query": "all", "device": "rtr1"},
            f"/api/v0/resources/ip/arp/all?device={FQDN}",
        ),
    ],
)
async def test_short_name_resolves_everywhere(server, tool, args, expected_url):
    mcp, requests, _ = server
    async with Client(mcp) as client:
        await client.call_tool(tool, args)
    tool_urls = [
        unquote(r.url.raw_path.decode()) for r in requests if not _is_search(r)
    ]
    assert any(url.startswith(expected_url) for url in tool_urls)
    # No request may carry the unresolved short name.
    for url in tool_urls:
        assert FQDN in url or "rtr1" not in url.lower()


@pytest.mark.asyncio
async def test_ambiguous_short_name_is_refused_without_secrets(server):
    mcp, requests, _ = server
    async with Client(mcp) as client:
        result = await client.call_tool("bgp_sessions", {"hostname": "sw1"})
    assert result.data["status"] == "error"
    message = result.data["message"]
    assert "matches 2 devices" in message
    assert "sw1.dc2.example.net (ID 4)" in message
    assert "secret" not in result.content[0].text
    assert all(_is_search(r) for r in requests)


@pytest.mark.asyncio
@pytest.mark.parametrize("hostname", [FQDN, "1"])
async def test_fqdn_and_id_skip_the_search(server, hostname):
    mcp, requests, _ = server
    async with Client(mcp) as client:
        await client.call_tool("device_get", {"hostname": hostname})
    assert not any(_is_search(r) for r in requests)


@pytest.mark.asyncio
async def test_unknown_short_name_passes_through_to_the_device_check(server):
    mcp, requests, _ = server
    async with Client(mcp) as client:
        result = await client.call_tool("bgp_sessions", {"hostname": "nope"})
    assert result.data["message"] == "Device nope does not exist"
    assert not any(r.url.path == "/api/v0/bgp" for r in requests)


@pytest.mark.asyncio
async def test_failed_lookup_passes_the_name_through(server):
    mcp, _, set_handler = server

    def unreachable(request: httpx2.Request) -> httpx2.Response:
        if _is_search(request):
            raise httpx2.ConnectError("boom", request=request)
        return _librenms(request)

    set_handler(unreachable)
    async with Client(mcp) as client:
        result = await client.call_tool("device_get", {"hostname": "rtr1"})
    assert result.data["message"] == "Device rtr1 does not exist"


@pytest.mark.parametrize(("raw", "expected"), [(None, False), ("true", True)])
def test_resolve_short_hostnames_setting(monkeypatch, raw, expected):
    monkeypatch.setenv("LIBRENMS_URL", "https://nms.invalid")
    monkeypatch.setenv("LIBRENMS_TOKEN", "t")
    if raw is None:
        monkeypatch.delenv("RESOLVE_SHORT_HOSTNAMES", raising=False)
    else:
        monkeypatch.setenv("RESOLVE_SHORT_HOSTNAMES", raw)
    assert get_librenms_config_from_env().resolve_short_hostnames is expected


@pytest.mark.asyncio
async def test_tool_search_call_tool_is_resolved_too(server):
    _, requests, _ = server
    mcp = FastMCP("search")
    register_tools(mcp, CONFIG)
    mcp.add_transform(BM25SearchTransform(max_results=5))
    mcp.add_middleware(ShortHostnameMiddleware(CONFIG))
    async with Client(mcp) as client:
        await client.call_tool(
            "call_tool", {"name": "bgp_sessions", "arguments": {"hostname": "rtr1"}}
        )
    assert f"/api/v0/bgp?hostname={FQDN}" in [
        unquote(r.url.raw_path.decode()) for r in requests
    ]
