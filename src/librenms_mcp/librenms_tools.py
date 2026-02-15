"""
LibreNMS MCP Server Tools
"""

from typing import Annotated
from typing import Any
from urllib.parse import quote

from fastmcp import Context
from pydantic import Field

from librenms_mcp.librenms_client import LibreNMSClient


def register_tools(mcp, config):
    """Register LibreNMS tools with the MCP server"""

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
        ctx: Context = None,
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
        ctx: Context = None,
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
        ctx: Context = None,
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
        ctx: Context = None,
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
    async def alert_rules_list(ctx: Context = None) -> dict:
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
        ctx: Context = None,
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
        ctx: Context = None,
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
        ctx: Context = None,
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
        ctx: Context = None,
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
    async def alert_templates_list(ctx: Context = None) -> dict:
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
        ctx: Context = None,
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
        ctx: Context = None,
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
        ctx: Context = None,
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
        ctx: Context = None,
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

    ##########################
    # ARP
    ##########################

    @mcp.tool(
        tags={"librenms", "arp", "read-only", "global-read"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def arp_search(
        query: Annotated[
            str,
            Field(
                description='Search string for ARP entries. Supports IP address, MAC address, CIDR notation, or "all" (use with device parameter for all entries on a device)'
            ),
        ],
        ctx: Context = None,
    ) -> dict:
        """
        Retrieve ARP entries from LibreNMS by search query.

        Args:
            query (str): Search string - IP, MAC, CIDR notation, or "all".

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info(f"Searching ARP entries with query: {query}")

            async with LibreNMSClient(config) as client:
                return await client.get(f"resources/ip/arp/{query}")

        except Exception as e:
            await ctx.error(f"Error ARP search {query}: {e!s}")
            return {"error": str(e)}

    ##########################
    # Bills (read endpoints + write)
    ##########################

    @mcp.tool(
        tags={"librenms", "bills", "read-only"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def bills_list(
        period: Annotated[
            str | None,
            Field(
                default=None,
                description="Optional: previous to list previous period bills",
            ),
        ] = None,
        ref: Annotated[
            str | None, Field(default=None, description="Bill reference filter")
        ] = None,
        custid: Annotated[
            str | None, Field(default=None, description="Customer ID filter")
        ] = None,
        ctx: Context = None,
    ) -> dict:
        """
        List bills from LibreNMS with optional filters.

        Args:
            period (str, optional): List previous period bills.
            ref (str, optional): Bill reference filter.
            custid (str, optional): Customer ID filter.

        Returns:
            dict: The JSON response from the API.
        """
        params: dict[str, Any] = {}
        if period is not None:
            params["period"] = period
        if ref is not None:
            params["ref"] = ref
        if custid is not None:
            params["custid"] = custid

        try:
            await ctx.info("Listing bills...")

            async with LibreNMSClient(config) as client:
                return await client.get("bills", params=params or None)

        except Exception as e:
            await ctx.error(f"Error listing bills: {e!s}")
            return {"error": str(e)}

    @mcp.tool(
        tags={"librenms", "bills", "read-only"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def bill_get(
        bill_id: Annotated[int, Field(ge=1, description="Bill ID")],
        period: Annotated[
            str | None, Field(default=None, description="Optional period=previous")
        ] = None,
        ctx: Context = None,
    ) -> dict:
        """
        Get a specific bill from LibreNMS by ID.

        Args:
            bill_id (int): Bill ID.
            period (str, optional): Optional period=previous.

        Returns:
            dict: The JSON response from the API.
        """
        params: dict[str, Any] = {}
        if period is not None:
            params["period"] = period

        try:
            await ctx.info(f"Getting bill {bill_id}...")
            async with LibreNMSClient(config) as client:
                return await client.get(f"bills/{bill_id}", params=params)

        except Exception as e:
            await ctx.error(f"Error getting bill {bill_id}: {e!s}")
            return {"error": str(e)}

    @mcp.tool(
        tags={"librenms", "bills", "read-only"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def bill_graph(
        bill_id: Annotated[int, Field(ge=1, description="Bill ID")],
        graph_type: Annotated[
            str,
            Field(description="Graph type: bits, monthly, hour, or day"),
        ],
        ctx: Context = None,
    ) -> dict:
        """
        Get bill graph image from LibreNMS.

        Args:
            bill_id (int): Bill ID.
            graph_type (str): Type of graph (bits, monthly, hour, day).

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info(f"Getting bill graph {bill_id}...")

            async with LibreNMSClient(config) as client:
                return await client.get(f"bills/{bill_id}/graphs/{graph_type}")

        except Exception as e:
            await ctx.error(f"Error bill graph {bill_id}: {e!s}")
            return {"error": str(e)}

    @mcp.tool(
        tags={"librenms", "bills", "read-only"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def bill_graph_data(
        bill_id: Annotated[int, Field(ge=1, description="Bill ID")],
        graph_type: Annotated[
            str,
            Field(description="Graph type: bits, monthly, hour, or day"),
        ],
        ctx: Context = None,
    ) -> dict:
        """
        Get bill graph data from LibreNMS.

        Args:
            bill_id (int): Bill ID.
            graph_type (str): Type of graph (bits, monthly, hour, day).

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info(f"Getting bill graph data {bill_id}...")

            async with LibreNMSClient(config) as client:
                return await client.get(f"bills/{bill_id}/graphdata/{graph_type}")

        except Exception as e:
            await ctx.error(f"Error bill graph data {bill_id}: {e!s}")
            return {"error": str(e)}

    @mcp.tool(
        tags={"librenms", "bills", "read-only"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def bill_history(
        bill_id: Annotated[int, Field(ge=1)],
        ctx: Context = None,
    ) -> dict:
        """
        Get bill history from LibreNMS.

        Args:
            bill_id (int): Bill ID.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info(f"Getting bill history {bill_id}...")

            async with LibreNMSClient(config) as client:
                return await client.get(f"bills/{bill_id}/history")

        except Exception as e:
            await ctx.error(f"Error bill history {bill_id}: {e!s}")
            return {"error": str(e)}

    @mcp.tool(
        tags={"librenms", "bills", "read-only"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def bill_history_graph(
        bill_id: Annotated[int, Field(ge=1, description="Bill ID")],
        history_id: Annotated[int, Field(ge=1, description="Bill history ID")],
        graph_type: Annotated[
            str,
            Field(description="Graph type: bits, monthly, hour, or day"),
        ],
        ctx: Context = None,
    ) -> dict:
        """
        Get bill history graph from LibreNMS.

        Args:
            bill_id (int): Bill ID.
            history_id (int): Bill history ID.
            graph_type (str): Type of graph (bits, monthly, hour, day).

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info(f"Getting bill history graph {bill_id}...")

            async with LibreNMSClient(config) as client:
                return await client.get(
                    f"bills/{bill_id}/history/{history_id}/graphs/{graph_type}"
                )

        except Exception as e:
            await ctx.error(f"Error bill history graph {bill_id}: {e!s}")
            return {"error": str(e)}

    @mcp.tool(
        tags={"librenms", "bills", "read-only"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def bill_history_graph_data(
        bill_id: Annotated[int, Field(ge=1, description="Bill ID")],
        history_id: Annotated[int, Field(ge=1, description="Bill history ID")],
        graph_type: Annotated[
            str,
            Field(description="Graph type: bits, monthly, hour, or day"),
        ],
        ctx: Context = None,
    ) -> dict:
        """
        Get bill history graph data from LibreNMS.

        Args:
            bill_id (int): Bill ID.
            history_id (int): Bill history ID.
            graph_type (str): Type of graph (bits, monthly, hour, day).

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info(f"Getting bill history graph data {bill_id}...")

            async with LibreNMSClient(config) as client:
                return await client.get(
                    f"bills/{bill_id}/history/{history_id}/graphdata/{graph_type}"
                )

        except Exception as e:
            await ctx.error(f"Error bill history graph data {bill_id}: {e!s}")
            return {"error": str(e)}

    @mcp.tool(
        tags={"librenms", "bills", "admin"},
        annotations={
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": False,
        },
    )
    async def bill_create_or_update(
        payload: Annotated[
            dict,
            Field(
                description="""Bill payload fields:
- bill_id (for updates only): Existing bill ID
- bill_name (required for create): Bill name
- ports (required for create): Array of port IDs to include
- bill_type (required): "quota" or "cdr" (95th percentile)
- bill_quota (required if quota type): Quota in bytes
- bill_cdr (required if cdr type): Committed data rate
- bill_day (optional): Billing day of month (1-31)
- bill_custid (optional): Customer ID reference
- bill_ref (optional): Billing reference
- bill_notes (optional): Notes"""
            ),
        ],
        ctx: Context = None,
    ) -> dict:
        """
        Create or update a bill in LibreNMS.

        Args:
            payload (dict): Bill payload with name, ports, and billing type.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info("Creating/updating bill...")

            async with LibreNMSClient(config) as client:
                return await client.post("bills", data=payload)

        except Exception as e:
            await ctx.error(f"Error creating/updating bill: {e!s}")
            return {"error": str(e)}

    @mcp.tool(
        tags={"librenms", "bills", "admin"},
        annotations={
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": True,
        },
    )
    async def bill_delete(
        bill_id: Annotated[int, Field(ge=1, description="Bill ID to delete")],
        ctx: Context = None,
    ) -> dict:
        """
        Delete a bill from LibreNMS by ID.

        Args:
            bill_id (int): Bill ID to delete.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info(f"Deleting bill {bill_id}...")

            async with LibreNMSClient(config) as client:
                return await client.delete(f"bills/{bill_id}")

        except Exception as e:
            await ctx.error(f"Error deleting bill {bill_id}: {e!s}")
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
    async def devicegroups_list(ctx: Context = None) -> dict:
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
        ctx: Context = None,
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
        ctx: Context = None,
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
        ctx: Context = None,
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
        name: Annotated[str, Field(description="Device group name")],
        full: Annotated[
            bool | None,
            Field(
                default=None,
                description="Set to true to get complete device data instead of just IDs",
            ),
        ] = None,
        ctx: Context = None,
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
        ctx: Context = None,
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
        ctx: Context = None,
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
        ctx: Context = None,
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
    # Devices (subset of most-used endpoints)
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
        ctx: Context = None,
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
        ctx: Context = None,
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
        ctx: Context = None,
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
        ctx: Context = None,
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
        ctx: Context = None,
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
        hostname: Annotated[str, Field(description="Device hostname or ID")],
        columns: Annotated[
            str | None,
            Field(
                default=None,
                description="Comma-separated list of columns to return (e.g., 'port_id,ifName,ifAlias,ifOperStatus')",
            ),
        ] = None,
        ctx: Context = None,
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
        ctx: Context = None,
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
        hostname: Annotated[str, Field()], ctx: Context = None
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
    async def device_outages(
        hostname: Annotated[str, Field()], ctx: Context = None
    ) -> dict:
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
        ctx: Context = None,
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
    # Inventory
    ##########################
    @mcp.tool(
        tags={"librenms", "inventory", "read-only"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def inventory_device(
        hostname: Annotated[str, Field(description="Device hostname or ID")],
        ent_physical_class: Annotated[
            str | None,
            Field(
                default=None,
                description="Filter by entity physical class (e.g., chassis, module, port, powerSupply, fan, sensor)",
            ),
        ] = None,
        ent_physical_contained_in: Annotated[
            int | None,
            Field(
                default=None,
                description="Filter by parent entity index",
            ),
        ] = None,
        ctx: Context = None,
    ) -> dict:
        """
        Get inventory for a device from LibreNMS.

        Args:
            hostname (str): Device hostname or ID.
            ent_physical_class (str, optional): Filter by entity physical class.
            ent_physical_contained_in (int, optional): Filter by parent entity.

        Returns:
            dict: The JSON response from the API.
        """
        params: dict[str, Any] = {}
        if ent_physical_class is not None:
            params["entPhysicalClass"] = ent_physical_class
        if ent_physical_contained_in is not None:
            params["entPhysicalContainedIn"] = ent_physical_contained_in

        try:
            await ctx.info(f"Getting inventory for {hostname}...")

            async with LibreNMSClient(config) as client:
                return await client.get(
                    f"inventory/{hostname}", params=params if params else None
                )

        except Exception as e:
            await ctx.error(f"Error inventory {hostname}: {e!s}")
            return {"error": str(e)}

    @mcp.tool(
        tags={"librenms", "inventory", "read-only"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def inventory_device_flat(
        hostname: Annotated[str, Field()], ctx: Context = None
    ) -> dict:
        """
        Get flattened inventory for a device from LibreNMS.

        Args:
            hostname (str): Device hostname.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info(f"Getting flattened inventory for {hostname}...")

            async with LibreNMSClient(config) as client:
                return await client.get(f"inventory/{hostname}/all")

        except Exception as e:
            await ctx.error(f"Error inventory flat {hostname}: {e!s}")
            return {"error": str(e)}

    ##########################
    # Locations
    ##########################
    @mcp.tool(
        tags={"librenms", "locations", "read-only", "global-read"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def locations_list(ctx: Context = None) -> dict:
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
        ctx: Context = None,
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
        ctx: Context = None,
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
        ctx: Context = None,
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
    async def location_get(
        location: Annotated[str, Field()], ctx: Context = None
    ) -> dict:
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
    # Logs
    ##########################
    @mcp.tool(
        tags={"librenms", "logs", "read-only", "global-read"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def logs_eventlog(
        hostname: Annotated[str, Field(description="Device hostname or ID")],
        start: Annotated[
            int | None,
            Field(default=None, description="Page number for pagination"),
        ] = None,
        limit: Annotated[
            int | None,
            Field(default=None, description="Maximum number of results to return"),
        ] = None,
        from_ts: Annotated[
            str | None,
            Field(
                default=None,
                description="Start timestamp filter (Unix timestamp or datetime string)",
            ),
        ] = None,
        to_ts: Annotated[
            str | None,
            Field(
                default=None,
                description="End timestamp filter (Unix timestamp or datetime string)",
            ),
        ] = None,
        sortorder: Annotated[
            str | None,
            Field(default=None, description="Sort order: ASC or DESC"),
        ] = None,
        ctx: Context = None,
    ) -> dict:
        """
        Get event logs for a device from LibreNMS.

        Args:
            hostname (str): Device hostname or ID.
            start (int, optional): Page number.
            limit (int, optional): Max results.
            from_ts (str, optional): Start timestamp.
            to_ts (str, optional): End timestamp.
            sortorder (str, optional): ASC or DESC.

        Returns:
            dict: The JSON response from the API.
        """
        params: dict[str, Any] = {}
        if start is not None:
            params["start"] = start
        if limit is not None:
            params["limit"] = limit
        if from_ts is not None:
            params["from"] = from_ts
        if to_ts is not None:
            params["to"] = to_ts
        if sortorder is not None:
            params["sortorder"] = sortorder

        try:
            await ctx.info(f"Getting event logs for {hostname}...")

            async with LibreNMSClient(config) as client:
                return await client.get(
                    f"logs/eventlog/{hostname}", params=params if params else None
                )

        except Exception as e:
            await ctx.error(f"Error eventlog {hostname}: {e!s}")
            return {"error": str(e)}

    @mcp.tool(
        tags={"librenms", "logs", "read-only", "global-read"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def logs_syslog(
        hostname: Annotated[str, Field(description="Device hostname or ID")],
        start: Annotated[
            int | None,
            Field(default=None, description="Page number for pagination"),
        ] = None,
        limit: Annotated[
            int | None,
            Field(default=None, description="Maximum number of results to return"),
        ] = None,
        from_ts: Annotated[
            str | None,
            Field(
                default=None,
                description="Start timestamp filter (Unix timestamp or datetime string)",
            ),
        ] = None,
        to_ts: Annotated[
            str | None,
            Field(
                default=None,
                description="End timestamp filter (Unix timestamp or datetime string)",
            ),
        ] = None,
        sortorder: Annotated[
            str | None,
            Field(default=None, description="Sort order: ASC or DESC"),
        ] = None,
        ctx: Context = None,
    ) -> dict:
        """
        Get syslogs for a device from LibreNMS.

        Args:
            hostname (str): Device hostname or ID.
            start (int, optional): Page number.
            limit (int, optional): Max results.
            from_ts (str, optional): Start timestamp.
            to_ts (str, optional): End timestamp.
            sortorder (str, optional): ASC or DESC.

        Returns:
            dict: The JSON response from the API.
        """
        params: dict[str, Any] = {}
        if start is not None:
            params["start"] = start
        if limit is not None:
            params["limit"] = limit
        if from_ts is not None:
            params["from"] = from_ts
        if to_ts is not None:
            params["to"] = to_ts
        if sortorder is not None:
            params["sortorder"] = sortorder

        try:
            await ctx.info(f"Getting syslogs for {hostname}...")

            async with LibreNMSClient(config) as client:
                return await client.get(
                    f"logs/syslog/{hostname}", params=params if params else None
                )

        except Exception as e:
            await ctx.error(f"Error syslog {hostname}: {e!s}")
            return {"error": str(e)}

    @mcp.tool(
        tags={"librenms", "logs", "read-only", "global-read"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def logs_alertlog(
        hostname: Annotated[str, Field(description="Device hostname or ID")],
        start: Annotated[
            int | None,
            Field(default=None, description="Page number for pagination"),
        ] = None,
        limit: Annotated[
            int | None,
            Field(default=None, description="Maximum number of results to return"),
        ] = None,
        from_ts: Annotated[
            str | None,
            Field(
                default=None,
                description="Start timestamp filter (Unix timestamp or datetime string)",
            ),
        ] = None,
        to_ts: Annotated[
            str | None,
            Field(
                default=None,
                description="End timestamp filter (Unix timestamp or datetime string)",
            ),
        ] = None,
        sortorder: Annotated[
            str | None,
            Field(default=None, description="Sort order: ASC or DESC"),
        ] = None,
        ctx: Context = None,
    ) -> dict:
        """
        Get alert logs for a device from LibreNMS.

        Args:
            hostname (str): Device hostname or ID.
            start (int, optional): Page number.
            limit (int, optional): Max results.
            from_ts (str, optional): Start timestamp.
            to_ts (str, optional): End timestamp.
            sortorder (str, optional): ASC or DESC.

        Returns:
            dict: The JSON response from the API.
        """
        params: dict[str, Any] = {}
        if start is not None:
            params["start"] = start
        if limit is not None:
            params["limit"] = limit
        if from_ts is not None:
            params["from"] = from_ts
        if to_ts is not None:
            params["to"] = to_ts
        if sortorder is not None:
            params["sortorder"] = sortorder

        try:
            await ctx.info(f"Getting alert logs for {hostname}...")

            async with LibreNMSClient(config) as client:
                return await client.get(
                    f"logs/alertlog/{hostname}", params=params if params else None
                )

        except Exception as e:
            await ctx.error(f"Error alertlog {hostname}: {e!s}")
            return {"error": str(e)}

    @mcp.tool(
        tags={"librenms", "logs", "read-only", "global-read"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def logs_authlog(
        start: Annotated[
            int | None,
            Field(default=None, description="Page number for pagination"),
        ] = None,
        limit: Annotated[
            int | None,
            Field(default=None, description="Maximum number of results to return"),
        ] = None,
        from_ts: Annotated[
            str | None,
            Field(
                default=None,
                description="Start timestamp filter (Unix timestamp or datetime string)",
            ),
        ] = None,
        to_ts: Annotated[
            str | None,
            Field(
                default=None,
                description="End timestamp filter (Unix timestamp or datetime string)",
            ),
        ] = None,
        sortorder: Annotated[
            str | None,
            Field(default=None, description="Sort order: ASC or DESC"),
        ] = None,
        ctx: Context = None,
    ) -> dict:
        """
        Get auth logs for a device from LibreNMS.

        Args:
            hostname (str): Device hostname or ID.
            start (int, optional): Page number.
            limit (int, optional): Max results.
            from_ts (str, optional): Start timestamp.
            to_ts (str, optional): End timestamp.
            sortorder (str, optional): ASC or DESC.

        Returns:
            dict: The JSON response from the API.
        """
        params: dict[str, Any] = {}
        if start is not None:
            params["start"] = start
        if limit is not None:
            params["limit"] = limit
        if from_ts is not None:
            params["from"] = from_ts
        if to_ts is not None:
            params["to"] = to_ts
        if sortorder is not None:
            params["sortorder"] = sortorder

        try:
            await ctx.info("Getting auth logs ...")

            async with LibreNMSClient(config) as client:
                return await client.get(
                    "logs/authlog", params=params if params else None
                )

        except Exception as e:
            await ctx.error(f"Error authlog: {e!s}")
            return {"error": str(e)}

    @mcp.tool(
        tags={"librenms", "logs", "admin"},
        annotations={
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": False,
        },
    )
    async def logs_syslogsink(
        payload: Annotated[
            dict[str, Any] | list[dict[str, Any]],
            Field(
                description="JSON syslog message(s) to ingest into LibreNMS syslog storage. Accepts a single object or an array of objects."
            ),
        ],
        ctx: Context = None,
    ) -> dict:
        """
        Add a syslog entry to LibreNMS via API sink.

        Args:
            payload (dict): Syslog message data.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info("Adding syslog sink...")

            async with LibreNMSClient(config) as client:
                return await client.post("syslogsink", data=payload)

        except Exception as e:
            await ctx.error(f"Error syslogsink: {e!s}")
            return {"error": str(e)}

    ##########################
    # Poller Groups
    ##########################
    @mcp.tool(
        tags={"librenms", "poller-groups", "read-only", "admin"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def poller_group_get(
        poller_group: Annotated[
            str, Field(description="Poller group identifier or 'all'")
        ],
        ctx: Context = None,
    ) -> dict:
        """
        Get poller group(s) from LibreNMS.

        Args:
            poller_group (str): Poller group identifier or 'all'.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info(f"Getting poller group {poller_group}...")

            async with LibreNMSClient(config) as client:
                return await client.get(f"poller_group/{poller_group}")

        except Exception as e:
            await ctx.error(f"Error poller group {poller_group}: {e!s}")
            return {"error": str(e)}

    ##########################
    # Port Groups
    ##########################
    @mcp.tool(
        tags={"librenms", "port-groups", "read-only", "global-read"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def port_groups_list(ctx: Context = None) -> dict:
        """
        List port groups from LibreNMS.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info("Getting port groups...")

            async with LibreNMSClient(config) as client:
                return await client.get("port_groups")

        except Exception as e:
            await ctx.error(f"Error listing port groups: {e!s}")
            return {"error": str(e)}

    @mcp.tool(
        tags={"librenms", "port-groups", "admin"},
        annotations={
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": False,
        },
    )
    async def port_group_add(
        payload: Annotated[
            dict,
            Field(
                description="""Port group payload:
- name (required): Port group name
- desc (optional): Port group description"""
            ),
        ],
        ctx: Context = None,
    ) -> dict:
        """
        Add a port group to LibreNMS.

        Args:
            payload (dict): Port group definition with name and optional description.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info("Adding port group...")

            async with LibreNMSClient(config) as client:
                return await client.post("port_groups", data=payload)

        except Exception as e:
            await ctx.error(f"Error adding port group: {e!s}")
            return {"error": str(e)}

    @mcp.tool(
        tags={"librenms", "port-groups", "read-only", "global-read"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def port_group_list_ports(
        name: Annotated[str, Field(description="Port group name")], ctx: Context = None
    ) -> dict:
        """
        List ports in a port group from LibreNMS.

        Args:
            name (str): Port group name.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info(f"Getting ports in group {name}...")

            async with LibreNMSClient(config) as client:
                return await client.get(f"port_groups/{name}")

        except Exception as e:
            await ctx.error(f"Error listing ports in group {name}: {e!s}")
            return {"error": str(e)}

    @mcp.tool(
        tags={"librenms", "port-groups", "admin"},
        annotations={
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": False,
        },
    )
    async def port_group_assign(
        port_group_id: Annotated[int, Field(ge=1, description="Port group ID")],
        payload: Annotated[
            dict,
            Field(description='Port IDs to assign. Format: {"port_ids": [1, 2, 3]}'),
        ],
        ctx: Context = None,
    ) -> dict:
        """
        Assign ports to a port group in LibreNMS.

        Args:
            port_group_id (int): Port group ID.
            payload (dict): Port IDs to assign as {"port_ids": [...]}.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info(f"Assigning ports to group {port_group_id}...")

            async with LibreNMSClient(config) as client:
                return await client.post(
                    f"port_groups/{port_group_id}/assign", data=payload
                )

        except Exception as e:
            await ctx.error(f"Error assigning port group {port_group_id}: {e!s}")
            return {"error": str(e)}

    @mcp.tool(
        tags={"librenms", "port-groups", "admin"},
        annotations={
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": False,
        },
    )
    async def port_group_remove(
        port_group_id: Annotated[int, Field(ge=1, description="Port group ID")],
        payload: Annotated[
            dict,
            Field(description='Port IDs to remove. Format: {"port_ids": [1, 2, 3]}'),
        ],
        ctx: Context = None,
    ) -> dict:
        """
        Remove ports from a port group in LibreNMS.

        Args:
            port_group_id (int): Port group ID.
            payload (dict): Port IDs to remove as {"port_ids": [...]}.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info(f"Removing ports from group {port_group_id}...")

            async with LibreNMSClient(config) as client:
                return await client.post(
                    f"port_groups/{port_group_id}/remove", data=payload
                )

        except Exception as e:
            await ctx.error(f"Error removing port group {port_group_id}: {e!s}")
            return {"error": str(e)}

    ##########################
    # Ports
    ##########################
    @mcp.tool(
        tags={"librenms", "ports", "read-only"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def ports_list(
        query: Annotated[
            dict | None,
            Field(
                default=None,
                description="""Query parameters for filtering ports:
- columns: Comma-separated list of fields to return (e.g., "port_id,ifName,ifAlias")
- device_id: Filter by device ID
- limit: Maximum number of results

Available columns: port_id, device_id, ifDescr, ifName, ifAlias, ifType, ifSpeed, ifOperStatus, ifAdminStatus, etc.""",
            ),
        ] = None,
        ctx: Context = None,
    ) -> dict:
        """
        Get all ports from LibreNMS with optional filters.

        Args:
            query (dict, optional): Filter parameters including columns, device_id, and limit.

        Returns:
            dict: The JSON response from the API containing port list.
        """
        try:
            await ctx.info("Getting all ports...")

            async with LibreNMSClient(config) as client:
                return await client.get("ports", params=query)

        except Exception as e:
            await ctx.error(f"Error listing ports: {e!s}")
            return {"error": str(e)}

    @mcp.tool(
        tags={"librenms", "ports", "read-only"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def ports_search(
        search: Annotated[
            str,
            Field(
                description="Search string - searches ifAlias, ifDescr, and ifName fields"
            ),
        ],
        ctx: Context = None,
    ) -> dict:
        """
        Search ports in LibreNMS by search string.

        Args:
            search (str): Search term to match against ifAlias, ifDescr, ifName.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info(f"Searching ports {search}...")

            async with LibreNMSClient(config) as client:
                return await client.get(f"ports/search/{search}")

        except Exception as e:
            await ctx.error(f"Error searching ports {search}: {e!s}")
            return {"error": str(e)}

    @mcp.tool(
        tags={"librenms", "ports", "read-only"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def ports_search_field(
        field: Annotated[
            str,
            Field(
                description="Field to search: ifAlias, ifDescr, ifName, ifType, etc."
            ),
        ],
        search: Annotated[str, Field(description="Search term")],
        ctx: Context = None,
    ) -> dict:
        """
        Search ports in LibreNMS by specific field.

        Args:
            field (str): Field to search (ifAlias, ifDescr, ifName, etc.).
            search (str): Search term.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info(f"Searching ports {field}={search}...")

            async with LibreNMSClient(config) as client:
                return await client.get(f"ports/search/{field}/{search}")

        except Exception as e:
            await ctx.error(f"Error field search {field}={search}: {e!s}")
            return {"error": str(e)}

    @mcp.tool(
        tags={"librenms", "ports", "read-only"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def ports_search_mac(
        mac: Annotated[
            str,
            Field(
                description="MAC address to search. Accepts multiple formats: aa:bb:cc:dd:ee:ff, aa-bb-cc-dd-ee-ff, aabb.ccdd.eeff, or aabbccddeeff"
            ),
        ],
        ctx: Context = None,
    ) -> dict:
        """
        Search ports in LibreNMS by MAC address.

        Args:
            mac (str): MAC address in any common format.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info(f"Searching ports by MAC address {mac}...")

            async with LibreNMSClient(config) as client:
                return await client.get(f"ports/mac/{mac}")

        except Exception as e:
            await ctx.error(f"Error MAC search {mac}: {e!s}")
            return {"error": str(e)}

    @mcp.tool(
        tags={"librenms", "ports", "read-only"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def port_get(
        port_id: Annotated[int, Field(ge=1)], ctx: Context = None
    ) -> dict:
        """
        Get port info from LibreNMS by port ID.

        Args:
            port_id (int): Port ID.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info(f"Getting port {port_id}...")

            async with LibreNMSClient(config) as client:
                return await client.get(f"ports/{port_id}")

        except Exception as e:
            await ctx.error(f"Error port {port_id}: {e!s}")
            return {"error": str(e)}

    @mcp.tool(
        tags={"librenms", "ports", "read-only"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def port_ip_info(
        port_id: Annotated[int, Field(ge=1)], ctx: Context = None
    ) -> dict:
        """
        Get port IP info from LibreNMS by port ID.

        Args:
            port_id (int): Port ID.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info(f"Getting port IP info {port_id}...")

            async with LibreNMSClient(config) as client:
                return await client.get(f"ports/{port_id}/ip")

        except Exception as e:
            await ctx.error(f"Error port IP {port_id}: {e!s}")
            return {"error": str(e)}

    @mcp.tool(
        tags={"librenms", "ports", "read-only"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def port_transceiver(
        port_id: Annotated[int, Field(ge=1)], ctx: Context = None
    ) -> dict:
        """
        Get port transceiver info from LibreNMS by port ID.

        Args:
            port_id (int): Port ID.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info(f"Getting port transceiver info {port_id}...")

            async with LibreNMSClient(config) as client:
                return await client.get(f"ports/{port_id}/transceiver")

        except Exception as e:
            await ctx.error(f"Error transceiver {port_id}: {e!s}")
            return {"error": str(e)}

    @mcp.tool(
        tags={"librenms", "ports", "read-only"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def port_description_get(
        port_id: Annotated[int, Field(ge=1)], ctx: Context = None
    ) -> dict:
        """
        Get port description from LibreNMS by port ID.

        Args:
            port_id (int): Port ID.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info(f"Getting port description {port_id}...")

            async with LibreNMSClient(config) as client:
                return await client.get(f"ports/{port_id}/description")

        except Exception as e:
            await ctx.error(f"Error description {port_id}: {e!s}")
            return {"error": str(e)}

    @mcp.tool(
        tags={"librenms", "ports"},
        annotations={
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": True,
        },
    )
    async def port_description_update(
        port_id: Annotated[int, Field(ge=1, description="Port ID")],
        payload: Annotated[
            dict,
            Field(
                description='Port description payload. Format: {"description": "new description"}'
            ),
        ],
        ctx: Context = None,
    ) -> dict:
        """
        Update port description in LibreNMS by port ID.

        Args:
            port_id (int): Port ID.
            payload (dict): Description as {"description": "..."}.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info(f"Updating port description {port_id}...")

            async with LibreNMSClient(config) as client:
                return await client.patch(f"ports/{port_id}/description", data=payload)

        except Exception as e:
            await ctx.error(f"Error updating description {port_id}: {e!s}")
            return {"error": str(e)}

    ##########################
    # Routing (subset)
    ##########################
    @mcp.tool(
        tags={"librenms", "routing", "read-only", "global-read"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def bgp_sessions(
        hostname: Annotated[
            str | None,
            Field(default=None, description="Filter by device hostname"),
        ] = None,
        asn: Annotated[
            int | None,
            Field(default=None, description="Filter by local ASN"),
        ] = None,
        remote_asn: Annotated[
            int | None,
            Field(default=None, description="Filter by remote ASN"),
        ] = None,
        remote_address: Annotated[
            str | None,
            Field(default=None, description="Filter by remote IP address"),
        ] = None,
        local_address: Annotated[
            str | None,
            Field(default=None, description="Filter by local IP address"),
        ] = None,
        bgp_descr: Annotated[
            str | None,
            Field(default=None, description="Filter by BGP description (SQL LIKE)"),
        ] = None,
        bgp_state: Annotated[
            str | None,
            Field(default=None, description="Filter by BGP state (e.g., established)"),
        ] = None,
        bgp_adminstate: Annotated[
            str | None,
            Field(
                default=None, description="Filter by admin state (start, stop, running)"
            ),
        ] = None,
        bgp_family: Annotated[
            int | None,
            Field(
                default=None,
                description="Filter by address family: 4 (IPv4) or 6 (IPv6)",
            ),
        ] = None,
        ctx: Context = None,
    ) -> dict:
        """
        List BGP sessions from LibreNMS with optional filters.

        Returns:
            dict: The JSON response from the API.
        """
        params: dict[str, Any] = {}
        if hostname is not None:
            params["hostname"] = hostname
        if asn is not None:
            params["asn"] = asn
        if remote_asn is not None:
            params["remote_asn"] = remote_asn
        if remote_address is not None:
            params["remote_address"] = remote_address
        if local_address is not None:
            params["local_address"] = local_address
        if bgp_descr is not None:
            params["bgp_descr"] = bgp_descr
        if bgp_state is not None:
            params["bgp_state"] = bgp_state
        if bgp_adminstate is not None:
            params["bgp_adminstate"] = bgp_adminstate
        if bgp_family is not None:
            params["bgp_family"] = bgp_family

        try:
            await ctx.info("Listing BGP sessions...")

            async with LibreNMSClient(config) as client:
                return await client.get("bgp", params=params if params else None)

        except Exception as e:
            await ctx.error(f"Error listing BGP sessions: {e!s}")
            return {"error": str(e)}

    @mcp.tool(
        tags={"librenms", "routing", "read-only", "global-read"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def bgp_session_get(
        bgp_id: Annotated[int, Field(ge=1)], ctx: Context = None
    ) -> dict:
        """
        Get BGP session from LibreNMS by ID.

        Args:
            bgp_id (int): BGP session ID.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info(f"Getting BGP session {bgp_id}...")

            async with LibreNMSClient(config) as client:
                return await client.get(f"bgp/{bgp_id}")

        except Exception as e:
            await ctx.error(f"Error BGP session {bgp_id}: {e!s}")
            return {"error": str(e)}

    @mcp.tool(
        tags={"librenms", "routing", "admin"},
        annotations={
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": True,
        },
    )
    async def bgp_session_edit(
        bgp_id: Annotated[int, Field(ge=1, description="BGP session ID")],
        payload: Annotated[
            dict,
            Field(
                description='BGP session payload. Format: {"bgp_descr": "description"}'
            ),
        ],
        ctx: Context = None,
    ) -> dict:
        """
        Edit BGP session in LibreNMS by ID.

        Args:
            bgp_id (int): BGP session ID.
            payload (dict): BGP fields to update.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info(f"Editing BGP session {bgp_id}...")

            async with LibreNMSClient(config) as client:
                return await client.post(f"bgp/{bgp_id}", data=payload)

        except Exception as e:
            await ctx.error(f"Error editing BGP {bgp_id}: {e!s}")
            return {"error": str(e)}

    @mcp.tool(
        tags={"librenms", "routing", "read-only", "global-read"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def routing_ip_addresses(ctx: Context = None) -> dict:
        """
        List all IP addresses from LibreNMS.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info("Listing IP addresses...")

            async with LibreNMSClient(config) as client:
                return await client.get("resources/ip/addresses")

        except Exception as e:
            await ctx.error(f"Error listing IP addresses: {e!s}")
            return {"error": str(e)}

    ##########################
    # Services
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
        ctx: Context = None,
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
        ctx: Context = None,
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
        ctx: Context = None,
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
        ctx: Context = None,
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
        service_id: Annotated[int, Field(ge=1)], ctx: Context = None
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

    ##########################
    # Switching (subset)
    ##########################
    @mcp.tool(
        tags={"librenms", "switching", "read-only"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def switching_vlans(ctx: Context = None) -> dict:
        """
        List all VLANs from LibreNMS.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info("Listing VLANs...")

            async with LibreNMSClient(config) as client:
                return await client.get("resources/vlans")

        except Exception as e:
            await ctx.error(f"Error listing VLANs: {e!s}")
            return {"error": str(e)}

    @mcp.tool(
        tags={"librenms", "switching", "read-only"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def switching_links(ctx: Context = None) -> dict:
        """
        List all links from LibreNMS.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info("Listing links...")

            async with LibreNMSClient(config) as client:
                return await client.get("resources/links")

        except Exception as e:
            await ctx.error(f"Error listing links: {e!s}")
            return {"error": str(e)}

    ##########################
    # System
    ##########################
    @mcp.tool(
        tags={"librenms", "system", "read-only"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def system_info(ctx: Context = None) -> dict:
        """
        Get system info from LibreNMS.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info("Getting system info...")

            async with LibreNMSClient(config) as client:
                return await client.get("system")

        except Exception as e:
            await ctx.error(f"Error system info: {e!s}")
            return {"error": str(e)}

    @mcp.tool(
        tags={"librenms", "system", "read-only"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def ping(ctx: Context = None) -> dict:
        """
        Simple API health check - ping LibreNMS API.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info("Pinging LibreNMS API...")

            async with LibreNMSClient(config) as client:
                return await client.get("ping")

        except Exception as e:
            await ctx.error(f"Error pinging API: {e!s}")
            return {"error": str(e)}

    ##########################
    # Additional Device Endpoints
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
        ctx: Context = None,
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
        ctx: Context = None,
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
        ctx: Context = None,
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
        ctx: Context = None,
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
        ctx: Context = None,
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
        ctx: Context = None,
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

    ##########################
    # FDB (Forwarding Database)
    ##########################
    @mcp.tool(
        tags={"librenms", "fdb", "read-only"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def fdb_lookup(
        mac: Annotated[
            str,
            Field(
                description="MAC address to look up. Accepts multiple formats: aa:bb:cc:dd:ee:ff, aabb.ccdd.eeff, or aabbccddeeff"
            ),
        ],
        ctx: Context = None,
    ) -> dict:
        """
        Look up a MAC address in the forwarding database.

        Args:
            mac (str): MAC address in any common format.

        Returns:
            dict: The JSON response with FDB entries.
        """
        try:
            await ctx.info(f"Looking up FDB entry for MAC {mac}...")

            async with LibreNMSClient(config) as client:
                return await client.get(f"resources/fdb/{mac}")

        except Exception as e:
            await ctx.error(f"Error looking up FDB for {mac}: {e!s}")
            return {"error": str(e)}

    ##########################
    # OSPF
    ##########################
    @mcp.tool(
        tags={"librenms", "routing", "ospf", "read-only", "global-read"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def ospf_list(ctx: Context = None) -> dict:
        """
        List all OSPF instances from LibreNMS.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info("Listing OSPF instances...")

            async with LibreNMSClient(config) as client:
                return await client.get("ospf")

        except Exception as e:
            await ctx.error(f"Error listing OSPF: {e!s}")
            return {"error": str(e)}

    @mcp.tool(
        tags={"librenms", "routing", "ospf", "read-only", "global-read"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def ospf_ports(ctx: Context = None) -> dict:
        """
        List all OSPF ports/interfaces from LibreNMS.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info("Listing OSPF ports...")

            async with LibreNMSClient(config) as client:
                return await client.get("ospf_ports")

        except Exception as e:
            await ctx.error(f"Error listing OSPF ports: {e!s}")
            return {"error": str(e)}

    ##########################
    # VRF
    ##########################
    @mcp.tool(
        tags={"librenms", "routing", "vrf", "read-only"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def vrf_list(ctx: Context = None) -> dict:
        """
        List all VRF (Virtual Routing and Forwarding) instances from LibreNMS.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info("Listing VRF instances...")

            async with LibreNMSClient(config) as client:
                return await client.get("routing/vrf")

        except Exception as e:
            await ctx.error(f"Error listing VRF: {e!s}")
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
        ctx: Context = None,
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

    ##########################
    # Sensors / Health
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
        ctx: Context = None,
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
        ctx: Context = None,
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
        ctx: Context = None,
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
        ctx: Context = None,
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
