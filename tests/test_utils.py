import pytest

from librenms_mcp.utils import env_float
from librenms_mcp.utils import env_int
from librenms_mcp.utils import http_host_from_env
from librenms_mcp.utils import normalize_transport
from librenms_mcp.utils import optional_segment
from librenms_mcp.utils import parse_bool
from librenms_mcp.utils import path_segment


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
        ("random", True, False),
        ("False", True, False),
        # Blank means "unset", so the default wins rather than False.
        ("", True, True),
        ("", False, False),
        ("  ", True, True),
        ("  ", False, False),
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


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("core1", "core1"),
        ("10.0.0.1", "10.0.0.1"),
        ("rules/5", "rules%2F5"),
        ("sw#1", "sw%231"),
        ("a?b=c", "a%3Fb%3Dc"),
        ("Te2/7", "Te2%2F7"),
        ("...", "..."),
        # Sent as given: interface names can carry real surrounding spaces.
        (" sw1 ", "%20sw1%20"),
        (" .. ", "%20..%20"),
        (42, "42"),
    ],
)
def test_path_segment_encodes_reserved_characters(value, expected):
    assert path_segment(value) == expected


@pytest.mark.parametrize(
    "value",
    ["", "   ", ".", "..", "../../system", "a/../b", "./x", "..\\x"],
)
def test_path_segment_rejects_dot_segments(value):
    # These survive percent-encoding and would be resolved as dot-segments.
    with pytest.raises(ValueError, match="Invalid path segment"):
        path_segment(value)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [(None, 30), ("", 30), ("   ", 30), ("45", 45), (" 45 ", 45)],
)
def test_env_int_treats_blank_as_unset(monkeypatch, raw, expected):
    if raw is None:
        monkeypatch.delenv("LIBRENMS_TEST_INT", raising=False)
    else:
        monkeypatch.setenv("LIBRENMS_TEST_INT", raw)
    assert env_int("LIBRENMS_TEST_INT", 30) == expected


def test_env_int_names_the_variable_on_bad_input(monkeypatch):
    monkeypatch.setenv("LIBRENMS_TEST_INT", "abc")
    with pytest.raises(ValueError, match="LIBRENMS_TEST_INT must be an integer"):
        env_int("LIBRENMS_TEST_INT", 30)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, "stdio"),
        ("", "stdio"),
        ("  ", "stdio"),
        ("stdio", "stdio"),
        (" SSE ", "sse"),
        ("HTTP", "http"),
        ("Streamable-HTTP", "http"),
        # Unknown values pass through for main() to reject.
        ("websocket", "websocket"),
    ],
)
def test_normalize_transport(raw, expected):
    assert normalize_transport(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [(None, 1.0), ("", 1.0), ("  ", 1.0), ("0.25", 0.25), (" 0 ", 0.0)],
)
def test_env_float_treats_blank_as_unset(monkeypatch, raw, expected):
    if raw is None:
        monkeypatch.delenv("LIBRENMS_TEST_FLOAT", raising=False)
    else:
        monkeypatch.setenv("LIBRENMS_TEST_FLOAT", raw)
    assert env_float("LIBRENMS_TEST_FLOAT", 1.0) == expected


def test_env_float_names_the_variable_on_bad_input(monkeypatch):
    monkeypatch.setenv("LIBRENMS_TEST_FLOAT", "lots")
    with pytest.raises(ValueError, match="LIBRENMS_TEST_FLOAT must be a number"):
        env_float("LIBRENMS_TEST_FLOAT", 1.0)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, ()),
        ("", ()),
        ("  ", ()),
        ("core1", ("core1",)),
        (" core1 ", (" core1 ",)),
    ],
)
def test_optional_segment(value, expected):
    assert optional_segment(value) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, "127.0.0.1"),
        ("  ", "127.0.0.1"),
        (" 0.0.0.0 ", "0.0.0.0"),  # noqa: S104
        ("[::]", "::"),
    ],
)
def test_http_host_from_env(monkeypatch, raw, expected):
    """The server and the healthcheck share this; uvicorn needs bare IPv6."""
    if raw is None:
        monkeypatch.delenv("MCP_HTTP_HOST", raising=False)
    else:
        monkeypatch.setenv("MCP_HTTP_HOST", raw)
    assert http_host_from_env() == expected
