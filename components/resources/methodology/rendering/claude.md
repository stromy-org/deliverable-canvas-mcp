---
version: 1.0
provider: claude
---

# Rendering rules — Claude (Claude Code / Claude Desktop)

These rules apply when you are running inside Claude Code (CLI or IDE) or
Claude Desktop. They specialise the universal planning ritual
(`methodology://planning-best-practices`).

## Artifact format: markdown

Emit a **single markdown artifact**. **Never** emit an HTML artifact that calls
back to the MCP — Claude does not have a bidirectional artifact-to-MCP channel
the way Cowork attempts. Plain markdown round-trips correctly.

## Artifact identifier (REQUIRED)

Every emission MUST use the identifier:

```
canvas-<canvas_id>-<deliverable_type>
```

where `<canvas_id>` is the 8-character hex you generated at session start (see
`planning-best-practices.md` step 3) and `<deliverable_type>` is the
underscored type (`proposal`, `press_release`, `messaging_framework`, …).

Examples:

- `canvas-a4f9c2b1-proposal`
- `canvas-7e3b5d9c-press_release`
- `canvas-2c8f4a01-messaging_framework`

Do **not** vary the identifier between renders within a session. Do **not**
re-use the identifier in a different chat session for the same client /
deliverable — start a fresh canvas (new `canvas_id`) instead. This prevents
cross-chat artifact version-history collisions.

## Section headings

- One `## ` heading per template section, **in template order**.
- Heading text = the template section's `title` field. **Not** the section
  `id`. The section `id` is the implicit positional anchor — 1st `## ` heading
  = first template section, etc.
- Do not embed the section `id` as an HTML comment, heading anchor, or any
  other side-channel. Positional matching is the rule.

## Re-emission

After every user-confirmed change:

1. Build the **full** updated markdown (every section, not a delta).
2. Emit it as a new version of the same artifact (same identifier).
3. Briefly summarise what changed since the last version (one sentence).

Never emit a partial canvas. Never mint a new artifact identifier mid-session.

## Self-check on finalisation

Before constructing the handoff envelope, walk the rendered markdown per the
universal ritual's step 6. Failing the walk means you re-emit and surface to
the user; it does not mean you call an MCP tool (no tools exist).
