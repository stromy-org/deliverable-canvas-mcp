"""Resource-discovery + resource-content tests.

The MCP exposes four resource families and zero tools (resource-only refactor,
2026-05-26). These tests assert the resource surface is intact and shaped per
the canonical contract in `PLAN_canvas_stateless_refactor.md` Component 0.
"""

from __future__ import annotations

import json

import pytest


async def test_template_list_returns_known_ids(client):
    res = await client.read_resource("template://list")
    body = json.loads(res[0].text)
    assert "templates" in body
    assert "proposal_v1" in body["templates"]


async def test_template_proposal_v1_shape(client):
    res = await client.read_resource("template://proposal_v1")
    body = json.loads(res[0].text)
    assert body["template_id"] == "proposal_v1"
    assert isinstance(body.get("methodology_version"), str)
    assert body["methodology_version"]  # non-empty
    assert isinstance(body["sections"], list)
    assert len(body["sections"]) >= 1
    for section in body["sections"]:
        assert isinstance(section.get("id"), str) and section["id"]
        assert isinstance(section.get("title"), str) and section["title"]
        assert isinstance(section.get("prompt_hint"), str) and section["prompt_hint"]


async def test_template_unknown_raises(client):
    with pytest.raises(Exception) as ei:
        await client.read_resource("template://nonexistent_v999")
    assert "unknown template_id" in str(ei.value).lower()


async def test_methodology_planning_best_practices_loads(client):
    res = await client.read_resource("methodology://planning-best-practices")
    text = res[0].text
    assert text.strip()
    assert "version:" in text  # frontmatter
    # Spot-check the planning ritual is documented.
    assert "canvas_id" in text


async def test_methodology_rendering_claude_loads(client):
    res = await client.read_resource("methodology://rendering/claude")
    text = res[0].text
    assert text.strip()
    assert "markdown" in text.lower()
    assert "## " in text  # mentions heading rule
    assert "canvas-<canvas_id>" in text  # identifier convention


async def test_methodology_rendering_cowork_loads(client):
    res = await client.read_resource("methodology://rendering/cowork")
    text = res[0].text
    assert text.strip()
    # Component 14 identifier convention literal.
    assert "canvas-<canvas_id>-<deliverable_type>" in text
    # Forbids HTML artifact with callMcpTool bridge.
    assert "callMcpTool" in text


async def test_methodology_rendering_codex_loads(client):
    res = await client.read_resource("methodology://rendering/codex")
    text = res[0].text
    assert text.strip()
    assert "placeholder" in text.lower()


async def test_methodology_rendering_unknown_provider_raises(client):
    with pytest.raises(Exception) as ei:
        await client.read_resource("methodology://rendering/nonexistent")
    assert "unknown rendering provider" in str(ei.value).lower()
