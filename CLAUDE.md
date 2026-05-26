<!--
  GENERATED FILE — DO NOT EDIT.
  Source of truth: AGENTS.md (cross-vendor standard).
  Override file:   .agent-overrides/claude.md (optional, appended below)
  Regenerate with: scripts/render-agent-md.py
-->

# Deliverable Canvas MCP

Provider-portable canvas storage for strategic deliverables (proposals, briefs, frameworks)

> **AGENTS.md is the canonical instruction file** for this repo (cross-vendor standard).
> `CLAUDE.md` and `.github/copilot-instructions.md` are generated from this file by
> `scripts/render-agent-md.py`. Gemini CLI reads this file directly via
> `context.fileName: ["AGENTS.md"]` in `.gemini/settings.json`. **Do not hand-edit
> the generated files.**

## Commands

```bash
uv sync                        # install dependencies
uv run python -m src.server    # run the server (HTTP on :8000)
uv run pytest                  # run tests
uv add <package>               # add a dependency
uv run python scripts/sync_skill_stubs.py --server deliverable-canvas-mcp-http  # regenerate .claude/skills/ stubs
uv run python scripts/sync_skill_stubs.py --server deliverable-canvas-mcp-http --check  # CI: exit 1 if stubs are stale
```

## Layout

```
src/server.py          FastMCP entrypoint (`mcp` instance)
src/config.py          Settings via pydantic-settings (reads .env)
src/auth.py            OAuth provider builder (disabled by default)
src/storage.py         Canvas persistence layer
src/store_singleton.py Process-wide store instance
src/template_loader.py Section template lookup
src/renderer/          Read-only HTML artifact renderer

components/tools/      @tool functions — auto-discovered, no registration
components/resources/  @resource functions
components/prompts/    @prompt functions
skills/                Skill directories — exposed as skill:// resources via SkillsDirectoryProvider
scripts/               Utility scripts (sync_skill_stubs.py)
tests/                 in-memory Client(transport=mcp) tests
```

### Layout decision (flat `src/`)

This MCP intentionally keeps `src/` flat (`src/server.py`, `src/storage.py`,
...) rather than wrapping under `src/deliverable_canvas/`. The Copier answer
`module_slug: deliverable_canvas` is therefore unused for path purposes — it
remains in `.copier-answers.yml` for future-proofing but is not load-bearing
here.

Why: the codebase is small enough that the extra package level adds noise
without payoff (single deployable, no `import deliverable_canvas` consumers,
flat layout already works with `from src.server import mcp` everywhere).
Adopting `src/deliverable_canvas/` is a low-priority follow-up; if you take
it on, `copier update --trust --skip-answered` against the post-2026-05-26
fastmcp-template will propose the structural move automatically.

See `scaffolds/fastmcp-template/CHANGELOG.md` for the upstream template
change that made `module_slug` load-bearing for new MCPs.

## Adding a component

Drop a `.py` file into the right `components/` subdirectory — `FileSystemProvider` picks it up automatically:

```python
from fastmcp.tools import tool   # or: resources.resource / prompts.prompt

@tool
def my_tool(param: str) -> str:
    """Description shown to the MCP client."""
    return param
```

No import in `server.py` needed. Type-hint everything; docstring becomes the schema description.

## Adding a skill

Create a subdirectory under `skills/` with a `SKILL.md` file:

```
skills/
└── my-skill/
    ├── SKILL.md          # Required — main instruction file (frontmatter: name, description)
    └── references/       # Optional — supporting files accessible via skill://<name>/{path}
```

Skills are exposed as MCP resources with `skill://` URI scheme. Clients discover skills via `list_resources()` and read them via `read_resource("skill://<name>/SKILL.md")`. `SkillsDirectoryProvider` handles discovery — no registration needed.

## Config

Add settings to `src/config.py` as `Settings` fields. Document them in `.env.example`. Never read `os.environ` directly inside components.

## Conventions

- Python 3.13, `uv` for all operations
- ruff: line-length 100, rules `E,F,I,UP,B`
- `MCP_DEV_MODE=true` enables hot-reload during development

## Agent-md & MCP rendering

This repo treats `AGENTS.md` and (optionally) `.agents/mcp.json` as the only authored sources. Run:

```bash
python scripts/render-agent-md.py            # CLAUDE.md + .github/copilot-instructions.md
python scripts/render-agent-md.py --check    # exit 1 if stale
python scripts/render-mcp.py                 # .mcp.json + .gemini/settings.json mcpServers + .codex/config.toml + .vscode/mcp.json
python scripts/render-mcp.py --check         # exit 1 if stale
```

**Never hand-edit** `CLAUDE.md`, `.github/copilot-instructions.md`, or any of the four per-agent MCP files — they all carry a "GENERATED FILE" banner; edits are wiped on next render.



## Deployment

Production runs on Azure Container Apps. The deploy path is:
- `Dockerfile` (multi-stage; runtime is `python:3.13-slim` + `uv sync --frozen`)
- `.github/workflows/deploy-aca.yml` builds on push to `main`, pushes to `ghcr.io/<owner>/<repo>`, then runs `az containerapp update`
- ACA pulls the new image and rolls the revision
- Liveness probe hits `GET /health` (defined in `src/server.py` via `@mcp.custom_route`)
- Production transport is `streamable-http` on port 8080; `min-replicas=0` (scale-to-zero)

One-time `az` CLI setup is documented in `README.md` → "Deploy to Azure Container Apps". Don't invent a different deploy path; extend this one.
