"""Sentry stays off unless a real DSN is configured."""

import logging

import pytest

from librenms_mcp.sentry_init import init_sentry


@pytest.mark.parametrize("dsn", ["", "   "])
def test_blank_dsn_means_sentry_is_not_configured(monkeypatch, caplog, dsn):
    """A whitespace-only DSN used to fail sentry_sdk.init on every start."""
    monkeypatch.setenv("SENTRY_DSN", dsn)
    with caplog.at_level(logging.WARNING):
        assert init_sentry() is False
    assert caplog.records == []
