# Spec: Seed U-U (island) worktop variants

## Problem

Kronospan Global Collection 2026 offers postformed worktops in 3 profiles:
- **U** (one edge finished) — 600mm wide → 19 variants in DB ✓
- **U-U** (both edges finished) — 900mm, 1200mm wide → **0 variants in DB** ✗
- **R3** (R3 radius, one edge) — 600mm wide → 6 variants in DB ✓

The spec (`blaty_postformed_spec.md`) says all 40 decors are available in U-U format.
This means we're missing ~80 variants (40 decors × 2 widths).

## What to seed

### New variants

For each decor that has a `PF-U-600` variant, create two new variants:

| Pattern | Format | Profile | Example |
|---|---|---|---|
| `{code}-PF-UU-900` | 4100×900 | U-U (both edges) | `K101-PF-UU-900` |
| `{code}-PF-UU-1200` | 4100×1200 | U-U (both edges) | `K101-PF-UU-1200` |

### Source decors (from `blaty_postformed_spec.md`)

All 40 decors from Global Collection 2026 are available in U-U format:
- 7045, 868S, K091, K092, K203, K204, K206, K212, K215
- 4298, 4299, 5527, K002, K003, K013, K016, K023, K028, K029, K030, K095
- K201, K205, K207, K209, K210, K213, K214, K367, K368, K369
- K023 (SQ), K217, K218, 2738, K698, K699, K703, K704, K705

### Edge banding for U-U

U-U worktops have **both front and back edges** finished with post-formed profile.
Same edge code as the U variant for that decor, but applied to both edges.

### Database changes

```sql
-- New variants (80 rows)
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
-- Should return 80 new variants
SELECT COUNT(*) FROM variants WHERE business_id LIKE '%-PF-UU-%';

-- Each decor should have 3 postformed variants (U, UU-900, UU-1200)
SELECT d.business_id, COUNT(v.id) as variant_count
FROM decors d
JOIN variants v ON v.decor_id = d.id
WHERE v.business_id LIKE '%-PF-%'
GROUP BY d.business_id
HAVING variant_count < 3;
```

## Test cases

```
test_uu_variant_count          -- 80 new variants
test_uu_format_900             -- all 4100x900
test_uu_format_1200            -- all 4100x1200
test_uu_thickness_38           -- all 38mm
test_uu_edge_banding           -- both edges have edge code
test_uu_roles_worktop          -- roles = ["worktop"]
test_uu_business_id_pattern    -- matches K101-PF-UU-900
```

## Status
- [x] Spec written
- [ ] Implementation
- [ ] Verify
- [ ] Docs
- [ ] Changelog
