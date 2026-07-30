from typing import cast

import pytest
from fastmcp.exceptions import ToolError

from librenms_mcp.librenms_client import LibreNMSClient
from librenms_mcp.tools.graphs import _graph_params
from librenms_mcp.tools.graphs import _resolve_port_id
from librenms_mcp.tools.graphs import _to_image


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
    assert image.to_image_content().mimeType == expected_mime


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
        self.calls: list[tuple[str, dict | None]] = []

    async def get(self, path: str, params: dict | None = None) -> dict:
        self.calls.append((path, params))
        return self._payload


def _as_client(fake: _FakeClient) -> LibreNMSClient:
    """Present the test double as the client type the helper expects."""
    return cast(LibreNMSClient, fake)


@pytest.mark.asyncio
async def test_resolve_port_id_matches_case_insensitively():
    client = _FakeClient({"ports": [{"port_id": 7, "ifName": "Te2/7"}]})
    assert await _resolve_port_id(_as_client(client), "sw1", "te2/7") == 7
    assert client.calls == [("devices/sw1/ports", {"columns": "port_id,ifName"})]


@pytest.mark.asyncio
async def test_resolve_port_id_encodes_hostname():
    client = _FakeClient({"ports": [{"port_id": 1, "ifName": "Po1"}]})
    await _resolve_port_id(_as_client(client), "sw 1/a", "Po1")
    assert client.calls[0][0] == "devices/sw%201%2Fa/ports"


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", [{"ports": []}, {"ports": None}, {}])
async def test_resolve_port_id_raises_when_absent(payload):
    with pytest.raises(ToolError, match="No interface named"):
        await _resolve_port_id(_as_client(_FakeClient(payload)), "sw1", "Po1")
