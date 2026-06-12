# Deliverable Canvas MCP

> **⚠️ RETIRED (2026-06-12) — decommission pending.** This MCP is de-wired from **all** client plugins; the canvas protocol now lives inline in each strategic skill (`proposal`, `messaging-framework`, `press-release`, `organic-social-campaign` — canonical in `Cowork/.claude/skills/`) as a plain chat markdown artifact with a user sign-off gate. Do **not** wire this server into any plugin. The ACA deployment is slated for teardown and the repo is retained only as a code archive in case an HTML-canvas host is ever needed (full deletion likely — see stromy-org `BACKLOG.md` ORG-076 for the deletion checklist). History: `infra-docs/ai/deliverable-canvas.md`.

Resource-only MCP for strategic deliverable canvases (proposals, briefs, frameworks). Exposes templates, methodology guidance, and the canonical `deliverable-canvas` skill — **zero tools**. The chat artifact is the canvas; iteration happens in chat, not on the server. No per-user storage, no SQLite, no resume.

Built with [FastMCP 3.0](https://gofastmcp.com) and managed with [uv](https://docs.astral.sh/uv/).

## Setup

```bash
uv sync
cp .env.example .env
```

## Run

```bash
# stdio (default)
uv run python -m src.server

# Or via the FastMCP CLI (reads fastmcp.json):
uv run fastmcp run
uv run fastmcp dev      # with the Inspector UI
```

HTTP transport is enabled by default — the server listens on `http://127.0.0.1:8000/mcp/`.

## Project layout

```
src/server.py              FastMCP server entrypoint (instance: `mcp`)
components/
├── tools/                 @tool functions, auto-discovered
├── resources/             @resource functions, auto-discovered
└── prompts/               @prompt functions, auto-discovered
skills/
└── deliverable-canvas/    Skill, served via the fs_read/fs_list tools
tests/                     pytest + in-memory FastMCP Client
```

Components are loaded by `FileSystemProvider`. Drop a new `.py` file into any
subdirectory of `components/` with a standalone `@tool` / `@resource` /
`@prompt` decorator — no registration required. Set `MCP_DEV_MODE=true`
in `.env` to enable hot-reload during development.

### Skills

The `skills/` directory is served through the generic `fs_read` / `fs_list`
tools (not `skill://` resources — most MCP clients surface only tools). Each
subdirectory with a `SKILL.md` is discoverable via `fs_list("skills")`; clients
read skill content with `fs_read("skills/<name>/SKILL.md")`.

Drop a new folder into `skills/` with a `SKILL.md` — no registration needed.

## Tests

```bash
uv run pytest
```

## Use with Claude Code

The included `.mcp.json` registers this server as `deliverable-canvas-mcp` for any
Claude Code session opened in this directory.



## Deploy to Azure Container Apps

Production runs on [Azure Container Apps](https://learn.microsoft.com/en-us/azure/container-apps/) with scale-to-zero. CI/CD is handled by `.github/workflows/deploy-aca.yml` on every push to `main`.

See [`azure_aca/README.md`](azure_aca/README.md) for the full setup guide (automated script or manual commands).
