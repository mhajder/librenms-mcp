"""Sentry stays off unless a real DSN is configured."""

import importlib.metadata
import logging
import sys
import types

import pytest

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


@pytest.fixture
def fake_sentry(monkeypatch):
    """Record sentry_sdk.init() calls; sentry-sdk is an optional extra."""
    calls: list[dict] = []
    modules = {
        "sentry_sdk": types.SimpleNamespace(init=lambda **kw: calls.append(kw)),
        "sentry_sdk.integrations": types.SimpleNamespace(),
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


def test_defaults_send_no_pii_and_name_the_package_release(
    fake_sentry, monkeypatch, caplog
):
    """Only SENTRY_DSN set: no tool inputs/outputs, release = this package."""
    asked = []

    def version(name: str) -> str:
        asked.append(name)
        return "9.8.7"

    monkeypatch.setattr(importlib.metadata, "version", version)
    with caplog.at_level(logging.INFO):
        assert init_sentry() is True

    [kwargs] = fake_sentry
    integrations = kwargs.pop("integrations")
    assert [type(i) for i in integrations] == [_MCPIntegration]
    assert kwargs == {
        "dsn": "https://key@sentry.invalid/1",
        "traces_sample_rate": 1.0,
        "send_default_pii": False,
        "environment": None,
        "release": "9.8.7",
        "profile_session_sample_rate": 1.0,
        "profile_lifecycle": "trace",
        "enable_logs": True,
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
    assert kwargs["send_default_pii"] is True
    assert kwargs["environment"] == "staging"
    assert kwargs["release"] == "1.2.3"
    assert kwargs["profile_session_sample_rate"] == 0.0
    assert kwargs["profile_lifecycle"] == "manual"
    assert kwargs["enable_logs"] is False


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
