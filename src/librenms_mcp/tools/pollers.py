"""
LibreNMS MCP Server Poller Tools
"""

from typing import Annotated

from fastmcp.server.context import Context
from pydantic import Field

from librenms_mcp.librenms_client import LibreNMSClient
from librenms_mcp.tools.name_refs import POLLER_GROUP
from librenms_mcp.tools.name_refs import is_librenms_id
from librenms_mcp.tools.name_refs import route_ref
from librenms_mcp.utils import error_body
from librenms_mcp.utils import optional_segment


def register_poller_tools(mcp, config):
    """Register LibreNMS poller tools with the MCP server"""
    ##########################
    # Poller Groups
    ##########################

    @mcp.tool(
        tags={"librenms", "poller-groups", "read-only", "global-read"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def poller_group_get(
        ctx: Context,
        poller_group: Annotated[
            str | None,
            Field(
                default=None,
                description="Poller group ID or name. Omit (or pass 'all') to list every poller group; a group literally named 'all' must be fetched by its ID.",
            ),
        ] = None,
    ) -> dict:
        """
        Get poller group(s) from LibreNMS.

        Args:
            poller_group (str, optional): Poller group ID or name; omit or 'all' for every group.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            # LibreNMS lists every group only when the segment is left out; it
            # would look up 'all' as a group name and report it missing.
            if poller_group is not None and poller_group.strip().casefold() == "all":
                poller_group = None
            await ctx.info(f"Getting poller group {poller_group or 'list'}...")

            async with LibreNMSClient(config) as client:
                group = optional_segment(poller_group)
                if group:
                    ref = await route_ref(client, POLLER_GROUP, group[0])
                    if is_librenms_id(ref) and int(ref) == 0:
                        # PHP's empty() is true for "0", so LibreNMS would
                        # answer with every group as if it were group 0; "00"
                        # misses the (virtual) default group as "not found".
                        return error_body(
                            "Poller group 0 (the default group) cannot be looked "
                            "up by ID; omit poller_group to list every group"
                        )
                    group = (ref,)
                return await client.get("poller_group", *group)

        except Exception as e:
            await ctx.error(f"Error poller group {poller_group}: {e!s}")
            return error_body(str(e))
