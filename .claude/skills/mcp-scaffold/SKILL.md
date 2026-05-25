---
name: mcp-scaffold
description: Orient agents working inside a FastMCP project that was generated from the mcp-template Copier scaffolding. Triggers on: bootstrap/post-generation work ("just generated", "add a tool", "add a resource", "add a prompt"), presence of `components/{tools,resources,prompts}/` directories, work touching `src/server.py` or `components/*.py`, or any question about repo layout, testing, or config in this project.
---

# MCP Scaffold — agent orientation guide

This skill describes the **repo-specific conventions** of this FastMCP project. It covers layout, the component auto-discovery contract, how to add components, config/env wiring, and the test pattern. For FastMCP API questions (auth, advanced decorators, transports, Inspector, deployment), defer to the `fastmcp` skill — or if unavailable, `WebFetch https://gofastmcp.com/llms.txt` to fetch the docs index.

---

## 1. When this skill applies

| Situation | First action |
|-----------|-------------|
| Just ran `copier copy` — need to implement the server | Follow the **Bootstrap checklist** (§5) |
| Adding / editing a tool, resource, or prompt | Read the **Discovery contract** (§3) then **Adding components** (§4) |
| Config, env var, or settings question | Read `src/config.py` and `.env.example` (§6) |
| Writing or running tests | Read the **Testing pattern** (§7) |
| Deploy / production / Docker / ACA question | Read README "Deploy to Azure Container Apps" section, `Dockerfile`, and `.github/workflows/deploy-aca.yml` |
| FastMCP API question | Invoke `fastmcp` skill or `WebFetch https://gofastmcp.com/llms.txt` |

---

## 2. Project layout

```
src/
  __init__.py
  server.py          FastMCP entrypoint — the `mcp` instance lives here
  config.py          pydantic-settings Settings class, reads from .env
  logging.py         Structured JSON logging setup (stdout → Azure Log Analytics)
  middleware.py      Tool-call logging middleware (logs name, input, user, duration)
  auth.py            OAuth provider builder (present when enable_oauth=true)

components/          FileSystemProvider scans this tree automatically
  tools/             @tool decorated functions
  resources/         @resource decorated functions
  prompts/           @prompt decorated functions

skills/              SkillsDirectoryProvider scans this tree
  server-guide/      Example skill (SKILL.md — exposed as skill:// resources)

tests/
  conftest.py        adds project root to sys.path
  test_server.py     smoke tests using in-memory Client(transport=mcp)

pyproject.toml       deps, build config, ruff + pytest settings
fastmcp.json         FastMCP CLI config (entrypoint, transport, uv env)
.mcp.json            Claude Code MCP registration (stdio + http entries)
.env.example         env var reference — copy to .env and fill in secrets
.copier-answers.yml  records the answers used during copier generation
```

---

## 3. The discovery contract (most important)

`src/server.py` wires two providers into `FastMCP`:

1. **`FileSystemProvider(COMPONENTS_DIR)`** — scans `components/` for tools, resources, and prompts.
2. **`SkillsDirectoryProvider(roots=SKILLS_DIR)`** — scans `skills/` for skill directories (each containing a `SKILL.md`) and exposes them as `skill://` MCP resources.

This means:
- **No registry, no import in `server.py`.** The providers scan their directories automatically.
- **Adding a component = dropping a `.py` file** into the right `components/` subdirectory with the right decorator. Nothing else.
- **Adding a skill = creating a directory** in `skills/` with a `SKILL.md` file. Nothing else.
- **Filename is free** — `my_tool.py`, `stripe_payments.py`, `fetch_orders.py` — any valid module name works.
- Hot-reload during development: set `MCP_DEV_MODE=true` in `.env` and both providers will detect changes without restarting.

---

## 4. Adding components

Use the exact import paths below — wrong imports silently fail to register.

### Tool
```python
from fastmcp.tools import tool

@tool
def my_tool(param: str, count: int = 1) -> str:
    """One-line description — becomes the tool description in the MCP schema."""
    return param * count
```
File goes in: `components/tools/my_tool.py`

### Resource
```python
from fastmcp.resources import resource

@resource("data://my-resource")
def my_resource() -> str:
    """Description of what this resource provides."""
    return "resource content"
```
File goes in: `components/resources/my_resource.py`

### Prompt
```python
from fastmcp.prompts import prompt

@prompt
def my_prompt(context: str, style: str = "concise") -> str:
    """Description of what this prompt template generates."""
    return f"You are a {style} assistant. Context: {context}"
```
File goes in: `components/prompts/my_prompt.py`

### Skill
```
skills/
└── my-skill/
    ├── SKILL.md          # Required — YAML frontmatter (name, description) + markdown body
    └── references/       # Optional — supporting files accessible via skill://<name>/{path}
```
Exposed as MCP resources: `skill://my-skill/SKILL.md`, `skill://my-skill/_manifest`, `skill://my-skill/references/...`

After adding or modifying a skill, re-run `uv run python scripts/sync_skill_stubs.py --server <package-slug>-http` to regenerate the `.claude/skills/` routing stubs.

**Rules:**
- Type-hint every parameter — FastMCP derives the JSON schema from hints.
- Docstring becomes the description visible to the MCP client.
- One component per file is preferred; multiple are allowed if tightly related.
- For async tools, use `async def` — FastMCP supports both.

---

## 5. Bootstrap checklist (post-`copier copy`)

1. **Read the user's intent** — understand what business logic the server should expose.
2. **Delete the example files** in `components/tools/`, `components/resources/`, `components/prompts/`, and `skills/server-guide/` — they are placeholders only.
3. **Drop in new components** following §4 above.
4. **Generate skill stubs** for any skills you added in `skills/`:
   ```bash
   uv run python scripts/sync_skill_stubs.py --server <package-slug>-http
   ```
   This creates routing stubs in `.claude/skills/` that point MCP clients to the hosted skill content via `ReadMcpResourceTool`. Re-run after adding or renaming skills.
5. **Verify:**
   ```bash
   uv run pytest                      # smoke tests
   uv run python -m src.server        # starts the server
   ```
   Also remove the echo test from `tests/test_server.py` and replace it with tests for the new components.

---

## 6. Configuration & environment

`src/config.py` uses `pydantic-settings`:

```python
class Settings(BaseSettings):
    fastmcp_transport: str = "http"   # "http" or "stdio"
    fastmcp_port: int = 8000
    mcp_dev_mode: bool = False
    log_level: str = "INFO"
    # add your own settings here
```

Rules:
- **Add new settings as fields on `Settings`**, not as bare `os.environ` reads.
- **Document new vars in `.env.example`** so other agents and humans know what is expected.
- Settings are read once at import time via `settings = Settings()` — no dynamic reload.
- Env vars map to field names (uppercase, underscores): `MCP_DEV_MODE=true` → `settings.mcp_dev_mode`.

---

## 7. Testing pattern

`pytest-asyncio` is pre-configured with `asyncio_mode = "auto"`. Use the in-memory transport — no network or process required:

```python
import pytest
from fastmcp.client import Client
from src.server import mcp

@pytest.fixture
async def client():
    async with Client(transport=mcp) as c:
        yield c

async def test_my_tool(client):
    result = await client.call_tool(name="my_tool", arguments={"param": "hello"})
    assert result.data == "hello"
```

Run with: `uv run pytest`

---

## 8. Logging & observability

All logs are structured JSON lines on stdout. Azure Container Apps forwards them to the Log Analytics workspace (`mcp-workspace`) automatically.

### How it works

- `src/logging.py` configures a `JSONFormatter` on the root logger at import time (called from `server.py`)
- `src/middleware.py` contains `ToolCallLoggingMiddleware` — a FastMCP `Middleware` subclass that logs every tool call
- Each log entry includes: `timestamp`, `tool` name, `input` arguments, `user_email` (from OAuth token when enabled, else `"anonymous"`), `duration_ms`, and `status` (`ok` / `error`)
- Log level is controlled by `LOG_LEVEL` env var (default: `INFO`)

### Querying in Azure

```kql
ContainerAppConsoleLogs_CL
| where Log_s contains "tool_call"
| extend parsed = parse_json(Log_s)
| project TimeGenerated, tool=parsed.tool, user=parsed.user_email, duration=parsed.duration_ms, status=parsed.status
```

### Adding custom log fields

Use `extra={"json_fields": {...}}` on any logger call — the `JSONFormatter` merges them into the output:

```python
logger.info("custom event", extra={"json_fields": {"key": "value"}})
```

---

## 9. Repo conventions cheatsheet

| Topic | Convention |
|-------|-----------|
| Python version | 3.13 (see `.python-version`) |
| Package manager | `uv` — use `uv run`, `uv sync`, `uv add` |
| Linter | ruff, line-length 100, rules `E,F,I,UP,B` |
| Test runner | pytest, `--import-mode=importlib` |
| Default transport | HTTP on `http://127.0.0.1:8000/mcp/` |
| Stdio transport | Set `FASTMCP_TRANSPORT=stdio` in `.env` or override in `.mcp.json` |
| Claude Code registration | `.mcp.json` registers both stdio and http variants |
| Dev hot-reload | `MCP_DEV_MODE=true` in `.env` |
| Production | `streamable-http` on `:80` (set in `Dockerfile`), `/health` is the ACA liveness probe |
