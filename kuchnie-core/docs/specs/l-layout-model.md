# Spec: kuchnie-core L-layout model — minimal runs + corner + positions

> Reader: whoever gives the live domain legs, a corner and positions — or
> reviews that work | Enables: building the minimal value objects against the
> validator's existing geometry-manifest contract instead of inventing a
> second geometry language | Update-trigger: the manifest contract in
> `validator.py` changes, a gate demands data the model refuses to carry, or
> ADR-034 is superseded

Serves: UC-11 phases 2–4 (zones, corner, base-run composition need leg
positions and the corner), unblocking UC-11 step 9's parked gates
progressively.

## Intent

`Kitchen` is a flat list of `Row`s: no position, no direction, no corner, no
leg adjacency — which is why gates G2/G3/G4/G5/G7 sit SKIPPED and the
playbook's Phases 2–5 have no data model. Meanwhile
`kuchnie_core.validator` already validates a geometry manifest (runs with
`start/end_position_mm`, `direction`, `turn`) that nothing produces. This
spec closes that hole from the model side: minimal value objects — a
value-object's worth of code, not a CAD kernel — whose output is exactly the
manifest the validator already checks. It is NOT an editor and NOT the
adapter: hb5 edits (ADR-009, `docs/adr/009-*.md`), adapter r4 produces
(`home-builder-adapter/docs/specs/adapter-position-extraction.md`), this
model carries.

**Non-goals**: no room/wall/door/window entities; no traffic-path or
walkway geometry (G5 stays a human checklist per ADR-035); no layout
engine, placement logic or auto-fill; no I/O beyond (de)serialization the
model already does; no U-shape work now (the manifest language admits it;
this spec does not implement it).

### Bounded context & ubiquitous language

| Term | Meaning |
|---|---|
| `Run` | one straight stretch of cabinets along one wall — the existing `Row`, now aware of where it starts, ends and points |
| `Leg` | a Run's role in an L-kitchen: one of the two stretches meeting at the corner |
| `Corner link` | the record that two Runs meet: which Runs, the turn direction, and the corner cabinet + filler widths consumed on BOTH legs |
| `Position` | a point in kitchen-plan coordinates, millimetres, as the validator's `*_position_mm` pairs |
| `Geometry manifest` | the dict contract `validate_manifest`/`check_run_continuity` already accept — the model's output language |

### Invariants

1. The corner consumes width from BOTH legs — violated by: a second leg
   whose usable width equals its wall width even though a 1050 corner-blind
   plus filler sits at its start.
2. Runs chain: a Run's end position equals the next Run's start position
   within the validator's 1 mm tolerance — violated by: leg B starting
   600 mm off leg A's end (check `run_continuity` fires).
3. Direction after a turn follows the validator's TURNS mapping — violated
   by: `east` + `left` declared as `north` (check `direction` fires).
4. Flat-Kitchen back-compat: a Kitchen whose Rows carry no positions loads,
   validates and decomposes exactly as today — violated by: loader raising
   on a legacy JSON without `start_position_mm`.
5. One corner link references existing Runs — violated by: a corner naming
   a Run id absent from the Kitchen.

### Entity / value-object model

Additive fields, plain dataclasses (ADR-012 discipline — English fields,
`_mm` suffixes, no new deps):

- `Run` (extends `Row`): `start_position_mm`, `end_position_mm`,
  `direction` (`east|north|west|south`), optional `turn` (`left|right`,
  set on the Run after the corner), optional corner participation.
- `CornerLink` (new value object): the two Run ids, corner cabinet id,
  strategy placeholder (blind today — the full strategy object is the
  Stage-2 corner-strategy spec), filler width per leg, consumed width per
  leg.
- `Kitchen`: gains `legs`/`corner` adjacency (ordered Run ids + the
  CornerLink); flat `rows` list stays the storage shape.

Derived, not stored: `Run.usable_width_mm()` (wall width minus corner
consumption), `Kitchen.geometry_manifest()`.

### Operation contracts

| Operation | Precondition | Postcondition | Invariant upheld |
|---|---|---|---|
| `Kitchen.geometry_manifest()` | Runs carry positions + directions | returned dict passes `validate_manifest` with issue count 0 for a well-formed L | 2, 3 |
| `Run.usable_width_mm()` | corner link resolved | wall width minus this leg's corner consumption + filler | 1 |
| `CornerLink` construction | both Run ids exist in the Kitchen | consumed widths recorded per leg | 1, 5 |
| legacy `Kitchen` load | JSON without positions | model identical to today's; validators skip position checks | 4 |

### Extension points

New shapes (U, galley) are more Runs + more corner links in the same
manifest language — the list-of-runs shape is the extension point, not a
subclass. The corner strategy enum grows in the Stage-2 corner-strategy
spec, which owns blind/diagonal/dead semantics; this model reserves the
field. New per-Run data (zone tags, appliance markers) lands as additive
optional fields per ADR-012's back-compat rule.

### Traceability

Invariants 1–3 encode playbook §3 (corner before widths; corner consumes
both legs) and the validator's tested contract; invariant 4 is ADR-034's
back-compat clause; the build-vs-resurrect boundary is ADR-034 wholesale.

## Decisions

- `docs/adr/034-l-layout-model-rebuilt-minimal-in-core.md` — rebuild
  minimal in core against the existing validator manifest contract; the
  retired plugin-era bytecode is never resurrected.
- `docs/adr/012-kuchnie-core-model-extensions.md` — the additive-dataclass
  discipline this extension follows.
- `docs/adr/009-*.md` — hb5 stays the editor; this model never becomes one.
- `docs/adr/035-playbook-operating-decisions.md` — G5 stays human; the
  model carries plan-sheet data, not triangle math.

## Ground truths

- tr-167da3d5 — `validate_manifest`/`print_validation_report` run
  end-to-end on the reference manifests (the contract this model targets
  is alive and executable).
- tr-23661434 — `validate_rows` encodes G1/G6 with G2/G3/G4/G5/G7 parked
  pending model support (the consumer waiting on this model).
- tr-65aa5969 — `evaluate_buildability` reports the parked gates as
  explicitly SKIPPED with reasons (the SKIP slots this model unparks).
- tr-591aa208 — corner-blind decomposer ships filler + blind front (the
  production side the CornerLink connects to a scene).

## Work

- wk-29bb6401 — L-layout model: Run positions/direction + CornerLink + Kitchen leg adjacency emitting the validator's geometry manifest, flat loads back-compatible (Stage 1 keystone, review §C)

## Acceptance

Pre-written `done --claim` texts, scoped to evidence commands:

- "kuchnie_core Run carries start/end position, direction and corner
  participation, Kitchen carries leg adjacency with a CornerLink recording
  filler and consumed width per leg, and Kitchen.geometry_manifest() for a
  hand-computed two-leg L passes validate_manifest with an empty issue
  list; pinned by kuchnie-core/tests/test_l_layout_model.py" (`wk-29bb6401`)
- "a legacy flat-Kitchen JSON without positions still loads and validates
  with unchanged results, covered by a back-compat test in
  kuchnie-core/tests/test_l_layout_model.py" (`wk-29bb6401`)

## Verification & Validation

Verification: hand-computed L-geometry test suite (Meyer-contract style,
like ConstructionMethod's) — one contract assertion per row of the
Operation contracts table, including the seeded-violation cases for
invariants 1–3 — oracle carried by `wk-29bb6401` (`--accept-cmd`);
intended accept command:
`.venv/bin/python -m pytest kuchnie-core/tests/test_l_layout_model.py -q`.
SC wiring at implementation (SC- markers + .sc.txt when the tests exist,
per the wtuu precedent).

### Success criteria

The markers below are mirrored in
`kuchnie-core/docs/specs/l-layout-model.sc.txt` and cited in
`kuchnie-core/tests/test_l_layout_model.py` docstrings; slug `llay` is
registered in `docs/specs/sc-slugs.txt`.

- [x] [SC-llay-001] `Run` extends the existing `Row` with additive
  optional layout fields (`start_position_mm`, `end_position_mm`,
  `direction`, `turn`, corner participation) defaulting to `None`; a
  Row built without them keeps its pre-spec behaviour
- [x] [SC-llay-002] `Kitchen.geometry_manifest()` for the hand-computed
  two-leg L passes `validate_manifest` with issue count 0, speaks the
  validator's run-entry keys, and survives the dict round-trip with
  legs, corner and per-run layout fields intact
- [x] [SC-llay-003] `Run.usable_width_mm(corner)` returns wall width
  minus the leg's consumed + filler widths on BOTH legs (3000 → 1900,
  2400 → 1790); read without the corner it exposes the invariant-1
  violation shape (2400 ≠ 1790, detectably)
- [x] [SC-llay-004] `CornerLink.for_kitchen` records filler and
  consumed width per leg and refuses a Run id absent from the Kitchen
  (`ValueError` naming the id)
- [x] [SC-llay-005] a leg-B start seeded 600 mm off leg A's end makes
  `check_run_continuity` fire the `run_continuity` error
- [x] [SC-llay-006] `east` + `left` declared as `north` fires the
  `direction` error against the validator's TURNS table
- [x] [SC-llay-007] the model's duplicated TURNS table pins the
  validator's current degenerate mapping (left and right agreeing per
  from-direction) — the rewrite target when wk-075803aa lands
- [x] [SC-llay-008] the legacy flat fixture `kitchen_01.yaml` loads
  with layout fields at `None`, validates via
  `row_findings`/`validate_rows` as before, and serializes to the
  pre-spec key set (unset layout keys omitted)

Validation: domain-language walkthrough of the model against project P1's
real L-kitchen (do Run/Leg/CornerLink say what the fitter and the playbook
mean) — attestation pending; when the operator files it (UNVERIFIED,
`--ttl-days`), edit this line to cite the id.

Residual (accepted, not closable): "wrong abstraction — revealed by the
first U-kitchen or island commission, not by an L test suite"
