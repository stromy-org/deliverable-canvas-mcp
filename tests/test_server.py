"""Server invariants — only the generic fs tools, resource families, skill via fs."""

from __future__ import annotations

import pytest
from fastmcp.exceptions import ToolError


async def test_only_fs_tools_registered(client):
    """No domain tools — the only tools are the generic fs_read / fs_list."""
    tools = await client.list_tools()
    assert {t.name for t in tools} == {"fs_read", "fs_list"}


async def test_resource_families_registered(client):
    """All four resource families must be reachable."""
    resources = await client.list_resources()
    uris = [str(r.uri) for r in resources]
    # template://list is a concrete URI; template://{id} and
    # methodology://rendering/{provider} are templated and may surface as
    # resource templates rather than concrete resources.
    templates = await client.list_resource_templates()
    template_uris = [str(t.uriTemplate) for t in templates]
    all_uris = uris + template_uris

    assert any("template://list" in u for u in all_uris)
    assert any("template://" in u and "{" in u for u in template_uris)
    assert any("methodology://planning-best-practices" in u for u in all_uris)
    assert any("methodology://rendering/" in u for u in all_uris)


async def test_skill_not_exposed_as_resource(client):
    resources = await client.list_resources()
    uris = [str(r.uri) for r in resources]
    assert not any("skill://" in u for u in uris)


async def test_fs_list_skills(client):
    result = await client.call_tool(name="fs_list", arguments={"path": "skills"})
    names = {entry["name"] for entry in result.data}
    assert "deliverable-canvas" in names


async def test_fs_read_skill(client):
    result = await client.call_tool(
        name="fs_read", arguments={"path": "skills/deliverable-canvas/SKILL.md"}
    )
    assert len(result.data) > 0


async def test_fs_read_traversal_blocked(client):
    with pytest.raises(ToolError):
        await client.call_tool(name="fs_read", arguments={"path": "../pyproject.toml"})


async def test_fs_read_outside_roots_blocked(client):
    with pytest.raises(ToolError):
        await client.call_tool(name="fs_read", arguments={"path": "src/config.py"})
