"""
Device checks shared by tools that filter LibreNMS data by hostname.

Several LibreNMS list endpoints cannot tell "no such device" from "no data":

- logs, BGP and device links resolve the hostname with getidbyname() and
  drop the filter when that finds nothing, answering with every device's data;
- availability, outages, health, port security and the graph list answer an
  unknown device with an empty (or generic) result;
- ARP "all" with a device, and the flat inventory, answer an unknown device
  with an empty list; the regular inventory does so for an unknown device ID
  (an unknown hostname gets a bare "Invalid device provided");
- Oxidized filters on the hostname column, so an unknown name (or a device ID)
  gives an empty list.

Each would read as the requested device's data (or its lack of any). Where
LibreNMS would answer with every device's data, tools confirm the device
exists first; where an unknown device can only give an empty or error answer,
they look it up only then (device_error_if_empty), saving a request per call.
"""

from collections.abc import Callable
from typing import Any

from librenms_mcp.librenms_client import LibreNMSClient
from librenms_mcp.utils import error_body


async def lookup_device(
    client: LibreNMSClient, hostname: str
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Look up a device by hostname or ID.

    Args:
        client: The open LibreNMS client.
        hostname: Device hostname or ID.

    Returns:
        tuple: ``(device, None)`` only when LibreNMS answers "ok" with the
        device record; otherwise ``(None, error)`` with an error body such as
        "Device foo does not exist".
    """
    found: Any = await client.get("devices", hostname)
    if isinstance(found, dict) and found.get("status") == "error":
        return None, found
    devices = found.get("devices") if isinstance(found, dict) else None
    if (
        isinstance(found, dict)
        and found.get("status") == "ok"
        and isinstance(devices, list)
        and devices
        and isinstance(devices[0], dict)
    ):
        return devices[0], None
    # Anything else did not come from LibreNMS as expected: an SSO proxy
    # answering 200 with a login page message, a gateway replying with a list,
    # or "ok" without the device record. Fail closed: the filter this check
    # guards cannot be trusted.
    return None, error_body(
        f"Unexpected response when looking up device {hostname!r}: {str(found)[:200]}"
    )


async def device_error_if_empty(
    client: LibreNMSClient,
    hostname: str,
    result: Any,
    key: str,
    proves_device: Callable[[Any], bool] = bool,
) -> Any:
    """Return result, unless it is empty or an error and hostname names no device.

    For endpoints that answer an unknown device with an empty list or an error,
    never with other devices' data: the device is looked up only when the
    answer could mean "no such device".

    Args:
        client: The open LibreNMS client.
        hostname: Device hostname or ID the result was requested for.
        result: The endpoint's response.
        key: The key holding the response's list.
        proves_device: Whether the value under key shows the device exists;
            by default, any non-empty value does.

    Returns:
        The result unchanged, or the lookup's error body.
    """
    if (
        isinstance(result, dict)
        and result.get("status") != "error"
        and proves_device(result.get(key))
    ):
        return result
    _, error = await lookup_device(client, hostname)
    return error or result
