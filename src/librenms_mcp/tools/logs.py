"""
LibreNMS MCP Server Logs Tools
"""

from typing import Annotated
from typing import Any

from fastmcp.server.context import Context
from pydantic import Field

from librenms_mcp.librenms_client import LibreNMSClient


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
        ctx: Context,
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
        ctx: Context,
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
        ctx: Context,
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
