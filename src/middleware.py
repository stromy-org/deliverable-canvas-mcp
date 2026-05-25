"""Middleware that logs every MCP tool call with input, user identity, and duration."""

import logging
import time

from fastmcp.server.middleware import Middleware, MiddlewareContext

logger = logging.getLogger(__name__)


def _identify_user() -> str:

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
