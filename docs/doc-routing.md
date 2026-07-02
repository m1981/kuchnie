# Documentation Routing Instructions

When making changes, update the RIGHT files based on what changed.

---

## Decision Tree

```
What changed?
│
├─ CODE (src/, *.py)
│  ├─ New feature/module → specs/ + architecture.md + CHANGELOG.md
│  ├─ Bug fix → CHANGELOG.md only
│  ├─ Refactor → architecture.md + CHANGELOG.md
│  └─ Formula/algorithm changed → spec that describes it + test
│
├─ SCHEMA (db/schema.sql, models/)
│  ├─ New table/column → specs/ + ADR + CHANGELOG.md
│  └─ Migration → CHANGELOG.md + migration doc if complex
│
├─ API (api/routers/)
│  ├─ New endpoint → specs/configurator-api.md + CHANGELOG.md
│  ├─ Changed endpoint → specs/configurator-api.md + CHANGELOG.md
│  └─ Removed endpoint → CHANGELOG.md + mark deprecated in spec
│
├─ CONFIG (configs/, *.json, *.yaml)
│  ├─ New config type → docs/config-syntax.md + CHANGELOG.md
│  └─ Changed config format → docs/config-syntax.md + CHANGELOG.md
│
├─ MATERIALS (data/, materials/)
│  ├─ New material/supplier → docs/materials/ + CHANGELOG.md
│  └─ Changed material spec → docs/materials/ + CHANGELOG.md
│
└─ DECISION (architecture choice)
   ├─ Reversible → docs/adr/NNN-<slug>.md
   └─ Irreversible → docs/adr/NNN-<slug>.md + update AGENTS.md if it affects constraints
```

## File Routing Table

| Change Type | Update These | Don't Touch |
|-------------|--------------|-------------|
| New cabinet type | `catalog/docs/specs/`, `CHANGELOG.md` | `vision/` |
| New decompose function | `src/` ADR if novel, `CHANGELOG.md` | `specs/` unless formula changes |
| New API endpoint | `catalog/docs/specs/configurator-api.md`, `CHANGELOG.md` | `architecture/` |
| Schema change | `catalog/docs/specs/`, ADR, `CHANGELOG.md` | `vision/` |
| New material data | `catalog/docs/materials/`, `CHANGELOG.md` | `specs/` |
| Blender geometry fix | `krono-compositor-mvp/docs/specs/`, `CHANGELOG.md` | `architecture/` |
| Config syntax change | `home-builder-adapter/docs/config-syntax.md`, `CHANGELOG.md` | `vision/` |
| Formula correction | Relevant spec + test + `CHANGELOG.md` | `architecture/` |
| Dependency update | `CHANGELOG.md` only | Everything else |
| Test addition | Nothing (tests ARE the doc) | Everything |

## The Three Files Rule

Every meaningful change touches **at most 3 doc files**:

1. **CHANGELOG.md** — always (append-only, one line)
2. **Relevant spec** — if behavior changed
3. **ADR** — if a decision was made

If you're touching more than 3 doc files, you're probably over-documenting.

## CHANGELOG Format

```markdown
## [Unreleased]

### Added
- feat(catalog): worktop_compatibility table for front↔worktop matching

### Changed
- fix(kitchen-cam): corrected LEGRABOX side panel formula

### Deprecated
- (nothing)

### Removed
- chore: deleted stale Kronospan images from public/
```

## ADR Format (New Decision)

```markdown
# NNN-<slug>

## Status
Accepted <!-- or Superseded by NNN, Deprecated -->

## Context
What is the issue that we're seeing that is motivating this decision?

## Decision
What is the change that we're proposing and/or doing?

## Consequences
What becomes easier or harder?
```

## When NOT to Update Docs

- **Typo fix** → no doc change
- **Import cleanup** → no doc change
- **Test addition** → tests ARE the documentation
- **Formatting** → no doc change
- **CI/build** → no doc change

## Project-Specific Routing

### kuchnie-core (root)
| File | When |
|------|------|
| `AGENTS.md` | Architecture constraints changed |
| `docs/adr/NNN-*.md` | New decision made |
| `CHANGELOG.md` | Always |

### catalog/
| File | When |
|------|------|
| `catalog/AGENTS.md` | Architecture constraints changed |
| `catalog/docs/specs/configurator-api.md` | API endpoint changed |
| `catalog/docs/specs/builder-gui.md` | GUI behavior changed |
| `catalog/docs/specs/scenarios-edge-cases.md` | New edge case discovered |
| `catalog/docs/architecture/configurator-design.md` | Design pattern changed |
| `catalog/docs/materials/*.md` | Material data changed |
| `catalog/docs/adr/NNN-*.md` | New decision made |
| `catalog/CHANGELOG.md` | Always |

### kitchen-cam/
| File | When |
|------|------|
| `kitchen-cam/AGENTS.md` | Migration status or constraints changed |
| `kitchen-cam/docs/architecture.md` | Pipeline structure changed |
| `kitchen-cam/docs/specs/legrabox-spec.md` | LEGRABOX formula changed |
| `kitchen-cam/docs/specs/cabinet-variants.md` | New cabinet type added |
| `kitchen-cam/CHANGELOG.md` | Always |

### home-builder-adapter/
| File | When |
|------|------|
| `home-builder-adapter/AGENTS.md` | Extraction rules or constraints changed |
| `home-builder-adapter/CHANGELOG.md` | Always |

### kitchen-erp/
| File | When |
|------|------|
| `kitchen-erp/CHANGELOG.md` | Always |

### krono-compositor-mvp/
| File | When |
|------|------|
| `krono-compositor-mvp/docs/architecture.md` | Compositor design changed |
| `krono-compositor-mvp/docs/specs/pipeline-rules.md` | Pipeline rules changed |
| `krono-compositor-mvp/docs/specs/blender-scene-ref.md` | Blender scene params changed |
| `krono-compositor-mvp/CHANGELOG.md` | Always |

## Prompt Template

When asking the LLM to make changes, include:

```
Update the following docs for this change:
- [ ] CHANGELOG.md (append under [Unreleased])
- [ ] Relevant spec in docs/specs/ (if behavior changed)
- [ ] ADR in docs/adr/ (if a decision was made)
- [ ] AGENTS.md (if architecture constraints changed)

Don't touch:
- docs/vision/ (strategy docs, update separately)
- docs/archive/ (historical, never modify)
```
