import logging
import os
from typing import Any

import httpx

from librenms_mcp.models import LibreNMSConfig
from librenms_mcp.models import TransportConfig
from librenms_mcp.utils import parse_bool

logger = logging.getLogger(__name__)


class LibreNMSClient:
    """Async client for LibreNMS API using API token authentication"""

    _instance = None
    _initialized = False

    def __new__(cls, config: LibreNMSConfig | None = None):
        """Create a new instance of LibreNMSClient."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, config: LibreNMSConfig | None = None):
        """Initialize the LibreNMSClient."""
        if self._initialized:
            return
        if config is None:
            raise ValueError("Config must be provided for first initialization")
        self.config = config
        # Ensure trailing slash for base_url
        base = config.librenms_url.rstrip("/")
        self.base_url = f"{base}/api/v0"
        self.client: httpx.AsyncClient | None = None
        self._initialized = True

    async def __aenter__(self):
        """Enter the async context manager."""
        if self.client is None:
            headers = {"X-Auth-Token": self.config.token}
            self.client = httpx.AsyncClient(
                verify=self.config.verify_ssl,
                timeout=self.config.timeout,
                headers=headers,
                base_url=self.base_url,
            )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit the async context manager."""
        # Keep client for reuse
        pass

    async def close(self):
        """Close the HTTP client session."""
        if self.client is not None:
            await self.client.aclose()
            self.client = None

    async def request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Perform a request to a LibreNMS API path."""
        if self.client is None:
            raise RuntimeError(
                "Client not initialized - use 'async with LibreNMSClient(config)' or call __aenter__"
            )
        url = path.lstrip("/")
        resp = await self.client.request(method, url, params=params, json=data)
        # resp.raise_for_status()
        return resp.json()

    async def get(
        self, path: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Perform a GET request to a LibreNMS API path."""
        return await self.request("GET", path, params=params)

    async def post(
        self, path: str, data: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Perform a POST request to a LibreNMS API path."""
        return await self.request("POST", path, data=data)

    async def put(
        self, path: str, data: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Perform a PUT request to a LibreNMS API path."""
        return await self.request("PUT", path, data=data)

    async def delete(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Perform a DELETE request to a LibreNMS API path."""
        return await self.request("DELETE", path, params=params, data=data)

    async def patch(
        self, path: str, data: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Perform a PATCH request to a LibreNMS API path."""
        return await self.request("PATCH", path, data=data)


def get_librenms_config_from_env() -> LibreNMSConfig:
    """Get LibreNMS configuration from environment variables."""
    # Parse disabled tags from comma-separated string
    disabled_tags_str = os.getenv("DISABLED_TAGS", "")
    disabled_tags = set()
    if disabled_tags_str.strip():
        # Split by comma and strip whitespace from each tag
        disabled_tags = {
            tag.strip() for tag in disabled_tags_str.split(",") if tag.strip()
        }

    return LibreNMSConfig(
        librenms_url=os.getenv("LIBRENMS_URL"),
        token=os.getenv("LIBRENMS_TOKEN"),
        verify_ssl=parse_bool(os.getenv("LIBRENMS_VERIFY_SSL"), default=True),
        timeout=int(os.getenv("LIBRENMS_TIMEOUT", "30")),
        read_only_mode=parse_bool(os.getenv("READ_ONLY_MODE"), default=False),
        disabled_tags=disabled_tags,
        rate_limit_enabled=parse_bool(os.getenv("RATE_LIMIT_ENABLED"), default=False),
        rate_limit_max_requests=int(os.getenv("RATE_LIMIT_MAX_REQUESTS", "60")),
        rate_limit_window_minutes=int(os.getenv("RATE_LIMIT_WINDOW_MINUTES", "1")),
    )


def get_transport_config_from_env() -> TransportConfig:
    """Get transport configuration from environment variables."""
    return TransportConfig(
        transport_type=os.getenv("MCP_TRANSPORT", "stdio").lower(),
        http_host=os.getenv("MCP_HTTP_HOST", "0.0.0.0"),
        http_port=int(os.getenv("MCP_HTTP_PORT", "8000")),
        http_bearer_token=os.getenv("MCP_HTTP_BEARER_TOKEN"),
    )


_librenms_client_singleton: LibreNMSClient | None = None


def get_librenms_client(config: LibreNMSConfig | None = None) -> LibreNMSClient:
    """Get the singleton LibreNMS client instance."""
    global _librenms_client_singleton
    if _librenms_client_singleton is None:
        if config is None:
            raise ValueError(
                "LibreNMS config must be provided for first initialization"
            )
        _librenms_client_singleton = LibreNMSClient(config)
    return _librenms_client_singleton
