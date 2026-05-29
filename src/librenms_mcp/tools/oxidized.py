"""
LibreNMS MCP Server Oxidized Tools
"""

from typing import Annotated
from urllib.parse import quote

from fastmcp.server.context import Context
from pydantic import Field

from librenms_mcp.librenms_client import LibreNMSClient
from librenms_mcp.utils import paginate_list


def register_oxidized_tools(mcp, config):
    """Register LibreNMS Oxidized tools with the MCP server"""
    ##########################
    # Oxidized Tools
    ##########################

    @mcp.tool(
        tags={"librenms", "oxidized", "read-only"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def oxidized_list(
        ctx: Context,
        hostname: Annotated[
            str | None,
            Field(default=None, description="Filter by device hostname. Optional."),
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
        List devices tracked by Oxidized for config backup.

        Args:
            hostname (str, optional): Filter by device hostname.
            limit (int): Maximum number of results to return.
            offset (int): Number of results to skip.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info("Listing Oxidized devices...")

            async with LibreNMSClient(config) as client:
                path = (
                    f"oxidized/{quote(hostname, safe='')}" if hostname else "oxidized"
                )
                result = await client.get(path)
                if isinstance(result, list):
                    result = {"devices": result}
                return paginate_list(result, limit, offset, key="devices")

        except Exception as e:
            await ctx.error(f"Error listing Oxidized devices: {e!s}")
            return {"error": str(e)}

    @mcp.tool(
        tags={"librenms", "oxidized", "read-only"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def oxidized_config_get(
        hostname: Annotated[str, Field(description="Device hostname")],
        ctx: Context,
    ) -> dict:
        """
        Get the stored device configuration from Oxidized for a specific device.

        Args:
            hostname (str): Device hostname.

        Returns:
            dict: The JSON response from the API containing the device config.
        """
        try:
            await ctx.info(f"Getting Oxidized config for {hostname}...")

            async with LibreNMSClient(config) as client:
                result = await client.get(f"oxidized/config/{quote(hostname, safe='')}")
                if isinstance(result, list):
                    return {"configs": result}
                return result

        except Exception as e:
            await ctx.error(f"Error getting Oxidized config for {hostname}: {e!s}")
            return {"error": str(e)}

    @mcp.tool(
        tags={"librenms", "oxidized", "read-only"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def oxidized_config_search(
        search: Annotated[
            str,
            Field(
                description="Search string to look for in all stored device configs (e.g. an IP address, interface name, ACL name, or any config keyword)"
            ),
        ],
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
        Search all Oxidized device configurations for a string.

        Args:
            search (str): Search string (IP, interface, ACL, keyword, etc.).
            limit (int): Maximum number of results to return.
            offset (int): Number of results to skip.

        Returns:
            dict: The JSON response from the API with matching devices and config snippets.
        """
        try:
            await ctx.info(f"Searching Oxidized configs for '{search}'...")

            async with LibreNMSClient(config) as client:
                result = await client.get(
                    f"oxidized/config/search/{quote(search, safe='')}"
                )
                if isinstance(result, list):
                    result = {"results": result}
                return paginate_list(result, limit, offset, key="results")

        except Exception as e:
            await ctx.error(f"Error searching Oxidized configs: {e!s}")
            return {"error": str(e)}
