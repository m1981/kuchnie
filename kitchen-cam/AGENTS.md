# Agent Guide — kitchen-cam

Read this before making changes. It's short on purpose.

---

## Project at a glance

CAM enrichment layer for kitchen cabinet manufacturing. Takes panels produced by
`kuchnie_core` and adds machining operations (System32 drilling, hinge cups,
handles, dowels). Exports DXF drilling files for CNC shops.

**One sentence:** `kuchnie_core` produces panels → `kitchen-cam` adds drilling →
DXF for CNC.

---

## Architecture (3 rules)

1. **kitchen-cam is a downstream consumer.** It imports from `kuchnie_core`. It
   never defines its own cabinet or panel model. (`ADR-010`)

2. **Machining ops are the domain.** System32 raster, hinge positions, handle
   holes, dowel patterns — these live here. Panel decomposition, cabinet types,
   BOM — those live in `kuchnie_core`.

3. **DXF is the output format.** The CNC company needs DXF drilling files. This
   is why `kitchen-cam` exists as a separate package (with `ezdxf` dependency)
   rather than being merged into `kuchnie_core`.

---

## File map

```
src/kitchen_cam/
├── __init__.py
├── machining.py        System32, hinges, handles — imports from kuchnie_core.model
└── dxf/
    └── legrabox_side_panel.py  Blum LEGRABOX DXF side-panel generator
```

**Dependency direction:** `dxf/` → `machining.py` → `kuchnie_core.model`.
Never import downward. `kuchnie_core` owns all domain types.

---

## Adding a machining operation

1. Extend `MachiningOp.drill_type` vocabulary if needed (open string in
   `kuchnie_core.model`)
2. Write an `apply_<operation>(panels, cab) -> list[Panel]` function in
   `machining.py`
3. Register it in `apply_all_drilling()`
4. Write tests in `tests/test_drill_engine.py` verifying drill positions,
   diameters, depths
5. Run `pytest -v` — all tests must pass

---

## Adding a DXF generator

1. Create `src/kitchen_cam/dxf/<name>.py`
2. Use `ezdxf` to generate the DXF
3. Import panel dimensions from `kuchnie_core.model`
4. Write tests that verify geometry output
5. Run `pytest -v`

---

## Key constraints

- `ezdxf` is only in `dxf/` — keep it out of `machining.py`
- `kuchnie_core` is the canonical panel model — kitchen-cam never redefines it
- CNC company requires DXF format — don't add output formats without checking
- All coordinates in mm, relative to bottom-left of panel's inside face
