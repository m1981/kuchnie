# ADR-007: LEGRABOX drawer box panels are 16mm chipboard

## Status

Accepted

## Context

The LEGRABOX drawer box consists of two board-cut panels:

- **Panel A (base/bottom)** — the floor of the drawer
- **Panel B (back/rear wall)** — the back panel connecting the two metal sides

The Blum planning sheet title says "Cutting – 16mm chipboard", implying both panels should be 16mm. However, during implementation, incorrect defaults were used:

- Initial default for base: 3mm HDF (confused with carcass back panel)
- Initial default for back: 12mm chipboard (arbitrary guess)

## Decision

**Both drawer box panels (A and B) are 16mm chipboard**, per Blum's specification.

| Panel    | Material  | Thickness | Source                           |
| -------- | --------- | --------- | -------------------------------- |
| A (base) | chipboard | **16mm**  | Blum: "Cutting – 16mm chipboard" |
| B (back) | chipboard | **16mm**  | Blum: "Cutting – 16mm chipboard" |

## Consequences

- `legrabox.decompose_drawer_box()` defaults: `base_thickness=16`, `back_thickness=16`
- Both panels use material code `"plyta_16mm"` by default
- The 3mm HDF is only used for the carcass back panel (`plecy`), not the drawer box
- If a user wants non-standard material (e.g., thinner back), they override via function parameters

## Alternatives considered

- **12mm for back**: Some cabinetmakers use thinner material for drawer backs. Rejected as default: Blum spec is 16mm, and thinner backs may not seat correctly in the LEGRABOX profile.
- **3mm HDF for base**: Far too thin. The drawer base sits in a groove in the metal sides and carries load. Rejected.

## References

- Source: Blum planning sheets (LEGRABOX, "Cutting – 16mm chipboard")
- Codified in: `src/kuchnie_core/legrabox.py::decompose_drawer_box()` default parameters
- Verified by: `tests/test_legrabox.py::test_drawer_box_back_dimensions`, `test_drawer_box_base_dimensions`
