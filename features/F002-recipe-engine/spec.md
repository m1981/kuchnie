# F002 — Recipe Engine (YAML-Driven Panel Decomposition)

## Job Story

**When** I am decomposing a `CabinetInstance` into the panels and machining operations needed to manufacture it,
**I want to** read the panel definitions from a declarative YAML **recipe** (formulas, edge specs, drill patterns) keyed by the cabinet's template ID, with formulas evaluated through a safe sandboxed evaluator,
**So I can** add or tune cabinet types by editing one YAML file (no Python edits, no recompilation, no security risk from `eval`), and so the same recipes drive both BOM and CAM export consistently.

---

## Bounded Context

- **Primary (the one that OWNS this):** Split intentionally — **data lives in `Core`**, **engine lives in `CAD`**.
  - `Core` (`src/kuchnie_core/`) owns the recipe data model and YAML files.
  - `CAD` (`kitchen-cad/`) owns the `RecipeEngine` (evaluator).
- **Touched (consumers, must have explicit reason):**
  - `Core` BOM pipeline — `kuchnie_core/bom.py` calls the engine via a thin facade to get panels for cost calculation.
  - `Web` (Phase 6, not now) — will display per-panel cost breakdowns; F006's concern, not F002's.

> **Change Locality Test result:** primary changes touch Core (data + model) + CAD (engine). The split is dictated by `03_implementation_placement.md` § Pattern 2 — the engine has heavier dependencies (`asteval`, topological sort) that Core must not inherit. The contract between them is the `Recipe` Pydantic model in Core. ✅ Passes.

---

## Subdomain Classification

- [x] **Core** — competitive advantage. Recipe-as-data is the pattern all five commercial CAD systems use; this is what makes the system flexible and maintainable. We invest engineering time here.
- [ ] Supporting
- [ ] Generic

**Reasoning:** With recipes-as-code, every new cabinet type costs Python skill + a release. With recipes-as-data (this feature), a carpenter can add a new cabinet by writing one YAML and a test fixture. That delta is the system's leverage.

---

## Data Ownership

- **Canonical writes happen in:**
  - Recipe definitions: `src/kuchnie_core/recipes/*.yaml` (hand-edited).
  - Recipe model: `src/kuchnie_core/recipes.py::Recipe` (Pydantic, immutable at load).
- **Read-only consumers:**
  - `kitchen-cad/src/kitchen_cad/recipe_engine.py::RecipeEngine` — loads recipes via `RecipeRegistry`, evaluates against a `FormulaContext`, produces `list[Panel]`.
  - `kuchnie_core/bom.py` — consumes the engine output (panels) to calculate BOM.
- **Storage format:** YAML, one file per recipe, ID matches `CabinetTemplate.recipe_id` (introduced in F003 — for F002 we test against fixture cabinets directly, no template registry needed yet).

---

## Scope — MoSCoW

### Must (do not ship without)

#### Recipe data model (Core)
- [ ] `src/kuchnie_core/recipes.py` with Pydantic models:
  - [ ] `Recipe` — top-level recipe definition.
  - [ ] `PanelRecipe` — one panel's spec (role + formulas + edges + drilling refs + material role).
  - [ ] `FormulaSpec` — typed wrapper around a formula string with declared variables.
  - [ ] `EdgeAssignment` — per-edge material role (e.g., front edge = "front_color").
  - [ ] `DrillPatternRef` — reference to a named drill pattern (e.g., `system32`, `hinges_3`).
- [ ] `RecipeRegistry` — load all YAMLs from a directory, lookup by `recipe_id`.

#### Formula engine (CAD)
- [ ] `kitchen-cad/src/kitchen_cad/recipe_engine.py::RecipeEngine`.
- [ ] `FormulaContext` — read-only object exposing:
  - `cabinet.width_mm`, `cabinet.height_mm`, `cabinet.depth_mm`, `cabinet.shelf_count`, `cabinet.door_count`, `cabinet.drawer_count`
  - `construction.side_thickness_mm`, `construction.front_thickness_mm`, `construction.back_thickness_mm`, `construction.back_recess_mm`, `construction.front_overlay_mm`, `construction.front_gap_mm`, `construction.shelf_thickness_mm`, `construction.top_thickness_mm`, `construction.bottom_thickness_mm`
  - `panels.<role>.width`, `panels.<role>.height`, `panels.<role>.depth` (derived chain — only roles already evaluated upstream)
- [ ] Safe evaluator using **`asteval`** (or `simpleeval` as documented fallback).
- [ ] **Topological sort** of panel dependencies — fail fast on circular references.
- [ ] `RecipeEngine.decompose(cabinet, construction, recipe) -> list[Panel]`.

#### Replace legacy unsafe code
- [ ] Delete or quarantine `eval(...)` call in `kitchen-app/kitchen_erp/recipe_loader.py` (legacy).
  - Option A (preferred): delete `recipe_loader.py` if no callers remain after F002.
  - Option B: leave behind a stub that raises `NotImplementedError("Use kitchen_cad.recipe_engine instead")`.
- [ ] Document the deprecation in the ADR.

#### Five worked recipes (gate-blocking per `docs/PHASES.md`)
- [ ] `src/kuchnie_core/recipes/base_door_single.yaml`
- [ ] `src/kuchnie_core/recipes/base_drawer_3.yaml`
- [ ] `src/kuchnie_core/recipes/wall_door_single.yaml`
- [ ] `src/kuchnie_core/recipes/tall_pantry.yaml`
- [ ] `src/kuchnie_core/recipes/corner_diagonal.yaml`

#### Per-recipe tests
- [ ] Each recipe has a fixture `CabinetInstance` + `ConstructionMethod` and an expected list of panel dims.
- [ ] Test asserts: panel count, each panel's dimensions, edge assignments.

#### Performance gate
- [ ] Microbench: 100 cabinet decompositions in < 2.0s on the dev machine.
- [ ] If exceeded, document in `tasks.md` notes — but still gate-blocking.

### Should (do if time permits)

- [ ] `kitchen-cli decompose <cabinet_id> --kitchen <yaml>` — CLI to print panels for one cabinet.
- [ ] Recipe linter: `kitchen-cli lint-recipes` — checks formula vars resolve, no cycles, all roles unique within a recipe.
- [ ] Caching layer in `RecipeRegistry` (load YAML once per process; auto-invalidate on file mtime change in dev mode).

### Could (almost certainly defer)

- [ ] Recipe inheritance (`extends: base_door_single`) — premature; YAML duplication is fine for v1.0.
- [ ] Visual recipe debugger / diagram export.
- [ ] Recipe versioning per file (`recipe_version: 1.0`) — defer until first breaking change.

### Won't (this iteration — explicit cuts)

- ❌ **Web UI for editing recipes.** Carpenters edit YAML in a text editor; F006 is not this.
- ❌ **Inter-recipe references** (one recipe pulls panels from another). Each recipe is self-contained.
- ❌ **Conditional panels** (`if cabinet.has_back: ...`) — every recipe is deterministic. If you need conditional structure, write a separate recipe (`base_door_single_open_back.yaml`).
- ❌ **Runtime panel role discovery.** The list of allowed roles is enumerated in `PanelRole` (already exists in `kuchnie_core/model.py`). Adding a new role requires a code change.
- ❌ **Templates.** F003 introduces `CabinetTemplate`. F002 tests against hand-crafted fixture `CabinetInstance`s.
- ❌ **Machining feature evaluation** (associative drills/grooves). F002 emits **drill pattern references** (string names like `"system32"`); F008 implements the engine that turns those into concrete `DrillPoint`s. This split keeps F002 small.
- ❌ **Reading recipes from Catalog database.** Recipes are domain truth in Core, not vendor data.

---

## Change Locality Test

- [x] Editing **two bounded contexts** (Core data + CAD engine) — but this split is **explicit and mandatory** per `03_implementation_placement.md` § Pattern 2. The contract between them (`Recipe` model) is published in Core.
- [x] **One published contract change**: `Recipe` Pydantic model becomes part of Core's published surface. `kitchen_config.yaml` schema is **unchanged** by F002 — recipes are referenced by ID but stored separately.
- [x] **Passes** with explicit dual-context justification.

---

## Glossary Impact

**New terms** (must be added to `docs/GLOSSARY.md` in the implementation commit):

- `Recipe` — already a placeholder in glossary; F002 makes it concrete with file-of-record `src/kuchnie_core/recipes.py::Recipe`.
- `RecipeEngine` — already placeholder; F002 makes it concrete with file-of-record `kitchen-cad/src/kitchen_cad/recipe_engine.py::RecipeEngine`.
- `PanelRecipe` — one panel's slot in a recipe.
- `FormulaSpec` — typed wrapper around a formula string.
- `FormulaContext` — read-only evaluation context (cabinet + construction + derived panels).
- `RecipeRegistry` — service that loads/queries recipes by ID.
- `EdgeAssignment` — per-edge material-role mapping in a recipe.
- `DrillPatternRef` — recipe-side reference to a named drill pattern (engine deferred to F008).

**Existing terms refined:**

- `Panel` — gains an explicit `recipe_role: str` field (e.g., `"side_left"`, `"top"`, `"shelf"`, `"door_1"`). Lets BOM and CAM trace each panel back to its recipe slot.
- `MaterialRef` — gains a notion of **material role** strings (`"body"`, `"front"`, `"back"`, `"shelf"`, `"front_color"` for edges) that F005 will fully realize. F002 uses string roles directly; F005 adds the resolver layer.

---

## Acceptance Criteria

The feature is **done** when:

- [ ] `src/kuchnie_core/recipes.py` exists with all Pydantic models listed above.
- [ ] `kitchen-cad/src/kitchen_cad/recipe_engine.py` exists with `RecipeEngine`, `FormulaContext`.
- [ ] `asteval` (or `simpleeval`) is a declared dependency of `kitchen-cad` only — **not** of `kuchnie_core`.
- [ ] All 5 recipes from "Must" exist and load without warnings.
- [ ] Tests pass: `pytest tests/core/test_recipes.py tests/cad/test_recipe_engine.py`.
  - [ ] One unit test per recipe asserting concrete panel dimensions against a fixture.
  - [ ] Circular-dependency test: a malformed recipe with `a depends on b depends on a` raises a clear error.
  - [ ] Unknown-variable test: a recipe referencing `cabinet.nonexistent_field` raises a clear error.
  - [ ] Negative-dimension test: a recipe producing a zero or negative panel dimension is rejected with a clear error pointing to the recipe and role.
- [ ] Performance test: `tests/cad/test_recipe_engine_perf.py` asserts 100 decompositions in < 2.0s.
- [ ] `recipe_loader.py` from `kitchen-app` is deleted or stubbed; no remaining `eval(` calls anywhere in the repo (verify with `grep -rn 'eval(' src/ kitchen-cad/ kitchen-app/`).
- [ ] `docs/GLOSSARY.md` updated with 8 new/refined terms.
- [ ] `docs/01_architecture.md` Context Map updated to show recipe data flow (Core → CAD engine).
- [ ] ADR `features/F002-recipe-engine/adr.md` status = `Accepted`.
- [ ] `status.md` set to `done`.
- [ ] `features/INDEX.md` updated.
- [ ] Phase 2 gate criteria in `docs/PHASES.md` ticked.

---

## Out of Scope (anti-drift)

- ❌ **Plugin extension.** The Blender plugin does not see recipes. The render adapter (F007) calls the engine to get panels for the scene, but the plugin itself is untouched.
- ❌ **Reflex UI.** F006 will surface recipes (template browser shows "what panels this template produces") but F002 ships no UI.
- ❌ **Template registry.** F003 introduces `CabinetTemplate` linking to `recipe_id`. For F002, tests construct fixture `CabinetInstance`s with explicit `recipe_id` strings.
- ❌ **Material resolution.** Recipes emit material **role strings** ("body", "front"). The translation from role string → concrete decor is F005's job (`MaterialResolver`).
- ❌ **Concrete drill positions.** Recipes name **drill patterns** (`drill_pattern: system32`); F008 turns named patterns into `DrillPoint` lists.
- ❌ **Hot-reload of recipes in production.** Dev-mode mtime check is OK as a "Should"; production reload would need explicit invalidation we don't need yet.
- ❌ **Recipe migration tooling.** v1.0 recipes are the first generation; no migration exists yet.
- ❌ **Worktop / accessory decomposition.** Recipes describe **panels only**. Worktops are computed elsewhere; accessories come from the cabinet's `SubAssembly` declaration (F001 / pre-existing).

---

## References

- **Pattern source:** `docs/02_pattern_analysis.md` § Pattern 2 (Panel Derivation Formulas, from all five commercial systems)
- **Placement decision:** `docs/03_implementation_placement.md` § Pattern 2 — split Core (data) + CAD (engine)
- **Process rules:** `docs/04_solo_dev_process.md`
- **Related ADRs:**
  - `features/F001-construction-method/adr.md` — provides `ConstructionMethod` fields read by formulas
  - `features/F002-recipe-engine/adr.md` — this feature's ADR
- **Related features:**
  - **Depends on:** F001 (recipes read `construction.*` fields)
  - **Enables:**
    - F003 (templates carry `recipe_id`)
    - F004 (Gate 4 / CAM-Readiness validates recipe output)
    - F007 (render adapter uses engine to get panels)
    - F008 (CLI cut list calls engine, then resolves `DrillPatternRef`s to concrete drills)
  - **Conflicts with:** `kitchen-app/kitchen_erp/recipe_loader.py` (legacy `eval`) — F002 deletes or stubs it.

---

## Recipe YAML — Worked Example (for spec clarity)

This is what a recipe looks like. Belongs in `src/kuchnie_core/recipes/base_door_single.yaml`. Not implementation — illustration so reviewers see the shape:

```yaml
recipe_id: base_door_single
description: "Single-door base cabinet with 1 fixed shelf"

panels:
  - role: side_left
    material_role: body
    formula:
      width:     "cabinet.depth_mm"
      height:    "cabinet.height_mm"
      thickness: "construction.side_thickness_mm"
    edges:
      front: front_color
      rear:  body_color
      top:   body_color
      bottom: body_color
    drilling:
      - pattern: system32
        face: inner

  - role: side_right
    material_role: body
    formula:
      width:     "cabinet.depth_mm"
      height:    "cabinet.height_mm"
      thickness: "construction.side_thickness_mm"
    edges:
      front: front_color
      rear:  body_color
      top:   body_color
      bottom: body_color
    drilling:
      - pattern: system32
        face: inner

  - role: top
    material_role: body
    formula:
      width:     "cabinet.width_mm - 2 * construction.side_thickness_mm"
      depth:     "cabinet.depth_mm - construction.back_thickness_mm - construction.back_recess_mm"
      thickness: "construction.top_thickness_mm"
    edges:
      front: front_color

  - role: bottom
    material_role: body
    formula:
      width:     "panels.top.width"      # ← derived chain
      depth:     "panels.top.depth"
      thickness: "construction.bottom_thickness_mm"
    edges:
      front: front_color

  - role: shelf
    material_role: shelf
    quantity_formula: "cabinet.shelf_count"
    formula:
      width:     "panels.top.width - 4"   # 2mm clearance per side
      depth:     "panels.top.depth - 10"  # 10mm setback from front
      thickness: "construction.shelf_thickness_mm"
    edges:
      front: front_color

  - role: back
    material_role: back
    formula:
      width:     "cabinet.width_mm - 2 * construction.side_thickness_mm + 2 * construction.back_recess_mm"
      height:    "cabinet.height_mm - 2 * construction.back_recess_mm"
      thickness: "construction.back_thickness_mm"
    # no edge banding on back

  - role: door
    material_role: front
    quantity_formula: "cabinet.door_count"
    formula:
      width:     "cabinet.width_mm - 2 * construction.front_overlay_mm"
      height:    "cabinet.height_mm - 2 * construction.front_overlay_mm"
      thickness: "construction.front_thickness_mm"
    edges:
      front:  front_color
      rear:   front_color
      left:   front_color
      right:  front_color
      top:    front_color
      bottom: front_color
```

> **Formula scope rules** (enforced by `FormulaContext`):
> - `cabinet.*` — the `CabinetInstance` (read-only).
> - `construction.*` — the resolved `ConstructionMethod` (read-only).
> - `panels.<role>.*` — only **already-evaluated** panels (topological predecessors).
> - **No Python builtins.** No `import`. No `__getattr__` tricks. `asteval` sandbox.
> - Allowed operators: `+ - * / // % ** ()` and comparison for `quantity_formula`.

---

## Open Questions

> All must be answered before coding begins.

- [x] **Q1:** asteval or simpleeval? → **A:** asteval. Better numeric support, larger user base, well-maintained. simpleeval is the documented fallback if asteval becomes unmaintained.
- [x] **Q2:** How is `quantity_formula` evaluated for panels that multiply (e.g., shelves)? → **A:** Same engine. `quantity_formula: "cabinet.shelf_count"` returns an int; engine emits N panels each with the same dimension formulas. If `quantity_formula` returns 0, the panel role is skipped.
- [x] **Q3:** What happens if a recipe is missing a panel role that the cabinet "needs"? → **A:** Nothing — the recipe defines what panels exist. F004's Cabinet validation gate (Phase 4) checks template/recipe consistency. F002 trusts the recipe author.
- [x] **Q4:** Should formulas support functions (`min`, `max`, `ceil`, `round`)? → **A:** Yes — asteval whitelists a small numeric set: `min`, `max`, `abs`, `round`, `floor`, `ceil`. Document the allowed list in `recipes.py` docstring. No string functions, no I/O.
- [x] **Q5:** Where does `material_role` get resolved to a concrete `Decor`? → **A:** Not here. F005 (`MaterialResolver`) walks a three-stage chain `material_role → project_slot → decor`. A `CabinetInstance.material_refs` maps `{role: slot_name}` (e.g., `{"body": "project_body", "front": "project_front"}`); the `Kitchen.material_slots` then maps `{slot_name: decor_id}` (e.g., `{"project_body": "kronospan_u112_pm"}`). F005 owns the full chain. F002 emits the role string verbatim on each `Panel`; it never sees decor IDs.

  > **Edge roles:** Recipes may emit edge role strings with the `_color` suffix (`front_color`, `body_color`). Convention: `<role>_color` means "use the paired edge of the decor in slot `<role>`". F005's `resolve_role(role).paired_edge_id` provides this. F002 emits the suffix string verbatim; F005 resolves it; F008 consumes the result in cut-list edge columns. The `_color` form is not a separate slot in `material_slots`.
- [x] **Q6:** What's the relationship to `kuchnie_core/catalog.py::TYPE_REGISTRY` (legacy)? → **A:** F002 supersedes the hardcoded `decompose_dolna_szufladowa()` etc. functions. They are quarantined (left in place but called only as a fallback for fixture cabinets that lack a `recipe_id`, with a deprecation warning). Full removal is a backlog item once all cabinet types have YAML recipes.
- [x] **Q7:** Does the engine cache parsed formulas? → **A:** Yes — `FormulaSpec` parses once at recipe-load time into an `asteval.Interpreter` symbol table; per-decomposition cost is evaluation only. Critical to hit the 2s/100 perf gate.

**All Open Questions resolved.** Spec is **ready** for implementation.
