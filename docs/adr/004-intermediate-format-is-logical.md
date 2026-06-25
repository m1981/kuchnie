# ADR-004: Intermediate format contains logical config, not physical panels

## Status

Accepted

## Context

The intermediate format is the JSON file that flows between kitchen-plugin, render-service, and kitchen-cli. It could contain:

- A) **Logical description**: rows + cabinet instances + materials + config
- B) **Physical description**: pre-decomposed panels with dimensions and edge banding

## Decision

**The intermediate format is the logical description (option A).** It contains rows, cabinet instances, materials, and global config — but NOT panels.

Both the render backend and the CLI import `kuchnie-core` and decompose independently. The intermediate format is the input to decomposition, not the output.

```
kitchen-plugin
    │
    ▼
intermediate.json (logical: rows + cabinets + config)
    │
    ├──► render-service: imports kuchnie_core, decomposes → Blender scene
    └──► kitchen-cli:    imports kuchnie_core, decomposes → cut list CSV
```

## Consequences

- The intermediate format is compact (cabinet config, not thousands of panels)
- Both consumers use the same decomposer (consistency guaranteed by shared library)
- The CLI can add machining overrides before decomposing
- The format is version-controlled (`"version": "1.0"`) for forward compatibility
- The format is self-contained (no external file references)

## Alternatives considered

- **Pre-decomposed panels**: Larger file, but consumers don't need the library. Rejected: creates risk of inconsistent decomposition if library and format diverge.
- **References to cabinet YAML files**: Smaller file, but not self-contained. Rejected: backend and CLI would need access to the same filesystem.

## References

- Codified in: `src/kuchnie_core/serialize.py`
- Verified by: `tests/test_serialize.py::test_json_contains_cabinet_details`
