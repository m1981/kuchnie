# ADR-001: Pairings are relations between decors, not variants

**Status**: Accepted
**Date**: 2026-06-26 (extracted from `02-data-model.md` on 2026-06-30)

---

## Context

A kitchen designer pairing materials thinks at the level of *visual identity*:

- "biały front na biały korpus" — pair white front with white carcass
- "dębowy front na dębowy blat" — pair oak front with oak worktop
- "ten sam dekor za kuchenką" — same decor as splashback

These statements are about **what something looks like** (decor), not about
specific purchasable formats (variant = decor × material × thickness × structure).

Pairing K8685 (Biel Alpejska) front with K110 (Biały Korpusowy) carcass is a
*design decision*. The variant chosen for the carcass (chipboard 18mm vs 16mm,
SM vs PE structure) is a *separate downstream choice*.

## Decision

`pairings` is a many-to-many relation between **decors**, not variants:

```
pairings(front_decor_id, target_decor_id, pairing_type, match_type, priority)
```

Variant selection is a second step: once the customer picks the paired decor,
they (or the configurator) pick the appropriate variant from that decor's
available variants filtered by `roles`.

## Consequences

### Positive
- One pairing rule covers all material variants of the same decor.
  Example: `K8685 → K110` works whether K8685 is delivered as chipboard 18mm
  or MDF 19mm — the pairing semantics are the same.
- The pairing table stays small. With 148 decors and ~3 pairings each,
  we have ~450 rows instead of ~1000+ if pairings were per-variant.
- Designers can author pairings without thinking about formats.

### Negative
- A pairing might be valid for one variant of a decor but not another.
  Example: K8685 in MDF Acrylic might not pair with K110 in chipboard
  for structural reasons (thickness mismatch).
  **Mitigation**: the configurator's `roles` filter + variant-level
  compatibility checks handle this at selection time.
- Cross-collection edge banding matches (variant-level by nature) live in
  a separate table: `variant_edges`.

## Pairing types

| Type | Meaning | Example |
|---|---|---|
| `carcass` | front → carcass | K8685 → K110 |
| `worktop` | front → worktop | K8685 → 868S RS |
| `splashback` | front → splashback panel | K8685 → K8685 (HPL) |
| `side_panel` | front → exposed side | K8685 → K8685 |
| `plinth` | front → plinth | K8685 → K110 |
| `hpl_laminate` | front → matching HPL | K8685 → K8685-HPL |

## Match quality

| Match | Meaning | Priority hint |
|---|---|---|
| `exact` | Same decor in different material | 1 |
| `close` | Color-family neighbor | 2 |
| `default` | Universal fallback (e.g. K110 white) | 99 |

## Example: designer picks front K8685

```sql
-- Step 1: find paired carcass decors
SELECT * FROM pairings
WHERE front_decor_id = (SELECT id FROM decors WHERE business_id = 'K8685')
  AND pairing_type = 'carcass'
ORDER BY priority;

-- Result:
-- K8685 → K8685 (exact, priority=1) "same decor as chipboard"
-- K8685 → K110  (default, priority=99) "white carcass, universal"

-- Step 2: for the chosen target decor, pick a carcass-capable variant
SELECT * FROM variants
WHERE decor_id = (SELECT id FROM decors WHERE business_id = 'K110')
  AND roles LIKE '%carcass%';
```

## Rejected alternatives

### Variant-level pairings
`pairings(front_variant_id, target_variant_id, ...)` — rejected because:
- Explodes row count by ~10× (148 decors × ~10 variants each).
- Forces designers to author pairings per format.
- Doesn't match how the domain experts (cabinet makers) actually think.

### Wildcard pairings (`front: "*"`)
Considered for "K110 pairs with everything as default." Rejected because:
- SQL doesn't naturally support `*` semantics — would need application-layer
  fallback logic.
- Confuses the data model: every other row is explicit, then `*` is special.
- Easier to seed explicit rows for all decors via a script:
  ```python
  for decor in all_fronts:
      add_pairing(decor, K110, type='carcass', match='default', priority=99)
  ```

## See also

- `db/schema.sql` — `pairings` table definition (lines 200–215)
- `docs/03-configurator-design.md` — how pairings drive the configurator flow
