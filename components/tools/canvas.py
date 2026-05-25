"""Canvas tool surface — six tools, all writes durable before return."""

from __future__ import annotations

from typing import Any

from fastmcp.tools import tool

from src.auth import AuthError, resolve_tenant
from src.storage import CanvasFinalized, CanvasNotFound, SectionNotFound
from src.store_singleton import store
from src.template_loader import UnknownTemplate, load_template


def _canvas_dict(c: Any) -> dict[str, Any]:
    return {
        "canvas_id": c.canvas_id,
        "deliverable_type": c.deliverable_type,
        "client_id": c.client_id,
        "title": c.title,
        "template_id": c.template_id,
        "meta": c.meta,
        "finalized": c.finalized,
        "created_ts": c.created_ts,
        "updated_ts": c.updated_ts,
        "sections": [
            {
                "id": s.id,
                "title": s.title,
                "body": s.body,
                "revision": s.revision,
                "updated_ts": s.updated_ts,
            }
            for s in c.sections
        ],
    }


@tool
def canvas_create(
    deliverable_type: str,
    client_id: str,
    title: str,
    template_id: str | None = None,
    brief: str | None = None,
    opened_by_skill: str | None = None,
    methodology_version: str | None = None,
) -> dict[str, Any]:
    """Create a new canvas.

    ``brief``, ``opened_by_skill``, ``methodology_version`` are stored in ``meta`` so any
    resuming agent can re-orient without conversation history.
    """
    try:
        tenant = resolve_tenant()
    except AuthError as e:
        raise ValueError(f"unauthorized: {e}") from e
    if template_id:
        try:
            sections = load_template(template_id)
        except UnknownTemplate as e:
            raise ValueError(str(e)) from e
    else:
        sections = []
    meta = {
        "brief": brief,
        "opened_by_skill": opened_by_skill,
        "methodology_version": methodology_version,
    }
    canvas = store.create_canvas(
        tenant_id=tenant,
        deliverable_type=deliverable_type,
        client_id=client_id,
        title=title,
        template_id=template_id,
        template_sections=sections,
        meta=meta,
    )
    return _canvas_dict(canvas)


@tool
def canvas_get(canvas_id: str) -> dict[str, Any]:
    """Return full canvas state."""
    try:
        tenant = resolve_tenant()
    except AuthError as e:
        raise ValueError(f"unauthorized: {e}") from e
    try:
        canvas = store.get_canvas(tenant_id=tenant, canvas_id=canvas_id)
    except CanvasNotFound as e:
        raise ValueError(f"canvas not found: {e}") from e
    return _canvas_dict(canvas)


@tool
def canvas_update_section(
    canvas_id: str,
    section_id: str,
    body: str,
    summary: str | None = None,
    instructed_by_user: bool = False,
) -> dict[str, Any]:
    """Append a revision to the section. The agent self-reports ``instructed_by_user``."""
    try:
        tenant = resolve_tenant()
    except AuthError as e:
        raise ValueError(f"unauthorized: {e}") from e
    try:
        sec = store.update_section(
            tenant_id=tenant,
            canvas_id=canvas_id,
            section_id=section_id,
            body=body,
            summary=summary,
            instructed_by_user=instructed_by_user,
        )
    except CanvasNotFound as e:
        raise ValueError(f"canvas not found: {e}") from e
    except SectionNotFound as e:
        raise ValueError(f"section not found: {e}") from e
    except CanvasFinalized as e:
        raise ValueError(
            f"canvas is finalized; create a new canvas to continue editing: {e}"
        ) from e
    return {"id": sec.id, "body": sec.body, "revision": sec.revision, "updated_ts": sec.updated_ts}


@tool
def canvas_list_revisions(
    canvas_id: str,
    section_id: str | None = None,
) -> list[dict[str, Any]]:
    """Revision log. If section_id omitted, returns all revisions for the canvas."""
    try:
        tenant = resolve_tenant()
    except AuthError as e:
        raise ValueError(f"unauthorized: {e}") from e
    try:
        return store.list_revisions(tenant_id=tenant, canvas_id=canvas_id, section_id=section_id)
    except CanvasNotFound as e:
        raise ValueError(f"canvas not found: {e}") from e


@tool
def canvas_finalize(canvas_id: str) -> dict[str, Any]:
    """Mark canvas as finalized. Idempotent."""
    try:
        tenant = resolve_tenant()
    except AuthError as e:
        raise ValueError(f"unauthorized: {e}") from e
    try:
        canvas = store.finalize(tenant_id=tenant, canvas_id=canvas_id)
    except CanvasNotFound as e:
        raise ValueError(f"canvas not found: {e}") from e
    return _canvas_dict(canvas)


@tool
def canvas_list(
    client_id: str | None = None,
    deliverable_type: str | None = None,
    include_finalized: bool = True,
) -> list[dict[str, Any]]:
    """List canvases for the calling tenant."""
    try:
        tenant = resolve_tenant()
    except AuthError as e:
        raise ValueError(f"unauthorized: {e}") from e
    return store.list_canvases(
        tenant_id=tenant,
        client_id=client_id,
        deliverable_type=deliverable_type,
        include_finalized=include_finalized,
    )
