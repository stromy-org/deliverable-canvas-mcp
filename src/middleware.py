"""Middleware that logs every MCP tool call with input, user identity, and duration."""

import logging
import time

from fastmcp.server.middleware import Middleware, MiddlewareContext

logger = logging.getLogger(__name__)


def _identify_user() -> str:
    """Best-effort user identity from the OAuth access token claims.

    Falls back to ``"anonymous"`` when OAuth is disabled or the token is absent
    (e.g. stdio transport). Storage scoping uses ``auth.current_user_id()`` which
    is stricter — this is only for log fields.
    """
    try:
        from fastmcp.server.dependencies import get_access_token

        token = get_access_token()
        if token and token.claims:
            return (
                token.claims.get("email")
                or token.claims.get("preferred_username")
                or token.claims.get("sub")
                or "authenticated"
            )
    except Exception:
        pass
    return "anonymous"


class ToolCallLoggingMiddleware(Middleware):

    async def on_call_tool(self, context: MiddlewareContext, call_next):
        tool_name = context.message.name
        tool_input = context.message.arguments or {}
        user_email = _identify_user()
        start = time.perf_counter()

        fields = {
            "event": "tool_call",
            "tool": tool_name,
            "input": tool_input,
            "user_email": user_email,
        }

        try:
            result = await call_next(context)
            duration_ms = round((time.perf_counter() - start) * 1000)
            fields.update({"duration_ms": duration_ms, "status": "ok"})
            logger.info(
                "tool_call %s",
                tool_name,
                extra={"json_fields": fields},
            )
            return result
        except Exception as exc:
            duration_ms = round((time.perf_counter() - start) * 1000)
            fields.update({
                "duration_ms": duration_ms,
                "status": "error",
                "error": str(exc),
            })
            logger.error(
                "tool_call %s failed",
                tool_name,
                extra={"json_fields": fields},
            )
            raise
