"""
Route-safe references to LibreNMS objects that are addressed by name or ID.

Locations, device, port and poller groups are routed as ``.../{name_or_id}``.
LibreNMS decodes %2F before matching routes, and these route parameters do not
accept a '/', so a name like 'DC1/Room 2' splits the route and comes back as
"This API route doesn't exist". Every such endpoint also accepts the numeric
ID, so a name containing '/' is translated to its ID first.

LibreNMS reads an all-digit reference as an ID (ctype_digit), never as a
name, so a group named "2024" cannot be reached by name and "2024" would
silently address whichever object has ID 2024. All-digit references are
therefore checked against the list too, at the cost of one request; when the
list cannot be read, the reference is sent as the ID. Other names are used as
given, without the extra request.
"""

from dataclasses import dataclass

from librenms_mcp.librenms_client import LibreNMSClient
from librenms_mcp.utils import unique_match


class UnroutableRefError(Exception):
    """A reference that cannot be safely routed; the message says why.

    Tools catch it with their other errors and return it as an error body.
    """


@dataclass(frozen=True)
class NamedKind:
    """Where to list one kind of named object, and how to read its entries."""

    label: str
    list_path: tuple[str, ...]
    list_key: str
    name_field: str


LOCATION = NamedKind("Location", ("resources", "locations"), "locations", "location")
DEVICE_GROUP = NamedKind("Device group", ("devicegroups",), "groups", "name")
PORT_GROUP = NamedKind("Port group", ("port_groups",), "groups", "name")
POLLER_GROUP = NamedKind(
    "Poller group", ("poller_group",), "get_poller_group", "group_name"
)


def is_librenms_id(ref: str) -> bool:
    """Whether LibreNMS reads ref as an ID: PHP's ctype_digit, ASCII only."""
    return ref.isascii() and ref.isdigit()


async def route_ref(client: LibreNMSClient, kind: NamedKind, name: str) -> str:
    """Return a reference LibreNMS routes to the object the caller meant.

    Args:
        client: The open LibreNMS client.
        kind: Which kind of object the name refers to.
        name: The object's name or ID, as given by the caller.

    Returns:
        str: The name unchanged, or the ID of the object it names.

    Raises:
        UnroutableRefError: When a name containing '/' matches no object (sent as
            a name it would only produce the misleading route error), a name
            matches several objects, an all-digit reference is both one
            object's ID and another's name, or the list of objects could not
            be read for a name containing '/'.
    """
    is_id = is_librenms_id(name)
    if "/" not in name and not is_id:
        return name
    result = await client.get(*kind.list_path)
    if not isinstance(result, dict) or result.get("status") == "error":
        if is_id:
            # LibreNMS checks permissions per object, so a token may reach
            # this ID without being allowed to list them all. The collision
            # check needs the list; without it, send the ID as LibreNMS
            # reads it, as it would be without the check.
            return name
        # A failed listing (permissions, a proxy, LibreNMS's own "none exist")
        # says nothing about this name; do not report it as missing.
        detail = result.get("message") if isinstance(result, dict) else None
        raise UnroutableRefError(
            f"Could not look up {kind.label.lower()} {name!r}: "
            f"{detail or str(result)[:200]}"
        )
    entries = [
        entry
        for entry in result.get(kind.list_key) or []
        if isinstance(entry, dict) and entry.get("id") is not None
    ]
    # Case-insensitive as a fallback, as LibreNMS's own name lookup (a
    # case-insensitive MySQL collation) would match.
    entry, ambiguous = unique_match(entries, kind.name_field, name)
    # LibreNMS looks the ID up numerically, so "007" addresses ID 7.
    id_ref = str(int(name)) if is_id else None
    by_id = next((e for e in entries if str(e["id"]) == id_ref), None)
    if ambiguous:
        ids = ", ".join(str(match["id"]) for match in ambiguous)
        if by_id is not None and by_id not in ambiguous:
            # "Use the ID" would send the same reference again; point the
            # caller at the object that has this ID by its name instead.
            raise UnroutableRefError(
                f"{name!r} is both the ID of {kind.label.lower()} "
                f"{by_id.get(kind.name_field)!r} and the name of "
                f"{kind.label.lower()}s with IDs {ids}; use the name of the "
                f"first or the ID of one of the others"
            )
        if by_id is not None:
            # The ID is one of the namesakes, so "use the ID" would loop too;
            # only the other namesakes have a reference of their own.
            others = ", ".join(
                str(match["id"]) for match in ambiguous if match is not by_id
            )
            raise UnroutableRefError(
                f"{kind.label} name {name!r} is shared by IDs {ids}, and "
                f"{name!r} is also the ID of one of them; use ID {others} for "
                f"the others, or rename one so the name is unique"
            )
        raise UnroutableRefError(
            f"{kind.label} name {name!r} is ambiguous (IDs {ids}); use the ID"
        )
    if is_id:
        if entry is None or entry is by_id:
            # Not anyone's name (or the name of the object with that ID):
            # LibreNMS reads it as the ID, as meant. An unknown ID is left to
            # LibreNMS to report.
            return name
        if by_id is not None:
            raise UnroutableRefError(
                f"{name!r} is both the ID of {kind.label.lower()} "
                f"{by_id.get(kind.name_field)!r} and the name of "
                f"{kind.label.lower()} ID {entry['id']}; use the name of the "
                f"first or the ID of the second"
            )
    if entry is not None:
        return str(entry["id"])
    raise UnroutableRefError(f"{kind.label} {name!r} does not exist")
