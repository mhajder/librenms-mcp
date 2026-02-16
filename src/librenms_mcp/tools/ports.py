"""
LibreNMS MCP Server Port Tools
"""

from typing import Annotated

from fastmcp.server.context import Context
from pydantic import Field

from librenms_mcp.librenms_client import LibreNMSClient


def register_port_tools(mcp, config):
    """Register LibreNMS port tools with the MCP server"""
    ##########################
    # Port Tools
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
        ctx: Context,
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
        ctx: Context,
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
        ctx: Context,
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
        ctx: Context,
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
    async def port_get(port_id: Annotated[int, Field(ge=1)], ctx: Context) -> dict:
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
    async def port_ip_info(port_id: Annotated[int, Field(ge=1)], ctx: Context) -> dict:
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
        port_id: Annotated[int, Field(ge=1)], ctx: Context
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
        port_id: Annotated[int, Field(ge=1)], ctx: Context
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
        ctx: Context,
        port_id: Annotated[int, Field(ge=1, description="Port ID")],
        payload: Annotated[
            dict,
            Field(
                description='Port description payload. Format: {"description": "new description"}'
            ),
        ],
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
    async def port_groups_list(ctx: Context) -> dict:
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
        ctx: Context,
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
        name: Annotated[str, Field(description="Port group name")], ctx: Context
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
        ctx: Context,
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
        ctx: Context,
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
