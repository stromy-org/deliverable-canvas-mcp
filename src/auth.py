"""Tenant API-key resolver. Reads tenants from settings.deliverable_canvas_tenants.

Format: "tenant_id:api_key,tenant_id:api_key"
"""

from __future__ import annotations

from typing import Any

from fastmcp.server.dependencies import get_http_request
from starlette.requests import Request

from .config import settings


class AuthError(Exception):
    """Raised when authentication fails. Surfaces as a tool error in FastMCP."""


def _load_tenant_keys() -> dict[str, str]:
    raw = (settings.deliverable_canvas_tenants or "").strip()
    if not raw:
        return {}
    out: dict[str, str] = {}
    for pair in raw.split(","):
        pair = pair.strip()
        if not pair or ":" not in pair:
            continue
        key, value = pair.split(":", 1)
        out[key.strip()] = value.strip()
    return out


def _api_key_to_tenant() -> dict[str, str]:
    return {v: k for k, v in _load_tenant_keys().items()}


def _request_or_none() -> Request | None:
    try:
        return get_http_request()
    except Exception:
        return None


def resolve_tenant() -> str:
    """Returns the tenant_id for the current request.

    - HTTP transport: requires ``X-Tenant-Key`` header matching a configured tenant.
    - stdio transport (no HTTP context): if exactly one tenant configured, return it;
      otherwise raise AuthError. Disabled (empty mapping) → return "default" for dev.
    """
    mapping = _api_key_to_tenant()
    request = _request_or_none()

    if not mapping:
        # Auth disabled — dev only.
        return "default"

    if request is None:
        # No HTTP context (stdio). Single-tenant fallback.
        if len(mapping) == 1:
            return next(iter(mapping.values()))
        raise AuthError("Authentication required: missing tenant context (stdio)")

    api_key: Any = request.headers.get("x-tenant-key") or request.headers.get("X-Tenant-Key")
    if not api_key:
        raise AuthError("Missing X-Tenant-Key header")
    tenant = mapping.get(str(api_key))
    if tenant is None:
        raise AuthError("Invalid tenant API key")
    return tenant
