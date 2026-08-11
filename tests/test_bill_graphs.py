"""Guards for the bill graph tools.

The bill graph endpoints answer with a rendered image, not JSON, so they have
to go through get_raw. Decoding them as JSON fails on every call.
"""

from typing import Any

import pytest
from fastmcp.utilities.types import Image

from librenms_mcp.tools import bills as bills_module


class _FakeContext:
    """Stands in for the FastMCP context the tools log through."""

    async def info(self, message: str) -> None:
        pass

    async def error(self, message: str) -> None:
        pass


class _FakeClient:
    """Records requests and replays a canned image response."""

    def __init__(self, raw: tuple[bytes, str]):
        self.raw = raw
        self.calls: list[tuple[str, str, Any]] = []

    def __call__(self, _config):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        return False

    async def get_raw(self, path: str, params: dict | None = None):
        self.calls.append(("GET", path, params))
        return self.raw


class _ToolRecorder:
    """Captures the tools a register_* function declares."""

    def __init__(self):
        self.tools: dict[str, Any] = {}

    def tool(self, **kwargs):  # noqa: ARG002
        def decorator(fn):
            self.tools[fn.__name__] = fn
            return fn

        return decorator


@pytest.fixture
def bill_tools() -> _ToolRecorder:
    recorder = _ToolRecorder()
    bills_module.register_bill_tools(recorder, None)
    return recorder


@pytest.mark.asyncio
async def test_bill_graph_returns_an_image(bill_tools, monkeypatch):
    fake = _FakeClient((b"\x89PNG", "image/png"))
    monkeypatch.setattr(bills_module, "LibreNMSClient", fake)

    image = await bill_tools.tools["bill_graph"](4, "bits", _FakeContext())

    assert isinstance(image, Image)
    assert fake.calls == [("GET", "bills/4/graphs/bits", None)]


@pytest.mark.asyncio
async def test_bill_history_graph_returns_an_image(bill_tools, monkeypatch):
    fake = _FakeClient((b"<svg/>", "image/svg+xml"))
    monkeypatch.setattr(bills_module, "LibreNMSClient", fake)

    image = await bill_tools.tools["bill_history_graph"](4, 9, "day", _FakeContext())

    assert isinstance(image, Image)
    assert fake.calls == [("GET", "bills/4/history/9/graphs/day", None)]
