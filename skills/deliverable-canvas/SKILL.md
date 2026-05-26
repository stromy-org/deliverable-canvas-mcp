---
name: deliverable-canvas
description: Protocol for collaborating with the user on a structured deliverable (proposal, messaging-framework, press-release, brief) through an MCP-backed canvas. Use whenever a strategic skill produces a multi-section document that downstream formatters (pptx, docx, pdf) will consume. Open or resume a canvas first, update sections turn by turn, finalize before handing off to a formatter.
---

# Deliverable Canvas Protocol

The deliverable canvas is a **shared workspace** between the agent and the user for structured deliverables. State lives in the `deliverable-canvas-mcp` server, not in the chat scroll-back. The same canvas can be resumed from any agent (Claude, Codex) in any future session.

## When to use

You are inside a strategic skill (proposal, messaging-framework, press-release, brief, charter, etc.) that produces a multi-section document. The downstream formatter (pptx / docx / pdf) needs a stable, addressable structure — not a chat transcript.

You are NOT inside such a skill (you're answering a question, writing code, generating a one-shot artifact). Don't open a canvas — it's overhead.

## Tools

The MCP server `deliverable-canvas` exposes six tools:

- `mcp__deliverable-canvas__canvas_create(deliverable_type, client_id, title, template_id?, brief?, opened_by_skill?, methodology_version?)`
- `mcp__deliverable-canvas__canvas_get(canvas_id)`
- `mcp__deliverable-canvas__canvas_update_section(canvas_id, section_id, body, summary?, instructed_by_user?, title?)` — **upserts**: creates the section if it does not exist yet. `title` is only used on first creation (defaults to a Title-Cased `section_id`); for templated sections it is ignored.
- `mcp__deliverable-canvas__canvas_list_revisions(canvas_id, section_id?)`
- `mcp__deliverable-canvas__canvas_finalize(canvas_id)`
- `mcp__deliverable-canvas__canvas_list(client_id?, deliverable_type?, include_finalized?)`

And four MCP resources:

- `canvas://<canvas_id>/state` — JSON snapshot for formatters and programmatic readers
- `canvas://<canvas_id>/artifact` — populated HTML for Claude Desktop Live Artifact rendering
- `template://list` — JSON array of available `template_id` values (call before `canvas_create` to see what's on offer)
- `template://<template_id>` — full template schema (`{template_id, description, sections: [{id, title}, ...]}`)

## Protocol — what every strategic skill MUST do

### 1. Resume or create

**First**, on entering a deliverable conversation, call `canvas_list(client_id=..., deliverable_type=...)`. If candidates exist, ask the user: *"I found N existing canvases for this client and deliverable. Resume <title> (updated <ts>), or start fresh?"*

- Resume → `canvas_get(canvas_id)` to load full state including `meta.brief` and `meta.opened_by_skill`. Continue from there.
- Fresh → `canvas_create(...)` with `template_id`, `brief` summarizing the engagement context, `opened_by_skill=<this-skill>`, and `methodology_version` (if known).

If no candidates, go straight to `canvas_create`.

### 2. Render the canvas to the user

Immediately after create or resume, **emit the artifact** so the user has a visual:

- Read `canvas://<canvas_id>/artifact` and output it as an HTML artifact (Claude Desktop) or a structured markdown outline of the sections (Codex CLI).

### 3. Update sections turn by turn

When the user instructs a change ("make pricing more aggressive", "rewrite the approach"), call `canvas_update_section(canvas_id, section_id, body, summary="...", instructed_by_user=True)`. Then re-emit the artifact resource so the user sees the change.

Section IDs are free-form snake_case strings. If you call `canvas_update_section` with a section that does not exist yet, it is created automatically — supply `title` to override the auto-derived display name (e.g. `title="Executive Summary"` for `section_id="executive_summary"`). Templated canvases (`canvas_create(..., template_id=...)`) pre-create a known section set; you can still add ad-hoc sections beyond the template by writing to a new `section_id`.

For agent-initiated refinements (you spotted something to clean up), call with `instructed_by_user=False` — the audit log distinguishes the two.

The canvas surface is **read-only**. The user does not edit the artifact directly; they tell you what to change, and you write it.

### 4. Finalize before formatter handoff

When the user signals the deliverable is ready, call `canvas_finalize(canvas_id)`. The canvas becomes write-locked. Then hand `canvas_id` (only) to the formatter skill — the formatter calls `canvas_get` to read the state.

## Failure modes

- **MCP unreachable.** Surface the error to the user. Ask: *"deliverable-canvas-mcp is not reachable. (a) wait, (b) draft inline without persistence?"* Never silently degrade — if you draft inline, banner the response so the user knows there's no canvas to resume from.
- **Canvas finalized but user wants to edit.** Offer: *"This canvas is finalized. Create a v2 canvas with these sections as starting bodies, or open a fresh canvas?"* Do not silently unlock.
- **Template not found.** `canvas_create` lists known templates in the error message. Before creating a canvas you can also call `ReadMcpResourceTool(uri="template://list")` to enumerate the available IDs, then `ReadMcpResourceTool(uri="template://<id>")` to inspect a specific template's section layout. New templates are added by dropping a JSON file in `MCPs/deliverable-canvas-mcp/components/resources/templates/<name>.json`.

## References

- [Protocol details](references/protocol.md) — resume flow, audit fields, error responses
- [Section schemas](references/sections-schemas.md) — templates per deliverable_type, how to add new ones

## Mentioning vs activating

Strategic skills **mention** this skill as a prerequisite in their body — they do not `Skill(...)` activate it. The protocol is inlined into the strategic skill body; this skill exists as the canonical reference.
