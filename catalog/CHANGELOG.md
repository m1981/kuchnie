# CHANGELOG

## 2026-06-30

### Added — Configurator API (Phase 1 MVP)

- `configurator_sessions` table in `db/schema.sql` — stores wizard state
  (front/carcass/worktop/edge/side_panel/plinth selections)
- 6 API endpoints (`POST /configurator/sessions`, `GET .../options`,
  `PATCH .../select`, `GET .../bom`, `GET /configurator/templates`,
  `POST .../from_template`)
- `repositories/configurator.py` — session CRUD + step logic (pairing-based
  carcass suggestions, fallback for all steps)
- `models/domain.py` — 6 new Pydantic models (`SessionOut`, `SelectRequest`,
  `ConfiguratorOption`, `ConfiguratorStepOut`, `BOMOut`, `TemplateOut`)
- `tests/test_configurator.py` — 20 test cases covering all endpoints
- `docs/specs/configurator-api.md` — full spec
- `docs/adr/002-configurator-session-fk-strategy.md` — decision to store
  business_id strings instead of integer FKs

### Changed — Catalog data expansion

- `data/kronospan_full.yaml` — 108 decors (was 62), 146 variants (was 100)
- `scripts/merge_global_collection.py` — merges Global Collection decors
  with image matching from PDF
- `scripts/generate_variants.py` — generates chipboard 18mm variants for
  decors missing them (46 new variants)
- `db/catalog.db` — 148 decors, 186 variants, 58 Kronospan images

### Fixed

- `public/index.html` — `selected.express` null guard
- `api/routers/admin.py` — edge query uses integer variant PK instead of
  string business_id
- `public/index.html` — "brak zdjęcia" placeholder for cards without images

### Docs — Reorganization

- Extracted `docs/02-data-model.md` into:
  - `docs/adr/001-pairings-as-decor-relations.md` — design rationale
  - `docs/architecture/multi-producer-strategy.md` — Kronospan vs Egger
  - `docs/README.md` — scope guardrails + index
- Deleted `docs/02-data-model.md` (content preserved in ADR + architecture)

---

## Earlier

See git history for changes before this date.
