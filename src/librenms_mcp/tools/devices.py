"""
LibreNMS MCP Server Device Tools
"""

from typing import Annotated
from typing import Any
from urllib.parse import quote

from fastmcp.server.context import Context
from pydantic import Field

from librenms_mcp.librenms_client import LibreNMSClient


def register_device_tools(mcp, config):
    """Register LibreNMS device tools with the MCP server"""
    ##########################
    # Device Tools
    ##########################

    @mcp.tool(
        tags={"librenms", "devices", "read-only"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def devices_list(
        ctx: Context,
        query: Annotated[
            dict | None,
            Field(
                default=None,
                description="""Query parameters for filtering devices. Examples:
- {"type": "hostname", "query": "router"} - search by hostname substring
- {"type": "os", "query": "linux"} - filter by operating system
- {"type": "location", "query": "datacenter"} - filter by location
- {"type": "up"} or {"type": "down"} - filter by status
- {"limit": 50} - limit number of results
- {"order": "hostname ASC"} - sort results

Valid type values: all, active, ignored, up, down, disabled, os, mac, ipv4, ipv6, location, location_id, hostname, sysName, display, device_id, type, serial, version, hardware, features""",
            ),
        ] = None,
    ) -> dict:
        """
        List devices from LibreNMS with optional filters.

        Args:
            query (dict, optional): Query parameters for filtering. Use "type" to filter
                by category (hostname, os, location, up, down, etc.) and "query" for
                the search term. Can also include "limit" and "order".

        Returns:
            dict: The JSON response from the API containing device list.
        """
        try:
            await ctx.info("Listing devices...")

            async with LibreNMSClient(config) as client:
                return await client.get("devices", params=query)

        except Exception as e:
            await ctx.error(f"Error listing devices: {e!s}")
            return {"error": str(e)}

    @mcp.tool(
        tags={"librenms", "devices", "admin"},
        annotations={
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": False,
        },
    )
    async def device_add(
        payload: Annotated[
            dict,
            Field(
                description="""Device add payload. Required and optional fields:
- hostname (required): Device hostname or IP
- version (optional): SNMP version (v1, v2c, v3). Default: v2c
- community (required for v1/v2c): SNMP community string
- authlevel (required for v3): noAuthNoPriv, authNoPriv, authPriv
- authname (required for v3): SNMPv3 username
- authpass (required for v3 with auth): Authentication password
- authalgo (optional): MD5 or SHA
- cryptopass (required for authPriv): Privacy password
- cryptoalgo (optional): AES or DES
- port (optional): SNMP port (default: 161)
- transport (optional): udp or tcp
- poller_group (optional): Poller group ID
- force_add (optional): Skip ICMP/SNMP checks (true/false)
- ping_fallback (optional): Add as ping-only if SNMP fails"""
            ),
        ],
        ctx: Context,
    ) -> dict:
        """
        Add a new device to LibreNMS.

        Args:
            payload (dict): Device add payload with hostname and SNMP credentials.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info("Adding device...")

            async with LibreNMSClient(config) as client:
                return await client.post("devices", data=payload)

        except Exception as e:
            await ctx.error(f"Error adding device: {e!s}")
            return {"error": str(e)}

    @mcp.tool(
        tags={"librenms", "devices", "read-only"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def device_get(
        hostname: Annotated[str, Field(description="Device hostname")],
        ctx: Context,
    ) -> dict:
        """
        Get device details from LibreNMS by hostname.

        Args:
            hostname (str): Device hostname.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info(f"Getting device {hostname}...")

            async with LibreNMSClient(config) as client:
                return await client.get(f"devices/{hostname}")

        except Exception as e:
            await ctx.error(f"Error getting device {hostname}: {e!s}")
            return {"error": str(e)}

    @mcp.tool(
        tags={"librenms", "devices", "admin"},
        annotations={
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": True,
        },
    )
    async def device_delete(
        hostname: Annotated[str, Field(description="Device hostname to delete")],
        ctx: Context,
    ) -> dict:
        """
        Delete a device from LibreNMS by hostname.

        Args:
            hostname (str): Device hostname to delete.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info(f"Deleting device {hostname}...")

            async with LibreNMSClient(config) as client:
                return await client.delete(f"devices/{hostname}")

        except Exception as e:
            await ctx.error(f"Error deleting device {hostname}: {e!s}")
            return {"error": str(e)}

    @mcp.tool(
        tags={"librenms", "devices", "admin"},
        annotations={
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": True,
        },
    )
    async def device_update(
        hostname: Annotated[str, Field(description="Device hostname or ID")],
        payload: Annotated[
            dict,
            Field(
                description="""Patchable device fields:
- notes: Device notes/comments
- purpose: Device purpose description
- override_sysLocation: true/false to override SNMP location
- location_id: Location ID to assign
- poller_group: Poller group ID
- ignore: 0/1 to ignore device in alerts
- disabled: 0/1 to disable polling
- snmp_disable: 0/1 to disable SNMP polling
- display: Custom display name
- type: Device type classification"""
            ),
        ],
        ctx: Context,
    ) -> dict:
        """
        Update device fields in LibreNMS.

        Args:
            hostname (str): Device hostname or ID.
            payload (dict): Fields to update on the device.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info(f"Updating device {hostname}...")

            # LibreNMS API expects "field" and "data" keys
            fields = list(payload.keys())
            values = list(payload.values())
            if len(fields) == 1:
                api_payload = {"field": fields[0], "data": values[0]}
            else:
                api_payload = {"field": fields, "data": values}

            async with LibreNMSClient(config) as client:
                return await client.patch(f"devices/{hostname}", data=api_payload)

        except Exception as e:
            await ctx.error(f"Error updating device {hostname}: {e!s}")
            return {"error": str(e)}

    @mcp.tool(
        tags={"librenms", "devices", "read-only"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def device_ports(
        ctx: Context,
        hostname: Annotated[str, Field(description="Device hostname or ID")],
        columns: Annotated[
            str | None,
            Field(
                default=None,
                description="Comma-separated list of columns to return (e.g., 'port_id,ifName,ifAlias,ifOperStatus')",
            ),
        ] = None,
    ) -> dict:
        """
        List ports for a device from LibreNMS.

        Args:
            hostname (str): Device hostname or ID.
            columns (str, optional): Comma-separated columns to return.

        Returns:
            dict: The JSON response from the API.
        """
        params: dict[str, Any] = {}
        if columns is not None:
            params["columns"] = columns

        try:
            await ctx.info(f"Listing ports for {hostname}...")

            async with LibreNMSClient(config) as client:
                return await client.get(
                    f"devices/{hostname}/ports", params=params if params else None
                )

        except Exception as e:
            await ctx.error(f"Error listing ports for {hostname}: {e!s}")
            return {"error": str(e)}

    @mcp.tool(
        tags={"librenms", "devices", "read-only"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def device_ports_get(
        hostname: Annotated[str, Field()],
        ifname: Annotated[str, Field(description="Interface name")],
        ctx: Context,
    ) -> dict:
        """
        Get port info for a device by interface name.

        Args:
            hostname (str): Device hostname.
            ifname (str): Interface name.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info(f"Getting port {ifname} on {hostname}...")

            async with LibreNMSClient(config) as client:
                return await client.get(
                    f"devices/{hostname}/ports/{quote(ifname, safe='')}"
                )

        except Exception as e:
            await ctx.error(f"Error getting port {ifname} on {hostname}: {e!s}")
            return {"error": str(e)}

    @mcp.tool(
        tags={"librenms", "devices", "read-only"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def device_availability(
        hostname: Annotated[str, Field()], ctx: Context
    ) -> dict:
        """
        Get device availability from LibreNMS.

        Args:
            hostname (str): Device hostname.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info(f"Getting availability for {hostname}...")

            async with LibreNMSClient(config) as client:
                return await client.get(f"devices/{hostname}/availability")

        except Exception as e:
            await ctx.error(f"Error availability {hostname}: {e!s}")
            return {"error": str(e)}

    @mcp.tool(
        tags={"librenms", "devices", "read-only"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def device_outages(hostname: Annotated[str, Field()], ctx: Context) -> dict:
        """
        Get device outages from LibreNMS.

        Args:
            hostname (str): Device hostname.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info(f"Getting outages for {hostname}...")

            async with LibreNMSClient(config) as client:
                return await client.get(f"devices/{hostname}/outages")

        except Exception as e:
            await ctx.error(f"Error outages {hostname}: {e!s}")
            return {"error": str(e)}

    @mcp.tool(
        tags={"librenms", "devices", "admin"},
        annotations={
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def device_set_maintenance(
        hostname: Annotated[str, Field(description="Device hostname or ID")],
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
        Set device maintenance in LibreNMS.

        Args:
            hostname (str): Device hostname or ID.
            payload (dict): Maintenance payload with duration.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info(f"Setting maintenance for {hostname}...")

            async with LibreNMSClient(config) as client:
                return await client.post(
                    f"devices/{hostname}/maintenance", data=payload
                )

        except Exception as e:
            await ctx.error(f"Error setting maintenance {hostname}: {e!s}")
            return {"error": str(e)}

    ##########################
    # Device Groups
    ##########################

    @mcp.tool(
        tags={"librenms", "device-groups", "read-only", "global-read"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def devicegroups_list(ctx: Context) -> dict:
        """
        List all device groups from LibreNMS.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info("Getting device groups...")

            async with LibreNMSClient(config) as client:
                return await client.get("devicegroups")

        except Exception as e:
            await ctx.error(f"Error listing device groups: {e!s}")
            return {"error": str(e)}

    @mcp.tool(
        tags={"librenms", "device-groups", "admin"},
        annotations={
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": False,
        },
    )
    async def devicegroup_add(
        payload: Annotated[
            dict,
            Field(
                description="""Device group payload fields:
- name (required): Group name
- type (required): "static" or "dynamic"
- desc (optional): Group description
- rules (required if dynamic): Dynamic group rule builder JSON
- devices (required if static): Array of device IDs

Example static group:
{"name": "Routers", "type": "static", "devices": [1, 2, 3]}

Example dynamic group:
{"name": "Linux Servers", "type": "dynamic", "rules": {"condition": "AND", "rules": [{"field": "os", "operator": "equal", "value": "linux"}]}}"""
            ),
        ],
        ctx: Context,
    ) -> dict:
        """
        Add a new device group to LibreNMS.

        Args:
            payload (dict): Device group definition with name, type, and devices/rules.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info("Creating/updating device group...")

            async with LibreNMSClient(config) as client:
                return await client.post("devicegroups", data=payload)

        except Exception as e:
            await ctx.error(f"Error adding device group: {e!s}")
            return {"error": str(e)}

    @mcp.tool(
        tags={"librenms", "device-groups", "admin"},
        annotations={
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": True,
        },
    )
    async def devicegroup_update(
        name: Annotated[str, Field(description="Device group name")],
        payload: Annotated[
            dict,
            Field(
                description="""Patchable fields:
- name: New group name
- type: "static" or "dynamic"
- desc: Group description
- rules: Dynamic group rules (for dynamic groups)
- devices: Array of device IDs (for static groups)"""
            ),
        ],
        ctx: Context,
    ) -> dict:
        """
        Update a device group in LibreNMS.

        Args:
            name (str): Device group name.
            payload (dict): Fields to update.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info(f"Updating device group {name}...")

            async with LibreNMSClient(config) as client:
                return await client.patch(f"devicegroups/{name}", data=payload)

        except Exception as e:
            await ctx.error(f"Error updating device group {name}: {e!s}")
            return {"error": str(e)}

    @mcp.tool(
        tags={"librenms", "device-groups", "admin"},
        annotations={
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": True,
        },
    )
    async def devicegroup_delete(
        name: Annotated[str, Field(description="Device group name to delete")],
        ctx: Context,
    ) -> dict:
        """
        Delete a device group from LibreNMS by name.

        Args:
            name (str): Device group name to delete.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info(f"Deleting device group {name}...")

            async with LibreNMSClient(config) as client:
                return await client.delete(f"devicegroups/{name}")

        except Exception as e:
            await ctx.error(f"Error deleting device group {name}: {e!s}")
            return {"error": str(e)}

    @mcp.tool(
        tags={"librenms", "device-groups", "read-only", "global-read"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def devicegroup_devices(
        ctx: Context,
        name: Annotated[str, Field(description="Device group name")],
        full: Annotated[
            bool | None,
            Field(
                default=None,
                description="Set to true to get complete device data instead of just IDs",
            ),
        ] = None,
    ) -> dict:
        """
        List devices in a device group from LibreNMS.

        Args:
            name (str): Device group name.
            full (bool, optional): If true, returns full device details.

        Returns:
            dict: The JSON response from the API.
        """
        params: dict[str, Any] = {}
        if full:
            params["full"] = 1

        try:
            await ctx.info(f"Listing devices in group {name}...")

            async with LibreNMSClient(config) as client:
                return await client.get(
                    f"devicegroups/{name}", params=params if params else None
                )

        except Exception as e:
            await ctx.error(f"Error listing devices in group {name}: {e!s}")
            return {"error": str(e)}

    @mcp.tool(
        tags={"librenms", "device-groups", "admin"},
        annotations={
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": True,
        },
    )
    async def devicegroup_set_maintenance(
        name: Annotated[str, Field(description="Device group name")],
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
        Set maintenance for a device group in LibreNMS.

        Args:
            name (str): Device group name.
            payload (dict): Maintenance payload with duration.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info(f"Setting maintenance for group {name}...")

            async with LibreNMSClient(config) as client:
                return await client.post(
                    f"devicegroups/{name}/maintenance", data=payload
                )

        except Exception as e:
            await ctx.error(f"Error setting maintenance for group {name}: {e!s}")
            return {"error": str(e)}

    @mcp.tool(
        tags={"librenms", "device-groups", "admin"},
        annotations={
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": False,
        },
    )
    async def devicegroup_add_devices(
        name: Annotated[str, Field(description="Device group name")],
        payload: Annotated[
            dict,
            Field(
                description='Array of device IDs to add. Format: {"devices": [1, 2, 3]}'
            ),
        ],
        ctx: Context,
    ) -> dict:
        """
        Add devices to a device group in LibreNMS.

        Args:
            name (str): Device group name.
            payload (dict): Device IDs to add as {"devices": [...]}.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info(f"Adding devices to group {name}...")

            async with LibreNMSClient(config) as client:
                return await client.post(f"devicegroups/{name}/devices", data=payload)

        except Exception as e:
            await ctx.error(f"Error adding devices to group {name}: {e!s}")
            return {"error": str(e)}

    @mcp.tool(
        tags={"librenms", "device-groups", "admin"},
        annotations={
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": False,
        },
    )
    async def devicegroup_remove_devices(
        name: Annotated[str, Field(description="Device group name")],
        payload: Annotated[
            dict,
            Field(
                description='Array of device IDs to remove. Format: {"devices": [1, 2, 3]}'
            ),
        ],
        ctx: Context,
    ) -> dict:
        """
        Remove devices from a device group in LibreNMS.

        Args:
            name (str): Device group name.
            payload (dict): Device IDs to remove as {"devices": [...]}.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info(f"Removing devices from group {name}...")

            async with LibreNMSClient(config) as client:
                return await client.delete(f"devicegroups/{name}/devices", data=payload)

        except Exception as e:
            await ctx.error(f"Error removing devices from group {name}: {e!s}")
            return {"error": str(e)}

    ##########################
    # Additional Device Tools
    ##########################

    @mcp.tool(
        tags={"librenms", "devices"},
        annotations={
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": False,
        },
    )
    async def device_discover(
        hostname: Annotated[str, Field(description="Device hostname or ID")],
        ctx: Context,
    ) -> dict:
        """
        Trigger device rediscovery in LibreNMS.

        Args:
            hostname (str): Device hostname or ID.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info(f"Triggering discovery for {hostname}...")

            async with LibreNMSClient(config) as client:
                return await client.get(f"devices/{hostname}/discover")

        except Exception as e:
            await ctx.error(f"Error triggering discovery for {hostname}: {e!s}")
            return {"error": str(e)}

    @mcp.tool(
        tags={"librenms", "devices"},
        annotations={
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": True,
        },
    )
    async def device_rename(
        hostname: Annotated[str, Field(description="Current device hostname or ID")],
        new_hostname: Annotated[str, Field(description="New hostname for the device")],
        ctx: Context,
    ) -> dict:
        """
        Rename a device in LibreNMS.

        Args:
            hostname (str): Current device hostname or ID.
            new_hostname (str): New hostname.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info(f"Renaming device {hostname} to {new_hostname}...")

            async with LibreNMSClient(config) as client:
                return await client.patch(f"devices/{hostname}/rename/{new_hostname}")

        except Exception as e:
            await ctx.error(f"Error renaming device {hostname}: {e!s}")
            return {"error": str(e)}

    @mcp.tool(
        tags={"librenms", "devices", "read-only"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def device_maintenance_status(
        hostname: Annotated[str, Field(description="Device hostname or ID")],
        ctx: Context,
    ) -> dict:
        """
        Check if a device is currently in maintenance mode.

        Args:
            hostname (str): Device hostname or ID.

        Returns:
            dict: The JSON response with maintenance status.
        """
        try:
            await ctx.info(f"Checking maintenance status for {hostname}...")

            async with LibreNMSClient(config) as client:
                return await client.get(f"devices/{hostname}/maintenance")

        except Exception as e:
            await ctx.error(f"Error checking maintenance status for {hostname}: {e!s}")
            return {"error": str(e)}

    @mcp.tool(
        tags={"librenms", "devices", "read-only"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def device_vlans(
        hostname: Annotated[str, Field(description="Device hostname or ID")],
        ctx: Context,
    ) -> dict:
        """
        Get VLANs configured on a specific device.

        Args:
            hostname (str): Device hostname or ID.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info(f"Getting VLANs for {hostname}...")

            async with LibreNMSClient(config) as client:
                return await client.get(f"devices/{hostname}/vlans")

        except Exception as e:
            await ctx.error(f"Error getting VLANs for {hostname}: {e!s}")
            return {"error": str(e)}

    @mcp.tool(
        tags={"librenms", "devices", "read-only"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def device_links(
        hostname: Annotated[str, Field(description="Device hostname or ID")],
        ctx: Context,
    ) -> dict:
        """
        Get network links for a specific device.

        Args:
            hostname (str): Device hostname or ID.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info(f"Getting links for {hostname}...")

            async with LibreNMSClient(config) as client:
                return await client.get(f"devices/{hostname}/links")

        except Exception as e:
            await ctx.error(f"Error getting links for {hostname}: {e!s}")
            return {"error": str(e)}

    @mcp.tool(
        tags={"librenms", "devices"},
        annotations={
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": False,
        },
    )
    async def device_eventlog_add(
        hostname: Annotated[str, Field(description="Device hostname or ID")],
        payload: Annotated[
            dict,
            Field(
                description="""Event log entry payload:
- text (required): Event message text
- type (optional): Event type/category
- severity (optional): Severity level (1-5)"""
            ),
        ],
        ctx: Context,
    ) -> dict:
        """
        Add a custom event log entry for a device.

        Args:
            hostname (str): Device hostname or ID.
            payload (dict): Event log entry with message.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info(f"Adding event log entry for {hostname}...")

            async with LibreNMSClient(config) as client:
                return await client.post(f"devices/{hostname}/eventlog", data=payload)

        except Exception as e:
            await ctx.error(f"Error adding event log for {hostname}: {e!s}")
            return {"error": str(e)}
