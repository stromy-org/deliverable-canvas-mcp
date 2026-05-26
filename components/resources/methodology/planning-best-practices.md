---
version: 1.0
---

# Planning best practices — universal ritual

This document describes how to run a multi-section deliverable session in chat
when the canvas MCP is **resource-only** (no tools). The canvas itself is a
markdown artifact you emit and re-emit in the chat — its state lives in the
artifact, not in the MCP.

## Principles

1. **The canvas is the chat artifact.** You own the rendering. The MCP gives you
   the template and the methodology; everything else (rendering, validating,
   packaging) happens in chat under your control.
2. **Re-emit the FULL canvas after every user-confirmed change.** Never emit a
   delta. Same artifact identifier every time (see the host-specific rendering
   methodology for the identifier convention).
3. **One section per turn unless the user asks otherwise.** Concentration beats
   sprawl. After each section, wait for user confirmation before moving on.
4. **User feedback is authoritative.** Treat user instructions as the final
   word. When you propose content based on `prompt_hint`, frame it as a
   proposal ("I'm proposing X — does that work?"), not a finished section.
5. **Use `instructed_by_user` framing in your summaries.** When you re-emit
   the canvas after a user instruction, note which sections changed and that
   they changed at the user's direction.
6. **Ask before finalising.** Before constructing the handoff envelope, confirm
   the canvas is done. Surface any sections that are empty or thin.

## Session walk

1. **Discover the template.** Read `template://list`, match the user's
   deliverable to a `template_id`, then read `template://{template_id}` for the
   section schema (sections, prompts, top-level `methodology_version`).
2. **Read host rendering rules.** Read `methodology://rendering/{host}` where
   `{host}` is `claude` (Claude Code / Claude Desktop) or `cowork`. This tells
   you the artifact identifier convention and any host-specific quirks.
3. **Generate a `canvas_id`.** 8 hex chars, e.g. `a4f9c2b1`. This anchors the
   artifact identifier for the entire session. Do not change it mid-session.
4. **Emit the empty canvas.** One `## <Title>` heading per template section, in
   template order, with empty bodies. Heading text = the template's `title`
   field for that section. Do not embed the section `id` as an anchor or HTML
   comment; positional order is the implicit anchor.
5. **Iterate section-by-section.** Propose content from `prompt_hint`, wait for
   user feedback, revise, re-emit the FULL canvas. Repeat.
6. **Self-check.** Before envelope construction:
   - Count `## ` headings at line-start (ignore those inside fenced code blocks).
   - Assert count == `len(template.sections)`.
   - For each heading position `i`: heading text equals
     `template.sections[i].title` AND the body (lines until next `## ` or EOF,
     stripped) is non-empty.
   Any failure → surface to user, fix, re-walk.
7. **Construct the envelope.** Build the JSON dict:
   ```json
   {
     "template_id":       "<template_id>",
     "deliverable_type":  "<deliverable type, e.g. proposal>",
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
   (authoritative source). `client_id` is top-level (not under `meta`) so
   formatters can resolve brand assets directly.
8. **Hand off to the formatter.** Invoke the formatter skill (`pptx`, `docx`,
   …) with `{envelope}` as input.

## Resume is out of scope

One chat = one canvas. To resume, the user reopens the chat. The MCP does not
store canvases; there is no `canvas_list`, no save-to-disk handoff, no
cross-session registry.

## When the host fails to render

If your rendered markdown is rejected by the host (rare), or a methodology
resource read fails, fall back to a built-in ritual: render the canvas inline
in the chat, surface the error to the user, continue the session. Do not
silently degrade.
