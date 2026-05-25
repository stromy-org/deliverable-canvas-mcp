# Section Schemas

Templates live in `MCPs/deliverable-canvas-mcp/templates/<template_id>.json`. Each defines the section list a new canvas of that type starts with.

## Format

```json
{
  "template_id": "proposal_v1",
  "description": "Stromy/Duke Strategies consulting proposal section schema",
  "sections": [
    {"id": "context",    "title": "Context"},
    {"id": "approach",   "title": "Approach"},
    {"id": "scope",      "title": "Scope"},
    {"id": "timeline",   "title": "Timeline"},
    {"id": "pricing",    "title": "Pricing"},
    {"id": "risks",      "title": "Risks"},
    {"id": "next_steps", "title": "Next Steps"}
  ]
}
```

Section `id` is the stable key used by `canvas_update_section` and by formatter skills to map sections to layout slots. Once a template is in production use, don't rename an `id` — bump the `template_id` (`proposal_v2`) instead.

## Bundled templates

| template_id      | deliverable_type     | sections |
|------------------|----------------------|----------|
| `proposal_v1`    | proposal             | context, approach, scope, timeline, pricing, risks, next_steps |

## Adding a new template

1. Create `templates/<new_id>.json` with the format above.
2. Add a mapping entry in the consuming formatter skill (e.g. `Cowork/skills/pptx/references/canvas-mapping.md`) so the formatter knows how each section becomes a slide / page / block.
3. Optional: write a test in `tests/test_storage.py` that creates a canvas with this template and asserts the section list.

No code changes needed in the MCP — templates are data, loaded by `src/template_loader.py` at request time.
