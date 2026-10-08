import logging
import os
from typing import Any
from typing import Literal

import httpx2

from librenms_mcp.models import LibreNMSConfig
from librenms_mcp.models import TransportConfig
from librenms_mcp.utils import env_int
from librenms_mcp.utils import http_host_from_env
from librenms_mcp.utils import normalize_transport
from librenms_mcp.utils import parse_bool
from librenms_mcp.utils import path_segment

logger = logging.getLogger(__name__)


class LibreNMSHTTPError(RuntimeError):
    """A response the caller cannot use: an error status from a raw endpoint
    such as a graph, or a JSON endpoint answering with something other than JSON.

    ``from_librenms`` is True only for LibreNMS's own body shape
    (``{"status": "error" | "ok", ...}``). That tells a LibreNMS "not found"
    apart from a reverse proxy or API gateway rejecting the request, even when
    the gateway also answers in JSON with a ``message``. ``body`` is the
    decoded JSON body, if there was one.
    """

    def __init__(
        self,
        message: str,
        status_code: int,
        from_librenms: bool,
        body: Any = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.from_librenms = from_librenms
        self.body = body


def _build_path(segments: tuple[str | int, ...]) -> str:
    """Join path parts into a LibreNMS API path, encoding each one.

    Every part is encoded as a single segment, so a model-supplied value can
    never add segments, a query string or a fragment, or walk up with ``..``.
    A tool that passes a pre-joined string by mistake gets a 404, not a request
    to a different endpoint.
    """
    if not segments:
        raise ValueError("A LibreNMS API path needs at least one segment")
    return "/".join(path_segment(seg) for seg in segments)


def _is_librenms_body(body: Any) -> bool:
    """Whether a decoded body has LibreNMS's own shape (``status`` ok or error).

    LibreNMS answers through api_success/api_error, which always set ``status``
    to "ok" or "error". Such a body is LibreNMS's real answer whatever the HTTP
    code, so it is never rewritten or retried as a proxy failure.
    """
    return isinstance(body, dict) and body.get("status") in ("ok", "error")


def _as_error_body(body: Any, status_code: int) -> dict[str, Any]:
    """Mark a non-2xx JSON body as an error so callers can check one field.

    Framework errors (``{"message": "Unauthenticated."}``), gateway errors with
    their own ``status`` value, and bodies that are not objects at all all end
    up as ``{"status": "error", "message": ...}``.
    """
    if isinstance(body, dict):
        marked = {**body, "status": "error"}
        if body.get("status") not in (None, "error"):
            marked["upstream_status"] = body["status"]
        marked.setdefault("message", f"HTTP {status_code}")
        return marked
    return {"status": "error", "message": f"HTTP {status_code}", "body": body}


def _error_message(body: Any) -> str | None:
    """Return the ``message`` of a decoded JSON error body, if it has one."""
    message = body.get("message") if isinstance(body, dict) else None
    return str(message) if message is not None else None


def _decode_error_body(resp: httpx2.Response) -> Any:
    """Decode an error response body, or return None when it is not JSON.

    Redirect bodies are never LibreNMS errors, so they are not parsed.
    """
    if resp.is_redirect:
        return None
    try:
        return resp.json()
    except ValueError:
        return None


ENCODED_SLASH_HINT = (
    "The request path contains an encoded slash (%2F), which some reverse "
    "proxies reject; for Apache, set 'AllowEncodedSlashes NoDecode'."
)


def _encoded_slash_suspect(status_code: int, from_librenms: bool, url: str) -> bool:
    """Whether a failure looks like a proxy rejecting an encoded slash.

    Apache and nginx answer 404; Tomcat and newer Traefik answer 400.
    """
    return status_code in (400, 404) and not from_librenms and "%2F" in url


def _http_error(
    resp: httpx2.Response,
    method: str,
    url: str,
    body: Any,
    stored_body: Any = None,
) -> LibreNMSHTTPError:
    """Build the error for an unusable response; shared by request() and get_raw().

    ``body`` is the decoded JSON body as received, or None when there is none
    (not JSON, or a redirect, whose body is never a LibreNMS answer). It decides
    the message and from_librenms. ``stored_body`` is what the exception
    carries for callers, when that differs (request() stores the normalized
    body); it defaults to ``body``.
    """
    from_librenms = _is_librenms_body(body)
    if resp.is_redirect:
        detail = _error_detail(resp)
    elif body is None:
        detail = f"non-JSON response: {_error_detail(resp)}"
    else:
        detail = _error_message(body) or _error_detail(resp)
    message = f"LibreNMS returned HTTP {resp.status_code} for {method} {url}: {detail}"
    if _encoded_slash_suspect(resp.status_code, from_librenms, url):
        message += f" ({ENCODED_SLASH_HINT})"
    return LibreNMSHTTPError(
        message,
        resp.status_code,
        from_librenms,
        body=body if stored_body is None else stored_body,
    )


def _error_detail(resp: httpx2.Response) -> str:
    """Describe an unusable response body for an error message.

    Redirects are not followed, so a 3xx (http -> https, an SSO proxy) is
    reported with its target, which points at the real misconfiguration.
    """
    if resp.is_redirect:
        return f"redirected to {resp.headers.get('location', '<unknown>')}"
    return resp.text.strip()[:200] or "<empty body>"


class LibreNMSClient:
    """Async client for LibreNMS API using API token authentication.

    This is a singleton so that every tool shares one connection pool. Only the
    first call's config is used - a config passed to a later call is discarded,
    which is safe here because the server builds exactly one config at startup.
    """

    _instance = None
    _initialized = False

    def __new__(cls, *args: Any, **kwargs: Any):  # noqa: ARG004
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
        self.client: httpx2.AsyncClient | None = None
        self._initialized = True

    async def __aenter__(self):
        """Enter the async context manager."""
        if self.client is None:
            headers = {"X-Auth-Token": self.config.token}
            self.client = httpx2.AsyncClient(
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

    def _require_client(self) -> httpx2.AsyncClient:
        if self.client is None:
            raise RuntimeError(
                "Client not initialized - use 'async with LibreNMSClient(config)' or call __aenter__"
            )
        return self.client

    async def request(
        self,
        method: str,
        *segments: str | int,
        params: dict[str, Any] | None = None,
        data: Any = None,
        raise_for_status: bool = False,
    ) -> dict[str, Any]:
        """Perform a request to a LibreNMS API path.

        The status code is deliberately not raised on: LibreNMS reports its own
        errors as JSON (``{"status": "error", "message": ...}``) alongside 4xx/5xx
        codes, and that message is more useful to the caller than the code.
        Any other non-2xx body (framework errors such as 401/403, gateway
        errors, JSON that is not an object) is marked with ``status: "error"``
        too, letting callers check one field. A body that is not JSON at all is not from LibreNMS - a reverse
        proxy error page, for instance - so that is surfaced with the status code
        attached rather than as a bare "Expecting value" decode error.

        Args:
            method: HTTP method.
            *segments: Path parts, each encoded as one segment.
            params: Optional query parameters.
            data: Optional JSON body.
            raise_for_status: Raise on a non-2xx status instead of returning the
                error body, for callers that react to the status code. The
                (normalized) body is kept on the exception.

        Raises:
            LibreNMSHTTPError: If the response is a redirect or not JSON, or on
                a non-2xx status when raise_for_status is set.
        """
        client = self._require_client()
        url = _build_path(segments)
        resp = await client.request(method, url, params=params, json=data)
        if resp.is_redirect:
            # Redirects are not followed; report the target even when the
            # redirect carries a JSON body.
            raise _http_error(resp, method, url, None)
        try:
            body = resp.json()
        except ValueError as e:
            raise _http_error(resp, method, url, None) from e
        if resp.is_success:
            return body
        raw_body = body
        if not _is_librenms_body(body):
            body = _as_error_body(body, resp.status_code)
            if _encoded_slash_suspect(resp.status_code, False, url):
                # Most tools return this body rather than raising, so the hint
                # has to travel in it, not only in an exception message.
                body["hint"] = ENCODED_SLASH_HINT
        if raise_for_status:
            raise _http_error(resp, method, url, raw_body, stored_body=body)
        return body

    async def get(
        self,
        *segments: str | int,
        params: dict[str, Any] | None = None,
        raise_for_status: bool = False,
    ) -> dict[str, Any]:
        """Perform a GET request to a LibreNMS API path."""
        return await self.request(
            "GET", *segments, params=params, raise_for_status=raise_for_status
        )

    async def get_raw(
        self, *segments: str | int, params: dict[str, Any] | None = None
    ) -> tuple[bytes, str]:
        """Perform a GET request returning the undecoded body and its content type.

        Graph endpoints return an image (SVG or PNG depending on the LibreNMS
        version and rrdtool build) rather than JSON, so they cannot go through
        `get()`, which would fail to decode the body.

        Args:
            *segments: Path parts, each encoded as one segment.
            params: Optional query parameters.

        Returns:
            tuple[bytes, str]: The raw response body and its MIME type.

        Raises:
            LibreNMSHTTPError: If LibreNMS answers with a non-2xx status.
        """
        client = self._require_client()
        url = _build_path(segments)
        resp = await client.get(url, params=params)
        if not resp.is_success:
            # Keep the LibreNMS JSON error message: it explains the failure
            # ("Device foo not found") where the bare status code does not.
            raise _http_error(resp, "GET", url, _decode_error_body(resp))
        content_type = resp.headers.get("content-type", "application/octet-stream")
        return resp.content, content_type.split(";")[0].strip()

    async def post(self, *segments: str | int, data: Any = None) -> dict[str, Any]:
        """Perform a POST request to a LibreNMS API path."""
        return await self.request("POST", *segments, data=data)

    async def put(self, *segments: str | int, data: Any = None) -> dict[str, Any]:
        """Perform a PUT request to a LibreNMS API path."""
        return await self.request("PUT", *segments, data=data)

    async def delete(
        self,
        *segments: str | int,
        params: dict[str, Any] | None = None,
        data: Any = None,
    ) -> dict[str, Any]:
        """Perform a DELETE request to a LibreNMS API path."""
        return await self.request("DELETE", *segments, params=params, data=data)

    async def patch(self, *segments: str | int, data: Any = None) -> dict[str, Any]:
        """Perform a PATCH request to a LibreNMS API path."""
        return await self.request("PATCH", *segments, data=data)


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

    # Get required config values
    librenms_url = os.getenv("LIBRENMS_URL")
    if not librenms_url:
        raise ValueError("LIBRENMS_URL environment variable is required")

    token = os.getenv("LIBRENMS_TOKEN")
    if not token:
        raise ValueError("LIBRENMS_TOKEN environment variable is required")

    raw_tool_search_strategy = os.getenv("TOOL_SEARCH_STRATEGY", "bm25").lower()
    tool_search_strategy: Literal["bm25", "regex"] = (
        "regex" if raw_tool_search_strategy == "regex" else "bm25"
    )

    return LibreNMSConfig(
        librenms_url=librenms_url,
        token=token,
        verify_ssl=parse_bool(os.getenv("LIBRENMS_VERIFY_SSL"), default=True),
        timeout=env_int("LIBRENMS_TIMEOUT", 30),
        read_only_mode=parse_bool(os.getenv("READ_ONLY_MODE"), default=False),
        disabled_tags=disabled_tags,
        rate_limit_enabled=parse_bool(os.getenv("RATE_LIMIT_ENABLED"), default=False),
        rate_limit_max_requests=env_int("RATE_LIMIT_MAX_REQUESTS", 60),
        rate_limit_window_minutes=env_int("RATE_LIMIT_WINDOW_MINUTES", 1),
        tool_search_enabled=parse_bool(os.getenv("TOOL_SEARCH_ENABLED"), default=False),
        tool_search_strategy=tool_search_strategy,
        tool_search_max_results=env_int("TOOL_SEARCH_MAX_RESULTS", 5),
    )


def get_transport_config_from_env() -> TransportConfig:
    """Get transport configuration from environment variables."""
    http_bearer_token = os.getenv("MCP_HTTP_BEARER_TOKEN")
    if http_bearer_token is not None:
        http_bearer_token = http_bearer_token.strip() or None

    # An unknown value is passed through for main() to reject. Raising here
    # would break `fastmcp run`, which imports the server module but picks the
    # transport itself and never reads MCP_TRANSPORT.
    return TransportConfig(
        transport_type=normalize_transport(os.getenv("MCP_TRANSPORT")),
        http_host=http_host_from_env(),
        http_port=env_int("MCP_HTTP_PORT", 8000),
        http_bearer_token=http_bearer_token,
    )
