# Integration Plan — kitchen-plugin + F001-F008 Gold

> **Confirmed:** Option A (adopt kitchen-plugin as foundation).
> **Confirmed:** The architectural "gold" in F001-F008 (stolen from PRO100, Polyboard, Winner Flex, TopSolid'Wood, PaletteCAD) is **abstractions on top of what kitchen-plugin already does imperatively**. Absorbing kitchen-plugin does NOT mean discarding the gold — it means turning F1-F4 into *refactoring* features that promote kitchen-plugin's hardcoded knowledge to declarative form, and treating F5/F6/F8 as net-new work that kitchen-plugin never touched.

This document is based on actual `pysum` of `kitchen-plugin/src/` (not docs, which the user warned are stale).

---

## 1. What kitchen-plugin Actually Has (Ground Truth from Code)

### Layer 1 — `core/` (pure math, zero deps)

- `Vector2D`, `Vector3D`, `BoundingBox`, `Transform2D` — linear algebra primitives
- Enums: `Direction`, `CabinetLevel`, `CabinetType`, `HandleType`, `DoorSide`
- Value object: `Dimensions` (with `with_offsets()` for tolerance shifts)

### Layer 2 — `kitchen/` (domain, depends only on core)

| File | Type | Owns |
|---|---|---|
| `cabinet.py` | `Cabinet` (frozen dataclass), `CabinetPlacement`, `Countertop` | Identity + position of a cabinet on a wall |
| `cabinet_geometry.py` | `CabinetGeometry` | **Construction math** — converts external dims → internal cavity + side/top/bottom/back panel dims. Hardcoded `DEFAULT_CORPUS_THICKNESS=18`, `DEFAULT_FRONT_THICKNESS=19`, `DEFAULT_BACK_THICKNESS=3`, `DEFAULT_GROOVE_*`, `DEFAULT_OVERLAY_*`. |
| `wall.py` | `Wall`, `Room`, `CornerReference`, `BoxVertices` | Wall-centric layout model |
| `layout.py` | `Run`, `Layout`, `LayoutEngine` | Places cabinets along walls; handles `cabinet_gap`, `front_gap`, plinth height, wall mount height, corner detection |
| `standards.py` | `KitchenStandards` | European 32mm-system standards: base_body_height, base_depth, wall_height, wall_depth, tall_height, plinth_height, plinth_setback, wall_mount_height, counter thickness/overhangs |

### Layer 3 — builders (config → domain)

- `config_parser.py` — loads JSON, applies defaults, validates schema (1.0/1.1), computes run positions
- `validators.py` — config-level checks: dimensions, overlaps, gaps, face direction, corners, room fit, countertops. Returns `list[str]` of error messages (no codes).
- `wall_builder.py` — `config_to_walls()`, `config_to_cabinets()`, `config_to_corners()`, `build_domain_layout()`. Glues raw JSON to domain objects.

### Layer 4 — adapters (bpy required)

- `geometry_builder.py` — `build_kitchen_from_layout()`, `_build_cabinet()`, `_create_carcass()`, `_add_back_panel()`, `_add_front()` (door, drawer), `_build_filler()`, `_build_countertop()`. **All decomposition logic lives here in Python branches per cabinet type.**
- `geometry_manifest.py` — exports JSON manifest of every built object with measurements, validation flags, classification
- `material_manager.py` — `create_materials()` + `_create_material()`. Reads `config["materials"]` as RGB colors only. **No texture paths, no Kronospan/Egger catalog awareness.**
- `manifest_validator.py` — `validate_manifest()` checks dimensions, overlaps, vertex/face counts, standard widths, run continuity, construction parameters. Returns `ValidationResult` with `Issue` objects (no error codes).
- `exporters.py` — `export_blend()`, `render_wireframe()`

### Layer 5 — CLI

- `main.py` — argparse: positional `config.json`, flags `--validate`, `--no-manifest`, `--no-materials`, `--export-blend`, `--render-wireframe`

### Tests

22 test files covering: config_parser, validators, cabinet construction, drawer validation, room validation, coordinate system, gap semantics, tolerance model, wall builder, wall-centric model, L/U/I shapes, manifest schema, manifest validation, layout, geometry_builder.

### What the README claims that isn't in code (stale docs warning)

- README claims a "DDD strategic design" with `kitchen/wall.py::Wall, Room, CornerReference`, `kitchen/cabinet.py::Cabinet, CabinetPlacement`, `kitchen/layout.py::Run, LayoutEngine`, `kitchen/cabinet_geometry.py::Board-level construction math`, `kitchen/standards.py::KitchenStandards`. **All confirmed by pysum.**
- CHANGELOG `[Unreleased]` shows breaking refactor that moved `WallCabinet` from `kitchen/wall.py` to `wall_builder.py`. Confirmed by pysum: `WallCabinet` is in `wall_builder.py`.
- Docs are LESS stale than warned, but the **architecture.md** layered-architecture description matches the code. Good signal.

---

## 2. The 00-brief.md Use Cases vs Current State

| Use case step | kitchen-plugin covers? | Gap |
|---|---|---|
| **UC1 First visit — 2.5D web preview** | | |
| 1. Visit customer with Kronospan/Egger decors | n/a (workflow) | — |
| 2-4. Open web app, see predefined layouts, choose one | ❌ no UI | **F006 (web sidebar) + F003 (templates)** |
| 5. Sidebar: change decors for ground/tall/wall cabinets, countertop, splashback | ❌ no UI, ❌ no catalog | **F005 (catalog) + F006 (UI)** |
| 6. Backend generates 2.5D high-quality image | ✅ kitchen-plugin renders | Need texture integration (F007) |
| 7. Screenshots, repeat | n/a (iPad) | — |
| **UC2 Cost estimation with BOM** | | |
| 1. Open web app | ❌ | **F006** |
| 2. Simple 2D layout, rows from measurements | ⚠️ partial — `LayoutEngine` exists but no web | F006 |
| 3. Add cabinet types from sidebar, arrow-move them | ❌ no UI | F006 + F003 |
| 4. Global dimension setup | ✅ `KitchenStandards` in code | UI exposure (F006) |
| 5. Per-cabinet override of dimensions/config | ⚠️ JSON only | F006 |
| 6. Auto cost update with board + accessory pricing | ❌ no pricing | **F008 cost-estimate (new)** |
| 7-8. Generate renders, send config + decor names to backend | ✅ kitchen-plugin renders | F007 integration |
| 9. Blender file generation with proper textures by decor names | ⚠️ Blender ✅, textures ❌ | **F005 + F007 wiring** |
| 10. Import to scene, generate renders | ✅ | — |
| **UC3 CAM preparation** | | |
| 1. Customer accepted | n/a | — |
| 2. Tweak intermediate format (vent holes, LED grooves) | ⚠️ JSON config exists; no editor for machining features | **F008 machining + F006 maybe** |
| 3. CLI → CSV cut list (e-rozkroj, e-rozrys) | ❌ kitchen-plugin emits manifest.json, not CSV | **F008 CSV exporter (new)** |
| 4. CLI → drill/dowel/hinge boring, panel rabbet | ❌ kitchen-plugin doesn't compute machining patterns | **F008 drill pattern + MachiningFeature (new)** |
| 5. Estimated cost with accessories + nesting | ❌ | F008 cost-estimate |
| 6. DXF to CNC company | ❌ | **F008 DXF exporter (new)** |

**Conclusion:** kitchen-plugin nails the **rendering + structural-validation** parts of UC1/UC2/UC3. It does NOT touch:
- Web UI (UC1 step 2-5, UC2 step 1-5)
- Material catalog with Polish producers (UC1 step 5, UC2 step 9)
- Cost estimation (UC2 step 6)
- CSV/DXF/CAM outputs (UC3 step 3-6)

These gaps map exactly to **F005 + F006 + F008** — the three features the cold review's discovery identified as genuinely new work.

---

## 3. The "Gold" From F001-F008 (and where it lives now)

The architectural insights stolen from commercial CAD systems. For each, I list: what kitchen-plugin has today, what the F-spec proposed, and the gap (= the gold to preserve).

### F001 — ConstructionMethod (from Winner Flex's "construction logic separation")

| | kitchen-plugin | F001 ADR |
|---|---|---|
| WHAT (cabinet identity) | `Cabinet` dataclass | `CabinetInstance` |
| HOW (joinery, thickness, joinery type) | Hardcoded constants in `cabinet_geometry.py` | **`ConstructionMethod` registry** with named methods (e.g., `dowel_camlock_18`, `groove_dado_18`) |
| Resolution | One global default forever | Project-level default + per-cabinet override |

**Gold to preserve:** the **registry of named methods**, swappable per project. kitchen-plugin's `cabinet_geometry.py` currently bakes one method (`DEFAULT_CORPUS_THICKNESS=18` + groove back + 2mm overlay) into code. F001 promotes it to data.

**Refactoring scope:** turn `cabinet_geometry.py`'s `DEFAULT_*` constants into a `ConstructionMethod` dataclass. Add a registry of named methods. `CabinetGeometry` constructor takes a `ConstructionMethod` instead of using module constants. Old constructor signature kept with a "default method" for backward compat.

### F002 — Recipe Engine (from Polyboard's "cabinet macros as data")

| | kitchen-plugin | F002 ADR |
|---|---|---|
| Cabinet decomposition | `geometry_builder._build_cabinet()` Python branches per `CabinetType` enum | **YAML recipes** with formulas (`asteval`) |
| Where new cabinet types are added | Edit Python, edit `CabinetType` enum, edit `_build_cabinet` switch | Add a new YAML file |
| Atomicity | Boards emitted as bpy `Object`s | `Panel` dataclass emitted; bpy is one consumer |

**Gold to preserve:** **decomposition is data, not code.** A new cabinet type is a YAML diff, not a Python diff. The renderer + cut-list + BOM all consume the same `list[Panel]` output.

**Refactoring scope:** Extract `_build_cabinet`'s per-type logic into YAML recipes evaluated by `asteval`. Replace bpy-emitting code with `Panel`-emitting code. `geometry_builder` becomes a thin "list[Panel] → bpy objects" translator. Per-type Python switch shrinks to zero.

### F003 — Template Registry (from PRO100's "cabinet macros")

| | kitchen-plugin | F003 ADR |
|---|---|---|
| Cabinet type | String enum value (`"base-door"`, `"base-drawer-door"`) | Full `CabinetTemplate` with default dims, constraints, sub-assemblies, material role defaults |
| Discoverability | Hardcoded in `CabinetType` enum + `config_parser` validation | YAML registry + `list_templates()` |
| User customization | JSON config (technical) | Web sidebar (UC1, UC2) |

**Gold to preserve:** the **declarative template with merge-by-kind sub-assembly overrides**. PRO100 lets users instantiate macros and override individual parts; kitchen-plugin makes you specify the whole cabinet JSON each time.

**Refactoring scope:** Build the YAML template registry. Each kitchen-plugin `CabinetType` enum value maps to one or more templates. Templates carry `default_sub_assemblies` (`door`, `shelf_bank`, `drawer_stack`) that decompose via the F002 recipe.

### F004 — Validation Gates (from TopSolid'Wood's "manufacturability gates")

| | kitchen-plugin | F004 ADR |
|---|---|---|
| Validation surfaces | `validators.py` (config), `manifest_validator.py` (post-build) | 4 gates: Cabinet, Row, Kitchen, CAM-readiness |
| Error model | `list[str]` (config-time) + `Issue` dataclass (post-build) | `Issue` with `code: str` (DIM-001 etc.), `severity`, `gate` |
| Cross-feature contracts | None | **Reserved codes** (KIT-100 / CAM-100 for F005) via `register_check` |
| Same answer everywhere | Only used by kitchen-plugin's own pipeline | Web, CLI, render all call the same gates |

**Gold to preserve:** the **error-code registry + reserved-codes contract pattern**. Without it, the Web sidebar invents its own dimension check, the CLI invents another, and the CNC sees a different "validity" answer at 6pm Friday than the customer saw at noon.

**Refactoring scope:** Promote `Issue` to carry a `code: str`. Wire `validators.py` checks into Cabinet/Row gates; wire `manifest_validator.py` checks into Kitchen/CAM gates. Add the `register_check` API. Reserve codes KIT-100 and CAM-100 for F005.

### F005 — Material Resolver (from Winner Flex's "material assignment decoupled")

| | kitchen-plugin | F005 ADR |
|---|---|---|
| Material model | `config["materials"]["carcass"]["color"] = [0.9, 0.9, 0.88]` (RGB) | Role → slot → decor chain; `ResolvedMaterial` with `texture_path`, `paired_edge_id`, `grain_direction`, `sheet_size_mm`, `sku` |
| Catalog | None | `catalog/` with Kronospan/Egger producers, decors, edges, pairings, variants |
| Edge banding | None | `paired_edge_id` resolution via `<role>_color` suffix |
| Material assignment to panels | bpy material per-Object via `material_manager.py` | Per-`Panel` via `recipe_role` |

**Gold to preserve:** **decouple material from construction.** Customer-facing decisions (which Kronospan decor for fronts?) are orthogonal to manufacturing (what joinery? what edge banding?). kitchen-plugin currently entangles them at render time.

**Refactoring scope:** Build the catalog as net-new (no equivalent in kitchen-plugin). Build `MaterialResolver` in `src/kuchnie_core/`. Modify `material_manager.py` to consume `ResolvedMaterial.texture_path` (image textures) instead of RGB-only color blocks.

### F006 — Web Sidebar (entirely new — no precedent in any CAD we studied; the WHOLE thing is original work)

kitchen-plugin has zero web UI. F006 is entirely net-new. **Gold: nothing to preserve here yet** — F006 itself is the gold (a Polish-market-focused 2.5D web configurator). Reflex (Python web framework) chosen so the solo dev stays in one language.

### F007 — Blender Adapter (now: integration, not "build from scratch")

| | kitchen-plugin | F007 ADR (now superseded) |
|---|---|---|
| Renderer | ✅ working | Build `kitchen-render/` from scratch ❌ |
| Standalone Python + subprocess | ✅ `main.py` already does this | Build the entry point ❌ |
| Manifest output | ✅ `geometry_manifest.py` | Build it ❌ |
| Material/texture integration | ❌ RGB only | Wire `MaterialResolver` → bpy textures |
| Render presets (camera angles, HDRI lighting, multi-view) | ❌ only wireframe | New work (see kitchen-plugin ROADMAP "Next Phase: Material System + Rendering") |
| WallPlacement model | ✅ `Wall`, `Room`, `CornerReference` | Build it ❌ |

**Gold to preserve:** the **decision to use subprocess** (not `pip install bpy`) and **manifest JSON as primary output** (not OBJ/glTF) — both already true in kitchen-plugin. F007's *rejected* alternatives (Alt A, B, C) still apply.

**Refactoring scope:** F007 becomes an **integration feature**, not a build feature. Wire F005's `ResolvedMaterial` into `material_manager.py`. Add render presets (camera, HDRI, multi-view). The "build the renderer" work is already done.

### F008 — CLI Cut List / DXF / Drill / BOM / Cost

| | kitchen-plugin | F008 ADR |
|---|---|---|
| CLI binary | `main.py` (`blender --background --python main.py`) | `kitchen-cli` (`cut-list`, `drill-pattern`, `dxf`, `bom`, `cost-estimate`, `render`) |
| Render subcommand | ✅ `main.py` IS this | Wrap kitchen-plugin's main.py |
| Cut list CSV (e-rozkroj) | ❌ | **New** |
| Drill pattern CSV | ❌ | **New** |
| DXF panel export | ❌ | **New** |
| BOM | ❌ | **New** |
| Cost estimate | ❌ | **New** |
| MachiningFeature (dowel holes, hinge boring, rabbets) | ❌ (only knows back-panel groove) | **New** |

**Gold to preserve:** the **`MachiningFeature` model**, **DrillPatternRef → MachiningFeature materialization** (F008's PatternResolver), the **subcommand registry** (F007 contributes `render`).

**Refactoring scope:** F008 is mostly net-new. Build `kitchen-cli` as a new top-level binary. The `render` subcommand wraps kitchen-plugin's existing `main.py`. The other subcommands (`cut-list`, `drill-pattern`, `dxf`, `bom`, `cost-estimate`) are entirely new and consume kitchen-plugin's domain types (`Panel` list, `CabinetGeometry`).

---

## 4. The Corrected Bounded Context Map

> **Critical change vs original planning:** `kuchnie_core` no longer owns Cabinet/Wall/Room geometry. kitchen-plugin does. Core becomes the **registry + workflow layer**, thinner and more focused.

| Context | Path | Owns | Was previously assigned to |
|---|---|---|---|
| **Catalog** | `catalog/` | Decor, Edge, Pairing, Producer, Variant — Polish material data | (unchanged) |
| **Geometry + Render** | `kitchen-plugin/` (consider rename to `kitchen-render/`, but optional) | Cabinet, Wall, Room, CornerReference, Run, Layout, LayoutEngine, CabinetGeometry, KitchenStandards, Manifest, ManifestValidator, bpy renderer, material_manager (wired to F005) | This was F007's job ("new `kitchen-render/`") |
| **Domain Core** | `src/kuchnie_core/` | **Registries:** `ConstructionMethod` (F001), `Recipe` (F002), `CabinetTemplate` (F003), `ValidationGate` registry (F004), `MaterialResolver` (F005). **Workflow:** Project, BOM, Kitchen-as-document, serialize/load YAML. | Was assigned Cabinet/Row geometry too (wrong) |
| **CAD/CAM** | `kitchen-cad/` | CSV/DXF/BOM/cost exporters, MachiningFeature, DrillPattern YAMLs, PatternResolver | (unchanged — F008) |
| **Web** | `kitchen-app/` | Reflex UI (sidebar, configurator, decor picker) — F006 | (unchanged) |
| **Plugin (external reference, untouched)** | `home_builder_5/` | Community reference; not part of runtime | Rule 4 (unchanged, but now demoted to "reference only") |

### Why this split is correct

1. **Construction math (e.g., side panel width = external_width - 2*corpus_thickness)** is geometry, not catalog. It belongs in kitchen-plugin's `cabinet_geometry.py`.
2. **What thickness to use** (i.e., which `ConstructionMethod`) is a *project setting*, not geometry. It belongs in `kuchnie_core` as a registry. kitchen-plugin's `CabinetGeometry` accepts a `ConstructionMethod` argument; it doesn't define methods.
3. **Cabinet identity** (`base-door` vs `base-drawer-door`) is a template, not a fixed enum. The enum stays in `kitchen-plugin/core/types.py` for now, but the *catalog of available templates* lives in `kuchnie_core/templates/` as YAML.
4. **Validation logic** stays where the data is (kitchen-plugin has the dimensions to check) but the **registry of codes** lives in `kuchnie_core` so Web/CLI/Render all see the same codes.

### Dependency direction (must stay acyclic)

```
catalog/  →  (nothing imports from catalog except via Protocol; F005 ACL pattern)

kuchnie_core/  imports:  catalog/  (via CatalogReader Protocol — Catalog implements Core's Protocol)
                         kitchen-plugin/kitchen/  (for Cabinet, Wall, Layout types) ← NEW direction

kitchen-plugin/  imports:  ITS OWN core/ + kitchen/  (Layer 1-2)
                           kuchnie_core/  (only for ConstructionMethod, Recipe, CabinetTemplate, MaterialResolver — i.e., registries)
                           bpy  (Layer 4 only)

kitchen-cad/  imports:  kuchnie_core/  (for Kitchen, BOM, MaterialResolver)
                        kitchen-plugin/kitchen/  (for CabinetGeometry types, Panel list)

kitchen-app/  imports:  kuchnie_core/
                        kitchen-cad/  (for cost-estimate inputs)
                        catalog/  (via Protocol)
```

**Question for the user:** is the dependency `kuchnie_core → kitchen-plugin` acceptable? Today, kitchen-plugin imports from itself only. If kuchnie_core needs `Cabinet`/`Wall`/`Layout` types, we have two choices:

- **A.** kuchnie_core imports them from `kitchen-plugin.kitchen` (reverses what previous planning assumed). Clean if we treat kitchen-plugin as "the geometry library." Cyclic-import risk: zero, as long as kitchen-plugin doesn't import from `kuchnie_core` (today it doesn't).

- **B.** Move `kitchen-plugin/src/kitchen/` and `kitchen-plugin/src/core/` UP into `src/kuchnie_core/` and leave the bpy adapters in `kitchen-plugin/src/{geometry_builder,manifest_validator,material_manager}.py`. Then kitchen-plugin becomes a small adapter package that depends on kuchnie_core.

- **C.** Leave the two trees separate, define a shared types package `src/kuchnie_types/` that both depend on, factor out `Cabinet`/`Wall`/`Layout`. More refactor effort up front.

**My recommendation: B.** It's the most explicit. The domain model (Cabinet, Wall, Layout, CabinetGeometry, KitchenStandards) belongs in Core; the bpy adapter belongs in kitchen-plugin. This is exactly what kitchen-plugin's own architecture.md already says (Layer 2 = "domain logic, depends only on core"). We just promote Layer 1+2 from `kitchen-plugin/src/{core,kitchen}/` to `kuchnie/src/kuchnie_core/{geometry,domain}/`.

---

## 5. Canonical Name Battles — Decisions Needed

For each pair, kitchen-plugin's version is on the left, our planned name on the right. **I recommend the left in all cases except where noted**, because kitchen-plugin's code is already working and tested.

| kitchen-plugin | F-spec planned | Recommendation | Reason |
|---|---|---|---|
| `Cabinet` | `CabinetInstance` | **`Cabinet`** | Shorter, used in 22 tests already. "Instance" suffix only matters if we have a "CabinetClass" — we don't. |
| `Run` | `Row` | **`Run`** | Tested, established. "Run" is also the English-Polish kitchen-industry term ("rząd szafek" / "kitchen run"). |
| `KitchenStandards` + `ConstructionMethod` separate | `ConstructionMethod` absorbs everything | **Both, distinct roles** | `KitchenStandards` = market-defaults (32mm system, base_depth=560). `ConstructionMethod` = swappable per project. Keep both, document the difference. |
| JSON config | YAML config | **YAML, with backward-compat JSON loader** | YAML is human-friendlier, and Recipe/Template/ConstructionMethod registries will be YAML anyway. Migrate kitchen-plugin's config_parser to also accept YAML; deprecate JSON gradually. |
| `Issue` (no code) | `Issue` with `code: str` | **`Issue` with `code: str`** | F004's gold — promote kitchen-plugin's `Issue`. |
| `CabinetType` enum | `CabinetTemplate` (data) | **Keep enum + add template registry** | Enum stays for type dispatch; template registry adds the data layer on top. |
| `validate_manifest()` returns `ValidationResult` | 4-gate `register_check` API | **Layer the 4-gate API on top of `validate_manifest`** | Don't replace — wrap. The existing checks become Cabinet/Kitchen gate implementations. |

---

## 6. The Spec-Rewrite Plan (Priority Order)

Each item below is "spec + ADR rewrite, status → re-proposed, supersedes old version." Estimated ~25-40 minutes each.

### Priority 1 — blocking F001 implementation

1. **F001 spec + ADR rewrite**
   - Old framing: "Introduce ConstructionMethod as a new core entity"
   - New framing: "Promote kitchen-plugin's `cabinet_geometry.py` defaults to a `ConstructionMethod` registry; `CabinetGeometry` constructor takes a method argument."
   - File of record changes from `src/kuchnie_core/construction.py` to:
     - `src/kuchnie_core/construction/method.py` — `ConstructionMethod` dataclass + registry
     - `kitchen-plugin/src/kitchen/cabinet_geometry.py` — modify constructor to accept `ConstructionMethod`
   - Status: `proposed-v2`; old ADR superseded.

2. **F007 ADR rewrite** (do this in the same commit as F001 since the bounded-context map shifts)
   - Old framing: "Build `kitchen-render/` standalone bpy renderer."
   - New framing: "Adopt `kitchen-plugin/` as the render + geometry subsystem. F007 work = (a) move Layer 1+2 from `kitchen-plugin/src/{core,kitchen}/` to `src/kuchnie_core/`, (b) wire `MaterialResolver` into `material_manager.py`, (c) add render presets (camera, HDRI, multi-view)."
   - F007 ADR Alt A,B,C still apply (don't pip install bpy, don't drive home_builder_5/) — re-cite them, mark as still rejected.
   - F007 status `supersedes` field expanded to include this entire integration plan.

### Priority 2 — blocking F002 / F004 implementation

3. **F002 spec + ADR rewrite**
   - Old framing: "Build RecipeEngine in CAD; recipes in YAML; emit Panel."
   - New framing: "Extract `kitchen-plugin/src/geometry_builder._build_cabinet()` per-type branches into YAML recipes. `RecipeEngine` (in Core) takes a `Cabinet` + `ConstructionMethod`, returns `list[Panel]`. `geometry_builder` becomes thin: consumes `list[Panel]`, emits bpy objects."
   - **No new bounded context** — recipes live in Core, evaluation engine lives in CAD as planned. But the *source material* (what to extract) is now kitchen-plugin's Python code, not blank slate.

4. **F004 spec + ADR rewrite**
   - Old framing: "Build 4 validation gates from scratch."
   - New framing: "Wrap kitchen-plugin's `validators.py` and `manifest_validator.py` into the 4-gate API. Promote `Issue` to carry `code: str`. Cabinet + Kitchen gates wrap existing checks; Row + CAM gates are new."
   - Reserve codes KIT-100, CAM-100 for F005 — unchanged.

### Priority 3 — Once F001-F002-F004 are stable

5. **F003 spec + ADR refresh** (less rewriting; mostly add cross-references)
   - kitchen-plugin's `CabinetType` enum + `config_parser` validation maps 1:1 to F003 templates. Each enum value gets a YAML.
   - Sub-assemblies (`door`, `shelf_bank`, `drawer_stack`) are new conceptual layer over kitchen-plugin's flat structure.

6. **F008 spec + ADR refresh**
   - kitchen-cli's `render` subcommand wraps `python -m kitchen_plugin.main` (or imports `main()` directly).
   - All other subcommands are net-new as before.
   - MachiningFeature still net-new — kitchen-plugin doesn't compute machining patterns.

### Not affected

- **F005 (Material Resolver)** — entirely net-new work; no rewrite needed beyond the `_color` edge convention already added.
- **F006 (Web Sidebar)** — entirely net-new; planning still pending.
- **GLOSSARY.md** — needs ~30 entries cross-referenced to `kitchen-plugin/src/...::ClassName` files. Most updates are mechanical: replace TBD with real paths.

---

## 7. Documentation Cleanup (after Priority 1-2)

1. **Add Rule 8** to `00_LLM_NAVIGATION.md`: "Before proposing any geometry, construction, validation, or rendering code, **`find kitchen-plugin/src -name '*.py'`** first. Pattern-match by directory name has failed once already (see `06_kitchen_plugin_discovery.md`)."
2. **Update `01_architecture.md`** — Context Map shows kitchen-plugin as a peer of kitchen-cad/kitchen-app.
3. **Update `03_implementation_placement.md`** — each pattern's verdict updated to "see kitchen-plugin for existing implementation; F00X extracts/wraps it."
4. **Update `04_solo_dev_process.md`** — add the pre-planning checklist: `find . -name '*.py' | wc -l` on every candidate context, `pysum` on anything > 500 LOC.
5. **Update `PHASES.md` Phase 7** — replace "build new renderer" with "adopt + integrate kitchen-plugin."
6. **Resolve legacy `kuchnie/docs/adr/001-008`** — re-status each:
   - 001 panel-is-atomic-unit — **partially done** (kitchen-plugin builds boards but doesn't expose them as a `Panel` model)
   - 002 construction-method-separation — **planned** (F001 will do this; kitchen-plugin has the constants but not the swap mechanism)
   - 003 kitchen-as-unit-of-work — **done** (kitchen-plugin already treats the kitchen as a unit)
   - 004 intermediate-format-is-logical — **done** (manifest.json + config.json)
   - 005 machining-op-model — **not done** (kitchen-plugin doesn't generate machining ops)
   - 006 legrabox-lw-formula — **probably in `kuchnie_core/legrabox.py`** — needs audit
   - 007 drawer-box-material-spec — **partially done** (kitchen-plugin draws drawer fronts; doesn't model drawer-box separately)
   - 008 material-master-catalog — **not done** (F005 is this)

---

## 8. What Doesn't Change

- **Rule 4** still holds: `home_builder_5/` is untouched. (Demoted from "renderer we feed" to "reference only.")
- **F005's role → slot → decor chain** — unaffected; F005 is net-new.
- **F006 web sidebar** — unaffected; net-new.
- **F008's MachiningFeature, DrillPattern YAMLs, PatternResolver** — unaffected; net-new.
- **The five (or six) architectural patterns we stole from PRO100/Polyboard/Winner Flex/TopSolid'Wood/PaletteCAD** — all preserved. Each becomes a *refactor target* on kitchen-plugin rather than a new build.

---

## 9. Open Questions for User

1. **Naming:** OK with keeping `kitchen-plugin/` as the directory name, or rename to `kitchen-render/`? (Functional impact zero; cosmetic only. I'd lean toward keeping the existing name to avoid pointless churn — but the docs will need to clarify it's *not* a Blender addon despite the name.)

2. **Layer 1+2 promotion:** Confirm choice **B** from § 4 — promote `kitchen-plugin/src/{core,kitchen}/` into `src/kuchnie_core/`? This is the cleanest dependency direction but touches a lot of imports in kitchen-plugin's 22 tests. (Option A — leave them where they are and have `kuchnie_core` import from `kitchen-plugin.kitchen` — is less migration work but inverts the natural "core is foundational" rule.)

3. **JSON → YAML migration:** Configure `config_parser.py` to accept both JSON and YAML in v1.2, deprecate JSON in v1.3, remove JSON in v2.0? Or hard cut to YAML now and migrate the 8 existing JSON test fixtures?

4. **Legacy ADR resolution:** Should I rewrite the legacy `kuchnie/docs/adr/001-008` to current-state status, or leave them historical and only reference them from the new ADRs?

5. **CHANGELOG:** kitchen-plugin has its own `CHANGELOG.md` with an `[Unreleased]` "DDD strategic design" section. Should our integration work be tracked in that CHANGELOG (kitchen-plugin's), in `kuchnie/CHANGELOG.md` (project root, exists), or both?

6. **Test consolidation:** kitchen-plugin has 22 tests; `kuchnie/tests/` has 7. Consolidate into a single `kuchnie/tests/` with subfolders, or keep distinct?

---

## 10. Summary

> **Option A confirmed. The "gold" from F001-F008 is fully preserved — it just changes from "build new" to "refactor kitchen-plugin's hardcoded knowledge into the data-driven registries F1-F4 designed." F5, F6, F8 are still mostly net-new. F7's scope dramatically shrinks to integration work.**
>
> **Estimated rewrite effort:** ~3 hours for Priority 1 (F001 + F007 specs/ADRs) and Priority 2 (F002 + F004). Priority 3 (F003 + F008 refresh) ~1 hour. Documentation cleanup ~1 hour. Total: **~5 hours of doc work** before any new code is written, but **6+ weeks of code work saved** vs Options B and C.
>
> **Next action requested:** Answer the 6 Open Questions in § 9, then I will execute the rewrites in priority order.
