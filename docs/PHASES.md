# Phases & Gate Criteria

> **Rule:** Do not start Phase N+1 until Phase N gate is signed off (all checkboxes ticked). No exceptions for "small leftover work."
>
> **Why this rule:** half-finished phases are how solo developers lose 2 weeks to debugging cross-phase regressions.
>
> **Agents:** when a user asks "what's next?", find the **current phase** (first phase with unticked gate criteria) and the **first proposed feature in that phase** (per `features/INDEX.md`).

---

## Phase Overview

| # | Phase | Week | Primary Context | Features | Status |
|---|---|---|---|---|---|
| 1 | Domain Foundations | 1 | Core | F001 | 🔵 current |
| 2 | Recipe Engine | 2 | Core + CAD | F002 | ⏳ proposed |
| 3 | Templates | 3 | Core + Web | F003 | ⏳ proposed |
| 4 | Validation Gates | 4 | Core | F004 | ⏳ proposed |
| 5 | Material Resolver | 5 | Catalog + Core | F005 | ⏳ proposed |
| 6 | Web Sidebar | 6 | Web | F006 | ⏳ proposed |
| 7 | Blender Adapter | 7 | Render | F007 | ⏳ proposed |
| 8 | CLI Cut List / DXF | 8 | CAD | F008 | ⏳ proposed |

**Legend:** 🔵 current · ⏳ proposed · ✅ done · 🛑 blocked

---

## Phase 1 — Domain Foundations

**Week:** 1
**Primary Context:** `kuchnie_core`
**Features:** F001 — Construction Method
**Goal:** `ConstructionMethod` exists as a first-class entity. `CabinetInstance` references a construction method by ID. `kitchen_config.yaml` v1.0 schema is published.

### Gate Criteria (all must be ✅ before Phase 2 starts)

- [ ] F001 `status.md` is `done`.
- [ ] `src/kuchnie_core/construction.py` exists with `ConstructionMethod`, `JoineryType`, `BackType`.
- [ ] `docs/GLOSSARY.md` contains: `ConstructionMethod`, `JoineryType`, `BackType`.
- [ ] `docs/schemas/kitchen_config.v1.0.yaml` published (schema file or pydantic-export).
- [ ] Round-trip test passes: YAML → `Kitchen` → YAML produces byte-identical output for a fixture.
- [ ] One worked example committed: `examples/kitchen_nowak.yaml`.
- [ ] `docs/01_architecture.md` Context Map shows `ConstructionMethod`.
- [ ] No `bpy`, `reflex`, or `fastapi` imports in `src/kuchnie_core/`.
- [ ] All existing tests still pass (no regression).

**Sign-off:** _________________ (date / commit hash)

---

## Phase 2 — Recipe Engine

**Week:** 2
**Primary Context:** `kuchnie_core` (data) + `kitchen-cad` (engine)
**Features:** F002 — Recipe Engine
**Goal:** YAML recipes drive panel calculation. The unsafe `eval()` in `recipe_loader.py` is replaced with `asteval`. At least 5 cabinet templates have working recipes.

### Gate Criteria

- [ ] F002 `status.md` is `done`.
- [ ] `src/kuchnie_core/recipes/` directory with at least 5 YAML files:
  - [ ] `base_door_single.yaml`
  - [ ] `base_drawer_3.yaml`
  - [ ] `wall_door_single.yaml`
  - [ ] `tall_pantry.yaml`
  - [ ] `corner_diagonal.yaml`
- [ ] `kitchen-cad/src/kitchen_cad/recipe_engine.py::RecipeEngine` exists.
- [ ] `asteval` (or equivalent safe evaluator) replaces all `eval()` calls.
- [ ] Each recipe has a unit test against a fixture `CabinetInstance`.
- [ ] Performance budget: 100 cabinets decompose in < 2 seconds.
- [ ] `docs/GLOSSARY.md` updated: `Recipe`, `RecipeEngine`.
- [ ] No regression in Phase 1 round-trip test.

**Sign-off:** _________________

---

## Phase 3 — Templates (Cabinet Macros)

**Week:** 3
**Primary Context:** `kuchnie_core`
**Features:** F003 — Template Registry
**Goal:** `CabinetTemplate` exists. A `TemplateRegistry` lists templates by category. Each template links to a recipe (from F002) and default dimensions.

### Gate Criteria

- [ ] F003 `status.md` is `done`.
- [ ] `src/kuchnie_core/templates.py` with `CabinetTemplate`, `TemplateRegistry`.
- [ ] `src/kuchnie_core/templates/*.yaml` for at least 10-15 templates (matching the 5 recipes from Phase 2 plus variants).
- [ ] `TemplateRegistry.instantiate(template_id, overrides)` → `CabinetInstance`.
- [ ] Tests: instantiation with defaults, with overrides, out-of-range rejection.
- [ ] `docs/GLOSSARY.md` updated: `CabinetTemplate`.
- [ ] Thumbnail paths defined (files may be placeholder PNGs at this phase).

**Sign-off:** _________________

---

## Phase 4 — Validation Gates

**Week:** 4
**Primary Context:** `kuchnie_core`
**Features:** F004 — Validation Gates
**Goal:** Four validation gates exist and are callable. Each consumer (Web, CAD, Render) knows which gates to call at which stage.

### Gate Criteria

- [ ] F004 `status.md` is `done`.
- [ ] `src/kuchnie_core/validation/` package with:
  - [ ] `CabinetValidationGate`
  - [ ] `RowValidationGate`
  - [ ] `KitchenValidationGate`
  - [ ] `CAMReadinessGate`
- [ ] `ValidationResult` with structured issues (code, message, severity, entity_ref).
- [ ] Tests for each gate covering pass + at least 3 failure modes.
- [ ] `docs/GLOSSARY.md` updated: `ValidationGate`, `ValidationResult`, `CAM Readiness`.
- [ ] Documented call-points: which app calls which gate, when.

**Sign-off:** _________________

---

## Phase 5 — Material Resolver

**Week:** 5
**Primary Context:** `catalog/` (data) + `kuchnie_core` (service)
**Features:** F005 — Material Resolver
**Goal:** `MaterialResolver` translates `decor_id` → `ResolvedMaterial` (texture, edge spec, color, grain). Cabinet model holds only `MaterialRef`s.

### Gate Criteria

- [ ] F005 `status.md` is `done`.
- [ ] `src/kuchnie_core/material_resolver.py::MaterialResolver`.
- [ ] `MaterialRef` and `ResolvedMaterial` Pydantic models.
- [ ] Catalog query backend (SQLite or YAML) returns decors & edges.
- [ ] Tests: resolve known decor, fail on unknown decor, pairing lookup.
- [ ] `docs/GLOSSARY.md` updated: `MaterialRef`, `MaterialResolver`, `ResolvedMaterial`.
- [ ] No decor data embedded in `CabinetInstance` — only `decor_id` refs.

**Sign-off:** _________________

---

## Phase 6 — Web Sidebar

**Week:** 6
**Primary Context:** `kitchen-app/`
**Features:** F006 — Web Sidebar (Template Browser)
**Goal:** Reflex UI lets the developer browse templates (from F003), pick decors (from F005), and place cabinets in rows.

### Gate Criteria

- [ ] F006 `status.md` is `done`.
- [ ] Sidebar UI with template categories (base / wall / tall / corner).
- [ ] Thumbnail browse + click-to-add.
- [ ] Row editor with arrow-based reordering.
- [ ] Decor picker UI with thumbnails (Kronospan / Egger).
- [ ] BOM panel shows cost in PLN, updates on change.
- [ ] Validation gates 1 + 2 called on edit; errors surface in UI.
- [ ] All `CabinetInstance` writes go through `kuchnie_core` API, not directly to SQLModel.

**Sign-off:** _________________

---

## Phase 7 — Blender Adapter (Render)

**Week:** 7
**Primary Context:** Render adapter (`kitchen-cad/render_adapter/` or new module)
**Features:** F007 — Blender Adapter
**Goal:** Adapter converts `Kitchen` → plugin's `kitchen_config.yaml`, invokes Blender headless, returns PNG path.

### Gate Criteria

- [ ] F007 `status.md` is `done`.
- [ ] `RowPlacement` → `WallPlacement` conversion implemented.
- [ ] CLI: `kitchen-cli render config.yaml --output kitchen.png`.
- [ ] Texture paths resolved via `MaterialResolver` (F005).
- [ ] Plugin loaded headless (`blender --background --python ...`).
- [ ] Validation Gate 3 called before invoking Blender.
- [ ] One worked example: `examples/kitchen_nowak.yaml` renders to PNG.
- [ ] `docs/GLOSSARY.md` updated: `WallPlacement`, `Scene`.

**Sign-off:** _________________

---

## Phase 8 — CLI Cut List / DXF

**Week:** 8
**Primary Context:** `kitchen-cad/`
**Features:** F008 — CLI Cut List + Drill + DXF
**Goal:** CLI produces e-rozkroj-compatible CSVs and DXF panels with machining features.

### Gate Criteria

- [ ] F008 `status.md` is `done`.
- [ ] `kitchen-cli cut-list config.yaml --output cuts.csv` (e-rozkroj / e-rozrys format).
- [ ] `kitchen-cli drill-pattern config.yaml --output drills.csv`.
- [ ] `kitchen-cli dxf config.yaml --output panels.dxf`.
- [ ] `MachiningFeature` model implemented (associative drill/groove/rabbet).
- [ ] Validation Gate 4 (CAM Readiness) called before export.
- [ ] `MachiningOp` (legacy) reconciled or deprecated.
- [ ] Round-trip test: example kitchen → CSV → manual diff against expected fixture.
- [ ] `docs/GLOSSARY.md` updated: `MachiningFeature` (and deprecation note on `MachiningOp`).

**Sign-off:** _________________

---

## Post v1.0 — Out of Scope (for now)

Explicit list to prevent agents from proposing them as "logical next steps":

- Multi-room projects
- Islands and slanted walls
- Nesting optimization (CNC company does this)
- ERP integration (SAP, Symfonia, Subiekt)
- Mobile-native iPad app (web app on iPad is sufficient for v1.0)
- Multi-user / cloud sync
- Auth / login
- Customer portal
- Multi-language UI (Polish only for v1.0)
- Curved cabinets / radius worktops
- Solid wood doors with grain matching across pieces
- Lighting / electrical planning beyond LED grooves
- AR / VR preview

If a user asks about any of the above, your response: "That is post-v1.0. We can capture it as a backlog item but should not scope it into the current phase."

---

## How to Mark a Phase Complete

1. Open this file.
2. For the relevant phase, tick every checkbox in **Gate Criteria**.
3. Fill `Sign-off` with date + commit hash.
4. Update **Phase Overview** table: change `🔵 current` → `✅ done`, mark next phase `🔵 current`.
5. Commit. The commit message: `phase: close Phase N — <name>`.
6. Open `features/INDEX.md` and mark the next phase's features as ready to start.

---

## How to Detect Drift

If at any point:

- Phase N has been "almost done" for > 1.5 × its time budget → **STOP**. Open the spec. Cut scope to "Must" only, defer "Should" to a follow-up feature.
- A feature in Phase N requires editing Phase N-2 code → **STOP**. That's drift. Document why in an ADR before continuing.
- An LLM agent proposes work that doesn't appear in any phase → **STOP**. Either add a feature to a phase or reject as out of scope.
