"""Deliverable Canvas MCP (FastMCP 3.0).

Uses FileSystemProvider for automatic component discovery from components/.
"""

from pathlib import Path

from fastmcp import FastMCP
from fastmcp.server.providers import FileSystemProvider
from starlette.requests import Request
from starlette.responses import JSONResponse

from .auth import build_auth_provider
from .config import settings
from .logging import setup_logging
from .middleware import ToolCallLoggingMiddleware

setup_logging()

PROJECT_ROOT = Path(__file__).parent.parent
COMPONENTS_DIR = PROJECT_ROOT / "components"

mcp = FastMCP(
    name="Deliverable Canvas MCP",
    instructions=(
        "Planning host for multi-section deliverables. Exposes templates + "
        "methodology as resources; the canvas itself is the chat artifact.\n\n"
        "The deliverable-canvas skill (procedural guide) is hosted as files "
        'under skills/. Call fs_list("skills") to discover it, then '
        'fs_read("skills/deliverable-canvas/SKILL.md") to load it and follow '
        "its instructions. fs_read / fs_list are the only tools."
    ),
    version="0.1.0",
    providers=[
        FileSystemProvider(COMPONENTS_DIR, reload=settings.mcp_dev_mode),
    ],
    auth=build_auth_provider(),
    middleware=[ToolCallLoggingMiddleware()],
)


@mcp.custom_route("/health", methods=["GET"])
async def health(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok", "service": "deliverable-canvas-mcp"})


if __name__ == "__main__":
    transport_kwargs = {}
    if settings.fastmcp_transport != "stdio":
        transport_kwargs["host"] = settings.fastmcp_host
        transport_kwargs["port"] = settings.fastmcp_port
    mcp.run(transport=settings.fastmcp_transport, **transport_kwargs)  # type: ignore[arg-type]
