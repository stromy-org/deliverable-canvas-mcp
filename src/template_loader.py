"""Load section schemas from templates/<template_id>.json."""

from __future__ import annotations

import json
from pathlib import Path

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


class UnknownTemplate(Exception):
    pass


def list_template_ids() -> list[str]:
    if not TEMPLATES_DIR.is_dir():
        return []
    return sorted(p.stem for p in TEMPLATES_DIR.glob("*.json"))


def load_template(template_id: str) -> list[dict[str, str]]:
    """Returns a list of {id, title} section dicts for the given template_id.

    Raises UnknownTemplate with the available list if not found.
    """
    path = TEMPLATES_DIR / f"{template_id}.json"
    if not path.is_file():
        known = ", ".join(list_template_ids()) or "(none)"
        raise UnknownTemplate(f"Unknown template_id '{template_id}'. Known: {known}")
    data = json.loads(path.read_text(encoding="utf-8"))
    sections = data.get("sections", [])
    return [{"id": str(s["id"]), "title": str(s["title"])} for s in sections]
