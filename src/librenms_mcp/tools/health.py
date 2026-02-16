"""
LibreNMS MCP Server Health Tools
"""

from typing import Annotated
from urllib.parse import quote

from fastmcp.server.context import Context
from pydantic import Field

from librenms_mcp.librenms_client import LibreNMSClient


def register_health_tools(mcp, config):
    """Register LibreNMS health tools with the MCP server"""
    ##########################
    # Sensors / Health Tools
    ##########################

    @mcp.tool(
        tags={"librenms", "health", "read-only"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def health_list(
        hostname: Annotated[str, Field(description="Device hostname or ID")],
        ctx: Context,
    ) -> dict:
        """
        List available health graphs for a device.

        Args:
            hostname (str): Device hostname or ID.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info(f"Getting health graphs for {hostname}...")

            async with LibreNMSClient(config) as client:
                return await client.get(f"devices/{hostname}/health")

        except Exception as e:
            await ctx.error(f"Error getting health graphs for {hostname}: {e!s}")
            return {"error": str(e)}

    @mcp.tool(
        tags={"librenms", "health", "read-only"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def health_by_type(
        hostname: Annotated[str, Field(description="Device hostname or ID")],
        type: Annotated[
            str,
            Field(description="Sensor type (e.g. temperature, voltage, fanspeed)"),
        ],
        ctx: Context,
    ) -> dict:
        """
        Get health data by sensor type for a device.

        Args:
            hostname (str): Device hostname or ID.
            type (str): Sensor type (e.g. temperature, voltage, fanspeed).

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info(f"Getting {type} health data for {hostname}...")

            async with LibreNMSClient(config) as client:
                return await client.get(
                    f"devices/{hostname}/health/{quote(type, safe='')}"
                )

        except Exception as e:
            await ctx.error(f"Error getting {type} health data for {hostname}: {e!s}")
            return {"error": str(e)}

    @mcp.tool(
        tags={"librenms", "health", "read-only"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def health_sensor_get(
        hostname: Annotated[str, Field(description="Device hostname or ID")],
        type: Annotated[
            str,
            Field(description="Sensor type (e.g. temperature, voltage, fanspeed)"),
        ],
        sensor_id: Annotated[int, Field(ge=1, description="Sensor ID")],
        ctx: Context,
    ) -> dict:
        """
        Get a specific sensor by ID for a device.

        Args:
            hostname (str): Device hostname or ID.
            type (str): Sensor type (e.g. temperature, voltage, fanspeed).
            sensor_id (int): Sensor ID.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info(f"Getting sensor {sensor_id} ({type}) for {hostname}...")

            async with LibreNMSClient(config) as client:
                return await client.get(
                    f"devices/{hostname}/health/{quote(type, safe='')}/{sensor_id}"
                )

        except Exception as e:
            await ctx.error(
                f"Error getting sensor {sensor_id} ({type}) for {hostname}: {e!s}"
            )
            return {"error": str(e)}

    @mcp.tool(
        tags={"librenms", "sensors", "read-only"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def sensors_list(
        ctx: Context,
    ) -> dict:
        """
        List all sensors across all devices.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info("Listing all sensors...")

            async with LibreNMSClient(config) as client:
                return await client.get("resources/sensors")

        except Exception as e:
            await ctx.error(f"Error listing sensors: {e!s}")
            return {"error": str(e)}
