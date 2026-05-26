"""Test fixtures.

The MCP is resource-only (zero tools, no DB). Tests use an in-memory FastMCP
``Client`` against the live ``mcp`` instance — no temp files, no storage setup.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
async def client(monkeypatch: pytest.MonkeyPatch):
    # Ensure OAuth is off for in-memory tests; auth is enforced at deploy time.
    monkeypatch.setenv("OAUTH_ENABLE", "false")
    for mod in ["src.config", "src.auth", "src.server"]:
        sys.modules.pop(mod, None)

    from fastmcp.client import Client

    from src.server import mcp

    async with Client(transport=mcp) as c:
        yield c
