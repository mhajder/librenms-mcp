"""The container healthcheck must ask the server itself, not just the port."""

import os
import socket
import subprocess
import sys
import threading
import time
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler
from http.server import ThreadingHTTPServer

import pytest

from librenms_mcp import healthcheck


@pytest.fixture(autouse=True)
def no_dotenv(monkeypatch):
    """Keep the repository's real .env out of these tests."""
    monkeypatch.setattr(healthcheck, "load_dotenv", lambda: None)


def _serve(status: int) -> Iterator[int]:
    """Run a tiny HTTP server answering `status` on /health, 404 elsewhere."""

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self.send_response(status if self.path == "/health" else 404)
            self.end_headers()
            self.wfile.write(b"ok")

        def log_message(self, format: str, *args: object) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_address[1]
    finally:
        server.shutdown()
        server.server_close()


@pytest.fixture
def healthy_port() -> Iterator[int]:
    yield from _serve(200)


@pytest.fixture
def failing_port() -> Iterator[int]:
    yield from _serve(503)


@pytest.fixture
def hung_port(monkeypatch) -> Iterator[int]:
    """A socket that accepts connections but never answers, like a stuck server.

    The kernel completes the TCP handshake from the listen backlog, so a plain
    connect would call this healthy.
    """
    monkeypatch.setattr(healthcheck, "PROBE_TIMEOUT_SECONDS", 0.3)
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        sock.listen()
        yield sock.getsockname()[1]


@pytest.fixture
def closed_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _configure(monkeypatch, port: int, transport: str = "http") -> None:
    monkeypatch.setenv("MCP_TRANSPORT", transport)
    monkeypatch.setenv("MCP_HTTP_PORT", str(port))
    monkeypatch.delenv("MCP_HTTP_HOST", raising=False)


@pytest.mark.parametrize("transport", ["http", " HTTP ", "sse", "streamable-http"])
def test_http_transports_are_probed(monkeypatch, closed_port, transport):
    _configure(monkeypatch, closed_port, transport)
    assert healthcheck.main() == 1


def test_health_endpoint_answering_200_is_healthy(monkeypatch, healthy_port):
    _configure(monkeypatch, healthy_port)
    assert healthcheck.main() == 0


def test_health_endpoint_error_is_unhealthy(monkeypatch, failing_port):
    _configure(monkeypatch, failing_port)
    assert healthcheck.main() == 1


def test_open_port_that_never_answers_is_unhealthy(monkeypatch, hung_port):
    """The reason for an HTTP probe: a stuck server still accepts TCP."""
    _configure(monkeypatch, hung_port)
    assert healthcheck.main() == 1


@pytest.mark.parametrize("transport", ["stdio", ""])
def test_stdio_has_nothing_to_probe(monkeypatch, closed_port, transport):
    _configure(monkeypatch, closed_port, transport)
    assert healthcheck.main() == 0


@pytest.mark.parametrize(
    ("host", "expected"),
    [
        (None, ["127.0.0.1"]),
        ("0.0.0.0", ["127.0.0.1"]),  # noqa: S104
        # A '::' bind is usually dual-stack; containers often lack IPv6 loopback.
        ("::", ["::1", "127.0.0.1"]),
        ("127.0.0.1", ["127.0.0.1"]),
        (" 172.18.0.5 ", ["172.18.0.5"]),
        ("[fd00::5]", ["fd00::5"]),
        ("[::]", ["::1", "127.0.0.1"]),
    ],
)
def test_probe_hosts_follow_the_bind_address(monkeypatch, host, expected):
    if host is None:
        monkeypatch.delenv("MCP_HTTP_HOST", raising=False)
    else:
        monkeypatch.setenv("MCP_HTTP_HOST", host)
    assert healthcheck.probe_hosts() == expected


def test_ipv6_wildcard_falls_back_to_ipv4_loopback(monkeypatch, healthy_port):
    """The ::1 probe fails without IPv6 loopback; 127.0.0.1 must still pass."""
    _configure(monkeypatch, healthy_port)
    monkeypatch.setenv("MCP_HTTP_HOST", "::")
    assert healthcheck.main() == 0


def test_transport_from_dotenv_is_probed(monkeypatch, closed_port):
    """A transport set only in .env must not be mistaken for stdio."""
    monkeypatch.delenv("MCP_TRANSPORT", raising=False)
    monkeypatch.setenv("MCP_HTTP_PORT", str(closed_port))

    def fake_load_dotenv() -> None:
        monkeypatch.setenv("MCP_TRANSPORT", "http")

    monkeypatch.setattr(healthcheck, "load_dotenv", fake_load_dotenv)
    assert healthcheck.main() == 1


def test_real_server_health_endpoint_needs_no_token(monkeypatch, closed_port, tmp_path):
    """End to end: the server's /health answers the probe, bearer auth or not."""
    port = closed_port
    env = {
        **os.environ,
        "LIBRENMS_URL": "https://nms.invalid",
        "LIBRENMS_TOKEN": "t",
        "MCP_TRANSPORT": "http",
        "MCP_HTTP_HOST": "127.0.0.1",
        "MCP_HTTP_PORT": str(port),
        "MCP_HTTP_BEARER_TOKEN": "secret",
        "SENTRY_DSN": "",
    }
    server = subprocess.Popen(
        [sys.executable, "-c", "import librenms_mcp.server as s; s.main()"],
        env=env,
        cwd=tmp_path,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        _configure(monkeypatch, port)
        deadline = time.monotonic() + 30
        while healthcheck.main() != 0:
            assert server.poll() is None, "server exited"
            assert time.monotonic() < deadline, "server never became healthy"
            time.sleep(0.3)
    finally:
        server.terminate()
        server.wait(timeout=10)
