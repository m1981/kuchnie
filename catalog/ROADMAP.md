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

## Phase 2: Curated content

| # | Task | Status |
|---|---|---|
| 1 | Seed `worktop_compatibility` table (front ↔ worktop matches) | 📋 |
| 2 | Seed `curated_kitchens` (8 reference templates) | 📋 |
| 3 | Wire `from_template` endpoint with real data | 📋 |
| 4 | Tests for template flow | 📋 |

## Phase 3: Smart UX (future)

| # | Task | Status |
|---|---|---|
| 1 | `style_tags` + `decor_style_tags` tables | ❄️ |
| 2 | Compare 3 options side-by-side | ❄️ |
| 3 | Shareable session links | ❄️ |
| 4 | Price calculation (`variant_prices` table) | ❄️ |
