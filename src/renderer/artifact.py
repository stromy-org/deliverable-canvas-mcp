"""Render a canvas to a read-only HTML artifact for Claude Desktop."""

from __future__ import annotations

import html
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from ..storage import Canvas

TEMPLATE_DIR = Path(__file__).parent
_env = Environment(
    loader=FileSystemLoader(str(TEMPLATE_DIR)),
    autoescape=select_autoescape(["html"]),
)


def _md_inline(text: str) -> str:
    """Minimal markdown → HTML for body text (paragraphs + line breaks + bold/italic).

    Deliberately tiny — the artifact is read-only and we avoid pulling a full markdown lib
    into the MCP runtime. Bodies are author-trusted plain text/markdown.
    """
    esc = html.escape(text)
    # bold then italic
    import re

    esc = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", esc)
    esc = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", esc)
    paragraphs = [p.strip() for p in esc.split("\n\n") if p.strip()]
    return "\n".join(f"<p>{p.replace(chr(10), '<br/>')}</p>" for p in paragraphs)


def _fmt_ts(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=UTC).strftime("%Y-%m-%d %H:%M UTC")


def render_canvas_html(canvas: Canvas) -> str:
    template = _env.get_template("artifact.html.j2")
    sections: list[dict[str, Any]] = [
        {
            "id": s.id,
            "title": s.title,
            "body_html": _md_inline(s.body) if s.body else '<p class="empty">(empty)</p>',
            "revision": s.revision,
            "updated": _fmt_ts(s.updated_ts),
        }
        for s in canvas.sections
    ]
    return template.render(
        title=canvas.title,
        client_id=canvas.client_id,
        deliverable_type=canvas.deliverable_type,
        finalized=canvas.finalized,
        updated=_fmt_ts(canvas.updated_ts),
        sections=sections,
    )
