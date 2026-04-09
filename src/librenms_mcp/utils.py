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
