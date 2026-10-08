import os
from collections.abc import Callable
from typing import Any
from typing import TypeVar

TRUTHY_VALUES = ("1", "true", "yes", "on")

# MCP_TRANSPORT spellings and the transport each selects. FastMCP calls the
# streamable HTTP transport "streamable-http"; that is accepted as well as the
# shorter "http" this server documents.
TRANSPORT_ALIASES = {
    "stdio": "stdio",
    "sse": "sse",
    "http": "http",
    "streamable-http": "http",
}
VALID_TRANSPORTS = frozenset(TRANSPORT_ALIASES.values())
HTTP_TRANSPORTS = frozenset({"sse", "http"})

# Liveness endpoint served on the HTTP transports and probed by the container
# healthcheck.
HEALTH_PATH = "/health"


def normalize_transport(val: str | None) -> str:
    """
    Resolve an MCP_TRANSPORT value to the transport it selects.

    Case and surrounding whitespace are ignored, and blank means stdio. An
    unknown value is returned as is (normalized) for the caller to reject, so
    that importing the server - as `fastmcp run` does - never fails on it.

    Args:
        val: The raw MCP_TRANSPORT value.

    Returns:
        str: One of VALID_TRANSPORTS, or the normalized unknown value.
    """
    raw = (val or "").strip().lower() or "stdio"
    return TRANSPORT_ALIASES.get(raw, raw)


def http_host_from_env() -> str:
    """
    Return MCP_HTTP_HOST, stripped and without IPv6 brackets, defaulting to
    loopback when unset or blank.

    The server and the container healthcheck both read the bind address here,
    so they always agree on it.
    """
    host = (os.getenv("MCP_HTTP_HOST") or "").strip() or "127.0.0.1"
    # Accept the URL form of an IPv6 literal ('[::]'); uvicorn needs it bare.
    if host.startswith("[") and host.endswith("]"):
        host = host[1:-1]
    return host


def transport_help() -> str:
    """List the accepted MCP_TRANSPORT spellings for error messages."""
    return ", ".join(TRANSPORT_ALIASES)


_Number = TypeVar("_Number", int, float)


def _env_number(
    name: str, default: _Number, cast: Callable[[str], _Number], kind: str
) -> _Number:
    """Read a numeric environment variable, treating a blank value as unset."""
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return cast(raw.strip())
    except ValueError:
        raise ValueError(f"{name} must be {kind}, got {raw!r}") from None


def env_int(name: str, default: int) -> int:
    """
    Read an integer environment variable.

    A blank or whitespace-only value counts as unset and yields the default,
    matching how parse_bool treats blank values.

    Raises:
        ValueError: If the variable is set to something that is not an integer.
    """
    return _env_number(name, default, int, "an integer")


def env_float(name: str, default: float) -> float:
    """
    Read a float environment variable, treating a blank value as unset.

    Raises:
        ValueError: If the variable is set to something that is not a number.
    """
    return _env_number(name, default, float, "a number")


def parse_bool(val: str | None, default: bool = True) -> bool:
    """
    Convert a value to boolean.

    A blank or whitespace-only value counts as unset and yields the default,
    so an env var declared without a value (``LIBRENMS_VERIFY_SSL=``) cannot
    silently flip a setting off.

    Args:
        val: The value to convert.
        default (bool, optional): The default value to return if val is None or blank. Defaults to True.

    Returns:
        bool: True if val represents a truthy value ("1", "true", "yes", "on"), case-insensitive; otherwise False.
    """
    if val is None:
        return default
    normalized = str(val).strip().casefold()
    if not normalized:
        return default
    return normalized in TRUTHY_VALUES


def paginate_list(
    result: Any,
    limit: int,
    offset: int,
    key: str | None = None,
) -> Any:
    """
    Perform client-side pagination on a list (either directly or inside a dictionary).

    Args:
        result: The original response from the LibreNMS API.
        limit (int): The maximum number of results to return.
        offset (int): The number of results to skip.
        key (str, optional): The key in the response dictionary containing the list.
                             If None, it will be auto-detected.

    Returns:
        The response with the list paginated and metadata added.
    """
    if isinstance(result, list):
        total = len(result)
        paginated_items = result[offset : offset + limit]
        return {
            "items": paginated_items,
            "count": len(paginated_items),
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    if not isinstance(result, dict) or result.get("status") == "error":
        return result

    # Find the target key
    if key is None:
        list_keys = [k for k, v in result.items() if isinstance(v, list)]
        if not list_keys:
            return result
        # Sort by list length descending to find the main list
        list_keys.sort(key=lambda k: len(result[k]), reverse=True)
        key = list_keys[0]

    items = result.get(key)
    if not isinstance(items, list):
        return result

    total = len(items)
    paginated_items = items[offset : offset + limit]

    paginated_result = {k: v for k, v in result.items() if k != key}
    paginated_result[key] = paginated_items
    paginated_result["count"] = len(paginated_items)
    paginated_result["total"] = total
    paginated_result["limit"] = limit
    paginated_result["offset"] = offset

    return paginated_result
