# ADR-014: Corner-blind front parts get their own `PanelRole` values

## Status

Accepted 2026-07-12. Amends ADR-012 §1 (the `PanelRole` vocabulary) —
executed together with this ADR (wk-31467921, premise tr-b2e3dbff).

## Context

The blind base corner cabinet (dolna narożna ślepa) introduces two front
parts that existed in no prior decomposer:

- the **blind front** (zaślepka) — a fixed panel of front material closing
  the zone hidden behind the perpendicular run;
- the **filler** (listwa maskująca) — the 50–100 mm strip at the internal
  corner mandated by the L-kitchen playbook (phase 3: without it, handles
  and perpendicular fronts collide).

Neither fits the existing vocabulary. `FRONT_DOOR` is wrong for both:
downstream CAM applies hinge-cup and handle drilling to `FRONT_DOOR`
panels, and both parts are FIXED — a hinge cup in a zaślepka is scrap.
`role=None` is wrong too: kitchen-erp's fold buckets `None` into
`corpus_m2`, pricing decor front board at the corpus rate (the exact
disease ADR-013 cured for drawer boxes).

## Decision

Extend the `PanelRole` enum with two values:

```python
FRONT_BLIND = "front_blind"   # fixed blind front (zaślepka) at a corner
FILLER      = "filler"        # listwa maskująca at the internal corner
```

- Emitted by `decompose_dolna_narozna_slepa` (and future corner/gable
  decomposers needing fixed decor parts).
- `kitchen-erp` `_FRONT_ROLES` gains both values: they are cut from front
  material and price as front board; being fixed, they must still never
  receive hinge or handle machining — CAM filters on `FRONT_DOOR` /
  `FRONT_DRAWER` exactly as before and is unaffected.
- The frozen-vocabulary test
  (`kuchnie-core/tests/test_panel_role.py::test_expected_members`) is
  updated in the same change, per its own "new roles = new ADR + new
  test entry" contract.

## Consequences

**Positive**

- Corner-blind fronts price correctly as front board in the BOM.
- CAM can never confuse a fixed blende with an openable door — the role
  is the discriminator, not the panel name.

**Negative / neutral**

- Any future exhaustive `match` over `PanelRole` gains two arms (none
  exist today — same verification as ADR-013).
- `FILLER` is corner-scoped today; if freestanding wall fillers appear
  later they reuse the same role.

## Alternatives considered

- **Reuse `FRONT_DOOR` with a `fixed` flag on `Panel`** — rejected: adds a
  field every other panel ignores, and role-based CAM filtering (ADR-012's
  point) would need to consult two fields.
- **`role=None` + name matching** — rejected: reintroduces the string
  matching ADR-012 §1 exists to eliminate, and misprices front board as
  corpus.
