# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- Builder GUI: sidebar gaps closed per ADR-005 (all advisory, none blocking)
  - Slot focus soft-filters the grid by role; clearing a slot re-filters (S5);
    role mismatch shows a ⚠ line but the assignment stands
  - Backend sync: pairing recommendations (★ polecane, float to top) for the
    chosen front; "Eksportuj BOM" replays the composition into a configurator
    session and downloads the server BOM with a shareable session token;
    discontinued decors flagged on cards and in the summary
  - Two-tone flow: wall_front advances right after base_front with an explicit
    "pomiń — jednokolorowa" skip; the decision persists in localStorage and
    in saved templates
- Verified in-browser (Playwright, 30 checks): slot advance, skip, S5
  filtering, recommendations, backend BOM, reload persistence, and
  grid↔sidebar color/code consistency

### Fixed

- Builder GUI: `parseRoles()` crashed on the list-typed `roles` from
  `/catalog/full` — role chips never rendered and every slot showed a false
  role-mismatch warning
- Decor swatch colors: `/catalog/full` now returns `color_hex`
  (`color_families.hex_approx`) and the builder uses it as the source of
  truth instead of a partial hardcoded JS map — Kość Słoniowa rendered gray
- Data: 0514 Kość Słoniowa szary→kremowy, 0515 Piaskowy szary→bezowy
  (`kronospan_full.yaml` + live DB)

- `docs/adr/005-sidebar-free-composition-over-wizard.md` — builder sidebar's
  top-level motivation is "templates make repeat work cheap": free
  composition + templates over the backend's rigid wizard flow; spec
  `builder-gui.md` now references it

## [0.4.0] — 2026-07-04

### Changed

- Schema 1.5.0 — producer generalization ahead of Egger onboarding (ADR-004):
  - `pairing_types` lookup table replaces the `pairings.pairing_type`
    CHECK enum (producer-branded types are now data, not DDL)
  - `decors.one_global` / `decors.new_2024` columns removed; stored as
    `decor_tags` (`one-global`, `new-2024`); `v_decors_full` recomputes
    both columns, so the API contract is unchanged
  - `variants.producer_sku` added (producer's own article number,
    unique when present)
  - `variants.multi_structures` deprecated (expand to per-structure
    variants instead)
- `init_schema()` auto-migrates pre-1.5.0 databases
  (`scripts/migrate_1_5_0.py`; incremental
  `docs/architecture/06-phase5-producer-generalization.sql`)

### Added

- `docs/adr/004-producer-generalization-for-egger.md` — incl. Egger
  variant `business_id` grammar (`U702-EU-18-ST9`)
- `tests/test_phase5_producer_generalization.py` (8 tests; suite 227 → 235)

## [0.3.0] — 2026-07-01

### Added

- Builder GUI walking skeleton (`public/index.html` rewrite)
  - Grid + sidebar layout (catalog left, kitchen assembly right)
  - 4 slots: base_front, wall_front, carcass, worktop
  - Click card → assign to active slot → advance to next empty
  - localStorage persistence (save/restore state + templates)
  - "Zapisz jako szablon" saves to localStorage
  - "Eksportuj BOM" downloads JSON
  - Search, producer/material/color/role filters
- `docs/specs/builder-gui.md` — walking skeleton spec
- `docs/scenarios-edge-cases.md` — 6 scenarios + 10 edge cases
- `public/mockup-builder.html` — reference mockup

### Changed

- Schema version bumped to 1.4.0 (4 new tables: worktop_compatibility,
  style_tags, decor_style_tags, curated_kitchens)

## [0.2.0] — 2026-06-30

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
