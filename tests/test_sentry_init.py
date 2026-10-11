"""Sentry stays off unless a real DSN is configured."""

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
