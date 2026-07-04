# Agent Guide — kuchnie-core

Read this before making changes. It's short on purpose.

---

## Project at a glance

Kitchen cabinet decomposition engine. Takes YAML cabinet definitions, produces physical panels with dimensions, edge banding, and machining operations. Outputs: BOM, cut list CSV, intermediate JSON.

**One sentence**: YAML → `CabinetInstance` → `decompose()` → `Panel[]` → CSV / JSON / BOM

---

## Component roster (monorepo)

This repo hosts 6 components. `kuchnie_core` is the pure-Python domain hub; every other component depends on it, never the other way. Roles and boundaries are codified in ADRs 009–011.

| Component | Role | AGENTS.md | Defining ADR |
|---|---|---|---|
| `kuchnie-core/` | **Domain hub** — Kitchen, Panel, decomposition, BOM, standards, validator. Pure Python. Imported by everyone. | this file | 001, 002, 003 |
| `catalog/` | Material catalog service — Kronospan/Egger decors, worktops, pairings, availability. FastAPI + SQLite. | `catalog/AGENTS.md` | 008 |
| `krono-compositor-mvp/` | **Sales tool (Stage 1)** — first-visit 2.5D previews + decor picker + screenshots. FastAPI + OpenCV + Alpine.js. | `krono-compositor-mvp/AGENTS.md` *(todo)* | 011 |
| `kitchen-erp/` *(was `kitchen-app/`)* | **BOM · cost · purchasing · rules admin · ops UI.** Reflex + SQLModel. Consumes `kuchnie_core` for domain computations. | `kitchen-erp/AGENTS.md` *(todo)* | 011 |
| `kitchen-cam/` *(was `kitchen-cad/`)* | **CAM enrichment** — machining ops (System32, hinges, handles), DXF for CNC shop. Downstream consumer of `kuchnie_core`. | `kitchen-cam/AGENTS.md` *(todo)* | 010 |
| `home-builder-adapter/` *(was `kitchen-plugin/`)* | **Blender scene extractor** — walks `home_builder_5` `.blend` tree → `kuchnie_core.Kitchen`. Only `bpy`-dependent component. | `home-builder-adapter/AGENTS.md` *(todo)* | 009 |

**External (not in this repo):**

- `/Users/michal/PycharmProjects/home_builder_5` — third-party licensed Blender addon used for interactive kitchen layout (Stage 2). Untouched per F007 Rule 4. Its scene tree is the input to `home-builder-adapter/`.

**Dependency direction:** every peripheral component imports `kuchnie_core`. No cycles. `kuchnie_core` imports only stdlib + Pydantic + PyYAML.

**Workflow stages:** Sales → Design (`home_builder_5`) → Extract (`home-builder-adapter`) → Refine + BOM (`kitchen-erp`) → CAM (`kitchen-cam`).

---

## Architecture (3 rules)

1. **Panel is the atom.** Not the cabinet. Everything above panels is organizational. Everything on panels (edges, machining ops) is decoration. (`ADR-001`)

2. **Construction method ≠ Cabinet instance.** The catalog (`catalog.py`) knows HOW to decompose. The model (`model.py`) knows WHAT was configured. The decomposer connects them. (`ADR-002`)

3. **Kitchen is the unit of work.** Serialize, render, export — always at kitchen level, never individual cabinets. (`ADR-003`)

---

## File map

```
kuchnie-core/src/kuchnie_core/
├── model.py          Dataclasses. No logic. No imports from other modules.
├── catalog.py        Decompose functions per cabinet type. Imports model only.
├── decomposer.py     Thin dispatcher: type → catalog function. 20 lines.
├── bom.py            Panels + accessories → costed BOM.
├── legrabox.py       LEGRABOX-specific catalog data + drawer decomposer.
├── loader.py         YAML → model. Adapter, no business logic.
├── kitchen.py        Kitchen-level aggregation (all_panels, kitchen_bom, validate).
├── serialize.py      Kitchen ↔ JSON. The intermediate format contract.
├── export/           CSV, DXF, etc. One file per output format.
```

**Dependency direction**: `export/` → `kitchen.py` → `decomposer.py` → `catalog.py` → `model.py`
Never import downward. `model.py` imports nothing from this package.

---

## Adding a cabinet type (step by step)

1. Write a `decompose_<type>(cab: CabinetInstance) -> DecompositionResult` function in `catalog.py` (or a dedicated module like `legrabox.py` for complex types)
2. Register in `TYPE_REGISTRY` dict at the bottom of `catalog.py`
3. Create a fixture YAML in `fixtures/`
4. Write tests that verify:
   - Panel count
   - Each panel's width, height, thickness
   - Edge banding (which edges, which material)
   - Machining ops (type, position, diameter)
   - Accessories (type, quantity)
5. Run `pytest -v` — all tests must pass

---

## Adding a feature

1. **Write the test first** (what should happen?)
2. **Write the code** (make the test pass)
3. **Check existing tests** still pass (`pytest -v`)
4. **Document the decision** if it's non-obvious → `docs/adr/NNN-<slug>.md`
5. **Append to CHANGELOG.md** under today's date

---

## Documentation conventions

| What | Where | Staleness-proof because |
|---|---|---|
| "We chose X because Y" | `docs/adr/NNN-*.md` | Immutable. New decision = new ADR. |
| "The formula is Z" | Docstring + test assertion | Test fails if code drifts. |
| "What changed" | `CHANGELOG.md` | Append-only. Historical fact. |
| "How to use this" | Module docstring at top of file | Reviewed with code. |
| "How the system works" | `AGENTS.md` (this file) | Keep under 200 lines. Update when architecture changes. |

**Never write a separate doc that restates what the code does.** If the code is clear and tested, it IS the documentation.

### File naming

- **kebab-case**: `configurator-api.md`, `wall-centric-model.md`
- **SCREAMING_SNAKE**: `README.md`, `CHANGELOG.md`, `AGENTS.md` only
- **Numbered**: ADRs (`001-*.md`) and vision (`00-*.md`) only
- **English**: file names in English, content can be Polish
- Full rules: `docs/file-naming-convention.md`

---

## Testing conventions

- **One test file per concern**: `test_K01_decomposition.py`, `test_legrabox.py`, `test_serialize.py`
- **Test names describe behavior**: `test_drawer_box_back_dimensions`, not `test_legrabox_3`
- **Assertions show the formula**: `assert back.width_mm == 700  # LW−38 = 738−38`
- **Fixture YAMLs in `fixtures/`**: one per cabinet type, one per kitchen layout
- **Run `pytest -v` before every commit**

---

## Conventions

- **Units**: always mm. Field names end with `_mm`: `width_mm`, `depth_mm`, `diameter_mm`
- **Coordinate system on panels**: x = left edge, y = bottom/front edge, viewed from machined face
- **Edge banding**: only edges that ARE banded appear in `banded_edges` dict. Absent = not banded.
- **Machining ops**: only ops that exist appear in `machining_ops` list. Empty list = no machining.
- **YAML keys**: Polish (user-facing). **Model fields**: English (engine-facing). Loader is the adapter.
- **JSON intermediate format**: self-contained (no external references), versioned (`"version": "1.0"`)

---

## What NOT to do

- Don't put panel dimensions in `CabinetInstance` — that's the catalog's job
- Don't import `catalog.py` from `model.py` — dependency goes one way
- Don't write a doc that restates code — write a test instead
- Don't edit an old ADR — write a new one that supersedes it
- Don't hardcode material thicknesses — use the YAML or Blum spec defaults
- Don't aggregate panels in the decomposer — aggregation happens in `export/`

---

## Documentation governance

> Source: `docs/DOC-GOVERNANCE-KIT.md` Layer 0. Merged here at resume time.

1. **Evidence protocol.** Every repo-state claim in any doc or review is tagged
   `VERIFIED(cmd)` / `INFERRED(basis)` / `UNVERIFIED`. Hedging is not a
   substitute for the tag.
2. **New-doc gate.** No new `.md` without three answers in the file header:
   `Reader:`, `Enables:`, `Update-trigger:`. Empty answer = don't write the
   doc.
3. **New-component gate.** No new top-level package without an accepted ADR
   stating purpose, why existing components can't absorb it, and lifespan.
   Run a duplication scan first. This rule would have prevented the
   kitchen-cam fork.
4. **Review output contract.** Audits/reviews are: 3-line TL;DR → 2–4 P0
   findings with evidence → one matrix → unknowns → one question. No praise
   without a named trade-off.
5. **Diagram labels.** Every architecture diagram is captioned `OBSERVED`
   (each arrow grep-verified) or `PROPOSED`. No unlabeled arrows.
6. **Freshness ritual.** At every freeze or quarter boundary, rerun the trust
   audit (`docs/freeze/FREEZE-PLAN.md`, Prompt 1 pattern) and re-stamp.
   STALE stamps are removed only by rewriting against code.

Trigger moments: session start → read order · new .md → gate 2 ·
new component → gate 3 · any review → contract 4 · new diagram → rule 5 ·
freeze/quarter → ritual 6.

Enforced by: Layer 1 (pre-commit hook, `scripts/check-governance.sh`) and
Layer 2 (LLM semantic gate, `scripts/llm-doc-gate.sh`, manual for now).

---

## Key formulas (reference, verified by tests)

| Formula | Source | Test |
|---|---|---|
| Carcass side height = cabinet_height − plinth_height | Standard | `test_side_dimensions` |
| Bottom width = cabinet_width − 2 × side_thickness | Standard | `test_bottom_dimensions` |
| Back width = cabinet_width − 2 × side + 2 × groove | Standard | `test_back_dimensions` |
| LEGRABOX LW = KB − 2 × 13mm | Blum DQBQRY | `test_lw_formula` |
| Drawer back = LW − 38 wide × back_height tall | Blum | `test_drawer_box_back_dimensions` |
| Drawer base = LW − 35 wide × NL−10 deep | Blum | `test_drawer_box_base_dimensions` |
| Drawer box panels = 16mm chipboard | Blum | `test_drawer_box_back_dimensions` |
| Runner first screw = 46mm from front | Blum | `test_drawer_box_first_screw_position` |

If a formula changes, update the function, the test, and the ADR (as a new ADR, not editing the old one).

---

## Current state

- 3 cabinet types: `dolna_szufladowa`, `gorna_drzwiowa`, `dolna_legrabox`
- 84 tests passing
- LEGRABOX: C height fully verified, M/F heights from catalogue (not yet PDF-confirmed)
- Runner screw positions: partial (PoC values, full table needed from Blum Montageanleitung)

---

## Doc routing (what to update when)

| Change | Update | Skip |
|--------|--------|------|
| New feature | `CHANGELOG.md` + relevant spec | `vision/` |
| Bug fix | `CHANGELOG.md` only | Everything else |
| Formula change | Spec + test + `CHANGELOG.md` | `architecture/` |
| Schema change | Spec + ADR + `CHANGELOG.md` | `vision/` |
| New decision | `docs/adr/NNN-*.md` | — |
| Config change | `docs/config-syntax.md` + `CHANGELOG.md` | `vision/` |

**Max 3 doc files per change.** If more, you're over-documenting.

Full routing: `docs/DOC_ROUTING.md`

---

## When stuck

1. Read the relevant ADR in `docs/adr/`
2. Read the test that verifies the behavior you're changing
3. Read the fixture YAML to understand the input shape
4. Run `pytest -v` to see what's currently passing
