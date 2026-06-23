# Changelog

All notable changes to this project are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/).

---

## [Unreleased]

### Changed — BREAKING

- **DDD strategic design: clean boundaries, domain model in production pipeline**
    - `build_kitchen(config)` removed from `geometry_builder.py` — replaced by `build_kitchen_from_layout(layout, settings)`
    - `build_layout(config)`, `ResolvedCabinet`, `WallBuilderResult` removed from `wall_builder.py`
    - `WallCabinet` moved from `kitchen/wall.py` to `wall_builder.py` (adapter concern, not domain)
    - `Position` class removed from `core/types.py` (unused)
    - `Tolerances` class gutted in `core/tolerances.py` (kitchen fields moved to `KitchenStandards`)
    - `CornerCabinet` alias removed from `kitchen/wall.py`
    - `mm_to_m()` removed from `config_parser.py` — now in `core/geometry.py`
    - `MIN_DRAWER_HEIGHT`, `MAX_DRAWER_COUNT` in `config_parser.py` now derive from `KitchenStandards`
    - `_build_cabinet()`, `_add_front()`, `_build_filler()` accept domain `Cabinet` objects (not dicts)
    - `_domain_cabinet_to_dict()` bridge removed

### Added

- **`build_domain_layout(config)` in `wall_builder.py`** — converts raw config to domain Layout
    - Returns `Layout` with `Room`, `Run`, `Cabinet`, `CabinetPlacement` objects
    - Uses `LayoutEngine` for position computation
    - Replaces duplicated direction/turn logic

- **`build_kitchen_from_layout(layout, settings)` in `geometry_builder.py`**
    - Reads positions from domain `Layout.placed_cabinets`
    - Domain `Cabinet` objects passed directly to mesh creation (no dict bridge)

- **`export_manifest()` accepts optional `layout` parameter**
    - `_build_layout_metadata_from_domain(layout)` reads from domain model
    - Old `_build_layout_metadata(config)` kept as fallback for test compatibility

- **Mermaid diagrams in `docs/architecture.md`**
    - Data flow diagram showing 5 bounded contexts
    - Class diagram showing all 28 domain classes

### Fixed

- **`LayoutEngine._create_walls()` direction bug** — L-shape and U-shape walls were all going east
    - Now uses `run.direction` directly instead of previous iteration's direction

- **European frameless front sizing** — fronts were larger than carcass (overlay model), now correctly smaller (gap model)
    - Front width = carcass_width - 2 × frontGap (was: + 2 × overlay)
    - Front height = carcass_height - 2 × frontGap (was: + 2 × overlay)
    - Gap is uniform on all sides (2mm default)

- **Manifest carcass parent bounds** — was including front panels in bounding box
    - Now excludes door_front and drawer_front when computing parent dimensions
    - Carcass shows actual box dimensions (600×560×720) not inflated door bounds

### Added

- **Countertop validation** (`_check_countertops()` in `validators.py`)
    - counterThickness: 20-40mm
    - counterOverhangFront: 20-30mm
    - counterOverhangEnd: 0-30mm

### Docs

- **`docs/architecture.md` updated to match refactored code**
    - Data flow ASCII diagram shows domain model in production pipeline
    - Module details updated (Tolerances removed, WallCabinet moved, KitchenStandards added)
    - File structure comments updated
    - Numerical values removed (deferred to `european-kitchen-standards.md`)
    - `validators` now shown using `KitchenStandards`

### Removed — BREAKING

- **OBJ and glTF export removed from `src/exporters.py`**
    - `export_obj()` and `export_gltf()` functions deleted
    - `--export-obj` and `--export-gltf` CLI flags removed from `main.py`
    - Old `.obj`, `.gltf`, `.mtl`, `.bin` files cleaned from `output/meshes/`
    - Manifest-first pipeline replaced these for validation; `.blend` kept for visual inspection

### Changed — BREAKING

- **Consolidated wall model: removed `src/wall_model.py`**
    - All Wall/Room/Cabinet types now live in `src/kitchen/wall.py` (single source of truth)
    - `wall_builder.py` updated to import from `kitchen/wall.py` with `Vector2D` (was: raw tuples)
    - `CornerReference` now has `width` field and `CornerCabinet` alias for backward compat
    - `WallCabinet`, `BoxVertices`, `create_box_vertices` moved from `wall_model.py` to `kitchen/wall.py`
    - Eliminates duplicate Wall/Room implementations (tuple-based vs Vector2D-based)

### Docs

- **Fixed 12 documentation staleness issues**
    - `architecture.md`: rebuilt test suite table from actual files (was: stale counts + non-existent files)
    - `architecture.md`: added missing CLI flags (`--export-obj`, `--export-gltf`, `--export-blend`)
    - `architecture.md`: updated file structure to match actual codebase
    - `architecture.md`: removed stale `← NEW` markers
    - `architecture.md`: marked completed items in Deprecated/Future Work sections
    - `config-syntax.md`: fixed coordinate origin contradiction (was: front-face, now: back-face to match code)
    - `README.md`: updated test count (was: 332+, now: 401)
    - `implementation-plan.md`: marked Phase 4 as completed, Phase 5 as in progress

### Changed — BREAKING

- **Carcass construction: hollow box → 4 separate boards**
    - Each cabinet carcass is now 4 separate solid boxes (left, right, top, bottom)
    - 1mm technical gap between all boards — no shared surfaces
    - Each board: 8 vertices, 6 faces (was: 16 vertices, 17 faces for hollow box)
    - Manifest output: carcass now has child objects classified as `"board"`
    - Parent empty groups all boards for a cabinet

- **Door/drawer front position: back → front**
    - Fronts now positioned at Y=0 (front of cabinet) instead of Y=depth (back)
    - Fixes fronts appearing at the wrong end of the cabinet

- **Manifest classification: new `"board"` type**
    - Individual carcass panels are classified as `"board"` (was: `"carcass"`)
    - Parent empties remain `"carcass"` but have 0 vertices
    - Schema `manifest_v2.schema.json` updated with `"board"` enum value

### Added

- **Manifest-first pipeline** (primary output for every build)
    - `src/geometry_manifest.py` — JSON manifest export
    - `src/manifest_validator.py` — dimension, overlap, clearance checks
    - `schemas/manifest_v2.schema.json` — JSON Schema for manifest format
    - `scripts/validate_manifest.py` — standalone validation (no bpy)
    - `scripts/summarize_manifest.py` — LLM/human-friendly summary

- **Carcass construction details**
    - Board dimension tables in docs
    - Construction rules (butt joints, technical gaps)
    - Overlap detection with 50mm minimum threshold

### Removed

- **Deprecated inspection scripts** (replaced by manifest pipeline)
    - `scripts/analyze_reference_obj.py`
    - `scripts/convert_obj_to_gltf.py`
    - `scripts/analyze_gltf_v2.py`
    - `scripts/compare_with_reference.py`
    - `scripts/validate_obj.py`
    - `src/geometry_inspector.py`
    - `src/geometry_validator.py`

### Fixed

- Door/drawer fronts placed at back of cabinet instead of front
- Carcass missing floor face, inner side faces, and ceiling face
- Manifest not capturing vertex/face data (arrays were empty)
- World bounds not reflecting rotation transforms
- Validator turn mapping mismatch with geometry_builder.py
