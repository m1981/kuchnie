# ADR-003: Worktop filtering as multi-step hierarchy

## Status

Accepted — 2026-07-01

## Context

Worktops ("blaty") have 4 independent dimensions that affect selection:

| Dimension | Values | Example |
|---|---|---|
| Technology | postformed, ABS edge, slim | `worktop_postformed` |
| Edge profile | U, U-U, R3 | `PF-U-600` vs `PF-UU-900` |
| Width | 600, 900, 1200, 635, 650, 1315 | `4100x600` |
| Thickness | 38mm, 12mm | implied by technology |

Fronts (chipboard, MDF) have one dimension: `material_type`. A flat pill filter works.
Worktops need a hierarchical filter — a flat pill would show 6+ confusing options with encoded labels.

### Current data (DB)

| Profile | Width | Material Type | Count |
|---|---|---|---|
| U (one edge) | 600mm | worktop_postformed | 19 |
| R3 (one edge) | 600mm | worktop_postformed | 6 |
| ABS square | 635mm | worktop_abs_edge | 12 |
| Slim | 650mm | worktop_slim | 7 |
| Black Wood | 1315mm | worktop_slim | 6 |

### Missing from DB (spec says they exist)

| Profile | Width | Material Type | Expected count |
|---|---|---|---|
| U-U (both edges) | 900mm | worktop_postformed | ~40 |
| U-U (both edges) | 1200mm | worktop_postformed | ~40 |

`sheet_formats` table has `4100x900` and `4100x1200` rows, but no variants use them.

## Decision

**Use a 3-step hierarchical filter for worktops, activated only when slot = worktop.**

```
Step 1: Technology    [Post-formed] [ABS] [Slim]
Step 2: Profile       [U] [U-U] [R3]           ← only for Post-formed
Step 3: Width         [600] [900] [1200]        ← only for U-U
```

Width and thickness are **implied** by technology — no separate filter needed.

### Why 3 steps, not flat pills

1. User decides "I want postformed" before caring about edge profile
2. Edge profile only matters for postformed (ABS and Slim have one option each)
3. Width only matters for island (U-U) worktops — wall worktops are always 600mm
4. Matches real-world decision flow: installer asks "postformed or slim?" first

### Business ID convention

```
K101-PF-U-600     Post-formed, Unicolor (one edge), 600mm
K101-PF-UU-900    Post-formed, U-U (both edges), 900mm    ← new
K101-PF-UU-1200   Post-formed, U-U (both edges), 1200mm   ← new
K101-PF-R3-600    Post-formed, R3 radius, 600mm
K093-ABS-635      ABS Square Edge, 635mm
K551-SL-12        Slim Line, 650mm
U190-BW-12        Black Wood, 1315mm
```

## Consequences

### Must do

1. Seed missing U-U variants (40 decors × 2 widths = 80 new variants)
2. Update `variant_edges` for U-U variants
3. Update frontend with 3-step filter (only when slot = worktop)
4. Update `materialOptions` computed property to exclude worktops from main pills

### Must NOT do

- Don't add width/thickness as separate filter pills (implied by technology)
- Don't show worktop tech options when filtering fronts (role-based visibility)
- Don't flatten worktop profiles into one "Blat" pill (loses critical info)

### Risks

- U-U variants not in DB yet → filter shows 0 results for U-U option
- If more worktop types added later (e.g. `worktop_fitline`), need to update Step 1 pills

## References

- `docs/materials/Kronospan/blaty_postformed_spec.md` — profile definitions
- `docs/specs/worktop-filtering.md` — UI spec (to be created)
- `sheet_formats` table — `4100x900`, `4100x1200` already exist
