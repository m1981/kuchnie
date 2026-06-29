# Full Audit — Six Active Parallel Prototypes

> **The previous diagnosis was wrong.** It is not "kitchen-plugin is the foundation" (doc 06) or "kitchen-plugin + compositor are the two backends" (doc 09). The actual situation is **six independent prototypes** of the same system, each exploring a different facet, **none of them importing from each other**, all recently active.
>
> The F001–F008 planning was a *seventh* design — built without awareness that six partial implementations of the same domain already exist.
>
> This document inventories all six with cold execution-flow analysis, identifies what each prototype actually demonstrates, and reframes the project as a **domain unification** problem rather than a greenfield build.

---

## 1. The Six Prototypes — Activity Summary

| Prototype | Last Python edit | LOC | Tests | Status | Demonstrates |
|---|---|---|---|---|---|
| `catalog/` | **2026-06-29** (today) | 7,841 | 75+ JS + Python | 🟢 Active | Polish material catalog: 177 Kronospan decors, 22 SQLite tables, FastAPI, Vite frontend |
| `kitchen-app/` | 2026-05-12 | 6,790 | ~20 Python | 🟡 Recent | Reflex web UI + BOM/cost system: SQLModel, 15 JSON recipes, hierarchical BOM tree, rules engine, purchasing strategies |
| `kitchen-cad/` | 2026-06-24 | 6,902 | ~30 Python | 🟢 Active | CSV/DXF cut-list with System 32 drilling, hinge positioning, edge banding, 8 cabinet types (Polish names) |
| `kitchen-plugin/` | 2026-06-24 | 10,727 | 22 Python | 🟢 Active | 3D bpy renderer + DDD layered domain: Cabinet, Wall, Room, Layout, CabinetGeometry, manifest validator |
| `krono-compositor-mvp/` | 2026-06-22 | 1,341 | 4 test suites | 🟢 Active | 2.5D real-time compositor: 5-pass Blender bake + OpenCV composite + FastAPI, ~500ms iteration |
| `src/kuchnie_core/` | **2026-06-28** | 1,954 | 7 Python | 🟢 Active | Legacy decomposers (Polish: `dolna_szufladowa`, `dolna_legrabox`, `gorna_drzwiowa`) + Legrabox math + Materials Protocol/Resolver + YAML loader + CSV cutlist export |

**Every prototype is active.** Even `kitchen-app/` (oldest, May 12) is not abandoned — its `kitchen-app/.web/` Reflex artifacts are fresh.

**Cross-import audit (verified by grep):**
```
catalog/                  → imports: nothing from sibling prototypes
kitchen-app/              → imports: nothing from sibling prototypes
kitchen-cad/              → imports: nothing from sibling prototypes
kitchen-plugin/           → imports: nothing from sibling prototypes
krono-compositor-mvp/     → imports: nothing from sibling prototypes
src/kuchnie_core/         → imports: nothing from sibling prototypes
```

**ZERO cross-imports between subsystems.** Six islands.

---

## 2. Per-Prototype Cold Execution Flow

### 2.1 `catalog/` — Material Catalog Service

**Entry:** `catalog/api/main.py` (FastAPI app)

```
startup:
  ├─ open SQLite at catalog/db/catalog.db
  ├─ init_schema (22 tables)
  └─ register routers: producers, decors, worktops, availability, admin

GET /api/v1/decors?producer=kronospan&material_type=mdf
  ├─ DecorRepository.list_filtered(filters, page, page_size)
  │    SELECT * FROM decors JOIN producers JOIN material_types WHERE ...
  ├─ paginate
  └─ return PaginatedResponse[DecorSummary]

GET /api/v1/decors/{decor_id}
  ├─ DecorRepository.get_by_id(business_id)
  │    JOIN variants, structures, collections
  └─ return DecorWithVariants

GET /api/v1/decors/{decor_id}/pairings?pairing_type=edge
  └─ PairingRepository.get_for_decor(business_id) → list[PairingOut]

POST /api/v1/admin/stats  (admin)
  └─ aggregate decor counts by producer/material_type

CLI: scripts/seed.py
  ├─ load_yaml('data/kronospan_full.yaml')
  ├─ CatalogImporter.import_all(data)
  │    producers → structures → collections → materials →
  │    decors → variants → worktops → decor_structures →
  │    pairings → availability → property_flags
  └─ ImportStats summary

Frontend (Vite + Alpine.js at catalog/index.html):
  GET /catalog.json (pre-built from public/)
  → filter by material/color/structure/role
  → display decor cards with images from public/kronospan/img/
```

**What works:** Full read API, frontend with filters, 177 Kronospan + Kronoswiss decors imported, 6 routers, 22-table schema, image assets (`K8685.jpg` etc.), 75 JS tests + Python API tests.

**What's the data model:**
- `Decor` (visual identity: K8685 Biel Alpejska, NCS S 0500-N, RAL 9016)
- `Variant` (material slug + thickness: K8685-CH chipboard 18mm, K8685-MDF acrylic)
- `Structure` (SM, PE, BS, PD, PW — 18 producer structure codes)
- `Edge`, `Pairing`, `Worktop`, `Availability`, `PropertyFlag`
- All hung off `Producer` (Kronospan, Kronoswiss)

**Gap:** No "this Kitchen has Decor X for fronts" — catalog/ doesn't know about cabinets/projects.

### 2.2 `kitchen-app/` — Reflex Web UI + BOM System

**Entry:** `kitchen-app/kitchen_app/kitchen_app.py` (Reflex app)

```
startup:
  ├─ rxconfig.py loads Reflex config
  ├─ KitchenState (rx.State) initialized
  └─ app.add_page(index, "/", on_load=KitchenState.load_mock_data)
     app.add_page(admin_page, "/admin")

User opens "/":
  KitchenState.load_mock_data()
  ├─ get_session() — SQLite via SQLModel
  ├─ load Project from DB
  ├─ for each Cabinet:
  │    cab.calculate_cost(defaults, waste_factor)
  │      ├─ if use_new_bom:
  │      │    BOMGenerator(cab, defaults).generate()
  │      │      ├─ get_recipe(cab.recipe_id) from recipes.json
  │      │      ├─ for each formula in recipe.formulas:
  │      │      │    eval_formula(formula, cabinet_dims)
  │      │      │      (e.g. corpus_m2 = ((2*h*d) + (w*d) + (2*w*100) + (4*w*d)) / 1000000)
  │      │      ├─ build BOMAssembly (Composite pattern)
  │      │      │    BOMAssembly contains BOMPart nodes
  │      │      ├─ RulesEngine.apply_rules(recipe.tags, assembly)
  │      │      │    e.g. tag "has_doors" → adds 2 hinges per door
  │      │      │    tag "is_base" → adds 4 legs
  │      │      └─ assembly.calculate() → total cost (recursive)
  │      └─ get_strategy_for_material(material.category)
  │             SheetMaterialStrategy / LinearMaterialStrategy / CountertopStrategy / ExactQuantityStrategy
  │             .calculate_purchase_quantity(net_quantity)
  └─ render UI: 2D layout, sidebar, cost panel, cost trace details

User clicks "+1 cabinet":
  KitchenState.add_cabinet(recipe_id)
  ├─ session.add(Cabinet(recipe_id=...))
  ├─ recalculate_costs()
  └─ rerender

Admin page /admin:
  AdminState.load_materials/hardware/hardware_rules from DB
  CRUD operations on Material, HardwareSet, HardwareRule
```

**What works:** Full Reflex 2D UI, recipe-driven BOM with Composite pattern, tag-based rules engine, 4 purchasing strategies, admin CRUD, SQLite-backed Project/Cabinet model, cost tracing.

**Recipe format (`kitchen-app/kitchen_erp/recipes.json`):**
```json
"DRAWER_BASE": {
  "name": "Drawer base",
  "type": "BASE",
  "tags": ["is_base", "has_drawers"],
  "default_dimensions": {"width_mm": 400, "height_mm": 802, "depth_mm": 560},
  "limits": {"width_min": 300, "width_max": 1200, ...},
  "formulas": {
    "corpus_m2": "((2 * height_mm * depth_mm) + ...) / 1000000",
    "back_m2": "...",
    "front_m2": "..."
  }
}
```

15 recipes: DRAWER_BASE, SINK_BASE, WALL_CABINET, OVEN_BASE, PULLOUT_FILLER, SIDE_PANEL, DISHWASHER, OVEN, FILLER, BASE_CABINET, COUNTERTOP, SINK, FAUCET, COOKTOP, HOOD.

**Gap:**
- Material catalog is ITS OWN SQLite (`Material` table in kitchen-app/database.db) — disconnected from `catalog/`'s 177 Kronospan decors
- Cabinet is m²-based (just panel areas) — no panel-level breakdown; doesn't know individual panels' dimensions
- No drilling, no DXF, no Blender — pure BOM/cost focus

### 2.3 `kitchen-cad/` — Panel + Drilling + CSV Generator

**Entry:** `kitchen-cad/example_generate.py`

```
main():
  spec = CorpusSpec(
    id="K01", name="Szafka dolna 800",
    width=800, height=720, depth=510,
    hinges=HingeSpec(count=2),
    config=BaseDoorConfig(shelves=[352], doors=[2])
  )

  panels = calculate_panels(spec)
    ├─ if isinstance(spec.config, BaseDoorConfig): _calculate_base_door(spec, config)
    ├─ if isinstance(spec.config, BaseDrawerConfig): _calculate_base_drawer(spec, config)
    ├─ if isinstance(spec.config, CornerBlindConfig): _calculate_corner_blind(...)
    ├─ ...sink, cargo, oven, corner_internal
    └─ each path internally:
       _side_panels(spec) → [Panel(left), Panel(right)]
         carcass thickness, edge bands on visible edges
       _horizontal_panels(spec) → [top, bottom panels]
       _shelf_panels(spec, [352]) → [Panel(shelf_1)]
       _back_panel(spec) → Panel(back)
       _door_fronts(spec, [2]) → [Panel(door_left), Panel(door_right)]

  panels = apply_all_drilling(panels, spec)
    ├─ apply_system32(panels, spec)
    │    for each side panel: shelf-pin holes at 32mm grid
    ├─ apply_hinges(panels, spec)
    │    for each side panel facing a door: hinge cup holes
    └─ apply_handles(panels, spec)
         for each door/drawer: handle screw holes (relingowe)

  generate_cutting_csv(panels, "output/ciecie.csv")
    semicolon-separated, Polish columns
  generate_edging_csv(panels, "output/oklejanie.csv")
    edge-banding linear meters per panel side
```

**Cabinet types supported (8):**
- `BaseDoorConfig` (`Szafka dolna standardowa`)
- `BaseDrawerConfig` (`Szafka dolna z N szufladami`)
- `CornerBlindConfig` (`Szafka dolna narożna ślepa`)
- `CornerInternalConfig` (`Szafka dolna narożna wewnętrzna` with Optima 800/900 carousel)
- `SinkConfig` (`Szafka dolna zlewowa` with optional sorting drawer)
- `CargoConfig` (`Szafka dolna z koszem cargo` MINI_40)
- `OvenConfig` (`Szafka do zabudowy piekarnika` reinforced shelf + vent)
- (Wall cabinet via WallDoorConfig — not listed in README but in models)

**What works:** Panel calculation per type, System 32 drilling, Blum CLIP 35mm hinges, handle drilling, CSV cut + edging output, DXF generator for Legrabox side panels (`generators/legrabox_side_panel.py`), comparison test framework (CSV self-compare, DXF self-compare).

**Gap:**
- Not connected to material catalog — `_edge_material(spec)` returns just `spec.edge_band_material` string
- No Kitchen-level concept (no walls, no layout, no rows of cabinets)
- No BOM, no cost, no rendering
- No CLI (per ROADMAP — Phase 3 planned)
- No DXF for cabinet (only Legrabox side panel) — DXF cabinet generator is `[ ]` in ROADMAP

**ROADMAP says:** Phase 1 ✅ complete, Phase 2.5 ✅ complete (discriminated unions), Phase 2 in progress (DXF + YAML loader + Hettich Sensys + Minifix + Blum drawer runners).

### 2.4 `kitchen-plugin/` — Blender 3D Renderer (already covered in doc 06 + 07)

**Entry:** `blender --background --python src/main.py -- configs/foo.json`

Already documented in doc 06 (4,523 LOC src + 22 tests; 5-layer DDD architecture with Cabinet, Wall, Room, Layout, CabinetGeometry, KitchenStandards; manifest output; standalone bpy invocation).

### 2.5 `krono-compositor-mvp/` — 2.5D Real-time Compositor (covered in doc 09)

Already documented in doc 09 (1,341 LOC; offline 5-pass Blender bake + online OpenCV composite + FastAPI; clean architecture domain/infrastructure/application/presentation; ~500ms per material swap; own catalog_db.py).

### 2.6 `src/kuchnie_core/` — Legacy Decomposer + Materials Protocol

**Entry:** Not a service — imported as library.

```
loader.load_kitchen("kitchen.yaml")
  → Kitchen(version, project_name, rows=[Row(cabinets=[CabinetInstance, ...])], worktops)

decomposer.decompose(cab: CabinetInstance) → DecompositionResult
  ├─ TYPE_REGISTRY (in catalog.py):
  │    "dolna_szufladowa" → decompose_dolna_szufladowa
  │    "dolna_legrabox"   → decompose_dolna_legrabox
  │    "gorna_drzwiowa"   → decompose_gorna_drzwiowa
  │    (only 3 Polish types hardcoded — partial)
  └─ each emits list[Panel] + list[Accessory]
       Panel has machining_ops (drill, groove, rabbet, dado)
       EdgeBand on each panel side

kitchen.decompose_kitchen(kitchen) → {cab_id: DecompositionResult}
kitchen.all_panels(kitchen) → list[Panel]
kitchen.all_accessories(kitchen) → list[Accessory]
kitchen.kitchen_bom(kitchen, board_prices, edge_prices) → BOM
kitchen.validate_rows(kitchen) → list[str] (validation messages, plain text)

export.cutlist_csv.export_cutlist_csv(kitchen, path)
  ├─ all_panels(kitchen)
  ├─ aggregate_panels → list[CutPiece]
  │    group by (material, thickness, w, h, edges) → quantity
  └─ pieces_to_csv(pieces) → "..." → write file

legrabox.lw(kb, side_thickness) → light_width
legrabox.decompose_drawer_box(...) → (list[Panel], list[MachiningOp])
legrabox.validate_height_nl(...) → list[str]

materials/ (Protocol pattern — F005-shaped):
  MaterialCatalog Protocol with get_variant/get_edge/find_worktops/find_edges_for_variant
  MaterialResolver wraps a MaterialCatalog with cache + try_resolve
  SqliteMaterialCatalog implements Protocol against catalog/db/catalog.db (!)
  VariantInfo, EdgeInfo, WorktopInfo dataclasses
```

**KEY DISCOVERY:** `src/kuchnie_core/materials/sqlite_repository.py::SqliteMaterialCatalog` already **reads from `catalog/db/catalog.db`**. So kuchnie_core CAN talk to catalog, but **only via the SQLite file** (not via the FastAPI), and the dependency is informal (path to `catalog.db` is configured).

**What works:** Complete Polish-type decompiler for 3 cabinet types, Legrabox math (LW, NL, capacity validation), BOM aggregation, CSV cut-list export, Materials Protocol with SQLite implementation talking to catalog/'s DB.

**Gap:**
- Only 3 cabinet types (vs kitchen-cad's 8, kitchen-app's 15, kitchen-plugin's 9 enum values)
- No 3D rendering, no Blender
- No web UI, no API
- `validate_rows` returns plain strings (no `Issue.code`)
- `CabinetInstance` model has ~25 fields hardcoded (corpus_thickness, joinery params, drawers list of dict, etc.) — predates F001's `ConstructionMethod` separation

---

## 3. The Six Versions of "Cabinet"

| Prototype | Class | Backing | Purpose | Fields (highlights) |
|---|---|---|---|---|
| kitchen-app | `kitchen_erp.models.Cabinet` | SQLModel/SQLite | BOM + cost UI | id, project_id, recipe_id, width_mm, height_mm, depth_mm, position_x, position_y, custom_front_material_id |
| kitchen-app | `kitchen_app.state.CabinetUI` | Pydantic | UI state projection | derived from above, includes cost preview |
| kitchen-cad | `kitchen_cad.models.CorpusSpec` | Pydantic | Panel calc + drilling | id, name, width, height, depth, hinges (HingeSpec), handles (HandleSpec), config (discriminated union) |
| kitchen-plugin | `kitchen.cabinet.Cabinet` (frozen dataclass) | dataclass | Geometry + render | id, cabinet_type (enum), wall_id, offset, dimensions, door_side, drawer_count, blind_depth |
| krono-compositor | layout.json dict | dict | 5-pass renderer input | type, width_mm, height_mm, depth_mm, id_hex, handle |
| kuchnie_core | `model.CabinetInstance` | dataclass | Legacy decompose | id, type (string), width_mm/height_mm/depth_mm, body_material, back_material, front_material, 5 thickness fields, back_type, drawers list, shelves list, fronts list, handles dict |

**Six different Cabinet conceptions.** The biggest divergence:
- kitchen-plugin/kuchnie_core think of a Cabinet as **a placed thing on a wall**
- kitchen-cad/kitchen-app think of a Cabinet as **a parametric specification independent of placement**
- compositor thinks of a Cabinet as **a JSON dict with mask color**

These aren't subclasses of one another. They're parallel models for the same real-world object.

---

## 4. The Three (Four?) Versions of "Recipe"

| Prototype | Where | Format | Style |
|---|---|---|---|
| kitchen-app | `kitchen_erp/recipes.json` | JSON, 15 recipes | Formulas as strings (`"corpus_m2": "((2*h*d) + ...) / 1000000"`), evaluated by `eval_formula()` |
| kitchen-cad | `panel_calculator.py::_calculate_base_door()` et al. | Python code | 8 cabinet types as Python functions per type |
| kitchen-plugin | `geometry_builder.py::_build_cabinet()` | Python code with `bpy` calls | Per-`CabinetType` enum branches |
| kuchnie_core | `catalog.py::decompose_dolna_*()` | Python code | 3 Polish types as functions in TYPE_REGISTRY |

**Four parallel implementations** of "given a cabinet spec, emit panels":
- 15 recipes (kitchen-app, formulas-only, no panels)
- 8 recipes (kitchen-cad, Python, panel-level with edges + drilling)
- 9 recipes (kitchen-plugin, Python with bpy, panel-level with geometry)
- 3 recipes (kuchnie_core, Python, panel-level with edges + machining)

**Worse:** the outputs are different shapes:
- kitchen-app emits `BOMPart` (material + m² + cost)
- kitchen-cad emits `Panel` (with `DrillPoint`s, `EdgeBand`s, dimensions)
- kitchen-plugin emits `bpy.Object`s (with manifest classifications)
- kuchnie_core emits `Panel` (with `MachiningOp`s) + `Accessory`s

**Only kitchen-cad and kuchnie_core agree on the output type name (`Panel`), but the Panel dataclasses are NOT the same.**

---

## 5. The Four (Five?) Versions of "Material/Decor"

| Prototype | Where | Schema | What it knows |
|---|---|---|---|
| catalog/ | SQLite via 22 tables | Producer/Decor/Variant/Edge/Pairing/Worktop/Availability | 177 Kronospan decors with images, all metadata, pairings, worktops, availability per channel |
| kitchen-app | `Material` SQLModel | name, brand, price, sheet_size_m2, has_woodgrain, unit, category | Pricing + purchasing strategy (sheet vs linear vs countertop vs exact) |
| kitchen-cad | string field on Panel (`_edge_material(spec)`) | just a string name | Edge banding material name |
| kitchen-plugin | `config["materials"]` dict | RGB colors per role | `carcass: {color: [0.9, 0.9, 0.88]}` — no real catalog |
| krono-compositor-mvp | `catalog_db.py` Python dict | id, name, price_group, allowed_zone, texture_width_mm, hex_color | 6 hardcoded materials with texture images |
| kuchnie_core | `materials/` Protocol | VariantInfo, EdgeInfo, WorktopInfo dataclasses + SqliteMaterialCatalog | Reads from catalog/db/catalog.db (the one real bridge!) |

**Five parallel material models** + 1 informal SQLite bridge (kuchnie_core → catalog).

**Important:** `kuchnie_core.materials.sqlite_repository.SqliteMaterialCatalog` is the **only existing cross-prototype integration** I can find. It reads `catalog/db/catalog.db` directly. The Protocol shape (`get_variant`, `get_edge`, `find_worktops`, `find_edges_for_variant`) looks deliberately like a thin projection over catalog/'s schema.

This means kuchnie_core's `materials/` package was **deliberately designed as an adapter between catalog and the rest**. But no other prototype uses it.

---

## 6. The Two (Three?) Versions of "Validation"

| Prototype | Where | Returns | Codes? | Layer |
|---|---|---|---|---|
| kitchen-plugin | `validators.py` (config-time) | `list[str]` (error messages) | No | pre-build |
| kitchen-plugin | `manifest_validator.py` (post-bpy) | `ValidationResult(issues: List[Issue])` | No (Issue has type+message) | post-build |
| kitchen-cad | (in `models.py` via Pydantic validators) | Raises ValidationError | No | construction-time |
| kuchnie_core | `kitchen.validate_rows(kitchen)` | `list[str]` (warnings) | No | runtime |
| kitchen-app | `_apply_cabinet_constraints` | UI form validation | No | input-time |

No prototype uses error codes (DIM-001 etc.). F004's "code registry" is genuinely new.

---

## 7. The Three Versions of "Cabinet Templates / Types"

| Prototype | How types are defined | How many |
|---|---|---|
| kitchen-app | `recipes.json` (15 entries with `tags`, `default_dimensions`, `limits`, `formulas`) | 15 |
| kitchen-cad | Discriminated union: `BaseDoorConfig \| BaseDrawerConfig \| ...` (Pydantic union) | 8 + screenshots per type in `cabinet-types/` |
| kitchen-plugin | `CabinetType(Enum)` (values like `BASE_DOOR`, `WALL_DOORS`, ...) | 9 |
| kuchnie_core | `TYPE_REGISTRY` dict: `{"dolna_szufladowa": decompose_dolna_szufladowa, ...}` | 3 |

**One concept, four definitions, different counts.**

---

## 8. So What IS This Project, Actually?

The user has spent significant time building **six prototypes that each prove a different idea**:

| Prototype | The idea it proves |
|---|---|
| catalog/ | "I can have a real Polish material catalog with 177 decors, web API, frontend" |
| kitchen-plugin | "I can have a clean DDD layered 3D renderer using Blender headless" |
| krono-compositor-mvp | "I can do live decor preview at 500ms instead of 30s per render" |
| kitchen-cad | "I can generate cut-list CSVs and drill patterns with System 32 + Blum hinges" |
| kitchen-app | "I can have a Reflex UI with recipe-driven BOM + cost + admin" |
| kuchnie_core | "I can have a Materials Protocol bridging catalog to the rest" |

**Each prototype answers one R&D question.** None of them is a "version" of a single system — they're six independent answers to six different questions.

**The F001-F008 planning was a seventh prototype** — but expressed as architecture docs, not code. Its job was to describe **how the previous six prototypes could be unified into one system**. But the docs were written **without knowledge that the previous six exist** (my fault — 3 audit misses in a row).

---

## 9. The Real Question Now

**Strategy U1 — Unify via shared core (slow, clean)**

Define canonical models in `src/kuchnie_core/`:
- One canonical `Cabinet` (synthesize from the 5 versions)
- One canonical `Material/Decor` (catalog's wins — it's the richest)
- One canonical `Panel` (kitchen-cad's wins — it has DrillPoints + EdgeBands)
- One canonical `Recipe` interface (kitchen-app's JSON schema + kitchen-cad's per-type Python)
- One canonical `ValidationGate` registry (F004 design — net new)

Then **gradually migrate** each prototype to import from kuchnie_core:
- catalog/ becomes a backing store (its API still serves frontends; kuchnie_core reads its DB via existing SqliteMaterialCatalog)
- kitchen-cad starts importing `kuchnie_core.Cabinet` instead of defining `CorpusSpec` (or `CorpusSpec` becomes a kuchnie_core-derived adapter)
- kitchen-plugin's `Cabinet` becomes an alias of kuchnie_core's
- kitchen-app's SQLModel `Cabinet` becomes a persistence adapter for kuchnie_core's `Cabinet`
- compositor's `layout.json` is generated from a kuchnie_core `Kitchen`

**Pros:** Truly unified system. Each prototype keeps its specialization (rendering, UI, drilling) but agrees on the domain.
**Cons:** **3-6 months of refactor work for a solo dev**. Each prototype's 6-10K LOC needs touching. Every test must keep passing.

**Strategy U2 — Pick one winner per concept (fast, lossy)**

Each domain concept picks one prototype as the canonical owner:

| Concept | Winner | Why | Lose |
|---|---|---|---|
| Material/Decor catalog | catalog/ | 177 real decors, 22-table schema, API, frontend, recently active | kitchen-app's `Material` table, compositor's `catalog_db.py`, kuchnie_core's `VariantInfo` |
| Cabinet (placement) | kitchen-plugin's `Cabinet` + `CabinetPlacement` | Cleanest DDD design, 22 tests, wall-relative model | kuchnie_core's `CabinetInstance`, kitchen-app's `Cabinet` |
| Cabinet (parametric spec) | kitchen-cad's `CorpusSpec` + discriminated union | 8 cabinet types covered, panel-level + drilling | kitchen-app's recipes.json |
| Recipe (panel decomp) | kitchen-cad's `panel_calculator` Python functions | Most cabinet types covered, most detail (panels + drilling) | kitchen-app's formula JSON, kuchnie_core's `decompose_dolna_*` |
| Recipe (BOM cost) | kitchen-app's `BOMGenerator` + `RulesEngine` + `PurchasingStrategy` | Most mature cost model | kuchnie_core's `calculate_bom` |
| Construction params | (none own this yet — F001 work) | F001 introduces ConstructionMethod | kitchen-plugin's hardcoded `DEFAULT_*` constants |
| 3D render | kitchen-plugin | Full Blender 3D + manifest | — (no competitor) |
| 2.5D realtime render | krono-compositor-mvp | OpenCV compositor | — (no competitor) |
| Web UI | kitchen-app | Reflex with state, admin, BOM panel | — (no competitor) |
| Cut-list CSV / DXF / drilling | kitchen-cad | Most complete | kuchnie_core's `cutlist_csv` |
| Material resolver (slot→decor) | kuchnie_core/materials | Already designed as Protocol over catalog | compositor's catalog_db |

Then **build glue code** in `src/kuchnie_core/` (small, ~500 LOC) that imports types from each winner and provides the integration points. Each prototype mostly stays put.

**Pros:** Each prototype is preserved; we don't fight existing code. Glue is small and focused. Lower risk per change.
**Cons:** ~6 imports from 4 prototypes; package layout is unusual; each prototype must be packaged so others can import it (`pip install -e ./kitchen-cad`, `pip install -e ./catalog`, etc.).

**Strategy U3 — Pick one as the project, abandon the others**

Choose one prototype as the project; treat the others as references; restart features in the chosen one with knowledge gained from the rest.

**Pros:** Single codebase, no integration headaches.
**Cons:** Throws away 30,000+ LOC of working code. Highest psychological cost.

---

## 10. My Recommendation

**Strategy U2 (pick-one-winner-per-concept).** Three reasons:

1. **You've already done the hard work.** Each prototype works in its own bounded scope. Throwing any of them out (U3) is wasteful; refactoring them all to share types (U1) is months of work that doesn't add features.

2. **The dependency graph is doable.** Each prototype already has zero cross-imports — they're naturally separable packages. Making them installable via `uv pip install -e ./catalog -e ./kitchen-cad -e ./kitchen-plugin -e ./kitchen-app -e ./krono-compositor-mvp` is a one-day exercise.

3. **The glue layer is small.** `src/kuchnie_core/` becomes a **thin integration package**:
   - Imports `Cabinet` from kitchen-plugin (the placement+geometry concept)
   - Imports `CorpusSpec` from kitchen-cad (the parametric spec concept)
   - Defines an adapter: `CorpusSpec(cabinet)` builds spec from kitchen-plugin cabinet for cut-list export
   - Imports decor lookups from catalog
   - Implements F001 (`ConstructionMethod` registry) and F004 (`ValidationGate` registry) — the genuinely new abstractions

The existing `kuchnie_core.materials` package (which already reads catalog's SQLite via `SqliteMaterialCatalog`) is the template for how this can work.

### What F001-F008 become under U2

| Old plan | Under U2 reframed |
|---|---|
| **F001 ConstructionMethod** | NEW work: introduce a `ConstructionMethod` registry in kuchnie_core. kitchen-plugin's `cabinet_geometry.py` constants get a one-line refactor to import from kuchnie_core. |
| **F002 Recipe Engine** | NOT a new build. **Decision needed:** does kitchen-cad's `panel_calculator` become the canonical Recipe Engine (Python functions per type), or do we promote kitchen-app's JSON-formula approach? My lean: **kitchen-cad's Python is canonical** (richer output); the JSON formulas in kitchen-app become BOM-side metadata layered on top. |
| **F003 Template Registry** | Already exists as kitchen-app/recipes.json (15) + kitchen-cad cabinet-types/ folders (8) + kitchen-plugin CabinetType enum (9). **Unification work:** pick one Polish-cabinet-type taxonomy, port all metadata into it. ~1 day of YAML editing. |
| **F004 Validation Gates** | NEW work: introduce `Issue.code` and the 4-gate registry. Each prototype's existing checks get wrapped as gate implementations. |
| **F005 Material Resolver** | Already started in `kuchnie_core/materials/`. **Decision needed:** is the existing `MaterialResolver` interface the canonical one, or do we redesign? My lean: **keep the existing one** (it's the only existing cross-prototype bridge); flesh out role→slot→decor chain on top. |
| **F006 Web Sidebar** | kitchen-app already IS the web UI. F006 becomes "wire kitchen-app to call kitchen-cad for cut-list and compositor for live render" — a few hundred lines of import + API call code. |
| **F007 Blender Adapter** | kitchen-plugin already IS the renderer. F007 becomes "wire kitchen-plugin's `material_manager.py` to read textures from catalog via kuchnie_core." |
| **F008 CLI Export** | kitchen-cad already has `example_generate.py` doing CSV+DXF. F008 becomes "package as `kitchen-cli` binary with subcommands + integrate with the canonical Recipe + ValidationGates." |

**Estimated effort under U2 (vs U1 or starting fresh):**
- Domain unification (decide owners, package layout, glue code): **3-5 days**
- F001 ConstructionMethod refactor: **1 day** (just lift kitchen-plugin's constants)
- F002 reconciliation (decide canonical recipe; port missing types between kitchen-cad/kuchnie_core/kitchen-app): **3-5 days**
- F003 template-registry consolidation: **2-3 days** (YAML editing)
- F004 introduce codes + gate registry: **2-3 days**
- F005 finish role→slot→decor chain on existing Protocol: **2-3 days**
- F006 wire kitchen-app to compositor + kitchen-cad: **3-5 days**
- F007 wire kitchen-plugin to catalog (textures): **2-3 days**
- F008 package kitchen-cli + integrate: **3-5 days**
- **Total: ~3-5 weeks of solo-dev work.** Versus 3-6 months of U1 or starting from scratch.

---

## 11. What I'm Asking You To Confirm

I will not write a single line of more planning or code until you confirm:

1. **Confirm strategy** — U1 (refactor to shared core), U2 (pick winners + glue, recommended), or U3 (start over with one)?

2. **If U2, confirm winners per concept** — see table in § 9 above. Specifically:
   - Catalog: catalog/ wins? (Yes is obvious.)
   - Cabinet placement: kitchen-plugin's wins?
   - Cabinet parametric spec: kitchen-cad's CorpusSpec wins?
   - Recipe: kitchen-cad's Python functions win (vs kitchen-app's JSON formulas)?
   - BOM cost: kitchen-app's BOMGenerator wins?
   - 3D render: kitchen-plugin wins (obvious; no competitor)?
   - 2.5D real-time: krono-compositor-mvp wins (obvious; no competitor)?
   - Web UI: kitchen-app wins (obvious; no competitor)?
   - Cut-list/DXF/drilling: kitchen-cad wins?

3. **Confirm packaging approach** — each prototype becomes an installable package (`uv pip install -e ./catalog -e ./kitchen-cad ...`) sharing a common Python environment? Or do they stay in subdirs and use sys.path tricks?

4. **Confirm whether to retire kuchnie_core's legacy decomposers** (`dolna_szufladowa`, `dolna_legrabox`, `gorna_drzwiowa`) — superseded by kitchen-cad's panel_calculator if you pick U2.

5. **Confirm I should consolidate the old planning docs (00–09) into a new single planning doc** once strategy is locked. They are increasingly contradictory as more reality is discovered.

I owe you an apology for the three audit misses. The process-checklist I wrote into doc 09 § 9 should have been here from session 1. From this point on, no planning happens without `pysum + py-diagram + grep cross-imports` on every sibling directory first.
