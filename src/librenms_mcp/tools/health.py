"""
LibreNMS MCP Server Health Tools
"""

from typing import Annotated
from urllib.parse import quote

from fastmcp.server.context import Context
from pydantic import Field

from librenms_mcp.librenms_client import LibreNMSClient
from librenms_mcp.utils import paginate_list


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
        List available health graphs for a device.

        Args:
            hostname (str): Device hostname or ID.
            limit (int): Maximum number of results to return.
            offset (int): Number of results to skip.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info(f"Getting health graphs for {hostname}...")

            async with LibreNMSClient(config) as client:
                result = await client.get(f"devices/{hostname}/health")
            return paginate_list(result, limit, offset)

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
        Get health data by sensor type for a device.

        Args:
            hostname (str): Device hostname or ID.
            type (str): Sensor type (e.g. temperature, voltage, fanspeed).
            limit (int): Maximum number of results to return.
            offset (int): Number of results to skip.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info(f"Getting {type} health data for {hostname}...")

            async with LibreNMSClient(config) as client:
                result = await client.get(
                    f"devices/{hostname}/health/{quote(type, safe='')}"
                )
            return paginate_list(result, limit, offset)

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
        List all sensors across all devices.

        Args:
            limit (int): Maximum number of results to return.
            offset (int): Number of results to skip.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info("Listing all sensors...")

            async with LibreNMSClient(config) as client:
                result = await client.get("resources/sensors")
            return paginate_list(result, limit, offset, key="sensors")

        except Exception as e:
            await ctx.error(f"Error listing sensors: {e!s}")
            return {"error": str(e)}
