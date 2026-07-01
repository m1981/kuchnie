# ADR-010: Kitchen-cad becomes kitchen-cam, downstream consumer of kuchnie_core

## Status

Accepted 2026-07-01

## Context

`kitchen-cad/` was introduced as a separate package aimed at manufacturing
concerns (System32 drilling, Blum side-panel DXF, CSV cut lists). In practice
it grew a parallel implementation of concepts already owned by `kuchnie_core`:

| Concept | `kuchnie_core` | `kitchen-cad` | Duplicate? |
|---|---|---|---|
| Panel model | `kuchnie_core.model.Panel` (dataclass) | `kitchen_cad.models.Panel` (Pydantic) | ✅ |
| Cabinet types | strings + `CabinetInstance` | Pydantic discriminated union (`BaseDoorConfig`, `BaseDrawerConfig`, `CornerBlindConfig`, `CornerInternalConfig`, `SinkConfig`, `CargoConfig`, `OvenConfig`) | ✅ |
| Corpus/dimensions | `kuchnie_core.model.CabinetInstance` fields | `kitchen_cad.models.CorpusSpec` | ✅ |
| Decomposition | `kuchnie_core.catalog.decompose_*` (registry) | `kitchen_cad.panel_calculator._calculate_*` (private per-type functions) | ✅ |
| Hinge modeling | `kuchnie_core.blum_hinges.HingeFactory` | `kitchen_cad.models.HingeSpec` + `kitchen_cad.drill_engine.apply_hinges` | ✅ |
| Drawer specs | `kuchnie_core.blum_drawers.DrawerSystemFactory` | `kitchen_cad.models.DrawerSpec` | ✅ |
| CSV cutting list | `kuchnie_core.export.cutlist_csv` | `kitchen_cad.csv_generator.generate_cutting_csv` | ✅ |

**Genuinely CAD-specific (not duplicated):**

- `kitchen_cad.drill_engine.system32_y_positions()` — System32 raster math
- `kitchen_cad.drill_engine.apply_system32()`, `apply_handles()`, `apply_all_drilling()` — machining-op enrichment on existing panels
- `kitchen_cad/generators/legrabox_side_panel.py` — Blum LEGRABOX DXF side-panel generator with drilling patterns for CNC

These CAM concerns are real and worth keeping. The duplicated models and
decomposition logic are not.

ADR-009 established the pattern: `kuchnie_core` is the pure domain hub;
peripheral packages depend on it, not the other way around. The same rule
applies here.

## Decision

**Rename `kitchen-cad/` → `kitchen-cam/`** and make it a **downstream consumer**
of `kuchnie_core`. It owns **only CAM enrichment**: machining-op computation
(System32, hinges, handles, dowels), DXF generation (drilling files for CNC
shops), and Blum-specific side-panel DXFs.

The name change is intentional: **CAM** (Computer-Aided Manufacturing) reflects
the actual scope. **CAD** (Computer-Aided Design) implies geometry/layout, which
is already owned by `home_builder_5` + `kuchnie_core`.

### What `kitchen-cam` owns (after migration)

- `kitchen-cam/src/kitchen_cam/machining.py` (renamed from `drill_engine.py`) —
  System32 raster, hinge positions, handle positions, dowel patterns. Pure
  functions: `Panel[] + CabinetInstance → Panel[]` with `MachiningOp[]` added.
- `kitchen-cam/src/kitchen_cam/dxf/` — DXF generators (currently only
  `legrabox_side_panel.py`, room to grow)
- `kitchen-cam/src/kitchen_cam/cli.py` (**new**) — `kitchen-cam drill kitchen.json --out drilling/`,
  `kitchen-cam side-panel --nl 500 --heights K,M --out legrabox.dxf`

### What migrates FROM `kitchen-cad` INTO `kuchnie_core`

| From | To | Rationale |
|---|---|---|
| `kitchen_cad.csv_generator.generate_cutting_csv` | Merge into `kuchnie_core.export.cutlist_csv` | CSV cut list is a domain output (list of panels), not a CAM-specific concern. `kuchnie_core` already owns this. |
| `kitchen_cad.csv_generator.generate_edging_csv` | New: `kuchnie_core.export.edging_csv` | Same rationale — panel-level output. |
| Any unique panel-role math (grooves, rabbets) not in kuchnie_core | Merge into `kuchnie_core.construction` | Domain, not CAM. |

### What is DELETED (no destination)

| File | Reason |
|---|---|
| `kitchen_cad/models.py` | Duplicate of `kuchnie_core.model` + `kuchnie_core.blum_hinges` + `kuchnie_core.blum_drawers`. `kitchen-cam` will import from `kuchnie_core`. |
| `kitchen_cad/panel_calculator.py` | Duplicate of `kuchnie_core.catalog` + `kuchnie_core.decomposer`. `kitchen-cam` consumes the panel list produced by `kuchnie_core.decompose()`. |
| `kitchen_cad/example_generate.py` | Rewrite as `kitchen-cam` CLI example that reads a `kuchnie_core.Kitchen` from JSON and emits DXFs. |

### What stays (renamed and rehomed)

| From | To | Change |
|---|---|---|
| `kitchen-cad/src/kitchen_cad/drill_engine.py` | `kitchen-cam/src/kitchen_cam/machining.py` | Rename; imports change to `from kuchnie_core.model import Panel, ...` |
| `kitchen-cad/generators/legrabox_side_panel.py` | `kitchen-cam/src/kitchen_cam/dxf/legrabox_side_panel.py` | Move into package layout; imports `LegraboxHeight`, dimensions from `kuchnie_core.legrabox` |
| `kitchen-cad/CHANGELOG.md` | `kitchen-cam/CHANGELOG.md` | Preserve history, note rename |
| `kitchen-cad/README.md`, `ROADMAP.md` | `kitchen-cam/README.md`, `ROADMAP.md` | Rewrite scope to reflect CAM-only role |
| `kitchen-cad/cabinet-types/*.png` | `kitchen-cam/docs/cabinet-types/*.png` OR archive | Visual reference; move under docs/ |

### Dependency direction (enforced)

```
kuchnie_core (pure domain — panels, decomposition, hardware, construction)
     ▲
     │ imports only
     │
kitchen-cam (CAM enrichment — machining ops, DXF)
```

`kitchen-cam` MUST NOT define its own cabinet or panel model. If a machining
operation needs data not in `kuchnie_core.model.MachiningOp`, extend the
`MachiningOp` model in `kuchnie_core` first, then use it in `kitchen-cam`.

## Consequences

**Positive**

- Single authoritative Panel/Cabinet/Hinge/Drawer model in `kuchnie_core`.
- `kitchen-cam` shrinks from ~2500 LOC to ~1000 LOC (only genuinely CAM code).
- New cabinet type = 1 file change (`kuchnie_core.catalog`), not 3.
- New machining operation = extend `kuchnie_core.model.MachiningOp` + one
  function in `kitchen-cam.machining`. No model duplication.
- The name `kitchen-cam` accurately signals scope to future LLM sessions.

**Negative**

- One-time migration effort (~2–3 days with LLM assistance).
- CHANGELOG history references `kitchen-cad` name; must add a note explaining
  the rename.
- Any external tools or scripts referencing `kitchen-cad` paths must update
  (verify: none outside the repo).

**Neutral**

- Existing `kitchen-cad` tests split by destination: pure decomposition tests
  merge into `tests/kuchnie_core/`; drilling and DXF tests move to
  `tests/kitchen_cam/`.

## Alternatives considered

**10a: Dissolve `kitchen-cad` entirely into `kuchnie_core`.**
Rejected because DXF generation is a CAM concern with heavy dependencies
(`ezdxf`) and file-system output responsibilities that don't belong in a pure
domain library. `kuchnie_core` should not depend on `ezdxf`.

**10c: Delete `kitchen-cad` entirely.**
Rejected because System32 raster math, drilling-op enrichment, and Blum
LEGRABOX DXF generation are real IP that reproduces work by CNC-shop suppliers.
Deleting means either abandoning DXF output or reinventing it later.

## References

- Duplication catalogue: derived from `code-sum.md` (repo root) — verified by
  side-by-side reading of `kitchen_cad/models.py` and `kuchnie_core/model.py`.
- Precedent: ADR-009 (`home-builder-adapter` as downstream consumer).
- Related ADRs:
  - ADR-001 (Panel is the atomic unit) — `kitchen-cam` treats `Panel` as the
    input atom, adds `MachiningOp` on it.
  - ADR-005 (MachiningOp model) — the shared vocabulary between `kuchnie_core`
    and `kitchen-cam`.
