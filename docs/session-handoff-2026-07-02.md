# Session Handoff — 2026-07-02

**Purpose.** Give a fresh LLM session the shortest complete context to continue
the ADR-010 / ADR-011 / ADR-012 workstreams without re-deriving decisions.
Paste this file into the new session's opening turn.

---

## TL;DR — where we are

Four related renames/restructures are in flight. Three are done, three are
pending. Between them, the repo has been reshaped from
`kitchen-cad / kitchen-app / kitchen-plugin` into
`kitchen-cam / kitchen-erp / home-builder-adapter` (rename ADRs 009–011),
with `kuchnie_core` growing into the domain hub.

**Landed this session (5 commits, newest first):**

| Commit | What |
|---|---|
| `70ae04f` | ADR-011 Commit **B.ii**: unify `kitchen_app/` + `kitchen_erp/` → `kitchen_erp/{ui,core}/` |
| `13757ef` | Package re-export: `kuchnie_core.export_edging_csv` at package root |
| `1cf04d0` | ADR-011 Commit **A**: `git mv kitchen-app/ kitchen-erp/` (43 files) |
| `c4873aa` | ADR-010 additive: add `kuchnie_core.export.edging_csv` + write ADR-012 |
| `71948db` | (prior) phase C/D leftovers cleanup |

**Test baseline (must be preserved):**

- `kuchnie_core`: **533 pass** (`pytest tests/ -q`)
- `kitchen-erp`: **38 pass / 3 fail / 12 errors / 1 collect error** — all pre-existing, unrelated to the renames. Same 15 test names in the failing set as before commit `71948db`.
- `kitchen-cam`: 292 pass / 35 xfail / 13 xpass — unaffected since commit `c4873aa` (docstring-only edits there).

**Pending workstreams (any subset, any order except where noted):**

1. **ADR-011 Commit C** — delete old BOM path (surgical, ~1 session).
2. **ADR-012 execution** — extend `kuchnie_core.model` (multi-commit, ~2–3 sessions). **Blocks** the ADR-010 deletion queue.
3. **ADR-010 completion** — delete `kitchen_cam.models/panel_calculator/csv_generator`, rewrite `kitchen_cam.machining` against `kuchnie_core.model`. Depends on ADR-012.
4. **Fix pre-existing kitchen-erp test failures** — HARDWARE_RULES + SQLAlchemy fixtures + oven backward-compat. Orthogonal cleanup.
5. **Regenerate `all-signatures.md`** — housekeeping, part of any commit.

---

## Universal reading order (read for every workstream, in this order)

1. **`AGENTS.md`** (repo root) — operational rules. Especially: model fields English / YAML keys Polish; don't edit old ADRs; docstring + test = documentation; ADR routing table.
2. **`CHANGELOG.md` § `[Unreleased]`** — the exact edits done today and the deferrals.
3. **`docs/adr/010-kitchen-cad-becomes-kitchen-cam.md`** — migration mapping + deletion queue (blocked).
4. **`docs/adr/011-kitchen-app-becomes-kitchen-erp.md`** — rename ADR (A done, B.ii done, C pending).
5. **`docs/adr/012-kuchnie-core-model-extensions.md`** — enumerates the 6 concrete extensions needed to unblock ADR-010.
6. **`all-signatures.md`** (repo root, untracked, regenerate with `py-diagram` skill) — structural snapshot of every Python file. Use it as ground truth when planning any wide change.

**Do NOT read** — noise for the current work:

- Anything in `docs/archive/`
- `kitchen-erp/docs/archived/`
- `features/archive/`
- ADRs 001–009 (foundational, already applied; only skim if a specific formula is in question).

---

## Workstream 1 — ADR-011 Commit C: delete old BOM path

**Scope.** Resolve the "two live BOM systems" state called out in ADR-011.

**Reading list:**

1. `docs/adr/011-*.md` §"Deprecate old BOM path"
2. `all-signatures.md` sections for:
   - `kitchen-erp/kitchen_erp/core/models.py` (has `Cabinet.calculate_cost`)
   - `kitchen-erp/kitchen_erp/ui/state.py` (has `set_use_new_bom`, `_new`-suffix methods)
   - `kitchen-erp/kitchen_erp/kitchen_erp.py` (Reflex entry — has the toggle UI)
3. The five test files that reference `calculate_cost`:
   - `kitchen-erp/tests/test_calculations.py`
   - `kitchen-erp/tests/test_database_integration.py`
   - `kitchen-erp/tests/test_end_to_end_workflow.py::test_backward_compatibility_verification`
   - `kitchen-erp/tests/test_integration_bom.py::test_backward_compatibility_old_vs_new`
   - `kitchen-erp/tests/test_integration_bom.py::test_new_bom_has_more_detail_than_old`

**Files that will change (touch list):**

- `kitchen-erp/kitchen_erp/core/models.py` — delete `Cabinet.calculate_cost` method (~50 LOC).
- `kitchen-erp/kitchen_erp/ui/state.py` — delete `set_use_new_bom`, `open_selected_cabinet_cost_trace` (old variant), `open_project_cost_trace` (old variant). Drop `_new` suffix from the surviving variants. Remove `use_new_bom` field.
- `kitchen-erp/kitchen_erp/kitchen_erp.py` — remove the toggle switch (`rx.Switch(checked=…, on_change=…)` at lines ~43-44 of pre-B.ii; verify new line numbers after B.ii).
- Test file changes: delete backward-compat tests entirely; rewrite `test_calculations.py` and `test_database_integration.py` to use `BOMGenerator` instead of `calculate_cost`.
- `CHANGELOG.md` — add "Deleted" section under `[Unreleased]`.

**Success criteria:**

- `Cabinet.calculate_cost` no longer exists in `all-signatures.md`.
- `use_new_bom` / `set_use_new_bom` no longer in `all-signatures.md`.
- Test posture: fewer or equal errors than the 15-test baseline. Some pre-existing errors may become "clean pass" or disappear (e.g. `test_backward_compatibility_old_vs_new` gets deleted).
- `kuchnie_core` tests unaffected (533 pass).

**Gotchas:**

- Some pre-existing failures may go away when the tests they were failing in get deleted. Don't count that as a fix; count deletions honestly.
- Reflex `.web/` directory is auto-generated — safe to `rm -rf` if the UI reload gets weird.

---

## Workstream 2 — ADR-012 execution: extend `kuchnie_core.model`

**Scope.** Add the 6 extensions ADR-012 enumerates so ADR-010 can be finished.
Each extension is a separate commit ideally.

**Reading list:**

1. `docs/adr/012-*.md` (full — this is the plan)
2. `docs/adr/001-panel-is-atomic-unit.md`, `docs/adr/005-machining-op-model.md` (foundational)
3. `all-signatures.md` sections for:
   - `src/kuchnie_core/model.py` (current shape)
   - `kitchen-cam/src/kitchen_cam/models.py` (target shape — Pydantic reference)
   - `src/kuchnie_core/blum_hinges.py` (for the HingeGeometry extension)
   - `src/kuchnie_core/catalog.py` (uses the model — needs updating when `role` field lands)
4. `AGENTS.md` §"Conventions" — units, field naming (`_mm` suffix), English enum values.

**Files that will change (extension by extension):**

| Extension | Files touched | New tests |
|---|---|---|
| 1. `PanelRole` enum + `Panel.role` | `src/kuchnie_core/model.py`, all of `src/kuchnie_core/catalog.py`, `src/kuchnie_core/legrabox.py` (populate `role` in every decomposition function) | `tests/test_panel_role.py` |
| 2. `MachiningOp.face` + `.drill_type` | `src/kuchnie_core/model.py`, existing tests referencing `MachiningOp` (verify defaults don't break them) | grow `tests/test_construction.py` |
| 3. `HingeGeometry` on `BlumHinge` | `src/kuchnie_core/blum_hinges.py` | grow `tests/test_blum_hinges.py` |
| 4. `HandleSpec` on `CabinetInstance` | `src/kuchnie_core/model.py`, `src/kuchnie_core/loader.py` | grow `tests/test_cabinet_instance.py` |
| 5. `ShelfPinSpec` on `CabinetInstance` | `src/kuchnie_core/model.py`, `src/kuchnie_core/loader.py` | grow `tests/test_cabinet_instance.py` |
| 6. `CabinetInstance.config` union | `src/kuchnie_core/model.py` (7 new dataclasses), `src/kuchnie_core/loader.py` (synthesise from legacy fields), fixtures may need `config:` blocks | new `tests/test_cabinet_config.py` |

**Success criteria per extension:**

- New extension covered by tests.
- All 533 pre-existing `kuchnie_core` tests still pass.
- `catalog.py` decomposition functions updated (where relevant) so real fixtures still decompose to the same panel dimensions.

**Order.** Land them in the order ADR-012 lists (1 → 6). Each builds on the previous. Do NOT try to land all six in one commit — each is 1–2 hours of focused work.

**Gotchas:**

- `kuchnie_core.model` currently uses **plain dataclasses**. Do not introduce Pydantic (see ADR-012 alternative 12a for why).
- Existing tests assume dataclass semantics (default values via `field(default_factory=...)`). New fields must have safe defaults or existing constructors break.
- YAML loader (`loader.py`) is the adapter Polish↔English. All new fields need loader translation.

---

## Workstream 3 — ADR-010 completion (blocked on Workstream 2)

**Scope.** Once all 6 extensions from Workstream 2 land, rewrite
`kitchen-cam.machining` against `kuchnie_core.model` and delete the
duplicated modules.

**Reading list (in this order, only when Workstream 2 is done):**

1. `docs/adr/010-*.md` §"What is DELETED" and §"What stays (renamed and rehomed)"
2. Deprecation banners in:
   - `kitchen-cam/src/kitchen_cam/models.py`
   - `kitchen-cam/src/kitchen_cam/panel_calculator.py`
   - `kitchen-cam/src/kitchen_cam/csv_generator.py`
   - `kitchen-cam/src/kitchen_cam/machining.py`
3. `all-signatures.md` section for `kitchen-cam/`.

**Files that will change:**

- Rewrite `kitchen-cam/src/kitchen_cam/machining.py` (~250 LOC) — imports change from `kitchen_cam.models` to `kuchnie_core.model`, role-matching becomes `panel.role == PanelRole.LEFT_SIDE`, hinge geometry pulled from `BlumHinge.geometry`, shelf-pin geometry from `CabinetInstance.shelf_pins`.
- Delete `kitchen_cam/models.py`, `panel_calculator.py`, `csv_generator.py`.
- Rewrite `kitchen-cam/tests/conftest.py` and `test_compare.py` fixtures to build `kuchnie_core.CabinetInstance` / `Kitchen` directly (per original ADR-010 step 5).
- Mass-`xfail` or rewrite the ~14 kitchen-cam test files that import from the deleted modules.

**Success criteria:**

- `grep -r "kitchen_cam.models\|kitchen_cam.panel_calculator\|kitchen_cam.csv_generator" kitchen-cam/` returns 0.
- All `kitchen-cam/tests/` either pass or are explicitly xfailed with a reason string referencing ADR-010.

---

## Workstream 4 — pre-existing kitchen-erp failures (orthogonal cleanup)

**Scope.** The 15 tests that were broken **before** this session's work.
Not blocking any ADR; fair game to fix opportunistically.

**Diagnostic starting points:**

1. `HARDWARE_RULES` collect error → `kitchen-erp/tests/test_rules_engine.py:3` imports `HARDWARE_RULES` from `kitchen_erp.core.rules_engine`, but that symbol doesn't exist in the module. Either the test is stale (delete/rewrite) or the module lost the export (restore).
2. SQLAlchemy 12 errors in `test_bom_generator.py` and `test_integration_bom.py` → typically fixture setup issues (probably a missing `Session` teardown or a `create_all` call). Read `tests/conftest.py` first.
3. `test_no_back_panel_for_oven_cabinet` and `test_tag_based_hardware_addition` failures → likely semantic drift; run the test in isolation with `-v -s` and read the assertion.

**Success criteria:** each fix documented in `CHANGELOG.md § Fixed`. No new failures introduced.

---

## Workstream 5 — regenerate `all-signatures.md` (do this last, or per-commit)

**Scope.** After any restructure, regenerate the signatures snapshot so the
next session has ground truth.

**How.** Use the `py-diagram` skill:
`/Users/michal/.pi/agent/skills/py-diagram/SKILL.md`

**Output.** Overwrite `all-signatures.md` at the repo root. It's untracked
(`.gitignore` policy discussion pending — for now, don't commit it; regenerate
on demand).

---

## Non-obvious rules learned this session

1. **The kuchnie_core Panel model has no `role` field.** Anyone writing CAM-adjacent code will assume it does (because `kitchen_cam.models.PanelRole` exists). This is the single biggest reason ADR-010 got stuck. ADR-012 fixes it.
2. **`kuchnie_core.MachiningOp` has no `face` / `drill_type` discriminator.** Rich drilling metadata from `kitchen_cam.DrillPoint` doesn't have a home yet. Same fix.
3. **`kuchnie_core.CabinetInstance.handles: dict` is untyped.** Any code that wants hinge geometry (`first_position`, `screw_spacing`, `edge_to_cup_centre`) currently can't get it from `kuchnie_core`. ADR-012 adds `HingeGeometry`.
4. **`rxconfig.py`'s `app_name` matches a Python module name, not the directory name.** After ADR-011 B.ii, `app_name = "kitchen_erp"` maps to `kitchen_erp/kitchen_erp.py`. Do not confuse "app name" with "component name".
5. **`kuchnie_core` uses plain dataclasses, not Pydantic.** Deliberately. ADR-012 alternative 12a explains why. Do not introduce Pydantic into `kuchnie_core`.
6. **Model fields English, YAML keys Polish.** Loader is the adapter. Enforced by every existing ADR.
7. **git rename detection is a heuristic display.** After large moves it may show "cross-wired" renames (e.g. `A/__init__.py → B/__init__.py` when both were empty). Verify with `ls` and `git show HEAD --stat`, then trust the working tree.

---

## What NOT to do

- **Do not edit old ADRs.** Supersede with a new ADR. ADRs 003 and 009 still mention `kitchen-app` — that's fine; ADR-011 supersedes.
- **Do not add features to the deprecated `kitchen-cam` modules** (`models.py`, `panel_calculator.py`, `csv_generator.py`, `machining.py`). They have deprecation banners referencing ADR-012.
- **Do not delete `Cabinet.calculate_cost` casually** — it's a real code path with real callers (see Workstream 1 for the surgical plan).
- **Do not touch `home_builder_5/`** — external licensed Blender addon, per F007 Rule 4.
- **Do not commit `all-signatures.md`** — it's a generated artefact.
- **Do not fold multiple workstreams into one commit.** Each ADR sub-step is a separate commit for readable history.
- **Do not run `reflex run` and trust the result** without also running `pytest kitchen-erp/tests/` — Reflex has its own state that can hide import errors.

---

## Fast-start template for a new session

```
Read in this order:
  1. AGENTS.md
  2. docs/session-handoff-2026-07-02.md   (this file)
  3. CHANGELOG.md § [Unreleased]
  4. docs/adr/012-kuchnie-core-model-extensions.md
  5. all-signatures.md   (regenerate first if stale)

Task: <pick a workstream from the handoff>

Constraints:
  - Preserve test baseline: kuchnie_core 533 pass; kitchen-erp 38/3/12/1;
    kitchen-cam 292/35/13.
  - Do not touch unrelated staged/unstaged files
    (home-builder-adapter delete, catalog/ untracked, kitchen-plugin/).
  - Follow workflow-commit: only stage what you edited.
```

---

## Repo state at handoff

```
HEAD:      70ae04f  refactor(kitchen-erp): unify internal packages under kitchen_erp/ (ADR-011 Commit B.ii)
branch:    main (23 commits ahead of origin — not yet pushed)
untracked (leave alone):
  - home-builder-adapter/docs/archive/wall-centric-model.md   (pre-existing deletion, unrelated)
  - catalog/docs/adr/003-worktop-filtering-hierarchy.md       (other work)
  - catalog/docs/specs/worktop-uu-seeding.md                  (other work)
  - kitchen-plugin/                                           (other work, unrelated to ADR-009)
  - all-signatures.md                                          (generated)
```
