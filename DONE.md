# Done — deliverable-canvas-mcp

Completion archive for plans that have shipped. Entries move here when `/plan-archive` runs.

## 2026-Q2

### 2026-05-27
- **ORG-PLAN-006** — Canvas MCP resource-only refactor — completed 2026-05-27 — plan: `plan_archives/2026/canvas-stateless-refactor.md` — backlog: none. Stripped the MCP to **zero tools**; sole surface is resources (`template://list`, `template://{template_id}`, `methodology://planning-best-practices`, `methodology://rendering/{provider}`, `skill://deliverable-canvas/SKILL.md`). Removed SQLite storage, per-user canvas pools, audit logging, backup/restore — the canvas is now a chat markdown artifact with identifier convention `canvas-<canvas_id>-<deliverable_type>` (Component 14). OAuth scope contract fixed: `OAUTH_REQUIRED_SCOPES` is whitespace-delimited per RFC 6749 (was comma-only), and `offline_access` is required for refresh tokens (eliminates ~1h Reconnect prompt). Migrated duke-strategies-plugin's `proposal` + `pptx` skills, fastmcp-template's worked example, skill-creator's example, AGENTS.md / catalog.json. ACA kept at `minReplicas=0`. Manual Phase C smoke (Acceptance #20–22) deferred to user out-of-band.
