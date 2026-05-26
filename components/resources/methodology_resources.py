"""Methodology resources — planning ritual + provider-specific rendering rules.

Resource-only MCP (post-2026-05-26 refactor): the agent reads these methodology
documents at session start to learn how to run a multi-section deliverable
session in chat. No tools — the canvas IS the chat artifact.

- ``methodology://planning-best-practices`` → universal planning ritual
- ``methodology://rendering/{provider}``    → host-specific rendering rules
"""

from __future__ import annotations

from pathlib import Path

from fastmcp.resources import resource

METHODOLOGY_DIR = Path(__file__).parent / "methodology"


def _read(relpath: str) -> str:
    path = METHODOLOGY_DIR / relpath
    if not path.is_file():
        raise ValueError(
            f"methodology file not found: {relpath}. "
            f"Expected under {METHODOLOGY_DIR}."
        )
    return path.read_text(encoding="utf-8")


@resource("methodology://planning-best-practices")
def methodology_planning() -> str:
    """Universal planning-ritual rules for a multi-section deliverable session."""
    return _read("planning-best-practices.md")


@resource("methodology://rendering/{provider}")
def methodology_rendering(provider: str) -> str:
    """Provider-specific rendering rules: ``claude`` | ``cowork`` | ``codex``."""
    allowed = {"claude", "cowork", "codex"}
    if provider not in allowed:
        raise ValueError(
            f"unknown rendering provider '{provider}'. Known: {sorted(allowed)}"
        )
    return _read(f"rendering/{provider}.md")
