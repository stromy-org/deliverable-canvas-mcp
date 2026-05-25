"""Test fixtures. Each test gets a fresh tmp SQLite store + in-memory FastMCP Client."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def tmp_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db = tmp_path / "canvas.db"
    monkeypatch.setenv("CANVAS_DB_PATH", str(db))
    # Reload only modules that captured settings at import time. Do NOT pop src.storage
    # — its exception classes are imported into test modules, and re-importing would
    # create new class objects that pytest.raises wouldn't match.
    for mod in [
        "src.config",
        "src.store_singleton",
        "src.auth",
        "src.server",
        "components.tools.canvas",
        "components.resources.canvas_resources",
    ]:
        sys.modules.pop(mod, None)
    return db


@pytest.fixture
async def client(tmp_db: Path):
    from fastmcp.client import Client

    from src.server import mcp

    async with Client(transport=mcp) as c:
        yield c


@pytest.fixture
def store_for(tmp_db: Path):
    from src.storage import CanvasStore

    return CanvasStore(tmp_db)
