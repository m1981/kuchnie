# RESUME.md — Freeze re-entry point

> **Audience:** a zero-context future session. Read this after `AGENTS.md`.

---

## State summary

All six ADR-012 model extensions landed (663/663 root tests clean). The
ADR-010 deletion queue (`kitchen_cam.models`, `panel_calculator`,
`csv_generator`) is **unblocked** — 13 xpasses in kitchen-cam confirm
field parity. ADR-011 rename is done but the old BOM path
(`calculate_cost` / `use_new_bom`) survives in `kitchen-erp`. Full
execution status: [`MIGRATION-STATUS.md`](MIGRATION-STATUS.md).

---

## Read order

`AGENTS.md` → **this file** → `MIGRATION-STATUS.md` →
`docs/freeze/DOC-TRUST-REPORT.md` → the ADR of your workstream.

---

## Resume menu (priority order)

### 1. Execute ADR-010/012 deletion queue — UNBLOCKED

Rewire `kitchen-cam/src/kitchen_cam/machining.py` to import from
`kuchnie_core.model` instead of `kitchen_cam.models`. Delete the
deprecated trio: `kitchen_cam/{models,panel_calculator,csv_generator}.py`.
Rewrite `kitchen-cam/tests/conftest.py` and `test_compare.py` fixtures to
build `kuchnie_core.CabinetInstance` / `Kitchen` directly. The 13 xpasses
confirm parity. **Must be one atomic commit** (see session handoff
atomic-commit warning about `PanelRole` existing in both namespaces).

**ADR:** `docs/adr/010-kitchen-cad-becomes-kitchen-cam.md`
+ `docs/adr/012-kuchnie-core-model-extensions.md`

### 2. Repair kitchen-erp tests + delete old BOM path

Fix `tests/test_rules_engine.py` `HARDWARE_RULES` import error. Fix
SQLAlchemy fixture teardown in `test_bom_generator.py` and
`test_integration_bom.py`. Then delete: `Cabinet.calculate_cost`
(`kitchen-erp/kitchen_erp/core/models.py:106`), `use_new_bom` field +
`set_use_new_bom` + non-`_new` trace methods
(`kitchen-erp/kitchen_erp/ui/state.py:108,412–499`), toggle switch
(`kitchen-erp/kitchen_erp/kitchen_erp.py`). Keep only the `_new`-suffixed
methods and drop the suffix.

**ADR:** `docs/adr/011-kitchen-app-becomes-kitchen-erp.md`

### 3. ADR-011 follow-up: BOMGenerator → kuchnie_core.decompose()

Wire `BOMGenerator.generate()` to call `kuchnie_core.decompose(cabinet)`.
Make `kitchen_erp.Material` a local cache/mirror of `catalog/` data
(ADR-008/011 declared intent). Add `kuchnie_core` import to kitchen-erp
(currently zero code imports — only a docstring reference).

**ADR:** `docs/adr/011-kitchen-app-becomes-kitchen-erp.md`

### 4. Write tests for home-builder-adapter

`home-builder-adapter/src/extract.py` (148 LOC) and `cli.py` (36 LOC)
have **zero tests**. Old 23-file suite was deleted in commit `8da1a61`
"Phase d"; only `tests/__init__.py` survived. 23 orphaned `.pyc` files
under `tests/__pycache__/` should be cleaned.

**ADR:** `docs/adr/009-kitchen-plugin-becomes-home-builder-adapter.md`

### 5. DECISION — ADR candidate: krono-promotion

`krono-compositor-mvp/src/compositor/presentation/catalog_db.py` is a
hardcoded material dict (6 materials, 2 price groups). Contradicts
ADR-008 (catalog as single source of truth). Decision needed: rename
`krono-compositor-mvp` off the `-mvp` suffix; route `catalog_db.py` to
the catalog service.

### 6. DECISION — ADR candidate: pydantic-boundary

`src/kuchnie_core/schema.py` uses `pydantic.BaseModel` at the YAML/JSON
boundary. `model.py` uses plain dataclasses. ADR-012 alt 12a says
"no Pydantic dep by design." Dependency now declared in `pyproject.toml`.
Decision: keep Pydantic at schema boundary, or refactor out.

### 7. Post-deletion housekeeping

- After (1): rewrite `kitchen-cam/README.md`, `ROADMAP.md`,
  `docs/specs/overview.md` (currently STALE-stamped).
- After (3): rename kitchen-erp recipes to "cost recipes" to kill name
  collision with `kuchnie_core/recipe.py`.

---

## DO-NOT list

| Don't | Why |
|---|---|
| Add features to `kitchen_cam.{models,panel_calculator,csv_generator}` | Deprecated — deletion queue (ADR-010/012) |
| Extend the old BOM path (`calculate_cost` / `use_new_bom`) | Superseded by recipe-based `BOMGenerator` (ADR-011) |
| Extend `krono/catalog_db.py` | Hardcoded dict; contradicts ADR-008. Needs krono-promotion decision |
| Touch `home_builder_5/` | External licensed addon, per F007 Rule 4 |
| Trust STALE-stamped docs | Re-verify any claim against code before acting on it |

---

## Environment notes

- `catalog/.venv` has no `pytest` installed — use root `.venv` to run
  catalog tests (see `docs/freeze/TEST-BASELINE-2026-07.md` N1).
- `home-builder-adapter/tests/__pycache__/` has 23 orphaned `.pyc` files
  from the deleted test suite — safe to `rm`.

---

## Trust rule

> ADRs record decisions, not state. For state, read
> `MIGRATION-STATUS.md` and verify with the commands it lists. Any
> document's claim about code is stale until re-verified in your session.
