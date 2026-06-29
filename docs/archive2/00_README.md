# Kuchnie — Solo-Dev Kitchen Design System

> **What:** Polish-market kitchen designer + manufacturer toolchain. One YAML kitchen → live 2.5D preview, 3D engineering render, CSV cut-list, DXF, BOM.
> **Who:** Solo carpenter/dev in Wrocław. Customers see real Kronospan/Egger decors interactively; CNC company gets e-rozkroj-compatible CSV/DXF.
> **Source of truth for use cases:** [`00-brief.md`](00-brief.md).

---

## The Six Subsystems

Each is a self-contained subdir with its own code, tests, and (often) `pyproject.toml`. **Zero cross-imports today** — the integration glue lives in `src/kuchnie_core/`.

| Subsystem | Canonical role | Read first |
|---|---|---|
| **`catalog/`** | Polish material catalog: 177 Kronospan decors, SQLite, FastAPI + Vite frontend. | `catalog/AGENTS.md` |
| **`src/kuchnie_core/`** | **The glue layer.** Owns the shared `Kitchen` YAML schema, `MaterialResolver`, `ConstructionMethod` registry, validation gates. Imports from the other 5 to give consumers one front door. | `01_DECISIONS.md` |
| **`kitchen-cad/`** | Parametric cabinet spec (`CorpusSpec`) → panels → drilling → CSV + DXF. 8 cabinet types. | `kitchen-cad/README.md` |
| **`kitchen-plugin/`** | 3D engineering renderer: Blender headless + DDD-layered domain (`Cabinet`, `Wall`, `Room`, `Layout`). Emits manifest JSON. | `kitchen-plugin/README.md` |
| **`krono-compositor-mvp/`** | 2.5D live compositor: offline 5-pass Blender bake + online OpenCV composite + FastAPI. ~500ms per material swap. | `krono-compositor-mvp/README.md` |
| **`kitchen-app/`** | Reflex web UI. Hosts the configurator, calls compositor for live preview, calls kitchen-cad for CSV. | `kitchen-app/README.md` |

`home_builder_5/` (sibling repo) is **external** community-maintained Blender addon — untouched.

---

## Read Order

1. **`00-brief.md`** — the three use cases. Everything else exists to serve these.
2. **`01_DECISIONS.md`** — locked architectural decisions (winner per concept, packaging, retirement).
3. **`02_WALKING_SKELETON.md`** — the first ~1 week of work. Thin slice through all six subsystems.
4. **`03_ROADMAP.md`** — what comes after the skeleton (~4–6 weeks to v1.0).
5. **`04_PROCESS.md`** — solo-dev rules + mandatory pre-planning checklist.
6. **`05_PATTERN_GOLD.md`** — distilled patterns from PRO100, Polyboard, Winner Flex, TopSolid'Wood, PaletteCAD. The architectural vocabulary.
7. **`06_AUDIT_EVIDENCE.md`** — full cold-execution analysis of all six prototypes (the evidence base for `01_DECISIONS.md`).
8. **`GLOSSARY.md`** — every term, with its canonical-owner module.
9. `archive/` — superseded docs kept for git history. Do not read unless tracing a decision.

---

## The One Rule

**No cross-subsystem import except via `src/kuchnie_core/`.** If `kitchen-app/` needs a `Panel`, it imports `kuchnie_core.recipe.Panel` — never `kitchen_cad.models.Panel` directly. The glue layer owns the contract; subsystems own implementations. Violating this re-introduces the parallel-prototype problem.

---

## For LLM Sessions

Before any planning or code suggestion, **run the pre-planning checklist in `04_PROCESS.md`**. Three audit misses in this project's history (documented in `06_AUDIT_EVIDENCE.md`) were all caused by skipping it.
