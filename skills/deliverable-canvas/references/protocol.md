# Canvas Protocol — Details

## Resume flow (canonical sequence)

```
canvas_list(client_id="dukestrategies", deliverable_type="proposal")
  → list of {canvas_id, title, updated_ts, finalized}

(if user picks one)
canvas_get(canvas_id)
  → full state including meta.brief, meta.opened_by_skill, meta.methodology_version

(continue editing)
canvas_update_section(...)
canvas_update_section(...)

canvas_finalize(canvas_id)
```

`meta` is the *only* re-orientation context — the resuming agent must not assume any prior chat history is available.

## Audit log

Every `canvas_update_section` writes one row to the audit table with:
- `tenant_id`, `tool`, `canvas_id`, `section_id`
- `instructed_by_user` (0/1)
- `body_hash` (sha256 of body — body content itself is NEVER logged)
- `ts` (unix seconds)

Use this to reconstruct AI vs user attribution post-hoc without storing raw content.

## Error contract

All tools raise `ValueError` with a message starting with one of:
- `unauthorized:` — tenant key missing or invalid
- `canvas not found:`
- `section not found:`
- `canvas is finalized;` — writes attempted on a finalized canvas
- `Unknown template_id` — template_id not in `templates/<id>.json`

FastMCP surfaces these as tool errors with `isError=True`; the agent should parse the prefix and route to the matching user-facing message described in SKILL.md "Failure modes".

## Persistence guarantees

- WAL mode SQLite, BEGIN IMMEDIATE on every write. Tool returns only after fsync.
- Backup: nightly `sqlite3 .backup` to `data/backups/canvas-YYYYMMDD.db`. Weekly snapshot to Azure Blob. Retention 90 days.
- Restore: `CanvasStore.restore_from(backup_path=..., db_path=...)` is the contract. Runbook in `azure_aca/README.md`.

## Tenant isolation

`tenant_id` is derived from the `X-Tenant-Key` HTTP header at request time. Every tool call resolves the tenant first; every query is scoped to that tenant. A canvas created by tenant A is invisible to tenant B (returns `canvas not found`).

## Renderer expectations

- **Claude Desktop**: emit `canvas://<id>/artifact` as an inline HTML artifact after each write.
- **Codex CLI**: print a markdown outline of `canvas_get` output (sections + bodies, truncated to ~200 chars each) after each write.
- **No renderer writes back.** All section updates flow through the agent calling `canvas_update_section`.
