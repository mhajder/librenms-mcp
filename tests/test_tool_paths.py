"""End-to-end checks of the URLs the tools send to LibreNMS.

Tool arguments come from the model and may be prompt-injected, so a value must
never be able to steer a request to a different endpoint.
"""

import httpx2
import pytest
from fastmcp import Client
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from librenms_mcp.librenms_client import LibreNMSClient
from librenms_mcp.models import LibreNMSConfig
from librenms_mcp.tools import register_tools

SVG = b"<svg xmlns='http://www.w3.org/2000/svg'/>"


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


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "failure",
    [
        # What LibreNMS answers when a proxy decodes %2F into an extra segment.
        httpx2.Response(500, json={"message": "Server Error"}),
        # A proxy rejecting the encoded slash in 'Te2/7' (not LibreNMS JSON).
        httpx2.Response(404, text="<html>Not Found</html>"),
    ],
)
async def test_port_graph_falls_back_on_500_and_proxy_404(server, failure):
    mcp, requests, set_handler = server
    set_handler(_fallback_handler(failure, "Te2/7"))
    async with Client(mcp) as client:
        await client.call_tool("port_graph", {"hostname": "sw1", "ifname": "Te2/7"})
    assert requests[-1].url.path == "/api/v0/portgroups/multiport/bits/9"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("failure", "message"),
    [
        (httpx2.Response(401, json={"message": "Unauthenticated."}), "Unauthenticated"),
        # LibreNMS's own 404 is a real answer, not a proxy problem.
        (
            httpx2.Response(
                404, json={"status": "error", "message": "Port Po99 not found"}
            ),
            "not found",
        ),
    ],
)
async def test_port_graph_reports_real_errors_instead_of_falling_back(
    server, failure, message
):
    mcp, requests, set_handler = server
    set_handler(lambda _r: failure)
    async with Client(mcp) as client:
        with pytest.raises(ToolError, match=message):
            await client.call_tool("port_graph", {"hostname": "sw1", "ifname": "Po99"})
    assert len(requests) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("args", "expected_url"),
    [
        ({"query": "10.0.0.1"}, "/api/v0/resources/ip/arp/10.0.0.1"),
        ({"query": "10.0.0.0/24"}, "/api/v0/resources/ip/arp/10.0.0.0/24"),
        (
            {"query": "all", "device": "core1"},
            "/api/v0/resources/ip/arp/all?device=core1",
        ),
        (
            {"query": " ALL ", "device": "core1"},
            "/api/v0/resources/ip/arp/all?device=core1",
        ),
        (
            {"query": "10.0.0.0/255.255.255.0"},
            "/api/v0/resources/ip/arp/10.0.0.0/24",
        ),
        (
            {"query": "00:11:22:33:44:55"},
            "/api/v0/resources/ip/arp/00%3A11%3A22%3A33%3A44%3A55",
        ),
        # The network address is sent, matching what LibreNMS looks up.
        ({"query": "10.0.0.5/24"}, "/api/v0/resources/ip/arp/10.0.0.0/24"),
    ],
)
async def test_arp_search_routes_cidr_and_device(server, args, expected_url):
    mcp, requests, _ = server
    async with Client(mcp) as client:
        await client.call_tool("arp_search", args)
    # A given device is checked first; the ARP request comes last.
    assert requests[-1].url.raw_path.decode() == expected_url


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "query",
    [
        "10.0.0.0/../x",
        "10.0.0.0/\u00b2",
        "10.0.0.0/\u0662\u0664",
        "10.0.0.0/999",
        "10.0.0.0/",
        "10.0.0.0/64",
    ],
)
async def test_arp_search_rejects_bad_cidr_prefix(server, query):
    mcp, requests, _ = server
    async with Client(mcp) as client:
        result = await client.call_tool("arp_search", {"query": query})
    assert "Invalid CIDR notation" in str(result.data)
    assert requests == []


@pytest.mark.asyncio
async def test_log_tools_count_the_logs_list(server):
    mcp, requests, set_handler = server
    set_handler(
        lambda _r: httpx2.Response(
            200,
            json={"status": "ok", "a_other": [1, 2, 3], "logs": [{"id": 1}]},
        )
    )
    async with Client(mcp) as client:
        result = await client.call_tool(
            "logs_syslog", {"hostname": "core1", "limit": 5, "sortorder": "DESC"}
        )
    assert result.data["count"] == 1
    assert dict(requests[-1].url.params) == {
        "start": "0",
        "limit": "5",
        "sortorder": "DESC",
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("tool", ["logs_eventlog", "logs_syslog", "logs_alertlog"])
@pytest.mark.parametrize("args", [{}, {"hostname": ""}])
async def test_log_tools_without_hostname_list_all_devices(server, tool, args):
    """The hostname segment is optional in LibreNMS and means all devices."""
    mcp, requests, _ = server
    async with Client(mcp) as client:
        await client.call_tool(tool, args)
    log_type = tool.removeprefix("logs_")
    assert requests[0].url.path == f"/api/v0/logs/{log_type}"


@pytest.mark.asyncio
async def test_arp_search_rejects_device_without_all(server):
    """Dropping the filter would pass off every device's entries as one's."""
    mcp, requests, _ = server
    async with Client(mcp) as client:
        result = await client.call_tool(
            "arp_search", {"query": "10.0.0.5", "device": "core-sw1"}
        )
    assert "only be used with query" in str(result.data)
    assert requests == []


def _fallback_handler(failure: httpx2.Response, ifname: str):
    """Fail the per-port graph, list one port, and render the port-group graph."""

    def handler(request: httpx2.Request) -> httpx2.Response:
        path = request.url.path
        if "/ports/" in path:
            return failure
        if path.endswith("/ports"):
            return httpx2.Response(
                200, json={"status": "ok", "ports": [{"port_id": 9, "ifName": ifname}]}
            )
        return httpx2.Response(
            200, content=SVG, headers={"content-type": "image/svg+xml"}
        )

    return handler


@pytest.mark.asyncio
@pytest.mark.parametrize("graph_type", ["Bits", " bits "])
async def test_port_graph_fallback_ignores_graph_type_case(server, graph_type):
    mcp, requests, set_handler = server
    set_handler(
        _fallback_handler(
            httpx2.Response(500, json={"message": "Graph type '' invalid"}), "Po1"
        )
    )
    async with Client(mcp) as client:
        await client.call_tool(
            "port_graph", {"hostname": "sw1", "ifname": "Po1", "graph_type": graph_type}
        )
    assert requests[-1].url.path == "/api/v0/portgroups/multiport/bits/9"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("graph_type", "expected"),
    [
        ("bits", "port_bits"),
        (" Errors ", "port_errors"),
        ("upkts", "port_upkts"),
        ("port_nupkts", "port_nupkts"),
    ],
)
async def test_port_graph_sends_librenms_graph_names(server, graph_type, expected):
    """LibreNMS answers a bare 'bits' with a 500; it wants 'port_bits'."""
    mcp, requests, set_handler = server
    set_handler(
        lambda _r: httpx2.Response(
            200, content=SVG, headers={"content-type": "image/svg+xml"}
        )
    )
    async with Client(mcp) as client:
        await client.call_tool(
            "port_graph",
            {"hostname": "sw1", "ifname": "Te2/7", "graph_type": graph_type},
        )
    assert [r.url.raw_path.decode().split("?")[0] for r in requests] == [
        f"/api/v0/devices/sw1/ports/Te2%2F7/{expected}"
    ]


@pytest.mark.asyncio
async def test_port_graph_reports_both_errors_when_fallback_fails(server):
    """The first failure (a wrong URL, an SSO proxy) must not be hidden."""
    mcp, _, set_handler = server
    set_handler(lambda _r: httpx2.Response(404, text="<html>Wrong path</html>"))
    async with Client(mcp) as client:
        with pytest.raises(ToolError) as exc:
            await client.call_tool("port_graph", {"hostname": "sw1", "ifname": "Po1"})
    message = str(exc.value)
    assert "HTTP 404 for GET devices/sw1/ports/Po1/port_bits" in message
    assert "lookup by port ID also failed" in message


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "by_name",
    [
        # Apache rejecting the encoded slash.
        httpx2.Response(404, text="<html>Not Found</html>"),
        # LibreNMS after a proxy decoded %2F into an extra segment.
        httpx2.Response(500, json={"message": "Server Error"}),
    ],
)
async def test_device_ports_get_falls_back_to_port_id(server, by_name):
    mcp, requests, set_handler = server

    def handler(request: httpx2.Request) -> httpx2.Response:
        path = request.url.path
        if path.startswith("/api/v0/devices/sw1/ports/"):
            return by_name
        if path == "/api/v0/devices/sw1/ports":
            return httpx2.Response(
                200,
                json={"status": "ok", "ports": [{"port_id": 9, "ifName": "Te2/7"}]},
            )
        return httpx2.Response(
            200, json={"status": "ok", "port": [{"port_id": 9, "ifName": "Te2/7"}]}
        )

    set_handler(handler)
    async with Client(mcp) as client:
        result = await client.call_tool(
            "device_ports_get", {"hostname": "sw1", "ifname": "Te2/7"}
        )
    assert requests[-1].url.path == "/api/v0/ports/9"
    # Same shape as the by-name route: one port object, not a list.
    assert result.data["port"] == {"port_id": 9, "ifName": "Te2/7"}


@pytest.mark.asyncio
async def test_device_ports_get_keeps_librenms_answers_for_plain_names(server):
    mcp, requests, set_handler = server
    set_handler(
        lambda _r: httpx2.Response(
            404, json={"status": "error", "message": "Device sw9 not found"}
        )
    )
    async with Client(mcp) as client:
        result = await client.call_tool(
            "device_ports_get", {"hostname": "sw9", "ifname": "Po1"}
        )
    assert result.data["message"] == "Device sw9 not found"
    assert len(requests) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("query", ["2001:db8::/64", "2001:db8::1", "fe80::1"])
async def test_arp_search_rejects_ipv6(server, query):
    """LibreNMS ARP data is IPv4-only; an empty list would read as no neighbours."""
    mcp, requests, _ = server
    async with Client(mcp) as client:
        result = await client.call_tool("arp_search", {"query": query})
    assert "IPv4-only" in str(result.data)
    assert requests == []


@pytest.mark.asyncio
async def test_port_graph_falls_back_on_gateway_json_404(server):
    """A gateway's JSON 404 is not a LibreNMS answer, so it is retried."""
    mcp, requests, set_handler = server
    set_handler(
        _fallback_handler(
            httpx2.Response(404, json={"message": "no Route matched"}), "Po1"
        )
    )
    async with Client(mcp) as client:
        await client.call_tool("port_graph", {"hostname": "sw1", "ifname": "Po1"})
    assert requests[-1].url.path == "/api/v0/portgroups/multiport/bits/9"


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [401, 403])
async def test_device_ports_get_never_retries_auth_errors(server, status):
    """An expired token on 'Te2/7' must cost one request, not three."""
    mcp, requests, set_handler = server
    set_handler(
        lambda _r: httpx2.Response(status, json={"message": "Unauthenticated."})
    )
    async with Client(mcp) as client:
        result = await client.call_tool(
            "device_ports_get", {"hostname": "sw1", "ifname": "Te2/7"}
        )
    assert result.data == {"status": "error", "message": "Unauthenticated."}
    assert len(requests) == 1


@pytest.mark.asyncio
async def test_device_ports_get_reports_both_errors_when_fallback_fails(server):
    mcp, _, set_handler = server
    set_handler(lambda _r: httpx2.Response(404, text="<html>Wrong path</html>"))
    async with Client(mcp) as client:
        result = await client.call_tool(
            "device_ports_get", {"hostname": "sw1", "ifname": "Po1"}
        )
    error = result.data["error"]
    assert "HTTP 404 for GET devices/sw1/ports/Po1:" in error
    assert "lookup by port ID also failed" in error


@pytest.mark.asyncio
async def test_device_ports_get_reports_by_id_errors_instead_of_success(server):
    """A 403 from ports/{id} must not come back as if the fallback worked."""
    mcp, _, set_handler = server

    def handler(request: httpx2.Request) -> httpx2.Response:
        path = request.url.path
        if path.startswith("/api/v0/devices/sw1/ports/"):
            return httpx2.Response(404, text="<html>Not Found</html>")
        if path == "/api/v0/devices/sw1/ports":
            return httpx2.Response(
                200,
                json={"status": "ok", "ports": [{"port_id": 9, "ifName": "Te2/7"}]},
            )
        return httpx2.Response(403, json={"message": "Forbidden"})

    set_handler(handler)
    async with Client(mcp) as client:
        result = await client.call_tool(
            "device_ports_get", {"hostname": "sw1", "ifname": "Te2/7"}
        )
    error = result.data["error"]
    assert "AllowEncodedSlashes" in error
    assert "lookup by port ID also failed" in error
    assert "HTTP 403 for GET ports/9: Forbidden" in error


@pytest.mark.asyncio
@pytest.mark.parametrize("graph_type", ["", "   ", "port_"])
async def test_port_graph_rejects_blank_graph_type(server, graph_type):
    mcp, requests, _ = server
    async with Client(mcp) as client:
        with pytest.raises(ToolError, match="graph_type is required"):
            await client.call_tool(
                "port_graph",
                {"hostname": "sw1", "ifname": "Po1", "graph_type": graph_type},
            )
    assert requests == []


@pytest.mark.asyncio
async def test_arp_search_treats_blank_device_as_unset(server):
    mcp, requests, _ = server
    async with Client(mcp) as client:
        await client.call_tool("arp_search", {"query": "10.0.0.1", "device": "  "})
        await client.call_tool("arp_search", {"query": "all", "device": " sw1 "})
    assert [r.url.raw_path.decode() for r in requests] == [
        "/api/v0/resources/ip/arp/10.0.0.1",
        "/api/v0/devices/sw1",
        "/api/v0/resources/ip/arp/all?device=sw1",
    ]


@pytest.mark.asyncio
async def test_device_ports_get_falls_back_on_proxy_400(server):
    mcp, requests, set_handler = server

    def handler(request: httpx2.Request) -> httpx2.Response:
        path = request.url.path
        if path.startswith("/api/v0/devices/sw1/ports/"):
            return httpx2.Response(400, text="Bad Request")
        if path == "/api/v0/devices/sw1/ports":
            return httpx2.Response(
                200,
                json={"status": "ok", "ports": [{"port_id": 9, "ifName": "Te2/7"}]},
            )
        return httpx2.Response(
            200, json={"status": "ok", "port": [{"port_id": 9, "ifName": "Te2/7"}]}
        )

    set_handler(handler)
    async with Client(mcp) as client:
        result = await client.call_tool(
            "device_ports_get", {"hostname": "sw1", "ifname": "Te2/7"}
        )
    assert requests[-1].url.path == "/api/v0/ports/9"
    assert result.data["port"]["port_id"] == 9


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("search", "expected"),
    [
        ("Te2/7", "/api/v0/ports/search/ifAlias%2CifDescr%2CifName/Te2%2F7"),
        ("mgmt0", "/api/v0/ports/search/mgmt0"),
        # LibreNMS treats a search of "0" as empty; keep the one-part form.
        ("0", "/api/v0/ports/search/0"),
    ],
)
async def test_ports_search_names_fields_only_for_slashes(server, search, expected):
    """LibreNMS decodes %2F; a lone 'Te2/7' would be read as field 'Te2'."""
    mcp, requests, _ = server
    async with Client(mcp) as client:
        await client.call_tool("ports_search", {"search": search})
    assert [r.url.raw_path.decode() for r in requests] == [expected]


@pytest.mark.asyncio
@pytest.mark.parametrize("tool", ["logs_eventlog", "logs_syslog", "logs_alertlog"])
async def test_log_tools_reject_unknown_hostnames(server, tool):
    """LibreNMS answers an unknown hostname with every device's logs."""
    mcp, requests, set_handler = server
    set_handler(
        lambda _r: httpx2.Response(
            404,
            json={
                "status": "error",
                "message": "Device core-sw1.invalid does not exist",
            },
        )
    )
    async with Client(mcp) as client:
        result = await client.call_tool(tool, {"hostname": "core-sw1.invalid"})
    assert result.data["message"] == "Device core-sw1.invalid does not exist"
    assert [r.url.path for r in requests] == ["/api/v0/devices/core-sw1.invalid"]


@pytest.mark.asyncio
async def test_log_tools_check_the_device_then_fetch_its_logs(server):
    mcp, requests, _ = server
    async with Client(mcp) as client:
        await client.call_tool("logs_eventlog", {"hostname": "core1"})
    assert [r.url.path for r in requests] == [
        "/api/v0/devices/core1",
        "/api/v0/logs/eventlog/core1",
    ]


@pytest.mark.asyncio
async def test_arp_search_rejects_unknown_devices(server):
    """An unknown device must not read as 'no ARP neighbours'."""
    mcp, requests, set_handler = server
    set_handler(
        lambda _r: httpx2.Response(
            404, json={"status": "error", "message": "Device typo-sw1 does not exist"}
        )
    )
    async with Client(mcp) as client:
        result = await client.call_tool(
            "arp_search", {"query": "all", "device": "typo-sw1"}
        )
    assert result.data["message"] == "Device typo-sw1 does not exist"
    assert [r.url.path for r in requests] == ["/api/v0/devices/typo-sw1"]
