---
name: deliverable-canvas
description: "Run the planning ritual for a multi-section deliverable (proposal, brief, press release, messaging framework) before handing off to a formatter skill. The MCP has no domain tools — the canvas IS the chat artifact. You read templates and methodology, render the markdown artifact, validate it, and construct a handoff envelope, all in chat."
---

# Deliverable Canvas — Planning Ritual (MCP-hosted skill)

This skill's full instructions are hosted on the `deliverable-canvas` MCP server. Do not hardcode workflow logic locally — always fetch the live version from the MCP.

## Loading instructions

1. Read the main skill instructions:
   → call the `fs_read` tool on the `deliverable-canvas` MCP with `path="skills/deliverable-canvas/SKILL.md"`.

2. Discover reference files (and any other skill assets), then read on demand:
   → call `fs_list` with `path="skills/deliverable-canvas"` (and `path="skills/deliverable-canvas/references"`),
   → call `fs_read` with `path="skills/deliverable-canvas/references/<file>"`.

Follow the instructions returned by the MCP exactly.
