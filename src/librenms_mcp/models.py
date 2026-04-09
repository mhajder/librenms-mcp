from typing import Literal

from pydantic import BaseModel
from pydantic import Field


class LibreNMSConfig(BaseModel):
    librenms_url: str = Field(
        ..., description="LibreNMS base URL, e.g. https://domain.tld:8443"
    )
    token: str = Field(..., description="LibreNMS API token")
    verify_ssl: bool = Field(True, description="Verify SSL (true/false)")
    timeout: int = Field(30, description="Timeout in seconds")
    read_only_mode: bool = Field(False, description="Read-only mode (true/false)")
    disabled_tags: set[str] = Field(
        default_factory=set, description="Set of tags to disable tools for"
    )
    rate_limit_enabled: bool = Field(
        False, description="Enable rate limiting (true/false)"
    )
    rate_limit_max_requests: int = Field(60, description="Maximum requests per minute")
    rate_limit_window_minutes: int = Field(
        1, description="Rate limit window in minutes"
    )
    tool_search_enabled: bool = Field(
        False, description="Enable FastMCP tool search transform"
    )
    tool_search_strategy: Literal["bm25", "regex"] = Field(
        "bm25",
        description="Tool search strategy: 'bm25' (natural language) or 'regex'",
    )
    tool_search_max_results: int = Field(
        5,
        ge=1,
        description="Maximum number of tools returned by search_tools",
    )


class TransportConfig(BaseModel):
    """Configuration for MCP transport layer"""

    transport_type: str = Field(
        "stdio",
        description="Transport type: 'stdio', 'sse' (Server-Sent Events), or 'http' (HTTP Streamable)",
    )
    # HTTP transport settings (for both SSE and HTTP Streamable)
    http_host: str = Field(
        "0.0.0.0", description="Host to bind for HTTP transports (SSE/HTTP Streamable)"
    )
    http_port: int = Field(
        8000, description="Port to bind for HTTP transports (SSE/HTTP Streamable)"
    )
    http_bearer_token: str | None = Field(
        None, description="Bearer token for HTTP authentication"
    )
