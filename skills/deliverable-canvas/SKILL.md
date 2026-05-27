---
name: deliverable-canvas
description: Run the planning ritual for a multi-section deliverable (proposal, brief, press release, messaging framework) before handing off to a formatter skill. The MCP is resource-only — no tools — and the canvas IS the chat artifact. You read templates and methodology, render the markdown artifact, validate it, and construct a handoff envelope, all in chat.
---

# Deliverable Canvas — Planning Ritual

The deliverable canvas is the markdown artifact you emit in the chat for a
multi-section deliverable. Its state lives in the artifact, not in this MCP.
The MCP gives you **templates** (section schemas) and **methodology** (the
planning ritual + host-specific rendering rules). You do all the work in chat.

## When to use

You are inside a strategic skill (proposal, messaging-framework, press-release,
brief, charter, …) that produces a multi-section document. The downstream
formatter (`pptx` / `docx` / `pdf`) needs a stable, addressable structure — not
a chat transcript.

## When NOT to use

You are answering a question, writing code, or generating a one-shot artifact.
Don't open a canvas — it's overhead.

## No tools — resources only

This MCP exposes **no tools**. The canvas IS your chat artifact. You read the
template and methodology as MCP resources; everything else (rendering,
validating, packaging) happens in chat under your control.

## Resource reference

- `template://list` — JSON `{"templates": [<template_id>, …]}`. Call first to
  discover available deliverable schemas.
- `template://{template_id}` — full template JSON with `description`,
  top-level `methodology_version`, and `sections: [{id, title, prompt_hint}]`.
- `methodology://planning-best-practices` — universal planning ritual. Read
  this first.
- `methodology://rendering/{provider}` — host-specific rendering rules.
  `provider` ∈ `{claude, cowork, codex}`. MUST be read before emitting any
  artifact.

## Protocol

1. **Discover the template.** Call
   `ReadMcpResourceTool(uri="template://list")`. Match the user's deliverable
   to a `template_id`. Read `template://{template_id}` for the section schema
   and the top-level `methodology_version`.
2. **Read methodology.** Call
   `ReadMcpResourceTool(uri="methodology://planning-best-practices")` and
   `ReadMcpResourceTool(uri="methodology://rendering/<host>")` where `<host>`
   is `claude` (Claude Code / Claude Desktop) or `cowork`.
3. **Generate a `canvas_id`.** 8 hex chars, e.g. `a4f9c2b1`. This anchors the
   artifact identifier for the entire session.
4. **Render the empty canvas as a markdown artifact** with identifier
   `canvas-<canvas_id>-<deliverable_type>`. One `## <Title>` heading per
   template section, in template order. Heading text = the template's `title`
   field for that section. Do NOT embed the section `id` as a heading anchor
   or HTML comment — positional order is the implicit anchor.
5. **Iterate section-by-section.** For each section: propose content based on
   `prompt_hint`, wait for user feedback, revise, re-emit the **full** canvas
   as a new version of the SAME artifact (same identifier) after every change.
   Never emit a delta. Never mint a new artifact identifier mid-session.
6. **Self-check before handoff.** Walk the rendered markdown:
   - Count `## ` headings at line-start (ignore those inside fenced code blocks).
   - Assert count == `len(template.sections)`.
   - For each heading position `i`: heading text equals
     `template.sections[i].title` AND the body (lines until next `## ` or EOF,
     stripped) is non-empty.
   Any failure → surface to user, fix, re-walk. No MCP round-trip.
7. **Construct the envelope.** Build the JSON dict:
   ```json
   {
     "template_id":       "<template_id>",
     "deliverable_type":  "<proposal | press_release | …>",
     "title":             "<user-confirmed title or null>",
     "client_id":         "<client_slug>",
     "sections": [
       {"id": "<section_id>", "title": "<section title>", "body": "<markdown>"}
     ],
     "meta": {
       "canvas_id":           "<8-char hex from step 3>",
       "methodology_version": "<copied verbatim from template JSON top-level>"
     }
   }
   ```
   `methodology_version` is read from the template JSON's top-level field
   (authoritative source). `client_id` is top-level (not under `meta`) so the
   formatter can resolve brand assets directly. `client_id` comes from the
   invoking plugin's companies directory (the org-wide skill-data-loading
   convention applies in the *formatter* — this canvas skill itself does not
   read client-data; it only passes the `client_id` through in the envelope).
8. **Hand off to the formatter.** Invoke the formatter skill (`pptx`, `docx`,
   …) with `{envelope}` as its input.

## Section ID convention

Section IDs are determined by the template (read `template://{template_id}`).
Emit sections in template order, with `## ` heading text = the template's
`title` for that section. The validation walk in Step 6 relies on positional
matching (1st `## ` = first template section, etc.), not on parsing section
IDs out of heading text — this avoids fragility around heading rewording
during user feedback.

## Resume (out of scope)

One chat = one canvas. To resume, the user reopens the chat. The MCP does not
store canvases; there is no `canvas_list`, no save-to-disk handoff, no
cross-session registry.

## Failure modes

| Failure                                  | Recovery                                                                           |
|------------------------------------------|------------------------------------------------------------------------------------|
| Unknown `template_id`                    | Read `template://list`, pick a valid one, retry.                                   |
| Self-check finds missing/empty sections  | Surface to user, iterate, re-check.                                                |
| Methodology resource read fails          | Continue with built-in fallback ritual from this SKILL.md; surface the error.      |
| Formatter rejects envelope               | Inspect formatter's error, adjust envelope shape, retry.                           |

## Mentioning vs activating

Strategic skills **mention** this skill as a prerequisite in their body — they
do not `Skill(...)` activate it. The protocol is inlined into the strategic
skill body; this skill exists as the canonical reference.

## Reference

- Live SKILL.md (canonical): `MCPs/deliverable-canvas-mcp/skills/deliverable-canvas/SKILL.md`
- Stubs distributed via `stromy-org/scripts/sync-mcp-skill-stubs.py` to consuming plugins
- Methodology source files: `MCPs/deliverable-canvas-mcp/components/resources/methodology/`
