"""Server invariants — zero tools, resource families discoverable, /health."""

from __future__ import annotations


async def test_no_tools_registered(client):
    """Resource-only invariant — the MCP exposes zero @tool functions."""
    tools = await client.list_tools()
    assert tools == [], f"expected zero tools, got {[t.name for t in tools]}"


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


async def test_skill_exposed_as_resource(client):
    resources = await client.list_resources()
    uris = [str(r.uri) for r in resources]
    assert any("skill://deliverable-canvas" in u for u in uris)
