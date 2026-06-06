---
name: canvas-deliverable
description: "Run the planning ritual for a multi-section deliverable (proposal, brief, press release, messaging framework) before handing off to a formatter skill. The MCP has no domain tools — the canvas IS the chat artifact. You read templates and methodology, render the markdown artifact, validate it, and construct a handoff envelope, all in chat."
---

# Deliverable Canvas — Planning Ritual (MCP-hosted skill)

This skill's full instructions are hosted on the `deliverable-canvas` MCP server. Do not hardcode workflow logic locally — always fetch the live version from the MCP.

## Loading instructions

1. Read the main skill instructions:
   → call the `fs_read` tool on the `deliverable-canvas` MCP with `path="skills/canvas-deliverable/SKILL.md"`.

2. Discover reference files (and any other skill assets), then read on demand:
   → call `fs_list` with `path="skills/canvas-deliverable"` (and `path="skills/canvas-deliverable/references"`),
   → call `fs_read` with `path="skills/canvas-deliverable/references/<file>"`.

Follow the instructions returned by the MCP exactly.

## This MCP is the only correct path

Produce this skill's output **only** by following the live SKILL.md fetched above and calling the `deliverable-canvas` MCP's own tools. Do **not** substitute a local or identically-named base skill from elsewhere, and do **not** invent your own output path. A locally-produced or unbranded artifact is **wrong output, not a fallback** — it bypasses the server-side brand and quality gates.

## If the `deliverable-canvas` MCP is slow to respond

This server scales to zero to save cost, so the first call may take ~10–30s to cold-start. If `fs_read` or a tool errors with unavailable/timeout:

1. Tell the user the server is starting, then retry the same `fs_read` call — the call itself wakes the container.
2. Retry with a short backoff up to ~3 times.
3. Only if it is still unreachable after retries, STOP and report. Never downgrade to a local or base skill just to "get something out".
