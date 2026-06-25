# ADR-002: Construction method is a first-class entity, separate from cabinet instance

## Status

Accepted

## Context

When decomposing a cabinet into panels, we need rules: how thick are the sides, how is the back panel set (groove or nailed), what formula gives the shelf width. Two approaches:

- A) Embed rules in each cabinet instance (concrete dimensions per piece)
- B) Separate rules into a reusable "construction method" that derives panels from config

This pattern comes from Polyboard, where Construction Method is a first-class object reusable across many cabinet types.

## Decision

**Construction rules live in the catalog, not in the cabinet instance.**

```
CabinetInstance          ConstructionMethod (catalog)
──────────────           ──────────────────────────
type: "dolna_legrabox"   panels: [side, bottom, back, ...]
width: 800               side.height = cab.height - plinth
height: 720              bottom.width = cab.width - 2 × side_thickness
depth: 510               back.width = cab.width - 2×18 + 2×groove
drawers: [...]           ...
```

The `CabinetInstance` carries configuration (dimensions, materials, drawer list). The catalog function (`decompose_dolna_legrabox`) carries the rules. The `decomposer.py` connects them.

## Consequences

- Adding a new cabinet type = writing one `decompose_<type>` function + one test
- Changing construction rules (e.g., groove depth) = editing one catalog function
- Cabinet instances are simple data (easy to serialize, easy to validate)
- The same instance can theoretically be decomposed with different methods (future: compare construction approaches)

## Alternatives considered

- **Embedded rules**: Each cabinet stores its own panel dimensions. Simple but makes bulk changes impossible and serialization bloated.
- **Declarative formulas as data**: Store formulas as strings/expressions. More flexible but harder to debug. Rejected for V1 — lambdas in Python are sufficient.

## References

- Pattern source: Polyboard (Compusoft)
- Codified in: `src/kuchnie_core/catalog.py`
- Verified by: all decomposition tests
