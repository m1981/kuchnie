# Changelog

All notable changes to `kuchnie-core` are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/).

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
