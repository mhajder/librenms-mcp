"""
Port lookups shared by tools that address a port by interface name.
"""

from collections.abc import Awaitable
from collections.abc import Callable
from typing import TypeVar

from fastmcp.exceptions import ToolError

from librenms_mcp.librenms_client import LibreNMSClient
from librenms_mcp.librenms_client import LibreNMSHTTPError

T = TypeVar("T")


class PortFallbackError(RuntimeError):
    """Both the by-name request and the port-ID fallback failed.

    The message keeps both failures: the first usually names the real problem
    (a proxy, a wrong LIBRENMS_URL), the second explains why the retry did not
    help.
    """

    def __init__(self, by_name_error: Exception, fallback_error: Exception) -> None:
        super().__init__(
            f"{by_name_error!s}; the lookup by port ID also failed: {fallback_error!s}"
        )


def should_retry_by_port_id(error: LibreNMSHTTPError, ifname: str) -> bool:
    """Whether a by-name port request failed in a way the port-ID route avoids.

    An interface name travels in the URL, and names like 'Te2/7' carry an
    encoded slash. Proxies that reject it answer 404 before LibreNMS sees the
    request (Apache and nginx with 404, Tomcat and newer Traefik with 400);
    proxies that decode it leave LibreNMS with an extra path segment, which it
    answers with a 500 (or, on some versions, a route 404). So a 400, 404 or
    500 is retried when the name has a slash, or when the error did not come
    from LibreNMS at all. Auth errors (401/403) are never retried, and neither
    is a LibreNMS "not found" for a plain name: those are real answers.
    """
    if error.status_code not in (400, 404, 500):
        return False
    return "/" in ifname or not error.from_librenms


async def resolve_port_id(client: LibreNMSClient, hostname: str, ifname: str) -> int:
    """Look up the numeric port ID behind a device hostname and interface name.

    Routes keyed by port ID avoid putting the interface name in the URL, which
    matters for names like 'Te2/7' behind proxies that reject an encoded slash.
    The name is matched exactly as given (path parts are not stripped either),
    then case-insensitively.
    """
    result = await client.get(
        "devices",
        hostname,
        "ports",
        params={"columns": "port_id,ifName"},
    )
    if result.get("status") == "error":
        raise ToolError(
            f"Could not list ports on {hostname}: {result.get('message', result)}"
        )
    ports = result.get("ports") or []
    # Exact name as given, then case-insensitive. Each stage must match
    # exactly one port: stacked switches can report the same ifName twice,
    # and a silent pick would show another port's data.
    stages: list[tuple[Callable[[str], str], str]] = [
        (str, ifname),
        (str.casefold, ifname.casefold()),
    ]
    for normalize, wanted in stages:
        matches = [
            port for port in ports if normalize(str(port.get("ifName", ""))) == wanted
        ]
        if len(matches) == 1:
            return int(matches[0]["port_id"])
        if matches:
            raise ToolError(_ambiguous(ifname, hostname, matches))
    raise ToolError(f"No interface named '{ifname}' found on {hostname}.")


def _ambiguous(ifname: str, hostname: str, matches: list[dict]) -> str:
    listed = ", ".join(
        f"{port.get('ifName')!r} (port_id {port.get('port_id')})"
        for port in sorted(matches, key=lambda port: str(port.get("ifName")))
    )
    return (
        f"Interface name '{ifname}' is ambiguous on {hostname}: {listed}. "
        "Use port_group_graph or the port tools with a port ID instead."
    )


async def with_port_id_fallback(
    client: LibreNMSClient,
    hostname: str,
    ifname: str,
    by_name: Callable[[], Awaitable[T]],
    by_id: Callable[[int], Awaitable[T]],
    log: Callable[[str], Awaitable[object]] | None = None,
) -> T:
    """Run a by-name port request, retrying through the port-ID route if needed.

    Args:
        client: The open LibreNMS client.
        hostname: Device hostname or ID.
        ifname: Interface name used by the by-name request.
        by_name: Performs the request that puts ifname in the URL. It must
            raise LibreNMSHTTPError on failure (get_raw does; pass
            raise_for_status=True to get).
        by_id: Performs the equivalent request for a port ID.
        log: Receives a progress message before the retry, e.g. ctx.info.

    Raises:
        LibreNMSHTTPError: The by-name error, when it is not worth retrying.
        PortFallbackError: When the port-ID fallback fails as well.
    """
    try:
        return await by_name()
    except LibreNMSHTTPError as by_name_error:
        if not should_retry_by_port_id(by_name_error, ifname):
            raise
        if log is not None:
            await log(
                f"Request for interface '{ifname}' failed ({by_name_error!s}); "
                "retrying by port ID..."
            )
        try:
            port_id = await resolve_port_id(client, hostname, ifname)
            return await by_id(port_id)
        except Exception as fallback_error:
            raise PortFallbackError(by_name_error, fallback_error) from fallback_error
