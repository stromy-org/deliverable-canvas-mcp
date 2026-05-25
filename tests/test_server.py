"""Tool surface integration tests via in-memory FastMCP Client."""

from __future__ import annotations

import pytest


async def _create(client) -> str:
    res = await client.call_tool(
        name="canvas_create",
        arguments={
            "deliverable_type": "proposal",
            "client_id": "dukestrategies",
            "title": "Test proposal",
            "template_id": "proposal_v1",
            "brief": "Pilot brief",
            "opened_by_skill": "proposal",
            "methodology_version": "v1",
        },
    )
    return res.data["canvas_id"]


async def test_canvas_create_with_template(client):
    res = await client.call_tool(
        name="canvas_create",
        arguments={
            "deliverable_type": "proposal",
            "client_id": "dukestrategies",
            "title": "Test",
            "template_id": "proposal_v1",
        },
    )
    data = res.data
    assert data["canvas_id"]
    assert len(data["sections"]) == 7
    assert data["sections"][0]["id"] == "context"
    assert data["finalized"] is False


async def test_canvas_create_unknown_template(client):
    with pytest.raises(Exception) as ei:
        await client.call_tool(
            name="canvas_create",
            arguments={
                "deliverable_type": "proposal",
                "client_id": "dukestrategies",
                "title": "Test",
                "template_id": "nope_v999",
            },
        )
    assert "Unknown template_id" in str(ei.value)


async def test_canvas_get(client):
    cid = await _create(client)
    res = await client.call_tool(name="canvas_get", arguments={"canvas_id": cid})
    assert res.data["canvas_id"] == cid
    assert res.data["meta"]["brief"] == "Pilot brief"


async def test_canvas_get_not_found(client):
    with pytest.raises(Exception) as ei:
        await client.call_tool(name="canvas_get", arguments={"canvas_id": "deadbeef"})
    assert "not found" in str(ei.value).lower()


async def test_canvas_update_section_appends_revision(client):
    cid = await _create(client)
    res1 = await client.call_tool(
        name="canvas_update_section",
        arguments={"canvas_id": cid, "section_id": "pricing", "body": "First", "instructed_by_user": True},
    )
    assert res1.data["revision"] == 1
    res2 = await client.call_tool(
        name="canvas_update_section",
        arguments={"canvas_id": cid, "section_id": "pricing", "body": "Second"},
    )
    assert res2.data["revision"] == 2
    revs = await client.call_tool(
        name="canvas_list_revisions",
        arguments={"canvas_id": cid, "section_id": "pricing"},
    )
    assert len(revs.data) == 2
    assert revs.data[0]["instructed_by_user"] == 1
    assert revs.data[1]["instructed_by_user"] == 0


async def test_canvas_update_section_unknown_section(client):
    cid = await _create(client)
    with pytest.raises(Exception) as ei:
        await client.call_tool(
            name="canvas_update_section",
            arguments={"canvas_id": cid, "section_id": "nope", "body": "x"},
        )
    assert "section not found" in str(ei.value).lower()


async def test_canvas_finalize_is_idempotent_and_locks_writes(client):
    cid = await _create(client)
    res = await client.call_tool(name="canvas_finalize", arguments={"canvas_id": cid})
    assert res.data["finalized"] is True
    res2 = await client.call_tool(name="canvas_finalize", arguments={"canvas_id": cid})
    assert res2.data["finalized"] is True  # idempotent
    with pytest.raises(Exception) as ei:
        await client.call_tool(
            name="canvas_update_section",
            arguments={"canvas_id": cid, "section_id": "pricing", "body": "post-final"},
        )
    assert "finalized" in str(ei.value).lower()


async def test_canvas_list_filters(client):
    cid_a = await _create(client)
    await client.call_tool(
        name="canvas_create",
        arguments={
            "deliverable_type": "messaging-framework",
            "client_id": "amaris",
            "title": "Amaris framing",
        },
    )
    only_dukes = await client.call_tool(
        name="canvas_list", arguments={"client_id": "dukestrategies"}
    )
    cids = {c["canvas_id"] for c in only_dukes.data}
    assert cid_a in cids
    assert all(c["client_id"] == "dukestrategies" for c in only_dukes.data)


async def test_canvas_state_resource(client):
    cid = await _create(client)
    res = await client.read_resource(f"canvas://{cid}/state")
    assert len(res) > 0
    text = res[0].text
    assert cid in text
    assert "proposal" in text


async def test_canvas_artifact_resource(client):
    cid = await _create(client)
    await client.call_tool(
        name="canvas_update_section",
        arguments={"canvas_id": cid, "section_id": "context", "body": "**Bold** context"},
    )
    res = await client.read_resource(f"canvas://{cid}/artifact")
    html = res[0].text
    assert "<html" in html
    assert "Test proposal" in html
    assert "<strong>Bold</strong>" in html


async def test_skills_exposed_as_resources(client):
    resources = await client.list_resources()
    uris = [str(r.uri) for r in resources]
    assert any("skill://deliverable-canvas" in u for u in uris)
