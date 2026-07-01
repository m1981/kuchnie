# Agent Guide — kitchen-cam

Read this before making changes. It's short on purpose.

---

## Project at a glance

CAM enrichment layer for kitchen cabinet manufacturing. Takes panels produced by
`kuchnie_core` and adds machining operations (System32 drilling, hinge cups,
handles, dowels). Exports DXF drilling files for CNC shops.

**One sentence:** `kuchnie_core` produces panels → `kitchen-cam` adds drilling →
DXF/CSV for CNC.

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
├── models.py           Pydantic models (Panel, DrillPoint, CorpusSpec, etc.)
                        NOTE: these are kitchen-cam-local models used by
                        panel_calculator. They WILL be consolidated with
                        kuchnie_core.model in a future migration.
├── panel_calculator.py Cabinet → panel decomposition (Pydantic-based).
                        NOTE: duplicates kuchnie_core.catalog + decomposer.
                        Will be deleted when migration to kuchnie_core is done.
├── machining.py        System32, hinges, handles — adds DrillPoint[] to panels.
├── csv_generator.py    CSV cut list and edging export.
├── dxf/
│   └── legrabox_side_panel.py  Blum LEGRABOX DXF side-panel generator.
tests/
├── unit/               Model validation, edge banding, hinge config, materials.
├── integration/        Drill templates, grooving, edge drilling, mirror.
├── e2e/                Full pipeline: spec → panels → drilling → CSV/DXF.
```

**Dependency direction:** `dxf/` → `machining.py` → `models.py`.
Never import downward. `models.py` imports nothing from this package.

---

## The migration status (ADR-010)

**Renamed from:** `kitchen-cad/` (commit history preserved in git)

**Current state:** Renamed and cleaned. `panel_calculator.py` and `models.py`
are kept as temporary compatibility shims — they duplicate `kuchnie_core.catalog`
and `kuchnie_core.model`. The plan is to:

1. Make `panel_calculator.py` delegate to `kuchnie_core.decompose()` instead of
   computing panels locally
2. Delete `models.py` and have all code use `kuchnie_core.model` directly
3. Delete `panel_calculator.py` once tests use `kuchnie_core` directly

This is **follow-up work** tracked separately from the rename.

---

## Adding a machining operation

1. Add a `DrillType` enum value in `models.py` (or `kuchnie_core.model` after
   migration)
2. Write an `apply_<operation>(panels, spec) -> list[Panel]` function in
   `machining.py`
3. Register it in `apply_all_drilling()`
4. Write tests in `tests/integration/` verifying drill positions, diameters,
   depths
5. Run `pytest -v` — all tests must pass

---

## Adding a DXF generator

1. Create `src/kitchen_cam/dxf/<name>.py`
2. Use `ezdxf` to generate the DXF
3. Import panel dimensions from `kitchen_cam.models` (or `kuchnie_core.model`)
4. Write tests that verify geometry output
5. Run `pytest -v`

---

## Key constraints

- `ezdxf` is only in `dxf/` — keep it out of `machining.py` and `models.py`
- `kuchnie_core` is the canonical panel model — kitchen-cam models are temporary
- CNC company requires DXF format — don't add other output formats without
  checking their requirements
- All coordinates are in mm, relative to bottom-left of the panel's inside face

---

## Documentation conventions

| What | Where |
|---|---|
| "We chose X because Y" | `docs/adr/NNN-<slug>.md` (in repo root) |
| "The formula is Z" | Docstring + test assertion |
| "What changed" | `CHANGELOG.md` |
| "How to use this" | Module docstring at top of file |
| "How the system works" | `AGENTS.md` (this file) |
