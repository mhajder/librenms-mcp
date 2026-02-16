"""
LibreNMS MCP Server Location Tools
"""

from typing import Annotated
from urllib.parse import quote

from fastmcp.server.context import Context
from pydantic import Field

from librenms_mcp.librenms_client import LibreNMSClient


def register_location_tools(mcp, config):
    """Register LibreNMS location tools with the MCP server"""
    ##########################
    # Location Tools
    ##########################

    @mcp.tool(
        tags={"librenms", "locations", "read-only", "global-read"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def locations_list(ctx: Context) -> dict:
        """
        List locations from LibreNMS.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info("Listing locations...")

            async with LibreNMSClient(config) as client:
                return await client.get("resources/locations")

        except Exception as e:
            await ctx.error(f"Error listing locations: {e!s}")
            return {"error": str(e)}

    @mcp.tool(
        tags={"librenms", "locations", "admin"},
        annotations={
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": False,
        },
    )
    async def location_add(
        payload: Annotated[
            dict,
            Field(
                description="""Location payload fields:
- location (required): Location name
- lat (required): Latitude coordinate (decimal degrees)
- lng (required): Longitude coordinate (decimal degrees)
- fixed_coordinates (optional): 0 = update from device, 1 = fixed (default: 1)"""
            ),
        ],
        ctx: Context,
    ) -> dict:
        """
        Add a new location to LibreNMS.

        Args:
            payload (dict): Location definition with name and coordinates.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info("Adding location...")

            async with LibreNMSClient(config) as client:
                return await client.post("locations", data=payload)

        except Exception as e:
            await ctx.error(f"Error adding location: {e!s}")
            return {"error": str(e)}

    @mcp.tool(
        tags={"librenms", "locations", "admin"},
        annotations={
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": True,
        },
    )
    async def location_delete(
        location: Annotated[str, Field(description="Location identifier")],
        ctx: Context,
    ) -> dict:
        """
        Delete a location from LibreNMS by identifier.

        Args:
            location (str): Location identifier.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info(f"Deleting location {location}...")

            async with LibreNMSClient(config) as client:
                return await client.delete(f"locations/{quote(location, safe='')}")

        except Exception as e:
            await ctx.error(f"Error deleting location {location}: {e!s}")
            return {"error": str(e)}

    @mcp.tool(
        tags={"librenms", "locations", "admin"},
        annotations={
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": True,
        },
    )
    async def location_edit(
        location: Annotated[str, Field(description="Location identifier or name")],
        payload: Annotated[
            dict,
            Field(
                description="""Location patchable fields:
- lat: Latitude coordinate (decimal degrees)
- lng: Longitude coordinate (decimal degrees)"""
            ),
        ],
        ctx: Context,
    ) -> dict:
        """
        Edit a location in LibreNMS.

        Args:
            location (str): Location identifier.
            payload (dict): Fields to update (lat, lng).

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info(f"Editing location {location}...")

            async with LibreNMSClient(config) as client:
                return await client.patch(
                    f"locations/{quote(location, safe='')}", data=payload
                )

        except Exception as e:
            await ctx.error(f"Error editing location {location}: {e!s}")
            return {"error": str(e)}

    @mcp.tool(
        tags={"librenms", "locations", "read-only", "admin"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def location_get(location: Annotated[str, Field()], ctx: Context) -> dict:
        """
        Get a specific location from LibreNMS by identifier.

        Args:
            location (str): Location identifier.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info(f"Getting location {location}...")

            async with LibreNMSClient(config) as client:
                return await client.get(f"location/{quote(location, safe='')}")

        except Exception as e:
            await ctx.error(f"Error getting location {location}: {e!s}")
            return {"error": str(e)}

    ##########################
    # Location Maintenance
    ##########################

    @mcp.tool(
        tags={"librenms", "locations", "admin"},
        annotations={
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def location_set_maintenance(
        location: Annotated[str, Field(description="Location identifier or name")],
        payload: Annotated[
            dict,
            Field(
                description="""Maintenance mode payload:
- duration (required): Duration in "H:i" format (e.g., "02:00" for 2 hours)
- title (optional): Maintenance window title
- notes (optional): Maintenance notes
- start (optional): Start time in "Y-m-d H:i:00" format (default: now)"""
            ),
        ],
        ctx: Context,
    ) -> dict:
        """
        Set maintenance mode for all devices in a location.

        Args:
            location (str): Location identifier or name.
            payload (dict): Maintenance payload with duration.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info(f"Setting maintenance for location {location}...")

            async with LibreNMSClient(config) as client:
                return await client.post(
                    f"locations/{quote(location, safe='')}/maintenance", data=payload
                )

        except Exception as e:
            await ctx.error(f"Error setting maintenance for location {location}: {e!s}")
            return {"error": str(e)}
