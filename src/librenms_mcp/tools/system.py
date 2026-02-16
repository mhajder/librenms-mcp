"""
LibreNMS MCP Server System Tools
"""

from fastmcp.server.context import Context

from librenms_mcp.librenms_client import LibreNMSClient


def register_system_tools(mcp, config):
    """Register LibreNMS system tools with the MCP server"""
    ##########################
    # System Tools
    ##########################

    @mcp.tool(
        tags={"librenms", "system", "read-only"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def system_info(ctx: Context) -> dict:
        """
        Get system info from LibreNMS.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info("Getting system info...")

            async with LibreNMSClient(config) as client:
                return await client.get("system")

        except Exception as e:
            await ctx.error(f"Error system info: {e!s}")
            return {"error": str(e)}

    @mcp.tool(
        tags={"librenms", "system", "read-only"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def ping(ctx: Context) -> dict:
        """
        Simple API health check - ping LibreNMS API.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info("Pinging LibreNMS API...")

            async with LibreNMSClient(config) as client:
                return await client.get("ping")

        except Exception as e:
            await ctx.error(f"Error pinging API: {e!s}")
            return {"error": str(e)}
