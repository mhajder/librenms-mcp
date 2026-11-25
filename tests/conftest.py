"""Shared test fixtures for LibreNMS MCP server tests."""

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from fastmcp import Client
from fastmcp import FastMCP

from librenms_mcp.models import LibreNMSConfig
from librenms_mcp.tools import register_tools

CONFIG = LibreNMSConfig(librenms_url="https://nms.invalid", token="t")


@pytest.fixture(scope="session")
def tools_server() -> FastMCP:
    """Build the server with every tool registered once for the test session.

    Tools look up the LibreNMSClient singleton on each call, so sharing one
    FastMCP instance does not share scripted LibreNMS state between tests.
    """
    mcp = FastMCP("test")
    register_tools(mcp, CONFIG)
    return mcp


@pytest_asyncio.fixture(scope="session")
async def tools_client(tools_server: FastMCP) -> AsyncGenerator[Client]:
    """Keep one in-memory MCP Client open across tests using the shared server."""
    async with Client(tools_server) as client:
        yield client
