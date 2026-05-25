"""Resume drill: a fresh client connection (new session) lists + reads an existing canvas."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest


@pytest.fixture
def shared_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db = tmp_path / "canvas.db"
    monkeypatch.setenv("CANVAS_DB_PATH", str(db))
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


async def test_resume_via_list_then_get(shared_db: Path):
    from fastmcp.client import Client

    from src.server import mcp

    # Session 1: create + update + close
    async with Client(transport=mcp) as c1:
        created = await c1.call_tool(
            name="canvas_create",
            arguments={
                "deliverable_type": "proposal",
                "client_id": "dukestrategies",
                "title": "Resume target",
                "template_id": "proposal_v1",
                "brief": "Session-1 brief",
                "opened_by_skill": "proposal",
                "methodology_version": "v1",
            },
        )
        cid = created.data["canvas_id"]
        await c1.call_tool(
            name="canvas_update_section",
            arguments={"canvas_id": cid, "section_id": "pricing", "body": "Session-1 pricing"},
        )

    # Session 2: list then get — must find + re-read meta.
    async with Client(transport=mcp) as c2:
        listed = await c2.call_tool(
            name="canvas_list",
            arguments={"client_id": "dukestrategies", "deliverable_type": "proposal"},
        )
        cids = [c["canvas_id"] for c in listed.data]
        assert cid in cids
        got = await c2.call_tool(name="canvas_get", arguments={"canvas_id": cid})
        assert got.data["meta"]["brief"] == "Session-1 brief"
        assert got.data["meta"]["opened_by_skill"] == "proposal"
        pricing = [s for s in got.data["sections"] if s["id"] == "pricing"][0]
        assert pricing["body"] == "Session-1 pricing"
