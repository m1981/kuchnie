# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- Style filter on configurator options: `?style=scandinavian`
- Compare endpoint: `GET /configurator/compare?ids=K003-CH-18-FP,K190-CH-18-PE`
- Session state endpoint: `GET /configurator/sessions/{token}` for shareable links
- `scripts/seed_decor_style_tags.py` — 359 decor-style associations
- `scripts/seed_worktop_compat.py` — 6626 worktop compatibility rows
- `scripts/seed_curated_kitchens.py` — 8 reference kitchen templates
- `style_tags`, `decor_style_tags`, `curated_kitchens`, `worktop_compatibility` tables

## [0.2.0] — 2026-06-30

### Added

- Configurator API (Phase 1 MVP) — 6-step kitchen material wizard
  - `configurator_sessions` table in `db/schema.sql`
  - 6 endpoints: `POST /sessions`, `GET .../options`, `PATCH .../select`,
    `GET .../bom`, `GET /templates`, `POST .../from_template`
  - `repositories/configurator.py` — session CRUD + step logic
  - `models/domain.py` — 6 Pydantic models (`SessionOut`, `SelectRequest`,
    `ConfiguratorOption`, `ConfiguratorStepOut`, `BOMOut`, `TemplateOut`)
  - `tests/test_configurator.py` — 20 test cases
  - `docs/specs/configurator-api.md` — full spec
  - `docs/adr/002-configurator-session-fk-strategy.md` — FK design decision
- Configurator data seeding
  - `scripts/seed_pairings_edges.py` — 136 carcass pairings + 69 edges
  - `scripts/importer.py` — `import_edges()` method for edges + variant_edges
- Catalog data expansion
  - `scripts/merge_global_collection.py` — merges 174 Global Collection decors
  - `scripts/generate_variants.py` — generates chipboard 18mm variants (46 new)
- `public/index.html` — "brak zdjęcia" placeholder for cards without images
- `docs/README.md` — scope guardrails + documentation index
- `docs/adr/001-pairings-as-decor-relations.md` — pairing design rationale
- `docs/architecture/multi-producer-strategy.md` — Kronospan vs Egger comparison

### Changed

- `data/kronospan_full.yaml` — 108 decors (was 62), 146 variants (was 100)
- `db/catalog.db` — 148 decors, 186 variants, 58 Kronospan images,
  145 pairings, 69 edges, 69 variant-edge links
- Extracted `docs/02-data-model.md` into ADR + architecture docs (deleted original)

### Fixed

- `public/index.html` — `selected.express` null guard (Alpine.js error on click)
- `api/routers/admin.py` — edge query uses integer variant PK instead of string
- `public/index.html` — cards without images show "brak zdjęcia" instead of blank

## [0.1.0] — 2026-06-28

### Added

- Initial catalog API (producers, decors, variants, worktops, availability, admin)
- SQLite schema with 21 tables, 5 views
- YAML importer (`scripts/importer.py`)
- Alpine.js frontend with filtering, search, detail overlay
- 30 API tests
- Kronospan + Swiss Krono producer data
