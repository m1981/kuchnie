# 03 — Roadmap (Post-Skeleton)

> **Prerequisite.** `02_WALKING_SKELETON.md` is done and tagged `skeleton-v0.1`. Do not start any phase below until then.
>
> **Estimated total post-skeleton effort:** 4–6 weeks of solo-dev work to v1.0.
>
> **Estimation basis.** Each item has a day count; the day is a focused-work day, not a calendar day. Allow ~50% calendar overhead.

---

## Phase Overview

| Phase | Theme | Features | Effort | Outcome |
|---|---|---|---|---|
| **P0** | Walking Skeleton | — | 1 week | All 6 subsystems wired through `kuchnie_core`; one YAML produces JPG+PNG+CSV. |
| **P1** | First-class joinery | F001 + F004 | ~1 week | Construction methods are swappable; validation issues have codes. |
| **P2** | Cabinet vocabulary | F002 + F003 | ~1.5 weeks | All Polish cabinet types unified; recipes live in one place. |
| **P3** | Materials & textures | F005 + F007 | ~1 week | Decor swap shows real Kronospan textures in 2.5D and 3D. |
| **P4** | User-facing polish | F006 + F008 | ~1.5 weeks | Multi-cabinet UI; `kitchen-cli` ships; CAM-ready outputs. |

---

## P1 — Construction Methods + Validation Codes (~1 week)

### F001 — ConstructionMethod Registry — ~1 day

**Why.** Today, panel thickness/groove/overlay constants are hardcoded in `kitchen-plugin/src/kitchen/cabinet_geometry.py` (DEFAULT_CORPUS_THICKNESS=18, DEFAULT_GROOVE_DEPTH=9, etc.) and partially duplicated as defaults in kitchen-cad's `CorpusSpec`. Two consequences: (a) can't have one kitchen with frameless 18mm and another with cam-lock 16mm; (b) F008 cut-list can't generate proper drill patterns without knowing the method.

**Pattern.** Winner Flex's "construction logic separation" (see `05_PATTERN_GOLD.md`).

**Work.**

| File | Change |
|---|---|
| `src/kuchnie_core/construction.py` | NEW. `ConstructionMethod` dataclass (corpus_thickness, front_thickness, back_thickness, groove_*, overlay_*, joinery_type). `default_registry: dict[str, ConstructionMethod]` with `dowel_18`, `camlock_18`, `frameless_18`, `frameless_16`. |
| `src/kuchnie_core/construction.py` | `get(method_id) -> ConstructionMethod`, `register(method)`. |
| `examples/skeleton_kitchen.yaml` | Replace `construction_method: dowel_18` string with reference into registry; loader resolves at load. |
| `kitchen-plugin/src/kitchen/cabinet_geometry.py` | Constructor accepts optional `method: ConstructionMethod | None`; if None, uses module-level DEFAULT (backward compat). New tests pass a custom method. |
| `kitchen-cad/src/kitchen_cad/models.py` | `CorpusSpec` gains `construction_method: str = "dowel_18"`. `panel_calculator` reads thickness/overlay from the resolved method instead of `CorpusSpec.edge_band_material`-style defaults. |
| `tests/test_construction_method.py` | NEW. Two recipes with different methods produce different panel thicknesses. |

**Done when.** `examples/skeleton_kitchen.yaml` with `construction_method: camlock_18` produces panels with 16mm thickness; same YAML with `frameless_18` produces 18mm.

### F004 — Validation Gates with Codes — ~3 days

**Why.** Five places do validation today (kitchen-plugin `validators.py`, `manifest_validator.py`; kitchen-cad Pydantic; kuchnie_core `validate_rows`; kitchen-app form constraints). All return strings. Cross-context = "Web shows 'too narrow', CLI exits 1 with 'width below minimum', they're the same error." Need codes for traceability.

**Pattern.** TopSolid'Wood's manufacturability gates (`05_PATTERN_GOLD.md`).

**Work.**

| File | Change |
|---|---|
| `src/kuchnie_core/validation/__init__.py` | NEW. `Issue(code, severity, message, source_ref)`, `ValidationResult`. |
| `src/kuchnie_core/validation/codes.py` | NEW. Code registry: `DIM-*`, `ROW-*`, `KIT-*`, `CAM-*`, `MFR-*` (Manifest). Reserve `KIT-100`, `CAM-100` for F005's "decor unresolvable" check. |
| `src/kuchnie_core/validation/gates.py` | NEW. Four logical gates: `CabinetGate`, `RowGate`, `KitchenGate`, `CAMGate`. Each: `validate(kitchen) -> list[Issue]`. |
| Wrap `kitchen-plugin/src/validators.py` | As implementations of CabinetGate/RowGate checks. |
| Wrap `kitchen-plugin/src/manifest_validator.py` | Returns `list[Issue]` with `MFR-*` codes (geometric gate; runs only post-render). |
| Wrap `kitchen-cad` Pydantic validators | They raise — convert to Issue in `kuchnie_core.recipe.decompose` boundary. |
| `tests/test_validation_gates.py` | NEW. Each gate has at least one passing and one failing test. |
| `kitchen-app/kitchen_app/state.py` | Display Issues by code in UI; the same Issue shows the same message everywhere. |

**Done when.** A kitchen with width=200 (below `DIM-001: cabinet width below 300mm minimum`) fails identically in web UI, `make skeleton`, and the photoreal render's pre-flight.

---

## P2 — Cabinet Vocabulary Unification (~1.5 weeks)

### F002 — Recipe Engine Reconciliation — ~5 days

**Why.** Four parallel decomposition implementations: kitchen-app/recipes.json (15 formulas-only types), kitchen-cad/`panel_calculator` (8 panel-level types), kitchen-plugin/`_build_cabinet` (9 bpy types), kuchnie_core/`decompose_dolna_*` (3 Polish types). They disagree on what a cabinet decomposes to. Canonical decision per `01_DECISIONS.md`: kitchen-cad wins.

**Pattern.** Polyboard's "cabinet macros as data" (`05_PATTERN_GOLD.md`).

**Work.**

| File | Change |
|---|---|
| `kitchen-cad/src/kitchen_cad/configs/` | NEW dir. Port the 3 Polish types from kuchnie_core (`dolna_szufladowa`, `dolna_legrabox`, `gorna_drzwiowa`) into kitchen-cad's discriminated-union pattern. Likely 2 new config classes + reuse `BaseDrawerConfig`. |
| `kitchen-cad/src/kitchen_cad/panel_calculator.py` | New `_calculate_*` for each ported type. Use kuchnie_core's Legrabox math (still in `kuchnie_core/legrabox.py`) via import — proves The One Rule (D6) holds in reverse direction too. **Important:** kitchen-cad imports from kuchnie_core for Legrabox math; kuchnie_core does not import kitchen-cad for this purpose. Verify with `check_imports.py`. |
| `src/kuchnie_core/_retired/` | Move `catalog.py`, `decomposer.py`. |
| `src/kuchnie_core/__init__.py` | Remove `decompose` (the kuchnie_core-native one); the canonical `decompose` is the one from `kuchnie_core.recipe` (which calls kitchen-cad). |
| `kitchen-app/kitchen_erp/recipes.json` | Demote from "the recipes" to "BOM cost metadata layered on top of kitchen-cad recipes." Each entry references a kitchen-cad cabinet type via `kitchen_cad_type: BaseDoorConfig`. |
| `kitchen-app/kitchen_erp/bom_generator.py` | Updated: reads `list[Panel]` from `kuchnie_core.recipe.decompose(cabinet)` instead of `cabinet.calculate_cost()`. Aggregates by material via `PurchasingStrategy`. |
| `kitchen-plugin/src/geometry_builder.py` | `_build_cabinet()` becomes thin: takes `list[Panel]` from `kuchnie_core.recipe.decompose(cabinet)` and emits `bpy.Object`s. Per-type Python branches deleted. |
| `tests/test_recipe_unification.py` | NEW. For each cabinet type, kitchen-cad's panel list matches what the retired kuchnie_core decompose would have produced (golden tests against historical CSVs). |

**Done when.** All 11 Polish-market cabinet types (kitchen-cad's 8 + the 3 ported) decompose identically across kitchen-cad, kitchen-plugin (via consume), and kitchen-app's BOM. Tests prove it.

### F003 — Template Registry Consolidation — ~3 days

**Why.** Kitchen-app has 15 recipes.json types; kitchen-cad has 8 directory-named cabinet-types/; kitchen-plugin has 9 `CabinetType` enum values. The names are inconsistent (Polish names in kitchen-cad; English enum names in kitchen-plugin; UPPER_SNAKE in kitchen-app). Customers and the carpenter need one taxonomy.

**Pattern.** PRO100's cabinet macros (`05_PATTERN_GOLD.md`).

**Work.**

| File | Change |
|---|---|
| `src/kuchnie_core/templates/` | NEW dir. One YAML per template (e.g., `base_door_60.yaml`, `base_drawer_3_60.yaml`, `wall_door_60.yaml`, `tall_oven_60.yaml`, `corner_blind_l.yaml`, `sink_base_80.yaml`, `cargo_60.yaml`, etc.). |
| Each template YAML | `template_id`, `label_pl`, `label_en`, `category` (BASE/WALL/TALL/CORNER), `kitchen_cad_config_class` (`BaseDoorConfig`...), `default_dimensions`, `dimension_constraints`, `default_sub_assemblies` (doors/shelves/drawers), `material_role_defaults` (body, front, back, shelf → slot names). |
| `src/kuchnie_core/templates/__init__.py` | `TemplateRegistry.list(category=None)`, `get(template_id)`, `instantiate(template_id, overrides, project_default_method) -> Cabinet`. |
| `kitchen-app/kitchen_erp/recipes.json` | Becomes a thin BOM-cost cross-reference (each entry: `template_id`, `hardware_tags`, `bom_formulas`). |
| `kitchen-app/` Sidebar | "Add cabinet" reads from `TemplateRegistry.list()` instead of hardcoded list. |
| `tests/test_templates.py` | NEW. Instantiating each template produces a valid Cabinet; F002 decompose returns non-empty panel list. |

**Done when.** kitchen-app sidebar shows templates in Polish (`Szafka dolna 60 cm`); instantiating creates a `Cabinet` consumed identically by kitchen-cad, kitchen-plugin, kitchen-app's BOM.

---

## P3 — Materials and Textures (~1 week)

### F005 — Material Resolver Chain — ~3 days

**Why.** Today `kuchnie_core.materials.MaterialResolver.resolve(code)` returns `VariantInfo`. Need the full chain from the brief: customer changes `front` decor; that's a *slot* on the kitchen, not on a cabinet; resolver walks `role(panel) → slot(kitchen) → decor(catalog) → variant(thickness)`.

**Pattern.** Winner Flex's material decoupling (`05_PATTERN_GOLD.md`).

**Work.**

| File | Change |
|---|---|
| `src/kuchnie_core/materials/resolver.py` | Add `resolve_role(role: str, cabinet: Cabinet, kitchen: Kitchen) -> ResolvedMaterial`. Walks role → cabinet.material_refs[role] (slot name) → kitchen.material_slots[slot] (decor id) → catalog → variant matching `kitchen.construction_method.corpus_thickness_mm`. |
| `src/kuchnie_core/materials/models.py` | `ResolvedMaterial` (decor_id, decor_name, texture_path, color_hex, paired_edge_id, grain_direction, thickness_mm, sheet_size_mm, sku). |
| Edge-role convention | `<role>_color` (e.g., `front_color`) resolves to paired edge of the `<role>` decor. Documented in `GLOSSARY.md`. |
| `src/kuchnie_core/validation/gates.py` | `CAMGate.check_cam_100`: every emitted role resolves through the chain. Reserved code from F004. |
| `tests/test_material_resolver.py` | Chain test: kitchen with `material_slots = {body: K8685}` and cabinet with `material_refs = {body: "body"}`; `resolve_role("body", cab, kitchen)` returns `ResolvedMaterial(decor_id=K8685, ...)`. |

**Done when.** Decor swap in skeleton kitchen (replacing K8685 with another decor in catalog) makes the next composite call return a JPG with a different texture; the cut-list CSV gets the corresponding `paired_edge_id` in edge-banding columns.

### F007 — Render Texture Wiring — ~3 days

**Why.** Today kitchen-plugin's `material_manager.py` reads `config["materials"]["carcass"]["color"] = [0.9, 0.9, 0.88]` (RGB float). Should read texture paths from catalog via F005's `ResolvedMaterial.texture_path`. Compositor needs same.

**Work.**

| File | Change |
|---|---|
| `kitchen-plugin/src/material_manager.py` | Accept `dict[role, ResolvedMaterial]` instead of color blocks. Build bpy materials with image-texture nodes pointing at `texture_path`. |
| `kitchen-plugin/src/main.py` | Resolve materials before render: `materials = {role: MaterialResolver().resolve_role(role, cab, kitchen) for role in roles}`. |
| `krono-compositor-mvp/src/compositor/presentation/catalog_db.py` | Derive at startup: load YAML from catalog/, project to compositor's flatter schema. Hardcoded Python dict deleted. |
| `krono-compositor-mvp/gen_kitchen.py` | `setup_front_materials` uses `MaterialResolver` for hex_color. UV-coords already correct. |
| `tests/test_texture_wiring.py` | NEW. Compositor's `/api/v1/catalog` matches catalog's `/api/v1/decors` filtered to FRONT-allowed materials. Render in photoreal includes the right texture file. |

**Done when.** The skeleton kitchen, swapped from K8685 → K0190 in the web UI, shows the K0190 wood-grain in both the live JPG and the photoreal PNG, and the CSV cut-list shows `K0190-CH` SKU for body panels.

---

## P4 — User-facing Polish (~1.5 weeks)

### F006 — Multi-cabinet Web Configurator — ~5 days

**Why.** Skeleton has one hardcoded cabinet. The brief (`00-brief.md`) UC2 needs: load predefined layouts, 2D row-based editor, add/move/customize cabinets, global+local dimension changes, live cost panel.

**Work.**

| File | Change |
|---|---|
| `kitchen-app/kitchen_app/state.py` | `KitchenState` actually persists a `Kitchen` (not the SQLModel one — the kuchnie_core one) via `kuchnie_core.serialize.to_json_str` to Reflex state. |
| `kitchen-app/kitchen_app/pages/configurator.py` | NEW. 2D row layout SVG; drag-to-reorder; arrow keys to move; per-cabinet sidebar. |
| `kitchen-app/kitchen_app/pages/layouts.py` | NEW. Gallery of predefined Kitchen YAMLs (L-shape 3.2m, U-shape 2.4m, I-shape 2.0m — 3 to start). Load → enter configurator. |
| `kitchen-app/kitchen_app/pages/sidebar.py` | NEW. Tabs: Layout (dimensions), Decors (calls `MaterialResolver.list_decors_for_role`), Cost (calls `BOMGenerator` on every state change), Validation (shows `Issue` list from F004 gates). |
| `examples/predefined_kitchens/` | 3 YAML files matching the predefined layouts. |

**Done when.** Carpenter can on iPad: open kitchen-app, pick "L-shape 3.2m", drag a cabinet to reorder, change `front` decor, see updated JPG within 1 second, see total cost updated in zł.

### F008 — `kitchen-cli` Packaging + CAM Outputs — ~5 days

**Why.** UC3 needs CLI that produces e-rozkroj CSV, drill pattern CSV, DXF, BOM, cost-estimate. Today only CSV partial.

**Work.**

| File | Change |
|---|---|
| `kitchen-cad/src/kitchen_cad/cli/__main__.py` | NEW. argparse with subcommands: `cut-list`, `drill-pattern`, `dxf`, `bom`, `cost-estimate`, `render`, `validate`. Each loads YAML via `kuchnie_core.load_kitchen`, runs gates, calls the appropriate exporter. |
| `kitchen-cad/src/kitchen_cad/exporters/dxf.py` | NEW. Per-panel DXF: `PANEL_OUTLINE`, `EDGE_BAND_TOP/BOTTOM/LEFT/RIGHT`, `DRILL_*`, `GROOVE_*` layers. Use existing `generators/legrabox_side_panel.py` as the pattern. |
| `kitchen-cad/src/kitchen_cad/exporters/drill_pattern.py` | NEW. CSV of all `DrillPoint`s across all panels with `pattern_ref` field. |
| `kitchen-cad/src/kitchen_cad/exporters/bom.py` | NEW. Wraps kitchen-app's `BOMGenerator` for CLI use (so cost is computed without Reflex running). |
| `pyproject.toml` (root or kitchen-cad) | Console script: `kitchen-cli = "kitchen_cad.cli.__main__:main"`. |
| `kuchnie_core/render.subprocess` | F007 contributes the `render` subcommand to kitchen-cli via the same subprocess pattern. |
| `tests/test_kitchen_cli.py` | NEW. End-to-end: `kitchen-cli cut-list examples/predefined_kitchens/l_shape.yaml --output /tmp/cuts.csv` exits 0, produces non-empty file with header matching e-rozkroj schema (verify column names with CNC company at this point). |

**Done when.** `kitchen-cli` is on `PATH`, all 7 subcommands run on a predefined kitchen, CSVs open in Excel with Polish characters, DXFs open in LibreCAD, photoreal render is generated, BOM matches kitchen-app's display.

---

## v1.0 Definition of Done

- [ ] All four phases complete; their tests pass.
- [ ] `00-brief.md` UC1, UC2, UC3 each demonstrable end-to-end on a fresh laptop after `make setup`.
- [ ] `scripts/check_imports.py` passes in CI.
- [ ] At least 3 predefined kitchen layouts ship in `examples/`.
- [ ] Carpenter has used the system with ≥ 1 real customer and shipped ≥ 1 e-rozkroj CSV to the Wrocław CNC company.
- [ ] CHANGELOG entry for v1.0.

---

## Out of Scope for v1.0 (Backlog)

- Worktop joinery and seaming
- Splashback
- Multiple kitchens per project
- Customer-facing portal (today: carpenter shows iPad)
- Hardware integration with supplier APIs (Hettich, Blum) for pricing
- Multi-language UI (only Polish today)
- Mobile-native app (web on iPad is enough)
- DDD bounded-context refactor of the prototypes themselves (only kuchnie_core glue evolves)
- Worker pool / job queue for renders (single laptop, one user)
