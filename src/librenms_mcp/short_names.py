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

A device whose stored hostname is the name itself wins over short-name
matches, so turning this on never breaks a call that already worked. The
name is stripped first, as the query-filter tools (blank_to_none) and
LibreNMS (TrimStrings) do.

Everything else passes through unchanged: FQDNs, IP addresses and device IDs,
names that match no device (the tools then answer "Device X does not
exist"), and lookups that fail. A name matching several devices is refused
with a tool error, since picking one would act on the wrong device.
"""

import logging
from typing import Any
from typing import TypeGuard

import mcp_types as mt
from fastmcp.exceptions import ToolError
from fastmcp.server.middleware import CallNext
from fastmcp.server.middleware import Middleware
from fastmcp.server.middleware import MiddlewareContext
from fastmcp.tools import ToolResult

from librenms_mcp.librenms_client import LibreNMSClient
from librenms_mcp.models import LibreNMSConfig
from librenms_mcp.tools.name_refs import is_librenms_id
from librenms_mcp.utils import unique_match

logger = logging.getLogger(__name__)

# Tool arguments holding an existing device's hostname or ID. device_add takes
# a payload instead, so a new device's hostname is never resolved.
DEVICE_ARGS = ("hostname", "device")


class AmbiguousShortNameError(Exception):
    """A short name that matches several devices; the message lists them."""


def is_short_name(value: Any) -> TypeGuard[str]:
    """Whether value is a bare short name: not empty, not an ID, no dot or colon.

    A dot rules out FQDNs and IPv4 addresses, a colon IPv6 addresses (which
    can have no dot, like ``::1``). Callers strip the value first.
    """
    return (
        isinstance(value, str)
        and bool(value)
        and not is_librenms_id(value)
        and "." not in value
        and ":" not in value
    )


def _first_label(value: Any) -> str:
    """A hostname or sysName up to its first dot, casefolded ("" when unset)."""
    return str(value or "").split(".", 1)[0].casefold()


def pick_unique_device(devices: list[Any], short_name: str) -> dict[str, Any] | None:
    """
    Find the one device that short_name names.

    A device whose stored hostname is short_name (exactly, then ignoring
    case) wins, as LibreNMS itself would match it. Otherwise the searches,
    one of them a substring match, are re-filtered to devices whose hostname
    or sysName, up to the first dot, equals short_name, ignoring case. Only
    device_id, hostname and sysName are read: search results also carry SNMP
    credentials, which must never reach a log or an error message.

    Returns:
        The matching device, or None when no device matches.

    Raises:
        AmbiguousShortNameError: When several devices match.
    """
    candidates = [d for d in devices if isinstance(d, dict)]
    exact, matches = unique_match(candidates, "hostname", short_name)
    if exact:
        return exact
    if not matches:
        target = short_name.casefold()
        matches = [
            d
            for d in candidates
            if target
            in (_first_label(d.get("hostname")), _first_label(d.get("sysName")))
        ]
    if len(matches) > 1:
        listed = ", ".join(
            f"{m.get('hostname')} (ID {m.get('device_id')})" for m in matches
        )
        raise AmbiguousShortNameError(
            f"Short name {short_name!r} matches {len(matches)} devices: "
            f"{listed}; use the full hostname or the device ID"
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
            value = args.get(key)
            name = value.strip() if isinstance(value, str) else value
            if not is_short_name(name):
                continue
            try:
                hostname = await self._resolve(name)
            except AmbiguousShortNameError as e:
                # A tool error (isError), like the tools' other failures; an
                # error body would read as a successful call, and as an empty
                # one for the graph tools, which return an image.
                raise ToolError(str(e)) from e
            if hostname and hostname != value:
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

        Searches hostnames (a substring match) and sysNames (LibreNMS matches
        those exactly), so a device added by IP is found by its sysName. If
        either search fails, the name passes through: half the candidates
        could hide an ambiguity.

        Raises:
            AmbiguousShortNameError: When several devices have that short name.
        """
        devices: dict[Any, dict[str, Any]] = {}
        try:
            async with LibreNMSClient(self.config) as client:
                for search_type in ("hostname", "sysName"):
                    found = await client.get(
                        "devices", params={"type": search_type, "query": name}
                    )
                    if not isinstance(found, dict) or found.get("status") != "ok":
                        return None
                    hits = found.get("devices")
                    if not isinstance(hits, list):
                        return None
                    for d in hits:
                        if isinstance(d, dict):
                            devices.setdefault(d.get("device_id") or id(d), d)
        except Exception:
            # Pass the name through; the tool's own checks report it.
            logger.warning("Short hostname lookup failed for %r", name, exc_info=True)
            return None
        device = pick_unique_device(list(devices.values()), name)
        hostname = device.get("hostname") if device else None
        return hostname if isinstance(hostname, str) and hostname else None
