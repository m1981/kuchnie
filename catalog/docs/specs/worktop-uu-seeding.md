# Spec: Seed U-U (island) worktop variants

## Problem

Kronospan Global Collection 2026 offers postformed worktops in 3 profiles:
- **U** (one edge finished) — 600mm wide → 19 variants in DB ✓
- **U-U** (both edges finished) — 900mm, 1200mm wide → **0 variants in DB** ✗
- **R3** (R3 radius, one edge) — 600mm wide → 6 variants in DB ✓

The manufacturer table (`blaty-postformed-spec.md`, str. 48) lists U-U ("Profil 2U")
availability at 900mm and 1200mm for all 40 rows of the Global Collection 2026
postformed table. The DB, however, models only 19 decors as `PF-U-600` variants —
and this spec's own derivation ("for each decor that has a `PF-U-600` variant")
keys off those. See **Resolution (2026-07-27)** below: the seeded scope is
**18 decors × 2 widths = 36 variants**.

## Resolution (2026-07-27)

The original prose ("~80 new variants") contradicted the spec's own SQL, which
derives U-U variants FROM existing `%-PF-U-600` variants (19 in the DB). Domain
review against the manufacturer sources resolved the discrepancy as follows:

1. **Scope = 18 decors, 36 variants.** U-U availability is documented per decor
   in the "Profil 2U (900mm)" / "Profil 2U (1200mm)" columns of the Global
   Collection 2026 postformed table
   (`catalog/docs/materials/Kronospan/blaty-postformed-spec.md`, section 5.1,
   from blaty.pdf str. 48). Of the 19 decors with a `PF-U-600` variant in the DB,
   18 appear in that table; decor **0190 (Czarny)** does not (it entered the DB
   as a legacy worktop pairing for K190 fronts, `global-collection-decory.yaml`),
   so it has no documented 2U offer and is excluded. Seeding the remaining
   21 table decors (K091, K092, 5527, K002, K003, K013, K016, K023, K028, K029,
   K030, K095, K203, K204, K206, K212, K215, K367, K368, K369, 2738) first
   requires their `PF-U-600` variants — out of scope here; note K023 appears
   twice in the table (structures SU and SQ), which the current
   `{decor}-PF-UU-{width}` business-id scheme cannot distinguish.
2. **Edge source = manufacturer's "Obrzeże HPL" column.** The DB's `PF-U-600`
   variants carried **no** `variant_edges` rows, so "copy the U variant's edge"
   had nothing to copy. The postformed table lists an HPL edge roll
   (42 × 4110 mm, w krążku) for its full decor list, with edge code identical
   to the decor code. The seeder (`catalog/scripts/seed_worktop_uu.py`)
   materialises that edge, links it to the source `PF-U-600` variant, then
   copies the link to both U-U variants.
3. **"Both edges finished" representation.** `variant_edges` has no
   per-edge-position column (`UNIQUE(variant_id, edge_id)`), so one
   variant→edge link per U-U variant is the correct representation; the
   both-long-edges-postformed fact is carried by `worktop_profiles` code
   `U-U` (`profiled_sides = 'front,back'`).
4. **Known gaps (tracked, out of this seeding's scope).** Ten of the 18
   seeded decors inherit structure code RS from `kronospan_full.yaml`
   where the manufacturer table says UE (4298, 4299), PE (K210),
   GG (K217, K218) or PN (K698, K699, K703, K704, K705) — upstream data
   fix tracked as `wk-4fc28a19`. And the 36 U-U variants are not yet
   represented in `worktop_specs` (the profile bridge feeding
   `v_worktops_full`), so the worktops endpoint hides them while the
   configurator role fallback offers them — tracked as `wk-bca0a74b`.

## What to seed

### New variants

For each decor that has a `PF-U-600` variant AND appears in the Global
Collection 2026 postformed table (18 decors — see Resolution), create two new
variants:

| Pattern | Format | Profile | Example |
|---|---|---|---|
| `{code}-PF-UU-900` | 4100×900 | U-U (both edges) | `K201-PF-UU-900` |
| `{code}-PF-UU-1200` | 4100×1200 | U-U (both edges) | `K201-PF-UU-1200` |

### Source decors (from `blaty-postformed-spec.md`)

All 40 rows of the Global Collection 2026 postformed table are offered in U-U
format by the manufacturer:
- 7045, 868S, K091, K092, K203, K204, K206, K212, K215
- 4298, 4299, 5527, K002, K003, K013, K016, K023, K028, K029, K030, K095
- K201, K205, K207, K209, K210, K213, K214, K367, K368, K369
- K023 (SQ), K217, K218, 2738, K698, K699, K703, K704, K705

Of these, the 18 with an existing `PF-U-600` variant are seeded now:
7045, 868S, 4298, 4299, K201, K205, K207, K209, K210, K213, K214, K217, K218,
K698, K699, K703, K704, K705.

### Edge banding for U-U

U-U worktops have **both front and back edges** finished with post-formed profile.
Same edge code as the U variant for that decor, applied to both edges. Since the
`PF-U-600` variants carried no edges in the DB, the seeder first establishes the
U variant's edge from the manufacturer's "Obrzeże HPL" column (HPL roll
42 × 4110 mm, edge code = decor code), then copies it to the U-U variants.

### Database changes

Implemented by the idempotent seeder `catalog/scripts/seed_worktop_uu.py`
(intent sketched below; the seeder additionally restricts to the 18 table
decors and establishes the U-variant HPL edges first).

```sql
-- New variants (36 rows: 18 decors × 2 widths)
INSERT INTO variants (business_id, decor_id, material_id, structure_id, 
                      sheet_format_id, roles, thickness_mm)
SELECT 
  d.business_id || '-PF-UU-900',
  d.id,
  m.id,  -- kronospan-postformed-global
  v.structure_id,
  (SELECT id FROM sheet_formats WHERE slug = '4100x900'),
  '["worktop"]',
  38.0
FROM decors d
JOIN variants v ON v.decor_id = d.id AND v.business_id LIKE '%-PF-U-600'
JOIN materials m ON m.slug = 'kronospan-postformed-global'
WHERE d.producer_id = (SELECT id FROM producers WHERE slug = 'kronospan');

-- Same for 1200mm width
-- (repeat with '-PF-UU-1200' and '4100x1200')
```

### Edge banding

```sql
-- Copy edge from U variant to U-U variant
INSERT INTO variant_edges (variant_id, edge_id)
SELECT 
  (SELECT id FROM variants WHERE business_id = 
    REPLACE(ve_old.business_id, '-PF-U-', '-PF-UU-')),
  ve_old.edge_id
FROM variant_edges ve_old
JOIN variants v ON ve_old.variant_id = v.id
WHERE v.business_id LIKE '%-PF-U-600';
```

## Verification

```sql
-- Should return 36 new variants
SELECT COUNT(*) FROM variants WHERE business_id LIKE '%-PF-UU-%';

-- Each seeded decor should have 3 postformed variants (U, UU-900, UU-1200);
-- expected output: only 0190 (excluded from U-U — see Resolution).
-- The NOT LIKE filter matters: R3-only decors (D3025, D3823, D4225,
-- D60664, D70601, K101) each carry a single PF-R3-600 variant and would
-- otherwise flood this check.
SELECT d.business_id, COUNT(v.id) as variant_count
FROM decors d
JOIN variants v ON v.decor_id = d.id
WHERE v.business_id LIKE '%-PF-%'
  AND v.business_id NOT LIKE '%-PF-R3-%'
GROUP BY d.business_id
HAVING variant_count < 3;
```

## Test cases / Success criteria

Tests: `catalog/tests/test_worktop_uu_seeding.py` (fixture-built DB from
`kronospan_full.yaml`; seeder run twice to prove idempotency).

- [x] [SC-wtuu-001] `test_uu_variant_count` — 36 U-U variants across 18 decors; 0190 excluded
- [x] [SC-wtuu-002] `test_uu_format_900` — 18 `*-PF-UU-900` variants, sheet format 4100×900
- [x] [SC-wtuu-003] `test_uu_format_1200` — 18 `*-PF-UU-1200` variants, sheet format 4100×1200
- [x] [SC-wtuu-004] `test_uu_thickness_38` — U-U variants are 38.0mm thick
- [x] [SC-wtuu-005] `test_uu_edge_banding` — U-U edge codes equal the source U variant's (HPL roll, code = decor code); U-U profile is `front,back`
- [x] [SC-wtuu-006] `test_uu_roles_worktop` — roles = `["worktop"]`
- [x] [SC-wtuu-007] `test_uu_business_id_pattern` — business ids match `{decor}-PF-UU-{900|1200}` (e.g. `K201-PF-UU-900`)

## Status
- [x] Spec written
- [x] Implementation
- [x] Verify
- [x] Docs
- [x] Changelog

Acceptance oracle: `wk-25d33212` (ADR-014 `--accept-cmd` runs the wtuu
pytest suite at that item's close).
