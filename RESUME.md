# RESUME.md — Freeze re-entry point

> **Audience:** a zero-context future session. Read this after `AGENTS.md`.

---

## State summary

All six ADR-012 model extensions landed (663/663 root tests clean). The
ADR-010 deletion queue was **executed** (`115d953`) and the governance
rules merged into `AGENTS.md` (`f111dde`, tag retagged). ADR-011 rename
is done but the old BOM path (`calculate_cost` / `use_new_bom`) survives
in `kitchen-erp`. Frozen execution-status snapshot:
[`docs/freeze/MIGRATION-STATUS-2026-07.md`](docs/freeze/MIGRATION-STATUS-2026-07.md)
(immutable — this file is the living status doc).

**Post-freeze events** (not in any freeze doc):

- Catalog schema 1.5.0 — producer generalization ahead of Egger,
  catalog-internal ADR-004 (`cc69f4c`, 2026-07-04) + fallout fixes
  (`e7c6808`, 2026-07-05).
- `kuchnie_core` moved to its own component home `kuchnie-core/`
  (`69e09c6`, 2026-07-05).
- Cold-review findings F1–F6 fixed TDD-style with execution-path seam
  tests (`afd7e04`, 2026-07-07): serialize round-trip rehydration,
  edging lengths from stored bands, Blum hinge defaults on the YAML
  path, LEGRABOX runner axes/stacking/aliasing, adapter constructor
  drift + first adapter tests (fake-bpy), generic `panel_to_dxf`
  consumer for machining ops. Key new seam suites:
  `kuchnie-core/tests/test_execution_paths.py`,
  `kitchen-cam/tests/{test_yaml_path_drilling,test_panel_dxf}.py`,
  `home-builder-adapter/tests/`.

---

## Read order

`AGENTS.md` → **this file** → `docs/freeze/DOC-TRUST-REPORT.md` →
the ADR of your workstream. (Historical freeze state:
`docs/freeze/MIGRATION-STATUS-2026-07.md`.)

---

## Resume menu (priority order)

### 0. ~~Execute Part C — merge governance rules into AGENTS.md~~ — DONE (commit `f111dde`, `freeze-2026-07` retagged)

### 1. ~~Execute ADR-010/012 deletion queue~~ — DONE (commit `115d953`)

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

### 4. ~~Write tests for home-builder-adapter~~ — DONE (commit `afd7e04`)

13 tests via fake-bpy `tests/conftest.py`: extraction unit tests, the
extract → JSON → decompose contract test, and CLI argv/open-mainfile
tests. The extract/cli constructor-drift bugs they exposed are fixed in
the same commit. Orphaned `tests/__pycache__/` cleaned.

**ADR:** `docs/adr/009-kitchen-plugin-becomes-home-builder-adapter.md`

### 5. DECISION — ADR candidate: krono-promotion

`krono-compositor-mvp/src/compositor/presentation/catalog_db.py` is a
hardcoded material dict (6 materials, 2 price groups). Contradicts
ADR-008 (catalog as single source of truth). Decision needed: rename
`krono-compositor-mvp` off the `-mvp` suffix; route `catalog_db.py` to
the catalog service.

### 6. DECISION — ADR candidate: pydantic-boundary

`kuchnie-core/src/kuchnie_core/schema.py` uses `pydantic.BaseModel` at the YAML/JSON
boundary. `model.py` uses plain dataclasses. ADR-012 alt 12a says
"no Pydantic dep by design." Dependency now declared in `pyproject.toml`.
Decision: keep Pydantic at schema boundary, or refactor out.

### 7. Post-deletion housekeeping

- ~~After (1): rewrite `kitchen-cam/README.md`, `ROADMAP.md`,~~
  ~~`docs/specs/overview.md` (currently STALE-stamped).~~ **DONE** (commit
  `8c5ba33`; `docs/specs/overview.md` did not exist).
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

> ADRs record decisions, not state. For state, read **this file** —
> the single living status doc — and verify against code. Freeze-dated
> docs under `docs/freeze/` are immutable snapshots, never updated. Any
> document's claim about code is stale until re-verified in your session.
