"""
LibreNMS MCP Server Service Tools
"""

from typing import Annotated
from typing import Any

from fastmcp.server.context import Context
from pydantic import Field

from librenms_mcp.librenms_client import LibreNMSClient


def register_service_tools(mcp, config):
    """Register LibreNMS service tools with the MCP server"""
    ##########################
    # Service Tools
    ##########################

    @mcp.tool(
        tags={"librenms", "services", "read-only", "global-read"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def services_list(
        ctx: Context,
        state: Annotated[
            int | None,
            Field(
                default=None, description="Filter by state: 0=Ok, 1=Warning, 2=Critical"
            ),
        ] = None,
        service_type: Annotated[
            str | None,
            Field(
                default=None, description="Filter by service type (SQL LIKE pattern)"
            ),
        ] = None,
    ) -> dict:
        """
        List all services from LibreNMS with optional filters.

        Args:
            state (int, optional): Filter by state (0=Ok, 1=Warning, 2=Critical).
            service_type (str, optional): Filter by service type.

        Returns:
            dict: The JSON response from the API.
        """
        params: dict[str, Any] = {}
        if state is not None:
            params["state"] = state
        if service_type is not None:
            params["type"] = service_type

        try:
            await ctx.info("Listing services...")

            async with LibreNMSClient(config) as client:
                return await client.get("services", params=params if params else None)

        except Exception as e:
            await ctx.error(f"Error listing services: {e!s}")
            return {"error": str(e)}

    @mcp.tool(
        tags={"librenms", "services", "read-only", "global-read"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def services_for_device(
        ctx: Context,
        hostname: Annotated[str, Field(description="Device hostname or ID")],
        state: Annotated[
            int | None,
            Field(
                default=None, description="Filter by state: 0=Ok, 1=Warning, 2=Critical"
            ),
        ] = None,
        service_type: Annotated[
            str | None,
            Field(
                default=None, description="Filter by service type (SQL LIKE pattern)"
            ),
        ] = None,
    ) -> dict:
        """
        Get services for a device from LibreNMS.

        Args:
            hostname (str): Device hostname or ID.
            state (int, optional): Filter by state (0=Ok, 1=Warning, 2=Critical).
            service_type (str, optional): Filter by service type.

        Returns:
            dict: The JSON response from the API.
        """
        params: dict[str, Any] = {}
        if state is not None:
            params["state"] = state
        if service_type is not None:
            params["type"] = service_type

        try:
            await ctx.info(f"Getting services for {hostname}...")

            async with LibreNMSClient(config) as client:
                return await client.get(
                    f"services/{hostname}", params=params if params else None
                )

        except Exception as e:
            await ctx.error(f"Error services for {hostname}: {e!s}")
            return {"error": str(e)}

    @mcp.tool(
        tags={"librenms", "services", "admin"},
        annotations={
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": False,
        },
    )
    async def service_add(
        hostname: Annotated[str, Field(description="Device hostname or ID")],
        payload: Annotated[
            dict,
            Field(
                description="""Service monitoring payload:
- type (required): Service check type (e.g., "http", "https", "dns", "ping", "smtp", "ssh", "tcp", "icmp")
- ip (optional): Service IP address (defaults to device IP)
- desc (optional): Service description
- param (optional): Check parameters/arguments (service-specific)
- ignore (optional): Exclude from alerts (0/1)

Example: {"type": "http", "desc": "Web Server", "param": "-p 8080 -u /health"}"""
            ),
        ],
        ctx: Context,
    ) -> dict:
        """
        Add a service for a device in LibreNMS.

        Args:
            hostname (str): Device hostname or ID.
            payload (dict): Service definition with type and optional parameters.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info(f"Adding service for {hostname}...")

            async with LibreNMSClient(config) as client:
                return await client.post(f"services/{hostname}", data=payload)

        except Exception as e:
            await ctx.error(f"Error adding service {hostname}: {e!s}")
            return {"error": str(e)}

    @mcp.tool(
        tags={"librenms", "services", "admin"},
        annotations={
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": True,
        },
    )
    async def service_edit(
        service_id: Annotated[int, Field(ge=1, description="Service ID")],
        payload: Annotated[
            dict,
            Field(
                description="""Service patchable fields:
- service_ip: Service IP address
- service_desc: Service description
- service_param: Service check parameters
- service_disabled: 0/1 to enable/disable
- service_ignore: 0/1 to ignore in alerts"""
            ),
        ],
        ctx: Context,
    ) -> dict:
        """
        Edit a service in LibreNMS by service ID.

        Args:
            service_id (int): Service ID.
            payload (dict): Fields to update.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info(f"Editing service {service_id}...")

            async with LibreNMSClient(config) as client:
                return await client.patch(f"services/{service_id}", data=payload)

        except Exception as e:
            await ctx.error(f"Error editing service {service_id}: {e!s}")
            return {"error": str(e)}

    @mcp.tool(
        tags={"librenms", "services", "admin"},
        annotations={
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": True,
        },
    )
    async def service_delete(
        service_id: Annotated[int, Field(ge=1)], ctx: Context
    ) -> dict:
        """
        Delete a service from LibreNMS by service ID.

        Args:
            service_id (int): Service ID.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info(f"Deleting service {service_id}...")

            async with LibreNMSClient(config) as client:
                return await client.delete(f"services/{service_id}")

        except Exception as e:
            await ctx.error(f"Error deleting service {service_id}: {e!s}")
            return {"error": str(e)}
