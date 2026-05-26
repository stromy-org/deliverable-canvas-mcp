"""Auth tests for the Microsoft Entra OAuth provider + identity."""

from __future__ import annotations

import sys

import pytest


def _reload_auth(monkeypatch: pytest.MonkeyPatch, **env: str):
    for key, value in env.items():
        monkeypatch.setenv(key.upper(), value)
    for mod in ["src.config", "src.auth"]:
        sys.modules.pop(mod, None)
    import importlib

    return importlib.import_module("src.auth")


def test_oauth_disabled_returns_local_dev(monkeypatch: pytest.MonkeyPatch):
    auth = _reload_auth(monkeypatch, OAUTH_ENABLE="false")
    assert auth.current_user_id() == "local-dev"
    assert auth.build_auth_provider() is None


def test_oauth_enabled_missing_settings_raises(monkeypatch: pytest.MonkeyPatch):
    auth = _reload_auth(
        monkeypatch,
        OAUTH_ENABLE="true",
        OAUTH_CLIENT_ID="",
        OAUTH_CLIENT_SECRET="",
        OAUTH_TENANT_ID="",
        OAUTH_BASE_URL="",
        OAUTH_REQUIRED_SCOPES="",
    )
    with pytest.raises(RuntimeError, match="OAUTH_ENABLE=true"):
        auth.build_auth_provider()


def test_current_user_id_raises_without_token(monkeypatch: pytest.MonkeyPatch):
    """When OAuth is on but the call happens outside an HTTP context (no token)."""
    auth = _reload_auth(
        monkeypatch,
        OAUTH_ENABLE="true",
        OAUTH_CLIENT_ID="dummy",
        OAUTH_CLIENT_SECRET="dummy",
        OAUTH_TENANT_ID="dummy",
        OAUTH_BASE_URL="https://example.test",
        OAUTH_REQUIRED_SCOPES="mcp.access offline_access",
    )
    with pytest.raises(auth.AuthError):
        auth.current_user_id()


def test_oauth_scopes_whitespace_delimited_single(monkeypatch: pytest.MonkeyPatch):
    """Single-scope value parses to a one-element list (RFC 6749 whitespace split)."""
    auth = _reload_auth(
        monkeypatch,
        OAUTH_ENABLE="true",
        OAUTH_CLIENT_ID="dummy",
        OAUTH_CLIENT_SECRET="dummy",
        OAUTH_TENANT_ID="dummy",
        OAUTH_BASE_URL="https://example.test",
        OAUTH_REQUIRED_SCOPES="mcp.access",
    )
    # Patch AzureProvider so we can inspect what scopes get passed in without
    # actually hitting Azure.
    captured: dict[str, list[str]] = {}

    class _FakeAzureProvider:
        def __init__(self, **kwargs):
            captured["required_scopes"] = kwargs["required_scopes"]

    import fastmcp.server.auth.providers.azure as azure_mod

    monkeypatch.setattr(azure_mod, "AzureProvider", _FakeAzureProvider)
    auth.build_auth_provider()
    assert captured["required_scopes"] == ["mcp.access"]


def test_oauth_scopes_whitespace_delimited_multi(monkeypatch: pytest.MonkeyPatch):
    """Multi-scope value parses by whitespace into separate scope strings."""
    auth = _reload_auth(
        monkeypatch,
        OAUTH_ENABLE="true",
        OAUTH_CLIENT_ID="dummy",
        OAUTH_CLIENT_SECRET="dummy",
        OAUTH_TENANT_ID="dummy",
        OAUTH_BASE_URL="https://example.test",
        OAUTH_REQUIRED_SCOPES="mcp.access offline_access",
    )
    captured: dict[str, list[str]] = {}

    class _FakeAzureProvider:
        def __init__(self, **kwargs):
            captured["required_scopes"] = kwargs["required_scopes"]

    import fastmcp.server.auth.providers.azure as azure_mod

    monkeypatch.setattr(azure_mod, "AzureProvider", _FakeAzureProvider)
    auth.build_auth_provider()
    assert captured["required_scopes"] == ["mcp.access", "offline_access"]
