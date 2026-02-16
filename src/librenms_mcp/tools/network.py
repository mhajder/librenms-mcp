"""
LibreNMS MCP Server Network Tools
"""

from typing import Annotated
from typing import Any

from fastmcp.server.context import Context
from pydantic import Field

from librenms_mcp.librenms_client import LibreNMSClient


def register_network_tools(mcp, config):
    """Register LibreNMS network tools with the MCP server"""
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
        ctx: Context,
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
        ctx: Context,
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
        bgp_id: Annotated[int, Field(ge=1)], ctx: Context
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
        ctx: Context,
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
    async def routing_ip_addresses(ctx: Context) -> dict:
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
    async def switching_vlans(ctx: Context) -> dict:
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
    async def switching_links(ctx: Context) -> dict:
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
        ctx: Context,
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
    async def ospf_list(ctx: Context) -> dict:
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
    async def ospf_ports(ctx: Context) -> dict:
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
    async def vrf_list(ctx: Context) -> dict:
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
