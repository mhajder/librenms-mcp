"""
LibreNMS MCP Server Service Tools
"""

from typing import Annotated
from typing import Any

from fastmcp.server.context import Context
from pydantic import Field

from librenms_mcp.librenms_client import LibreNMSClient
from librenms_mcp.tools.device_check import device_error_if_empty
from librenms_mcp.tools.device_check import lookup_device
from librenms_mcp.utils import error_body
from librenms_mcp.utils import paginate_list


def _flatten_services(result: Any) -> Any:
    """Unwrap LibreNMS's nested services list so pagination sees each service.

    The services endpoints answer ``{"services": [[{...}, {...}]]}``: one list
    per device group, wrapped in an outer list. Paginating that as is would
    page the wrapper (count and total always 1) instead of the services.
    """
    if not isinstance(result, dict):
        return result
    services = result.get("services")
    if isinstance(services, list) and all(
        isinstance(group, list) for group in services
    ):
        return {**result, "services": [svc for group in services for svc in group]}
    return result


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
            int | str | None,
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
        List all services from LibreNMS with optional filters.

        Args:
            state (int, optional): Filter by state (0=Ok, 1=Warning, 2=Critical).
            service_type (str, optional): Filter by service type.
            limit (int): Maximum number of results to return.
            offset (int): Number of results to skip.

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
                result = await client.get("services", params=params or None)
            return paginate_list(
                _flatten_services(result), limit, offset, key="services"
            )

        except Exception as e:
            await ctx.error(f"Error listing services: {e!s}")
            return error_body(str(e))

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
            int | str | None,
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
        Get services for a device from LibreNMS.

        Args:
            hostname (str): Device hostname or ID.
            state (int, optional): Filter by state (0=Ok, 1=Warning, 2=Critical).
            service_type (str, optional): Filter by service type.
            limit (int): Maximum number of results to return.
            offset (int): Number of results to skip.

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
                # An unknown device ID gets an empty list, as if it had none.
                result = await device_error_if_empty(
                    client,
                    hostname,
                    _flatten_services(
                        await client.get("services", hostname, params=params or None)
                    ),
                    "services",
                )
            return paginate_list(result, limit, offset, key="services")

        except Exception as e:
            await ctx.error(f"Error services for {hostname}: {e!s}")
            return error_body(str(e))

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
- ip (optional): Service IP address or hostname to check (defaults to the device's poller target: its overwrite IP if set, else its hostname)
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
                # add_service_for_host does not check the device exists, so an
                # unknown one could get an orphaned service; confirm it first.
                _, error = await lookup_device(client, hostname)
                if error:
                    return error
                if not payload.get("ip"):
                    # LibreNMS answers a service without "ip" with a 500, but
                    # for an empty one Services::addService stores the device's
                    # poller target (its overwrite_ip, else its hostname), as
                    # the web UI does.
                    payload = {**payload, "ip": ""}
                return await client.post("services", hostname, data=payload)

        except Exception as e:
            await ctx.error(f"Error adding service {hostname}: {e!s}")
            return error_body(str(e))

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
                return await client.patch("services", service_id, data=payload)

        except Exception as e:
            await ctx.error(f"Error editing service {service_id}: {e!s}")
            return error_body(str(e))

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
                return await client.delete("services", service_id)

        except Exception as e:
            await ctx.error(f"Error deleting service {service_id}: {e!s}")
            return error_body(str(e))
