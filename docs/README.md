# Documentation Structure

## Layers

| Layer | Directory | Purpose | Trust Level |
|-------|-----------|---------|-------------|
| Vision | `vision/` | Strategy, mission, roadmap | Aspirational |
| Decisions | `adr/` | Immutable architecture decisions | High |
| Shared | `*.md` | Cross-project docs | Varies |
| Archive | `archive/` | Historical, no longer current | Low |

## Projects

Each project has its own `docs/` directory with:
- `specs/` — contracts and specifications
- `adr/` — project-specific decisions
- `architecture/` — current state documentation
- `archive/` — historical docs

## See Also

- `REORGANIZATION_PLAN.md` — migration details
- Per-project `AGENTS.md` — AI agent guides
