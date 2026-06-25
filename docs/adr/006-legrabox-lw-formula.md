# ADR-006: LEGRABOX LW formula uses runner clearance, not side thickness

## Status

Accepted

## Context

The LEGRABOX planning sheets use "LW" (Lichte Weite / clear width) as the basis for drawer box panel formulas:

- Drawer back width = LW − 38
- Drawer base width = LW − 35

The question is how to compute LW from the cabinet dimensions. Two candidates:

- A) LW = KB − 2 × side_thickness (e.g., 800 − 36 = 764)
- B) LW = KB − 2 × 13mm runner clearance (e.g., 764 − 26 = 738)

Where KB = cabinet internal width (between inner faces of side panels).

## Decision

**LW = KB − 2 × 13mm** (formula B). The 13mm per side is the LEGRABOX runner + clearance, as stated in Blum's documentation: "LW ≈ KB − 26mm for LEGRABOX (13mm clearance per side)".

The side panel thickness is already accounted for when computing KB from the external cabinet width:

```
KB = external_width − 2 × side_thickness   (e.g., 800 − 36 = 764)
LW = KB − 2 × 13                           (e.g., 764 − 26 = 738)
```

## Verification

For KB = 764mm (800mm cabinet with 18mm sides):

- LW = 764 − 26 = 738mm
- Drawer back width = 738 − 38 = **700mm** ✓ (matches Blum planning sheet DQBQRY)
- Drawer base width = 738 − 35 = **703mm** ✓

The incorrect formula (A) would give back = 726, base = 729 — both 26mm too wide.

## Consequences

- `legrabox.lw(kb)` subtracts 26mm, not `2 × side_thickness`
- The `side_thickness` parameter is accepted but not used (kept for API compatibility)
- All drawer box panels are 26mm narrower than they would be under formula A
- Blum's official LW/KB table should be consulted for exact values (may vary by ±1mm per runner type)

## References

- Source: User's PDF analysis of Blum planning sheets DQBQRY, DQBMJY, DQBNYM
- Codified in: `src/kuchnie_core/legrabox.py::lw()`
- Verified by: `tests/test_legrabox.py::test_lw_formula`, `test_drawer_box_back_dimensions`, `test_drawer_box_base_dimensions`
