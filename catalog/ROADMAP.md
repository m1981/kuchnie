# ROADMAP — catalog

## Phase 1: Configurator API (MVP)

| # | Task | Status |
|---|---|---|
| 1 | Spec: `docs/specs/configurator-api.md` | ✅ |
| 2 | Schema: add `configurator_sessions` table | ✅ |
| 3 | Models: `ConfiguratorSession`, `ConfiguratorOption`, `ConfiguratorBOM` | ✅ |
| 4 | Repository: `configurator.py` — session CRUD + step logic | ✅ |
| 5 | Router: `configurator.py` — 6 endpoints | ✅ |
| 6 | Tests: `test_configurator.py` — 20 test cases | ✅ |
| 7 | Pairings seed: ensure test data exists | ✅ |
| 8 | Verify: all tests pass, no regressions | ✅ |
| 9 | ADR-002: FK strategy | ✅ |
| 10 | CHANGELOG | ✅ |
