# ROADMAP — catalog

## Phase 1: Configurator API (MVP) ✅

| # | Task | Status |
|---|---|---|
| 1 | Spec: `docs/specs/configurator-api.md` | ✅ |
| 2 | Schema: add `configurator_sessions` table | ✅ |
| 3 | Models: `ConfiguratorSession`, `ConfiguratorOption`, `ConfiguratorBOM` | ✅ |
| 4 | Repository: `configurator.py` — session CRUD + step logic | ✅ |
| 5 | Router: `configurator.py` — 6 endpoints | ✅ |
| 6 | Tests: `test_configurator.py` — 20 test cases | ✅ |
| 7 | Pairings seed: 136 carcass pairings (front → K110) | ✅ |
| 8 | Edge seed: 69 edges + 69 variant-edge links from obrzeze | ✅ |
| 9 | Verify: 227 tests pass, 0 regressions | ✅ |
| 10 | ADR-002: FK strategy | ✅ |
| 11 | CHANGELOG | ✅ |

## Phase 2: Curated content ✅

| # | Task | Status |
|---|---|---|
| 1 | Seed `worktop_compatibility` (6626 rows) | ✅ |
| 2 | Seed `curated_kitchens` (8 templates, 6 featured) | ✅ |
| 3 | `from_template` endpoint working | ✅ |
| 4 | `TemplateOut` model with `featured` field | ✅ |

## Phase 3: Smart UX

| # | Task | Status |
|---|---|---|
| 1 | Seed `decor_style_tags` (359 associations) | ✅ |
| 2 | Style filter: `?style=scandinavian` on options | ✅ |
| 3 | Compare endpoint: `GET /compare?ids=...` | ✅ |
| 4 | Session state: `GET /sessions/{token}` for shareable links | ✅ |
| 5 | Price calculation (`variant_prices` table) | ❄️ |
