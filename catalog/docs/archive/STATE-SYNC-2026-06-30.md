# State Sync — 2026-06-30

## What happened since last session

The project was **massively refactored** from Node.js/YAML to Python/FastAPI/SQLite.

### Key commits (chronological):
1. `548221a` — Material Master Catalog + bridge module
2. `a48eb0c` — FastAPI REST API over SQLite (6 endpoints, 30 tests)
3. `444534a` — Connect frontend to FastAPI API
4. `8098f6f` — Remove Node.js prototype, keep Python/FastAPI pipeline
5. `caeae64` — Consolidate scattered files into catalog/
6. `3faa7ba` — Kitchen configurator sessions, API endpoints, tests
7. `51d9d93` — Seed pairings (136) and edges (69)
8. `807d68e` — Phase 2: worktop_compatibility + curated_kitchens

### Architecture shift:
```
BEFORE (our session):  YAML → Node.js build.js → catalog.json → Alpine.js
AFTER (current):       YAML → Python importer → SQLite → FastAPI API → Alpine.js
```

## Current State (verified from code + DB)

### Stack
- **Backend**: Python 3.13 + FastAPI + SQLite (aiosqlite)
- **Frontend**: Alpine.js (still at catalog/public/index.html)
- **DB**: catalog/db/catalog.db (28 tables, 8 views)
- **Tests**: pytest, 4081 lines across 10 test files

### Database (live counts)
| Table | Count |
|-------|-------|
| producers | 2 (kronospan, swiss_krono) |
| collections | 7 |
| materials | 7 |
| decors | 148 (108 kronospan + 40 swiss_krono) |
| variants | 186 |
| structures | 49 |
| edges | 69 |
| pairings | 145 |
| worktop_specs | 12 |
| worktop_compatibility | 6626 |
| curated_kitchens | 8 |
| configurator_sessions | 0 |

### API Endpoints (6 routers)
| Router | Prefix | Purpose |
|--------|--------|---------|
| producers | /catalog/producers | Producer CRUD |
| decors | /catalog/decors | Decor + variant queries |
| worktops | /catalog/worktops | Worktop specs |
| availability | /catalog/availability | Variant availability |
| admin | /catalog/admin | Import, stats, images |
| configurator | /sessions | 6-step kitchen wizard |

### Data Files
| File | Decors | Variants |
|------|--------|----------|
| data/kronospan_full.yaml | 108 | 146 |
| data/kronoswiss_full.yaml | 40 | ~40 |
| data/kronospan_sample.yaml | (sample) | — |

### Docs
| Path | Content |
|------|---------|
| docs/ROADMAP.md | Phase 1 ✅, Phase 2 📋, Phase 3 ❄️ |
| docs/CHANGELOG.md | Keep a Changelog format |
| docs/README.md | Scope guardrails |
| docs/adr/001-pairings-as-decor-relations.md | Pairing = decor→decor |
| docs/adr/002-configurator-session-fk-strategy.md | Session FK design |
| docs/architecture/01-05*.sql | Schema evolution phases |
| docs/architecture/multi-producer-strategy.md | Kronospan vs Egger |
| docs/specs/configurator-api.md | Configurator spec |
| docs/materials/players.md | European manufacturer landscape |

### Scripts
| Script | Purpose |
|--------|---------|
| scripts/seed.py | Main seed from YAML |
| scripts/importer.py | YAML → SQLite importer |
| scripts/seed_pairings_edges.py | 136 pairings + 69 edges |
| scripts/seed_worktop_compat.py | 6626 worktop compat rows |
| scripts/seed_curated_kitchens.py | 8 reference templates |
| scripts/generate_variants.py | Generate chipboard variants |
| scripts/merge_global_collection.py | Merge 174 Global Collection |
| scripts/build_image_map.py | Map decor images |

## What's different from our session

| Our design | Current state | Delta |
|------------|---------------|-------|
| Node.js build.js | Python importer.py | ✅ Better |
| YAML → JSON pipeline | YAML → SQLite → API | ✅ Better |
| Zod validation | Pydantic models | ✅ Same concept |
| 177 decors / 180 variants | 148 decors / 186 variants | ⚠️ Different count |
| decors.yaml (single) | kronospan_full.yaml + kronoswiss_full.yaml | ✅ Multi-producer |
| Frontend reads JSON | Frontend reads API | ✅ Better |
| No configurator | 6-step configurator wizard | ✅ New |
| No pairings in DB | 145 pairings seeded | ✅ New |
| No worktop specs | 12 worktop specs + 6626 compat | ✅ New |
| Design-only schema docs | schema.sql in db/ (28 tables) | ✅ Implemented |

## Remaining from our plan

| Plan item | Status |
|-----------|--------|
| SQLite schema | ✅ Implemented (db/schema.sql) |
| Pydantic models | ✅ Implemented (models/domain.py) |
| FastAPI API | ✅ Implemented (api/routers/) |
| Pairings | ✅ 145 seeded |
| Worktops | ✅ 12 specs seeded |
| Egger data | ❌ Not yet |
| Swiss-Krono data | ✅ 40 decors in DB |
| Configurator | ✅ Phase 1 done |
| Curated kitchens | ✅ 8 templates |
| Frontend API integration | ✅ Done |

## Next steps (from ROADMAP.md)

Phase 2 (current):
- [ ] Wire `from_template` endpoint with real data
- [ ] Tests for template flow

Phase 3 (future):
- [ ] style_tags + decor_style_tags tables
- [ ] Compare 3 options side-by-side
- [ ] Shareable session links
- [ ] Price calculation
