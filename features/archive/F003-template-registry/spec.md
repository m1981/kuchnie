# F003 — Template Registry (Cabinet Macros)

## Job Story

**When** I am configuring a kitchen for a Wrocław customer — either in the web sidebar (F006) or via CLI — and I need to drop a typical cabinet (szafka dolna 60 cm jednodrzwiowa, słupek na piekarnik, narożna diagonalna) into a row,
**I want to** browse a curated menu of `CabinetTemplate`s organized by category (base / wall / tall / corner), each with sensible default dimensions, default sub-assemblies, dimension constraints, and a recipe reference,
**So I can** instantiate a complete `CabinetInstance` with one call (`registry.instantiate("base_door_60", overrides={"width_mm": 800})`) instead of hand-assembling cabinets from raw dimensions, and so the set of cabinet types I offer to customers is consistent, tested, and tweakable by editing YAML.

---

## Bounded Context

- **Primary (the one that OWNS this):** `Core` (`src/kuchnie_core/`)
- **Touched (consumers, must have explicit reason):**
  - **None in F003.** Future consumers (F006 web sidebar, F008 CLI cabinet adder) are downstream and not touched by this feature.
  - F003 ships pure data + service in Core. F006 will import the registry and surface it in Reflex.

> **Change Locality Test result:** single bounded context. Templates are data, registry is a Core service. ✅ Passes cleanly.

---

## Subdomain Classification

- [x] **Core** — competitive advantage. A curated, Polish-market template library (with mm-correct widths, Blum-compatible drawer counts, Wrocław-typical corner sizes) is what makes the system usable by a carpenter on the first visit. PRO100 ships with American widths and generic categories; we ship with what Polish customers actually buy.
- [ ] Supporting
- [ ] Generic

**Reasoning:** Templates encode market knowledge. The set of cabinet types a Polish carpenter offers (and what counts as "standard") differs from American (face-frame) or German (rigid-modular) markets. Owning the template catalog as data lets us refine the offering quickly without code changes.

---

## Data Ownership

- **Canonical writes happen in:**
  - Template definitions: `src/kuchnie_core/templates/<category>/*.yaml` (hand-edited, organized by category subfolder).
  - Template model: `src/kuchnie_core/templates.py::CabinetTemplate` (Pydantic, immutable at load).
- **Read-only consumers:**
  - `kitchen-app` (F006) — Reflex sidebar imports the registry, displays by category with thumbnails.
  - `kitchen-cad` CLI (F008) — `kitchen-cli add-cabinet --template base_door_60 --row 1` will use the registry.
  - `kuchnie_core/bom.py` — when a `CabinetInstance` is decomposed, BOM joins template metadata for richer reporting (Should-have, not Must).
- **Storage format:** YAML, organized by category subfolder. Thumbnails as PNG in `src/kuchnie_core/templates/thumbnails/<template_id>.png`.

---

## Scope — MoSCoW

### Must (do not ship without)

#### Template data model (Core)
- [ ] `src/kuchnie_core/templates.py` with Pydantic models:
  - [ ] `CabinetTemplate` — top-level template definition (immutable, `frozen=True`).
  - [ ] `DimensionConstraints` — per-dimension min/max bounds.
  - [ ] `DefaultSubAssembly` — declarative sub-assembly defaults (kind + count + per-kind params).
  - [ ] `MaterialRoleDefaults` — mapping of role string → project-level material slot.
  - [ ] `CabinetCategory` enum: `BASE`, `WALL`, `TALL`, `CORNER` (extensible — `ISLAND`, `BAR` are backlog).

#### Registry service (Core)
- [ ] `TemplateRegistry` class with:
  - [ ] `load_from_directory(path: Path)` — walk all category subfolders, load each `*.yaml`.
  - [ ] `get(template_id: str) -> CabinetTemplate` — raises `KeyError` if missing.
  - [ ] `list_all() -> list[CabinetTemplate]`.
  - [ ] `list_by_category(category: CabinetCategory) -> list[CabinetTemplate]`.
  - [ ] `list_by_tag(tag: str) -> list[CabinetTemplate]` — for search.
  - [ ] `instantiate(template_id: str, overrides: dict, project_default_construction_method_id: str) -> CabinetInstance`.
  - [ ] `reload()` — clear and re-load.
- [ ] Module-level singleton: `default_registry = TemplateRegistry()`.

#### Instantiation logic
- [ ] `TemplateRegistry.instantiate()` produces a fully populated `CabinetInstance`:
  - [ ] Auto-generate `id` (UUID4 string or short slug — implementation choice, document in tasks).
  - [ ] Copy `recipe_id` from template.
  - [ ] Resolve `construction_method_id`: template override → project default (F001 behavior).
  - [ ] Apply dimensions: defaults overridden by user input, validated against constraints.
  - [ ] Build `sub_assemblies` from `default_sub_assemblies` with override merging.
  - [ ] Build `material_refs` from template's `material_role_defaults`.
- [ ] **Reject** out-of-range overrides with a clear `TemplateInstantiationError` naming the field and the violated constraint.

#### 10–15 worked templates (per Phase 3 gate in `docs/PHASES.md`)

Polish-market mix. IDs in English (universal), labels in Polish (UI-facing).

**Base (szafki dolne):**
- [ ] `base_door_30.yaml` — 1 drzwi, 30 cm
- [ ] `base_door_40.yaml` — 1 drzwi, 40 cm
- [ ] `base_door_60.yaml` — 1 drzwi, 60 cm (most common width)
- [ ] `base_door_80.yaml` — 1 drzwi, 80 cm
- [ ] `base_drawer_3_60.yaml` — 3 szuflady, 60 cm (Blum Tandembox M)

**Wall (szafki górne):**
- [ ] `wall_door_30.yaml` — 1 drzwi, 30 cm, wys. 720
- [ ] `wall_door_60.yaml` — 1 drzwi, 60 cm, wys. 720
- [ ] `wall_door_80.yaml` — 1 drzwi, 80 cm, wys. 720

**Tall (słupki):**
- [ ] `tall_pantry_60.yaml` — słupek spiżarniany, 60 cm, wys. 2000
- [ ] `tall_oven_60.yaml` — słupek pod piekarnik, 60 cm, wys. 2000

**Corner (narożne):**
- [ ] `corner_diagonal_90.yaml` — narożna diagonalna, 90×90 cm
- [ ] `corner_blind_left_100.yaml` — narożna ślepa lewa, 100 cm

**Total: 12 templates.** All reference the 5 recipes from F002 (variants share recipes — e.g., `base_door_30`, `base_door_40`, `base_door_60`, `base_door_80` all use `base_door_single` recipe).

#### Thumbnails

- [ ] Placeholder PNG (single solid color or simple line art) for each of the 12 templates: `src/kuchnie_core/templates/thumbnails/<template_id>.png`.
- [ ] Real renders deferred to backlog (will come from F007 batch render once that exists).
- [ ] Templates reference thumbnails by **relative path** from the templates directory, so the registry can resolve absolute paths.

#### Tests

- [ ] `tests/core/test_template_registry.py`:
  - [ ] `test_load_registry_from_directory()` — loads all 12, no errors.
  - [ ] `test_get_template_by_id()` — success + KeyError on missing.
  - [ ] `test_list_by_category()` — base returns base templates only.
  - [ ] `test_list_by_tag()` — `single_door` returns expected subset.
  - [ ] `test_instantiate_with_defaults()` — `base_door_60` → `CabinetInstance` with 600/720/560.
  - [ ] `test_instantiate_with_overrides()` — `base_door_60` with `{width_mm: 800}` → 800mm width preserved.
  - [ ] `test_instantiate_rejects_out_of_range()` — `base_door_60` with `{width_mm: 1500}` raises `TemplateInstantiationError` mentioning `width_mm` and `max=1200`.
  - [ ] `test_instantiate_inherits_project_construction_method()` — template has no method override → cabinet uses project default.
  - [ ] `test_instantiate_resolves_recipe_id()` — `base_door_60` instance has `recipe_id == "base_door_single"`.
- [ ] **Integration test against F002:** `test_instantiate_then_decompose.py` — instantiate a template, run through F002 `RecipeEngine`, get a valid panel list. Catches cross-feature regressions early.

### Should (do if time permits)

- [ ] `kitchen-cli list-templates [--category base]` — print available templates.
- [ ] `kitchen-cli show-template <template_id>` — print full YAML.
- [ ] Template linter: validates that every template's `recipe_id` resolves in the recipe registry (cross-feature consistency).
- [ ] `material_role_defaults` validation: warn if a role string isn't recognized (`body`, `front`, `back`, `shelf` are canonical for v1.0).

### Could (almost certainly defer)

- [ ] Template inheritance (`extends: base_door_60`) — premature; ~12 templates with mild duplication is fine.
- [ ] Template variants generated programmatically (e.g., generate base_door_W for W in [30,40,50,60,80]). Backlog — explicit YAMLs are searchable and diffable.
- [ ] Per-region template packs (e.g., `templates_de/`, `templates_pl/`). For v1.0, Polish-market only.
- [ ] User-defined templates loaded from `~/.kuchnie/templates/` overlay. Deferred to post-v1.0.

### Won't (this iteration — explicit cuts)

- ❌ **Web UI for editing or browsing templates.** F006 is the sidebar; F003 is data + service only.
- ❌ **Template authoring tooling.** YAML is hand-edited. No GUI editor in v1.0.
- ❌ **Generating templates from existing cabinets** ("save this cabinet as a template"). Backlog — interesting but adds complexity now.
- ❌ **Sub-assembly auto-derivation from recipe.** Templates declare sub-assemblies explicitly. The recipe defines panels; the template defines what user-facing components (doors, drawers, shelves) those panels assemble into.
- ❌ **Validation of sub-assembly counts against recipe panel emissions.** F004's Gate 1 (Cabinet validation) handles this. F003 trusts the template author.
- ❌ **Per-cabinet construction method overrides via templates.** v1.0 templates may declare a method override, but `CabinetInstance.construction_method_id` still respects F001's "project-level default, per-cabinet field exists but rarely populated" decision.
- ❌ **Thumbnails as real renders.** Placeholder PNGs only. Real renders deferred to a batch job after F007 lands.
- ❌ **Reading templates from `catalog/`.** Catalog is for materials, not cabinet types. Different bounded context.
- ❌ **Multi-language label support.** v1.0 has Polish labels hardcoded. Backlog: `labels: {pl: "Szafka dolna", en: "Base cabinet"}`.

---

## Change Locality Test

- [x] Editing **one bounded context** (Core). Web/CAD/Render are future consumers; F003 itself touches none of them.
- [x] **One published contract change**: `CabinetTemplate` Pydantic model becomes part of Core's published surface. `kitchen_config.yaml` schema is **unchanged** (templates are referenced by ID at instantiation, but instantiated `CabinetInstance`s look identical to F001's model in the serialized kitchen).
- [x] **Passes.**

---

## Glossary Impact

**New terms** (must be added to `docs/GLOSSARY.md` in the implementation commit):

- `CabinetTemplate` — already a placeholder; F003 makes it concrete with file-of-record `src/kuchnie_core/templates.py::CabinetTemplate`.
- `TemplateRegistry` — service that loads/queries templates by ID.
- `CabinetCategory` — enum: `BASE`, `WALL`, `TALL`, `CORNER`.
- `DimensionConstraints` — per-dimension min/max.
- `DefaultSubAssembly` — declarative sub-assembly default in a template.
- `MaterialRoleDefaults` — role string → project material slot mapping in a template.
- `TemplateInstantiationError` — raised when overrides violate constraints.

**Existing terms refined:**

- `CabinetInstance` — gains `template_id: str` (optional, for traceability). Allows BOM and elevation views to link back to the template that produced the cabinet.
- `SubAssembly` — F003 introduces the **declarative form** (`DefaultSubAssembly`) used in templates. The runtime form (`SubAssembly` on `CabinetInstance`) is the F001 concept and is built from defaults at instantiation.

---

## Acceptance Criteria

The feature is **done** when:

- [ ] `src/kuchnie_core/templates.py` exists with all Pydantic models.
- [ ] `src/kuchnie_core/templates/` directory contains the 12 worked templates organized by category subfolder.
- [ ] `src/kuchnie_core/templates/thumbnails/` contains 12 placeholder PNGs.
- [ ] `CabinetInstance` updated with optional `template_id: str | None` field.
- [ ] `TemplateRegistry` module singleton loads on first use.
- [ ] All listed tests in `tests/core/test_template_registry.py` pass.
- [ ] Integration test `tests/integration/test_template_to_panels.py` passes — instantiation + F002 decomposition produces non-empty, validly-dimensioned panel list for at least 3 templates (one base, one wall, one tall).
- [ ] `docs/GLOSSARY.md` updated with 7 new/refined terms.
- [ ] `docs/01_architecture.md` Context Map updated to show `TemplateRegistry` in Core.
- [ ] ADR `features/F003-template-registry/adr.md` status = `Accepted`.
- [ ] `examples/kitchen_nowak.yaml` updated to use `template_id` references where applicable (cabinets get instantiated from templates, then customized).
- [ ] `status.md` set to `done`.
- [ ] `features/INDEX.md` updated.
- [ ] Phase 3 gate criteria in `docs/PHASES.md` ticked.

---

## Out of Scope (anti-drift)

- ❌ **Plugin extension.** The plugin doesn't see templates. The render adapter (F007) consumes already-instantiated `CabinetInstance`s.
- ❌ **Reflex UI (sidebar, browse).** F006's job. F003 ships data + service.
- ❌ **Real cabinet thumbnails.** Placeholders only. A backlog item generates real ones from F007 once that exists.
- ❌ **Per-customer or per-project template overlays.** v1.0 has one global template library.
- ❌ **Template editing via API.** Templates are git-tracked YAML, edited in an editor.
- ❌ **Auto-suggestion / recommendation engine.** ("You added a sink base, want a dishwasher beside it?") Way out of scope.
- ❌ **Migration tooling** for legacy hardcoded cabinets in `kuchnie_core/catalog.py`. F002 quarantined the legacy decomposers; F003 sidesteps them entirely by going through the new path.
- ❌ **Reconciliation with the Blender plugin's bay_presets.py.** The plugin keeps its bay presets for its own use; our templates are independent. The render adapter (F007) translates our `CabinetInstance` into plugin scene language without going through bay presets.
- ❌ **Worktop templates / island templates / bar templates.** v1.0 = base / wall / tall / corner only.
- ❌ **Adding templates for cabinet types whose recipes don't exist yet.** Templates always reference an existing recipe. Adding a new cabinet type means: write recipe (F002 path), then write template (F003 path), then ship.

---

## References

- **Pattern source:** `docs/02_pattern_analysis.md` § Pattern 1 (Cabinet Macros, from PRO100)
- **Placement decision:** `docs/03_implementation_placement.md` § Pattern 4 — Cabinet Macros (Core data + Web UI consumer)
- **Process rules:** `docs/04_solo_dev_process.md`
- **Related ADRs:**
  - `features/F001-construction-method/adr.md` — `construction_method_id` resolution rule (template override → project default).
  - `features/F002-recipe-engine/adr.md` — templates carry `recipe_id`s that resolve through the recipe engine.
  - `features/F003-template-registry/adr.md` — this feature's ADR.
- **Related features:**
  - **Depends on:**
    - F001 (templates may reference construction methods; instantiation honours project default).
    - F002 (every template must reference an existing `recipe_id`).
  - **Enables:**
    - F004 (Gate 1 / Cabinet validates dimensions against template constraints).
    - F006 (Web sidebar browses templates by category, instantiates on drop).
    - F008 (`kitchen-cli add-cabinet --template`).
  - **Conflicts with:**
    - `kitchen-plugin/src/product_libraries/frameless/bay_presets.py` and similar plugin-internal preset systems — they are inside the plugin (untouched, per Rule 4). Our templates are the truth from Core's perspective.
    - `kuchnie_core/catalog.py::TYPE_REGISTRY` — F002 quarantined the legacy decomposers; F003 simply doesn't use them. Full removal is backlog.

---

## Template YAML — Worked Example (for spec clarity)

This is what a template looks like. Belongs in `src/kuchnie_core/templates/base/base_door_60.yaml`. Not implementation — illustration so reviewers see the shape:

```yaml
template_id: base_door_60
label_pl: "Szafka dolna 60 cm, drzwi prawe"
description_pl: "Standardowa szafka dolna z jednymi drzwiami otwieranymi w prawo i jedną półką."
category: BASE
recipe_id: base_door_single

# Optional construction method override.
# null (or omit) = inherit from project's default_construction_method_id.
construction_method_id: null

default_dimensions:
  width_mm: 600
  height_mm: 720
  depth_mm: 560

dimension_constraints:
  width_mm: { min: 300, max: 1200 }
  height_mm: { min: 250, max: 1000 }
  depth_mm: { min: 300, max: 700 }

default_sub_assemblies:
  - kind: door
    count: 1
    swing: right          # right | left | double
  - kind: shelf_bank
    shelf_count: 1
    adjustable: true

material_role_defaults:
  body: project_body       # role → project material slot
  front: project_front
  back: project_back
  shelf: project_body

thumbnail: "thumbnails/base_door_60.png"

tags:
  - base
  - single_door
  - standard
  - "600"
```

> **Instantiation example** (Python, illustrative):
>
> ```python
> from kuchnie_core.templates import default_registry
>
> cabinet = default_registry.instantiate(
>     template_id="base_door_60",
>     overrides={
>         "width_mm": 800,
>         "sub_assemblies": [
>             {"kind": "shelf_bank", "shelf_count": 2},
>         ],
>     },
>     project_default_construction_method_id="dowel_camlock_18",
> )
> # cabinet.id = "cab_a3f2"  (auto-generated)
> # cabinet.template_id = "base_door_60"
> # cabinet.recipe_id = "base_door_single"
> # cabinet.construction_method_id = "dowel_camlock_18"
> # cabinet.width_mm = 800   (overridden, within [300, 1200])
> # cabinet.sub_assemblies[1].shelf_count = 2   (override merged)
> # cabinet.material_refs = {body: "project_body", front: ..., ...}
> ```

> **Override semantics:**
> - Scalar overrides (`width_mm: 800`) replace defaults.
> - List overrides (`sub_assemblies: [...]`) merge by `kind` — same-kind items in the override patch the defaults; unspecified kinds remain from defaults. This is intentional: don't accidentally lose the default door when overriding only the shelf.
> - Material overrides (`material_refs: {...}`) replace per-role; unspecified roles remain from defaults.

---

## Open Questions

> All must be answered before coding begins.

- [x] **Q1:** Flat templates folder or category subfolders? → **A:** Subfolders by category (`templates/base/`, `templates/wall/`, …). Templates will grow to 30–50 over time; subfolders aid navigation. (Recipes stay flat — fewer of them, one per cabinet type.)
- [x] **Q2:** Where do thumbnails live? → **A:** `src/kuchnie_core/templates/thumbnails/<template_id>.png`. Co-located with templates so they ship together. F006 may copy them into the web app's static dir at build time.
- [x] **Q3:** Templates in Polish or English? → **A:** **IDs in English** (universal, code-friendly). **Labels and descriptions in Polish** via `label_pl` / `description_pl` fields. Multi-language is post-v1.0; for now Polish only. (Field name suffix `_pl` makes future expansion mechanical.)
- [x] **Q4:** Should `instantiate()` validate overrides immediately or defer to Gate 1? → **A:** **Immediately.** Out-of-range overrides raise `TemplateInstantiationError` at instantiation time. Gate 1 (F004) is for whole-cabinet consistency (sub-assemblies fit, recipe outputs make sense); instantiation rejects the obvious violations early.
- [x] **Q5:** How are sub-assembly overrides merged? → **A:** Merge by `kind` — list items with the same `kind` value are patched together, others remain from defaults. Replacing all sub-assemblies entirely is possible via `sub_assemblies_replace: true` flag (rare; documented but not needed in v1.0 tests).
- [x] **Q6:** What ID format for instantiated cabinets? → **A:** Short slug `cab_<6 hex chars>` (e.g., `cab_a3f2c1`). UUIDs are too long for human review of kitchen YAMLs. Implementation detail; capture in `tasks.md`.
- [x] **Q7:** Do we support tag-based template search now or defer? → **A:** Implement `list_by_tag()` now (small cost, ~5 LOC). F006 may or may not surface it — that's F006's UX choice.
- [x] **Q8:** Should templates declare `material_role_defaults` if every cabinet ends up with the same 4 roles? → **A:** Yes, for **flexibility**. A glass-door wall cabinet might want `material_role_defaults: {body: project_body, front: glass, back: project_back}`. Explicit beats implicit, even at the cost of one extra section per YAML.
- [x] **Q9:** Where does the recipe-template consistency check live? → **A:** Template linter (Should-have). Not Must — we trust YAML authors in v1.0 and rely on the integration test to catch mismatches.
- [x] **Q10:** Naming convention — `base_door_60` or `base-door-60` or `base.door.60`? → **A:** Snake_case (`base_door_60`). Matches Python identifier rules in case we want to import-by-attribute later; matches recipe ID style.

**All Open Questions resolved.** Spec is **ready** for implementation.
