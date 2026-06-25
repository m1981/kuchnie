# ADR-005: Machining operations are first-class objects on panels

## Status

Accepted

## Context

Panels need more than just dimensions — they need drilling patterns, grooves, rabbets, and dados. These machining operations must be tracked for:

- DXF export (CNC company needs hole positions)
- Cost estimation (machining adds time/cost)
- Render accuracy (visual details like shelf pin holes)

Two approaches:

- A) Separate machining file per panel (external reference)
- B) Machining ops stored ON the panel as a list

## Decision

**MachiningOp is a dataclass stored directly on Panel.machining_ops.**

```python
@dataclass
class MachiningOp:
    type: str           # "drill", "groove", "rabbet", "dado"
    x_mm: float = 0     # from left edge of panel
    y_mm: float = 0     # from bottom/front edge of panel
    diameter_mm: float = 0
    depth_mm: float = 0  # 0 = through hole
    width_mm: float = 0  # for groove/rabbet
    length_mm: float = 0 # for groove
    note: str = ""       # human-readable source description
```

Coordinate system: panel lying flat, viewed from the machined face. x = left-to-right, y = bottom-to-top.

## Consequences

- Each panel carries its own machining ops — no external files to manage
- The decomposer adds ops during decomposition (e.g., runner screws go on side panels)
- DXF export reads `panel.machining_ops` directly
- Ops are serialized with the panel (intermediate format, JSON round-trip)
- Multiple ops per panel are supported (e.g., 8 runner screws per side panel)

## First use case: LEGRABOX runner mounting

Each drawer generates 4 drill ops on each carcass side panel (runner screws at Blum-defined positions). A cabinet with 2 drawers gets 8 drill ops per side panel.

## References

- Codified in: `src/kuchnie_core/model.py::MachiningOp`
- First consumer: `src/kuchnie_core/legrabox.py::decompose_drawer_box()`
- Verified by: `tests/test_legrabox.py::test_K02_has_machining_ops`
