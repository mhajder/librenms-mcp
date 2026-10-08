"""
LibreNMS MCP Server Logs Tools
"""

from typing import Annotated
from typing import Any

from fastmcp.server.context import Context
from pydantic import Field

from librenms_mcp.librenms_client import LibreNMSClient
from librenms_mcp.utils import optional_segment

# Parameters shared by the log tools.
HostnameField = Annotated[
    str | None,
    Field(
        default=None,
        description="Device hostname or ID. Omit for entries from all devices.",
    ),
]
StartField = Annotated[
    int,
    Field(
        default=0,
        description="Number of results to skip (offset) for pagination",
        ge=0,
    ),
]
LimitField = Annotated[
    int,
    Field(
        default=100,
        description="Maximum number of results to return",
        ge=1,
    ),
]
FromField = Annotated[
    str | None,
    Field(
        default=None,
        description="Start timestamp filter (Unix timestamp or datetime string)",
    ),
]
ToField = Annotated[
    str | None,
    Field(
        default=None,
        description="End timestamp filter (Unix timestamp or datetime string)",
    ),
]
SortOrderField = Annotated[
    str | None,
    Field(default=None, description="Sort order: ASC or DESC"),
]


async def _list_logs(
    config,
    log_type: str,
    *,
    hostname: str | None,
    start: int,
    limit: int,
    from_ts: str | None,
    to_ts: str | None,
    sortorder: str | None,
) -> dict:
    """Fetch a page from a LibreNMS log endpoint and annotate it with paging info.

    The hostname segment is optional in LibreNMS; leaving it out (None or an
    empty string) returns entries for all devices. A given hostname is looked
    up first, because LibreNMS answers an unknown one with all devices' logs.
    """
    params: dict[str, Any] = {"start": start, "limit": limit}
    if from_ts is not None:
        params["from"] = from_ts
    if to_ts is not None:
        params["to"] = to_ts
    if sortorder is not None:
        params["sortorder"] = sortorder

    host_segment = optional_segment(hostname)
    async with LibreNMSClient(config) as client:
        if host_segment:
            # LibreNMS ignores a hostname it cannot resolve and returns every
            # device's logs, which would read as this device's. Check first.
            device = await client.get("devices", *host_segment)
            if device.get("status") == "error":
                return device
        result = await client.get("logs", log_type, *host_segment, params=params)

    if isinstance(result, dict) and result.get("status") == "ok":
        logs = result.get("logs")
        result["count"] = len(logs) if isinstance(logs, list) else 0
        result["limit"] = limit
        result["start"] = start
    return result


def register_logs_tools(mcp, config):
    """Register LibreNMS logs tools with the MCP server"""
    ##########################
    # Logs Tools
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
        ctx: Context,
        hostname: HostnameField = None,
        start: StartField = 0,
        limit: LimitField = 100,
        from_ts: FromField = None,
        to_ts: ToField = None,
        sortorder: SortOrderField = None,
    ) -> dict:
        """
        Get event logs for a device from LibreNMS.

        Args:
            hostname (str, optional): Device hostname or ID; omit for all devices.
            start (int): Number of results to skip.
            limit (int): Max results.
            from_ts (str, optional): Start timestamp.
            to_ts (str, optional): End timestamp.
            sortorder (str, optional): ASC or DESC.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info(f"Getting event logs for {hostname or 'all devices'}...")
            return await _list_logs(
                config,
                "eventlog",
                hostname=hostname,
                start=start,
                limit=limit,
                from_ts=from_ts,
                to_ts=to_ts,
                sortorder=sortorder,
            )

        except Exception as e:
            await ctx.error(f"Error eventlog {hostname or 'all devices'}: {e!s}")
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
        ctx: Context,
        hostname: HostnameField = None,
        start: StartField = 0,
        limit: LimitField = 100,
        from_ts: FromField = None,
        to_ts: ToField = None,
        sortorder: SortOrderField = None,
    ) -> dict:
        """
        Get syslogs for a device from LibreNMS.

        Args:
            hostname (str, optional): Device hostname or ID; omit for all devices.
            start (int): Number of results to skip.
            limit (int): Max results.
            from_ts (str, optional): Start timestamp.
            to_ts (str, optional): End timestamp.
            sortorder (str, optional): ASC or DESC.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info(f"Getting syslogs for {hostname or 'all devices'}...")
            return await _list_logs(
                config,
                "syslog",
                hostname=hostname,
                start=start,
                limit=limit,
                from_ts=from_ts,
                to_ts=to_ts,
                sortorder=sortorder,
            )

        except Exception as e:
            await ctx.error(f"Error syslog {hostname or 'all devices'}: {e!s}")
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
        ctx: Context,
        hostname: HostnameField = None,
        start: StartField = 0,
        limit: LimitField = 100,
        from_ts: FromField = None,
        to_ts: ToField = None,
        sortorder: SortOrderField = None,
    ) -> dict:
        """
        Get alert logs for a device from LibreNMS.

        Args:
            hostname (str, optional): Device hostname or ID; omit for all devices.
            start (int): Number of results to skip.
            limit (int): Max results.
            from_ts (str, optional): Start timestamp.
            to_ts (str, optional): End timestamp.
            sortorder (str, optional): ASC or DESC.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info(f"Getting alert logs for {hostname or 'all devices'}...")
            return await _list_logs(
                config,
                "alertlog",
                hostname=hostname,
                start=start,
                limit=limit,
                from_ts=from_ts,
                to_ts=to_ts,
                sortorder=sortorder,
            )

        except Exception as e:
            await ctx.error(f"Error alertlog {hostname or 'all devices'}: {e!s}")
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
        ctx: Context,
        start: StartField = 0,
        limit: LimitField = 100,
        from_ts: FromField = None,
        to_ts: ToField = None,
        sortorder: SortOrderField = None,
    ) -> dict:
        """
        Get authentication logs from LibreNMS.

        Auth logs are server-wide rather than per-device, so this takes no hostname.

        Args:
            start (int): Number of results to skip.
            limit (int): Max results.
            from_ts (str, optional): Start timestamp.
            to_ts (str, optional): End timestamp.
            sortorder (str, optional): ASC or DESC.

        Returns:
            dict: The JSON response from the API.
        """
        try:
            await ctx.info("Getting auth logs ...")
            return await _list_logs(
                config,
                "authlog",
                hostname=None,
                start=start,
                limit=limit,
                from_ts=from_ts,
                to_ts=to_ts,
                sortorder=sortorder,
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
        ctx: Context,
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
