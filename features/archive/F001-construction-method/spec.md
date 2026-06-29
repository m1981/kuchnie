# F001 — Construction Method as First-Class Entity

## Job Story

**When** I am setting up a kitchen project for a Wrocław customer,
**I want to** pick or define a single `ConstructionMethod` (panel thicknesses, joinery type, back attachment, overlays, drilling system) that applies to the whole project,
**So I can** swap construction details (e.g., dowel + cam-lock → confirmat) by changing one reference, without rewriting every cabinet template or recipe.

---

## Bounded Context

- **Primary (the one that OWNS this):** `Core` (`src/kuchnie_core/`)
- **Touched (consumers, must have explicit reason):**
  - `CAD` (`kitchen-cad/`): reads thickness and back-recess values in `panel_calculator.py` — replaces current reads from `config_parser.py` DEFAULTS dict.
  - `Render adapter` (Phase 7): translates `ConstructionMethod` to the plugin's `corpusThickness` / `frontThickness` scene settings.

> **Change Locality Test result:** primary writes are in Core only. Consumers are conformist reads. The plugin itself is untouched (just receives scene settings as it already does). ✅ Passes.

---

## Subdomain Classification

- [x] **Core** — competitive advantage. This is the swappable-method capability that PRO100 and Polyboard charge a license premium for. We build it ourselves.
- [ ] Supporting
- [ ] Generic

**Reasoning:** Construction method is **the** abstraction commercial Polish carpenters fight with. Owning this lets us switch CNC suppliers (different machines = different drilling patterns) without touching cabinet templates. Direct competitive advantage.

---

## Data Ownership

- **Canonical writes happen in:** `src/kuchnie_core/construction.py::ConstructionMethod` (Pydantic, immutable).
- **Read-only consumers:**
  - `kitchen-cad/src/kitchen_cad/panel_calculator.py` — reads thickness fields.
  - `kitchen-cad/src/kitchen_cad/drill_engine.py` — reads `drilling_system`, `system32_offset_mm`.
  - Render adapter (F007) — reads to populate plugin's scene settings.
- **Storage:** YAML files in `src/kuchnie_core/construction_methods/` (one method per file). Loaded by `ConstructionMethodRegistry`.

---

## Scope — MoSCoW

### Must (do not ship without)
- [ ] `ConstructionMethod` Pydantic model in `src/kuchnie_core/construction.py`.
- [ ] `JoineryType` enum: `DOWEL_CAMLOCK`, `CONFIRMAT`, `DADO`, `BUTT_GLUE`.
- [ ] `BackType` enum: `GROOVE`, `NAILED`, `RABBET`, `SCREWED`.
- [ ] `ConstructionMethodRegistry` — load YAML files, lookup by ID.
- [ ] At least 2 worked methods committed:
  - [ ] `dowel_camlock_18.yaml` (default for v1.0)
  - [ ] `confirmat_18.yaml` (alternative for cheaper builds)
- [ ] `CabinetInstance` gains `construction_method_id: str` field.
- [ ] `Kitchen` gains `default_construction_method_id: str` field.
- [ ] `kitchen_config.yaml` v1.0 schema published in `docs/schemas/kitchen_config.v1.0.yaml`.
- [ ] Round-trip test: YAML → `Kitchen` → YAML byte-identical.
- [ ] Migration: existing YAML examples updated to v1.0 (or auto-upgraded with default method).

### Should (do if time permits)
- [ ] CLI command: `kitchen-cli list-construction-methods`.
- [ ] Validation: cabinet's method must exist in registry (warn if missing).

### Could (almost certainly defer)
- [ ] Web UI to edit construction methods (deferred to F006).
- [ ] Per-cabinet method override (deferred — v1.0 uses project-level method only).

### Won't (this iteration — explicit cuts)
- ❌ Method UI in Reflex — F006 handles that, not F001.
- ❌ Linking construction methods to CNC machine profiles — out of scope for v1.0.
- ❌ Multi-method projects (mixed cabinets using different methods) — v1.0 = one method per kitchen.
- ❌ Changing the plugin's `config_parser.py` DEFAULTS dict — we feed values via scene config; plugin internals untouched per Rule 4.

---

## Change Locality Test

- [x] Editing **one bounded context** (Core) — adapters in CAD/Render are thin reads.
- [x] **One published contract change**: `kitchen_config.yaml` bumps from undefined/v0.x → v1.0.
- [x] **Passes.**

---

## Glossary Impact

**New terms** (must be added to `docs/GLOSSARY.md` in the implementation commit):

- `ConstructionMethod` — reusable spec of how a cabinet is built.
- `JoineryType` — enum: panel-joining method.
- `BackType` — enum: back-panel attachment method.
- `ConstructionMethodRegistry` — service that loads/queries methods.

**Existing terms refined:**

- `CabinetInstance` — now holds `construction_method_id` instead of inheriting `corpusThickness` from a flat dict.
- `Kitchen` — now holds `default_construction_method_id`.
- `kitchen_config.yaml` — formally versioned (v1.0). Add to glossary as Published Language.

---

## Acceptance Criteria

The feature is **done** when:

- [ ] Code committed: `src/kuchnie_core/construction.py` with model + enums + registry.
- [ ] YAML methods committed: at least 2 in `src/kuchnie_core/construction_methods/`.
- [ ] `CabinetInstance` and `Kitchen` models updated with method references.
- [ ] Tests in `tests/core/test_construction_method.py`:
  - [ ] Load registry from YAML directory.
  - [ ] Lookup by ID (success + KeyError on missing).
  - [ ] `CabinetInstance` round-trip with method reference.
  - [ ] `Kitchen` round-trip with default method.
- [ ] Tests in `tests/core/test_yaml_roundtrip.py`:
  - [ ] `examples/kitchen_nowak.yaml` → `Kitchen` → YAML → byte-identical.
- [ ] `docs/GLOSSARY.md` updated with 4 new terms (see Glossary Impact).
- [ ] `docs/schemas/kitchen_config.v1.0.yaml` exists (can be Pydantic-exported JSON Schema).
- [ ] `docs/01_architecture.md` Context Map updated to show `ConstructionMethod` in Core.
- [ ] ADR `features/F001-construction-method/adr.md` status = `Accepted`.
- [ ] `examples/kitchen_nowak.yaml` exists and validates.
- [ ] `status.md` set to `done`.
- [ ] `features/INDEX.md` updated.
- [ ] Phase 1 gate criteria in `docs/PHASES.md` ticked.

---

## Out of Scope (anti-drift)

- ❌ **Plugin extension.** We do not modify `home_builder_5/`. Plugin already accepts thickness scene settings; the render adapter (F007) feeds them.
- ❌ **Reflex UI for methods.** F006 handles UI. F001 is data + service only.
- ❌ **Migration tooling beyond v1.0 default fill.** If a user has YAMLs without `construction_method_id`, we inject the default ID at load time. No fancy migration scripts.
- ❌ **Per-cabinet method override.** v1.0 explicitly enforces one method per kitchen. A future feature can lift this restriction.
- ❌ **Joinery geometry (actual cam-lock hole positions).** That's F008's territory — `MachiningFeature`s on panels. F001 only stores the *type*, not the *drilling pattern*.
- ❌ **Reconciling with plugin's `corpusThickness` global setting.** Plugin keeps its model; adapter translates.

---

## References

- **Pattern source:** `docs/02_pattern_analysis.md` § Pattern 1 (Construction Method, from Polyboard)
- **Placement decision:** `docs/03_implementation_placement.md` § Pattern 1 — Construction Method
- **Process rules:** `docs/04_solo_dev_process.md`
- **Related ADRs:**
  - F001 ADR — this feature's decision (see `adr.md`)
- **Related features:**
  - **Depends on:** none (this is Phase 1, the foundation)
  - **Enables:** F002 (recipes read thicknesses from method), F005 (material refs become viable), F007 (adapter translates method to scene settings), F008 (drilling reads `system32_offset_mm`)
  - **Conflicts with:** legacy `config_parser.py` DEFAULTS dict in `kitchen-plugin/src/` — superseded but not deleted (plugin keeps its own copy; adapter feeds it).

---

## Open Questions

> All must be answered before coding begins. Each answer either updates the spec or becomes a line in the ADR.

- [x] **Q1:** One method per kitchen, or per cabinet? → **A:** Per kitchen for v1.0. Per cabinet deferred. Documented in "Won't" above.
- [x] **Q2:** YAML files or Pydantic constants for the built-in methods? → **A:** YAML, so users can add custom methods without editing Python. ADR documents this.
- [x] **Q3:** Are method IDs human-readable slugs or UUIDs? → **A:** Slugs (`dowel_camlock_18`). Humans pick them in YAML; UUIDs would be useless friction.
- [x] **Q4:** Should the registry be a singleton or instantiated per Kitchen load? → **A:** Singleton at module level, refreshed only on `reload()` call. Tests use a separate registry instance.
- [x] **Q5:** Versioning of methods (e.g., `dowel_camlock_18@v2`)? → **A:** Not in v1.0. If a method changes, name a new one. Versioning is a backlog item.

**All Open Questions resolved.** Spec is **ready** for implementation.
