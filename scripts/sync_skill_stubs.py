#!/usr/bin/env python3
"""Generate .claude/skills/ routing stubs from MCP-hosted skills in skills/."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Extract YAML frontmatter dict and remaining body from a markdown file."""
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    raw = text[4:end]
    body = text[end + 4 :].lstrip("\n")
    result: dict[str, str] = {}
    for line in raw.splitlines():
        match = re.match(r'^(\w[\w-]*)\s*:\s*(.+)$', line)
        if match:
            key = match.group(1)
            val = match.group(2).strip()
            if (val.startswith('"') and val.endswith('"')) or (
                val.startswith("'") and val.endswith("'")
            ):
                val = val[1:-1]
            result[key] = val
    return result, body


def discover_skills(skills_dir: Path) -> list[Path]:
    """Return sorted list of SKILL.md paths found in skills_dir/*/SKILL.md."""
    return sorted(skills_dir.glob("*/SKILL.md"))


def discover_references(skill_dir: Path) -> list[str]:
    """Return sorted list of reference file paths relative to the skill directory."""
    refs_dir = skill_dir / "references"
    if not refs_dir.is_dir():
        return []
    return sorted(
        f"references/{p.name}" for p in refs_dir.glob("*.md")
    )


def derive_title(name: str) -> str:
    """Convert kebab-case name to Title Case."""
    return " ".join(word.capitalize() for word in name.split("-"))


def derive_source_name(server: str) -> str:
    """Strip transport suffix (-http, -sse) from server name to get the source MCP name."""
    for suffix in ("-http", "-sse"):
        if server.endswith(suffix):
            return server[: -len(suffix)]
    return server


def patch_description(description: str, source_name: str, server: str) -> str:
    """Replace backtick-wrapped source MCP name with client-facing server name."""
    if source_name == server:
        return description
    return description.replace(f"`{source_name}`", f"`{server}`")


def render_stub(
    name: str,
    description: str,
    server: str,
    references: list[str],
) -> str:
    """Render a routing stub SKILL.md that points to the MCP-hosted skill."""
    title = derive_title(name)
    lines: list[str] = [
        "---",
        f"name: {name}",
        f'description: "{description}"',
        "---",
        "",
        f"# {title} (MCP-hosted skill)",
        "",
        f"This skill's full instructions are hosted on the `{server}` MCP server."
        " Do not hardcode workflow logic locally"
        " — always fetch the live version from the MCP.",
        "",
        "## Loading instructions",
        "",
        "1. Read the main skill instructions:",
        f'   → call the `fs_read` tool on the `{server}` MCP with'
        f' `path="skills/{name}/SKILL.md"`.',
        "",
    ]

    step = 2
    if references:
        lines.append(f"{step}. Read reference files on demand (`fs_read` with these paths):")
        for ref in references:
            lines.append(f"   - `skills/{name}/{ref}`")
        lines.append("")
        step += 1

    lines.append(
        f"{step}. To discover every file in this skill, call `fs_list` with"
        f' `path="skills/{name}"`.'
    )
    lines.append("")
    lines.append("Follow the instructions returned by the MCP exactly.")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate .claude/skills/ routing stubs from MCP-hosted skills.",
    )
    parser.add_argument("--server", required=True, help="MCP server name as seen by the client")
    parser.add_argument(
        "--skills-dir", default="skills", help="Source skills directory (default: skills/)"
    )
    parser.add_argument(
        "--output-dir",
        default=".claude/skills",
        help="Output stubs directory (default: .claude/skills/)",
    )
    parser.add_argument(
        "--source-name",
        default=None,
        help="MCP name used in source descriptions (default: derived from --server)",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--dry-run", action="store_true", help="Print what would be written")
    group.add_argument("--check", action="store_true", help="Exit 1 if any stubs are out of date")
    args = parser.parse_args()

    skills_dir = Path(args.skills_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    server: str = args.server
    source_name: str = args.source_name or derive_source_name(server)

    if not skills_dir.is_dir():
        print(f"error: skills directory not found: {skills_dir}", file=sys.stderr)
        return 1

    skill_files = discover_skills(skills_dir)
    if not skill_files:
        print(f"no skills found in {skills_dir}", file=sys.stderr)
        return 0

    drift_count = 0
    written_count = 0

    for skill_md in skill_files:
        skill_dir = skill_md.parent
        skill_name = skill_dir.name

        text = skill_md.read_text(encoding="utf-8")
        fm, _ = parse_frontmatter(text)

        if "name" not in fm or "description" not in fm:
            print(
                f"warning: skipping {skill_name}"
                " — missing name or description in frontmatter",
                file=sys.stderr,
            )
            continue

        name = fm["name"]
        description = patch_description(fm["description"], source_name, server)
        references = discover_references(skill_dir)
        stub = render_stub(name, description, server, references)

        out_path = output_dir / name / "SKILL.md"

        if args.dry_run:
            print(f"=== {out_path} ===")
            print(stub)
            written_count += 1
            continue

        if args.check:
            if not out_path.exists():
                print(f"missing: {out_path}", file=sys.stderr)
                drift_count += 1
            elif out_path.read_text(encoding="utf-8") != stub:
                print(f"outdated: {out_path}", file=sys.stderr)
                drift_count += 1
            continue

        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(stub, encoding="utf-8")
        written_count += 1
        print(f"wrote: {out_path}")

    if args.check:
        if drift_count:
            print(f"{drift_count} stub(s) out of date", file=sys.stderr)
            return 1
        print(f"{len(skill_files)} stub(s) up to date")
        return 0

    if args.dry_run:
        print(f"{written_count} stub(s) would be written")
    else:
        print(f"{written_count} stub(s) synced")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
