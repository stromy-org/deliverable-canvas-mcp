"""Authentication + user identity for the deliverable-canvas MCP.

Two functions:

- ``build_auth_provider()`` returns the FastMCP ``AzureProvider`` (or ``None`` when
  ``OAUTH_ENABLE=false``). Wired into ``FastMCP(auth=...)`` in ``server.py``.
- ``current_user_id()`` returns the identity of the calling user, derived from the
  OAuth access token claims. Storage rows are scoped by this value so canvases are
  per-user isolated even on a shared MCP.

OAuth-disabled fallback: returns ``"local-dev"`` so the server is usable for local
testing without an Azure round-trip. Disabling OAuth in production is a deployment
error — the operator docs spell this out.
"""

from __future__ import annotations

import logging

from .config import settings

logger = logging.getLogger(__name__)


class AuthError(Exception):
    """Raised when user identity cannot be resolved. Surfaces as a tool error in FastMCP."""


def build_auth_provider():
    """Return an ``AzureProvider`` when OAuth is enabled, else ``None``.

    Mirrors the ``nl-gov-data`` / fastmcp-template pattern so operator setup is
    identical across the org's MCPs.
    """
    if not settings.oauth_enable:
        return None

    from fastmcp.server.auth.providers.azure import AzureProvider

    scopes = [s.strip() for s in settings.oauth_required_scopes.split(",") if s.strip()]

    missing = [
        name
        for name, value in (
            ("OAUTH_CLIENT_ID", settings.oauth_client_id),
            ("OAUTH_CLIENT_SECRET", settings.oauth_client_secret),
            ("OAUTH_TENANT_ID", settings.oauth_tenant_id),
            ("OAUTH_BASE_URL", settings.oauth_base_url),
        )
        if not value
    ]
    if not scopes:
        missing.append("OAUTH_REQUIRED_SCOPES")
    if missing:
        raise RuntimeError(
            "OAUTH_ENABLE=true but required Azure settings are missing: "
            + ", ".join(missing)
            + ". See infra-docs/ai/deliverable-canvas.md 'Auth' section."
        )

    if settings.fastmcp_transport == "stdio":
        logger.warning(
            "OAUTH_ENABLE=true with FASTMCP_TRANSPORT=stdio — "
            "FastMCP auth is not applied to stdio transport."
        )

    return AzureProvider(
        client_id=settings.oauth_client_id,
        client_secret=settings.oauth_client_secret,
        tenant_id=settings.oauth_tenant_id,
        base_url=settings.oauth_base_url,
        required_scopes=scopes,
    )


def current_user_id() -> str:
    """Return the user identity for the current request.

    Resolution order (first match wins):
      1. ``email`` claim — human-readable, stable per Entra user
      2. ``preferred_username`` claim — fallback for accounts without an email
      3. ``sub`` claim — opaque but always present
      4. ``"local-dev"`` literal when OAuth is disabled (dev mode only)

    Raises ``AuthError`` when OAuth is enabled but no token / claims are available.
    """
    if not settings.oauth_enable:
        return "local-dev"

    try:
        from fastmcp.server.dependencies import get_access_token

        token = get_access_token()
    except Exception as e:
        raise AuthError(f"no access token in request context: {e}") from e

    if not token or not token.claims:
        raise AuthError("access token present but claims missing")

    for claim in ("email", "preferred_username", "sub"):
        value = token.claims.get(claim)
        if value:
            return str(value)

    raise AuthError("access token has no email/preferred_username/sub claim")
