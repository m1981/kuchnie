# ADR-003: Kitchen is the unit of work flowing through the system

## Status

Accepted

## Context

The system has three apps (kitchen-app, kitchen-plugin, kitchen-cli) that need to share data. The question is: what is the unit of data that flows between them?

Candidates:

- A) A single cabinet (too granular — can't represent layout)
- B) A row of cabinets (missing cross-row context like worktops)
- C) The entire kitchen (rows + worktops + project metadata)

## Decision

**The Kitchen is the unit of work.** It wraps rows, which wrap cabinets. This is what gets:

- Serialized to intermediate JSON (the contract between apps)
- Sent to the render backend (for Blender scenes)
- Consumed by the CLI (for cut lists and DXF)

```
Kitchen
├── project_name, created
├── rows: [Row]
│   ├── wall_width_mm, wall_height_mm
│   └── cabinets: [CabinetInstance]
└── worktops: [WorktopSegment]
```

## Consequences

- `kitchen_to_json()` serializes the whole kitchen — one file, self-contained
- `all_panels(kitchen)` aggregates panels across all cabinets, all rows
- `export_cutlist_csv(kitchen, path)` produces a single CSV for the whole kitchen
- `validate_rows(kitchen)` checks that cabinets fit in their rows
- Per-cabinet operations (decompose, BOM) still work on individual cabinets

## References

- Codified in: `src/kuchnie_core/model.py::Kitchen`, `src/kuchnie_core/kitchen.py`
- Verified by: `tests/test_kitchen.py`, `tests/test_serialize.py`, `tests/test_cutlist.py`
