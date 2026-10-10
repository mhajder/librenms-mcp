"""
LibreNMS MCP Server Oxidized Tools
"""

from typing import Annotated

from fastmcp.server.context import Context
from pydantic import Field

from librenms_mcp.librenms_client import LibreNMSClient
from librenms_mcp.tools.device_check import lookup_device
from librenms_mcp.utils import error_body
from librenms_mcp.utils import optional_segment
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
            Field(
                default=None,
                description="Filter by device hostname or ID. Optional. An unknown device returns an error.",
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
        List devices tracked by Oxidized for config backup.

        Args:
            hostname (str, optional): Filter by device hostname or ID.
            limit (int): Maximum number of results to return.
            offset (int): Number of results to skip.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info("Listing Oxidized devices...")

            host = optional_segment(hostname)
            async with LibreNMSClient(config) as client:
                result = await client.get("oxidized", *host)
                if host and result == []:
                    # Oxidized filters on the hostname column, so an unknown
                    # name or a device ID gives an empty list, which reads as
                    # "not backed up". Only then confirm the device, and ask
                    # again by its hostname (an ID is translated this way).
                    device, error = await lookup_device(client, host[0])
                    if error is not None:
                        return error
                    # device is set whenever error is None; "or {}" only
                    # tells the type checker so.
                    stored = str((device or {}).get("hostname") or host[0])
                    if stored != host[0]:
                        result = await client.get("oxidized", stored)
                if isinstance(result, list):
                    result = {"devices": result}
                return paginate_list(result, limit, offset, key="devices")

        except Exception as e:
            await ctx.error(f"Error listing Oxidized devices: {e!s}")
            return error_body(str(e))

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
                result = await client.get("oxidized", "config", hostname)
                if isinstance(result, list):
                    return {"configs": result}
                return result

        except Exception as e:
            await ctx.error(f"Error getting Oxidized config for {hostname}: {e!s}")
            return error_body(str(e))

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
                description="Search string to look for in all stored device configs (e.g. an IP address, interface name, ACL name, or any config keyword). Must not contain '/': LibreNMS cannot route it, so search for a part without it (e.g. '10.0.0.0' instead of '10.0.0.0/24')."
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
        if "/" in search:
            # The route is oxidized/config/search/{searchstring} with no
            # catch-all constraint, and LibreNMS decodes %2F, so a slash splits
            # the term into extra path segments and the request misses the
            # route. Say so instead of returning a confusing 404.
            parts = [part.strip() for part in search.split("/") if part.strip()]
            hint = f", e.g. {parts[0]!r}" if parts else ""
            return error_body(
                "LibreNMS cannot search Oxidized configs for a term containing "
                f"'/' ({search!r}); search for a part without it{hint}."
            )

        try:
            await ctx.info(f"Searching Oxidized configs for '{search}'...")

            async with LibreNMSClient(config) as client:
                result = await client.get("oxidized", "config", "search", search)
                # LibreNMS returns the matches under "nodes".
                if isinstance(result, list):
                    result = {"nodes": result}
                return paginate_list(result, limit, offset, key="nodes")

        except Exception as e:
            await ctx.error(f"Error searching Oxidized configs: {e!s}")
            return error_body(str(e))
