import pytest

from librenms_mcp.utils import parse_bool


@pytest.mark.parametrize(
    ("val", "default", "expected"),
    [
        (None, True, True),
        (None, False, False),
        ("1", False, True),
        ("true", False, True),
        ("yes", False, True),
        ("on", False, True),
        ("TrUe", False, True),
        ("YES", False, True),
        ("ON", False, True),
        ("1 ", False, True),
        ("0", True, False),
        ("false", True, False),
        ("no", True, False),
        ("off", True, False),
        ("", True, False),
        ("random", True, False),
        ("  ", True, False),
        ("False", True, False),
    ],
)
def test_parse_bool(val, default, expected):
    assert parse_bool(val, default) is expected


def test_paginate_list_direct_list():
    from librenms_mcp.utils import paginate_list

    items = [1, 2, 3, 4, 5]
    result = paginate_list(items, limit=2, offset=1)
    assert result == {
        "items": [2, 3],
        "count": 2,
        "total": 5,
        "limit": 2,
        "offset": 1,
    }


def test_paginate_list_dict_with_key():
    from librenms_mcp.utils import paginate_list

    data = {
        "status": "ok",
        "devices": [{"id": 1}, {"id": 2}, {"id": 3}],
        "other": "value",
    }
    result = paginate_list(data, limit=2, offset=1, key="devices")
    assert result == {
        "status": "ok",
        "devices": [{"id": 2}, {"id": 3}],
        "other": "value",
        "count": 2,
        "total": 3,
        "limit": 2,
        "offset": 1,
    }


def test_paginate_list_dict_autodetect():
    from librenms_mcp.utils import paginate_list

    data = {
        "status": "ok",
        "ports": [{"id": 10}, {"id": 20}, {"id": 30}],
        "some_list": [1],  # shorter list, should prefer the longer one
    }
    result = paginate_list(data, limit=1, offset=1)
    assert result == {
        "status": "ok",
        "ports": [{"id": 20}],
        "some_list": [1],
        "count": 1,
        "total": 3,
        "limit": 1,
        "offset": 1,
    }


def test_paginate_list_error_and_invalid():
    from librenms_mcp.utils import paginate_list

    # If it's not dict/list
    assert paginate_list("not a list", 5, 0) == "not a list"

    # If status is error
    error_data = {"status": "error", "message": "API error"}
    assert paginate_list(error_data, 5, 0) == error_data

    # If dictionary has no lists
    no_lists = {"status": "ok", "value": "some string"}
    assert paginate_list(no_lists, 5, 0) == no_lists
