# Deliverable Canvas MCP

Resource-only planning host for multi-section deliverables (proposals, briefs, press releases, messaging frameworks). The MCP exposes **zero tools** — only templates and methodology as MCP resources. The canvas itself is the markdown artifact in the user's chat; the agent renders, validates, and packages it in chat. Matches the planned `stromy-format-mcp` pattern.

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
src/auth.py            OAuth provider builder (Microsoft Entra ID)
src/middleware.py      Tool-call logging middleware (used by audit)

components/resources/  @resource functions — template:// and methodology://
  ├─ template_resources.py     template://list, template://{template_id}
  ├─ methodology_resources.py  methodology://planning-best-practices,
  │                            methodology://rendering/{provider}
  ├─ templates/                template JSON files
  └─ methodology/              planning + rendering markdown files

skills/                Skill directories — exposed as skill:// resources via SkillsDirectoryProvider
scripts/               Utility scripts (sync_skill_stubs.py)
tests/                 in-memory Client(transport=mcp) tests
```

**No tools.** This MCP intentionally exposes zero `@tool` functions (resource-only,
post-2026-05-26 refactor). See `skills/deliverable-canvas/SKILL.md` for the
session protocol — the agent does all the work in chat.

## Resource surface

- `template://list` — JSON `{"templates": [<template_id>, …]}`.
- `template://{template_id}` — template JSON with `description`,
  `methodology_version`, and `sections: [{id, title, prompt_hint}]`.
- `methodology://planning-best-practices` — universal planning ritual.
- `methodology://rendering/{provider}` — host-specific rendering rules
  (`provider` ∈ `{claude, cowork, codex}`).

Auth gates *access* to these resources (framework-level). There is no per-user
data to partition because there is no canvas data — the canvas lives in the
user's chat as a markdown artifact with identifier
`canvas-<canvas_id>-<deliverable_type>`.

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

## Adding a resource

This MCP is resource-only. To add a new template or methodology variant, drop
the data file in the right place — no Python edits needed:

- New deliverable template: drop a JSON file in
  `components/resources/templates/<id>.json` matching the schema
  `{template_id, description, methodology_version, sections: [{id, title, prompt_hint}]}`.
- New rendering provider: drop `components/resources/methodology/rendering/<provider>.md`.
- New universal methodology variant: edit
  `components/resources/methodology/planning-best-practices.md`.

If you genuinely need a new `@resource` family (rare), drop a `.py` file in
`components/resources/` — `FileSystemProvider` picks it up automatically.
Do NOT add `@tool` functions; this MCP is resource-only by design.

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
- Production transport is `streamable-http` on port 8080; `min-replicas=0` (scale-to-zero — intentional)

## Operational notes

- **`min-replicas=0` is intentional.** Cold-start on first call after idle is
  ~1–2 s; this is preferred over the ~$5–15/month savings vs `min-replicas=1`.
- **OAuth `offline_access` scope is REQUIRED.** Without it the Claude app's
  connector has no refresh token and surfaces "Reconnect" every ~1h when the
  access token expires. `OAUTH_REQUIRED_SCOPES` is **whitespace-delimited**
  per OAuth 2.0 (RFC 6749); `src/auth.py` is the authoritative parser.
  Required value: `"mcp.access offline_access"`.
- **Artifact identifier convention.** The agent emits the canvas as a markdown
  artifact in chat with identifier `canvas-<canvas_id>-<deliverable_type>`
  where `<canvas_id>` is an 8-character hex generated once per session. The
  same identifier is reused for every emission in the session; different
  sessions MUST use different identifiers to prevent cross-chat version-history
  collisions.

One-time `az` CLI setup is documented in `README.md` → "Deploy to Azure Container Apps". Don't invent a different deploy path; extend this one.
