"""Canvas resources — read-only state + populated HTML artifact."""

from __future__ import annotations

import json

from fastmcp.resources import resource

from src.auth import AuthError, current_user_id
from src.renderer.artifact import render_canvas_html
from src.storage import CanvasNotFound
from src.store_singleton import store


@resource("canvas://{canvas_id}/state")
def canvas_state(canvas_id: str) -> str:
    """JSON snapshot of canvas state — used by formatters and renderers."""
    try:
        user = current_user_id()
    except AuthError as e:
        raise ValueError(f"unauthorized: {e}") from e
    try:
        c = store.get_canvas(user_id=user, canvas_id=canvas_id)
    except CanvasNotFound as e:
        raise ValueError(f"canvas not found: {e}") from e
    return json.dumps(
        {
            "canvas_id": c.canvas_id,
            "deliverable_type": c.deliverable_type,
            "client_id": c.client_id,
            "title": c.title,
            "template_id": c.template_id,
            "meta": c.meta,
            "finalized": c.finalized,
            "sections": [
                {"id": s.id, "title": s.title, "body": s.body, "revision": s.revision}
                for s in c.sections
            ],
        },
        indent=2,
    )


@resource("canvas://{canvas_id}/artifact")
def canvas_artifact(canvas_id: str) -> str:
    """Populated read-only HTML artifact for Claude Desktop Live Artifact rendering."""
    try:
        user = current_user_id()
    except AuthError as e:
        raise ValueError(f"unauthorized: {e}") from e
    try:
        c = store.get_canvas(user_id=user, canvas_id=canvas_id)
    except CanvasNotFound as e:
        raise ValueError(f"canvas not found: {e}") from e
    return render_canvas_html(c)
