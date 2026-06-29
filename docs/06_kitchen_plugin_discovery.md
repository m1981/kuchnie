# Kitchen-Plugin Discovery — Major Planning Course-Correction

> **TL;DR:** `kuchnie/kitchen-plugin/` is **not** a legacy Blender addon. It is **our most mature working subsystem** — a clean DDD-layered Python project (4,523 LOC, 23 test files, recent active development) that already implements large fractions of what we planned to build in F001, F002, F004, F007, and partly F008.
>
> **The previous planning treated it as something to deprecate. That framing was wrong. It should be the foundation.**
>
> This document explains what kitchen-plugin actually is, what it overlaps with, why I missed this during cold review, and three options for how to proceed — with a recommendation.

---

## What kitchen-plugin/ Actually Is

`kuchnie/kitchen-plugin/` is a **standalone Python project** named `kitchen-generator` (per `pyproject.toml`) that:

- Has its own clean **5-layer DDD architecture** (core → kitchen → builder → adapters → main)
- Owns a coherent **domain model**: `Wall`, `Room`, `Cabinet`, `CabinetPlacement`, `Run`, `Layout`, `LayoutEngine`, `KitchenStandards`
- Takes **versioned JSON config** (`schemas/v1.0`, `v1.1`) describing runs of cabinets along walls
- Runs **Blender headless via subprocess**: `blender --background --python src/main.py -- configs/foo.json`
- Produces **two outputs**:
  - **Manifest JSON** (primary) — measurements + validation, no bpy needed to read
  - `.blend` file (optional) — for visual inspection
- Has its own **validation pipeline** (dimensions, overlaps, clearance ≥ 900mm, standard widths, drawer counts, room sanity)
- Has its own **construction math** (`cabinet_geometry.py`: corpus 18mm, front 19mm, back 3mm, groove offsets, overlays)
- **23 test files** covering I/L/U-shape kitchens, tolerances, gap semantics, manifest schema, drawer validation, coordinate system, room validation, wall builder, cabinet construction
- **Recent CHANGELOG entries** show active DDD refactoring (this is in-progress work, not legacy)

### What it imports / depends on

- Pure Python + dataclasses only in `core/` and `kitchen/`
- `bpy` only in 5 files: `geometry_builder.py`, `material_manager.py`, `exporters.py`, `geometry_manifest.py`, `main.py` (adapters layer)
- Zero dependencies on `kuchnie_core/` (the other Python tree under `src/`)
- Zero dependencies on `home_builder_5/`

### How kuchnie_core sees it

`kuchnie/src/kuchnie_core/serialize.py` line 3 says:

> "This is THE contract between **kitchen-plugin**, render-service, and kitchen-cli."

So `kuchnie_core` was designed to **produce JSON that feeds kitchen-plugin**. Kitchen-plugin is the rendering/geometry backend; `kuchnie_core` is/was meant to be the higher-level domain layer that calls it.

---

## What This Overlaps With In Our Plans

| Our Feature | What we planned to build | What kitchen-plugin already has | Overlap severity |
|---|---|---|---|
| **F001 — ConstructionMethod** | `ConstructionMethod` dataclass with `corpus_thickness_mm`, `front_thickness_mm`, `back_thickness_mm`, `groove_*`, `overlay_*` | `cabinet_geometry.py` with `DEFAULT_CORPUS_THICKNESS=18`, `DEFAULT_FRONT_THICKNESS=19`, `DEFAULT_BACK_THICKNESS=3`, `DEFAULT_GROOVE_DEPTH=9`, `DEFAULT_GROOVE_WIDTH=3.2`, `DEFAULT_GROOVE_OFFSET=10`, `DEFAULT_OVERLAY_SIDE/TOP/BOTTOM=2`. Plus a `CabinetGeometry` class that uses them. | **Near-identical concept; different name and home.** |
| **F002 — Recipe Engine** | YAML recipes decompose `CabinetInstance` → list of `Panel` | `cabinet_geometry.py` computes internal cavity & 4-board carcass; `geometry_builder.py` builds them in bpy. No YAML — formulas are Python. | **Same job, hardcoded Python implementation.** YAML extraction is the new work. |
| **F003 — Template Registry** | YAML-defined cabinet templates with constraints + sub-assemblies | Cabinet `type` strings in JSON config: `base-door`, `base-drawer-door`, `base-drawers`, `base-sink`, `corner-blind`, `tall-oven`, `wall-cabinet`, `filler`, etc. **Implicitly templated** by type. | **Concept exists informally.** Need to formalize into YAML registry. |
| **F004 — Validation Gates** | 4 gates (Cabinet/Row/Kitchen/CAM) with collect-all-issues, codes (DIM-001 etc.) | `manifest_validator.py` with `DEFAULT_DIMENSION_TOLERANCE_MM`, overlap detection, `MIN_WALKWAY_CLEARANCE_MM=900`, `STANDARD_WIDTHS_MM`, drawer validation. 23 tests including `test_p2_room_validation.py`, `test_p1_drawer_validation.py`, `test_manifest_validation.py`. | **Already implemented for 2 of 4 gates** (Cabinet + Kitchen). |
| **F005 — Material Resolver** | Role → slot → decor chain, `ResolvedMaterial`, paired edges | `material_manager.py` (bpy Cycles materials only — colors, no Kronospan/Egger catalog). JSON config has `materials` block with color floats only. | **Almost no overlap.** kitchen-plugin only handles render-time material colors, not the Polish material catalog or CNC data. F005 is genuinely new. |
| **F006 — Web Sidebar** | Reflex UI | None | **No overlap.** |
| **F007 — Blender Adapter** | NEW `kitchen-render/` standalone bpy renderer (our F007 ADR) | **kitchen-plugin IS exactly this.** Same architecture (standalone Python + bpy via subprocess), same approach (manifest JSON as primary output), same pattern (config → build → validate → optional render). | 🔴 **F007 was planning to build what already exists.** |
| **F008 — CLI Export** | `kitchen-cli` binary with `cut-list`, `drill-pattern`, `dxf`, `bom`, `cost-estimate`, `render` | `main.py` with `--validate`, `--export-blend`, `--render-wireframe`, `--no-materials`. No CSV/DXF/BOM/cost. | **CLI shell exists; CSV/DXF exporters are new work.** |

---

## Why I Missed This

Several reasons compounded:

1. **The name.** "kitchen-plugin" sounds like another Blender addon — making me think it was a sibling of `home_builder_5/`. The user said "the plugin is `home_builder_5/`" early on and I anchored on that.

2. **The previous planning treated it as legacy.** Both the F001 ADR (line 12: "the plugin's `config_parser.py` DEFAULTS dict") and F004 ADR (line 14: "the existing `kitchen-plugin/src/config_parser.py` validators are similar — plugin-local, not reusable") referenced kitchen-plugin/ as **something to be superseded**. The phrasing came from earlier sessions and I propagated it without auditing.

3. **The legacy ADRs in `kuchnie/docs/adr/` describe an aspirational future**, not the current state. They talk about "panel-is-atomic-unit" (ADR 001), "construction-method-separation" (ADR 002), etc. — as if those were not-yet-built designs. But kitchen-plugin already has board-level construction (4-board carcass) and construction-method separation (`cabinet_geometry.py` parameters). The ADRs were the plan; kitchen-plugin is the partial execution.

4. **I never opened kitchen-plugin/src/.** Cold review checked `home_builder_5/`, `kuchnie/src/kuchnie_core/`, but didn't recurse into `kitchen-plugin/`. The directory name "plugin" pattern-matched to "external thing we don't touch."

5. **The cold review's Finding #1 ("docs in wrong repo")** was correct but incomplete. It found that `src/kuchnie_core/` is in `kuchnie/`, not `home_builder_5/`. It should have *also* discovered that `kitchen-plugin/src/` exists in `kuchnie/` and represents the most mature subsystem.

**Operational lesson:** before writing any architectural plan, **`find . -name "*.py" | head -100`** in every candidate directory. Name-based pattern-matching is unreliable. The structure on disk is the only ground truth.

---

## What This Means For The Planning

### Hard truth

**At least 5 of the 8 features (F001, F002, F004, F007, partly F008) were planned as if kitchen-plugin/ didn't exist.** Their "Affected files" lists propose creating new files in `src/kuchnie_core/` or new packages (`kitchen-cad/`, `kitchen-render/`) that **duplicate concepts already implemented in kitchen-plugin/**.

If we executed the plans as written, we'd end up with **two parallel implementations** of:
- Construction parameters (`ConstructionMethod` in core ↔ `cabinet_geometry.py` defaults in kitchen-plugin)
- Cabinet decomposition (`RecipeEngine` in CAD ↔ `geometry_builder._build_cabinet()` in kitchen-plugin)
- Validation (4 gates in core/validation ↔ `manifest_validator.py` in kitchen-plugin)
- Bpy invocation (kitchen-render/ in F007 ↔ main.py in kitchen-plugin)

This is **exactly the duplication every architecture skill explicitly forbids**.

### What's actually new work

After accounting for kitchen-plugin/, the genuinely new work is:

1. **Catalog (F005)** — Kronospan/Egger material catalog with paired edges, variants, grain direction. Nothing in kitchen-plugin or kuchnie_core matches this.
2. **Recipe YAMLs (F002 partial)** — extracting kitchen-plugin's hardcoded Python decomposition into editable YAML.
3. **Template YAMLs (F003 partial)** — formalizing kitchen-plugin's implicit `type: base-door` strings into a registry.
4. **CSV/DXF exporters (F008 partial)** — kitchen-plugin produces a JSON manifest, not e-rozkroj CSVs or DXFs.
5. **Web sidebar (F006)** — entirely new.
6. **Cost estimation (F008 partial)** — new.
7. **Material resolution and texture-path wiring (F005 + F007 integration)** — kitchen-plugin handles `bpy` Cycles materials by RGB only; integrating real Kronospan textures is new.

That's perhaps **30-40% of the planned scope** is genuinely new. The other **60-70% is already done** — it just lives under a misleading directory name and isn't integrated with the planned `kuchnie_core` layer.

---

## Three Options

### Option A — **Adopt kitchen-plugin as the foundation** (recommended)

Treat kitchen-plugin as **our render + geometry + construction-validation subsystem**. Don't replace it; integrate with it. Specifically:

1. **Rename** `kitchen-plugin/` → `kitchen-render/` (or keep the name; the directory name doesn't matter, the role does). The F007 ADR's stated "build kitchen-render/ from scratch" is rescinded; F007 ADR is rewritten as "adopt kitchen-plugin/, integrate with kuchnie_core."
2. **Promote** its domain types where they're better than `kuchnie_core/model.py`:
   - `kitchen-plugin/src/kitchen/cabinet.py::Cabinet` is cleaner than `kuchnie_core/model.py::CabinetInstance`. Decide which is the authoritative `Cabinet`/`CabinetInstance`.
   - `kitchen-plugin/src/kitchen/wall.py::Wall, Room` is what F001+F002 implicitly need; `kuchnie_core` has only `Row` (less structured).
   - `kitchen-plugin/src/kitchen/standards.py::KitchenStandards` overlaps with F001's `ConstructionMethod` — merge.
3. **Extract** kitchen-plugin's hardcoded knowledge:
   - `cabinet_geometry.py` constants → F001's YAML `ConstructionMethod` files
   - `geometry_builder._build_cabinet()` per-type branches → F002's YAML recipes
   - `manifest_validator.py` checks → F004's gate registry (with code numbers)
4. **Bridge** kitchen-plugin's JSON config schema with the YAML format `kuchnie_core` is moving toward. One of two paths:
   - Keep both formats; write a `kuchnie_core ↔ kitchen-plugin JSON` translator (an ACL).
   - Migrate kitchen-plugin to consume YAML directly. More work but cleaner.
5. **Restate** the bounded contexts:

| Original (wrong) | Corrected |
|---|---|
| Catalog \| `catalog/` | Catalog \| `catalog/` ✅ unchanged |
| Domain Core \| `src/kuchnie_core/` | Domain Core \| `src/kuchnie_core/` (slimmer — owns workflow, BOM, exports; not geometry) |
| CAD \| `kitchen-cad/` | CAD \| `kitchen-cad/` (CSV/DXF/BOM exporters only) ✅ unchanged |
| Web \| `kitchen-app/` | Web \| `kitchen-app/` ✅ unchanged |
| Render \| **new** `kitchen-render/` (F007) | **Geometry + Render** \| `kitchen-plugin/` (renamed or kept) — owns Cabinet construction, validation, bpy rendering. **Far larger scope than F007 imagined.** |

**Pros:**
- Preserves **4,523 LOC + 23 passing tests** of working code.
- Reduces planned work by ~60-70%.
- Aligns with what the user has actually been building.
- The DDD architecture in kitchen-plugin is **better than the architecture we were planning** (proper 5-layer separation, frozen dataclasses, no bpy in core).

**Cons:**
- Must rewrite F001/F002/F004/F007/F008 specs and ADRs (~2-3 hours).
- Have to decide on the YAML-vs-JSON config split (or unify).
- Have to deduplicate `kuchnie_core/model.py::CabinetInstance` vs `kitchen-plugin/src/kitchen/cabinet.py::Cabinet`.

### Option B — **Black-box kitchen-plugin behind an adapter**

Treat kitchen-plugin as a **completed external subsystem** with a stable JSON contract. `kuchnie_core` builds a `Kitchen`, serializes to kitchen-plugin's JSON, subprocesses `python -m kitchen_plugin.main`. F007 becomes the thin adapter. Our F001/F002/F004 specs are **still wrong** because they define `ConstructionMethod` / `Recipe` / validation in `kuchnie_core` while kitchen-plugin has its own — but maybe that's tolerable if kitchen-plugin's are render-side and ours are CNC-side.

**Pros:**
- Zero changes to kitchen-plugin/.
- Lower immediate disruption.

**Cons:**
- **Two domain models forever.** Two construction-param schemas. Two validators. Every change requires changing both.
- The exact "two parallel formula systems" pattern F007 ADR (line 79) was uncomfortable with — formalized.
- 23 tests in kitchen-plugin protect a model that diverges from kuchnie_core. Bug fixes won't propagate.
- Wastes the better architecture in kitchen-plugin by burying it behind an opaque interface.

### Option C — **Replace kitchen-plugin with new code per F007 ADR**

Execute F007 ADR literally: build `kitchen-render/` from scratch. Migrate kitchen-plugin's 23 tests across. Eventually delete kitchen-plugin.

**Pros:**
- Single clean architecture per the planned design.
- F001–F008 specs apply as written.

**Cons:**
- **Discards 4,523 LOC of working tested code** for purity.
- Weeks of work to recreate construction math, validation, geometry builder.
- The "single clean architecture" is **probably worse** than what kitchen-plugin already has — F007 ADR didn't propose a 5-layer DDD split.
- High regression risk: the rebuilt validator must catch every case the 23 existing tests cover.
- The solo-dev process doc (`04_solo_dev_process.md`) explicitly warns against this kind of rewrite.

---

## Recommendation

**Option A — adopt kitchen-plugin as the foundation.**

It's the only option consistent with the architectural rules we already wrote (avoid duplication, change locality, single source of truth) **and** with the work the user has already done.

### What Option A means concretely

#### Immediate (before any new code)

1. **Pause** F001 implementation. The "Affected files" list creates `src/kuchnie_core/construction.py`, but kitchen-plugin/src/kitchen/cabinet_geometry.py + standards.py already have the data. We need to decide where the canonical `ConstructionMethod` lives before writing it.

2. **Add a navigation entry** to `00_LLM_NAVIGATION.md`:
   - Six bounded contexts, not five. `kitchen-plugin/` is the sixth (or replaces "Render adapter").
   - Document what it owns: Cabinet, Wall, Room, Layout, CabinetGeometry, KitchenStandards, Manifest, ManifestValidator.
   - Add Rule 8: "Before proposing any geometry, construction, or validation code, check kitchen-plugin/ first."

3. **Update GLOSSARY.md** — every term we defined needs a "Compare with kitchen-plugin" line:
   - `ConstructionMethod` → "Compare with `kitchen-plugin/src/kitchen/cabinet_geometry.py::CabinetGeometry` and `kitchen-plugin/src/kitchen/standards.py::KitchenStandards`. Resolution TBD."
   - `CabinetInstance` → "Compare with `kitchen-plugin/src/kitchen/cabinet.py::Cabinet`. Resolution TBD."
   - `Row` → "kitchen-plugin uses `Run` (`kitchen/layout.py`). Resolution TBD."
   - `RecipeEngine` → "kitchen-plugin implements decomposition imperatively in `geometry_builder._build_cabinet()`. YAML extraction is F002's new work."
   - `Validation Gates` → "kitchen-plugin's `manifest_validator.py` covers Cabinet + Kitchen gates today. Row + CAM gates are new."

4. **Decide** the canonical-name battles (need user input):
   - `Cabinet` (kitchen-plugin) vs `CabinetInstance` (kuchnie_core)?
   - `Run` (kitchen-plugin) vs `Row` (kuchnie_core)?
   - `KitchenStandards` (kitchen-plugin) vs `ConstructionMethod` (planned)?
   - JSON config (kitchen-plugin) vs YAML config (planned)?
   - All these are user-facing concept choices, not just code choices.

#### Spec rewrites (Phase: F001 close-out blocking)

5. **F001 ADR + spec rewrite:** ConstructionMethod still exists as a concept, but its **file of record** is `kitchen-plugin/src/kitchen/standards.py` (extended) or a new shared module. The bullet "translate ConstructionMethod to corpusThickness scene settings" was already known to be stale; now it's worse — kitchen-plugin already *consumes* those values directly from `cabinet_geometry.py` defaults. The new F001 work is: **extract hardcoded defaults to a YAML or Python registry of named methods (`dowel_camlock_18`, `groove_dado_18`, etc.) and let kitchen-plugin select among them.**

6. **F002 ADR + spec rewrite:** RecipeEngine still exists as a concept, but the implementation strategy is **"extract `kitchen-plugin/src/geometry_builder._build_cabinet()` per-type code paths into YAML recipes + an asteval engine"** — not "build a new RecipeEngine from scratch." The 4-board carcass logic already exists; YAML-ifying it preserves behavior.

7. **F004 ADR + spec rewrite:** Validation gates exist, partially, in `manifest_validator.py`. F004 work becomes:
   - Promote `manifest_validator.py` to the gate registry pattern (codes DIM-001 etc.).
   - Add the Row gate (kitchen-plugin doesn't have this).
   - Add the CAM gate (kitchen-plugin only validates render-readiness).
   - Reserve KIT-100 / CAM-100 for F005.

8. **F007 ADR rewrite:** "Build kitchen-render/ standalone bpy renderer" → "Adopt kitchen-plugin as the render + geometry subsystem. Bridge to kuchnie_core via {decision}." This is a fundamental ADR change — write a new ADR (F007-v2 or F009 "Kitchen-Plugin Adoption") rather than editing the old one. The old F007 ADR's rejected alternatives still apply (don't pip-install bpy, don't drive home_builder_5/, etc.) — just the chosen option changes.

9. **F008 ADR + spec rewrite:** `kitchen-cli` subcommands `cut-list`, `drill-pattern`, `dxf`, `bom`, `cost-estimate` are still new work. `render` becomes a wrapper around `python -m kitchen_plugin.main` (or direct import; depends on packaging decision).

#### Documentation cleanup

10. **GLOSSARY.md** — see step 3 above.
11. **PHASES.md** — Phase 7 description needs total rewrite (no more "build new kitchen-render/"; it's now an integration phase).
12. **01_architecture.md** + **03_implementation_placement.md** — need a kitchen-plugin section.
13. **04_solo_dev_process.md** — add the "find . -name '*.py' before planning" lesson.
14. **legacy ADRs in `kuchnie/docs/adr/001-008`** — audit: which are "design done by kitchen-plugin already", which are still open?

---

## Open Questions (need user decision)

Before I rewrite any specs, you need to answer these:

1. **Is kitchen-plugin/ actively maintained?** Or was it set aside when you started planning F001–F008? (CHANGELOG looks active; recency of edits suggests yes.)

2. **Did the original ADRs in `kuchnie/docs/adr/` predate or follow kitchen-plugin?** If the ADRs describe kitchen-plugin's design (post-hoc documentation), they're history. If they describe a future replacement, that intent is now what's wrong.

3. **What was the intended relationship between `kuchnie_core/` and `kitchen-plugin/`?** Both contain a `Kitchen` concept. `serialize.py` line 3 says kitchen-plugin is *downstream* of kuchnie_core. Was kuchnie_core meant to replace kitchen-plugin, or wrap it?

4. **Canonical names** — which "wins" for each pair? (Cabinet/CabinetInstance, Run/Row, KitchenStandards/ConstructionMethod, JSON/YAML config.)

5. **Is `home_builder_5/` still in scope at all?** kitchen-plugin already replaces the rendering job home_builder_5/ would have done. If kitchen-plugin is the renderer, we can demote home_builder_5/ to "reference for research; not used at runtime." Rule 4 becomes "don't import from home_builder_5/; it's a reference, not a dependency."

6. **What's the timeline pressure?** If you have customers waiting on the first 2.5D web preview (the original use case from `00-brief.md`), Option A's spec rewrite is ~2-3 hours of doc work; Option B ships sooner but encodes permanent technical debt; Option C delays things by weeks but yields the architecturally purest result.

---

## Recommendation Summary

> **Choose Option A.** Adopt kitchen-plugin as the foundation. Rewrite F001/F002/F004/F007/F008 specs to integrate with it rather than duplicate it. Total effort: ~2-3 hours of doc work, then resumed implementation that **leverages 4,500+ LOC + 23 tests of existing work** instead of redoing it.

The cold review missed this because it didn't open `kitchen-plugin/src/`. That's now fixed. The remaining cold-review findings (#2-#10) are still valid but minor compared to this one.

**Next action requested:** Confirm Option A, answer the six Open Questions above, and I will rewrite the affected specs in priority order.
