# Session Handoff — 2026-07-08 (cold-review fix session)

**Purpose.** Give a fresh LLM session the shortest complete context on the
cold-review fix work (findings F1–F6), the testing doctrine it established,
and what remains open. Paste into a new session's opening turn, or read
after `AGENTS.md` → `RESUME.md`.

---

## TL;DR — what happened

A cold review along execution paths (YAML → decompose → drilling → export,
and Blender → adapter → JSON hub) had confirmed **6 defects (F1–F6)**. This
session fixed all six **test-first**, one finding at a time, red → green,
in two commits:

| Commit | What |
|---|---|
| `afd7e04` | fix: cold-review findings F1–F6 — seam defects, TDD across execution paths (22 files, +853/−47) |
| `a3c436f` | docs: RESUME — record fix commit, close resume-menu item 4 (adapter tests) |

**Test baseline after the session (all green, root `.venv`):**

- `kuchnie-core`: **680 pass**
- `kitchen-cam`: **57 pass** (2 former ezdxf skips now run — ezdxf installed)
- `home-builder-adapter`: **13 pass** (first tests this component ever had)
- `catalog`: **236 pass**

Commits landed after this session (other workstreams, not covered here):
truth-ledger series `854ad28`…`9e1ceff`, plus `4aad26c`/`be3964a` doc
removals.

---

## The six findings and their fixes

**F1 — serialize round-trip loses nested specs.**
`serialize._build_cabinet` left `handles`/`shelf_pins`/`hinges` as plain
dicts and never re-synthesised `config`. Fixed: rehydrate into
`HandleSpec`/`ShelfPinSpec`/`HingeGeometry`, drop stored `config`, re-run
`loader._apply_synthesised_config`. Contract test: `decompose(roundtrip(k))`
asdict-equal to `decompose(k)` for K01/G01/K02_legrabox.
→ `kuchnie-core/src/kuchnie_core/serialize.py`

**F2 — edging CSV re-derived lengths instead of using stored bands.**
`collect_edging_rows` now uses `band.length_mm` as authoritative;
derivation via `_edge_length_mm` is only the fallback for length-less
bands. Invariant test: K01 left-side front edge = `side.height_mm` (620),
not width (510).
→ `kuchnie-core/src/kuchnie_core/export/edging_csv.py`

**F3 — hinges=None on the YAML path produced zero drillings.**
Semantics fixed repo-wide: `hinges=None` means *not specified* → Blum
CLIP top defaults (`HingeGeometry()` now defaults cup ⌀35 mm × 13 mm
deep). Explicit opt-out is `ilosc_zawiasow: 0` on the front.
→ `kuchnie-core/src/kuchnie_core/blum_hinges.py`,
`kitchen-cam/src/kitchen_cam/machining.py` (`apply_hinges`: dead
`cab.handles` guard removed, `hinge = cab.hinges or HingeGeometry()`).

**F4 — LEGRABOX runner ops: wrong axis, no stacking, aliased left/right.**
Root cause was a *contradictory axis convention* between `model.py` and
kitchen-cam. Canonical now (docstring fixed in `model.py`):
`x_mm` = distance from LEFT edge of panel — for carcass side panels that
is the cabinet FRONT edge; `y_mm` = distance from BOTTOM edge.
`decompose_drawer_box(..., *, runner_y_mm)` is keyword-only and required
(a runner op without a vertical position is scrap board). Ops carry
`x_mm` = Blum NL500 screw offsets {46, 78, 110, 398}, `y_mm` = runner
height, `face="inside"`, `drill_type="runner_screw"` (ADR-012 §2 routing).
`catalog.decompose_dolna_legrabox` stacks `runner_y` per drawer and gives
the right side `copy.deepcopy`-ed ops (no shared objects). TODO comment in
catalog.py: exact Blum screw-axis offset within the zone pending
Montageanleitung transcription.
→ `kuchnie-core/src/kuchnie_core/{legrabox,catalog,model}.py`

**F5 — home-builder-adapter constructor drift (dead on arrival).**
`cabinets_to_kitchen` called `CabinetInstance`/`Row`/`Kitchen` with
long-renamed field names; CLI ignored its `.blend` argument. Fixed both;
materials from Blender extraction are explicitly `"unassigned"` (Blender
carries geometry, not decor codes — BOM resolves against catalog,
ADR-008). CLI honours Blender's `--` argv convention and opens the
`.blend` via `bpy.ops.wm.open_mainfile`. First-ever adapter tests (13)
via **fake-bpy conftest** (inject fake `bpy` into `sys.modules` before
importing the module under test), including the ADR-004 contract test:
extract → JSON round-trip → decompose.
→ `home-builder-adapter/{src/{extract,cli}.py,tests/,pyproject.toml}`

**F6 — machining_ops had no output consumer.**
New generic writer `panel_to_dxf(panel, path)`: outline LWPOLYLINE + one
circle per drill op, layer per `drill_type` (SYSTEM32/SHELF_PIN/HINGE_CUP/
HINGE_SCREW/RUNNER_SCREW/HANDLE, fallback DRILL). Draws EXACTLY what the
model says — adds no positions of its own (contrast:
`legrabox_side_panel.py` re-computes geometry; candidate for retirement
after output comparison). Tests are **semantic-golden**: write, read back
with ezdxf, assert the entity model — never byte-golden.
→ `kitchen-cam/src/kitchen_cam/dxf/panel_dxf.py`

---

## Testing doctrine established (reuse in future work)

1. **Round-trip contract tests** — assert `decompose(roundtripped)` equals
   `decompose(original)`; the decomposer is the real consumer of ADR-004
   JSON, not field-by-field dict comparison.
2. **Physical invariant tests** — drillings inside panel bounds (with
   radius margin), depth < thickness, edging length = physical edge
   length, mirrored sides carry independent op objects (`id()` sets).
3. **Vendor reference data** — Blum values hardcoded from catalogue
   sheets into tests ({46, 78, 110, 398}; cup ⌀35×13; System 32 = 37 mm
   offset / 32 mm pitch). Never re-derive expected values with the
   formula under test.
4. **Semantic-golden file tests** — for DXF and similar formats, assert
   the parsed entity model, not bytes.
5. **Blessed-bug tests get corrected, not deleted.** Three legacy tests
   encoded the defects (runner axis in `test_legrabox.py`, empty
   `drill_type` in `test_machining_op.py`, hinges=None→0 ops in
   `test_drill_engine.py`); each was rewritten to state the intended
   contract.
6. Red tests must fail **for the physical reason** ("0 hinge cups"), not
   with import errors.

Key seam suites: `kuchnie-core/tests/test_execution_paths.py`,
`kitchen-cam/tests/{test_yaml_path_drilling,test_panel_dxf}.py`,
`home-builder-adapter/tests/`.

---

## Environment changes made

- `ezdxf` installed into root `.venv` (optional dep; brought numpy,
  pyparsing).
- `kitchen-cam/pyproject.toml`: `pythonpath = ["src"]` added to pytest
  config (same pattern as kuchnie-core).
- `home-builder-adapter/pyproject.toml`: pytest config added —
  `pythonpath = ["."]`; the package literally lives at `src/` and is
  imported as `src.extract`.

---

## Open items (nobody asked for these yet — cold-review minors)

- Worktop `length_mm=0  # Will be calculated` in loader — never
  calculated.
- Construction thickness fields typed `int`, should be `float`.
- `dict[str, callable]` typing in the type registry.
- `GrainAxis` unused — no grain handling in cutlist.
- Resolver docstring makes a false claim.
- Adapter maps `TALL → tall_oven`; decompose coverage for `tall_oven`
  untested (may not be in `TYPE_REGISTRY`).
- F4 TODO: exact Blum screw-axis offset within runner zone (needs
  LEGRABOX Montageanleitung transcription).
- `legrabox_side_panel.py` duplicates drilling constants now owned by the
  model + `panel_to_dxf`; retire after comparing outputs.

Larger agreed direction (user's "#2"): wire kitchen-erp and krono to
catalog as material truth — RESUME menu items 2, 3, 5. Item 4 is DONE.

---

## Standing constraints (carried across sessions)

- Commit only files you've touched.
- Never touch `home_builder_5/` (external licensed addon, F007 Rule 4).
- ADRs and `docs/freeze/` are immutable; `RESUME.md` is the single living
  status doc.
- Model fields English, YAML keys Polish; docstring + test = documentation.

---

# Continuation — 2026-07-08 (session 2: ADR-011 old-BOM deletion)

**Note on status docs:** `RESUME.md` was deleted (`be3964a`) — current
migration state now lives in the truth ledger (`scripts/truth list --live`)
and this doc. `docs/freeze/MIGRATION-STATUS-2026-07.md` remains an immutable
(and partially superseded) snapshot.

## What happened

Picked up the "larger agreed direction" (wire kitchen-erp to canonical
domain/material truth). Executed the first ADR-011 chunk **test-first** in
one commit:

| Commit | What |
|---|---|
| `f819da9` | feat(kitchen-erp): delete old BOM path — recipe BOMGenerator is the only cost path (16 files, +341/−490) |

- **Deleted:** `Cabinet.calculate_cost()`, `use_new_bom` toggle + UI switch,
  `*_new` suffixes (canonical names kept), orphaned `CabinetCostResult`;
  `scripts/validate_migration.py` → `attic/` (its comparison job is done).
- **Suite repaired first: 38 pass / 15 broken → 66 pass.** kitchen-erp had
  no recorded baseline and had rotted along four axes: fixtures missing
  `Material.unit`, `ProjectDefaults.edge_band_mat_id`, `Cabinet.type`,
  `Project.customer_name`; `test_rules_engine` importing the deleted
  `HARDWARE_RULES`; expectations naming renamed hardware ("Drawer slides" →
  "Drawer System (Blum/Hettich)"); old-vs-new comparison tests pinned to the
  deleted path.
- **Doctrine additions (extends the six rules above):**
  7. Unit tests must not depend on the app database — pin rules with
     `RulesEngine(get_default_hardware_rules())`; a no-arg `RulesEngine()`
     reads `database.db` via a class-level cache.
  8. Deletions get pinning tests (`tests/test_adr011_canonical_bom.py`)
     so the deleted path cannot quietly grow back.
- New deterministic pricing test: `tests/test_calculations.py` hand-computes
  a WALL_CABINET BOM to **$155.80** from recipe formulas + default rules
  (doctrine rule 3 applied to the canonical path).
- Front-material semantics stated in tests: `has_custom_front` only selects
  the MATERIAL; any cabinet with doors/drawers gets a front part (defaults
  when no override), zero-front cabinets get none.
- Run suite via `uv run --with pytest --with pytest-asyncio -- python -m
  pytest tests/ -q` in `kitchen-erp/` (pytest is a dev dep; root `.venv`
  lacks sqlmodel).

## Truth-ledger integration (first live decay event)

The post-commit scan staled 3 claims; handled per protocol: `tr-6e83eb77`
(old path present) → **diverged**, queued for human retraction;
`tr-50764deb` (zero kuchnie_core imports) and `tr-d7dd1870` (Material still
independent) re-verified **live** with advanced anchors; successor claim
`tr-65e723dd` (old path deleted) filed. Tripwire precision this event: 3
fired / 1 fact actually changed.

## Open items after this session

1. **ADR-011 phase 2 (next):** wire `BOMGenerator.generate()` →
   `kuchnie_core.decompose()` via `to_kuchnie_core(cabinet_sqlmodel) ->
   CabinetInstance` adapter; panels from the domain hub, pricing stays in
   erp.
2. **Material mirror:** `kitchen_erp.Material` becomes a cache/mirror of
   `catalog/` (ADR-008/011); then krono's hardcoded `CATALOG` dict routes to
   the catalog service (claims `tr-d7dd1870`, `tr-88dc0d9a` watch these).
3. Human decision queued: retract `tr-6e83eb77` (`TRUTH_HUMAN=1`).
4. Cold-review minors from session 1 remain unaddressed (list above).

---

# Continuation — 2026-07-08 (session 3: ADR-011 phase 2 executed)

Item 3 done: Michal retracted `tr-6e83eb77` himself (first human tombstone).
Item 1 done in commit `c9fd86c`:

- **`kitchen_erp/core/domain_adapter.py` (new):** `to_kuchnie_core()` maps
  `Cabinet` → `CabinetInstance` (`BASE_CABINET→dolna_drzwiowa`,
  `WALL_CABINET→gorna_drzwiowa`, `DRAWER_BASE→dolna_szufladowa`; other
  kinds → `None`). Doors/drawers synthesize `fronts`/`drawers` dicts
  (drawer front height = (side_h − 3·(n+1))/n). `quantities_from_decomposition()`
  folds panels by `PanelRole` into corpus/back/front m2 + corpus/front
  edging lm (real `banded_edges` lengths, back never banded).
- **`BOMGenerator.generate()`:** domain quantities when the adapter returns
  an instance; recipe formulas only as fallback (appliances, fillers,
  panels). Pricing, rules engine, plinth logic unchanged — pricing stays
  in erp. Fixed on the way: gated-off fronts no longer charge ghost
  edging/CNC (the old path did).
- **Packaging:** kitchen-erp depends on `kuchnie-core` via editable path
  source (`[tool.uv.sources]`); uv resolves it transparently in `uv run`.
- **Suite 66 → 76** (9 adapter tests + ghost-cost pinning test). Reference
  wall-cabinet price hand-computed from the construction: **$141.05**
  (sides 2×300×500, top/bottom 2×964×300, back 980×480, door 994×494,
  edging 5.904 lm) — replaces the $155.80 formula estimate.

Ledger: mini-round verifier **diverged** on `tr-65e723dd` (my successor
claim from session 2) — text said "no calculate_cost or use_new_bom
ANYWHERE" while the evidence grep matched the pinning tests; scope
overstatement by the author, caught by an isolated verifier. Replaced by
`tr-b270996f` (correctly scoped to `kitchen_erp/` production package).
Phase-2 commit tripped `tr-50764deb` (zero kuchnie_core imports) —
diverged, replaced by `tr-b485d74c`. Tripwire precision this event: 1/1.

## Open items after session 3

1. **Material mirror (next):** item 2 above, unchanged.
2. Human decisions queued: retract `tr-65e723dd` and `tr-50764deb`
   (`TRUTH_HUMAN=1`; successors already live-filed).
3. Verify successors `tr-b485d74c`/`tr-b270996f` in the next verification
   round.
4. Cold-review minors from session 1 remain unaddressed.
