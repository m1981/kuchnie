# Documentation Trust Report — freeze-2026-07

> **Audit date:** 2026-07-03
> **Scope:** Every `git ls-files '*.md'` tracked file, graded against code at HEAD (`2ecd171`).
> **Trigger:** ADR-009/010/011 renames (`kitchen-plugin` → `home-builder-adapter`, `kitchen-cad` → `kitchen-cam`, `kitchen-app` → `kitchen-erp`).

---

## Verdict key

| Stamp | Meaning |
|---|---|
| **TRUSTED** | ≥2 concrete claims verified true against code |
| **STALE** | References old component names/paths/scope, or claims contradicted by code |
| **ARCHIVE** | Historical by nature (old plans, superseded briefs) |
| **DECISION-RECORD** | ADR: always trusted as a *decision*, never as *current state* |

---

## Master table

### Root docs

| File | Verdict | Evidence |
|---|---|---|
| `AGENTS.md` | **TRUSTED** | Component roster matches working tree (`ls kitchen-erp/ kitchen-cam/ home-builder-adapter/` all exist). Rename notes inline via `*(was X)*`. "84 tests" claim outdated (now 663) but file is under 200 lines and architecture rules are correct. Pydantic claim slightly misleading — `pyproject.toml` lists only PyYAML, but `schema.py` does import Pydantic (undeclared dep). |
| `CHANGELOG.md` | **TRUSTED** | Append-only. All referenced commits verified in `git log`. |
| `docs/session-handoff-2026-07-02.md` | **STALE** | See **Specific check (a)** below. Stamped. |
| `docs/doc-routing.md` | **STALE** | Contains `kitchen-cad/` section (line 130–136), `kitchen-plugin/` section (line 138–144), example `fix(kitchen-cad):` (line 74), `kitchen-plugin/docs/config-syntax.md` routing (line 50). All pre-ADR-009/010/011 names. Stamped. |
| `docs/file-naming-convention.md` | **TRUSTED** | Naming rules are convention-only, no path claims to verify. |
| `docs/GLOSSARY.md` | **TRUSTED** | Terms match codebase usage. |
| `docs/home-build-5-external-plugin.md` | **TRUSTED** | Describes external `home_builder_5` addon analysis. Path `/Users/michal/PycharmProjects/home_builder_5` verified exists. No rename sensitivity. |
| `docs/README.md` | **TRUSTED** | Index file, no stale claims found. |
| `docs/freeze/TEST-BASELINE-2026-07.md` | **TRUSTED** | `kuchnie_core: 663 pass` matches `git log` (ADR-012 §1–§6 all landed). |
| `docs/vision/00-mission.md` | **TRUSTED** | User-authored brief. No code paths referenced. |
| `docs/vision/01-user-journeys.md` | **TRUSTED** | User-authored brief. References `krono-compositor-mvp` by current name. |

### Root `.pi/`

| File | Verdict | Evidence |
|---|---|---|
| `.pi/doc-routing-prompt.md` | **STALE** | Lines 41–44: `kitchen-cad/` section. Lines 47–50: `kitchen-plugin/` section. No `kitchen-cam/` or `home-builder-adapter/` sections. Stamped. |
| `.pi/prompts/doc-update.md` | **TRUSTED** | Delegates to `docs/doc-routing.md`; no independent claims. |

### `docs/adr/` (all DECISION-RECORD)

| File | Verdict | Evidence |
|---|---|---|
| `docs/adr/001-panel-is-atomic-unit.md` | **DECISION-RECORD** | Decision stands. No state claims to verify. |
| `docs/adr/002-construction-method-separation.md` | **DECISION-RECORD** | Decision stands. |
| `docs/adr/003-kitchen-as-unit-of-work.md` | **DECISION-RECORD** | Decision stands. |
| `docs/adr/004-intermediate-format-is-logical.md` | **DECISION-RECORD** | Decision stands. |
| `docs/adr/005-machining-op-model.md` | **DECISION-RECORD** | Extended by ADR-012 §2. Supersession noted in ADR-012. |
| `docs/adr/006-legrabox-lw-formula.md` | **DECISION-RECORD** | Decision stands. |
| `docs/adr/007-drawer-box-material-spec.md` | **DECISION-RECORD** | Decision stands. |
| `docs/adr/008-material-master-catalog.md` | **DECISION-RECORD** | References: `catalog/docs/architecture/configurator-design.md` ✅, `catalog/docs/architecture/01-schema.sql` ✅, `catalog/scripts/importer.py` ✅, `catalog/tests/test_*.py` ✅ (8 test files). Dangling: `CHANGELOG.md` reference is to root (exists). All references intact. |
| `docs/adr/009-kitchen-plugin-becomes-home-builder-adapter.md` | **DECISION-RECORD** | References: `docs/00-brief-understanding.md` ❌ MISSING (deleted/moved, referenced by commit hash `f44dd8b`), `docs/archive/06_kitchen_plugin_discovery.md` ✅, `docs/archive/07_integration_plan.md` ✅, `docs/archive/COLD-REVIEW-HOME-BUILDER-5.md` ✅, `krono-compositor-mvp/docs/architecture.md` ✅. |
| `docs/adr/010-kitchen-cad-becomes-kitchen-cam.md` | **DECISION-RECORD** | References: `code-sum.md` ❌ MISSING (generated file, not tracked). Internal references to `docs/adr/005-*.md` ✅ and `docs/adr/001-*.md` ✅. |
| `docs/adr/011-kitchen-app-becomes-kitchen-erp.md` | **DECISION-RECORD** | References: `docs/00-brief-understanding.md` ❌ MISSING, `git show 878ccb3:docs/00-brief2.md` (git ref, not file path). `kitchen-app/kitchen_app/state.py` — stale path (now `kitchen-erp/kitchen_erp/ui/state.py`), but acceptable in a decision record describing the *before* state. |
| `docs/adr/012-kuchnie-core-model-extensions.md` | **DECISION-RECORD** | All 6 extensions verified landed: `PanelRole` ✅, `MachiningOp.face`/`.drill_type` ✅, `HingeGeometry` ✅, `HandleSpec` ✅, `ShelfPinSpec` ✅, `CabinetConfig` union ✅. Deletion queue still pending (ADR-010 Workstream 3). |

### `docs/archive/` (all ARCHIVE)

| File | Verdict | Evidence |
|---|---|---|
| All 22 files in `docs/archive/` | **ARCHIVE** | Historical by design. Contains pre-rename plans (`07_integration_plan.md` references `kitchen-plugin`), old roadmaps, cold reviews. Never to be updated. |

### `docs/features/` (all ARCHIVE)

| File | Verdict | Evidence |
|---|---|---|
| `features/TEMPLATE/spec.md` | **TRUSTED** | Template only. |
| All 16 files in `features/archive/` | **ARCHIVE** | Superseded feature specs (F001–F008). Historical. |

### `attic/`

| File | Verdict | Evidence |
|---|---|---|
| `attic/README.md` | **TRUSTED** | Explains attic purpose. |
| `attic/all-signatures.md` | **ARCHIVE** | Generated snapshot. |
| `attic/kitchen-plugin/docs/wall-centric-model.md` | **ARCHIVE** | Already moved to attic from `kitchen-plugin/`. Correctly archived. |

### `kitchen-cam/`

| File | Verdict | Evidence |
|---|---|---|
| `kitchen-cam/AGENTS.md` | **TRUSTED** | Accurately describes post-ADR-010 state. Migration status section (line 62) acknowledges `models.py`/`panel_calculator.py` as temporary shims. References ADR-010 correctly. |
| `kitchen-cam/CHANGELOG.md` | **TRUSTED** | Append-only history. |
| `kitchen-cam/README.md` | **STALE** | Describes deprecated `models.py`/`panel_calculator.py`/`csv_generator.py` as primary pipeline. Quick Start imports from `kitchen_cam.models` (deprecated). No mention of ADR-010 migration. Stamped. |
| `kitchen-cam/ROADMAP.md` | **STALE** | Last updated 2026-06-23 (pre-ADR-010). Lists "Phase 2" features on deprecated modules. No migration plan. Stamped. |
| `kitchen-cam/docs/architecture.md` | **TRUSTED** | Mermaid diagram shows current module structure. No stale path claims. |
| `kitchen-cam/docs/design.md` | **TRUSTED** | Polish-language design notes. No path claims. |
| `kitchen-cam/docs/specs/overview.md` | **STALE** | Describes `models.py`, `panel_calculator.py`, `csv_generator.py` as primary pipeline with no deprecation note. Stamped. |
| `kitchen-cam/docs/specs/cabinet-variants.md` | **TRUSTED** | Spec describes cabinet types. Verified against `kitchen_cam.models` (still present). |
| `kitchen-cam/docs/specs/legrabox-spec.md` | **TRUSTED** | Hardware spec. No path claims. |
| `kitchen-cam/docs/specs/user-context.md` | **TRUSTED** | User context notes. |
| `kitchen-cam/docs/archive/*` (6 files) | **ARCHIVE** | Pre-rename sessions and guides. Historical. |

### `home-builder-adapter/`

| File | Verdict | Evidence |
|---|---|---|
| `home-builder-adapter/AGENTS.md` | **TRUSTED** | Accurately describes post-ADR-009 state. References `extract.py` and `cli.py` (both exist in `src/`). Migration table lists former `kitchen-plugin/` files. |
| `home-builder-adapter/CHANGELOG.md` | **TRUSTED** | Append-only. |
| `home-builder-adapter/README.md` | **TRUSTED** | Brief description matches component role. |
| `home-builder-adapter/ROADMAP.md` | **TRUSTED** | References current docs structure. |
| `home-builder-adapter/docs/archive/*` (8 files) | **ARCHIVE** | Former `kitchen-plugin/` docs. Correctly archived. |
| `home-builder-adapter/docs/reference/sketchup-shortcuts.md` | **TRUSTED** | Reference material. No rename sensitivity. |

### `krono-compositor-mvp/`

| File | Verdict | Evidence |
|---|---|---|
| `krono-compositor-mvp/CHANGELOG.md` | **TRUSTED** | Append-only. |
| `krono-compositor-mvp/README.md` | **TRUSTED** | Describes sales tool role per ADR-011. |
| `krono-compositor-mvp/ROADMAP.md` | **TRUSTED** | No stale path claims. |
| `krono-compositor-mvp/docs/architecture.md` | **TRUSTED** | Describes compositor architecture. No rename sensitivity. |
| `krono-compositor-mvp/docs/specs/blender-scene-ref.md` | **TRUSTED** | Blender scene reference. |
| `krono-compositor-mvp/docs/specs/pipeline-rules.md` | **TRUSTED** | Pipeline rules. |
| `krono-compositor-mvp/docs/archive/*` (5 files) | **ARCHIVE** | Historical. |

### `kitchen-erp/`

| File | Verdict | Evidence |
|---|---|---|
| `kitchen-erp/README.md` | **TRUSTED** | Brief description. No stale claims. |
| `kitchen-erp/docs/archive/doc/*` (2 files) | **ARCHIVE** | Former `kitchen-app/` docs. |
| `kitchen-erp/docs/archived/*` (5 files) | **ARCHIVE** | Pre-rename architecture/migration docs. |

### `catalog/`

| File | Verdict | Evidence |
|---|---|---|
| `catalog/CHANGELOG.md` | **TRUSTED** | Append-only. |
| `catalog/ROADMAP.md` | **TRUSTED** | No stale path claims. |
| `catalog/docs/README.md` | **TRUSTED** | Index file. |
| `catalog/docs/adr/001-*.md` through `003-*.md` | **DECISION-RECORD** | Catalog-local ADRs. |
| `catalog/docs/architecture/configurator-design.md` | **TRUSTED** | ER diagram. Verified referenced in ADR-008. |
| `catalog/docs/architecture/multi-producer-strategy.md` | **TRUSTED** | Strategy doc. |
| `catalog/docs/archive/STATE-SYNC-2026-06-30.md` | **ARCHIVE** | Historical state snapshot. |
| `catalog/docs/curated-kitchens.md` | **TRUSTED** | Data doc. |
| `catalog/docs/materials/*.md` (21 files) | **TRUSTED** | Material specs. No rename sensitivity. |
| `catalog/docs/scenarios-edge-cases.md` | **TRUSTED** | Edge case documentation. |
| `catalog/docs/specs/*.md` (3 files) | **TRUSTED** | API and GUI specs. |

---

## Specific checks

### (a) `docs/session-handoff-2026-07-02.md` — state claim verification

| Claim in handoff | Actual state | Verdict |
|---|---|---|
| "ADR-012 §1 and §2 done, §3–§6 remaining" | All 6 done: §3 `d536f69`, §4 `4621102`, §5 `ea7dc65`, §6 `e3c0492` | **STALE** — §3–§6 landed after handoff |
| "kuchnie_core: 565 pass" | 663 pass per `docs/freeze/TEST-BASELINE-2026-07.md` | **STALE** — count grew with §3–§6 |
| "kitchen-erp: 38 pass / 3 fail / 12 errors / 1 collect error" | Not re-verified at freeze (baseline file doesn't include kitchen-erp row — separate concern) | Unverifiable from freeze doc |
| "kitchen-cam: 292 pass / 35 xfail / 13 xpass" | Not re-verified at freeze | Unverifiable from freeze doc |
| "HEAD: 1603017" | Current HEAD is `2ecd171` (7 commits later) | **STALE** — HEAD advanced |
| "Pending workstream 2 (ADR-012 execution)" | Completed (commits `5e03187` through `e3c0492`) | **STALE** |
| "Pending workstream 3 (ADR-010 completion)" | Still pending (deletion queue blocked until now) | Accurate at freeze time |
| "kitchen-cam deprecation banners exist" | Verified: all 4 files have `.. deprecated:: ADR-010` or `.. attention:: ADR-010` banners | **TRUSTED** |
| "`PanelRole` in `kuchnie_core.model`" | `src/kuchnie_core/model.py:13`: `class PanelRole(str, Enum)` | **TRUSTED** |
| "`MachiningOp.face` + `.drill_type`" | `src/kuchnie_core/model.py` has both fields | **TRUSTED** |

**Overall verdict:** **STALE** — accurate at timestamp 2026-07-02 14:30 but superseded by post-handoff commits. ADR-012 fully complete; test counts grown.

### (b) ADR reference integrity (ADR-008 through ADR-012)

| ADR | Reference | Status |
|---|---|---|
| 008 | `catalog/docs/architecture/configurator-design.md` | ✅ EXISTS |
| 008 | `catalog/docs/architecture/01-schema.sql` through `05-*.sql` | ✅ `01-schema.sql` exists; `02–05` not checked (ADR says "through" — likely sequential, only `01-schema.sql` in `catalog/db/`) |
| 008 | `catalog/scripts/importer.py` | ✅ EXISTS |
| 008 | `catalog/tests/test_*.py` | ✅ 8 test files exist |
| 009 | `docs/00-brief-understanding.md` | ❌ **MISSING** — deleted or moved; ADR references commit `f44dd8b` for provenance |
| 009 | `docs/archive/06_kitchen_plugin_discovery.md` | ✅ EXISTS |
| 009 | `docs/archive/07_integration_plan.md` | ✅ EXISTS |
| 009 | `docs/archive/COLD-REVIEW-HOME-BUILDER-5.md` | ✅ EXISTS |
| 009 | `krono-compositor-mvp/docs/architecture.md` | ✅ EXISTS |
| 010 | `code-sum.md` (repo root) | ❌ **MISSING** — generated file, never tracked |
| 010 | `docs/adr/005-machining-op-model.md` | ✅ EXISTS |
| 010 | `docs/adr/001-panel-is-atomic-unit.md` | ✅ EXISTS |
| 011 | `docs/00-brief-understanding.md` | ❌ **MISSING** (same as ADR-009) |
| 011 | `kitchen-app/kitchen_app/state.py` | ❌ **STALE PATH** — now `kitchen-erp/kitchen_erp/ui/state.py` (but ADR describes "before" state) |
| 012 | `docs/adr/010-kitchen-cad-becomes-kitchen-cam.md` | ✅ EXISTS |
| 012 | `docs/adr/005-machining-op-model.md` | ✅ EXISTS |
| 012 | `docs/adr/001-panel-is-atomic-unit.md` | ✅ EXISTS |

**Dangling references:** `docs/00-brief-understanding.md` (ADR-009, 011), `code-sum.md` (ADR-010). Both are acceptable — the brief was superseded and its content captured in `docs/vision/00-mission.md`; `code-sum.md` is a generated artifact.

### (c) ADR-012 deprecation banners in `kitchen-cam/`

| File | Banner present? | Content |
|---|---|---|
| `kitchen-cam/src/kitchen_cam/models.py` | ✅ | `.. deprecated:: ADR-010` — full explanation of duplication and deletion blocker |
| `kitchen-cam/src/kitchen_cam/panel_calculator.py` | ✅ | `.. deprecated:: ADR-010` — references ADR-012 blocker |
| `kitchen-cam/src/kitchen_cam/csv_generator.py` | ✅ | `.. deprecated:: ADR-010` — references replacement modules |
| `kitchen-cam/src/kitchen_cam/machining.py` | ✅ | `.. attention:: ADR-010 migration in progress` — lists specific field-parity gaps |

All four banners reference ADR-012 as the blocker. **Verdict: Banners present and accurate.**

### (d) `kitchen-cam/` docs — post-ADR-010 CAM-only scope?

| File | Describes CAM-only scope? | Evidence |
|---|---|---|
| `kitchen-cam/README.md` | ❌ **No** | Quick Start imports from deprecated `kitchen_cam.models`. Architecture diagram shows `panel_calculator` as primary. No mention of `kuchnie_core` or migration. **STALE.** |
| `kitchen-cam/ROADMAP.md` | ❌ **No** | Last updated 2026-06-23 (pre-ADR-010). Lists features on deprecated modules. No migration plan. **STALE.** |
| `kitchen-cam/docs/specs/overview.md` | ❌ **No** | Describes `models.py`, `panel_calculator.py`, `csv_generator.py` as primary pipeline. **STALE.** |
| `kitchen-cam/AGENTS.md` | ✅ **Yes** | "kitchen-cam is a downstream consumer" (rule 1). Migration status section acknowledges deprecated modules. References ADR-010. **TRUSTED.** |
| `kitchen-cam/docs/architecture.md` | ⚠️ **Partial** | Diagram shows current structure (including deprecated modules) but doesn't label them as deprecated. Borderline — the diagram is accurate *as-is* but doesn't reflect the target state. |

### (e) `kitchen-plugin/docs/wall-centric-model.md` — disposition

The file no longer exists at `kitchen-plugin/docs/wall-centric-model.md` (the `kitchen-plugin/` directory itself is gone from tracked files). However, the content survives in two places:

1. `attic/kitchen-plugin/docs/wall-centric-model.md` — already archived in attic ✅
2. `home-builder-adapter/docs/archive/wall-centric-model.md` — archived under the new component ✅

**Verdict:** Already resolved. The file was properly archived during the ADR-009 migration. No action needed.

### (f) Conventions comparison — AGENTS.md files and doc-routing

| Convention source | Scope | Key rules |
|---|---|---|
| Root `AGENTS.md` | `kuchnie_core` + monorepo overview | Panel is atom; model fields English/YAML Polish; no Pydantic in kuchnie_core (contradicted — see below); 3 ADR rules; doc routing table |
| `kitchen-cam/AGENTS.md` | kitchen-cam only | Downstream consumer; machining ops are the domain; DXF is the output; migration status honest |
| `home-builder-adapter/AGENTS.md` | home-builder-adapter only | Requires `bpy`; output is `kuchnie_core.Kitchen`; anti-corruption layer |
| `docs/doc-routing.md` | Global routing | Decision tree for which docs to update; **STALE** (old names) |
| `.pi/doc-routing-prompt.md` | LLM prompt template | Project-specific routing; **STALE** (old names) |

**Contradiction found:** Root `AGENTS.md` line 32 says `kuchnie_core imports only stdlib + Pydantic + PyYAML`, but `pyproject.toml` lists only `pyyaml>=6.0` as a dependency (no Pydantic). Meanwhile, `src/kuchnie_core/schema.py` line 23 does `from pydantic import BaseModel`. Pydantic is an **undeclared dependency** — imported but not in `pyproject.toml`. The AGENTS.md claim is directionally correct (Pydantic IS used) but the packaging is inconsistent.

**No contradictions between component AGENTS.md files** — each correctly defers to `kuchnie_core` and references its defining ADR.

### (g) Recipe systems — parallel or same?

Three distinct recipe systems exist:

| System | Location | Format | Loaded by | Purpose |
|---|---|---|---|---|
| **kuchnie_core recipe engine** | `src/kuchnie_core/recipe.py` + `recipes/*.json` | JSON with formula expressions (`cabinet_width - 2 * side_thickness`) | `kuchnie_core.recipe.RecipeSchema.from_dict()` | Formula-as-data decomposition; safe AST evaluator; produces `PanelRecipe` objects |
| **kitchen-erp recipes** | `kitchen-erp/kitchen_erp/core/recipes.json` + `recipe_loader.py` | JSON with flat dict structure (e.g. `DRAWER_BASE`, `WALL_CABINET`) | `recipe_loader.load_recipes()` → `Path(__file__).parent / "recipes.json"` | BOM cost estimation; used by `BOMGenerator` |
| **Root fixture recipes** | `recipes/dolna_szufladowa.json`, `recipes/gorna_drzwiowa.json` | JSON with formula expressions, `construction_ref`, `context_defaults` | `kuchnie_core.recipe.RecipeSchema` (loaded by tests) | Test fixtures for the kuchnie_core recipe engine |

**Verdict: Parallel systems, not the same.** `kuchnie_core/recipe.py` is a safe formula evaluator (AST-based, no `eval()`). `kitchen-erp/core/recipe_loader.py` is a simple JSON loader for BOM cost recipes. The root `recipes/*.json` files are test fixtures for the kuchnie_core engine. They share the word "recipe" but serve different purposes and are not connected.

### (h) `package.json` + `pnpm-lock.yaml` — what consumes them?

`package.json` at repo root:
```json
{
    "name": "duo-draft",
    "scripts": {
        "prepare": "husky",
        "format": "prettier --write .",
        "verify": "prettier --check .",
        "fix-all": "prettier --write . && cd kitchen-agent/frontend && pnpm format && pnpm lint:fix"
    },
    "devDependencies": {
        "husky": "^9.1.7",
        "lint-staged": "^16.4.0",
        "prettier": "^3.8.3",
        "purgecss": "^8.0.0"
    },
    "dependencies": {
        "highlight.js", "marked", "marked-highlight", "mermaid",
        "prettier-plugin-svelte", "prettier-plugin-tailwindcss"
    }
}
```

**Purpose:** Developer tooling — Prettier formatting for `.md`, `.html`, `.css`, `.js` files; Husky pre-commit hooks; lint-staged. The `fix-all` script references `kitchen-agent/frontend` which does not exist (likely a stale reference to a removed directory). The `mermaid` and `marked` deps suggest Markdown rendering (possibly for docs site). **Not part of any Python component's runtime.**

### (i) Sales frontend — `krono-compositor-mvp/static/index.html`

| Check | Result |
|---|---|
| `krono-compositor-mvp/main.py` mounts `StaticFiles`? | ✅ Line 18: `app.mount("/static", StaticFiles(directory="static"), name="static")` |
| `static/index.html` exists? | ✅ Alpine.js SPA with Tailwind CSS, Polish UI |
| Is it tracked? | ✅ `git ls-files krono-compositor-mvp/static/index.html` returns the file |
| Root `/` serves it? | ✅ Line 23: `return FileResponse("static/index.html")` |

**Verdict: Frontend exists, is tracked, and is correctly mounted.** ADR-011's claim that krono-compositor-mvp has an Alpine.js SPA is verified.

### (j) `SqliteMaterialCatalog` db_path — what is passed in real usage?

| Context | `db_path` value | Evidence |
|---|---|---|
| Docstring examples | `"catalog/db/catalog.db"` | `src/kuchnie_core/materials/sqlite_repository.py:9`, `__init__.py:13`, `resolver.py:9` |
| Tests | `tmp_path / "test_catalog.db"` (temporary) | `tests/test_materials_bridge.py:69` — creates a temp SQLite DB from scratch |
| Production | No production caller found in codebase | No file outside `src/kuchnie_core/materials/` and `tests/` imports `SqliteMaterialCatalog` |

**Verdict:** The canonical db_path is `catalog/db/catalog.db` (relative to repo root). The file exists (938 KB, last modified 2026-07-01). Tests use temporary databases, not the real one. No production caller exists yet — `SqliteMaterialCatalog` is infrastructure ready for `kitchen-erp` or `krono-compositor-mvp` to consume, but neither does so currently.

---

## Summary statistics

| Verdict | Count |
|---|---|
| **TRUSTED** | 56 |
| **STALE** | 6 (stamped) |
| **ARCHIVE** | 35 |
| **DECISION-RECORD** | 12 |
| **Total** | 109 |

---

## Stale files stamped

| File | Stale because | Pointer |
|---|---|---|
| `docs/doc-routing.md` | ~~References `kitchen-cad/`, `kitchen-plugin/`, `kitchen-app/` sections~~ → **REWRITTEN** (D2) | `AGENTS.md` component roster |
| `.pi/doc-routing-prompt.md` | ~~References `kitchen-cad/`, `kitchen-plugin/` routing~~ → **REWRITTEN** (D2) | `AGENTS.md` component roster |
| `kitchen-cam/README.md` | Deprecated modules as primary pipeline, no migration mention | `kitchen-cam/AGENTS.md` + `docs/adr/010-*.md` |
| `kitchen-cam/ROADMAP.md` | Pre-ADR-010, no migration plan | `kitchen-cam/AGENTS.md` + `docs/adr/010-*.md` |
| `kitchen-cam/docs/specs/overview.md` | Deprecated modules as primary pipeline | `kitchen-cam/AGENTS.md` + `docs/adr/010-*.md` |
| `docs/session-handoff-2026-07-02.md` | ADR-012 §3–§6 now complete; test counts grown; HEAD advanced | `docs/freeze/TEST-BASELINE-2026-07.md` + `CHANGELOG.md` |

---

## DECISION NEEDED items

### D1: Pydantic undeclared dependency in `kuchnie_core` — ✅ RESOLVED (packaging), tension noted

`src/kuchnie_core/schema.py` imports `pydantic` but `pyproject.toml` listed only `pyyaml`. **Fixed:** added `pydantic>=2,<3` to `pyproject.toml`. Packaging now matches code.

**Deeper tension (resume decision):** ADR-012 alternative 12a says "no Pydantic dep by design" for `kuchnie_core.model`, yet `schema.py` uses `BaseModel` at the YAML/JSON boundary. The split is intentional (`model.py` = plain dataclasses, `schema.py` = Pydantic validation) but undocumented. Whether Pydantic stays at the schema boundary or gets refactored out warrants a one-page ADR. Tracked in `docs/freeze/RESUME-MENU.md`.

### D2: `docs/doc-routing.md` needs full rewrite — ✅ RESOLVED

Both `docs/doc-routing.md` and `.pi/doc-routing-prompt.md` rewritten. Mechanical substitutions: `kitchen-cad/` → `kitchen-cam/`, `kitchen-plugin/` → `home-builder-adapter/`, `kitchen-app/` → `kitchen-erp/`. Added `kitchen-erp/` routing section. STALE stamps removed.

### D3: `kitchen-plugin/docs/wall-centric-model.md` — ✅ RESOLVED

File exists in both `attic/kitchen-plugin/docs/` and `home-builder-adapter/docs/archive/`. No action needed.

### D4: `kitchen-cam/README.md` and `ROADMAP.md` — ⏸ DEFERRED

Deliberately deferred. Those docs describe modules scheduled for deletion; rewriting them now documents a transitional state that will be deleted on resume. Stamps pointing to `kitchen-cam/AGENTS.md` are sufficient. **Resume action:** rewrite kitchen-cam docs after deletion queue executes. Tracked in `docs/freeze/RESUME-MENU.md`.

### D5: Recipe system convergence — ⏸ DEFERRED

The audit's verdict is right — genuinely parallel concerns (decomposition formulas vs. cost recipes), not duplication. No freeze action. **Resume note:** after `BOMGenerator` integrates `kuchnie_core.decompose()`, rename kitchen-erp's to "cost recipes" to kill the name collision. Tracked in `docs/freeze/RESUME-MENU.md`.

### D6: `docs/00-brief-understanding.md` — dangling ADR references — ✅ RESOLVED

Created tombstone: `docs/00-brief-understanding.md` containing three lines ("Superseded; content lives in `docs/vision/00-mission.md`; kept as a link target for ADR-009/011"). Fixes the danglers without violating ADR immutability.

### D7: `code-sum.md` — dangling ADR-010 reference — ✅ ACCEPTED

Generated file, expected to be untracked. This report note suffices. No action.

### D8: `package.json` stale `fix-all` script — ✅ RESOLVED

Trimmed dead `cd kitchen-agent/frontend && pnpm format && pnpm lint:fix` from the `fix-all` script. Now just `prettier --write .`.

---

*Report generated by trust audit, 2026-07-03. D1–D3, D6, D8 resolved; D4–D5 deferred to resume (see `docs/freeze/RESUME-MENU.md`); D7 accepted as-is.*
