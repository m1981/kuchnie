# Migration Status — freeze-2026-07

> **Purpose.** Record execution status of ADR-008 through ADR-012 so no future
> session re-derives it. Each row is verified against code at HEAD.
> **Rule:** ADRs record decisions, not state. THIS file records state.

---

## ADR status table

| ADR | Commitment | Status | Evidence | Next action |
|---|---|---|---|---|
| **ADR-008** | Material catalog as separate bounded context (`catalog/`) | **DONE** | `catalog/db/catalog.db` exists (938 KB); 227 tests pass (`docs/freeze/TEST-BASELINE-2026-07.md`); `catalog/scripts/importer.py` populates it | None for the catalog itself. Parallel stores still survive — see "Known contradictions" |
| **ADR-009** | Rename `kitchen-plugin/` → `home-builder-adapter/`; domain IP → `kuchnie_core` | **MOSTLY DONE / DRIFTED** | Directory renamed. `extract.py` (148 LOC) + `cli.py` (36 LOC) import `kuchnie_core.model` (`home-builder-adapter/src/extract.py:29`). **Drift:** `pyproject.toml` still says `name = "kitchen-generator"`, `dependencies = []` despite importing `kuchnie_core` | Fix pyproject.toml (Part 2a) |
| **ADR-010** | Rename `kitchen-cad/` → `kitchen-cam/`; delete duplicated modules; make it downstream consumer of `kuchnie_core` | **RENAME DONE / DELETION PENDING** | Directory renamed. `machining.py` still imports `from kitchen_cam.models import ...` (`kitchen-cam/src/kitchen_cam/machining.py`). Deletion trio still present: `models.py`, `panel_calculator.py`, `csv_generator.py` (verified `ls`). 13 xpasses in kitchen-cam baseline confirm field parity reached. | Execute deletion queue — **UNBLOCKED** by ADR-012 completion |
| **ADR-011** | Rename `kitchen-app/` → `kitchen-erp/`; delete old BOM path; sales role → `krono-compositor-mvp` | **RENAME DONE / OLD BOM PATH NOT DELETED / KUCHNIE_CORE INTEGRATION NOT-STARTED** | Directory renamed. `kitchen_erp/ui/state.py` still has `use_new_bom` (line 108), `set_use_new_bom` (line 412), `calculate_cost` calls (lines 437, 499). `grep -rn kuchnie_core kitchen-erp/ --include="*.py"` returns only `__init__.py:11` docstring — zero code imports. | (1) Delete old BOM path. (2) Wire `BOMGenerator` → `kuchnie_core.decompose()` |
| **ADR-012** | Extend `kuchnie_core.model` with 6 extensions to unblock ADR-010 | **DONE** | §1 `PanelRole` (`5e03187`), §2 `MachiningOp.face/.drill_type` (`1603017`), §3 `HingeGeometry` (`d536f69`), §4 `HandleSpec` (`4621102`), §5 `ShelfPinSpec` (`ea7dc65`), §6 `CabinetConfig` union (`e3c0492`). 663/663 root tests pass (`docs/freeze/TEST-BASELINE-2026-07.md`). | None — fully complete |

---

## Parallel material stores (ADR-008 context)

| Store | Location | Fate per ADR | Status |
|---|---|---|---|
| `catalog/` SQLite | `catalog/db/catalog.db` | **Canonical** (ADR-008) | Active, 227 tests |
| `kitchen_erp` Material table | `kitchen_erp/kitchen_erp/core/models.py:6` `class Material(SQLModel, table=True)` | → mirror of catalog (ADR-011) | **NOT-STARTED** — still independent |
| `krono` catalog_db.py | `krono-compositor-mvp/src/compositor/presentation/catalog_db.py` | Frozen; contradicts ADR-008 (hardcoded dict with 6 materials, 2 price groups) | Needs "krono-promotion" decision — route to catalog service |

---

## Paused mid-step

| Item | Exact next command / file | Blocked by |
|---|---|---|
| ADR-010 deletion: rewrite `machining.py` | Rewrite imports in `kitchen-cam/src/kitchen_cam/machining.py` from `kitchen_cam.models` → `kuchnie_core.model` (must land in same commit as trio deletion — see session handoff atomic-commit warning) | Nothing — **UNBLOCKED** |
| ADR-010 deletion: delete trio | `rm kitchen-cam/src/kitchen_cam/models.py panel_calculator.py csv_generator.py` | Same commit as machining.py rewrite |
| ADR-010 deletion: rewrite tests | `kitchen-cam/tests/conftest.py` + `test_compare.py` fixtures → build `kuchnie_core.CabinetInstance` / `Kitchen` directly | Same commit |
| ADR-011 old BOM: delete `Cabinet.calculate_cost` | Remove method from `kitchen-erp/kitchen_erp/core/models.py:106`; remove callers in `kitchen_erp/ui/state.py` (lines 437, 499); drop `use_new_bom` field (line 108) and `set_use_new_bom` (line 412) | Nothing — **UNBLOCKED** |
| ADR-011 old BOM: remove toggle UI | Remove `rx.Switch` from `kitchen-erp/kitchen_erp/kitchen_erp.py` | Same commit as BOM path deletion |

---

## Known contradictions (repo reality vs accepted ADRs)

| Contradiction | ADR violated | Evidence |
|---|---|---|
| `home-builder-adapter/pyproject.toml` says `name = "kitchen-generator"`, `dependencies = []` but code imports `kuchnie_core` | ADR-009 | `pyproject.toml` vs `extract.py:29` |
| `machining.py` imports `kitchen_cam.models` (deprecated) | ADR-010 | `kitchen-cam/src/kitchen_cam/machining.py` imports |
| `Cabinet.calculate_cost` + `use_new_bom` toggle still live | ADR-011 (declares old path deleted) | `kitchen_erp/ui/state.py:108,412,437,499` |
| `krono/catalog_db.py` is a hardcoded material dict, not consuming `catalog/` | ADR-008 | `krono-compositor-mvp/src/compositor/presentation/catalog_db.py` |
| `kuchnie_core/pyproject.toml` declares `pydantic>=2,<3` but ADR-012 alt 12a says "no Pydantic dep by design" for the domain model | ADR-012 (tension, not violation) | `pyproject.toml` imports in `schema.py`; `model.py` is plain dataclasses |

---

## Findings not recorded in any ADR

### (a) home-builder-adapter has ZERO tests

Old test suite (23 files) deleted in commit `8da1a61 "Phase d"`. Only `tests/__init__.py` survived the rename. 23 orphaned `.pyc` files remain under `home-builder-adapter/tests/__pycache__/`. New `extract.py` (148 LOC) and `cli.py` (36 LOC) — 184 total — are **never tested**.

**Evidence:** `docs/freeze/TEST-BASELINE-2026-07.md` notes N5: "home-builder-adapter has no test sources."

### (b) kitchen-erp test suite broken mid-ADR-011

Baseline shows 38 pass / 3 fail / 13 errors / 1 collection error. Root cause: `test_rules_engine.py` imports `HARDWARE_RULES` from `kitchen_erp.core.rules_engine` but that symbol doesn't exist (`ImportError`). Remaining errors are SQLAlchemy fixture issues. **None of these are caused by the rename** — they pre-date it.

**Evidence:** `docs/freeze/TEST-BASELINE-2026-07.md` notes N2, N3.

### (c) Pydantic design tension

`kuchnie-core/src/kuchnie_core/schema.py:23` imports `from pydantic import BaseModel`. Meanwhile `kuchnie-core/src/kuchnie_core/model.py` uses plain dataclasses exclusively. ADR-012 alternative 12a rationale states: *"kuchnie_core uses plain dataclasses by design (no Pydantic dep, no runtime coercion)."* The split is intentional (Pydantic at the YAML/JSON schema boundary, dataclasses in the domain core) but undocumented. Dependency now declared in `pyproject.toml` (D1 from trust audit). Whether Pydantic stays at the schema boundary or gets refactored out is a **resume decision** — see "ADR candidate: pydantic-boundary" in `RESUME.md`.

---

*Freeze date: 2026-07-03. Verified by commands cited in evidence columns.*
