# 01 — Locked Architectural Decisions

> **Status:** Accepted 2026-06-29. Supersedes everything in `archive/`.
> **Evidence base:** `06_AUDIT_EVIDENCE.md` (cold execution flow analysis of all six prototypes).

---

## D1 — Strategy: U2 (Pick a winner per concept + thin glue)

**Decision.** Each domain concept has exactly one **canonical owner**. The other prototypes either delete their version or treat it as a private projection. A thin glue layer in `src/kuchnie_core/` re-exports types and provides adapters.

**Why not U1 (refactor everything into shared core):** 30,000+ LOC of touched code; 3–6 months; no new features delivered while refactoring.
**Why not U3 (pick one, abandon others):** discards 4 working specialized subsystems.
**Why U2:** preserves all the R&D work; integration effort is ~3–5 weeks; risk is locally bounded per concept.

---

## D2 — Canonical Owners (the winner table)

| Concept | Canonical owner | Module path | Retired duplicates |
|---|---|---|---|
| **Material catalog** (Decor, Variant, Edge, Pairing, Worktop, Producer) | `catalog/` | SQLite + FastAPI + 22-table schema | `kitchen-app/Material` table → becomes thin pricing-only projection; compositor `catalog_db.py` → derived from catalog at boot; kuchnie_core `materials/VariantInfo` → already an adapter, kept |
| **Cabinet (placement on a wall)** | `kitchen-plugin/` | `kitchen.cabinet.Cabinet`, `CabinetPlacement` | `kuchnie_core.model.CabinetInstance` → **retired**; kitchen-app `Cabinet` SQLModel → becomes persistence adapter |
| **Cabinet (parametric spec)** | `kitchen-cad/` | `kitchen_cad.models.CorpusSpec` + discriminated-union configs | kitchen-app `recipes.json` → relegated to BOM-formula metadata layered on top |
| **Panel (atomic manufacturing unit)** | `kitchen-cad/` | `kitchen_cad.models.Panel` (+ `EdgeBand`, `DrillPoint`) | `kuchnie_core.model.Panel` → **retired** |
| **Recipe (cabinet → panels)** | `kitchen-cad/` | `kitchen_cad.panel_calculator.calculate_panels()` + per-type Python functions | `kuchnie_core.catalog.decompose_dolna_*` → **retired**; kitchen-plugin `_build_cabinet` → becomes thin bpy adapter consuming `list[Panel]`; kitchen-app formula JSON → kept for BOM only |
| **BOM + cost** | `kitchen-app/` | `kitchen_erp.bom_generator.BOMGenerator` + `rules_engine` + `purchasing` | `kuchnie_core.bom.calculate_bom` → **retired** |
| **3D engineering render** | `kitchen-plugin/` | `geometry_builder`, `geometry_manifest`, `manifest_validator`, `exporters` | (no competitor) |
| **2.5D live render** | `krono-compositor-mvp/` | `SceneCompositor` + FastAPI | (no competitor) |
| **Web UI** | `kitchen-app/` | Reflex pages + `KitchenState` | (no competitor) |
| **Cut-list / DXF / drilling** | `kitchen-cad/` | `csv_generator`, `drill_engine`, `generators/legrabox_side_panel` | `kuchnie_core.export.cutlist_csv` → **retired** |
| **Material resolver (role → slot → decor → variant)** | `src/kuchnie_core/` | `kuchnie_core.materials.MaterialResolver` (already an adapter over catalog's SQLite) | compositor catalog logic → projection only |
| **`ConstructionMethod` registry** (NEW) | `src/kuchnie_core/` | `kuchnie_core.construction` (to be created) | kitchen-plugin hardcoded `DEFAULT_*` constants → migrated to import from registry |
| **Validation gates with codes** (NEW) | `src/kuchnie_core/` | `kuchnie_core.validation` (to be created) | kitchen-plugin `validators.py` + `manifest_validator.py` → wrapped as gate implementations; kitchen-cad Pydantic validators → kept inline |
| **Kitchen YAML loader/serializer** | `src/kuchnie_core/` | `kuchnie_core.loader`, `kuchnie_core.serialize` (already exist; need schema update) | — |

> The patterns referenced in the registry/gate column come from `05_PATTERN_GOLD.md` — the distilled CAD/CAM vocabulary that justifies these new abstractions.

---

## D3 — Packaging: Subdirs + `PYTHONPATH`, not `pip install -e`

**Decision.** Keep prototypes as subdirs. Use a project-root `pyproject.toml` workspace + `PYTHONPATH` for development; no per-prototype editable installs.

```
kuchnie/
├── pyproject.toml          ← workspace-level; declares src layout
├── src/kuchnie_core/       ← glue
├── catalog/                ← own pyproject.toml + own .venv? OR shared?
├── kitchen-cad/            ← own pyproject.toml today (FastAPI not needed, plain lib)
├── kitchen-plugin/         ← own pyproject.toml
├── kitchen-app/            ← own pyproject.toml (Reflex)
└── krono-compositor-mvp/   ← own pyproject.toml (FastAPI + OpenCV)
```

**Rationale.** Each prototype already has its own `pyproject.toml` and `.venv`. Forcing pip-editable installs creates dependency-graph headaches (Reflex pulls fastapi; catalog pulls fastapi; compositor pulls fastapi — version conflicts likely). Subdirs + `PYTHONPATH` lets each subsystem keep its own deps, while `kuchnie_core` imports across them at integration points.

**Mechanism.** A `conftest.py` at project root (or a `Makefile` `export PYTHONPATH=...:catalog:kitchen-cad:kitchen-plugin/src:krono-compositor-mvp/src:kitchen-app:src`) gives imports like `from kitchen_cad.models import CorpusSpec` clean access across subdirs. The walking skeleton sets this up.

---

## D4 — Retirements (delete or shrink in next sweep)

Confirmed retirements (delete in the F002/F005 phases after kuchnie_core glue is in place):

- `src/kuchnie_core/catalog.py` (the `decompose_dolna_*` functions and `TYPE_REGISTRY`)
- `src/kuchnie_core/decomposer.py`
- `src/kuchnie_core/model.py::CabinetInstance` (replaced by `from kitchen_plugin.kitchen.cabinet import Cabinet`)
- `src/kuchnie_core/model.py::Panel` (replaced by `from kitchen_cad.models import Panel`)
- `src/kuchnie_core/bom.py` (replaced by `kitchen-app/kitchen_erp/bom_generator.py`)
- `src/kuchnie_core/export/cutlist_csv.py` (replaced by `kitchen-cad/src/kitchen_cad/csv_generator.py`)

**Kept** (with refactor):
- `src/kuchnie_core/loader.py` and `serialize.py` — Kitchen YAML I/O
- `src/kuchnie_core/materials/` — already the canonical material resolver (the one existing cross-prototype bridge)
- `src/kuchnie_core/legrabox.py` — Polish-specific Legrabox drawer math. Reused by kitchen-cad's drawer logic.
- `src/kuchnie_core/model.py::Kitchen, Row, WorktopSegment` — kept as the YAML-document shape, but `Row` may rename to `Run` to match kitchen-plugin (decision below).

---

## D5 — Naming Reconciliations

Two name battles between subsystems. Resolved:

- **`Run` (kitchen-plugin) vs `Row` (kuchnie_core)** → **`Run`** wins (kitchen-plugin's term; matches Polish-industry "rząd"). `kuchnie_core.model.Row` → renamed to `Run` in the YAML-shape refactor.
- **`Cabinet` (kitchen-plugin) vs `CabinetInstance` (kuchnie_core) vs `CorpusSpec` (kitchen-cad)** → **two distinct things, kept**:
  - `Cabinet` = placement-aware (has wall_id, offset). Lives in kitchen-plugin.
  - `CorpusSpec` = parametric-spec for panel decomposition. Lives in kitchen-cad.
  - The glue (`kuchnie_core.recipe.cabinet_to_corpus_spec(cab)`) adapts the first to the second when calling decomposition. **The pair is intentional, not a duplicate to fix.**

---

## D6 — Cross-Import Rule (The One Rule)

```
kuchnie_core/  imports from: catalog/, kitchen-cad/, kitchen-plugin/, krono-compositor-mvp/, kitchen-app/
all other subsystems  imports from: kuchnie_core/ ONLY (not from each other)

If kitchen-app needs a Panel:                from kuchnie_core.recipe import Panel   ✓
If kitchen-app imports kitchen_cad directly:                                            ✗
```

This makes `kuchnie_core` the **anti-corruption layer** between subsystems. Each subsystem stays focused on its specialization; cross-cutting concerns go through one place.

**Enforcement:** a lint rule in CI (`scripts/check_imports.py`) that walks the AST of each subsystem and fails on disallowed cross-imports. Written in the walking skeleton phase.

---

## D7 — What the F00X Plans Become

The original F001–F008 ADRs assumed greenfield. Under U2, each becomes either an **integration job** or a **net-new abstraction layered on existing code**. See `03_ROADMAP.md` for the new sequencing.

| Feature | New shape under U2 |
|---|---|
| **F001 ConstructionMethod** | Net-new registry in `kuchnie_core`. kitchen-plugin's `cabinet_geometry.py` constants migrate to import from it. ~1 day. |
| **F002 Recipe Engine** | Reconciliation. kitchen-cad's `panel_calculator` is canonical. Port the 3 Polish types from kuchnie_core into kitchen-cad. ~3–5 days. |
| **F003 Template Registry** | Reconciliation. Pick one Polish-cabinet-type taxonomy across kitchen-app/recipes.json + kitchen-cad/cabinet-types/ + kitchen-plugin/CabinetType. ~2–3 days. |
| **F004 Validation Gates** | Net-new code registry. Existing checks wrapped as gates. ~2–3 days. |
| **F005 Material Resolver** | Build the role→slot→decor chain on top of existing `kuchnie_core.materials.MaterialResolver`. ~2–3 days. |
| **F006 Web Sidebar** | Integration: wire kitchen-app to compositor (live render) and kitchen-cad (CSV export). ~3–5 days. |
| **F007 Render Adapter** | Integration: wire kitchen-plugin's `material_manager.py` to load real textures via catalog. ~2–3 days. |
| **F008 CLI Export** | Package `kitchen-cli` binary wrapping kitchen-cad + kitchen-plugin subcommands. ~3–5 days. |

**Total post-skeleton effort: ~3–5 weeks of solo-dev work.**

---

## D8 — Walking Skeleton First

No "real" feature work starts until the walking skeleton (`02_WALKING_SKELETON.md`) is green. The skeleton is the proof that the integration plan in this document survives contact with code. ~1 week.
