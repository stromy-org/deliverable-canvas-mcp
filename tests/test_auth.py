"""Auth resolution tests for the tenant API-key middleware."""

from __future__ import annotations

import sys

import pytest


def _reload_auth(monkeypatch: pytest.MonkeyPatch, tenants: str = ""):
    monkeypatch.setenv("DELIVERABLE_CANVAS_TENANTS", tenants)
    for mod in ["src.config", "src.auth"]:
        sys.modules.pop(mod, None)
    import importlib

    return importlib.import_module("src.auth")


def test_disabled_auth_returns_default(monkeypatch: pytest.MonkeyPatch):
    auth = _reload_auth(monkeypatch, "")
    assert auth.resolve_tenant() == "default"


def test_single_tenant_stdio_fallback(monkeypatch: pytest.MonkeyPatch):
    auth = _reload_auth(monkeypatch, "only:key1")
    assert auth.resolve_tenant() == "only"


def test_multi_tenant_no_context_raises(monkeypatch: pytest.MonkeyPatch):
    auth = _reload_auth(monkeypatch, "a:k1,b:k2")
    with pytest.raises(auth.AuthError):
        auth.resolve_tenant()
