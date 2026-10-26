"""
Short hostname resolution for tools that take a device reference.

Agents and people often name a device by its short name ("rtr1") while
LibreNMS stores the FQDN ("rtr1.dc1.example.net"). LibreNMS does not match
short names, so such calls fail with "Device rtr1 does not exist".

ShortHostnameMiddleware swaps a bare short name in a tool's ``hostname`` or
``device`` argument for the stored hostname of the one device it names,
before the tool runs. The tool then sends that hostname everywhere it would
have sent the short name - path, query string and its own device check
(tools/device_check) - so no request carries the unresolved name. Rewriting
request paths instead would miss the query-string filters (bgp_sessions,
arp_search), which LibreNMS drops for an unknown name, answering with every
device's data.

Everything else passes through unchanged: FQDNs, IP addresses and device IDs,
names that match no device (the tools then answer "Device X does not
exist"), and lookups that fail. A name matching several devices is refused
with an error body, since picking one would act on the wrong device.
"""

import logging
from typing import Any
from typing import TypeGuard

import mcp_types as mt
from fastmcp.server.middleware import CallNext
from fastmcp.server.middleware import Middleware
from fastmcp.server.middleware import MiddlewareContext
from fastmcp.tools import ToolResult

from librenms_mcp.librenms_client import LibreNMSClient
from librenms_mcp.models import LibreNMSConfig
from librenms_mcp.tools.name_refs import is_librenms_id
from librenms_mcp.utils import error_body

logger = logging.getLogger(__name__)

# Tool arguments holding an existing device's hostname or ID. device_add takes
# a payload instead, so a new device's hostname is never resolved.
DEVICE_ARGS = ("hostname", "device")


class AmbiguousShortNameError(Exception):
    """A short name that matches several devices; the message lists them."""


def is_short_name(value: Any) -> TypeGuard[str]:
    """Whether value is a bare short name: not empty, not an ID, no dot (FQDN/IP)."""
    return (
        isinstance(value, str)
        and bool(value)
        and not is_librenms_id(value)
        and "." not in value
    )


def pick_unique_device(devices: list[Any], short_name: str) -> dict[str, Any] | None:
    """
    Find the one device whose short name equals short_name, ignoring case.

    The devices search is a substring match, so this re-filters to devices
    whose hostname or sysName, up to the first dot, equals short_name. Only
    device_id, hostname and sysName are read: search results also carry SNMP
    credentials, which must never reach a log or an error message.

    Returns:
        The matching device, or None when no device matches.

    Raises:
        AmbiguousShortNameError: When several devices match.
    """
    target = short_name.casefold()
    matches = [
        d
        for d in devices
        if isinstance(d, dict)
        and target
        in (
            str(d.get("hostname") or "").split(".", 1)[0].casefold(),
            str(d.get("sysName") or "").split(".", 1)[0].casefold(),
        )
    ]
    if len(matches) > 1:
        candidates = ", ".join(
            f"{m.get('hostname')} (ID {m.get('device_id')})" for m in matches
        )
        raise AmbiguousShortNameError(
            f"Short name {short_name!r} matches {len(matches)} devices: "
            f"{candidates}; use the full hostname or the device ID"
        )
    return matches[0] if matches else None


class ShortHostnameMiddleware(Middleware):
    """Resolve short device names in tool arguments to stored hostnames."""

    def __init__(self, config: LibreNMSConfig) -> None:
        self.config = config

    async def on_call_tool(
        self,
        context: MiddlewareContext[mt.CallToolRequestParams],
        call_next: CallNext[mt.CallToolRequestParams, ToolResult],
    ) -> ToolResult:
        args = dict(context.message.arguments or {})
        changed = False
        for key in DEVICE_ARGS:
            name = args.get(key)
            if not is_short_name(name):
                continue
            try:
                hostname = await self._resolve(name)
            except AmbiguousShortNameError as e:
                return ToolResult(structured_content=error_body(str(e)))
            if hostname and hostname != name:
                logger.info(
                    "Resolved short hostname %r -> %r for %s",
                    name,
                    hostname,
                    context.message.name,
                )
                args[key] = hostname
                changed = True
        if changed:
            message = context.message.model_copy(update={"arguments": args})
            context = context.copy(message=message)
        return await call_next(context)

    async def _resolve(self, name: str) -> str | None:
        """Return the stored hostname of the one device named name, or None.

        Raises:
            AmbiguousShortNameError: When several devices have that short name.
        """
        try:
            async with LibreNMSClient(self.config) as client:
                found = await client.get(
                    "devices", params={"type": "hostname", "query": name}
                )
        except Exception:
            # Pass the name through; the tool's own checks report it.
            logger.warning("Short hostname lookup failed for %r", name, exc_info=True)
            return None
        if not isinstance(found, dict) or found.get("status") != "ok":
            return None
        devices = found.get("devices")
        if not isinstance(devices, list):
            return None
        device = pick_unique_device(devices, name)
        hostname = device.get("hostname") if device else None
        return hostname if isinstance(hostname, str) and hostname else None
