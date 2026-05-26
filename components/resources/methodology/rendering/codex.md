---
version: 0.1
provider: codex
status: placeholder
---

# Rendering rules — Codex (placeholder)

Codex CLI is not yet a supported host for the deliverable-canvas MCP. This
resource exists as a placeholder so the `methodology://rendering/{provider}`
contract is uniform across hosts.

When Codex deployment becomes real, this file will document Codex-specific
rendering conventions. Until then:

- Do not run a canvas session inside Codex; redirect the user to Claude Code
  or Cowork.
- If you must proceed in Codex anyway, follow `methodology://rendering/claude`
  and assume markdown artifacts are not supported — emit the canvas inline in
  the response and surface to the user that the experience is degraded.

## Artifact identifier convention

The same convention applies if/when Codex gains artifact support:

```
canvas-<canvas_id>-<deliverable_type>
```

See `methodology://rendering/claude` for full identifier discipline.
