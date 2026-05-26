"""Template resources — schemas for canvas section layouts.

Templates live as JSON files under ``components/resources/templates/<id>.json``
so they are part of the standard FastMCP components tree (and therefore
automatically copied into the Docker image alongside resources/prompts).

Exposed as MCP resources so the agent can discover and inspect available
templates before starting a canvas session:

- ``template://list``           → JSON array of available template IDs
- ``template://{template_id}``  → full template JSON (description, methodology_version,
  sections: [{id, title, prompt_hint}, ...])

The MCP is resource-only (no tools) — the agent renders the canvas in chat
based on the template's section layout and ``prompt_hint`` per section.
"""

from __future__ import annotations

import json
from pathlib import Path

from fastmcp.resources import resource

TEMPLATES_DIR = Path(__file__).parent / "templates"


def _list_ids() -> list[str]:
    if not TEMPLATES_DIR.is_dir():
        return []
    return sorted(p.stem for p in TEMPLATES_DIR.glob("*.json"))


@resource("template://list")
def template_list() -> str:
    """Available canvas template IDs — call before reading a specific template."""
    return json.dumps({"templates": _list_ids()}, indent=2)


@resource("template://{template_id}")
def template_schema(template_id: str) -> str:
    """Full template JSON: ``{template_id, description, methodology_version, sections}``."""
    path = TEMPLATES_DIR / f"{template_id}.json"
    if not path.is_file():
        known = ", ".join(_list_ids()) or "(none)"
        raise ValueError(f"unknown template_id '{template_id}'. Known: {known}")
    return path.read_text(encoding="utf-8")
