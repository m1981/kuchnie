# ADR — F003 — Cabinet Templates as YAML, Curated by Category, Instantiated to CabinetInstance

**Date:** 2026-06-28
**Status:** `Proposed`
**Feature:** F003
**Author:** solo dev

---

## Context

A working kitchen configurator needs a curated menu of cabinet types — not a freeform "specify all dimensions yourself" UX. PRO100's leverage point is its template library; users drag a "60 cm jednodrzwiowa" into a row and tune what matters. Every other commercial CAD system converges on the same pattern.

F001 published `ConstructionMethod`. F002 published `Recipe` (HOW panels are computed from dimensions). What's missing is the bridge: **a named, default-dimensioned, sub-assembly-equipped object that a user can pick from a list**. That bridge is the `CabinetTemplate`.

The decision needs to be made **now** because: (1) Phase 4 (Validation Gates) wants to validate cabinets against template constraints; (2) Phase 6 (Web Sidebar) is unbuildable without a registry to populate the sidebar; (3) the Polish-market curation (mm-correct widths, slupek pod piekarnik, narożna diagonalna) is encoded in templates — getting this right early saves a re-curation later.

---

## Decision

We will introduce `CabinetTemplate` as an immutable Pydantic model in `src/kuchnie_core/templates.py`, with templates stored as one YAML per file in `src/kuchnie_core/templates/<category>/`. A `TemplateRegistry` module-level singleton loads and indexes templates; its `instantiate(template_id, overrides, project_default_construction_method_id) -> CabinetInstance` method is the canonical way to create a cabinet.

Templates carry:
- Identity (`template_id`, Polish label, English-ID, description, tags).
- Structure (`category`, `recipe_id`, optional `construction_method_id` override).
- Defaults (`default_dimensions`, `default_sub_assemblies`, `material_role_defaults`).
- Constraints (`dimension_constraints` — per-dim min/max).
- Presentation (`thumbnail` — relative PNG path).

Instantiation:
1. Validates overrides against `dimension_constraints` immediately; raises `TemplateInstantiationError` with the violating field and bound.
2. Resolves `construction_method_id`: template override → project default (F001 rule).
3. Auto-generates a short slug `cab_<6 hex>` as the `CabinetInstance.id`.
4. Merges sub-assembly overrides by `kind` (not full replace) to preserve unspecified defaults.
5. Sets `CabinetInstance.template_id` for traceability back to the template.

Twelve worked templates ship in Phase 3, covering Polish-market base / wall / tall / corner standards. Templates are organized by category subfolder (templates will grow to 30–50; flat would become unreadable). Recipes stay flat (fewer recipes, one per cabinet type).

The `CabinetTemplate` Pydantic model becomes part of Core's published API.

---

## Alternatives Considered

| Option | Why rejected |
|---|---|
| **A. No template layer; users specify every cabinet from scratch** | UX disaster. Even a 10-cabinet kitchen would take an hour to configure. Every commercial CAD ships templates for a reason. |
| **B. Templates as Python classes** (one class per template) | Carpenters cannot edit Python. Defeats the data-driven goal. Same rationale as recipes (F002). |
| **C. Templates as Python dataclasses defined in one big module** | Slightly better than (B) but still code-not-data. A Polish carpenter wanting to add `base_door_70` (atypical width but possible) shouldn't need a Python release. |
| **D. Templates in SQLite / database** | Sync friction (which is truth?), not diffable in git, no clean review of changes. YAML in git is the right answer (same as F002). |
| **E. Templates inside `catalog/`** | Catalog is **vendor data** (Kronospan, Egger decors and edges) — different lifecycle, different concept. Cabinet templates are **domain assets** owned by Core. Putting them in catalog would blur the bounded context. |
| **F. Flat templates folder** (no category subfolders) | At 30–50 templates, a flat folder becomes hard to navigate. Subfolders matching `CabinetCategory` enum make the structure self-documenting and lint-friendly. |
| **G. Programmatic variants** (loop over widths to auto-generate base_door_W for W in [30,40,50,60,80]) | Removes per-width searchability and diffability. Explicit YAMLs let a reviewer see "exactly what's offered" by `ls`. The mild duplication is acceptable at 12–50 templates. |
| **H. Recipe and template merged into one concept** | Loses the separation that's the system's value: one recipe can back many templates (base_door_30, base_door_40, base_door_60, base_door_80 all use `base_door_single`). Merging would force a recipe per width. |
| **I. Templates without dimension constraints (any value goes)** | Lets the user pass `width_mm: 50000`. The cabinet would technically construct in the recipe engine, but produce nonsense. Constraints catch this at instantiation, not at Gate 1, because the error is local to the template (width-out-of-range), not to the kitchen layout. |
| **J. Constraints inside `default_dimensions`** | Conflates value with rule. Two separate fields keep the YAML scannable: "what's the default" vs "what's allowed". |
| **K. Replace-all semantics on sub-assembly overrides** | If a user overrides only the shelf count, they shouldn't lose the door from the default. Merge-by-kind is the obvious win. Replace-all is available behind an explicit flag for the rare full-rewrite case. |
| **L. Auto-derive sub-assemblies from recipe panel output** | Sub-assemblies are user-facing assemblies (doors, drawers, shelves) — not the same as recipe panels (sides, top, back). The template author decides "this cabinet has 1 door and 1 shelf", and the recipe figures out the panels to support that. Auto-derivation would couple two intentionally separate concepts. |
| **M. UUID instance IDs** | Hard to read in YAML and CLI output. Short `cab_<6 hex>` slugs are readable and collision-acceptable for kitchen scales (worst case: tens of thousands of cabinets across all of a developer's projects). |
| **N. Templates carry localization for all languages** | v1.0 is Polish-only. Field names use `_pl` suffix to make future expansion mechanical (`label_en`, `label_de`). Speculative multi-language is YAGNI for now. |
| **O. Templates inherit from base templates** (`extends: base_door_60`) | Premature at 12 templates. Revisit when count > 40 and duplication becomes painful. Until then, explicit YAMLs are searchable. |
| **P. Per-customer template overlays** (load `~/.kuchnie/templates/` over base set) | Out of scope for solo-dev v1.0. Backlog if customers ever request custom templates. |

---

## Consequences

### Positive
- **One YAML adds one cabinet type** — the leverage point for a Polish carpenter expanding the offering.
- **Polish-market curation lives in data**, not code. `base_door_30/40/60/80` widths reflect what customers actually buy.
- **Reviewable history** — git log on `templates/base/base_door_60.yaml` shows every change to that cabinet's defaults.
- **Same registry powers web sidebar (F006) and CLI (F008)** — single source of cabinet-menu truth.
- **`CabinetInstance.template_id` enables traceability** — BOM can group by template, elevations can group by category.
- **Cross-feature integration test** (instantiate + decompose) catches recipe/template drift early.
- **Category subfolders make the catalog self-documenting** — a new contributor can `ls templates/` and see the structure.

### Negative
- **Two layers to maintain** when adding a cabinet type: write a recipe (F002), then write one or more templates (F003) that reference it. Mitigated by templates being short (~30 lines of YAML) and the recipe being the "interesting" file.
- **`CabinetInstance` model gains an optional `template_id` field.** Additive, but every consumer that touches `CabinetInstance` (CAD, Web, Render adapter) sees the new field. Optional + nullable keeps the change backward-compatible.
- **Thumbnails complicate Core's "pure data" stance.** PNGs are binary, not YAML. We accept this — they live in a `thumbnails/` subdirectory and the registry resolves paths but doesn't load images (consumers do that).
- **Sub-assembly merge semantics are subtle.** The merge-by-`kind` rule is documented but a future LLM might propose "let's replace all on override" thinking it's simpler. The ADR's LLM Hints section explicitly forbids this.

### Neutral
- **Template count will grow.** From 12 (Phase 3) to 30–50 (end of v1.0). YAML + git is fine at this scale; no need for indexing layer.
- **Polish labels in code-adjacent YAML.** Carpenters editing templates see Polish text in their editor — net positive for the developer.
- **The Blender plugin's own preset systems (`bay_presets.py`, etc.) are untouched** — they continue to serve the plugin's own UI (which we don't use). Our templates are independent. Two parallel template systems coexist for two different consumers. (Rule 4 stands.)

---

## Affected Files (canonical)

### Created
- `src/kuchnie_core/templates.py` — Pydantic models + `TemplateRegistry` + `TemplateInstantiationError`
- `src/kuchnie_core/templates/base/base_door_30.yaml`
- `src/kuchnie_core/templates/base/base_door_40.yaml`
- `src/kuchnie_core/templates/base/base_door_60.yaml`
- `src/kuchnie_core/templates/base/base_door_80.yaml`
- `src/kuchnie_core/templates/base/base_drawer_3_60.yaml`
- `src/kuchnie_core/templates/wall/wall_door_30.yaml`
- `src/kuchnie_core/templates/wall/wall_door_60.yaml`
- `src/kuchnie_core/templates/wall/wall_door_80.yaml`
- `src/kuchnie_core/templates/tall/tall_pantry_60.yaml`
- `src/kuchnie_core/templates/tall/tall_oven_60.yaml`
- `src/kuchnie_core/templates/corner/corner_diagonal_90.yaml`
- `src/kuchnie_core/templates/corner/corner_blind_left_100.yaml`
- `src/kuchnie_core/templates/thumbnails/*.png` — 12 placeholder PNGs
- `tests/core/test_template_registry.py`
- `tests/integration/test_template_to_panels.py` — F002 × F003 integration

### Modified
- `src/kuchnie_core/model.py::CabinetInstance` — add optional `template_id: str | None`
- `examples/kitchen_nowak.yaml` — re-author using `template_id` references where applicable
- `docs/GLOSSARY.md` — promote / add 7 entries
- `docs/01_architecture.md` — Context Map shows `TemplateRegistry` in Core

### Deleted or stubbed
- None. F003 doesn't supersede legacy code paths (F002 already quarantined `catalog.py::decompose_*`).

---

## LLM Hints

> Direct instructions for future LLM sessions in this decision area.

- **When asked "where do cabinet templates live?"** → `src/kuchnie_core/templates/<category>/*.yaml`. Data in Core. Registry in Core (singleton). Engine for instantiation in Core.
- **When asked "should we put templates in `catalog/`?"** → **No.** Catalog is vendor decor/edge data. Templates are domain cabinet types. Different bounded context. See Alternative E.
- **When asked "can templates be Python classes / dataclasses / modules?"** → No. YAML data. Same rationale as recipes (F002). See Alternatives B and C.
- **When asked "should we flatten the templates folder?"** → No. Category subfolders. Templates will grow; subfolders match the `CabinetCategory` enum. See Alternative F.
- **When asked "can we auto-generate template variants by looping over widths?"** → No. Explicit YAMLs are searchable, diffable, and lintable. See Alternative G.
- **When asked "should templates and recipes be merged?"** → **No.** They are intentionally separate. One recipe backs many templates. See Alternative H.
- **When asked "should we replace all sub-assemblies on override?"** → **No.** Merge by `kind` so a user overriding only the shelf count doesn't lose the door. See Alternative K.
- **When asked "can templates inherit / extend other templates?"** → Not in v1.0. Revisit when count > 40. See Alternative O.
- **When asked "where do thumbnails live?"** → `src/kuchnie_core/templates/thumbnails/<template_id>.png`. Co-located with templates. F006 may copy to its static dir.
- **When asked "are these real thumbnails?"** → No, placeholders. Real thumbnails come from a batch render job after F007 lands. Not in F003 scope.
- **When asked "should constraints be inside `default_dimensions`?"** → No. Separate `dimension_constraints` field. Value vs rule = two concepts = two fields. See Alternative J.
- **When asked "should `instantiate()` defer validation to Gate 1?"** → No. Validate overrides at instantiation. Gate 1 (F004) checks whole-cabinet consistency; instantiation rejects obvious violations early. See spec Open Q4.
- **When asked "what about the plugin's bay_presets.py?"** → Leave it alone. The plugin keeps its own preset system for its own UI (which we don't use). Our `TemplateRegistry` is independent. Rule 4 stands.
- **When asked "should we add a template for X" where X is `worktop_segment`, `island_unit`, `bar_corner`, etc.?"** → Not in v1.0. `CabinetCategory` is `BASE | WALL | TALL | CORNER`. Anything else is backlog.
- **When asked "should template labels be multi-language now?"** → No. Polish only. `_pl` suffix on field names makes future expansion mechanical. See Alternative N.
- **When asked "should we cache instantiated cabinets?"** → No. Instantiation is cheap (Pydantic construction + dict merge). Caching would risk staleness on template reload.
- **Do not propose:**
  - Replacing YAML with TOML / JSON / INI.
  - Loading templates from an HTTP endpoint.
  - Adding async loading to `TemplateRegistry` (sync singleton is correct).
  - Adding a template authoring GUI in v1.0.
  - Generating templates dynamically from cabinet usage statistics.
  - Embedding actual material data (decor color hex) in templates instead of role strings.
- **Related ADRs:**
  - **F001 (Construction Method)** — instantiation resolves `construction_method_id` via template-override → project-default chain.
  - **F002 (Recipe Engine)** — every template's `recipe_id` must resolve in the recipe registry. The integration test enforces this.
  - **F004 (Validation Gates)** — Gate 1 (Cabinet) reads template constraints to validate field consistency beyond simple dim ranges (e.g., sub-assembly fit).
  - **F005 (Material Resolver)** — `material_role_defaults` strings (`project_body`, `project_front`) get resolved by F005's `MaterialResolver` against project-level decor IDs.
  - **F006 (Web Sidebar)** — consumes `TemplateRegistry.list_by_category()` to populate the sidebar; calls `instantiate()` on drop.
  - **F008 (CLI)** — `kitchen-cli add-cabinet --template <id>` calls `instantiate()`.

---

## Sign-off

- [ ] `docs/GLOSSARY.md` updated with 7 terms.
- [ ] 12 worked template YAMLs committed in category subfolders.
- [ ] 12 placeholder thumbnail PNGs committed.
- [ ] `CabinetInstance.template_id` field added.
- [ ] Tests in place: `tests/core/test_template_registry.py`, `tests/integration/test_template_to_panels.py`.
- [ ] `examples/kitchen_nowak.yaml` reauthored to use `template_id` references.
- [ ] Status moved from `Proposed` → `Accepted` after first green test run (specifically the integration test, since it proves the template→recipe→panel pipeline works end to end).
