"""
LibreNMS MCP Server Inventory Tools
"""

from typing import Annotated
from typing import Any

from fastmcp.server.context import Context
from pydantic import Field

from librenms_mcp.librenms_client import LibreNMSClient
from librenms_mcp.utils import paginate_list


def register_inventory_tools(mcp, config):
    """Register LibreNMS inventory tools with the MCP server"""
    ##########################
    # Inventory Tools
    ##########################

    @mcp.tool(
        tags={"librenms", "inventory", "read-only"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def inventory_device(
        ctx: Context,
        hostname: Annotated[str, Field(description="Device hostname or ID")],
        ent_physical_class: Annotated[
            str | None,
            Field(
                default=None,
                description="Filter by entity physical class (e.g., chassis, module, port, powerSupply, fan, sensor)",
            ),
        ] = None,
        ent_physical_contained_in: Annotated[
            int | str | None,
            Field(
                default=None,
                description="Filter by parent entity index",
            ),
        ] = None,
        limit: Annotated[
            int,
            Field(
                default=100,
                description="Maximum number of results to return",
                ge=1,
            ),
        ] = 100,
        offset: Annotated[
            int,
            Field(
                default=0,
                description="Number of results to skip (offset) for pagination",
                ge=0,
            ),
        ] = 0,
    ) -> dict:
        """
        Get inventory for a device from LibreNMS.

        Args:
            hostname (str): Device hostname or ID.
            ent_physical_class (str, optional): Filter by entity physical class.
            ent_physical_contained_in (int, optional): Filter by parent entity.
            limit (int): Maximum number of results to return.
            offset (int): Number of results to skip.

        Returns:
            dict: The JSON response from the API.
        """
        params: dict[str, Any] = {}
        if ent_physical_class is not None:
            params["entPhysicalClass"] = ent_physical_class
        if ent_physical_contained_in is not None:
            params["entPhysicalContainedIn"] = ent_physical_contained_in

        try:
            await ctx.info(f"Getting inventory for {hostname}...")

            async with LibreNMSClient(config) as client:
                result = await client.get(
                    f"inventory/{hostname}", params=params or None
                )
            return paginate_list(result, limit, offset, key="inventory")

        except Exception as e:
            await ctx.error(f"Error inventory {hostname}: {e!s}")
            return {"error": str(e)}

    @mcp.tool(
        tags={"librenms", "inventory", "read-only"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def inventory_device_flat(
        hostname: Annotated[str, Field()],
        ctx: Context,
        limit: Annotated[
            int,
            Field(
                default=100,
                description="Maximum number of results to return",
                ge=1,
            ),
        ] = 100,
        offset: Annotated[
            int,
            Field(
                default=0,
                description="Number of results to skip (offset) for pagination",
                ge=0,
            ),
        ] = 0,
    ) -> dict:
        """
        Get flattened inventory for a device from LibreNMS.

        Args:
            hostname (str): Device hostname.
            limit (int): Maximum number of results to return.
            offset (int): Number of results to skip.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info(f"Getting flattened inventory for {hostname}...")

            async with LibreNMSClient(config) as client:
                result = await client.get(f"inventory/{hostname}/all")
            return paginate_list(result, limit, offset, key="inventory")

        except Exception as e:
            await ctx.error(f"Error inventory flat {hostname}: {e!s}")
            return {"error": str(e)}
