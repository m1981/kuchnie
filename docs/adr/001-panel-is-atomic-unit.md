# ADR-001: Panel is the atomic manufacturing unit

## Status

Accepted

## Context

A kitchen consists of cabinets, but CNC machines don't cut "cabinets" — they cut individual panels, drill holes in them, and apply edge banding. We need to decide what the fundamental unit of manufacturing data is.

Candidates:

- A) The cabinet (decompose later, at export time)
- B) The panel (decompose early, at design time)

## Decision

**The panel is the atomic manufacturing unit.** Cabinets are organizational. Everything above panels (rows, kitchens) is grouping. Everything on panels (edges, machining ops) is decoration on that physical piece.

```
Kitchen → Row → Cabinet → Panel → EdgeBand / MachiningOp
                                ↑
                          THIS is the atom
```

## Consequences

- `Panel` is a first-class dataclass with dimensions, material, edges, and machining ops
- The decomposer produces `list[Panel]` from a `CabinetInstance`
- Cut lists, BOMs, and DXF exports all operate on panels, not cabinets
- Edge banding and machining ops are stored ON the panel, not as separate structures
- A `DecompositionResult` contains panels + accessories (purchased hardware)

## References

- Codified in: `src/kuchnie_core/model.py::Panel`
- Verified by: `tests/test_K01_decomposition.py`, `tests/test_G01_decomposition.py`
