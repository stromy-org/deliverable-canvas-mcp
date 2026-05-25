# Deliverable Canvas MCP

Provider-portable canvas storage for strategic deliverables (proposals, briefs, frameworks)

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
└── server-guide/          Example skill, exposed as skill:// resources
tests/                     pytest + in-memory FastMCP Client
```

Components are loaded by `FileSystemProvider`. Drop a new `.py` file into any
subdirectory of `components/` with a standalone `@tool` / `@resource` /
`@prompt` decorator — no registration required. Set `MCP_DEV_MODE=true`
in `.env` to enable hot-reload during development.

### Skills

The `skills/` directory exposes skill folders as MCP resources using the
`skill://` URI scheme. Each subdirectory with a `SKILL.md` becomes
discoverable via `list_resources()`. Clients read skill content with
`read_resource("skill://<name>/SKILL.md")`.

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
