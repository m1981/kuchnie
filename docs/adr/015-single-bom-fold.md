# ADR-015: `calculate_bom` is the single geometry→quantity fold

## Status

Accepted 2026-07-17. Extends ADR-011 phase 2 (kitchen-erp consumes
kuchnie_core as the domain hub) — executed with wk-64266e86, premise
tr-847d40f8.

## Context

Three parallel folds computed quantity (and partly cost) over the same
`DecompositionResult`:

1. `kuchnie_core.bom.calculate_bom` — per-panel itemized BOM, costed
   from price dicts; feeds `kitchen_bom` in the hub.
2. `kitchen_erp.core.domain_adapter.quantities_from_decomposition` —
   its own panel walk into m²/lm buckets that `BOMGenerator` prices.
3. `kitchen_erp.core.variant_derivation._bom_lines` — a third walk:
   buckets via (2) plus its own per-band edging and accessory loops.

The area and edging arithmetic was duplicated three times. The numbers
agreed only because the math was still trivial; any refinement landing
in one fold (waste factors, offcut rules, banding allowances) would
silently diverge the others — and quoting/offer calibration would learn
against differing numbers (tr-847d40f8). One divergence was already
observable: `_bom_lines` lumped a per-cabinet front override's m² into
the variant decor's board line, overstating the decor order and hiding
the override material from purchasing.

## Decision

`kuchnie_core.bom.calculate_bom` is the ONE place decomposition geometry
becomes quantities. Its `BOMItem` carries two fields for downstream
aggregation:

- `role: PanelRole | None` — the parent panel's role (edge-band items
  inherit it; accessories carry `None`);
- `measure: float` — the trade quantity: m² for panels, lm for edge
  bands, szt for accessories.

Everything downstream is a *view* over those items:

- `quantities_from_decomposition` buckets `measure` by `role_bucket(role)`
  (corpus | front | back | box) and contains no panel arithmetic;
- `_bom_lines` groups board by (bucket, actual panel material), edging
  by band material, and passes accessories through verbatim;
- `BOMGenerator` inherits the fold through the bucket view unchanged.

Pricing stays where ADR-011 put it: `BOMGenerator` keeps its ERP-only
lines (recipe-formula fallback for non-carcass modules, CNC service
positions, rules-engine hardware, plinth). Those are additions on top of
the fold, not competing folds of the same geometry.

## Consequences

- Quantity refinements land once, in `calculate_bom`, and every
  consumer — hub `kitchen_bom`, ERP cost trace, variant purchasing
  lines — moves together.
- Behavior fix, pinned by test: a per-cabinet front override now prices
  under its own decor line in variant BOM output instead of inflating
  the variant decor's quantity
  (`test_override_front_board_prices_under_its_own_decor`).
- Drift is guarded structurally: `test_adr015_single_bom_fold.py`
  asserts the view functions reference `calculate_bom` and contain no
  geometry arithmetic (`width_mm`, `banded_edges`, unit divisions).
- Remaining known seam, out of scope here: hardware comes from two
  sources — the rules engine (BOMGenerator, tag-driven) and decomposer
  accessories (variant lines). That is a hardware-source consolidation,
  not a geometry fold, and is tracked as its own issue.
