"""Sentry stays off unless a real DSN is configured."""

import importlib.metadata
import logging
import sys
import types

import pytest

from librenms_mcp.sentry_init import _data_collection
from librenms_mcp.sentry_init import init_sentry


@pytest.mark.parametrize("dsn", ["", "   "])
def test_blank_dsn_means_sentry_is_not_configured(monkeypatch, caplog, dsn):
    """A whitespace-only DSN used to fail sentry_sdk.init on every start."""
    monkeypatch.setenv("SENTRY_DSN", dsn)
    with caplog.at_level(logging.WARNING):
        assert init_sentry() is False
    assert caplog.records == []


@pytest.mark.parametrize("name", ["SENTRY_SEND_DEFAULT_PII", "SENTRY_ENABLE_LOGS"])
def test_invalid_bool_leaves_sentry_off(monkeypatch, caplog, name):
    """As documented: an invalid value logs an error, it does not stop startup."""
    calls = []
    # Stand-ins for sentry-sdk, an optional extra that may not be installed.
    modules = {
        "sentry_sdk": types.SimpleNamespace(init=lambda **kw: calls.append(kw)),
        "sentry_sdk.integrations": types.SimpleNamespace(),
        "sentry_sdk.integrations.logging": types.SimpleNamespace(
            LoggingIntegration=lambda **_kwargs: None
        ),
        "sentry_sdk.integrations.mcp": types.SimpleNamespace(MCPIntegration=object),
    }
    for module_name, module in modules.items():
        monkeypatch.setitem(sys.modules, module_name, module)
    monkeypatch.setenv("SENTRY_DSN", "https://key@sentry.invalid/1")
    monkeypatch.setenv(name, "enable")
    with caplog.at_level(logging.ERROR):
        assert init_sentry() is False
    assert calls == []
    assert f"{name} must be one of" in caplog.text


SENTRY_ENV_VARS = (
    "SENTRY_TRACES_SAMPLE_RATE",
    "SENTRY_SEND_DEFAULT_PII",
    "SENTRY_ENVIRONMENT",
    "SENTRY_RELEASE",
    "SENTRY_PROFILE_SESSION_SAMPLE_RATE",
    "SENTRY_PROFILE_LIFECYCLE",
    "SENTRY_ENABLE_LOGS",
)


class _MCPIntegration:
    """Stand-in for sentry_sdk.integrations.mcp.MCPIntegration."""


class _LoggingIntegration:
    """Stand-in for sentry_sdk.integrations.logging.LoggingIntegration."""

    def __init__(self, **kwargs):
        self.kwargs = kwargs


@pytest.fixture
def fake_sentry(monkeypatch):
    """Record sentry_sdk.init() calls; sentry-sdk is an optional extra."""
    calls: list[dict] = []
    modules = {
        "sentry_sdk": types.SimpleNamespace(init=lambda **kw: calls.append(kw)),
        "sentry_sdk.integrations": types.SimpleNamespace(),
        "sentry_sdk.integrations.logging": types.SimpleNamespace(
            LoggingIntegration=_LoggingIntegration
        ),
        "sentry_sdk.integrations.mcp": types.SimpleNamespace(
            MCPIntegration=_MCPIntegration
        ),
    }
    for module_name, module in modules.items():
        monkeypatch.setitem(sys.modules, module_name, module)
    for name in SENTRY_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("SENTRY_DSN", " https://key@sentry.invalid/1 ")
    return calls


def _logging_integration(kwargs: dict) -> _LoggingIntegration:
    [integration] = [
        i for i in kwargs["integrations"] if isinstance(i, _LoggingIntegration)
    ]
    return integration


def test_defaults_send_no_pii_and_name_the_package_release(
    fake_sentry, monkeypatch, caplog
):
    """Only SENTRY_DSN set: no tool inputs/outputs, no Sentry logs, no
    profiling, release = this package."""
    asked = []

    def version(name: str) -> str:
        asked.append(name)
        return "9.8.7"

    monkeypatch.setattr(importlib.metadata, "version", version)
    with caplog.at_level(logging.INFO):
        assert init_sentry() is True

    [kwargs] = fake_sentry
    integrations = kwargs.pop("integrations")
    # sentry-sdk 3.x stopped enabling the logging integration on its own;
    # without it logged errors never reach Sentry.
    assert [type(i) for i in integrations] == [_MCPIntegration, _LoggingIntegration]
    assert integrations[1].kwargs == {"level": None, "event_level": logging.ERROR}
    collection = kwargs.pop("data_collection")
    assert collection["mcp"] == {"inputs": False, "outputs": False}
    assert collection["gen_ai"] == {"inputs": False, "outputs": False}
    assert collection["user_info"] is False
    # Over the HTTP transports, request bodies are MCP calls with tool arguments.
    assert collection["http_bodies"] == []
    # A tool's arguments are locals of the frame that raised.
    assert collection["stack_frame_variables"] is False
    assert collection["cookies"] == {"mode": "off"}
    assert kwargs == {
        "dsn": "https://key@sentry.invalid/1",
        "traces_sample_rate": 1.0,
        "environment": None,
        "release": "9.8.7",
        "profile_session_sample_rate": 0.0,
        "profile_lifecycle": "trace",
    }
    # The distribution name from pyproject.toml, or the lookup always fails.
    assert asked == ["librenms-mcp"]
    assert "Sentry monitoring enabled (traces_sample_rate=1.0" in caplog.text
    assert "environment=default" in caplog.text


def test_settings_are_read_from_the_environment(fake_sentry, monkeypatch):
    monkeypatch.setenv("SENTRY_TRACES_SAMPLE_RATE", "0.25")
    monkeypatch.setenv("SENTRY_SEND_DEFAULT_PII", "yes")
    monkeypatch.setenv("SENTRY_ENVIRONMENT", " staging ")
    monkeypatch.setenv("SENTRY_RELEASE", "1.2.3")
    monkeypatch.setenv("SENTRY_PROFILE_SESSION_SAMPLE_RATE", "0")
    monkeypatch.setenv("SENTRY_PROFILE_LIFECYCLE", "manual")
    monkeypatch.setenv("SENTRY_ENABLE_LOGS", "off")

    assert init_sentry() is True

    [kwargs] = fake_sentry
    assert kwargs["traces_sample_rate"] == 0.25
    # Opting in keeps the SDK defaults, except that secret-looking frame
    # locals are still filtered.
    assert kwargs["data_collection"] == {
        "stack_frame_variables": {"mode": "denylist", "terms": []}
    }
    assert kwargs["environment"] == "staging"
    assert kwargs["release"] == "1.2.3"
    assert kwargs["profile_session_sample_rate"] == 0.0
    assert kwargs["profile_lifecycle"] == "manual"
    # An explicit SENTRY_ENABLE_LOGS wins over the PII setting.
    assert _logging_integration(kwargs).kwargs == {
        "level": None,
        "event_level": logging.ERROR,
    }


@pytest.mark.parametrize(
    ("pii", "logs", "expected_level"),
    [
        # Log lines carry LibreNMS request URLs with device hostnames and IP
        # addresses, so they follow the PII choice...
        (None, None, None),
        ("true", None, logging.INFO),
        # ...unless SENTRY_ENABLE_LOGS says otherwise.
        (None, "true", logging.INFO),
        ("true", "false", None),
    ],
)
def test_sentry_logs_follow_the_pii_setting_by_default(
    fake_sentry, monkeypatch, pii, logs, expected_level
):
    if pii is not None:
        monkeypatch.setenv("SENTRY_SEND_DEFAULT_PII", pii)
    if logs is not None:
        monkeypatch.setenv("SENTRY_ENABLE_LOGS", logs)
    assert init_sentry() is True
    assert _logging_integration(fake_sentry[0]).kwargs == {
        "level": expected_level,
        "event_level": logging.ERROR,
    }


def test_profiling_is_off_by_default(fake_sentry):
    assert init_sentry() is True
    assert fake_sentry[0]["profile_session_sample_rate"] == 0.0


def test_unknown_profile_lifecycle_falls_back_to_trace(fake_sentry, monkeypatch):
    monkeypatch.setenv("SENTRY_PROFILE_LIFECYCLE", "continuous")
    init_sentry()
    assert fake_sentry[0]["profile_lifecycle"] == "trace"


def test_release_is_none_when_the_package_is_not_installed(fake_sentry, monkeypatch):
    def missing(_name: str) -> str:
        raise importlib.metadata.PackageNotFoundError

    monkeypatch.setattr(importlib.metadata, "version", missing)
    assert init_sentry() is True
    assert fake_sentry[0]["release"] is None


def test_invalid_sample_rate_leaves_sentry_off(fake_sentry, monkeypatch, caplog):
    monkeypatch.setenv("SENTRY_TRACES_SAMPLE_RATE", "half")
    with caplog.at_level(logging.ERROR):
        assert init_sentry() is False
    assert fake_sentry == []
    assert "SENTRY_TRACES_SAMPLE_RATE must be a number, got 'half'" in caplog.text


@pytest.mark.parametrize(
    "name", ["SENTRY_TRACES_SAMPLE_RATE", "SENTRY_PROFILE_SESSION_SAMPLE_RATE"]
)
@pytest.mark.parametrize("value", ["50", "-0.1", "1.01"])
def test_out_of_range_sample_rate_leaves_sentry_off(
    fake_sentry, monkeypatch, caplog, name, value
):
    """A rate of 50 meant as a percentage must not reach the SDK."""
    monkeypatch.setenv(name, value)
    with caplog.at_level(logging.ERROR):
        assert init_sentry() is False
    assert fake_sentry == []
    assert f"{name} must be between 0.0 and 1.0" in caplog.text


@pytest.mark.parametrize("value", ["0", "1", "1.0"])
def test_sample_rate_bounds_are_accepted(fake_sentry, monkeypatch, value):
    monkeypatch.setenv("SENTRY_TRACES_SAMPLE_RATE", value)
    assert init_sentry() is True
    assert fake_sentry[0]["traces_sample_rate"] == float(value)


def test_init_failure_is_logged_not_raised(fake_sentry, monkeypatch, caplog):
    def failing_init(**_kwargs):
        raise RuntimeError("bad dsn")

    monkeypatch.setattr(sys.modules["sentry_sdk"], "init", failing_init)
    with caplog.at_level(logging.ERROR):
        assert init_sentry() is False
    assert "Failed to initialize Sentry: bad dsn" in caplog.text
    assert fake_sentry == []


def test_missing_sentry_sdk_warns_and_stays_off(monkeypatch, caplog):
    monkeypatch.setenv("SENTRY_DSN", "https://key@sentry.invalid/1")
    # A None entry makes the import raise ImportError.
    monkeypatch.setitem(sys.modules, "sentry_sdk", None)
    with caplog.at_level(logging.WARNING):
        assert init_sentry() is False
    assert "Sentry SDK not installed but SENTRY_DSN is configured" in caplog.text


@pytest.mark.parametrize("send_default_pii", [False, True])
def test_data_collection_is_accepted_by_the_real_sdk(send_default_pii):
    """The other tests stub sentry_sdk, so a key or mode the SDK rejects would
    only surface at startup, leaving Sentry silently off."""
    sentry_sdk = pytest.importorskip("sentry_sdk")
    # No integrations: they patch libraries process-wide even without a DSN.
    client = sentry_sdk.Client(
        data_collection=_data_collection(send_default_pii),
        default_integrations=False,
        auto_enabling_integrations=False,
    )
    try:
        resolved = client.options["data_collection"]
    finally:
        client.close()
    assert resolved["mcp"]["inputs"] is send_default_pii
    if send_default_pii:
        assert resolved["stack_frame_variables"]["mode"] == "denylist"
    else:
        assert resolved["stack_frame_variables"] is False


def _capture_frame_vars(send_default_pii):
    """Raise inside a real client and return the raising frame's variables."""
    sentry_sdk = pytest.importorskip("sentry_sdk")
    events = []
    client = sentry_sdk.Client(
        dsn="https://key@example.invalid/1",
        data_collection=_data_collection(send_default_pii),
        default_integrations=False,
        auto_enabling_integrations=False,
        before_send=lambda event, _hint: events.append(event),
    )

    # The arguments are the frame locals under test.
    def device_add(hostname, authpass):  # noqa: ARG001
        raise RuntimeError("boom")

    try:
        with sentry_sdk.isolation_scope() as scope:
            scope.set_client(client)
            try:
                device_add("switch1", "hunter2")
            except RuntimeError:
                sentry_sdk.capture_exception()
    finally:
        client.close()
    return events[0]["exception"]["values"][0]["stacktrace"]["frames"][-1].get("vars")


def test_frame_variables_are_not_sent_without_pii():
    assert _capture_frame_vars(send_default_pii=False) is None


def test_secret_frame_variables_are_filtered_with_pii():
    """sentry-sdk 3.x sends frame locals unfiltered by default."""
    frame_vars = _capture_frame_vars(send_default_pii=True)
    assert frame_vars["hostname"] == "'switch1'"
    assert "hunter2" not in str(frame_vars)
