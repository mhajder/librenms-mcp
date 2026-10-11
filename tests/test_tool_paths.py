"""End-to-end checks of the URLs the tools send to LibreNMS.

Tool arguments come from the model and may be prompt-injected, so a value must
never be able to steer a request to a different endpoint.
"""

import json
from urllib.parse import unquote

import httpx2
import pytest
from fastmcp import Client
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from librenms_mcp.librenms_client import LibreNMSClient
from librenms_mcp.models import LibreNMSConfig
from librenms_mcp.tools import register_tools

SVG = b"<svg xmlns='http://www.w3.org/2000/svg'/>"


def _librenms_default(request: httpx2.Request) -> httpx2.Response:
    """Answer like a LibreNMS with every device: a device record for lookups."""
    parts = request.url.path.split("/")
    if request.method == "GET" and len(parts) == 5 and parts[3] == "devices":
        name = unquote(parts[4])
        return httpx2.Response(
            200, json={"status": "ok", "devices": [{"device_id": 1, "hostname": name}]}
        )
    return httpx2.Response(200, json={"status": "ok"})


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
    state = {"handler": _librenms_default}

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
        ("oxidized_config_get", {"hostname": "a/b"}, "/api/v0/oxidized/config/a%2Fb"),
        (
            "ports_search_field",
            {"field": "ifAlias", "search": "uplink to core/1"},
            "/api/v0/ports/search/ifAlias/uplink%20to%20core%2F1",
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
        ("oxidized_config_get", {"hostname": "../../devices"}),
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
    # The ARP request comes first; a given device is only checked after it.
    assert requests[0].url.raw_path.decode() == expected_url


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

    def handler(request: httpx2.Request) -> httpx2.Response:
        if request.url.path.startswith("/api/v0/devices/"):
            return _librenms_default(request)
        return httpx2.Response(
            200, json={"status": "ok", "a_other": [1, 2, 3], "logs": [{"id": 1}]}
        )

    set_handler(handler)
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
@pytest.mark.parametrize(
    ("query", "expected_url"),
    [
        (None, "/api/v0/ports"),
        ({"columns": "port_id"}, "/api/v0/ports?columns=port_id"),
        ({"device_id": ""}, "/api/v0/ports"),
        # LibreNMS's ports endpoint ignores device_id, so the filter is routed.
        ({"device_id": 1}, "/api/v0/devices/1/ports?columns=port_id%2CifName"),
        (
            {"device_id": "sw1", "columns": "port_id,ifName"},
            "/api/v0/devices/sw1/ports?columns=port_id%2CifName",
        ),
    ],
)
async def test_ports_list_routes_device_filter(server, query, expected_url):
    mcp, requests, _ = server
    async with Client(mcp) as client:
        await client.call_tool("ports_list", {"query": query})
    assert requests[0].url.raw_path.decode() == expected_url


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


@pytest.mark.asyncio
@pytest.mark.parametrize("args", [{"query": "all"}, {"query": " ALL ", "device": "  "}])
async def test_arp_search_rejects_all_without_device(server, args):
    """LibreNMS answers "all" without a device with an empty list."""
    mcp, requests, _ = server
    async with Client(mcp) as client:
        result = await client.call_tool("arp_search", args)
    assert result.data == {
        "status": "error",
        "message": 'Query "all" requires the device parameter',
    }
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
    error = result.data["message"]
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
    error = result.data["message"]
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
    # device is a query parameter, which LibreNMS trims; the device check (made
    # because the default answer has no entries) must
    # use the same trimmed value or it would reject what the filter accepts.
    assert [r.url.raw_path.decode() for r in requests] == [
        "/api/v0/resources/ip/arp/10.0.0.1",
        "/api/v0/resources/ip/arp/all?device=sw1",
        "/api/v0/devices/sw1",
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
    set_handler(_unknown_device_without_data("arp"))
    async with Client(mcp) as client:
        result = await client.call_tool(
            "arp_search", {"query": "all", "device": "typo"}
        )
    assert result.data["message"] == "Device typo does not exist"
    assert [r.url.path for r in requests] == [
        "/api/v0/resources/ip/arp/all",
        "/api/v0/devices/typo",
    ]


@pytest.mark.asyncio
async def test_bgp_sessions_rejects_unknown_devices(server):
    """LibreNMS drops an unresolvable hostname filter and lists every session."""
    mcp, requests, set_handler = server
    set_handler(
        lambda _r: httpx2.Response(
            404, json={"status": "error", "message": "Device typo-rtr1 does not exist"}
        )
    )
    async with Client(mcp) as client:
        result = await client.call_tool("bgp_sessions", {"hostname": "typo-rtr1"})
    assert result.data["message"] == "Device typo-rtr1 does not exist"
    assert [r.url.path for r in requests] == ["/api/v0/devices/typo-rtr1"]


@pytest.mark.asyncio
async def test_bgp_sessions_checks_the_device_then_filters(server):
    mcp, requests, _ = server
    async with Client(mcp) as client:
        await client.call_tool("bgp_sessions", {"hostname": "core1"})
    assert [r.url.raw_path.decode() for r in requests] == [
        "/api/v0/devices/core1",
        "/api/v0/bgp?hostname=core1",
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("args", [{}, {"hostname": "  "}])
async def test_bgp_sessions_without_hostname_lists_everything(server, args):
    mcp, requests, _ = server
    async with Client(mcp) as client:
        await client.call_tool("bgp_sessions", args)
    assert [r.url.raw_path.decode() for r in requests] == ["/api/v0/bgp"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("search", "hint"),
    [
        ("10.0.0.0/24", "e.g. '10.0.0.0'"),
        ("/24", "e.g. '24'"),
        ("/", None),
    ],
)
async def test_oxidized_search_explains_slashes_instead_of_failing(
    server, search, hint
):
    """LibreNMS's search route cannot take '/'; it splits into extra segments."""
    mcp, requests, _ = server
    async with Client(mcp) as client:
        result = await client.call_tool("oxidized_config_search", {"search": search})
    assert result.data["status"] == "error"
    error = result.data["message"]
    assert "cannot search Oxidized configs" in error
    if hint:
        assert hint in error
    else:
        assert "e.g." not in error
    assert requests == []


@pytest.mark.asyncio
async def test_oxidized_search_without_slash_is_sent(server):
    mcp, requests, _ = server
    async with Client(mcp) as client:
        await client.call_tool("oxidized_config_search", {"search": "ip route 0.0.0.0"})
    assert [r.url.raw_path.decode() for r in requests] == [
        "/api/v0/oxidized/config/search/ip%20route%200.0.0.0"
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("tool", "args", "expected"),
    [
        ("logs_eventlog", {"hostname": "   "}, ["/api/v0/logs/eventlog"]),
        ("bgp_sessions", {"hostname": "   "}, ["/api/v0/bgp"]),
    ],
)
async def test_blank_filters_mean_no_filter(server, tool, args, expected):
    """One rule for every optional filter: blank is unset, no device check."""
    mcp, requests, _ = server
    async with Client(mcp) as client:
        await client.call_tool(tool, args)
    assert [r.url.raw_path.decode().split("?")[0] for r in requests] == expected


@pytest.mark.asyncio
async def test_bgp_sessions_trims_the_hostname_like_librenms(server):
    """?hostname= ' core1 ' filters on 'core1' in LibreNMS; check that device."""
    mcp, requests, _ = server
    async with Client(mcp) as client:
        await client.call_tool("bgp_sessions", {"hostname": " core1 "})
    assert [r.url.raw_path.decode() for r in requests] == [
        "/api/v0/devices/core1",
        "/api/v0/bgp?hostname=core1",
    ]


@pytest.mark.asyncio
async def test_device_check_reports_non_librenms_answers(server):
    """A gateway answering 200 with a list must not fail on .get()."""
    mcp, requests, set_handler = server
    set_handler(lambda _r: httpx2.Response(200, json=["not", "a", "device"]))
    async with Client(mcp) as client:
        result = await client.call_tool("bgp_sessions", {"hostname": "core1"})
    assert result.data["status"] == "error"
    assert (
        "Unexpected response when looking up device 'core1'" in result.data["message"]
    )
    assert len(requests) == 1


@pytest.mark.asyncio
async def test_services_are_paginated_individually(server):
    """LibreNMS nests services one level deep: {"services": [[...]]}."""
    mcp, _, set_handler = server
    services = [{"service_id": i} for i in range(1, 6)]
    set_handler(
        lambda _r: httpx2.Response(200, json={"status": "ok", "services": [services]})
    )
    async with Client(mcp) as client:
        result = await client.call_tool("services_list", {"limit": 2, "offset": 1})
    assert result.data["services"] == [{"service_id": 2}, {"service_id": 3}]
    assert (result.data["count"], result.data["total"]) == (2, 5)


@pytest.mark.asyncio
async def test_device_check_fails_closed_on_non_librenms_answers(server):
    """An SSO proxy's 200 {"message": ...} must not count as 'device exists'."""
    mcp, requests, set_handler = server
    set_handler(lambda _r: httpx2.Response(200, json={"message": "login required"}))
    async with Client(mcp) as client:
        result = await client.call_tool("logs_eventlog", {"hostname": "core1"})
    assert result.data["status"] == "error"
    assert (
        "Unexpected response when looking up device 'core1'" in result.data["message"]
    )
    assert [r.url.path for r in requests] == ["/api/v0/devices/core1"]


@pytest.mark.asyncio
async def test_oxidized_list_rejects_unknown_devices(server):
    """LibreNMS answers an unknown hostname with [], i.e. 'not backed up'."""
    mcp, requests, set_handler = server

    def handler(request: httpx2.Request) -> httpx2.Response:
        if request.url.path == "/api/v0/devices/typo":
            return _unknown_device(request)
        return httpx2.Response(200, json=[])

    set_handler(handler)
    async with Client(mcp) as client:
        result = await client.call_tool("oxidized_list", {"hostname": "typo"})
    assert result.data["message"] == "Device typo does not exist"
    assert [r.url.path for r in requests] == [
        "/api/v0/oxidized/typo",
        "/api/v0/devices/typo",
    ]


@pytest.mark.asyncio
async def test_oxidized_list_with_entries_needs_no_device_lookup(server):
    """A device the endpoint returns exists; a failing lookup must not matter."""
    mcp, requests, set_handler = server

    def handler(request: httpx2.Request) -> httpx2.Response:
        if request.url.path.startswith("/api/v0/devices/"):
            return httpx2.Response(200, json={"message": "login required"})
        return httpx2.Response(200, json=[{"hostname": "core1", "os": "nxos"}])

    set_handler(handler)
    async with Client(mcp) as client:
        result = await client.call_tool("oxidized_list", {"hostname": "core1"})
        await client.call_tool("oxidized_list", {})
    assert result.data["devices"] == [{"hostname": "core1", "os": "nxos"}]
    assert [r.url.path for r in requests] == [
        "/api/v0/oxidized/core1",
        "/api/v0/oxidized",
    ]


@pytest.mark.asyncio
async def test_oxidized_list_keeps_an_empty_answer_for_a_known_device(server):
    """A disabled or ignored device exists but is not backed up."""
    mcp, requests, set_handler = server

    def handler(request: httpx2.Request) -> httpx2.Response:
        if request.url.path.startswith("/api/v0/devices/"):
            return _librenms_default(request)
        return httpx2.Response(200, json=[])

    set_handler(handler)
    async with Client(mcp) as client:
        result = await client.call_tool("oxidized_list", {"hostname": "core1"})
    assert result.data["devices"] == []
    assert [r.url.path for r in requests] == [
        "/api/v0/oxidized/core1",
        "/api/v0/devices/core1",
    ]


@pytest.mark.asyncio
async def test_oxidized_list_translates_a_device_id_to_its_hostname(server):
    """Oxidized filters on hostname; an ID would otherwise give an empty list."""
    mcp, requests, set_handler = server

    def handler(request: httpx2.Request) -> httpx2.Response:
        if request.url.path == "/api/v0/devices/1":
            return httpx2.Response(
                200,
                json={
                    "status": "ok",
                    "devices": [{"device_id": 1, "hostname": "core1"}],
                },
            )
        if request.url.path == "/api/v0/oxidized/1":
            return httpx2.Response(200, json=[])
        return httpx2.Response(200, json=[{"hostname": "core1", "os": "nxos"}])

    set_handler(handler)
    async with Client(mcp) as client:
        result = await client.call_tool("oxidized_list", {"hostname": "1"})
    assert [r.url.path for r in requests] == [
        "/api/v0/oxidized/1",
        "/api/v0/devices/1",
        "/api/v0/oxidized/core1",
    ]
    assert result.data["devices"] == [{"hostname": "core1", "os": "nxos"}]


@pytest.mark.asyncio
async def test_inventory_flat_rejects_unknown_devices(server):
    """inventory/{host}/all answers an unknown device with an empty list."""
    mcp, requests, set_handler = server
    set_handler(_unknown_device_without_data("inventory"))
    async with Client(mcp) as client:
        result = await client.call_tool("inventory_device_flat", {"hostname": "typo"})
    assert result.data["message"] == "Device typo does not exist"
    assert [r.url.path for r in requests] == [
        "/api/v0/inventory/typo/all",
        "/api/v0/devices/typo",
    ]


@pytest.mark.asyncio
async def test_oxidized_slash_hint_is_trimmed(server):
    mcp, _, _ = server
    async with Client(mcp) as client:
        result = await client.call_tool(
            "oxidized_config_search", {"search": " 10.0.0.0 /24"}
        )
    assert "e.g. '10.0.0.0'" in result.data["message"]


@pytest.mark.asyncio
async def test_inventory_rejects_unknown_devices(server):
    """inventory/{host} answers an unknown device with an empty list too."""
    mcp, requests, set_handler = server
    set_handler(_unknown_device_without_data("inventory"))
    async with Client(mcp) as client:
        result = await client.call_tool("inventory_device", {"hostname": "typo"})
    assert result.data["message"] == "Device typo does not exist"
    assert [r.url.path for r in requests] == [
        "/api/v0/inventory/typo",
        "/api/v0/devices/typo",
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("tool", "args"),
    [
        ("bill_graph", {"bill_id": 1, "graph_type": "day"}),
        ("bill_graph_data", {"bill_id": 1, "graph_type": "hour"}),
        (
            "bill_history_graph",
            {"bill_id": 1, "history_id": 2, "graph_type": "monthly"},
        ),
        (
            "bill_history_graph_data",
            {"bill_id": 1, "history_id": 2, "graph_type": "monthly"},
        ),
    ],
)
async def test_bill_graph_types_are_limited_to_what_librenms_supports(
    server, tool, args
):
    """Current periods take bits/monthly, history bits/day/hour; others fail."""
    mcp, requests, _ = server
    async with Client(mcp) as client:
        with pytest.raises(ToolError, match="graph_type"):
            await client.call_tool(tool, args)
    assert requests == []


@pytest.mark.asyncio
async def test_device_ports_get_reports_a_missing_port(server):
    """LibreNMS answers a missing port with status ok and an empty record."""
    mcp, requests, set_handler = server

    def handler(request: httpx2.Request) -> httpx2.Response:
        if request.url.path == "/api/v0/devices/sw1":
            return httpx2.Response(
                200, json={"status": "ok", "devices": [{"device_id": 1}]}
            )
        return httpx2.Response(200, json={"status": "ok", "port": {"in_rate": "0 bps"}})

    set_handler(handler)
    async with Client(mcp) as client:
        result = await client.call_tool(
            "device_ports_get", {"hostname": "sw1", "ifname": "Po99"}
        )
    assert result.data == {
        "status": "error",
        "message": "No port named 'Po99' on device 'sw1'",
    }
    assert [r.url.path for r in requests] == [
        "/api/v0/devices/sw1/ports/Po99",
        "/api/v0/devices/sw1",
    ]


@pytest.mark.asyncio
async def test_device_ports_get_reports_a_missing_device(server):
    mcp, _, set_handler = server

    def handler(request: httpx2.Request) -> httpx2.Response:
        if request.url.path == "/api/v0/devices/typo":
            return httpx2.Response(
                404, json={"status": "error", "message": "Device typo does not exist"}
            )
        return httpx2.Response(200, json={"status": "ok", "port": {"in_rate": "0 bps"}})

    set_handler(handler)
    async with Client(mcp) as client:
        result = await client.call_tool(
            "device_ports_get", {"hostname": "typo", "ifname": "Po1"}
        )
    assert result.data["message"] == "Device typo does not exist"


@pytest.mark.asyncio
async def test_device_ports_get_found_port_costs_one_request(server):
    mcp, requests, set_handler = server
    set_handler(
        lambda _r: httpx2.Response(
            200, json={"status": "ok", "port": {"port_id": 7, "ifName": "Po1"}}
        )
    )
    async with Client(mcp) as client:
        result = await client.call_tool(
            "device_ports_get", {"hostname": "sw1", "ifname": "Po1"}
        )
    assert result.data["port"]["port_id"] == 7
    assert len(requests) == 1


def _unknown_device(_request: httpx2.Request) -> httpx2.Response:
    return httpx2.Response(
        404, json={"status": "error", "message": "Device typo does not exist"}
    )


def _unknown_device_without_data(key: str):
    """Answer like LibreNMS for device 'typo', which does not exist.

    The device lookup fails; data endpoints answer with an empty list under
    key, as LibreNMS does for a device it cannot resolve.
    """

    def handler(request: httpx2.Request) -> httpx2.Response:
        if request.url.path == "/api/v0/devices/typo":
            return _unknown_device(request)
        return httpx2.Response(200, json={"status": "ok", key: []})

    return handler


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("tool", "args", "key", "path"),
    [
        (
            "device_availability",
            {},
            "availability",
            "/api/v0/devices/typo/availability",
        ),
        ("device_outages", {}, "outages", "/api/v0/devices/typo/outages"),
        ("device_ports", {}, "ports", "/api/v0/devices/typo/ports"),
        ("health_list", {}, "graphs", "/api/v0/devices/typo/health"),
        (
            "health_by_type",
            {"type": "device_state"},
            "graphs",
            "/api/v0/devices/typo/health/device_state",
        ),
        (
            "health_sensor_get",
            {"type": "device_state", "sensor_id": 1},
            "graphs",
            "/api/v0/devices/typo/health/device_state/1",
        ),
        ("port_security_device", {}, "port", "/api/v0/port_security/device/typo"),
        ("services_for_device", {}, "services", "/api/v0/services/typo"),
    ],
)
async def test_device_scoped_tools_reject_unknown_devices(
    server, tool, args, key, path
):
    """Each answers an unknown device with no data; only then is it looked up."""
    mcp, requests, set_handler = server
    set_handler(_unknown_device_without_data(key))
    async with Client(mcp) as client:
        result = await client.call_tool(tool, {"hostname": "typo", **args})
    assert result.data["message"] == "Device typo does not exist"
    assert [r.url.path for r in requests] == [path, "/api/v0/devices/typo"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("tool", "args", "key"),
    [
        ("device_outages", {}, "outages"),
        ("device_ports", {}, "ports"),
        ("health_list", {}, "graphs"),
        ("inventory_device", {}, "inventory"),
        ("port_security_device", {}, "port"),
        ("services_for_device", {}, "services"),
    ],
)
async def test_device_scoped_tools_with_data_cost_one_request(server, tool, args, key):
    """Data proves the device exists, so there is no separate lookup."""
    mcp, requests, set_handler = server
    set_handler(
        lambda _r: httpx2.Response(200, json={"status": "ok", key: [{"id": 1}]})
    )
    async with Client(mcp) as client:
        result = await client.call_tool(tool, {"hostname": "sw1", **args})
    assert result.data.get("status") != "error"
    assert len(requests) == 1


# devices/{hostname}/graphs lists these for any device ID, even an unknown one.
_ALWAYS_LISTED = [
    {"desc": "Poller Time", "name": "device_poller_perf"},
    {"desc": "Ping Response", "name": "device_icmp_perf"},
]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "always_listed",
    [
        _ALWAYS_LISTED,
        # Releases before 25.1 name the ping graph device_ping_perf.
        [
            {"desc": "Poller Time", "name": "device_poller_perf"},
            {"desc": "Ping Response", "name": "device_ping_perf"},
        ],
    ],
)
async def test_device_graphs_list_rejects_unknown_devices(server, always_listed):
    """The two graphs LibreNMS always lists must not pass for a real device."""
    mcp, requests, set_handler = server

    def handler(request: httpx2.Request) -> httpx2.Response:
        if request.url.path == "/api/v0/devices/typo":
            return _unknown_device(request)
        return httpx2.Response(200, json={"status": "ok", "graphs": always_listed})

    set_handler(handler)
    async with Client(mcp) as client:
        result = await client.call_tool("device_graphs_list", {"hostname": "typo"})
    assert result.data["message"] == "Device typo does not exist"
    assert [r.url.path for r in requests] == [
        "/api/v0/devices/typo/graphs",
        "/api/v0/devices/typo",
    ]


@pytest.mark.asyncio
async def test_device_graphs_list_with_device_graphs_costs_one_request(server):
    mcp, requests, set_handler = server
    graphs = [*_ALWAYS_LISTED, {"desc": "System Uptime", "name": "device_uptime"}]
    set_handler(
        lambda _r: httpx2.Response(200, json={"status": "ok", "graphs": graphs})
    )
    async with Client(mcp) as client:
        result = await client.call_tool("device_graphs_list", {"hostname": "sw1"})
    assert result.data["graphs"] == graphs
    assert len(requests) == 1


@pytest.mark.asyncio
async def test_device_links_checks_the_device_first(server):
    """device_links drops the filter and lists every device's links."""
    mcp, requests, set_handler = server
    set_handler(_unknown_device)
    async with Client(mcp) as client:
        result = await client.call_tool("device_links", {"hostname": "typo"})
    assert result.data["message"] == "Device typo does not exist"
    assert [r.url.path for r in requests] == ["/api/v0/devices/typo"]


@pytest.mark.asyncio
async def test_service_add_defaults_ip_to_the_device_hostname(server):
    """LibreNMS 500s without "ip"; for an empty one it stores the poller target."""
    mcp, requests, _ = server
    async with Client(mcp) as client:
        await client.call_tool(
            "service_add", {"hostname": "1", "payload": {"type": "icmp"}}
        )
        await client.call_tool(
            "service_add",
            {"hostname": "1", "payload": {"type": "icmp", "ip": "192.0.2.9"}},
        )
    posts = [json.loads(r.content) for r in requests if r.method == "POST"]
    assert posts == [{"type": "icmp", "ip": ""}, {"type": "icmp", "ip": "192.0.2.9"}]
    # The device is confirmed before every add: add_service_for_host does not
    # check it, explicit ip or not.
    assert [r.method for r in requests] == ["GET", "POST", "GET", "POST"]


@pytest.mark.asyncio
async def test_service_add_rejects_unknown_devices(server):
    """add_service_for_host does not check the device exists."""
    mcp, requests, set_handler = server
    set_handler(_unknown_device)
    async with Client(mcp) as client:
        result = await client.call_tool(
            "service_add", {"hostname": "typo", "payload": {"type": "icmp"}}
        )
    assert result.data["message"] == "Device typo does not exist"
    assert [r.method for r in requests] == ["GET"]


@pytest.mark.asyncio
async def test_alert_get_by_id_looks_in_every_state(server):
    """alerts/{id} only searches active alerts unless a state is given."""
    mcp, requests, _ = server
    async with Client(mcp) as client:
        await client.call_tool("alert_get_by_id", {"alert_id": 42})
    assert requests[0].url.path == "/api/v0/alerts/42"
    states = requests[0].url.params["state"].split(",")
    # Every state LibreNMS defines today, plus room for ones it adds later.
    assert {"0", "1", "2", "3", "4", "5"} < set(states)


@pytest.mark.asyncio
async def test_bill_get_with_a_period_keeps_an_empty_answer(server):
    """With a period LibreNMS joins the history; empty means no data, not no bill."""
    mcp, requests, set_handler = server
    body = {"status": "ok", "bills": [], "count": 0}

    def handler(request: httpx2.Request) -> httpx2.Response:
        if request.url.params.get("period"):
            return httpx2.Response(200, json=body)
        return httpx2.Response(
            200, json={"status": "ok", "bills": [{"bill_id": 7}], "count": 1}
        )

    set_handler(handler)
    async with Client(mcp) as client:
        result = await client.call_tool(
            "bill_get", {"bill_id": 7, "period": "previous"}
        )
    assert result.data == body
    # The plain lookup confirms the bill exists.
    assert [dict(r.url.params) for r in requests] == [{"period": "previous"}, {}]


@pytest.mark.asyncio
async def test_bill_get_reports_a_failed_existence_check(server):
    """A failed plain lookup proves nothing; it must not pass as 'no data'."""
    mcp, _, set_handler = server
    denied = {"status": "error", "message": "Denied"}

    def handler(request: httpx2.Request) -> httpx2.Response:
        if request.url.params.get("period"):
            return httpx2.Response(200, json={"status": "ok", "bills": []})
        return httpx2.Response(403, json=denied)

    set_handler(handler)
    async with Client(mcp) as client:
        result = await client.call_tool(
            "bill_get", {"bill_id": 7, "period": "previous"}
        )
    assert result.data == denied


@pytest.mark.asyncio
async def test_bill_get_reports_a_missing_bill(server):
    mcp, requests, set_handler = server
    body = {"status": "ok", "bills": [], "count": 0}
    set_handler(lambda _r: httpx2.Response(200, json=body))
    async with Client(mcp) as client:
        with_period = await client.call_tool(
            "bill_get", {"bill_id": 7, "period": "previous"}
        )
        plain = await client.call_tool("bill_get", {"bill_id": 7})
        # LibreNMS acts on "previous" alone; any other period is a plain lookup.
        other_period = await client.call_tool(
            "bill_get", {"bill_id": 7, "period": "current"}
        )
    not_found = {"status": "error", "message": "Bill 7 does not exist"}
    assert with_period.data == not_found
    assert plain.data == not_found
    assert other_period.data == not_found
    assert len(requests) == 4


@pytest.mark.asyncio
async def test_health_sensor_get_reports_a_missing_sensor(server):
    """With the device confirmed, an empty answer means no such sensor."""
    mcp, requests, set_handler = server

    def handler(request: httpx2.Request) -> httpx2.Response:
        if request.url.path == "/api/v0/devices/core1":
            return _librenms_default(request)
        return httpx2.Response(200, json={"status": "ok", "graphs": []})

    set_handler(handler)
    async with Client(mcp) as client:
        result = await client.call_tool(
            "health_sensor_get",
            {"hostname": "core1", "type": "temperature", "sensor_id": 999},
        )
    assert result.data == {
        "status": "error",
        "message": "Sensor 999 (temperature) does not exist on core1",
    }
    assert len(requests) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("sensor_device_id", "unknown_device"), [(2, False), (1, True)]
)
async def test_health_sensor_get_checks_the_sensor_device(
    server, sensor_device_id, unknown_device
):
    """LibreNMS finds the sensor by ID alone; it must belong to the device."""
    mcp, _, set_handler = server
    sensor = {"sensor_id": 5, "device_id": sensor_device_id}

    def handler(request: httpx2.Request) -> httpx2.Response:
        if request.url.path == "/api/v0/devices/typo":
            return _unknown_device(request)
        if request.url.path == "/api/v0/devices/core1":
            return _librenms_default(request)
        return httpx2.Response(200, json={"status": "ok", "graphs": [sensor]})

    set_handler(handler)
    hostname = "typo" if unknown_device else "core1"
    async with Client(mcp) as client:
        result = await client.call_tool(
            "health_sensor_get",
            {"hostname": hostname, "type": "temperature", "sensor_id": 5},
        )
    if unknown_device:
        assert result.data["message"] == "Device typo does not exist"
    else:
        assert result.data == {
            "status": "error",
            "message": "Sensor 5 (temperature) does not exist on core1",
        }


@pytest.mark.asyncio
async def test_health_sensor_get_returns_the_device_sensor(server):
    mcp, _, set_handler = server
    body = {"status": "ok", "graphs": [{"sensor_id": 5, "device_id": 1}]}

    def handler(request: httpx2.Request) -> httpx2.Response:
        if request.url.path == "/api/v0/devices/core1":
            return _librenms_default(request)
        return httpx2.Response(200, json=body)

    set_handler(handler)
    async with Client(mcp) as client:
        result = await client.call_tool(
            "health_sensor_get",
            {"hostname": "core1", "type": "temperature", "sensor_id": 5},
        )
    assert result.data == body


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("type", "row", "found"),
    [
        # LibreNMS <= 25.1 returns sensor 5 whatever type the path names.
        ("temperature", {"sensor_class": "voltage"}, False),
        ("temperature", {"sensor_class": "temperature"}, True),
        # LibreNMS drops "device_" and compares classes case-insensitively.
        ("device_Temperature", {"sensor_class": "temperature"}, True),
        # Processor, storage and mempool rows carry no sensor_class.
        ("processor", {"processor_id": 5}, True),
    ],
)
async def test_health_sensor_get_checks_the_sensor_type(server, type, row, found):
    mcp, _, set_handler = server
    body = {"status": "ok", "graphs": [{"sensor_id": 5, "device_id": 1, **row}]}

    def handler(request: httpx2.Request) -> httpx2.Response:
        if request.url.path == "/api/v0/devices/core1":
            return _librenms_default(request)
        return httpx2.Response(200, json=body)

    set_handler(handler)
    async with Client(mcp) as client:
        result = await client.call_tool(
            "health_sensor_get",
            {"hostname": "core1", "type": type, "sensor_id": 5},
        )
    if found:
        assert result.data == body
    else:
        assert result.data == {
            "status": "error",
            "message": f"Sensor 5 ({type}) does not exist on core1",
        }


@pytest.mark.asyncio
async def test_all_digit_group_ref_is_sent_when_the_list_is_denied(server):
    """LibreNMS checks permissions per group; listing them all may be denied."""
    mcp, requests, set_handler = server

    def handler(request: httpx2.Request) -> httpx2.Response:
        if request.url.path == "/api/v0/devicegroups":
            return httpx2.Response(403, json={"status": "error", "message": "Denied"})
        return httpx2.Response(200, json={"status": "ok", "devices": []})

    set_handler(handler)
    async with Client(mcp) as client:
        result = await client.call_tool("devicegroup_devices", {"name": "7"})
    assert result.data["status"] == "ok"
    assert [r.url.path for r in requests] == [
        "/api/v0/devicegroups",
        "/api/v0/devicegroups/7",
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("args", "expected"),
    [
        ({}, ["/api/v0/poller_group"]),
        ({"poller_group": "all"}, ["/api/v0/poller_group"]),
        ({"poller_group": " ALL "}, ["/api/v0/poller_group"]),
        # An all-digit reference is checked against the group names first.
        ({"poller_group": "2"}, ["/api/v0/poller_group", "/api/v0/poller_group/2"]),
    ],
)
async def test_poller_group_get_lists_all_without_a_group(server, args, expected):
    """LibreNMS looks up 'all' as a group name; listing needs no segment."""
    mcp, requests, _ = server
    async with Client(mcp) as client:
        await client.call_tool("poller_group_get", args)
    assert [r.url.path for r in requests] == expected


@pytest.mark.asyncio
async def test_poller_group_get_refuses_id_zero(server):
    """LibreNMS reads "0" as no group and would answer with every group."""
    mcp, requests, _ = server
    async with Client(mcp) as client:
        result = await client.call_tool("poller_group_get", {"poller_group": "0"})
    assert result.data["status"] == "error"
    assert "Poller group 0" in result.data["message"]
    # Only the name check ran; poller_group/0 was never requested.
    assert [r.url.path for r in requests] == ["/api/v0/poller_group"]


@pytest.mark.asyncio
async def test_poller_group_named_zero_goes_by_its_id(server):
    mcp, requests, set_handler = server
    set_handler(
        lambda _r: httpx2.Response(
            200,
            json={
                "status": "ok",
                "get_poller_group": [{"id": 5, "group_name": "0"}],
            },
        )
    )
    async with Client(mcp) as client:
        await client.call_tool("poller_group_get", {"poller_group": "0"})
    assert requests[-1].url.path == "/api/v0/poller_group/5"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("tool", "extra", "method", "path"),
    [
        ("location_get", {}, "GET", "/api/v0/location/7"),
        ("location_edit", {"payload": {"lat": 1}}, "PATCH", "/api/v0/locations/7"),
    ],
)
async def test_location_names_with_a_slash_go_by_id(server, tool, extra, method, path):
    """A '/' in the name splits LibreNMS's route; the ID always works."""
    mcp, requests, set_handler = server

    def handler(request: httpx2.Request) -> httpx2.Response:
        if request.url.path == "/api/v0/resources/locations":
            return httpx2.Response(
                200,
                json={
                    "status": "ok",
                    "locations": [{"id": 7, "location": "DC1/Room 2"}],
                },
            )
        return httpx2.Response(200, json={"status": "ok"})

    set_handler(handler)
    async with Client(mcp) as client:
        await client.call_tool(tool, {"location": "DC1/Room 2", **extra})
    assert [(r.method, r.url.path) for r in requests][-1] == (method, path)


def _device_groups(*groups: tuple[int, str]):
    """Answer devicegroups with the given (id, name) groups, else status ok."""

    def handler(request: httpx2.Request) -> httpx2.Response:
        if request.method == "GET" and request.url.path == "/api/v0/devicegroups":
            return httpx2.Response(
                200,
                json={
                    "status": "ok",
                    "groups": [{"id": i, "name": n} for i, n in groups],
                },
            )
        return httpx2.Response(200, json={"status": "ok"})

    return handler


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("groups", "ref", "expected_path"),
    [
        # LibreNMS reads "2024" as an ID, so the group named so goes by its ID.
        ([(7, "2024")], "2024", "/api/v0/devicegroups/7"),
        # Nobody is named "7": it is the ID, as meant.
        ([(7, "core")], "7", "/api/v0/devicegroups/7"),
        # The name and the ID are the same group.
        ([(7, "7")], "7", "/api/v0/devicegroups/7"),
        # An unknown ID is left to LibreNMS to report.
        ([(7, "core")], "99", "/api/v0/devicegroups/99"),
    ],
)
async def test_all_digit_group_refs_go_to_the_meant_group(
    server, groups, ref, expected_path
):
    mcp, requests, set_handler = server
    set_handler(_device_groups(*groups))
    async with Client(mcp) as client:
        await client.call_tool("devicegroup_delete", {"name": ref})
    assert (requests[-1].method, requests[-1].url.path) == ("DELETE", expected_path)


@pytest.mark.asyncio
async def test_all_digit_group_ref_naming_another_group_is_refused(server):
    """ "2024" is group 7's name and group 2024's ID: deleting either is a guess."""
    mcp, requests, set_handler = server
    set_handler(_device_groups((7, "2024"), (2024, "core")))
    async with Client(mcp) as client:
        result = await client.call_tool("devicegroup_delete", {"name": "2024"})
    assert result.data["status"] == "error"
    assert "both the ID of device group 'core'" in result.data["message"]
    assert [r.method for r in requests] == ["GET"]


@pytest.mark.asyncio
async def test_all_digit_group_id_shared_by_several_names_points_to_its_name(server):
    """ "Use the ID" would loop: the caller already sent group 2024's ID."""
    mcp, requests, set_handler = server
    set_handler(_device_groups((2024, "core"), (1, "2024"), (2, "2024")))
    async with Client(mcp) as client:
        result = await client.call_tool("devicegroup_delete", {"name": "2024"})
    assert result.data["status"] == "error"
    assert "both the ID of device group 'core'" in result.data["message"]
    assert not result.data["message"].endswith("use the ID")
    assert [r.method for r in requests] == ["GET"]


@pytest.mark.asyncio
async def test_all_digit_group_id_among_its_namesakes_names_the_others(server):
    """Groups 5 and 9 are both named "5": "use the ID" would loop for group 5."""
    mcp, requests, set_handler = server
    set_handler(_device_groups((5, "5"), (9, "5")))
    async with Client(mcp) as client:
        result = await client.call_tool("devicegroup_delete", {"name": "5"})
    assert result.data["status"] == "error"
    assert "use ID 9 for the others" in result.data["message"]
    assert [r.method for r in requests] == ["GET"]


@pytest.mark.asyncio
async def test_all_digit_group_ref_with_leading_zeros_is_read_as_the_id(server):
    """LibreNMS reads "007" as ID 7, so a group named "007" conflicts with it."""
    mcp, requests, set_handler = server
    set_handler(_device_groups((7, "core"), (12, "007")))
    async with Client(mcp) as client:
        result = await client.call_tool("devicegroup_delete", {"name": "007"})
    assert result.data["status"] == "error"
    assert "both the ID of device group 'core'" in result.data["message"]
    assert [r.method for r in requests] == ["GET"]


@pytest.mark.asyncio
async def test_location_names_without_a_slash_need_no_lookup(server):
    mcp, requests, _ = server
    async with Client(mcp) as client:
        await client.call_tool("location_get", {"location": "DC1"})
    assert [r.url.path for r in requests] == ["/api/v0/location/DC1"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("tool", "args", "key", "message"),
    [
        ("alert_get_by_id", {"alert_id": 9}, "alerts", "Alert 9 does not exist"),
        ("alert_rule_get", {"rule_id": 9}, "rules", "Alert rule 9 does not exist"),
        (
            "alert_template_get",
            {"template_id": 9},
            "alert_templates",
            "Alert template 9 does not exist",
        ),
        ("bill_get", {"bill_id": 9}, "bills", "Bill 9 does not exist"),
        ("port_get", {"port_id": 9}, "port", "Port 9 does not exist"),
    ],
)
async def test_lookups_by_unknown_id_report_not_found(server, tool, args, key, message):
    """LibreNMS answers an unknown ID with status ok and an empty list."""
    mcp, _, set_handler = server
    set_handler(
        lambda _r: httpx2.Response(200, json={"status": "ok", key: [], "count": 0})
    )
    async with Client(mcp) as client:
        result = await client.call_tool(tool, args)
    assert result.data == {"status": "error", "message": message}


@pytest.mark.asyncio
async def test_lookups_by_known_id_are_unchanged(server):
    mcp, _, set_handler = server
    body = {"status": "ok", "port": [{"port_id": 33}], "count": 1}
    set_handler(lambda _r: httpx2.Response(200, json=body))
    async with Client(mcp) as client:
        result = await client.call_tool("port_get", {"port_id": 33})
    assert result.data == body


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("tool", "message"),
    [
        ("alert_acknowledge", "No Alert by that ID"),
        ("alert_unmute", "No alert by that ID"),
    ],
)
async def test_alert_actions_on_unknown_alerts_are_errors(server, tool, message):
    """LibreNMS reports 'No alert by that ID' with status ok, like a success."""
    mcp, _, set_handler = server
    set_handler(
        lambda _r: httpx2.Response(200, json={"status": "ok", "message": message})
    )
    async with Client(mcp) as client:
        result = await client.call_tool(tool, {"alert_id": 999})
    assert result.data == {"status": "error", "message": message}


@pytest.mark.asyncio
async def test_unknown_location_name_with_a_slash_is_reported(server):
    """Sent as a name it would split the route ('This API route doesn't exist')."""
    mcp, requests, set_handler = server
    set_handler(lambda _r: httpx2.Response(200, json={"status": "ok", "locations": []}))
    async with Client(mcp) as client:
        result = await client.call_tool("location_get", {"location": "DC9/Room 1"})
    assert result.data == {
        "status": "error",
        "message": "Location 'DC9/Room 1' does not exist",
    }
    assert [r.url.path for r in requests] == ["/api/v0/resources/locations"]


@pytest.mark.asyncio
async def test_location_delete_goes_by_id_for_names_with_a_slash(server):
    """del_location takes an ID too (ctype_digit -> where id); verified live."""
    mcp, requests, set_handler = server

    def handler(request: httpx2.Request) -> httpx2.Response:
        if request.url.path == "/api/v0/resources/locations":
            return httpx2.Response(
                200,
                json={
                    "status": "ok",
                    "locations": [{"id": 7, "location": "DC1/Room 2"}],
                },
            )
        return httpx2.Response(200, json={"status": "ok"})

    set_handler(handler)
    async with Client(mcp) as client:
        await client.call_tool("location_delete", {"location": "DC1/Room 2"})
    assert [(r.method, r.url.path) for r in requests] == [
        ("GET", "/api/v0/resources/locations"),
        ("DELETE", "/api/v0/locations/7"),
    ]


@pytest.mark.asyncio
async def test_location_lookup_failure_is_not_reported_as_missing(server):
    mcp, _, set_handler = server
    set_handler(
        lambda _r: httpx2.Response(403, json={"status": "error", "message": "Denied"})
    )
    async with Client(mcp) as client:
        result = await client.call_tool("location_get", {"location": "DC1/Room 2"})
    assert result.data == {
        "status": "error",
        "message": "Could not look up location 'DC1/Room 2': Denied",
    }


@pytest.mark.asyncio
async def test_location_names_with_a_slash_match_case_insensitively(server):
    mcp, requests, set_handler = server

    def handler(request: httpx2.Request) -> httpx2.Response:
        if request.url.path == "/api/v0/resources/locations":
            return httpx2.Response(
                200,
                json={
                    "status": "ok",
                    "locations": [{"id": 7, "location": "DC1/Room 2"}],
                },
            )
        return httpx2.Response(200, json={"status": "ok"})

    set_handler(handler)
    async with Client(mcp) as client:
        await client.call_tool("location_get", {"location": "dc1/room 2"})
    assert requests[-1].url.path == "/api/v0/location/7"


def _groups_handler(request: httpx2.Request) -> httpx2.Response:
    if request.url.path in ("/api/v0/devicegroups", "/api/v0/port_groups"):
        return httpx2.Response(
            200, json={"status": "ok", "groups": [{"id": 4, "name": "Site A/Core"}]}
        )
    return httpx2.Response(200, json={"status": "ok"})


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("tool", "extra", "method", "path"),
    [
        ("devicegroup_devices", {}, "GET", "/api/v0/devicegroups/4"),
        (
            "devicegroup_update",
            {"payload": {"desc": "x"}},
            "PATCH",
            "/api/v0/devicegroups/4",
        ),
        ("devicegroup_delete", {}, "DELETE", "/api/v0/devicegroups/4"),
        (
            "devicegroup_add_devices",
            {"payload": {"devices": [1]}},
            "POST",
            "/api/v0/devicegroups/4/devices",
        ),
        (
            "devicegroup_remove_devices",
            {"payload": {"devices": [1]}},
            "DELETE",
            "/api/v0/devicegroups/4/devices",
        ),
        (
            "devicegroup_set_maintenance",
            {"payload": {"duration": "01:00"}},
            "POST",
            "/api/v0/devicegroups/4/maintenance",
        ),
        ("port_group_list_ports", {}, "GET", "/api/v0/port_groups/4"),
    ],
)
async def test_group_names_with_a_slash_go_by_id(server, tool, extra, method, path):
    """A '/' in the name splits LibreNMS's route; every group route takes the ID."""
    mcp, requests, set_handler = server
    set_handler(_groups_handler)
    async with Client(mcp) as client:
        await client.call_tool(tool, {"name": "Site A/Core", **extra})
    assert [(r.method, r.url.path) for r in requests][-1] == (method, path)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("tool", "label"),
    [("devicegroup_devices", "Device group"), ("port_group_list_ports", "Port group")],
)
async def test_unknown_group_name_with_a_slash_is_reported(server, tool, label):
    mcp, requests, set_handler = server
    set_handler(_groups_handler)
    async with Client(mcp) as client:
        result = await client.call_tool(tool, {"name": "Site B/Edge"})
    assert result.data == {
        "status": "error",
        "message": f"{label} 'Site B/Edge' does not exist",
    }
    assert len(requests) == 1


@pytest.mark.asyncio
async def test_group_names_without_a_slash_need_no_lookup(server):
    mcp, requests, _ = server
    async with Client(mcp) as client:
        await client.call_tool("devicegroup_devices", {"name": "Core"})
    assert [r.url.path for r in requests] == ["/api/v0/devicegroups/Core"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("DC1/Pollers", ["/api/v0/poller_group", "/api/v0/poller_group/3"]),
        ("DC1", ["/api/v0/poller_group/DC1"]),
    ],
)
async def test_poller_group_names_with_a_slash_go_by_id(server, name, expected):
    """get_poller_group takes an ID too (ctype_digit -> find)."""
    mcp, requests, set_handler = server
    set_handler(
        lambda _r: httpx2.Response(
            200,
            json={
                "status": "ok",
                "get_poller_group": [{"id": 3, "group_name": "DC1/Pollers"}],
            },
        )
    )
    async with Client(mcp) as client:
        await client.call_tool("poller_group_get", {"poller_group": name})
    assert [r.url.path for r in requests] == expected


@pytest.mark.asyncio
async def test_unknown_poller_group_name_with_a_slash_is_reported(server):
    mcp, _, set_handler = server
    set_handler(
        lambda _r: httpx2.Response(200, json={"status": "ok", "get_poller_group": []})
    )
    async with Client(mcp) as client:
        result = await client.call_tool(
            "poller_group_get", {"poller_group": "DC9/Pollers"}
        )
    assert result.data == {
        "status": "error",
        "message": "Poller group 'DC9/Pollers' does not exist",
    }


@pytest.mark.asyncio
async def test_service_add_with_an_ip_still_rejects_unknown_devices(server):
    """An explicit ip used to skip the check and could orphan a service."""
    mcp, requests, set_handler = server
    set_handler(_unknown_device)
    async with Client(mcp) as client:
        result = await client.call_tool(
            "service_add",
            {"hostname": "999", "payload": {"type": "icmp", "ip": "10.0.0.1"}},
        )
    assert result.data["message"] == "Device typo does not exist"
    assert [r.method for r in requests] == ["GET"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "body",
    [
        {"status": "ok"},
        {"status": "ok", "devices": []},
        {"message": "login required"},
    ],
)
async def test_device_check_requires_the_device_record(server, body):
    """Only LibreNMS's "ok" with the device record confirms a device."""
    mcp, requests, set_handler = server
    set_handler(lambda _r: httpx2.Response(200, json=body))
    async with Client(mcp) as client:
        result = await client.call_tool("logs_eventlog", {"hostname": "core1"})
    assert result.data["status"] == "error"
    assert (
        "Unexpected response when looking up device 'core1'" in result.data["message"]
    )
    assert [r.url.path for r in requests] == ["/api/v0/devices/core1"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("tool", "args"),
    [
        ("oxidized_config_search", {"search": "10.0.0.0/24"}),
        ("arp_search", {"query": "2001:db8::/64"}),
        ("arp_search", {"query": "10.0.0.0/99"}),
        ("arp_search", {"query": "10.0.0.1", "device": "core1"}),
    ],
)
async def test_local_validation_errors_use_the_librenms_shape(server, tool, args):
    """Callers check status == "error" for LibreNMS's and our own errors alike."""
    mcp, requests, _ = server
    async with Client(mcp) as client:
        result = await client.call_tool(tool, args)
    assert result.data["status"] == "error"
    assert result.data["message"]
    assert "error" not in result.data
    assert requests == []
