from typing import cast

import pytest
from fastmcp.exceptions import ToolError

from librenms_mcp.librenms_client import LibreNMSClient
from librenms_mcp.tools.graphs import _graph_params
from librenms_mcp.tools.graphs import _to_image
from librenms_mcp.tools.port_lookup import resolve_port_id as _resolve_port_id


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        (
            {"from_": None, "to": None, "width": None, "height": None, "legend": None},
            {},
        ),
        (
            {"from_": "-1d", "to": None, "width": None, "height": None, "legend": None},
            {"from": "-1d"},
        ),
        (
            {
                "from_": "-1d",
                "to": "-1h",
                "width": 900,
                "height": 300,
                "legend": True,
            },
            {
                "from": "-1d",
                "to": "-1h",
                "width": 900,
                "height": 300,
                "legend": "yes",
            },
        ),
        (
            {
                "from_": None,
                "to": None,
                "width": None,
                "height": None,
                "legend": False,
            },
            {"legend": "no"},
        ),
    ],
)
def test_graph_params_omits_unset_values(kwargs, expected):
    assert _graph_params(**kwargs) == expected


@pytest.mark.parametrize(
    ("content_type", "expected_mime"),
    [
        ("image/svg+xml", "image/svg+xml"),
        ("image/png", "image/png"),
    ],
)
def test_to_image_preserves_content_type(content_type, expected_mime):
    image = _to_image(b"payload", content_type)
    assert image.to_image_content().mime_type == expected_mime


def test_to_image_rejects_non_image():
    # LibreNMS answers graph failures with a JSON body rather than an image.
    with pytest.raises(ToolError, match="application/json"):
        _to_image(b'{"status": "error"}', "application/json")


class _FakeClient:
    """Minimal stand-in exposing only the get() used by _resolve_port_id.

    Instantiating a real LibreNMSClient is not viable here: it is a singleton, so
    building one in a test would leak into every later test in the session.
    Callers cast it to LibreNMSClient, since only get() is exercised.
    """

    def __init__(self, payload: dict) -> None:
        self._payload = payload
        self.calls: list[tuple[tuple[str | int, ...], dict | None]] = []

    async def get(self, *segments: str | int, params: dict | None = None) -> dict:
        self.calls.append((segments, params))
        return self._payload


def _as_client(fake: _FakeClient) -> LibreNMSClient:
    """Present the test double as the client type the helper expects."""
    return cast(LibreNMSClient, fake)


@pytest.mark.asyncio
async def test_resolve_port_id_matches_case_insensitively():
    client = _FakeClient({"ports": [{"port_id": 7, "ifName": "Te2/7"}]})
    assert await _resolve_port_id(_as_client(client), "sw1", "te2/7") == 7
    assert client.calls == [
        (("devices", "sw1", "ports"), {"columns": "port_id,ifName"})
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", [{"ports": []}, {"ports": None}, {}])
async def test_resolve_port_id_raises_when_absent(payload):
    with pytest.raises(ToolError, match="No interface named"):
        await _resolve_port_id(_as_client(_FakeClient(payload)), "sw1", "Po1")


@pytest.mark.asyncio
async def test_resolve_port_id_surfaces_librenms_errors():
    """An auth or lookup failure must not be reported as a missing interface.

    The client marks framework errors (a bare message) with status "error" too,
    so this one shape covers both.
    """
    client = _FakeClient({"status": "error", "message": "Unauthenticated."})
    with pytest.raises(ToolError, match="Unauthenticated"):
        await _resolve_port_id(_as_client(client), "sw1", "Po1")


@pytest.mark.asyncio
async def test_resolve_port_id_prefers_the_exact_name():
    client = _FakeClient(
        {
            "ports": [
                {"port_id": 1, "ifName": "TE2/7"},
                {"port_id": 2, "ifName": "Te2/7"},
            ]
        }
    )
    assert await _resolve_port_id(_as_client(client), "sw1", "Te2/7") == 2


@pytest.mark.asyncio
async def test_resolve_port_id_rejects_ambiguous_case_insensitive_names():
    """'te2/7' must not silently pick one of two differently-cased ports."""
    client = _FakeClient(
        {
            "ports": [
                {"port_id": 1, "ifName": "TE2/7"},
                {"port_id": 2, "ifName": "Te2/7"},
            ]
        }
    )
    with pytest.raises(
        ToolError, match=r"ambiguous.*'TE2/7' \(port_id 1\), 'Te2/7' \(port_id 2\)"
    ):
        await _resolve_port_id(_as_client(client), "sw1", "te2/7")


@pytest.mark.asyncio
async def test_resolve_port_id_finds_padded_vendor_names():
    """A device may report 'Gi0/1 '; the exact name as given must still match."""
    client = _FakeClient(
        {
            "ports": [
                {"port_id": 1, "ifName": "Gi0/1"},
                {"port_id": 2, "ifName": "Gi0/1 "},
            ]
        }
    )
    assert await _resolve_port_id(_as_client(client), "sw1", "Gi0/1 ") == 2
    assert await _resolve_port_id(_as_client(client), "sw1", "Gi0/1") == 1


@pytest.mark.asyncio
async def test_resolve_port_id_rejects_duplicate_exact_names():
    """Stacked switches can report one ifName twice; never pick one silently."""
    client = _FakeClient(
        {
            "ports": [
                {"port_id": 1, "ifName": "Te2/7"},
                {"port_id": 5, "ifName": "Te2/7"},
            ]
        }
    )
    with pytest.raises(ToolError, match=r"ambiguous.*port_id 1.*port_id 5"):
        await _resolve_port_id(_as_client(client), "sw1", "Te2/7")


@pytest.mark.asyncio
async def test_resolve_port_id_does_not_strip_the_name():
    """Names are matched as given; ' Te2/7 ' is not silently 'Te2/7'."""
    client = _FakeClient({"ports": [{"port_id": 7, "ifName": "Te2/7"}]})
    with pytest.raises(ToolError, match="No interface named"):
        await _resolve_port_id(_as_client(client), "sw1", " Te2/7 ")
