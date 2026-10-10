"""
LibreNMS MCP Server Health Tools
"""

from typing import Annotated

from fastmcp.server.context import Context
from pydantic import Field

from librenms_mcp.librenms_client import LibreNMSClient
from librenms_mcp.tools.device_check import device_error_if_empty
from librenms_mcp.tools.device_check import lookup_device
from librenms_mcp.utils import error_body
from librenms_mcp.utils import not_found_if_empty
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
                result = await device_error_if_empty(
                    client,
                    hostname,
                    await client.get("devices", hostname, "health"),
                    "graphs",
                )
            return paginate_list(result, limit, offset)

        except Exception as e:
            await ctx.error(f"Error getting health graphs for {hostname}: {e!s}")
            return error_body(str(e))

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
                result = await device_error_if_empty(
                    client,
                    hostname,
                    await client.get("devices", hostname, "health", type),
                    "graphs",
                )
            return paginate_list(result, limit, offset)

        except Exception as e:
            await ctx.error(f"Error getting {type} health data for {hostname}: {e!s}")
            return error_body(str(e))

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
                result = await client.get(
                    "devices", hostname, "health", type, sensor_id
                )
                sensors = result.get("graphs") if isinstance(result, dict) else None
                if (
                    isinstance(result, dict)
                    and result.get("status") != "error"
                    and isinstance(sensors, list)
                    and sensors
                ):
                    # LibreNMS releases up to at least 25.1 look the sensor up
                    # by its ID alone, ignoring the device and type in the
                    # path, so a row proves neither that the device exists nor
                    # that the sensor is on it, nor that it is of that type.
                    # (Later releases scope it to both.)
                    device, error = await lookup_device(client, hostname)
                    if error is not None:
                        return error
                    device_id = str((device or {}).get("device_id"))
                    # LibreNMS drops a "device_" prefix from the type, and
                    # matches the class case-insensitively (MySQL collation).
                    sensor_class = type.removeprefix("device_").casefold()
                    result = {
                        **result,
                        "graphs": [
                            sensor
                            for sensor in sensors
                            if not isinstance(sensor, dict)
                            or (
                                str(sensor.get("device_id", device_id)) == device_id
                                # Processor, storage and mempool rows have no
                                # sensor_class; their type picks the table.
                                and str(
                                    sensor.get("sensor_class", sensor_class)
                                ).casefold()
                                == sensor_class
                            )
                        ],
                    }
                else:
                    result = await device_error_if_empty(
                        client, hostname, result, "graphs"
                    )
            # With the device confirmed, an empty answer (or another device's
            # sensor, or one of another type) means no such sensor on it.
            return not_found_if_empty(
                result,
                "graphs",
                f"Sensor {sensor_id} ({type}) does not exist on {hostname}",
            )

        except Exception as e:
            await ctx.error(
                f"Error getting sensor {sensor_id} ({type}) for {hostname}: {e!s}"
            )
            return error_body(str(e))

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
                result = await client.get("resources", "sensors")
            return paginate_list(result, limit, offset, key="sensors")

        except Exception as e:
            await ctx.error(f"Error listing sensors: {e!s}")
            return error_body(str(e))
