"""Storage-layer unit tests: persistence-across-restart, backup/restore, per-user isolation."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.storage import CanvasFinalized, CanvasNotFound, CanvasStore


def _mk_sections() -> list[dict[str, str]]:
    return [
        {"id": "context", "title": "Context"},
        {"id": "pricing", "title": "Pricing"},
    ]


def test_create_and_get_round_trip(store_for: CanvasStore):
    c = store_for.create_canvas(
        user_id="t1",
        deliverable_type="proposal",
        client_id="c1",
        title="X",
        template_id="proposal_v1",
        template_sections=_mk_sections(),
        meta={"brief": "hello"},
    )
    got = store_for.get_canvas(user_id="t1", canvas_id=c.canvas_id)
    assert got.canvas_id == c.canvas_id
    assert got.meta["brief"] == "hello"
    assert [s.id for s in got.sections] == ["context", "pricing"]


def test_user_isolation(store_for: CanvasStore):
    c = store_for.create_canvas(
        user_id="t1",
        deliverable_type="proposal",
        client_id="c1",
        title="X",
        template_id=None,
        template_sections=_mk_sections(),
    )
    with pytest.raises(CanvasNotFound):
        store_for.get_canvas(user_id="t2", canvas_id=c.canvas_id)


def test_update_increments_revision_and_writes_log(store_for: CanvasStore):
    c = store_for.create_canvas(
        user_id="t1",
        deliverable_type="proposal",
        client_id="c1",
        title="X",
        template_id=None,
        template_sections=_mk_sections(),
    )
    store_for.update_section(
        user_id="t1",
        canvas_id=c.canvas_id,
        section_id="context",
        body="v1",
        summary=None,
        instructed_by_user=True,
    )
    store_for.update_section(
        user_id="t1",
        canvas_id=c.canvas_id,
        section_id="context",
        body="v2",
        summary="refine",
        instructed_by_user=False,
    )
    revs = store_for.list_revisions(user_id="t1", canvas_id=c.canvas_id, section_id="context")
    assert [r["revision"] for r in revs] == [1, 2]
    assert revs[0]["instructed_by_user"] == 1
    assert revs[1]["summary"] == "refine"


def test_update_unknown_section_upserts(store_for: CanvasStore):
    """Unknown section_id auto-creates the section (upsert semantics)."""
    c = store_for.create_canvas(
        user_id="t1",
        deliverable_type="proposal",
        client_id="c1",
        title="X",
        template_id=None,
        template_sections=_mk_sections(),
    )
    sec = store_for.update_section(
        user_id="t1",
        canvas_id=c.canvas_id,
        section_id="executive_summary",
        body="hello",
        summary="first write",
        instructed_by_user=True,
    )
    assert sec.id == "executive_summary"
    assert sec.body == "hello"
    assert sec.revision == 1
    refreshed = store_for.get_canvas(user_id="t1", canvas_id=c.canvas_id)
    new_section = next(s for s in refreshed.sections if s.id == "executive_summary")
    assert new_section.title == "Executive Summary"


def test_update_section_explicit_title(store_for: CanvasStore):
    c = store_for.create_canvas(
        user_id="t1",
        deliverable_type="proposal",
        client_id="c1",
        title="X",
        template_id=None,
        template_sections=[],
    )
    store_for.update_section(
        user_id="t1",
        canvas_id=c.canvas_id,
        section_id="intro",
        body="b",
        summary=None,
        instructed_by_user=False,
        title="Introduction & Context",
    )
    refreshed = store_for.get_canvas(user_id="t1", canvas_id=c.canvas_id)
    assert refreshed.sections[0].title == "Introduction & Context"


def test_finalize_idempotent_and_locks(store_for: CanvasStore):
    c = store_for.create_canvas(
        user_id="t1",
        deliverable_type="proposal",
        client_id="c1",
        title="X",
        template_id=None,
        template_sections=_mk_sections(),
    )
    f1 = store_for.finalize(user_id="t1", canvas_id=c.canvas_id)
    assert f1.finalized
    f2 = store_for.finalize(user_id="t1", canvas_id=c.canvas_id)
    assert f2.finalized
    with pytest.raises(CanvasFinalized):
        store_for.update_section(
            user_id="t1",
            canvas_id=c.canvas_id,
            section_id="context",
            body="post",
            summary=None,
            instructed_by_user=False,
        )


def test_persistence_across_restart(tmp_path: Path):
    db = tmp_path / "p.db"
    s1 = CanvasStore(db)
    c = s1.create_canvas(
        user_id="t1",
        deliverable_type="proposal",
        client_id="c1",
        title="X",
        template_id=None,
        template_sections=_mk_sections(),
        meta={"brief": "hello"},
    )
    s1.update_section(
        user_id="t1",
        canvas_id=c.canvas_id,
        section_id="context",
        body="durable",
        summary=None,
        instructed_by_user=True,
    )
    # "restart"
    s2 = CanvasStore(db)
    got = s2.get_canvas(user_id="t1", canvas_id=c.canvas_id)
    assert got.sections[0].body == "durable"
    assert got.sections[0].revision == 1
    assert got.meta["brief"] == "hello"


def test_backup_restore_drill(tmp_path: Path):
    db = tmp_path / "live.db"
    backup = tmp_path / "backup.db"
    store_a = CanvasStore(db)
    c = store_a.create_canvas(
        user_id="t1",
        deliverable_type="proposal",
        client_id="c1",
        title="X",
        template_id=None,
        template_sections=_mk_sections(),
    )
    store_a.update_section(
        user_id="t1",
        canvas_id=c.canvas_id,
        section_id="pricing",
        body="aggressive",
        summary=None,
        instructed_by_user=True,
    )
    store_a.backup_to(backup)

    # Wipe
    db.unlink()
    restored = CanvasStore.restore_from(backup_path=backup, db_path=db)
    got = restored.get_canvas(user_id="t1", canvas_id=c.canvas_id)
    assert got.sections[1].body == "aggressive"


def test_list_canvases_filters(store_for: CanvasStore):
    a = store_for.create_canvas(
        user_id="t1", deliverable_type="proposal", client_id="c1",
        title="A", template_id=None, template_sections=[],
    )
    b = store_for.create_canvas(
        user_id="t1", deliverable_type="press-release", client_id="c1",
        title="B", template_id=None, template_sections=[],
    )
    c = store_for.create_canvas(
        user_id="t1", deliverable_type="proposal", client_id="c2",
        title="C", template_id=None, template_sections=[],
    )
    only_c1 = store_for.list_canvases(
        user_id="t1", client_id="c1", deliverable_type=None, include_finalized=True
    )
    cids = {x["canvas_id"] for x in only_c1}
    assert {a.canvas_id, b.canvas_id} <= cids
    assert c.canvas_id not in cids

    only_proposal_c1 = store_for.list_canvases(
        user_id="t1", client_id="c1", deliverable_type="proposal", include_finalized=True
    )
    assert [x["canvas_id"] for x in only_proposal_c1] == [a.canvas_id]

    store_for.finalize(user_id="t1", canvas_id=a.canvas_id)
    drafts = store_for.list_canvases(
        user_id="t1", client_id=None, deliverable_type=None, include_finalized=False
    )
    drafts_ids = {x["canvas_id"] for x in drafts}
    assert a.canvas_id not in drafts_ids
    assert b.canvas_id in drafts_ids
