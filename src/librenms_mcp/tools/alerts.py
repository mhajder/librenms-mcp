"""
LibreNMS MCP Server Alert Tools
"""

from typing import Annotated
from typing import Any

from fastmcp.server.context import Context
from pydantic import Field

from librenms_mcp.librenms_client import LibreNMSClient


def register_alert_tools(mcp, config):
    """Register LibreNMS alert tools with the MCP server"""
    ##########################
    # Alert Tools
    ##########################

    @mcp.tool(
        tags={"librenms", "alert", "read-only", "global-read"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def alerts_get(
        ctx: Context,
        state: Annotated[
            int | None,
            Field(
                default=None,
                description="Filter the alerts by state: 0 = ok, 1 = alert, 2 = ack. Optional.",
            ),
        ] = None,
        severity: Annotated[
            str | None,
            Field(
                default=None,
                description="Filter the alerts by severity. Valid values: ok, warning, critical. Optional.",
            ),
        ] = None,
        alert_rule: Annotated[
            int | None,
            Field(
                default=None, description="Filter alerts by alert rule ID. Optional."
            ),
        ] = None,
        order: Annotated[
            str | None,
            Field(
                default=None,
                description="How to order the output, default is by timestamp (descending). Can be appended by DESC or ASC to change the order. Optional.",
            ),
        ] = None,
    ) -> dict:
        """
        Get alerts from LibreNMS with optional filters.

        Args:
            state (int, optional): Filter the alerts by state: 0 = ok, 1 = alert, 2 = ack.
            severity (str, optional): Filter the alerts by severity. Valid values: ok, warning, critical.
            alert_rule (int, optional): Filter alerts by alert rule ID.
            order (str, optional): How to order the output, default is by timestamp (descending). Can be appended by DESC or ASC.

        Returns:
            dict: The JSON response from the API.
        """
        params: dict[str, Any] = {}
        if state is not None:
            params["state"] = state
        if severity is not None:
            params["severity"] = severity
        if alert_rule is not None:
            params["alert_rule"] = alert_rule
        if order is not None:
            params["order"] = order

        try:
            await ctx.info("Retrieving alerts...")

            async with LibreNMSClient(config) as client:
                return await client.get("alerts", params=params)

        except Exception as e:
            await ctx.error(f"Error retrieving alerts: {e!s}")
            return {"error": str(e)}

    @mcp.tool(
        tags={"librenms", "alert", "read-only", "global-read"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def alert_get_by_id(
        alert_id: Annotated[
            int,
            Field(description="The ID of the alert to retrieve.", ge=1),
        ],
        ctx: Context,
    ) -> dict:
        """
        Get a specific alert from LibreNMS by ID.

        Args:
            alert_id (int): The ID of the alert to retrieve.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info(f"Retrieving alert {alert_id}...")

            async with LibreNMSClient(config) as client:
                return await client.get(f"alerts/{alert_id}")

        except Exception as e:
            await ctx.error(f"Error retrieving alert {alert_id}: {e!s}")
            return {"error": str(e)}

    @mcp.tool(
        tags={"librenms", "alert", "admin"},
        annotations={
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def alert_acknowledge(
        ctx: Context,
        alert_id: Annotated[int, Field(ge=1, description="Alert ID to acknowledge")],
        note: Annotated[
            str | None,
            Field(
                default=None,
                description="Optional note to attach to the acknowledgement",
            ),
        ] = None,
        until_clear: Annotated[
            bool | None,
            Field(
                default=None,
                description="If true, acknowledge until the alert clears. If false, acknowledge only this instance.",
            ),
        ] = None,
    ) -> dict:
        """
        Acknowledge an alert in LibreNMS by ID.

        Args:
            alert_id (int): Alert ID to acknowledge.
            note (str, optional): Note to attach to the acknowledgement.
            until_clear (bool, optional): Whether to acknowledge until the alert clears.

        Returns:
            dict: The JSON response from the API.
        """
        data: dict[str, Any] = {}
        if note is not None:
            data["note"] = note
        if until_clear is not None:
            data["until_clear"] = until_clear

        try:
            await ctx.info(f"Acknowledging alert {alert_id}")

            async with LibreNMSClient(config) as client:
                return await client.put(
                    f"alerts/{alert_id}", data=data if data else None
                )

        except Exception as e:
            await ctx.error(f"Error acknowledging alert {alert_id}: {e!s}")
            return {"error": str(e)}

    @mcp.tool(
        tags={"librenms", "alert", "admin"},
        annotations={
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def alert_unmute(
        alert_id: Annotated[int, Field(ge=1, description="Alert ID to unmute")],
        ctx: Context,
    ) -> dict:
        """
        Unmute an alert in LibreNMS by ID.

        Args:
            alert_id (int): Alert ID to unmute.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info(f"Unmuting alert {alert_id}")

            async with LibreNMSClient(config) as client:
                return await client.put(f"alerts/unmute/{alert_id}")

        except Exception as e:
            await ctx.error(f"Error unmuting alert {alert_id}: {e!s}")
            return {"error": str(e)}

    ##########################
    # Alert Rules
    ##########################

    @mcp.tool(
        tags={"librenms", "alert-rules", "read-only", "global-read"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def alert_rules_list(ctx: Context) -> dict:
        """
        List all alert rules from LibreNMS.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info("Listing all alert rules...")

            async with LibreNMSClient(config) as client:
                return await client.get("rules")

        except Exception as e:
            await ctx.error(f"Error listing rules: {e!s}")
            return {"error": str(e)}

    @mcp.tool(
        tags={"librenms", "alert-rules", "read-only", "global-read"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def alert_rule_get(
        rule_id: Annotated[int, Field(ge=1, description="Alert rule ID")],
        ctx: Context,
    ) -> dict:
        """
        Get details for a specific alert rule by ID.

        Args:
            rule_id (int): Alert rule ID.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info(f"Getting details for rule {rule_id}...")

            async with LibreNMSClient(config) as client:
                return await client.get(f"rules/{rule_id}")

        except Exception as e:
            await ctx.error(f"Error getting rule {rule_id}: {e!s}")
            return {"error": str(e)}

    @mcp.tool(
        tags={"librenms", "alert-rules", "admin"},
        annotations={
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": False,
        },
    )
    async def alert_rule_add(
        payload: Annotated[
            dict,
            Field(
                description="""Alert rule payload fields:
- name (required): Rule name
- builder (required): Rule builder JSON with conditions
- devices (required): Array of device IDs or [-1] for all devices
- severity (required): ok, warning, critical
- count (optional): Trigger threshold count (default: 1)
- delay (optional): Delay before alerting in seconds
- interval (optional): Re-alert interval in seconds
- mute (optional): Mute alerts (true/false)
- invert (optional): Invert rule logic (true/false)
- notes (optional): Rule notes
- disabled (optional): Disable rule (0/1)

Example:
{"name": "Device Down", "severity": "critical", "devices": [-1], "builder": {"condition": "AND", "rules": [...]}}"""
            ),
        ],
        ctx: Context,
    ) -> dict:
        """
        Add a new alert rule to LibreNMS.

        Args:
            payload (dict): Alert rule definition with name, builder, devices, and severity.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info("Adding new alert rule...")

            async with LibreNMSClient(config) as client:
                return await client.post("rules", data=payload)

        except Exception as e:
            await ctx.error(f"Error adding rule: {e!s}")
            return {"error": str(e)}

    @mcp.tool(
        tags={"librenms", "alert-rules", "admin"},
        annotations={
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": True,
        },
    )
    async def alert_rule_edit(
        payload: Annotated[
            dict,
            Field(
                description="""Alert rule edit payload (must include rule_id field):
- rule_id (required): Rule ID to edit
- name: Rule name
- builder: Rule builder JSON with conditions
- devices: Array of device IDs or [-1] for all devices
- severity: ok, warning, critical
- count: Trigger threshold count
- delay: Delay before alerting in seconds
- interval: Re-alert interval in seconds
- mute: Mute alerts (true/false)
- invert: Invert rule logic (true/false)
- notes: Rule notes
- disabled: Disable rule (0/1)"""
            ),
        ],
        ctx: Context,
    ) -> dict:
        """
        Edit an existing alert rule in LibreNMS.

        Args:
            payload (dict): Alert rule payload with id and fields to update.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info(f"Editing rule {payload.get('rule_id')}...")

            async with LibreNMSClient(config) as client:
                return await client.put("rules", data=payload)

        except Exception as e:
            await ctx.error(f"Error editing rule: {e!s}")
            return {"error": str(e)}

    @mcp.tool(
        tags={"librenms", "alert-rules", "admin"},
        annotations={
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": True,
        },
    )
    async def alert_rule_delete(
        rule_id: Annotated[int, Field(ge=1, description="Alert rule ID to delete")],
        ctx: Context,
    ) -> dict:
        """
        Delete an alert rule from LibreNMS by ID.

        Args:
            rule_id (int): Alert rule ID to delete.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info(f"Deleting rule {rule_id}...")

            async with LibreNMSClient(config) as client:
                return await client.delete(f"rules/{rule_id}")

        except Exception as e:
            await ctx.error(f"Error deleting rule {rule_id}: {e!s}")
            return {"error": str(e)}

    ##########################
    # Alert Templates
    ##########################

    @mcp.tool(
        tags={"librenms", "alert-templates", "read-only"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def alert_templates_list(ctx: Context) -> dict:
        """
        List all alert templates from LibreNMS.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info("Listing all alert templates...")

            async with LibreNMSClient(config) as client:
                return await client.get("templates")

        except Exception as e:
            await ctx.error(f"Error listing alert templates: {e!s}")
            return {"error": str(e)}

    @mcp.tool(
        tags={"librenms", "alert-templates", "read-only"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def alert_template_get(
        template_id: Annotated[int, Field(ge=1, description="Alert template ID")],
        ctx: Context,
    ) -> dict:
        """
        Get a specific alert template from LibreNMS by ID.

        Args:
            template_id (int): Alert template ID.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info(f"Getting alert template {template_id}...")

            async with LibreNMSClient(config) as client:
                return await client.get(f"templates/{template_id}")

        except Exception as e:
            await ctx.error(f"Error getting alert template {template_id}: {e!s}")
            return {"error": str(e)}

    @mcp.tool(
        tags={"librenms", "alert-templates"},
        annotations={
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": False,
        },
    )
    async def alert_template_create(
        payload: Annotated[
            dict,
            Field(
                description="""Alert template payload fields:
- name (required): Template name
- template (required): Template body (Laravel Blade syntax)
- title (optional): Alert title template
- title_rec (optional): Recovery title template
- rules (optional): Array of alert rule IDs to associate with this template

Example:
{"name": "Custom Alert", "template": "{{ $alert->title }}\\nSeverity: {{ $alert->severity }}", "title": "Alert: {{ $alert->title }}"}"""
            ),
        ],
        ctx: Context,
    ) -> dict:
        """
        Create a new alert template in LibreNMS.

        Args:
            payload (dict): Alert template definition with name and template body.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info("Creating new alert template...")

            async with LibreNMSClient(config) as client:
                return await client.post("templates", data=payload)

        except Exception as e:
            await ctx.error(f"Error creating alert template: {e!s}")
            return {"error": str(e)}

    @mcp.tool(
        tags={"librenms", "alert-templates"},
        annotations={
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": True,
        },
    )
    async def alert_template_edit(
        payload: Annotated[
            dict,
            Field(
                description="""Alert template edit payload (must include id field):
- id (required): Template ID to edit
- name: Template name
- template: Template body (Laravel Blade syntax)
- title: Alert title template
- title_rec: Recovery title template
- rules: Array of alert rule IDs to associate with this template"""
            ),
        ],
        ctx: Context,
    ) -> dict:
        """
        Edit an existing alert template in LibreNMS.

        Args:
            payload (dict): Alert template payload with id and fields to update.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info(f"Editing alert template {payload.get('id')}...")

            async with LibreNMSClient(config) as client:
                return await client.put("templates", data=payload)

        except Exception as e:
            await ctx.error(f"Error editing alert template: {e!s}")
            return {"error": str(e)}

    @mcp.tool(
        tags={"librenms", "alert-templates"},
        annotations={
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": True,
        },
    )
    async def alert_template_delete(
        template_id: Annotated[
            int, Field(ge=1, description="Alert template ID to delete")
        ],
        ctx: Context,
    ) -> dict:
        """
        Delete an alert template from LibreNMS by ID.

        Args:
            template_id (int): Alert template ID to delete.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info(f"Deleting alert template {template_id}...")

            async with LibreNMSClient(config) as client:
                return await client.delete(f"templates/{template_id}")

        except Exception as e:
            await ctx.error(f"Error deleting alert template {template_id}: {e!s}")
            return {"error": str(e)}
