---
name: deliverable-canvas
description: "Run the planning ritual for a multi-section deliverable (proposal, brief, press release, messaging framework) before handing off to a formatter skill. The MCP is resource-only — no tools — and the canvas IS the chat artifact. You read templates and methodology, render the markdown artifact, validate it, and construct a handoff envelope, all in chat."
---

# Deliverable Canvas — Planning Ritual (MCP-hosted skill)

This skill's full instructions are hosted on the `deliverable-canvas` MCP server. Do not hardcode workflow logic locally — always fetch the live version from the MCP.

## Loading instructions

1. Read the main skill instructions:
   → `ReadMcpResourceTool(server="deliverable-canvas", uri="skill://deliverable-canvas/SKILL.md")`

2. Discover available reference files via the manifest, then read on demand:
   → `ReadMcpResourceTool(server="deliverable-canvas", uri="skill://deliverable-canvas/_manifest")`
   → `ReadMcpResourceTool(server="deliverable-canvas", uri="skill://deliverable-canvas/references/<file>")`

Follow the instructions returned by the MCP resource exactly.
