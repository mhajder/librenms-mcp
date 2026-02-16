"""
LibreNMS MCP Server Bill Tools
"""

from typing import Annotated
from typing import Any

from fastmcp.server.context import Context
from pydantic import Field

from librenms_mcp.librenms_client import LibreNMSClient


def register_bill_tools(mcp, config):
    """Register LibreNMS bill tools with the MCP server"""
    ##########################
    # Bill Tools
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
        ctx: Context,
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
        ctx: Context,
        bill_id: Annotated[int, Field(ge=1, description="Bill ID")],
        period: Annotated[
            str | None, Field(default=None, description="Optional period=previous")
        ] = None,
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
        ctx: Context,
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
        ctx: Context,
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
        ctx: Context,
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
        ctx: Context,
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
        ctx: Context,
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
        ctx: Context,
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
        ctx: Context,
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
