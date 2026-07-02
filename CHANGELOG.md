# Changelog

All notable changes to `kuchnie-core` are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/).

---

## [Unreleased] — 2026-07-01 — Architecture decisions codified

### Added — ADR-010 partial execution (safe, additive)

- `kuchnie_core.export.edging_csv` — per-edge banding worklist CSV. One row per banded edge across the kitchen. Same Polish CNC format as `cutlist_csv` (UTF-8-SIG BOM, `;` delimiter, Polish headers). Migrated semantically from `kitchen_cam.csv_generator.generate_edging_csv` but rewritten against `kuchnie_core.model.Panel.banded_edges` (dict-keyed) instead of the deprecated `kitchen_cam.models.Panel.edges` (list-with-side).
- `tests/test_edging_csv.py` — 8 tests covering row collection, edge-length rule (front/back → width; left/right → height), Polish header, UTF-8-SIG BOM, semicolon delimiter, round-trip. Also a regression guard for `cutlist_csv` Polish format.
- Deprecation banners on `kitchen-cam/src/kitchen_cam/{models,panel_calculator,csv_generator,machining}.py` pointing at ADR-012 as the unblocking work.

### Decided — ADR-012

- **ADR-012**: enumerates the `kuchnie_core.model` extensions required to execute the remaining ADR-010 steps (delete `kitchen_cam.models` / `panel_calculator` / `csv_generator`, rewrite `machining.py`). Extensions: `PanelRole` enum, `MachiningOp.face`/`drill_type`, `HingeGeometry`, `HandleSpec`, `ShelfPinSpec`, discriminated `CabinetInstance.config` union. Migration is BLOCKED on this — attempted mechanical rewrite fails to import.

### Decided (documented, not yet executed)

- **ADR-009**: `kitchen-plugin/` → `home-builder-adapter/`. Ports & Adapters pattern. Pure code (geometry, standards, construction math, manifest validator) migrates into `kuchnie_core/`. `bpy`-dependent extraction stays isolated as an anti-corruption layer against `home_builder_5` (external, licensed).
- **ADR-010**: `kitchen-cad/` → `kitchen-cam/`. Downstream consumer of `kuchnie_core`. Duplicate Panel / CabinetInstance / Hinge / Drawer models deleted. Package keeps System32 drilling and DXF generation only; CSV cut list merges into `kuchnie_core.export`. **Partially executed**: CSV merge done (see above). Model migration blocked on ADR-012.
- **ADR-011**: `kitchen-app/` → `kitchen-erp/`. Accept ERP scope (BOM, purchasing, rules, admin). Sales-tool role explicitly reassigned to `krono-compositor-mvp/`. Old (non-recipe) BOM path deleted; `use_new_bom` flag removed.

Execution plan: phases B–F in session handoff notes. Rename phase (Phase C, commit `8e85da1`) complete. Model migration deferred to ADR-012.

---

## 2026-06-30 — Catalog consolidation

### Moved

- `data/materials/` → `catalog/data/materials/` (YAML source data + build pipeline)
- `docs/materials-boards/` → `catalog/docs/materials/` (source PDFs + markdown specs)
- `scripts/convert-global-collection.js` → `catalog/scripts/` (conversion script)

### Updated

- `catalog/package.json` — build/test scripts now run from catalog/ directly
- `catalog/data/materials/build.js` — fixed output path to `catalog/public/`
- `catalog/AGENTS.md` — updated directory structure diagram
- `catalog/Makefile` — simplified paths (no more `cd ..`)
- `catalog/docs/architecture/` — updated path references

### Verified

- 78/78 catalog validation tests pass
- 110/110 root tests pass
- `make build`, `make test`, `make validate` all pass

---

## 2026-06-24 — Walking skeleton + LEGRABOX + Kitchen model

### Architecture decisions

See `docs/adr/` for full rationale:

- ADR-001: Panel is the atomic manufacturing unit
- ADR-002: Construction method separated from cabinet instance (Polyboard pattern)
- ADR-003: Kitchen is the unit of work flowing through the system
- ADR-004: Intermediate format is logical description, not physical panels
- ADR-005: MachiningOp is a first-class object on Panel
- ADR-006: LEGRABOX LW = KB − 2×13mm runner clearance
- ADR-007: LEGRABOX drawer box panels are 16mm chipboard

### Added

**Core engine** (`src/kuchnie_core/`):

- `model.py` — Panel, EdgeBand, MachiningOp, Accessory, CabinetInstance, DecompositionResult
- `model.py` — Kitchen, Row, WorktopSegment (kitchen-level models)
- `catalog.py` — 3 cabinet types: `dolna_szufladowa`, `gorna_drzwiowa`, `dolna_legrabox`
- `decomposer.py` — thin dispatcher from CabinetInstance → panels via catalog
- `bom.py` — per-cabinet costed BOM (panels + edge banding + accessories)
- `kitchen.py` — kitchen-level aggregation (all_panels, kitchen_bom, validate_rows)
- `loader.py` — YAML → CabinetInstance, YAML → Kitchen
- `serialize.py` — Kitchen ↔ JSON round-trip (intermediate format)
- `export/cutlist_csv.py` — aggregated cut list CSV (semicolon-separated)
- `legrabox.py` — LEGRABOX catalog (heights, NL matrix, formulas, validation, drawer box decomposition, runner mounting drill ops)

**Fixtures** (`fixtures/`):

- `K01.yaml` — base cabinet with 2 metabox drawers
- `G01.yaml` — wall cabinet with 2 doors
- `K02_legrabox.yaml` — base cabinet with 2 LEGRABOX C drawers (NL=500)
- `kitchen_01.yaml` — minimal test kitchen (1 row, 2 cabinets)

**Tests** (`tests/`):

- 84 tests passing across 6 test files
- Decomposition tests (K01: 16 tests, G01: 19 tests)
- LEGRABOX tests (24 tests — formulas, validation, full cabinet integration)
- Kitchen model tests (10 tests — loading, aggregation, row validation)
- Serialize tests (8 tests — JSON round-trip, self-contained format)
- Cut list tests (7 tests — aggregation, CSV output, total quantity)

### Fixed

- Drawer box panel thickness: was 3mm/12mm, corrected to **16mm** per Blum spec (ADR-007)
- LW formula: was subtracting `2 × side_thickness`, corrected to `2 × 13mm` runner clearance (ADR-006)

### Design patterns applied

- **Polyboard pattern**: Construction method as first-class entity (ADR-002)
- **Winner Flex pattern**: Material decoupled from construction
- **Anti-corruption layer**: Intermediate format isolates design from manufacturing (ADR-004)

---

## 2026-06-27 — Material Master Catalog (Kronospan + Swiss Krono)

### Architecture decisions

- ADR-008: Material Master Catalog — separate bounded context from project domain
- ER diagram: `catalog/docs/architecture/04-er-diagram.md` (32 entities, 2 bounded contexts)
- Schema: 6 incremental migrations (`01-schema.sql` through `05-phase4b-property-flags.sql`)

### Added

**Catalog schema** (`catalog/docs/architecture/`):

- 21 tables: producers, structures, collections, subcollections, materials,
  material_types, decors, variants, worktop_constructions, worktop_profiles,
  worktop_specs, sheet_formats, edges, edge_suppliers, variant_edges,
  decor_structures, pairings, variant_availability, property_flags,
  color_families, tags, decor_tags
- 9 views: v_decors_full, v_pairings_full, v_worktops_full,
  v_synchro_variants, v_variants_availability, v_property_flags,
  v_decor_structures_full
- 13 indexes

**Catalog importer** (`catalog/scripts/`):

- `importer.py` — CatalogImporter class (11 import methods, FK validation, idempotent)
- `generate_kronospan_yaml.py` — YAML generator from Kronospan data
- `generate_kronoswiss_yaml.py` — YAML generator from Swiss Krono data

**Catalog data** (`catalog/data/`):

- `kronospan_full.yaml` — 62 decors, 11 variants, 6 worktops, 69 junction rows,
  5 pairings, 11 availability, 10 property flags
- `kronoswiss_full.yaml` — 40 decors, 10 variants, 6 worktops, 40 junction rows,
  4 pairings, 5 availability, 12 property flags

**Material analysis** (`docs/materials-boards/`):

- Kronospan: 20 markdown spec files (Global Collection, MDF, Acrylic, Mirror,
  Metal, HDF, HPL, Emporio, Kaindl, Focus, Rocko Tiles, blaty 4 collections)
- Swiss Krono: 3 markdown spec files (laminated boards, worktops, BE Velvet)
- PDF page exports for visual reference

**Tests** (`catalog/tests/`):

- 177 tests passing across 7 test files (catalog schema + import)
- Phase 1: 32 tests — worktop specs, sheet formats, subcollections
- Phase 2: 28 tests — decor_structures junction, pairings expansion
- Phase 3: 33 tests — importer (per-entity + full import + validation)
- Import: 45 tests — Kronospan + KronoSwiss + cross-catalog
- Phase 4a: 21 tests — variant availability (Express 24h, konfekcja)
- Phase 4b: 18 tests — property flags (antibacterial, waterproof, etc.)

**Materials bridge** (`src/kuchnie_core/materials/`):

- `models.py` — 5 frozen DTOs: VariantInfo, EdgeInfo, WorktopInfo, PropertyFlag, AvailabilityInfo
- `exceptions.py` — 3 domain exceptions: MaterialNotFoundError, EdgeNotFoundError, CatalogUnavailableError
- `protocol.py` — MaterialCatalog Protocol (runtime_checkable, 4 methods)
- `sqlite_repository.py` — SqliteMaterialCatalog (lazy connection, PRAGMA query_only)
- `resolver.py` — MaterialResolver (cached facade, LRU-style dict cache)
- `__init__.py` — public API with __all__ exports
- 26 tests: protocol conformance, SQLite reads, caching, FakeCatalog for engine tests

**ADR** (`docs/adr/`):

- ADR-008: Material Master Catalog — 7 decisions (bounded contexts, EAV, junction tables, Protocol pattern)

### Fixed

- `structures.code UNIQUE` column-level constraint blocked same code per producer
  (e.g. Kronospan SM vs KronoSwiss SM). Removed column-level UNIQUE,
  kept only `UNIQUE(code, producer_id)` composite.

### Key entities

| Entity | Kronospan | KronoSwiss | Total |
|--------|-----------|------------|-------|
| Decors | 62 | 40 | 102 |
| Variants | 11 | 10 | 21 |
| Worktop specs | 6 | 6 | 12 |
| Structures | 26 | 23 | 49 |
| Pairings | 5 | 4 | 9 |
| Availability | 11 | 5 | 16 |
| Property flags | 10 | 12 | 22 |

### Design patterns applied

- **Bounded contexts**: Catalog (material master) vs Project (customer kitchen)
- **EAV pattern**: property_flags table prevents schema bloat
- **Junction table**: decor_structures replaces CSV multi_structures column
- **Bridge by business_id**: Project references Catalog via string codes, not FK
- **Idempotent migrations**: CREATE TABLE IF NOT EXISTS + INSERT OR IGNORE

---

## Next (planned)

- [ ] Add remaining cabinet types from taxonomy (corner blind, corner internal, sink, cargo, oven)
- [ ] Fill in complete runner screw position table (all NL values from Blum PDF)
- [ ] Confirm M and F back panel heights from Blum PDF sheets
- [ ] Shelf pin System32 drill operations on side panels
- [ ] Handle boring drill operations on front panels
- [ ] DXF export (panels + machining ops → DXF files for CNC)
- [ ] Dimension constraints per cabinet type (min/max, auto-correction)
- [ ] Blender render service (FastAPI + headless Blender)
- [ ] kitchen-plugin web app (Svelte layout editor)
- [ ] ADR-008: Material Master Catalog decision record  ✅ DONE
- [ ] ADR-009: Worktop construction types
- [ ] Full YAML data: expand to 174 Kronospan + 174 KronoSwiss decors
- [x] Bridge module: `src/kuchnie_core/materials/` — Python API over catalog SQLite  ✅ DONE
- [ ] Catalog REST API (FastAPI) — parallel agent in progress
- [ ] Catalog frontend (Svelte) — parallel agent in progress
