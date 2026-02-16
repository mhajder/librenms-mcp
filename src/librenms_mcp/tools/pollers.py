"""
LibreNMS MCP Server Poller Tools
"""

from typing import Annotated

from fastmcp.server.context import Context
from pydantic import Field

from librenms_mcp.librenms_client import LibreNMSClient


def register_poller_tools(mcp, config):
    """Register LibreNMS poller tools with the MCP server"""
    ##########################
    # Poller Groups
    ##########################

    @mcp.tool(
        tags={"librenms", "poller-groups", "read-only", "admin"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def poller_group_get(
        poller_group: Annotated[
            str, Field(description="Poller group identifier or 'all'")
        ],
        ctx: Context,
    ) -> dict:
        """
        Get poller group(s) from LibreNMS.

        Args:
            poller_group (str): Poller group identifier or 'all'.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info(f"Getting poller group {poller_group}...")

            async with LibreNMSClient(config) as client:
                return await client.get(f"poller_group/{poller_group}")

        except Exception as e:
            await ctx.error(f"Error poller group {poller_group}: {e!s}")
            return {"error": str(e)}
