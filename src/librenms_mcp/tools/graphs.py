"""
LibreNMS MCP Server Graph Tools
"""

from typing import Annotated
from typing import Any
from urllib.parse import quote

from fastmcp.exceptions import ToolError
from fastmcp.server.context import Context
from fastmcp.utilities.types import Image
from pydantic import Field

from librenms_mcp.librenms_client import LibreNMSClient

# Graph endpoints return an image, so a failure cannot be reported as a dict the
# way the JSON tools do. They raise ToolError instead.

FromField = Annotated[
    str | None,
    Field(
        default=None,
        description="Start of the time range, either a relative offset such as '-1d', '-6h' or '-1w', or a Unix timestamp. Defaults to the LibreNMS default (-1d).",
    ),
]
ToField = Annotated[
    str | None,
    Field(
        default=None,
        description="End of the time range, either a relative offset or a Unix timestamp. Defaults to now.",
    ),
]
WidthField = Annotated[
    int | None,
    Field(default=None, description="Graph width in pixels.", ge=1),
]
HeightField = Annotated[
    int | None,
    Field(default=None, description="Graph height in pixels.", ge=1),
]
LegendField = Annotated[
    bool | None,
    Field(default=None, description="Whether to render the graph legend."),
]


def _graph_params(
    from_: str | None,
    to: str | None,
    width: int | None,
    height: int | None,
    legend: bool | None,
) -> dict[str, Any]:
    """Build the query parameters shared by every graph endpoint."""
    params: dict[str, Any] = {}
    if from_ is not None:
        params["from"] = from_
    if to is not None:
        params["to"] = to
    if width is not None:
        params["width"] = width
    if height is not None:
        params["height"] = height
    if legend is not None:
        params["legend"] = "yes" if legend else "no"
    return params


async def _resolve_port_id(client: LibreNMSClient, hostname: str, ifname: str) -> int:
    """Look up the numeric port ID behind a device hostname and interface name."""
    result = await client.get(
        f"devices/{quote(hostname, safe='')}/ports",
        params={"columns": "port_id,ifName"},
    )
    for port in result.get("ports") or []:
        if str(port.get("ifName", "")).casefold() == ifname.casefold():
            return int(port["port_id"])
    raise ToolError(f"No interface named '{ifname}' found on {hostname}.")


def _to_image(data: bytes, content_type: str) -> Image:
    """Wrap a graph response body in an MCP image.

    LibreNMS serves graphs as SVG on current releases and as PNG on older ones,
    so the MIME type is taken from the response rather than assumed.
    """
    if not content_type.startswith("image/"):
        raise ToolError(
            f"Expected an image from the LibreNMS graph endpoint, got '{content_type}'. "
            "This usually means LibreNMS returned a JSON error instead of rendering the graph."
        )
    return Image(data=data, format=content_type.removeprefix("image/"))


def register_graph_tools(mcp, config):
    """Register LibreNMS graph tools with the MCP server"""
    ##########################
    # Graph Tools
    ##########################

    @mcp.tool(
        tags={"librenms", "graphs", "read-only"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def device_graphs_list(
        hostname: Annotated[str, Field(description="Device hostname or device ID")],
        ctx: Context,
    ) -> dict:
        """
        List the graph types available for a device.

        Use this to discover the values accepted by the `graph_type` argument of
        device_graph, for example 'device_icmp_perf' or 'device_poller_perf'.

        Args:
            hostname (str): Device hostname or device ID.

        Returns:
            dict: The JSON response from the API listing available graphs.
        """
        try:
            await ctx.info(f"Listing available graphs for {hostname}...")

            async with LibreNMSClient(config) as client:
                return await client.get(f"devices/{quote(hostname, safe='')}/graphs")

        except Exception as e:
            await ctx.error(f"Error listing graphs for {hostname}: {e!s}")
            return {"error": str(e)}

    @mcp.tool(
        tags={"librenms", "graphs", "read-only"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def device_graph(
        hostname: Annotated[str, Field(description="Device hostname or device ID")],
        graph_type: Annotated[
            str,
            Field(
                description="Graph type, as returned by device_graphs_list (e.g. 'device_icmp_perf', 'device_poller_perf', 'device_availability')"
            ),
        ],
        ctx: Context,
        from_time: FromField = None,
        to_time: ToField = None,
        width: WidthField = None,
        height: HeightField = None,
        legend: LegendField = None,
    ) -> Image:
        """
        Render a device-level graph as an image.

        Args:
            hostname (str): Device hostname or device ID.
            graph_type (str): Graph type from device_graphs_list.
            from_time (str, optional): Start of the time range, e.g. '-1d'.
            to_time (str, optional): End of the time range.
            width (int, optional): Graph width in pixels.
            height (int, optional): Graph height in pixels.
            legend (bool, optional): Whether to render the legend.

        Returns:
            Image: The rendered graph.
        """
        try:
            await ctx.info(f"Rendering {graph_type} graph for {hostname}...")

            async with LibreNMSClient(config) as client:
                data, content_type = await client.get_raw(
                    f"devices/{quote(hostname, safe='')}/{quote(graph_type, safe='')}",
                    params=_graph_params(from_time, to_time, width, height, legend),
                )
                return _to_image(data, content_type)

        except ToolError:
            raise
        except Exception as e:
            await ctx.error(f"Error rendering {graph_type} graph for {hostname}: {e!s}")
            raise ToolError(
                f"Could not render the {graph_type} graph for {hostname}: {e!s}"
            ) from e

    @mcp.tool(
        tags={"librenms", "graphs", "ports", "read-only"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def port_graph(
        hostname: Annotated[str, Field(description="Device hostname or device ID")],
        ifname: Annotated[
            str,
            Field(
                description="Interface name as reported by LibreNMS, e.g. 'Po1' or 'Te2/7'"
            ),
        ],
        ctx: Context,
        graph_type: Annotated[
            str,
            Field(
                default="bits",
                description="Graph type: 'bits' (traffic), 'upkts' (unicast packets), 'errors', or 'etherlike'",
            ),
        ] = "bits",
        from_time: FromField = None,
        to_time: ToField = None,
        width: WidthField = None,
        height: HeightField = None,
        legend: LegendField = None,
    ) -> Image:
        """
        Render a per-port graph as an image, for example interface traffic.

        Some LibreNMS releases fail to render through the per-port endpoint and
        answer 500 with an empty graph type in the message. For 'bits' this tool
        then falls back to the port-group endpoint, which renders the same
        traffic data, so callers still get a graph without needing a port ID.

        Args:
            hostname (str): Device hostname or device ID.
            ifname (str): Interface name, e.g. 'Po1' or 'Te2/7'.
            graph_type (str): bits, upkts, errors or etherlike.
            from_time (str, optional): Start of the time range, e.g. '-1d'.
            to_time (str, optional): End of the time range.
            width (int, optional): Graph width in pixels.
            height (int, optional): Graph height in pixels.
            legend (bool, optional): Whether to render the legend.

        Returns:
            Image: The rendered graph.
        """
        params = _graph_params(from_time, to_time, width, height, legend)
        try:
            await ctx.info(f"Rendering {graph_type} graph for {hostname} {ifname}...")

            async with LibreNMSClient(config) as client:
                try:
                    data, content_type = await client.get_raw(
                        f"devices/{quote(hostname, safe='')}/ports/{quote(ifname, safe='')}/{quote(graph_type, safe='')}",
                        params=params,
                    )
                except Exception as e:
                    # Only 'bits' has a port-group equivalent to fall back to.
                    if graph_type != "bits":
                        raise
                    await ctx.info(
                        f"Per-port graph endpoint failed ({e!s}); retrying via the port-group endpoint..."
                    )
                    port_id = await _resolve_port_id(client, hostname, ifname)
                    data, content_type = await client.get_raw(
                        f"portgroups/multiport/bits/{port_id}", params=params
                    )
                return _to_image(data, content_type)

        except ToolError:
            raise
        except Exception as e:
            await ctx.error(
                f"Error rendering {graph_type} graph for {hostname} {ifname}: {e!s}"
            )
            raise ToolError(
                f"Could not render the {graph_type} graph for {hostname} {ifname}: {e!s}"
            ) from e

    @mcp.tool(
        tags={"librenms", "graphs", "ports", "read-only"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def port_group_graph(
        port_ids: Annotated[
            list[int],
            Field(
                description="One or more port IDs to plot on a single graph. Resolve names to IDs with ports_search_field or device_ports.",
                min_length=1,
            ),
        ],
        ctx: Context,
        from_time: FromField = None,
        to_time: ToField = None,
        width: WidthField = None,
        height: HeightField = None,
        legend: LegendField = None,
    ) -> Image:
        """
        Render a traffic graph for one or more ports, by port ID.

        Plots every supplied port on the same axes, which makes it useful for
        comparing members of a LAG. Unlike port_graph this takes numeric port
        IDs rather than interface names.

        Args:
            port_ids (list[int]): Port IDs to plot.
            from_time (str, optional): Start of the time range, e.g. '-1d'.
            to_time (str, optional): End of the time range.
            width (int, optional): Graph width in pixels.
            height (int, optional): Graph height in pixels.
            legend (bool, optional): Whether to render the legend.

        Returns:
            Image: The rendered graph.
        """
        ids = ",".join(str(port_id) for port_id in port_ids)
        try:
            await ctx.info(f"Rendering traffic graph for port(s) {ids}...")

            async with LibreNMSClient(config) as client:
                data, content_type = await client.get_raw(
                    f"portgroups/multiport/bits/{quote(ids, safe='')}",
                    params=_graph_params(from_time, to_time, width, height, legend),
                )
                return _to_image(data, content_type)

        except ToolError:
            raise
        except Exception as e:
            await ctx.error(f"Error rendering traffic graph for port(s) {ids}: {e!s}")
            raise ToolError(
                f"Could not render the traffic graph for port(s) {ids}: {e!s}"
            ) from e
