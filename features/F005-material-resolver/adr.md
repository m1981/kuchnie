# ADR — F005 — MaterialResolver as Core Service, Catalog as Protocol Implementer

**Date:** 2026-06-28
**Status:** `Proposed`
**Feature:** F005
**Author:** solo dev

---

## Context

Winner Flex's design insight — material assignment fully decoupled from construction — is already half-realized in our system: F001 published `ConstructionMethod` (HOW), F002 published `Recipe` (WHAT panels), F003 published `CabinetTemplate` (WHAT cabinet), and all three intentionally store **only role strings or slot names** for materials, never decor data. The other half is the resolver service that walks role → slot → decor → catalog and produces a concrete `ResolvedMaterial` for render, export, and cost consumers.

Two structural pressures shape this decision:

1. **Catalog is a separate bounded context.** It owns vendor data (Kronospan, Egger decor sheets). It already has its own Pydantic model in `catalog/docs/architecture/02-pydantic-models.py`. We must not couple Core's domain model to Catalog's schema, nor force Catalog to import Core types.

2. **Three consumers will call the resolver** (F006 web UI, F007 render adapter, F008 CAD CLI), each at a different stage. They cannot each invent catalog queries — the Plugin's `wood_materials.py` shows what that looks like (procedural shaders embedded in the renderer; impossible to reuse for cut-list export).

The decision needs to be made **now** because: (1) F004's reserved codes `KIT-100` and `CAM-100` cannot be filled until the resolver exists; (2) F006 (Web), F007 (Render), F008 (CLI) are unbuildable without a stable resolver API; (3) the Catalog-to-Core relationship pattern needs to be set before further cross-context features arrive.

---

## Decision

We will introduce `MaterialResolver` as a Core service that chains *role → slot → decor → ResolvedMaterial*, backed by a `CatalogReader` Protocol that Catalog implements. The pattern is **Customer/Supplier via Published Language**: Core publishes the Protocol; Catalog conforms to it. Core does not import from Catalog; Catalog imports the Protocol type from Core.

Specifically:

1. `src/kuchnie_core/material_resolver.py` ships: `CatalogReader` (Protocol), `DecorRecord` / `EdgeRecord` / `VariantRecord` (read-only projections), `GrainDirection` (enum), `ResolvedMaterial` (frozen dataclass), `MaterialResolverError`, and `MaterialResolver` (the service).

2. `MaterialResolver` is constructed with `(catalog: CatalogReader, kitchen: Kitchen)` and provides `resolve_role()`, `resolve_slot()`, `resolve_decor()`, and `list_decors_for_role()`. It maintains an in-memory cache keyed by `(decor_id, thickness_mm)`.

3. The resolver picks the **variant matching `ConstructionMethod.*_thickness_mm`** automatically. If no variant matches, it raises `MaterialResolverError`. `CAM-100` catches this gracefully at validation.

4. `Kitchen` gains a `material_slots: dict[str, str]` field — open-ended mapping of project slot name to `decor_id`. Templates declare slot references via `material_role_defaults`; cabinets inherit the references; kitchens declare what each slot actually is.

5. `catalog/src/catalog/yaml_reader.py::YamlCatalogReader` implements `CatalogReader`. Catalog data is YAML in `catalog/data/<producer>/decors/*.yaml` and `catalog/data/<producer>/edges/*.yaml`.

6. F005 ships **12 curated Kronospan + Egger decors** and **3 edges** as the v1.0 Polish-market baseline.

7. F005 ships three validation checks registered on F004 gates at module import: `SlotDeclarationCheck` and `DecorResolutionCheck` on `KitchenValidationGate` (both under `KIT-100`); `MaterialRoleResolutionCheck` on `CAMReadinessGate` (`CAM-100`).

8. Pricing, edge overrides, variant disambiguation, and live catalog sync are explicitly out of scope.

The `CatalogReader` Protocol and `ResolvedMaterial` type become part of Core's published API.

---

## Alternatives Considered

| Option | Why rejected |
|---|---|
| **A. Embed decor data in `CabinetInstance`** | Defeats the entire feature. The whole point is refs-only. F001–F003 explicitly committed to this; reversing it would break BOM, CAM, and render simultaneously. |
| **B. Resolve at recipe-emit time (push resolution into F002)** | Couples the engine to Catalog. F002's engine is pure formula evaluation; injecting catalog queries breaks the contract and bloats the test surface. The engine emits `material_role` strings; the resolver chains them. Clean separation. |
| **C. Single global resolver (process-level singleton)** | Each kitchen has different `material_slots`. A singleton would need re-initialization per kitchen and would risk leaking state across projects. Per-kitchen `MaterialResolver` instances are cheap and clear. |
| **D. HTTP-based catalog backend** | Adds runtime dependency, network failure modes, and zero benefit at the v1.0 scale (~12 decors). YAML in git is right. |
| **E. SQLite as the v1.0 storage** | At 12 decors, YAML wins on diffability and reviewability. SQLite is a Could when the catalog grows past ~200 decors. |
| **F. Inline decor IDs in `CabinetTemplate`** | Templates are reusable across projects. A `base_door_60` for customer A shouldn't carry customer A's decor choices. Slot names (`project_body`) decouple template from kitchen. |
| **G. Inline decor IDs in `CabinetInstance`** | Closer but still wrong — every kitchen change to "what is body?" would require touching every cabinet. Project-level `material_slots` consolidates this. |
| **H. Asynchronous resolver** | Synchronous catalog queries take microseconds. Async adds complexity for no gain. |
| **I. Pydantic for `ResolvedMaterial`** | Dataclass is enough — no validation needs, no serialization beyond CLI debug output. Frozen dataclass is lighter and signals "this is a value, not a validated entity". |
| **J. Resolver as static / module-level functions** | Loses the kitchen context that the resolver needs. Instance methods carry the catalog + kitchen state cleanly. |
| **K. Mandatory `material_slots` schema with required keys** (`project_body`, `project_front`, `project_back`, `project_countertop`) | Templates may declare any role (a glass-front wall cabinet uses `glass`). Mandatory keys would force every kitchen to declare slots it doesn't use. Open dict + validation check is right. |
| **L. Auto-fallback to nearest thickness when exact variant missing** | Hides real bugs. Producing an 18mm panel when carpenter ordered 19mm material is exactly the foot-gun F004 exists to prevent. Hard fail + clear validation issue. |
| **M. Decor → multiple paired edges** | A single decor can ship with one default edge from the producer. Custom edge selection is an explicit override (Could). Modeling N-paired-edges for v1.0 over-engineers. |
| **N. Resolver also computes pricing** | Pricing is a downstream BOM concern with its own logic (waste factor, sheet rounding, discounts). Coupling pricing to material resolution would make every render call drag pricing through. Separation is right. |
| **O. Resolver writes to catalog** (e.g., "save this newly-imported decor") | Read-only by Protocol design. Import scripts (separate utility) can write to YAML directly. |
| **P. Multi-language decor names now** | v1.0 is Polish. Decor names are vendor strings ("U112 PM Dąb Bardolino"); we ship them as-is. Future i18n keyed by `decor_id`. |
| **Q. Catalog imports Core's `Kitchen` model to validate references** | Catalog must not depend on Core's domain types. Catalog publishes records via the Protocol; validation lives in Core's gates (F004 + F005's registered checks). |
| **R. Resolver in Catalog instead of Core** | The resolver chains *kitchen slots → decor* — it needs `Kitchen` context (a Core type). Catalog cannot import Core. Therefore resolver lives in Core. |
| **S. Procedural materials (port plugin's `wood_materials.py`)** | The plugin generates procedural wood shaders inside Blender. Useless for cut-list export. We use texture lookups (`texture_path` field) exclusively. Plugin's procedural code stays inside the plugin; render adapter (F007) translates by setting the texture path on Blender materials, ignoring the procedural side. |
| **T. Disk-backed resolution cache** | In-memory cache scoped to resolver lifetime is enough. Disk cache adds invalidation problems for negligible perf gain. |
| **U. Variant disambiguation when multiple variants match the same thickness** | At v1.0 each thickness has one variant per decor. If this collides later, add disambiguation then. |
| **V. Resolver returns a list of options instead of one ResolvedMaterial** | Forces every consumer to pick. The resolver decides via the construction method; that's the design. Picker UI uses `list_decors_for_role()` separately. |

---

## Consequences

### Positive
- **Refs-only model is enforceable.** A grep for decor data in `CabinetInstance` would find none — by construction.
- **One swap point for project-wide decor changes** — edit `kitchen.material_slots`; every cabinet using `project_body` updates.
- **Catalog stays independent of Core.** No circular imports, no cross-context types in the wrong direction.
- **F004 contract fulfilled** — `KIT-100` and `CAM-100` filled cleanly via `register_check`, validating both the F004 extension API and the F005 chain.
- **Render, BOM, and CAM all read the same `ResolvedMaterial`** — no more "the renderer uses one color and the export uses another".
- **Caching is trivial** — `(decor_id, thickness_mm)` is a small key space; in-memory dict suffices.
- **The catalog YAMLs are diffable and reviewable** — adding a new Kronospan decor is a single PR with one file.

### Negative
- **Three-stage chain (role → slot → decor → variant) is more indirection than direct decor IDs on cabinets.** Mitigated by the resolver being the only place that walks the chain; consumers see only `ResolvedMaterial`.
- **The Polish-market catalog is curated by hand** (12 decors initially). Growing it past ~50 will need an importer script. Backlog item.
- **`MaterialResolverError` becomes a new exception consumers must handle (or pre-validate via gates).** Mitigated by F004's checks — well-validated kitchens never hit the exception.
- **Asymmetric dependency direction (Catalog → Core)** means Catalog cannot exist without Core in v1.0. Acceptable: they're both part of the same product.
- **Two parallel material systems coexist** — ours (texture lookups) and the plugin's (procedural shaders). Rule 4 stands; the render adapter (F007) bridges via texture path.

### Neutral
- **Catalog gains a Pydantic / dataclass projection layer.** The reader translates internal catalog records to Core's `DecorRecord` etc. Small mapping code; explicit and easy to test.
- **`ResolvedMaterial` is a value object** (frozen dataclass). Consumers can pass it freely; no shared mutable state.
- **Cache invalidation is trivially "rebuild resolver"** — fine for the kitchen-scale workloads we serve.

---

## Affected Files (canonical)

### Created (Core)
- `src/kuchnie_core/material_resolver.py` — Protocol, dataclasses, resolver, error type
- `src/kuchnie_core/validation/checks/material_checks.py` — three F004-registered checks
- `tests/core/material/test_resolver.py`
- `tests/core/validation/test_material_checks.py`

### Created (Catalog)
- `catalog/src/catalog/yaml_reader.py::YamlCatalogReader` — Protocol implementation
- `catalog/data/kronospan/decors/*.yaml` — 8 curated decors
- `catalog/data/egger/decors/*.yaml` — 4 curated decors
- `catalog/data/kronospan/edges/*.yaml` — 3 edges
- `tests/catalog/test_yaml_reader.py`

### Created (Integration)
- `tests/integration/test_kitchen_full_resolution.py` — F001+F002+F003+F004+F005 end-to-end

### Modified
- `src/kuchnie_core/model.py::Kitchen` — add `material_slots: dict[str, str]`
- `src/kuchnie_core/validation/codes.py` — fill in `KIT-100` and `CAM-100` registrations (mark `default_severity: ERROR`, owner: F005)
- `examples/kitchen_nowak.yaml` — add `material_slots` section
- `docs/GLOSSARY.md` — 11 new/refined entries
- `docs/01_architecture.md` — Context Map shows Catalog → Core arrow via `CatalogReader` Protocol
- `docs/03_implementation_placement.md` § Pattern 3 — link to F005 ADR

### Deleted or stubbed
- None.

---

## LLM Hints

> Direct instructions for future LLM sessions in this decision area.

- **When asked "should `CabinetInstance` carry decor data?"** → **No.** Refs only. The whole F005 feature exists to enforce this. See Alternative A.
- **When asked "should we resolve materials during recipe evaluation?"** → **No.** F002 emits role strings; F005 resolves them. Engine stays catalog-free. See Alternative B.
- **When asked "should the resolver be a global singleton?"** → **No.** Per-kitchen instances. See Alternative C.
- **When asked "YAML or SQLite for catalog?"** → **YAML in v1.0.** SQLite is a Could when catalog grows past ~200 decors. See Alternative E.
- **When asked "where does `CatalogReader` Protocol live?"** → **Core.** Catalog imports it to declare implementation. Core never imports from Catalog. See Alternative R.
- **When asked "should the resolver live in Catalog?"** → **No.** Resolver needs `Kitchen` context (a Core type). Catalog cannot import Core. Resolver is in Core. See Alternative R.
- **When asked "what if a variant matching the thickness doesn't exist?"** → **Raise `MaterialResolverError`.** Do not silently substitute. `CAM-100` catches at validation. See Alternative L.
- **When asked "should `material_slots` have required keys?"** → **No.** Open dict. `SlotDeclarationCheck` validates declared-vs-referenced. See Alternative K.
- **When asked "can a decor have multiple paired edges?"** → **One pairing in v1.0.** Override is Could. See Alternative M.
- **When asked "should the resolver compute pricing?"** → **No.** BOM concern. See Alternative N.
- **When asked "should the resolver be async?"** → **No.** See Alternative H.
- **When asked "Pydantic or dataclass for `ResolvedMaterial`?"** → **Frozen dataclass.** Value object, not validated entity. See Alternative I.
- **When asked "should we use the plugin's `wood_materials.py` for procedural rendering?"** → **No.** We use texture lookups. The plugin's procedural code stays untouched (Rule 4); F007's adapter sets the texture path on Blender materials. See Alternative S.
- **When asked "can the resolver write to catalog?"** → **No.** Protocol is read-only. Importers are separate utilities. See Alternative O.
- **When asked "can we cache to disk?"** → **No.** In-memory only. See Alternative T.
- **When asked "should we add more checks?"** → If purely structural (no catalog access), they belong in F004 as built-in checks. If they query catalog (material resolution), they belong in F005 as registered checks. Keep `KIT-100` / `CAM-100` as the resolution codes; add new codes (`KIT-101`, `CAM-101`, …) for distinct concerns.
- **When asked "should grain direction be set by recipe or decor?"** → **Decor publishes default, recipe overrides.** ResolvedMaterial carries the decor's default. F002 panels may set their own `grain_direction` which wins in CAM export. See spec Open Q9.
- **When asked "should we localize decor names?"** → **No** in v1.0. See Alternative P.
- **Do not propose:**
  - Adding `decor_id` directly to `CabinetInstance`.
  - Adding decor data to `CabinetTemplate` (templates are project-agnostic).
  - Embedding pricing in `ResolvedMaterial`.
  - HTTP-based catalog sync.
  - Live Kronospan/Egger website scraping.
  - Adding a Web UI for editing decors (carpenters use Kronospan's printed catalog).
  - Procedural material generation in Core (Blender's wood shaders are not the model).
  - Two-way Catalog ↔ Core type sharing.
- **Related ADRs:**
  - **F001 (Construction Method)** — `front_thickness_mm` / `side_thickness_mm` etc. drive variant selection. If construction changes thickness, resolver picks a different variant transparently.
  - **F003 (Template Registry)** — templates ship `material_role_defaults` (role → slot mapping) that cabinets inherit and the resolver consumes.
  - **F004 (Validation Gates)** — reserved codes `KIT-100` and `CAM-100` are filled by F005's checks via `register_check`. F004 does not implement them; F004 publishes the contract.
  - **F006 (Web Sidebar)** — calls `list_decors_for_role()` to populate the decor picker.
  - **F007 (Blender Adapter)** — calls `resolve_role()` per panel; sets Blender material `image_texture.image` from `ResolvedMaterial.texture_path`.
  - **F008 (CLI Cut List / DXF)** — calls `resolve_role()` per panel; uses `sheet_size_mm` for waste calc; uses `paired_edge_id` for edging CSV.

---

## Sign-off

- [ ] `docs/GLOSSARY.md` updated with 11 new/refined entries.
- [ ] Core `material_resolver.py` exports Protocol, dataclasses, resolver, error.
- [ ] Catalog `yaml_reader.py` implements the Protocol.
- [ ] 12 decor YAMLs + 3 edge YAMLs committed in `catalog/data/`.
- [ ] `Kitchen.material_slots` field added.
- [ ] Three validation checks registered on F004 gates at module import.
- [ ] `examples/kitchen_nowak.yaml` updated and passes all four gates including F005 checks.
- [ ] `grep -r "from catalog" src/kuchnie_core/` returns no hits (Core never imports Catalog).
- [ ] Reserved codes `KIT-100` and `CAM-100` are now filled in the registry with owner: F005.
- [ ] Status moved from `Proposed` → `Accepted` after first green full-resolution integration test run.
