"""End-to-end checks of the URLs the tools send to LibreNMS.

Tool arguments come from the model and may be prompt-injected, so a value must
never be able to steer a request to a different endpoint.
"""

import httpx2
import pytest
from fastmcp import Client
from fastmcp import FastMCP

from librenms_mcp.librenms_client import LibreNMSClient
from librenms_mcp.models import LibreNMSConfig
from librenms_mcp.tools import register_tools


@pytest.fixture
def server():
    """Yield (mcp, requests, set_handler) backed by a scripted LibreNMS.

    LibreNMSClient is a singleton, so the class state is reset around each test
    rather than leaking an instance into the others.
    """
    LibreNMSClient._instance = None
    LibreNMSClient._initialized = False
    config = LibreNMSConfig(librenms_url="https://nms.invalid", token="t")
    requests: list[httpx2.Request] = []
    state = {"handler": lambda _r: httpx2.Response(200, json={"status": "ok"})}

    def transport(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        return state["handler"](request)

    client = LibreNMSClient(config)
    client.client = httpx2.AsyncClient(
        base_url=client.base_url, transport=httpx2.MockTransport(transport)
    )
    mcp = FastMCP("test")
    register_tools(mcp, config)

    def set_handler(handler) -> None:
        state["handler"] = handler

    try:
        yield mcp, requests, set_handler
    finally:
        LibreNMSClient._instance = None
        LibreNMSClient._initialized = False


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("tool", "args", "expected_path"),
    [
        (
            "device_get",
            {"hostname": "core1/discover"},
            "/api/v0/devices/core1%2Fdiscover",
        ),
        ("device_get", {"hostname": "sw#1"}, "/api/v0/devices/sw%231"),
        ("device_get", {"hostname": " sw1 "}, "/api/v0/devices/%20sw1%20"),
        ("poller_group_get", {"poller_group": "a/b"}, "/api/v0/poller_group/a%2Fb"),
        (
            "bill_graph_data",
            {"bill_id": 1, "graph_type": "a/b"},
            "/api/v0/bills/1/graphdata/a%2Fb",
        ),
    ],
)
async def test_string_arguments_stay_in_one_path_segment(
    server, tool, args, expected_path
):
    mcp, requests, _ = server
    async with Client(mcp) as client:
        await client.call_tool(tool, args, raise_on_error=False)
    assert [r.url.raw_path.decode().split("?")[0] for r in requests] == [expected_path]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("tool", "args"),
    [
        ("device_delete", {"hostname": ".."}),
        ("device_delete", {"hostname": "../rules/5"}),
        ("logs_eventlog", {"hostname": "../../devices/core1/discover"}),
        ("bill_graph_data", {"bill_id": 1, "graph_type": "../../devices"}),
    ],
)
async def test_dot_segments_are_rejected_without_a_request(server, tool, args):
    """Behind a proxy that decodes %2F, '..%2F' would still walk up the path."""
    mcp, requests, _ = server
    async with Client(mcp) as client:
        result = await client.call_tool(tool, args)
    assert "Invalid path segment" in str(result.data)
    assert requests == []
