"""
LibreNMS MCP Server Port Security Tools
"""

from typing import Annotated
from urllib.parse import quote

from fastmcp.server.context import Context
from pydantic import Field

from librenms_mcp.librenms_client import LibreNMSClient
from librenms_mcp.utils import paginate_list


def register_port_security_tools(mcp, config):
    """Register LibreNMS port security tools with the MCP server"""
    ##########################
    # Port Security Tools
    ##########################

    @mcp.tool(
        tags={"librenms", "ports", "port-security", "read-only"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def port_security_list(
        ctx: Context,
        limit: Annotated[
            int,
            Field(default=100, description="Maximum number of results to return", ge=1),
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
        List port security configuration across all devices.

        Covers switchport port-security state such as the maximum number of
        learned MAC addresses, violation mode and current status.

        Args:
            limit (int): Maximum number of results to return.
            offset (int): Number of results to skip.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info("Listing port security configuration...")

            async with LibreNMSClient(config) as client:
                result = await client.get("port_security")
                return paginate_list(result, limit, offset, key="port")

        except Exception as e:
            await ctx.error(f"Error listing port security configuration: {e!s}")
            return {"error": str(e)}

    @mcp.tool(
        tags={"librenms", "ports", "port-security", "read-only"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def port_security_device(
        hostname: Annotated[str, Field(description="Device hostname or device ID")],
        ctx: Context,
        limit: Annotated[
            int,
            Field(default=100, description="Maximum number of results to return", ge=1),
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
        Get port security configuration for every port on a device.

        Args:
            hostname (str): Device hostname or device ID.
            limit (int): Maximum number of results to return.
            offset (int): Number of results to skip.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info(f"Getting port security for {hostname}...")

            async with LibreNMSClient(config) as client:
                result = await client.get(
                    f"port_security/device/{quote(hostname, safe='')}"
                )
                return paginate_list(result, limit, offset, key="port")

        except Exception as e:
            await ctx.error(f"Error getting port security for {hostname}: {e!s}")
            return {"error": str(e)}

    @mcp.tool(
        tags={"librenms", "ports", "port-security", "read-only"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def port_security_port(
        port_id: Annotated[int, Field(ge=1, description="Port ID")],
        ctx: Context,
    ) -> dict:
        """
        Get port security configuration for a single port.

        Args:
            port_id (int): Port ID.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info(f"Getting port security for port {port_id}...")

            async with LibreNMSClient(config) as client:
                return await client.get(f"port_security/port/{port_id}")

        except Exception as e:
            await ctx.error(f"Error getting port security for port {port_id}: {e!s}")
            return {"error": str(e)}
