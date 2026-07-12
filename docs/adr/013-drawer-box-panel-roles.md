# ADR-013: Drawer-box panels get their own `PanelRole` values

## Status

Accepted 2026-07-12. Amends ADR-012 §1 (the `PanelRole` vocabulary) —
executed together with this ADR (wk-c9e848a3, premise tr-6d3edb9e).

## Context

ADR-012 §1 froze the `PanelRole` vocabulary at nine carcass/front values
and deliberately left non-carcass panels at `role=None` ("intermediate
parts, not carcass roles"). That decision had an unpriced consequence:
`kitchen-erp`'s `quantities_from_decomposition` buckets panels by role
with a `role=None` fallthrough into `corpus_m2` / `corpus_edge_lm`. The
drawer-box back and base emitted by `legrabox.py` and
`blum_drawers.DrawerSystem.decompose_drawer_box` therefore landed in
the corpus position — drawer-box board (often a different, cheaper
board than the decor carcass) was quantified and priced as corpus board
(tr-6d3edb9e).

## Decision

Extend the `PanelRole` enum with two values:

```python
DRAWER_BACK = "drawer_back"
DRAWER_BASE = "drawer_base"
```

- Emitted by both drawer-box decomposers (`legrabox.decompose_drawer_box`
  and `blum_drawers.DrawerSystem.decompose_drawer_box`). `catalog.py`
  carcass decomposers are unaffected — they never produce box panels.
- `kitchen-erp` `DomainQuantities` grows `drawer_box_m2`; the fold routes
  the two roles there, and `BOMGenerator` prices it as its own BOM
  position (at the corpus board rate until `ProjectDefaults` grows a
  dedicated drawer-box material — an open follow-up).
- The frozen-vocabulary test
  (`kuchnie-core/tests/test_panel_role.py::test_expected_members`) is
  updated in the same change, per its own "new roles = new ADR + new
  test entry" contract.

## Consequences

**Positive**

- Drawer-box board is visible and repriceable in the BOM instead of
  silently inflating the corpus position.
- Downstream CAM can now filter box parts by role instead of matching
  on `"_drawer_"` id substrings.

**Negative / neutral**

- Any future exhaustive `match` over `PanelRole` gains two arms (none
  exist today — verified before landing).
- `role=None` still exists as a legacy default for direct `Panel()`
  construction; the fallthrough-to-corpus behaviour for unknown roles
  is retained deliberately.

## Alternatives considered

**13a. Keep `role=None` and bucket by id substring (`"_drawer_"`).**
Rejected — string matching on ids is the exact anti-pattern ADR-012
introduced roles to eliminate.

**13b. Single `DRAWER_BOX` role for both parts.**
Rejected — back and base can differ in material/thickness (16 mm board
back vs HDF base is a common spec, ADR-007); one role would re-merge
what pricing may need split.

## References

- ADR-012 §1: the `PanelRole` vocabulary this ADR extends.
- ADR-007: drawer-box material spec (why back/base materials differ).
- ADR-001: Panel is the atomic unit — roles are decoration on that atom.
- Ledger: tr-6d3edb9e (defect fact), wk-c9e848a3 (the work).
