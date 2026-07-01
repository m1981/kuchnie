# Full Ground-Truth Audit — 2026-06-29

> **What the user asked:** Run `lsproj | grep -v tests | pysum --pipe` and follow execution flow for each folder to check what's really implemented.
>
> **Bottom line:** The project is **six parallel implementations** of overlapping concepts (~37,000 LOC across 200+ Python files), built as separate experiments with **ZERO cross-context imports**. Every major concept in F001-F008 has 2–4 working implementations across different subsystems, in different paradigms (dataclass/Pydantic/SQLModel/Reflex/FastAPI/bpy), with no agreed-upon canonical version.
>
> **The previous planning (F001-F008 specs) treated this as a greenfield design exercise. That framing is fundamentally wrong.** This is a **consolidation project**, not a feature-development project.
>
> This document is the honest reset. It supersedes parts of docs 06, 07, 08, 09 by going wider — the previous discoveries (`kitchen-plugin/`, `krono-compositor-mvp/`) were correct as far as they went, but only revealed 2 of the 6 mature subsystems.

---

## 1. Method

```bash
cd /Users/michal/PycharmProjects/kuchnie
lsproj | grep -v "tests"           # 149 source files
lsproj | grep -v "tests" | pysum --pipe > /tmp/kuchnie_full_pysum.md
```

Then read every `## file.py` heading in the pysum output. Then check cross-context imports:

```bash
grep -rln "from kuchnie_core" kitchen-app/ kitchen-cad/ kitchen-plugin/ krono-compositor-mvp/
# Result: ZERO matches. Every subsystem is fully standalone.
```

---

## 2. The Six Subsystems — Full Mapping

### 2.1 `src/kuchnie_core/` — 1,954 LOC — "the manufacturing heart"

Per `pyproject.toml`: `name = "kuchnie-core"`, `description = "Kitchen cabinet decomposition engine — the manufacturing heart"`. This is **declared** as the project root package, but in practice nothing else imports from it.

**Files:**

```
src/kuchnie_core/
├── model.py          Kitchen, Row, CabinetInstance, Panel, EdgeBand,
│                     MachiningOp, Accessory, WorktopSegment, GrainAxis,
│                     DecompositionResult.  ALL dataclasses (not Pydantic).
├── decomposer.py     decompose(cab) → DecompositionResult.
│                     Dispatches via catalog.TYPE_REGISTRY[cab.type].
├── catalog.py        Three hardcoded Polish-named decomposers:
│                     decompose_dolna_szufladowa (lower drawer cab),
│                     decompose_gorna_drzwiowa  (upper door cab),
│                     decompose_dolna_legrabox  (lower legrabox cab).
│                     TYPE_REGISTRY: dict mapping cab type → function.
├── legrabox.py       Full Blum Legrabox drawer math:
│                     lw(kb), back_panel_width, base_panel_width,
│                     drawer dimensions, height validation, capacity
│                     validation, decompose_drawer_box, make_runner_accessory.
│                     ~MATURE for Legrabox specifically.
├── bom.py            BOM, BOMItem, calculate_bom(result, board_prices,
│                     edge_prices). Simple aggregation.
├── kitchen.py        decompose_kitchen, all_panels, all_accessories,
│                     kitchen_bom, validate_rows.
├── loader.py         load_cabinet, load_kitchen (YAML).
├── serialize.py      Kitchen ↔ JSON. Comment: "THE contract between
│                     kitchen-plugin, render-service, and kitchen-cli."
│                     (Aspirational — nobody actually uses this contract.)
├── export/
│   └── cutlist_csv.py CutPiece, aggregate_panels, export_cutlist_csv.
└── materials/        ★ NEW DISCOVERY — F005 is partially built here ★
    ├── protocol.py      MaterialCatalog Protocol
    ├── models.py        VariantInfo, EdgeInfo, WorktopInfo, PropertyFlag,
    │                    AvailabilityInfo
    ├── resolver.py      MaterialResolver (the F005 class we planned)
    ├── sqlite_repository.py  SqliteMaterialCatalog implementation
    └── exceptions.py    MaterialCatalogError, MaterialNotFoundError, etc.
```

**Status:** A working decomposer engine with three Polish cabinet types, full Legrabox math, BOM aggregation, CSV cut list export, and a partial F005 MaterialResolver with SQLite implementation. **Pure Python + PyYAML; no SQLModel, no Reflex, no Pydantic.**

**Test fixtures referenced:** `fixtures/G01.yaml`, `K01.yaml`, `K02_legrabox.yaml`, `kitchen_01.yaml`.

### 2.2 `catalog/` — 7,841 LOC — "full FastAPI catalog service"

A complete tiered web service:

```
catalog/
├── api/
│   ├── main.py                FastAPI app with CORS + lifespan + static
│   ├── deps.py                SQLite connection injection
│   └── routers/
│       ├── decors.py          GET /decors (filtered + paginated),
│       │                      /decors/{id}, /decors/{id}/variants,
│       │                      /decors/{id}/pairings
│       ├── producers.py       GET /producers
│       ├── worktops.py        GET /worktops (filtered)
│       ├── availability.py    GET /availability (filtered by channel/producer)
│       └── admin.py           GET /admin/stats, /admin/full_catalog
├── models/
│   └── domain.py              Pydantic output models: ProducerOut,
│                              DecorSummary, VariantOut, DecorWithVariants,
│                              PairingOut, WorktopOut, AvailabilityOut,
│                              PaginatedResponse, StatsOut.
├── repositories/              SQLite DAOs:
│   ├── decor_repo.py          DecorRepository with filter+paginate
│   ├── pairing_repo.py        PairingRepository
│   ├── worktop_repo.py        WorktopRepository
│   └── availability_repo.py   AvailabilityRepository
├── db/
│   ├── engine.py              get_connection, init_schema
│   └── schema.sql             Full DB schema (separate file)
├── scripts/
│   ├── importer.py            CatalogImporter: imports producers,
│   │                          structures, collections, materials, decors,
│   │                          variants, worktops, pairings, availability,
│   │                          property_flags from YAML → SQLite.
│   ├── seed.py                CLI: load YAML → init schema → import
│   ├── generate_kronospan_yaml.py    Generates kronospan_full.yaml from
│   │                                 source data
│   └── generate_kronoswiss_yaml.py   Same for Kronoswiss
├── data/
│   ├── kronospan_full.yaml    Real Kronospan catalog data
│   ├── kronospan_sample.yaml  Subset for tests
│   └── kronoswiss_full.yaml   Real Kronoswiss catalog data
├── db/catalog.db-wal          Live SQLite DB (currently has data)
└── docs/architecture/
    ├── 02-pydantic-models.py  Reference Pydantic models (not imported, but
    │                          the canonical design):
    │                          Producer, MaterialType, Collection, Structure,
    │                          Material, Decor, Edge, Variant, Pairing, Tag,
    │                          + enums: MaterialTypeSlug, Role, PairingType,
    │                          MatchType, Sidedness, StructureType,
    │                          StructureFinish
    │                          + YAML projection models: YamlVariant,
    │                          YamlDecor, YamlDecorsFile
    └── 03-fastapi-design.py   PairingResolutionLogic, SearchLogic,
                               StatisticsLogic — design exploration
```

**Status:** A production-grade FastAPI catalog service with real Polish material data (Kronospan + Kronoswiss), full CRUD via repositories, REST API exposing producers/decors/variants/pairings/worktops/availability/admin endpoints. **This IS F005's catalog. Built. Running.**

**Stack:** Python 3.12, FastAPI, SQLite (raw `sqlite3` module + parameterized queries — not SQLAlchemy), Pydantic. Has its own `pyproject.toml`.

### 2.3 `kitchen-app/` — 6,790 LOC — "Reflex web app + ERP"

A complete two-tier Reflex application:

```
kitchen-app/
├── rxconfig.py                Reflex config
├── kitchen_app/               UI layer (Reflex pages + state)
│   ├── kitchen_app.py         Pages: top_bar, cabinet_2d_box, plan_module_box,
│   │                          main_canvas, action_bar, sidebar, cost_trace_panel,
│   │                          index. Real working 2D configurator.
│   ├── state.py               KitchenState (rx.State):
│   │                          - cabinets, rows, layouts
│   │                          - add_cabinet, move_cabinet, delete_cabinet
│   │                          - add_equipment
│   │                          - select_cabinet, update_cabinet_field
│   │                          - load_ikea_layout, load_mock_data
│   │                          - change_global_front, change_local_front
│   │                          - open_*_cost_trace, _format_cost_trace_line
│   │                          - _relayout_ordered_row, _relayout_project
│   │                          - row siblings management, anchor overlays
│   ├── admin_state.py         AdminState (rx.State):
│   │                          - load/save/delete: Material, HardwareSet,
│   │                            HardwareRule (full admin CRUD)
│   │                          - initialize_default_rules
│   └── admin_ui.py            material_row, hardware_row, hardware_rule_row,
│                              material_form, hardware_form, hardware_rule_form,
│                              admin_page
├── kitchen_erp/               Domain layer (SQLModel ORM + business logic)
│   ├── models.py              SQLModel ORM:
│   │                          - Material, HardwareSet, HardwareRule,
│   │                            ProjectDefaults
│   │                          - Cabinet (has has_custom_front,
│   │                            local_front_mat, calculate_cost methods)
│   │                          - Project (has generate_project_bom method)
│   ├── database.py            SQLite session via SQLModel
│   ├── schemas.py             Pydantic:
│   │                          - BOMNode, BOMPart, BOMAssembly (tree structure
│   │                            with .calculate() method)
│   │                          - CostTraceLine, CabinetCostResult
│   ├── bom_generator.py       BOMGenerator(cabinet, defaults):
│   │                          - .generate() → BOMAssembly
│   │                          - .generate_cost_trace_lines()
│   ├── recipe_loader.py       ★ F002 partial implementation ★
│   │                          - load_recipes() — loads JSON recipes
│   │                          - get_recipe(recipe_id)
│   │                          - get_recipe_tags(recipe_id)
│   │                          - eval_formula(formula, dims) — formula
│   │                            evaluator with dimension substitution
│   │                          - clear_recipe_cache()
│   ├── rules_engine.py        RulesEngine:
│   │                          - apply_rules(tags, assembly, multipliers)
│   │                          - get_required_hardware_for_tags(tags)
│   │                          - get_default_hardware_rules, load from DB
│   └── purchasing.py          ★ F008 cost-estimate partial implementation ★
│                              PurchasingStrategy (ABC):
│                              - SheetMaterialStrategy (sheet rounding,
│                                grain-aware waste factor)
│                              - LinearMaterialStrategy (roll length)
│                              - CountertopStrategy (standard length)
│                              - ExactQuantityStrategy (waste factor)
│                              - get_strategy_for_material(category)
├── examples/
│   └── demo_bom_system.py     End-to-end demo: create_demo_database,
│                              demo_recipe_system, demo_bom_generation,
│                              demo_rules_engine, demo_purchasing_strategies,
│                              demo_old_vs_new_comparison.
│                              (The "old vs new" suggests an in-progress
│                              migration between two BOM implementations.)
├── scripts/
│   └── validate_migration.py  check_recipe_coverage, compare_costs,
│                              generate_report — migration validation
└── database.db                Live SQLite DB
```

**Status:** A working 2D kitchen configurator with admin panel, BOM cost trace, rules engine for auto-adding hardware, purchasing strategies for waste calculation. **F003 + F006 + parts of F002 + parts of F008 are already implemented here.**

**Stack:** Python 3.12, Reflex, SQLModel (SQLAlchemy-based ORM), Pydantic, SQLite.

### 2.4 `kitchen-cad/` — 6,902 LOC — "CAD/CAM output engine"

A complete CSV/DXF/drill-pattern generation pipeline:

```
kitchen-cad/
├── src/kitchen_cad/
│   ├── models.py              ★ F003 + F008 model layer ★
│   │                          Enums: CorpusType, PanelRole, EdgeSide,
│   │                          DrillFace, DrillType, CornerSide, CarouselType,
│   │                          CargoType.
│   │                          Constants: SYSTEM32_OFFSET, SYSTEM32_SPACING.
│   │                          Models (Pydantic, with validators):
│   │                          - Panel
│   │                          - EdgeBand
│   │                          - DrillPoint
│   │                          - HingeSpec, DrawerSpec, HandleSpec
│   │                          - BaseDoorConfig, BaseDrawerConfig,
│   │                            CornerBlindConfig, CornerInternalConfig,
│   │                            SinkConfig, CargoConfig, OvenConfig
│   │                          - CorpusSpec (has _sync_config_from_legacy,
│   │                            *_resolved properties)
│   ├── panel_calculator.py    ★ F002 RecipeEngine — already implemented ★
│   │                          calculate_panels(spec) → list[Panel]
│   │                          Per-cabinet-type:
│   │                          - _calculate_base_door
│   │                          - _calculate_base_drawer
│   │                          - _calculate_corner_blind
│   │                          - _calculate_corner_internal
│   │                          - _calculate_sink
│   │                          - _calculate_cargo
│   │                          - _calculate_oven
│   │                          Building blocks:
│   │                          - _side_panels, _horizontal_panels,
│   │                            _shelf_panels, _back_panel,
│   │                            _door_fronts, _drawer_fronts
│   │                          IMPERATIVE PYTHON (like kitchen-plugin) —
│   │                          NOT YAML recipes as F002 ADR planned.
│   ├── drill_engine.py        ★ F008 PatternResolver — already implemented ★
│   │                          - system32_y_positions(height)
│   │                          - _shelf_pin_offsets, _get_shelf_positions
│   │                          - _get_door_hinge_counts
│   │                          - apply_system32(panels, spec)
│   │                          - _hinge_positions, apply_hinges
│   │                          - apply_handles
│   │                          - apply_all_drilling
│   └── csv_generator.py       ★ F008 CSV exporters — already implemented ★
│                              - generate_cutting_csv(panels, path)
│                              - generate_edging_csv(panels, path)
│                              - _edge_length(panel, edge)
├── generators/
│   └── legrabox_side_panel.py ★ F008 DXF exporter — partially started ★
│                              ezdxf-based:
│                              - generate_side_panel_dxf
│                              - add_outline, add_system32_holes,
│                                add_legarabox_profile_holes,
│                                add_dowel_holes, add_edgebanding_marks,
│                                add_dimensions_and_notes
│                              - DXF layers, dimensions, notes
│                              ONLY does Legrabox side panel; needs
│                              extension to all panel types.
└── example_generate.py        E2E demo: build configs → calculate_panels →
                               apply_all_drilling → generate_cutting_csv +
                               generate_edging_csv
```

**Status:** F002 (decomposition) + F008's CSV exporters fully implemented imperatively per-cabinet-type. F008's drill pattern engine works. F008's DXF exporter started (Legrabox-only). Has its own complete Pydantic model layer that doesn't share types with kuchnie_core.

**Stack:** Python 3.12, Pydantic, ezdxf (DXF library).

### 2.5 `kitchen-plugin/` — 10,727 LOC — "3D engineering renderer"

(Detailed analysis in doc 06; key points repeated here.)

```
kitchen-plugin/
├── src/
│   ├── core/                 Pure math: Vector2D/3D, BoundingBox, Transform2D,
│   │                         Direction, CabinetType, CabinetLevel, HandleType,
│   │                         DoorSide, Dimensions
│   ├── kitchen/              Domain: Cabinet, CabinetPlacement, Countertop,
│   │                         Wall, Room, CornerReference, Run, Layout,
│   │                         LayoutEngine, CabinetGeometry, KitchenStandards
│   ├── config_parser.py      JSON loader + validation + run-position calc
│   ├── validators.py         Config-level checks
│   ├── wall_builder.py       config → domain Layout
│   ├── geometry_builder.py   bpy mesh construction (per-cabinet-type)
│   ├── geometry_manifest.py  Post-build manifest JSON
│   ├── material_manager.py   bpy Cycles materials (RGB only)
│   ├── manifest_validator.py Post-build validation (Issue, ValidationResult,
│   │                         dimension/overlap/clearance/standard-width/
│   │                         construction checks)
│   ├── exporters.py          .blend save, wireframe render
│   └── main.py               CLI: blender --background --python main.py --
│                             config.json [--validate --export-blend ...]
└── configs/*.json            Test layouts (i-shape, l-shape, u-shape, ref_*)
```

**Status:** As doc 06. The 3D engineering renderer + cabinet geometry library.

### 2.6 `krono-compositor-mvp/` — 1,341 LOC — "2.5D live compositor"

(Detailed analysis in doc 09; key points repeated here.)

```
krono-compositor-mvp/
├── gen_kitchen.py            446 LOC — Blender 5-pass renderer (independent
│                             from kitchen-plugin)
├── main.py                   FastAPI entry
├── src/compositor/
│   ├── domain/interfaces.py        Protocol contracts
│   ├── infrastructure/opencv_impl.py OpenCV implementations
│   ├── application/scene_compositor.py SceneCompositor.render_scene()
│   └── presentation/
│       ├── api.py                  GET /catalog, POST /render
│       ├── schemas.py              ZoneRequest, RenderRequest, ZoneType,
│       │                           AllowedZone
│       └── catalog_db.py           Hardcoded Polish materials (dab_szlachetny,
│                                   marmur_bianco, zielony_kamienny, ...)
├── layout.json                 Compositor's input format (flat cabinet list)
├── static/index.html           Alpine.js + Tailwind demo frontend
└── assets/                     Cached render passes + texture JPEGs
```

**Status:** As doc 09. The 2.5D real-time material compositor.

---

## 3. Cross-Context Imports — The Key Discovery

```bash
$ grep -rln "from kuchnie_core" kitchen-app/ kitchen-cad/ kitchen-plugin/ krono-compositor-mvp/
(empty — zero matches)

$ grep -rln "from catalog" kitchen-app/ kitchen-cad/ kitchen-plugin/ krono-compositor-mvp/
(empty — zero matches)

$ grep -rln "from kitchen_cad\|from kitchen_app\|from kitchen_plugin\|from compositor" \
       src/ catalog/ kitchen-app/ kitchen-cad/ kitchen-plugin/ krono-compositor-mvp/
(only matches: each subsystem importing its own modules)
```

**Every subsystem is fully standalone. There are zero cross-context imports.**

This is "polyrepo-within-a-repo" — six independent prototypes that happen to share a parent directory. They were built as separate experiments exploring different paradigms:

- **kuchnie_core:** dataclass-based pure Python + Polish-named decomposers
- **catalog:** FastAPI + raw SQLite + Pydantic + repositories
- **kitchen-app:** Reflex + SQLModel + recipe formulas + rules engine
- **kitchen-cad:** Pydantic + imperative panel calculator + ezdxf
- **kitchen-plugin:** bpy + dataclasses + DDD layered architecture
- **compositor:** FastAPI + OpenCV + Alpine.js

---

## 4. The Massive Duplication Map

| Concept | `kuchnie_core` | `catalog` | `kitchen-app` | `kitchen-cad` | `kitchen-plugin` | `compositor` |
|---|---|---|---|---|---|---|
| **Cabinet model** | `CabinetInstance` (dataclass) | — | `Cabinet` (SQLModel) | `CorpusSpec` (Pydantic) | `Cabinet` (dataclass) | — |
| **Panel model** | `Panel` (dataclass) | — | `BOMPart` (Pydantic, different concept) | `Panel` (Pydantic) | (emits bpy.Object) | — |
| **Recipe / decomposition** | `catalog.py` (3 Polish funcs) + `legrabox.py` | — | `recipe_loader.py` + `eval_formula` | `panel_calculator.calculate_panels` (imperative per-type) | `geometry_builder._build_cabinet` (imperative per-type) | — |
| **Material catalog** | `materials/` (Protocol + SqliteImpl) | **the canonical one** — FastAPI + SQLite + YAML data | `kitchen_erp/models.py::Material` (SQLModel) | (none) | (RGB color in config) | `catalog_db.py` (hardcoded Python dict) |
| **BOM / cost** | `bom.py::calculate_bom` | — | `bom_generator.py::BOMGenerator` + `purchasing.py` strategies | (none) | (none) | (none) |
| **Drilling / machining** | `model.py::MachiningOp` + `legrabox.py` ops | — | (none) | `models.py::DrillPoint` + `drill_engine.py` (System32, hinges, handles) | (only back-panel groove via `cabinet_geometry`) | (none) |
| **Layout / runs** | `model.py::Row` | — | `state.py` row management | — | `Run` + `Layout` + `LayoutEngine` | — |
| **YAML / config loader** | `loader.py::load_kitchen` | `importer.py::CatalogImporter` | `recipe_loader.py::load_recipes` (JSON, not YAML) | (none) | `config_parser.py::load_config` (JSON) | (reads `layout.json` inline) |
| **CSV / DXF export** | `export/cutlist_csv.py` | — | (none) | `csv_generator.py` + `generators/legrabox_side_panel.py` (DXF) | (none) | (none) |
| **Material resolver** | `materials/resolver.py::MaterialResolver` | (catalog provides data via API) | `rules_engine.py` (different — for hardware) | (none) | (none) | (none — just maps texture_id) |
| **Polish-market knowledge** | Polish cabinet names (`dolna_szufladowa` etc.) | Polish decor data (Kronospan, Kronoswiss) | — | (English; cabinet configs are abstract) | (English) | Polish material names (`dab_szlachetny` etc.) |

**Count:** every concept on this list is duplicated in 2–4 subsystems, in different paradigms, with no shared types.

---

## 5. The F001-F008 Planning vs Reality

| Feature | What F00X spec planned | What actually exists |
|---|---|---|
| **F001 — ConstructionMethod** | Build a registry of swappable construction methods | Hardcoded constants in `kitchen-plugin/src/kitchen/cabinet_geometry.py`. `kitchen-cad/src/kitchen_cad/models.py::CorpusSpec` accepts thickness fields too. `kuchnie_core/legrabox.py` has its own thickness assumptions. **3 places.** None swappable. |
| **F002 — Recipe Engine** | YAML recipes evaluated by asteval | `kuchnie_core/catalog.py` (Polish-named imperative Python) + `kitchen-cad/panel_calculator.py` (imperative Python per-type) + `kitchen-plugin/geometry_builder._build_cabinet` (imperative Python per-type) + `kitchen-app/kitchen_erp/recipe_loader.py` (JSON recipes with `eval_formula`). **4 implementations.** None YAML. Three imperative. |
| **F003 — Template Registry** | YAML cabinet templates | `kitchen-cad/models.py` has BaseDoorConfig, BaseDrawerConfig, CornerBlindConfig, SinkConfig, CargoConfig, OvenConfig as Pydantic models (acts as templates). `kitchen-plugin` has `CabinetType` enum. **Templates exist as code, not data.** |
| **F004 — Validation Gates** | 4 gates with codes + reserved pattern | `kitchen-plugin/manifest_validator.py` has Issue + ValidationResult + 6 check functions. `kitchen-plugin/validators.py` has config-level checks. `kuchnie_core/kitchen.py::validate_rows` exists. `kitchen-app` has implicit validation via SQLModel constraints. `kitchen-cad/models.py` has Pydantic validators. **Validation exists but scattered across 5 places; no code registry.** |
| **F005 — Material Resolver** | Build catalog + resolver chain | `catalog/` IS the catalog service (FastAPI + SQLite + YAML data for Kronospan + Kronoswiss). `src/kuchnie_core/materials/` has `MaterialResolver` + `MaterialCatalog` Protocol + `SqliteMaterialCatalog`. `compositor/catalog_db.py` has Polish materials. `kitchen-app/kitchen_erp/models.py::Material` has SQLModel records. **4 catalogs; the F005 resolver is partially built.** |
| **F006 — Web Sidebar** | Build Reflex sidebar | `kitchen-app/` is a full working Reflex app with 2D configurator, cabinet sidebar, admin panel, cost trace. **F006 is the most-complete feature already.** |
| **F007 — Blender Adapter** | Build kitchen-render/ | `kitchen-plugin/` is the 3D renderer (mature). `compositor/` is the 2.5D renderer (mature). **Both exist.** |
| **F008 — CLI Cut List / DXF / Cost** | `kitchen-cli` binary with subcommands | `kitchen-cad/example_generate.py` does E2E cut-list + drill + edging. `kitchen-cad/csv_generator.py` exports cutting + edging CSVs. `kitchen-cad/drill_engine.py` does System32, hinges, handles. `kitchen-cad/generators/legrabox_side_panel.py` does DXF for Legrabox side. `kitchen-app/kitchen_erp/purchasing.py` does cost. **Most of F008 is in kitchen-cad + kitchen-app, just not wrapped in a `kitchen-cli` binary.** |

**Verdict:** Every feature in F001–F008 has a working implementation somewhere. **The problem is not "build the features." The problem is "they don't agree with each other."**

---

## 6. Why The Previous Planning Was Wrong

The F001–F008 specs were written treating the project as **greenfield**. They asked: "What should we build?"

The actual question is: **"Which of the 2–4 existing implementations of every concept should win, and how do we consolidate?"**

These are **different problems**. The first produces architectural specs. The second produces migration plans, deduplication ADRs, and integration tasks.

Even after I caught `kitchen-plugin/` (doc 06) and `krono-compositor-mvp/` (doc 09), the planning was still incomplete — `catalog/`, `kitchen-app/`, and `kitchen-cad/` are each individually larger than `kuchnie_core/`, and each one re-implements concepts the previous planning treated as TBD.

---

## 7. The Six-Subsystem Strengths (What To Keep)

Each subsystem has done something well that the others haven't. **A good consolidation preserves the strongest implementation per concept.**

| Concept | Strongest implementation | Why |
|---|---|---|
| **Material catalog data + API** | `catalog/` | Production-grade service, real Kronospan + Kronoswiss data, full filter/paginate API, importer pipeline |
| **Material resolver** | `kuchnie_core/materials/` | Protocol-based, clean separation, has SQLite implementation |
| **Cabinet decomposition (recipe)** | `kitchen-cad/panel_calculator.py` | Most cabinet types supported (base-door, base-drawer, corner-blind, corner-internal, sink, cargo, oven), Pydantic-typed Panel output, integrates with drill engine |
| **Drilling / machining** | `kitchen-cad/drill_engine.py` | Has System32 + hinges + handles + Legrabox-specific. Best Pattern resolver in the project. |
| **Legrabox-specific math** | `kuchnie_core/legrabox.py` | Most detailed Legrabox formulas (lw, back_panel_width, drawer dims, validations) |
| **CSV export** | `kitchen-cad/csv_generator.py` | Has both cutting + edging CSV. `kuchnie_core/export/cutlist_csv.py` is older. |
| **DXF export** | `kitchen-cad/generators/legrabox_side_panel.py` | Only DXF impl in the project; needs extension to all panel types |
| **BOM + cost** | `kitchen-app/kitchen_erp/bom_generator.py` + `purchasing.py` | Best — has cost trace, purchasing strategies, waste factors, sheet rounding. `kuchnie_core/bom.py` is simpler. |
| **Recipe formula evaluation** | `kitchen-app/kitchen_erp/recipe_loader.py` | Has `eval_formula(formula, dims)` — F002's asteval-ish design, but already working |
| **Rules engine (hardware auto-add)** | `kitchen-app/kitchen_erp/rules_engine.py` | The "material-configurator" rule engine F009 was supposed to design — already exists for hardware. Could be extended to materials. |
| **Web 2D configurator** | `kitchen-app/kitchen_app/state.py + kitchen_app.py` | Working Reflex app with rows, cabinets, sidebar, cost trace |
| **Admin UI** | `kitchen-app/kitchen_app/admin_*` | Full CRUD for materials + hardware + hardware rules |
| **3D engineering geometry** | `kitchen-plugin/src/kitchen/cabinet_geometry.py + kitchen/layout.py` | Best Cabinet/Wall/Room/Layout domain model in the project |
| **3D engineering render** | `kitchen-plugin/src/geometry_builder.py + main.py` | Mature bpy renderer with manifest output |
| **Post-build geometric validation** | `kitchen-plugin/src/manifest_validator.py` | Only impl that checks built geometry against expected |
| **2.5D real-time render** | `krono-compositor-mvp/` | Two-phase architecture, ~500ms iteration, FastAPI service |
| **Pure-Python domain types** | `kitchen-plugin/src/{core,kitchen}/` | Cleanest layering, frozen dataclasses, no framework deps |
| **Workflow types (Kitchen, Run, Layout)** | `kitchen-plugin/src/kitchen/` | Best — has runs, walls, rooms, corners |

---

## 8. Each Subsystem's Weaknesses (What To Drop)

| Subsystem | Weak / superseded parts |
|---|---|
| `kuchnie_core/catalog.py` | Three hardcoded Polish-named decomposers — superseded by `kitchen-cad/panel_calculator.py` which is broader |
| `kuchnie_core/model.py` | Dataclass-based; types are duplicated in Pydantic form in kitchen-cad. Decide on one paradigm. |
| `kuchnie_core/bom.py` | Simpler than `kitchen-app/kitchen_erp/bom_generator.py`. Drop in favor of the kitchen-app version. |
| `kuchnie_core/export/cutlist_csv.py` | Older than `kitchen-cad/csv_generator.py`. Drop. |
| `compositor/catalog_db.py` | Hardcoded; superseded by `catalog/` service. Should be projection from `catalog/` data. |
| `compositor/gen_kitchen.py` | Duplicates cabinet building done by `kitchen-plugin/geometry_builder.py`. Should delegate. |
| `kitchen-plugin/material_manager.py` | RGB-only; should consume `MaterialResolver.resolve_role` for textures. |
| `kitchen-plugin/configs/*.json` | JSON config format; the project is moving to YAML. Migration needed. |
| `kitchen-app/kitchen_erp/recipe_loader.py` JSON recipes | If F002 standardizes on YAML, these recipes need conversion. |
| `kitchen-cad/models.py::CorpusSpec` legacy sync | `_sync_config_from_legacy` indicates mid-migration; clean up. |
| **All of them:** standalone, no cross-imports | Must be wired together via shared kuchnie_core types |

---

## 9. The Right Strategy (Replacing The F001-F008 Plan)

The work is **NOT** "build F001 through F008." The work is:

### Phase 0 — Stop adding code (1 day)

**Freeze new code.** Cancel/pause the F001-F008 spec-rewrite effort I proposed in doc 07. Those specs would have added a 7th paradigm.

### Phase 1 — Decide canonical types (1 week)

For each row in the duplication map (§ 4), pick the winner. Write a one-page ADR per decision:

- ADR-C01: Which `Cabinet` wins? (Recommend: `kitchen-plugin/kitchen/cabinet.py::Cabinet` — cleanest, most tested. SQLModel records become a separate persistence concern.)
- ADR-C02: Which `Panel` wins? (Recommend: `kitchen-cad/models.py::Panel` — Pydantic, integrates with drill engine.)
- ADR-C03: Which recipe paradigm wins? (Recommend: extract `kitchen-cad/panel_calculator` per-type functions into YAML; reuse `kitchen-app/recipe_loader.eval_formula` evaluator.)
- ADR-C04: Which material catalog wins? (Easy: `catalog/` — only production-grade impl.)
- ADR-C05: Which BOM/cost wins? (Recommend: `kitchen-app/kitchen_erp/{bom_generator,purchasing}.py`.)
- ADR-C06: Which Layout/Run wins? (Easy: `kitchen-plugin/kitchen/layout.py::LayoutEngine`.)
- ADR-C07: Which validation paradigm wins? (Recommend: 4-gate registry in core (new wrapper) consuming `kitchen-plugin/manifest_validator` + `kitchen-cad/models.py` Pydantic validators.)
- ADR-C08: YAML vs JSON for kitchen config? (Recommend: YAML, with JSON loader kept for `kitchen-plugin/configs/*.json` test fixtures.)
- ADR-C09: How does `kuchnie_core` relate to the 5 other subsystems? (Recommend: kuchnie_core absorbs canonical types from kitchen-plugin's Layer 1+2 and becomes THE shared types library that all 5 others import.)

### Phase 2 — Wire subsystems via canonical types (2-3 weeks)

Concretely:

- Move `kitchen-plugin/src/{core,kitchen}/` into `src/kuchnie_core/{geometry,domain}/`. Update kitchen-plugin's 22 tests to import from new location.
- Move/refactor `kitchen-cad/src/kitchen_cad/models.py::Panel` to use kuchnie_core types where they overlap. Decide on dataclass vs Pydantic per type (recommend: dataclass for value objects in core, Pydantic for I/O boundaries).
- Make `kitchen-app/kitchen_erp/models.py::Cabinet` (SQLModel) a **persistence shadow** of the canonical `kuchnie_core.Cabinet` — i.e., kitchen-app loads from DB and converts to canonical Cabinet for any business logic.
- Migrate `kuchnie_core/catalog.py` Polish decomposers into kitchen-cad recipes (then delete).
- Migrate `compositor/catalog_db.py` to read from `catalog/` API or local YAML projection.
- Update `kitchen-plugin/material_manager.py` to use `kuchnie_core/materials/resolver.py::MaterialResolver`.
- Build `kitchen-cli` binary as a thin entry-point wrapping `kitchen-cad/{csv_generator, drill_engine}` + `kuchnie_core/{materials, kitchen}` + delegating `render` to `kitchen-plugin/main.py`.
- Decide the `catalog/` deployment: standalone FastAPI on port 8001 (called by everyone) OR direct in-process import. (Recommend: in-process for v1.0 — `from catalog.repositories.decor_repo import DecorRepository` — the FastAPI surface is kept for an admin tool but isn't required for runtime.)

### Phase 3 — Eliminate duplications (1 week)

- Delete `kuchnie_core/catalog.py` (Polish-named decomposers) after recipes migrated.
- Delete `kuchnie_core/bom.py` after BOMGenerator adopted.
- Delete `kuchnie_core/export/cutlist_csv.py` after kitchen-cad's superseded.
- Delete `compositor/catalog_db.py` after projection works.
- Delete `compositor/gen_kitchen.py` cabinet-building code (keep camera/lighting/pass setup) after delegating to kitchen-plugin.
- Decide the BOM "old vs new" migration in kitchen-app — finish it.
- Decide the `kitchen-cad/models.py::CorpusSpec._sync_config_from_legacy` migration — finish it.

### Phase 4 — Add genuine net-new (after consolidation)

After Phases 1-3, the genuinely new work that no subsystem covers:

- DXF for non-Legrabox panels (extend `kitchen-cad/generators/`)
- F009-equivalent material rule engine (extend `rules_engine.py` from hardware-only to also do materials, per `material-configurator/docs/00-overview.md`)
- Multi-view render presets for kitchen-plugin (per its own ROADMAP)
- Reconciliation between `kitchen-plugin/configs/*.json` schema and any YAML format chosen in ADR-C08

**This is roughly 6-9 weeks of consolidation work, not 8 weeks of feature work.**

---

## 10. What Happens To Docs 06-09

| Doc | Status | Action |
|---|---|---|
| 06 (kitchen-plugin discovery) | Correct on kitchen-plugin's existence, but underestimates the scope of what was already built elsewhere | **Keep**, mark superseded by doc 10 for the "what's already implemented" question. |
| 07 (integration plan) | Correct in spirit (adopt existing code) but wrong in scope — assumed only kitchen-plugin had real code | **Keep**, mark superseded by doc 10's Phase 0-4 plan. The 6 Open Questions in § 9 of doc 07 are still good — just expanded. |
| 08 (architecture diagram) | UC walks are still useful as mental models, BUT they assume a single coherent system that doesn't exist yet | **Keep**, but add a banner: "This is the TARGET architecture after consolidation. The current state is six standalone subsystems per doc 10." |
| 09 (compositor discovery) | Correct on compositor; correct on Seam A; correct on D1/D2 deduplications | **Keep**, fold into doc 10's bigger map. |

---

## 11. What Happens To F001-F008 Specs

Three options. **My strong recommendation: Option Y.**

### Option X — Rewrite F001-F008 specs to match existing code

For each spec, rewrite "Affected files" sections to point to existing implementations. Each spec becomes "promote concept X from <existing impl> to canonical".

**Pros:** Reuses spec-writing scaffolding.
**Cons:** F001-F008 was never the right unit of work. The real units are the ADR-C01..C09 decisions and the migration tasks they unlock. Forcing them into the F-spec mold is square-peg-round-hole.

### Option Y — Retire F001-F008 specs; replace with consolidation ADRs + migration tasks

Mark F001-F008 status as `superseded-by-consolidation`. Write 9 short ADR-C0X decisions (§ 9 Phase 1). Track migration as a numbered task list, not as features.

**Pros:** Maps cleanly to the actual work. Faster.
**Cons:** Throws away ~30 hours of spec-writing effort.

### Option Z — Hybrid: keep F005, F006, F008 as feature specs (they have net-new components); retire F001-F004, F007 as superseded

F001-F004 + F007 are conceptually correct but their "build from scratch" framing is wrong. F005 (catalog merger + resolver chain) and F008 (kitchen-cli + DXF expansion) have enough genuine new work to remain features. F006 (web sidebar) is mostly done already but could still be a feature for the remaining gaps.

**Pros:** Salvages the specs that still describe real net-new work.
**Cons:** Inconsistent — some specs survive, some don't.

---

## 12. Honest Process Failure Acknowledgement

I have, across this entire planning effort, repeatedly failed to do the one thing I should have done first: **`ls && find . -name "*.py" | wc -l` on every directory in the project root**. The pattern:

- Session 1: Wrote F001-F008 specs assuming greenfield.
- Session 2 (cold review): Caught `kitchen-plugin/` only because user said "look at home_builder_5/."
- Session 3 (this session): Caught `krono-compositor-mvp/` only because user asked about 2.5D.
- Session 4 (now): Caught `catalog/`, `kitchen-app/`, `kitchen-cad/` only because user said "run pysum on the whole project."

**Four sessions to find what one `ls` would have shown.** That is a systemic failure of the planning approach, not a one-off.

### Hard rules being added to `04_solo_dev_process.md`

```
RULE 0 (mandatory before any planning, no exceptions):
  1. ls $PROJECT_ROOT
  2. For every sibling directory (not just src/):
       find <dir> -name "*.py" -not -path "*/__pycache__/*" | wc -l
       find <dir> -name "*.py" -not -path "*/__pycache__/*" | xargs wc -l | tail -1
  3. For any directory with > 50 Python files OR > 1000 LOC:
       Read its README.md (if present), pysum its src/.
  4. For any directory whose name pattern-matches "plugin/external/legacy/scratch":
       Read README and pysum anyway. Names lie.
  5. grep -rln "from <other_subsystem>" across all subsystems to confirm
     whether they're integrated or standalone.
  6. ONLY THEN may you write any architectural document.

VIOLATING THIS RULE costs the solo dev hours per session of redirection.
```

---

## 13. Bottom Line

> **The project is six standalone parallel implementations with zero cross-context imports. Every concept in F001-F008 has 2-4 working implementations.** 
>
> **The right work for the next 6-9 weeks is consolidation (Phases 0-3 in § 9), not feature development.**
>
> **F001-F008 specs as written are wrong about scope.** Recommendation: retire them, replace with 9 short ADR-C0X decisions + a migration task list.
>
> **My process has failed four times to discover existing code before planning.** Mandatory pre-planning checklist now goes in `04_solo_dev_process.md` (§ 12 above).

### What I need from you

**Decision A — Strategy choice:**
- [ ] **Option Y** (retire F001-F008; replace with consolidation ADRs + migration plan). **Recommended.**
- [ ] **Option Z** (keep F005/F006/F008 as features; retire F001-F004/F007 as superseded). Lighter touch.
- [ ] **Option X** (rewrite F001-F008 to match existing code). Most conservative, least efficient.
- [ ] Something else (describe).

**Decision B — Priority order for ADR-C01..C09:**
Which canonical-type decisions matter most to lock in first? My ranking:
1. C04 (catalog) — easiest, biggest leverage
2. C09 (kuchnie_core's role)
3. C01 + C02 (Cabinet, Panel canonical types)
4. C03 (recipe paradigm)
5. C05 (BOM/cost)
6. Others later

**Decision C — Honest gut-check from you:**
Looking at the six-subsystem state with fresh eyes, **does this feel like:**
- (a) "Yes — I was exploring; consolidation is the right next phase." → proceed with Option Y
- (b) "Some of those are dead-ends I forgot about." → tell me which, I'll narrow the scope
- (c) "I want to start fresh from kuchnie_core and absorb only what I want." → very different plan (more like new build but informed by what works in each subsystem)

I will not write another planning doc until you answer Decision A. Apologies for the iterative discovery — the four-strikes pattern stops here.
