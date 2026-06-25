# Rules — kuchnie-core

> Quick reference for future sessions. Read this before touching code.
> If a rule conflicts with the code, the code wins — update this file.

---

## Architecture (3 rules)

**R1. Panel is the atom.** The CNC machine cuts panels, not cabinets.
Everything above panels (rows, kitchens) is grouping.
Everything on panels (edges, machining ops) is decoration.
→ `src/kuchnie_core/model.py::Panel`

**R2. Construction method ≠ Cabinet instance.** Decomposition rules live in
the catalog (one function per type). Cabinet instances carry only config
(dimensions, materials, drawers). The decomposer connects them.
→ `src/kuchnie_core/catalog.py`

**R3. Kitchen is the unit of work.** What flows between apps:
Kitchen → JSON (intermediate) → render-service / kitchen-cli.
The intermediate format is LOGICAL (rows + cabinets), not physical (panels).
Both consumers decompose independently via `kuchnie_core`.
→ `src/kuchnie_core/serialize.py`, `docs/adr/004-intermediate-format-is-logical.md`

---

## Adding a cabinet type (checklist)

1. Write `decompose_<type>(cab) → DecompositionResult` in `catalog.py`
2. Register in `TYPE_REGISTRY`
3. Create `fixtures/<ID>.yaml` (Polish keys — the loader handles mapping)
4. Write `tests/test_<type>.py` with assertions on panel count, dimensions, edges, accessories
5. Run `pytest` — all tests must pass

Each decompose function produces:

- Carcass panels (sides, top, bottom, back)
- Sub-assembly panels (drawer boxes, shelves)
- Front panels (doors, drawer fronts)
- MachiningOps on panels (drill, groove, rabbet)
- Accessories (runners, hinges, shelf pins, handles)

---

## LEGRABOX rules

All formulas in `src/kuchnie_core/legrabox.py`. All verified in `tests/test_legrabox.py`.

```
KB  = external_width − 2 × side_thickness     (cabinet internal width)
LW  = KB − 2 × 13mm                           (clear width, runner clearance)
Back width  = LW − 38                          (chipboard back panel)
Base width  = LW − 35                          (drawer base panel)
Base depth  = NL − 10                          (chipboard back variant)
Back height = per code: N=39, M=63, K=101, C=148, F=212
Both panels = 16mm chipboard                   (Blum spec, NOT 3mm or 12mm)
First runner screw = 46mm from cabinet front edge
```

Height × NL compatibility and capacity rules: `legrabox.py::NL_MATRIX`, `CAPACITY_NL`.

---

## Naming conventions

| Layer         | Language | Example                              |
| ------------- | -------- | ------------------------------------ |
| YAML fixtures | Polish   | `szerokosc`, `wysokosc`, `glebokosc` |
| Python model  | English  | `width_mm`, `height_mm`, `depth_mm`  |
| Loader        | Adapter  | `loader.py` maps PL → EN             |
| Panel names   | Polish   | `"Lewy bok"`, `"Dno"`, `"Plecy"`     |

Units: always mm. Field names include `_mm` suffix on dimensions.

---

## Edge banding rules

- Only edges that ARE banded appear in `panel.banded_edges`
- Empty dict `{}` = no banding (e.g., HDF back, drawer box panels)
- Edge band has explicit `length_mm` (set by catalog, not derived by BOM)
- Standard carcass: front edge only
- Standard fronts (doors/drawers): all 4 edges

→ `src/kuchnie_core/catalog.py` (each decompose function sets edges)

---

## MachiningOp coordinate system

Panel lying flat, viewed from the machined face:

- `x_mm` = from LEFT edge
- `y_mm` = from BOTTOM edge (front edge for carcass sides)
- `diameter_mm` = for drills/bores
- `depth_mm` = 0 means through-hole

→ `src/kuchnie_core/model.py::MachiningOp`

---

## Testing rules

- One test file per cabinet type: `tests/test_<type>.py`
- Test names describe the invariant: `test_back_dimensions`, `test_side_edge_banding`
- Expected values in test comments show the formula: `# 738 − 38 = 700`
- Full suite must pass before committing: `pytest -v`
- Current count: **84 tests** across 6 files

---

## Documentation rules

| Type      | File                | Staleness prevention                                          |
| --------- | ------------------- | ------------------------------------------------------------- |
| Decisions | `docs/adr/NNN-*.md` | Immutable — never edit, only supersede                        |
| Changelog | `CHANGELOG.md`      | Append-only — historical facts can't go stale                 |
| Rules     | `docs/rules.md`     | Update when rules change — references code, not duplicates it |
| Formulas  | Docstrings + tests  | Code wins — test fails if formula drifts                      |

**Never duplicate code in docs.** Reference it: `→ src/kuchnie_core/legrabox.py::lw()`

---

## File map

```
src/kuchnie_core/
├── model.py          Panel, MachiningOp, EdgeBand, Cabinet, Kitchen, Row
├── catalog.py        Decompose functions per cabinet type + TYPE_REGISTRY
├── decomposer.py     Thin dispatcher: CabinetInstance → DecompositionResult
├── bom.py            Per-cabinet costed BOM
├── legrabox.py       LEGRABOX catalog, formulas, validation, drawer decomposition
├── kitchen.py        Kitchen-level aggregation + row validation
├── loader.py         YAML → Model (cabinet + kitchen)
├── serialize.py      Kitchen ↔ JSON (intermediate format)
└── export/
    └── cutlist_csv.py  Aggregated cut list CSV

fixtures/             YAML cabinet + kitchen definitions
tests/                One test file per feature / cabinet type
docs/adr/             Architecture Decision Records
```

---

## Key invariants (pytest enforces these)

1. K01 decomposes into 6 panels (2 sides + bottom + back + 2 fronts)
2. G01 decomposes into 9 panels (2 sides + top + bottom + back + 2 shelves + 2 doors)
3. K02 (LEGRABOX) decomposes into 10 panels + 8 drill ops per side panel
4. LW = KB − 26mm (NOT KB − 2×side_thickness)
5. Drawer box panels are 16mm chipboard (NOT 3mm or 12mm)
6. JSON round-trip preserves all kitchen data
7. Cut list total quantity = total raw panel count
8. Kitchen BOM total = sum of all item totals
