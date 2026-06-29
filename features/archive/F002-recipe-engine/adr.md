# ADR — F002 — Recipes as YAML Data, Evaluated by an asteval-Sandboxed Engine in CAD

**Date:** 2026-06-28
**Status:** `Proposed`
**Feature:** F002
**Author:** solo dev

---

## Context

Panel dimensions in all five reference CAD systems (PRO100, Polyboard, Winner Flex, TopSolid'Wood, PaletteCAD) are computed from **formulas**, not hardcoded. The Blender plugin uses Geometry Node driver expressions (`"var_width - 2 * var_thickness"`) — code-not-data. Our existing `kitchen-app/kitchen_erp/recipe_loader.py` introduced a JSON-recipe system but uses Python `eval()` — a known RCE risk noted in earlier audits.

`03_implementation_placement.md` § Pattern 2 mandates: recipe **data** lives in `kuchnie_core`, evaluation **engine** lives in `kitchen-cad`. F001 published `ConstructionMethod` and the `kitchen_config.yaml` v1.0 schema. F002 builds on F001 to make panel decomposition fully data-driven.

The decision needs to be made **now** because: (1) F003 (templates) depends on `recipe_id` resolution; (2) F004 (validation) depends on knowing what panels a recipe emits; (3) every week without F002 means more hardcoded `decompose_*` functions in `kuchnie_core/catalog.py` to migrate later.

---

## Decision

We will:

1. Define `Recipe`, `PanelRecipe`, `FormulaSpec`, `EdgeAssignment`, `DrillPatternRef` as immutable Pydantic models in `src/kuchnie_core/recipes.py`. Recipes are stored as one YAML file per recipe in `src/kuchnie_core/recipes/`. A module-level `RecipeRegistry` loads and indexes them by `recipe_id`.

2. Implement `RecipeEngine` in `kitchen-cad/src/kitchen_cad/recipe_engine.py`. The engine takes a `CabinetInstance`, the resolved `ConstructionMethod`, and a `Recipe`, builds a `FormulaContext`, evaluates panel formulas in **topologically sorted dependency order**, and returns `list[Panel]`. Formulas are evaluated with **`asteval`** — a sandboxed AST-walking numeric evaluator.

3. Each `FormulaSpec` is parsed once at recipe-load time into a reusable interpreter symbol table; per-decomposition cost is evaluation only.

4. Delete or stub `kitchen-app/kitchen_erp/recipe_loader.py`. The unsafe `eval()` is removed from the repository.

5. Five worked recipes ship in Phase 2: `base_door_single`, `base_drawer_3`, `wall_door_single`, `tall_pantry`, `corner_diagonal`. Each has a fixture-based unit test asserting concrete panel dimensions.

The `Recipe` Pydantic model becomes part of Core's published API. The engine's interface (`decompose(cabinet, construction, recipe) -> list[Panel]`) is the contract between Core's data and CAD's evaluation.

---

## Alternatives Considered

| Option | Why rejected |
|---|---|
| **A. Keep `eval()` from legacy `recipe_loader.py`** | RCE risk. YAML files are hand-edited; a malicious recipe could run arbitrary code. Non-negotiable. |
| **B. `simpleeval`** | Smaller community than asteval; less numeric tooling (no `min`/`max`/`ceil` out of the box without configuration). Documented as fallback if asteval becomes unmaintained. |
| **C. Hand-rolled AST walker** | Significant maintenance burden for a solo dev. Reimplements asteval poorly. Only chosen if both asteval and simpleeval fail to meet needs — neither will. |
| **D. Lambdas / Python snippets embedded in YAML** | Same RCE issue as `eval`. Defeats the data-not-code premise. |
| **E. Sympy expressions** | Symbolic algebra engine — overkill for runtime numeric evaluation. Slow startup, heavyweight dependency. |
| **F. Recipes as Python modules** (one `.py` per recipe) | Carpenters cannot edit Python. Defeats the goal of data-driven cabinet types. Also blocks recipe linting from non-Python tools. |
| **G. Recipes in SQLite / database** | Sync friction (which file is truth?), not diffable in git, no easy review of changes. YAML in git is the right answer. |
| **H. Engine in `kuchnie_core` instead of `kitchen-cad`** | Couples Core to `asteval` and topological sort. `03_implementation_placement.md` Pattern 2 explicitly splits to keep Core lightweight. Violating this would re-introduce the heavy-Core problem we just designed away. |
| **I. Engine in a new `kitchen-recipes` package** | Premature for a solo dev. The engine is small (≤ 500 LOC expected); a separate package is overhead without benefit. |
| **J. No formula dependencies** (every formula references only `cabinet.*` and `construction.*`) | Forces redundancy: `shelf.width` must repeat the full expression for `top.width` instead of `panels.top.width - 4`. Increases recipe size and maintenance cost. The DAG cost is small. |
| **K. Fixed-point iteration instead of topological sort** | Hides circular-dependency bugs (engine just oscillates). Topological sort fails fast and explicitly. |
| **L. Conditional panels** (`if cabinet.has_back:`) | Adds complexity to the YAML grammar. If structure differs, write a separate recipe. Composability and simplicity beat conditionals. |
| **M. Recipe inheritance** (`extends: base_door_single`) | Premature optimization. For v1.0, 10–15 recipes total are expected; YAML duplication is acceptable. Revisit if recipe count exceeds 40. |
| **N. JSON instead of YAML** | YAML's comments and readability matter for recipes hand-edited by a carpenter. JSON's strict syntax is friction here. |
| **O. Inline drill positions in recipes** | Couples F002 to F008 (associative machining features). Recipes emit named pattern references (`drill_pattern: system32`); F008's engine resolves them. Keeps F002 small. |

---

## Consequences

### Positive
- **Add a cabinet type by writing one YAML.** No Python edits, no release. The solo dev's leverage point.
- **`eval()` removed from the repo.** Safer, auditable, lintable.
- **Same engine drives BOM and CAM export** — single source of panel truth.
- **Recipes diff cleanly in git** — code reviews on cabinet changes become readable.
- **Test surface is small and predictable**: one unit test per recipe + four engine-behavior tests cover the design.
- **Performance budget is healthy** — pre-parsing formulas at load makes per-decomposition cost near-instant.

### Negative
- **Two contexts touched** (Core data + CAD engine). The split is mandatory by `03_implementation_placement.md`, but every future change to the `Recipe` model touches both. Mitigated by keeping the model frozen and additive.
- **`asteval` becomes a dependency** of `kitchen-cad`. Acceptable — it's a small, mature library with no transitive concerns.
- **DAG and topological sort code to write and test.** ~50 LOC; manageable but non-trivial for a solo dev.
- **Legacy `decompose_dolna_szufladowa()` etc. functions in `kuchnie_core/catalog.py` need migration.** F002 quarantines them with deprecation warnings; full removal is a backlog item.

### Neutral
- **Recipe count grows over time.** Expected: 10–15 by end of v1.0, 30–50 long-term. YAML is fine at this scale; no need for indexing or search.
- **`Panel` model gains `recipe_role: str` field.** Additive; existing consumers ignore it.
- **The plugin's Geometry Node drivers are untouched.** They continue to compute their own dimensions inside Blender; the render adapter (F007) passes concrete panel dimensions to the plugin scene. Two parallel formula systems exist, but each serves a different consumer (CNC export vs visual render). This is acceptable per Rule 4 (plugin is a renderer).

---

## Affected Files (canonical)

### Created
- `src/kuchnie_core/recipes.py` — Pydantic models + `RecipeRegistry`
- `src/kuchnie_core/recipes/base_door_single.yaml`
- `src/kuchnie_core/recipes/base_drawer_3.yaml`
- `src/kuchnie_core/recipes/wall_door_single.yaml`
- `src/kuchnie_core/recipes/tall_pantry.yaml`
- `src/kuchnie_core/recipes/corner_diagonal.yaml`
- `kitchen-cad/src/kitchen_cad/recipe_engine.py` — `RecipeEngine`, `FormulaContext`, topological sort, asteval wiring
- `tests/core/test_recipes.py` — Pydantic model + registry tests
- `tests/cad/test_recipe_engine.py` — one test per recipe + behavior tests (cycles, unknowns, negatives)
- `tests/cad/test_recipe_engine_perf.py` — 100 decompositions < 2s

### Modified
- `src/kuchnie_core/model.py::Panel` — add `recipe_role: str` field
- `src/kuchnie_core/bom.py` — call engine through a facade instead of legacy `decompose()` for cabinets that have a recipe
- `kitchen-cad/pyproject.toml` (or `requirements.txt`) — add `asteval`
- `docs/GLOSSARY.md` — promote 8 placeholder/refined terms to concrete entries
- `docs/01_architecture.md` — Context Map shows Core→CAD recipe data flow

### Deleted or stubbed
- `kitchen-app/kitchen_erp/recipe_loader.py` — deleted if no callers, stubbed with `NotImplementedError` if any caller remains pending its own migration

### Quarantined (legacy, deprecated with warning)
- `src/kuchnie_core/catalog.py::decompose_dolna_szufladowa`
- `src/kuchnie_core/catalog.py::decompose_gorna_drzwiowa`
- `src/kuchnie_core/catalog.py::decompose_dolna_legrabox`

> Full removal of legacy `catalog.py` decomposers is **backlog** — happens when every used cabinet type has a YAML recipe.

---

## LLM Hints

> Direct instructions for future LLM sessions in this decision area.

- **When asked "where do recipes live?"** → `src/kuchnie_core/recipes/*.yaml`. Data in Core, engine in CAD.
- **When asked "can we use `eval()`?"** → **No.** RCE risk. `asteval` is the answer. See Alternative A.
- **When asked "should we use simpleeval / sympy / a custom parser?"** → No. asteval. simpleeval is the documented fallback if asteval is ever unmaintained. See Alternatives B, C, E.
- **When asked "should recipes be Python modules / classes?"** → No. They are data. Carpenters edit YAML. See Alternative F.
- **When asked "should recipes go in a database?"** → No. YAML in git. See Alternative G.
- **When asked "should the engine live in `kuchnie_core`?"** → **No.** Core stays light. Engine is in `kitchen-cad`. The `Recipe` model in Core is the contract. See Alternative H and `03_implementation_placement.md` Pattern 2.
- **When asked "can formulas have if/else?"** → No. Write a separate recipe. See Alternative L.
- **When asked "can recipes extend / inherit other recipes?"** → Not in v1.0. Revisit if recipe count > 40. See Alternative M.
- **When asked "where do drill positions come from?"** → Recipes emit named `DrillPatternRef`s (e.g., `"system32"`). The pattern→`DrillPoint` engine is **F008**. F002 emits references only.
- **When asked "where does `material_role: front` resolve to an actual decor?"** → F005 (`MaterialResolver`). F002 emits the role string verbatim.
- **When asked "what about the plugin's Geometry Node drivers?"** → Leave them alone. The plugin renders its own geometry; the render adapter (F007) feeds concrete dimensions. Two parallel formula systems serve two different consumers. Rule 4 stands.
- **When asked "can we cache recipe-engine results across calls?"** → Yes, by `(cabinet_id, construction_method_id, recipe_id)`-keyed cache, but this is a **Should** not a **Must**. Invalidate on any input change.
- **When asked "should formulas support string operations?"** → No. Numeric only. asteval is configured to expose `min/max/abs/round/floor/ceil` and nothing else.
- **Do not propose:**
  - Adding Jinja2 or any templating to recipes (asteval handles expressions; structure stays YAML).
  - Making the engine async (synchronous, single-process is correct).
  - Caching at module import time (recipes must reload during dev — registry tracks file mtime).
  - Reimplementing topological sort with a graph library (the recipes are small; ~10–20 panels each; a hand-rolled sort is fine and dependency-free).
- **Related ADRs:**
  - **F001 (Construction Method)** — provides the `ConstructionMethod` fields read by `FormulaContext`.
  - **F003 (Template Registry)** — templates carry `recipe_id`s that resolve through this engine.
  - **F004 (Validation Gates)** — Gate 4 (CAM-Readiness) validates engine output.
  - **F007 (Blender Adapter)** — consumes engine output to populate the render scene.
  - **F008 (CLI Cut List / DXF)** — consumes engine output and resolves `DrillPatternRef`s into concrete `DrillPoint`s.

---

## Sign-off

- [ ] `docs/GLOSSARY.md` updated with 8 terms.
- [ ] `asteval` declared as a dependency of `kitchen-cad` only.
- [ ] Tests in place: `tests/core/test_recipes.py`, `tests/cad/test_recipe_engine.py`, `tests/cad/test_recipe_engine_perf.py`.
- [ ] All 5 worked recipes committed and passing tests.
- [ ] No `eval(` calls remain in `src/`, `kitchen-cad/`, `kitchen-app/`.
- [ ] Legacy `decompose_*` functions in `kuchnie_core/catalog.py` carry deprecation warnings.
- [ ] Status moved from `Proposed` → `Accepted` after first green test run.
