# Agent Guide — kuchnie-core

Read this before making changes. It's short on purpose.

---

## Project at a glance

Kitchen cabinet decomposition engine. Takes YAML cabinet definitions, produces physical panels with dimensions, edge banding, and machining operations. Outputs: BOM, cut list CSV, intermediate JSON.

**One sentence**: YAML → `CabinetInstance` → `decompose()` → `Panel[]` → CSV / JSON / BOM

---

## Architecture (3 rules)

1. **Panel is the atom.** Not the cabinet. Everything above panels is organizational. Everything on panels (edges, machining ops) is decoration. (`ADR-001`)

2. **Construction method ≠ Cabinet instance.** The catalog (`catalog.py`) knows HOW to decompose. The model (`model.py`) knows WHAT was configured. The decomposer connects them. (`ADR-002`)

3. **Kitchen is the unit of work.** Serialize, render, export — always at kitchen level, never individual cabinets. (`ADR-003`)

---

## File map

```
src/kuchnie_core/
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

## When stuck

1. Read the relevant ADR in `docs/adr/`
2. Read the test that verifies the behavior you're changing
3. Read the fixture YAML to understand the input shape
4. Run `pytest -v` to see what's currently passing
