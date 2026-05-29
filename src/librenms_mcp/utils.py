from typing import Any

TRUTHY_VALUES = ("1", "true", "yes", "on")


def parse_bool(val: str | None, default: bool = True) -> bool:
    """
    Convert a value to boolean.

    Args:
        val: The value to convert.
        default (bool, optional): The default value to return if val is None. Defaults to True.

    Returns:
        bool: True if val represents a truthy value ("1", "true", "yes", "on"), case-insensitive; otherwise False.
    """
    if val is None:
        return default
    return str(val).strip().casefold() in TRUTHY_VALUES


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
