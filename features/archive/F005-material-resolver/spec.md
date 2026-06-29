# F005 — Material Resolver (decor_id → ResolvedMaterial)

## Job Story

**When** I am preparing a kitchen for render (F007), CNC export (F008), or cost calculation (F006), and any consumer needs to know "what is the body material of this cabinet?",
**I want to** call a single `MaterialResolver` that walks the chain *role → project slot → decor → ResolvedMaterial*, queries the Catalog (Kronospan, Egger), returns texture path, color hex, paired edge, grain direction, and the variant matching the cabinet's construction method,
**So I can** keep `CabinetInstance` storing only ID references (not embedded decor data), swap project-wide decors by editing one section of the kitchen YAML, and have render + export + cost all agree on what material a given panel is — without each consumer re-implementing catalog lookups.

---

## Bounded Context

- **Primary (split intentionally):**
  - `Catalog` (`catalog/`) — owns decor/edge data and the concrete reader implementation.
  - `Core` (`src/kuchnie_core/`) — owns the `CatalogReader` Protocol, the `MaterialResolver` service, the `ResolvedMaterial` type, and the F004 validation checks (`KIT-100`, `CAM-100`).
- **Touched (consumers, must have explicit reason):**
  - None added by F005 itself. Future consumers (F006 decor picker UI, F007 texture lookup, F008 sheet-size lookup) will call the resolver.

> **Change Locality Test result:** two contexts, but the relationship is **Customer/Supplier via Published Language** — Core defines the `CatalogReader` Protocol; Catalog implements it. Catalog has no compile-time dependency on Core. Core has no compile-time dependency on Catalog's storage. This is the textbook ACL/Protocol pattern and is dictated by `04_solo_dev_process.md` § Context Map. ✅ Passes.

---

## Subdomain Classification

- [x] **Core** — competitive advantage. Polish-market specifics live here: which Kronospan decor pairs with which edge, which Egger laminate has visible grain, which variant matches the carpenter's typical 18mm corpus stock. We curate the catalog and the resolver behavior.
- [ ] Supporting
- [ ] Generic

**Reasoning:** The decor catalog itself is **vendor-published data** (Kronospan, Egger publish their decor sheets). We could classify it as Generic (just an import job). But the **curation** — which decors a Polish carpenter actually offers, what edges go with what, which variants are standard stock — is Core. Cleanest framing: the data is Generic; the resolver and curated subset are Core. F005 builds both.

---

## Data Ownership

- **Canonical writes happen in:**
  - Decor and edge YAMLs: `catalog/data/<producer>/decors/*.yaml`, `catalog/data/<producer>/edges/*.yaml` (hand-edited or producer-imported).
  - Resolver service: `src/kuchnie_core/material_resolver.py::MaterialResolver` (Core).
  - Protocol: `src/kuchnie_core/material_resolver.py::CatalogReader` (Core).
  - Concrete reader: `catalog/src/catalog/yaml_reader.py::YamlCatalogReader` (Catalog).
  - `ResolvedMaterial` type: `src/kuchnie_core/material_resolver.py::ResolvedMaterial` (Core).
- **Read-only consumers:**
  - `kitchen-app` (F006) — calls `resolver.list_decors_for_role()` to populate decor picker UI; calls `resolve_slot()` to display preview swatches.
  - `kitchen-cad` CLI (F008) — calls `resolve_role()` to get `sheet_size_mm` for cut list waste calc; calls to get edge specs for edging CSV.
  - Render adapter (F007) — calls `resolve_role()` per cabinet panel to get `texture_path` for Blender material assignment.

---

## Scope — MoSCoW

### Must (do not ship without)

#### Core types and service

- [ ] `src/kuchnie_core/material_resolver.py`:
  - [ ] `CatalogReader` Protocol with methods:
    - `get_decor(decor_id: str) -> DecorRecord | None`
    - `get_edge(edge_id: str) -> EdgeRecord | None`
    - `get_variant(decor_id: str, thickness_mm: int) -> VariantRecord | None`
    - `list_decors_by_producer(producer: str) -> list[DecorRecord]`
  - [ ] `DecorRecord` dataclass — minimal projection of a Decor (decor_id, name, producer, color_hex, texture_path, grain_direction, paired_edge_id).
  - [ ] `EdgeRecord` dataclass — minimal projection of an Edge (edge_id, name, color_hex, thickness_mm, abs_or_pvc).
  - [ ] `VariantRecord` dataclass — (decor_id, thickness_mm, sheet_size_mm, sku).
  - [ ] `GrainDirection` enum: `NONE`, `VERTICAL`, `HORIZONTAL`.
  - [ ] `ResolvedMaterial` dataclass (frozen) — the output type. Fields: `decor_id`, `name`, `texture_path`, `color_hex`, `grain_direction`, `paired_edge_id`, `paired_edge_color_hex`, `thickness_mm`, `sheet_size_mm: tuple[int, int]`, `sku`.
  - [ ] `MaterialResolverError` — raised on unresolvable refs (used by checks; consumers may pre-check via gates).
  - [ ] `MaterialResolver` class with constructor `(catalog: CatalogReader, kitchen: Kitchen)` and methods:
    - [ ] `resolve_role(role: str, cabinet: CabinetInstance) -> ResolvedMaterial` — full chain: role → slot → decor → ResolvedMaterial. **Edge-role convention:** if `role` ends with `_color` (e.g., `front_color`, `body_color`), strip the suffix and resolve the base role (`front`, `body`); consumers use `ResolvedMaterial.paired_edge_id` / `paired_edge_color_hex` for edge banding. `<role>_color` is never a separate slot in `kitchen.material_slots`.
    - [ ] `resolve_slot(slot_name: str, thickness_mm: int) -> ResolvedMaterial` — middle of chain: slot → decor → ResolvedMaterial.
    - [ ] `resolve_decor(decor_id: str, thickness_mm: int) -> ResolvedMaterial` — bottom of chain: decor → ResolvedMaterial.
    - [ ] `list_decors_for_role(role: str, producer: str | None = None) -> list[DecorRecord]` — for UI (F006).
  - [ ] In-memory cache keyed by `(decor_id, thickness_mm)` — invalidated on resolver instance recreation.

#### Kitchen model addition

- [ ] `src/kuchnie_core/model.py::Kitchen` gains:
  - `material_slots: dict[str, str]` — mapping of project slot name (e.g., `project_body`, `project_front`, `glass`) to `decor_id`.
  - Default to empty dict for backward compatibility; resolution fails clearly if a slot is referenced but not declared.

#### Catalog implementation (YAML reader)

- [ ] `catalog/src/catalog/yaml_reader.py::YamlCatalogReader` — implements `CatalogReader`.
  - [ ] Loads from `catalog/data/<producer>/decors/*.yaml` and `catalog/data/<producer>/edges/*.yaml`.
  - [ ] Indexes by `decor_id` and `edge_id` on construction.
  - [ ] Lazy texture path resolution (does not load images; just returns paths).
- [ ] Producer subfolder convention documented: `catalog/data/kronospan/`, `catalog/data/egger/`.

#### Curated catalog content (Polish-market minimum)

- [ ] **8 Kronospan decors:**
  - `kronospan_w980_sm.yaml` — biały klasyczny (corpus default)
  - `kronospan_u112_pm.yaml` — dąb Bardolino (front oak)
  - `kronospan_h3303_st10.yaml` — equivalent oak (verify ID with reality)
  - `kronospan_k001_pe.yaml` — beton (countertop)
  - `kronospan_k003_pe.yaml` — alternate countertop
  - `kronospan_w1000_sm.yaml` — antracyt
  - `kronospan_d364_pr.yaml` — black gloss front
  - `kronospan_w908_sm.yaml` — szary jasny

- [ ] **4 Egger decors:**
  - `egger_h3303_st10.yaml` — Sonoma oak
  - `egger_w1000_st9.yaml` — premium white
  - `egger_u999_st2.yaml` — black matte
  - `egger_h1145_st10.yaml` — natural oak

- [ ] **3 edges with pairings:**
  - `edge_w980_05.yaml` — biały 0.5mm, paired with kronospan_w980_sm and other whites
  - `edge_u112_pm_05.yaml` — dąb Bardolino 0.5mm, paired with kronospan_u112_pm
  - `edge_universal_black_2mm.yaml` — universal black 2mm, manually selected

#### Validation checks (registered on F004 gates)

- [ ] `src/kuchnie_core/validation/checks/material_checks.py`:
  - [ ] `SlotDeclarationCheck` (KIT-100a — needs sub-code or merged into KIT-100):
    - For each cabinet's `material_refs`, verify every referenced slot name exists in `kitchen.material_slots`.
  - [ ] `DecorResolutionCheck` (KIT-100):
    - For each `kitchen.material_slots` entry, verify the `decor_id` resolves in the catalog.
  - [ ] `MaterialRoleResolutionCheck` (CAM-100):
    - For each panel's `material_role` in the `DecompositionResult`, verify the full chain resolves and a variant matches the construction method's thickness.
- [ ] Register on F004 gates at module load:
  - `KitchenValidationGate.register_check(SlotDeclarationCheck())`
  - `KitchenValidationGate.register_check(DecorResolutionCheck())`
  - `CAMReadinessGate.register_check(MaterialRoleResolutionCheck())`

#### Tests

- [ ] `tests/core/material/test_resolver.py`:
  - [ ] `test_resolve_decor_returns_resolved_material()`
  - [ ] `test_resolve_slot_chains_through_kitchen()`
  - [ ] `test_resolve_role_chains_full_path()` — role → slot → decor → ResolvedMaterial.
  - [ ] `test_resolve_unknown_decor_raises()`
  - [ ] `test_resolve_unknown_slot_raises()`
  - [ ] `test_resolve_role_picks_correct_variant_by_thickness()` — 18mm corpus picks 18mm variant.
  - [ ] `test_resolve_role_falls_back_when_exact_thickness_missing()` — picks nearest available variant + WARNING (or raises — decide in tasks).
  - [ ] `test_cache_hit_returns_same_instance()`.
- [ ] `tests/catalog/test_yaml_reader.py`:
  - [ ] `test_load_kronospan_decors()` — loads 8 decors without error.
  - [ ] `test_load_edges_with_pairings()`.
  - [ ] `test_get_decor_by_id_returns_record()`.
  - [ ] `test_paired_edge_lookup()`.
- [ ] `tests/core/validation/test_material_checks.py`:
  - [ ] `test_slot_declaration_check_fires_on_missing_slot()`.
  - [ ] `test_decor_resolution_check_fires_on_unknown_decor()`.
  - [ ] `test_material_role_resolution_check_fires_on_unresolved_role()` (CAM-100).
- [ ] `tests/integration/test_kitchen_full_resolution.py`:
  - [ ] `examples/kitchen_nowak.yaml` resolves every cabinet's body, front, back, shelf roles cleanly.
  - [ ] Worktop's material resolves.
  - [ ] All four gates pass (Phase 4 + Phase 5 integrated).

#### Example kitchen updated

- [ ] `examples/kitchen_nowak.yaml`:
  - Add `material_slots:` section mapping slots to actual Kronospan/Egger decor IDs from the curated 12.
  - Verify F004 + F005 integration test passes cleanly on it.

### Should (do if time permits)

- [ ] `kitchen-cli list-decors [--producer kronospan]` — print catalog by producer.
- [ ] `kitchen-cli resolve <decor_id> [--thickness 18]` — print full `ResolvedMaterial`.
- [ ] `kitchen-cli show-pairings` — list every decor with its paired edge.
- [ ] Producer-specific YAML generators (`scripts/generate_kronospan_yaml.py`) — already referenced in the existing repo structure; align with F005's schema.
- [ ] Fuzzy decor search by name (`resolver.find_by_name("dąb")`) for UI autocomplete.

### Could (almost certainly defer)

- [ ] SQLite-backed `CatalogReader` (alongside YAML) — speed up large catalogs. Not needed at v1.0 scale (12 decors).
- [ ] Edge override mechanism — kitchen declares `edge_overrides: {project_body: edge_universal_black_2mm}` to override pairing. Defer; default pairing covers v1.0 needs.
- [ ] Material role aliasing — template declares `glass` role; kitchen maps via alias table. Defer; direct slot names work.
- [ ] Multi-language decor names (`name_pl`, `name_en`).
- [ ] Variant disambiguation when multiple variants match (e.g., two 18mm variants with different sheet sizes).

### Won't (this iteration — explicit cuts)

- ❌ **Pricing in `ResolvedMaterial`.** BOM is downstream; `ResolvedMaterial` is structural data only. Pricing lives in catalog + BOM logic, queried separately.
- ❌ **Live catalog sync from Kronospan/Egger websites.** Manual YAML for v1.0. A backlog item can add an importer.
- ❌ **Decor approval workflow / "is this decor still available?".** Business state, not material data.
- ❌ **Custom user-uploaded textures.** Catalog is the only source.
- ❌ **Procedural materials** (the plugin's `wood_materials.py` approach — generating wood shaders in Blender). We use texture lookups exclusively. Plugin's procedural code is untouched (Rule 4); the render adapter (F007) just sets the texture path.
- ❌ **Multi-language decor names.** Polish only in v1.0. `_pl` suffix on optional fields makes future expansion mechanical, but v1.0 ships single-language.
- ❌ **Decor versioning** (Kronospan occasionally updates a decor's specs). Out of scope; treat each decor_id as stable forever in v1.0.
- ❌ **Custom edge specifications per panel.** Use pairing default. Override is a Could.
- ❌ **Variant selection UI / variant disambiguation in CLI.** Resolver picks the variant matching construction method's thickness; conflicts are deferred.
- ❌ **Embedding decor data in `CabinetInstance` or `Kitchen`.** This is the whole point of F005 — refs only. Anti-pattern check.
- ❌ **Web UI for editing decors.** Carpenters use Kronospan's printed catalog; we curate IDs.
- ❌ **Plugin extension.** Plugin reads texture paths from the scene; render adapter (F007) injects them. Plugin's own `wood_materials.py` and `finish_colors.py` stay untouched.

---

## Change Locality Test

- [x] Editing **two bounded contexts** (Catalog data + Core service). The split is structurally required: Catalog cannot import from Core (otherwise it would be Core); Core defines a Protocol that Catalog implements. Standard Customer/Supplier via Published Language pattern.
- [x] **One published contract change**: the `CatalogReader` Protocol becomes part of Core's published surface. The `Kitchen.material_slots` field is a same-version schema addition (v1.0 in progress, no consumer has shipped).
- [x] **Passes** with explicit dual-context justification.

---

## Glossary Impact

**New terms** (must be added to `docs/GLOSSARY.md` in the implementation commit):

- `MaterialResolver` — promote placeholder → concrete (file of record: `src/kuchnie_core/material_resolver.py`).
- `MaterialRef` — promote placeholder → concrete. **Refined meaning:** in v1.0, `material_refs` on `CabinetInstance` is a `dict[role_str, slot_name_str]`. The slot name is a project-level identifier (e.g., `project_body`); the resolver chains to the decor.
- `ResolvedMaterial` — promote placeholder → concrete.
- `CatalogReader` — new Protocol; Catalog's implementation contract.
- `DecorRecord` — new; minimal projection of a Decor used by Core.
- `EdgeRecord` — new; minimal projection of an Edge used by Core.
- `VariantRecord` — new; minimal projection of a Variant used by Core.
- `GrainDirection` — new enum.
- `MaterialResolverError` — new exception.
- `MaterialSlot` — new term: project-level slot name in `Kitchen.material_slots`.
- `SlotDeclarationCheck`, `DecorResolutionCheck`, `MaterialRoleResolutionCheck` — new validation check classes.

**Existing terms refined:**

- `Decor` — clarify that Catalog owns the full record; Core sees only `DecorRecord` projection through the Protocol.
- `Kitchen` — gains `material_slots: dict[str, str]` field.
- `MaterialRef` — clarified above.

---

## Acceptance Criteria

The feature is **done** when:

- [ ] `src/kuchnie_core/material_resolver.py` exists with Protocol, dataclasses, resolver, error type.
- [ ] `catalog/src/catalog/yaml_reader.py::YamlCatalogReader` implements the Protocol.
- [ ] 12 Kronospan/Egger decor YAMLs and 3 edge YAMLs committed to `catalog/data/`.
- [ ] `Kitchen.material_slots` field added.
- [ ] 3 validation checks registered on F004 gates at module load.
- [ ] `examples/kitchen_nowak.yaml` updated with `material_slots` section, validates cleanly through all four gates.
- [ ] All unit tests pass: resolver, reader, checks, integration.
- [ ] No `kuchnie_core` import in `catalog/src/catalog/yaml_reader.py` (Catalog implements Protocol structurally; type-checker may need `if TYPE_CHECKING:` for Protocol annotation).

Wait — re-check that: Catalog *does* need to import the Protocol to declare implementation. Yes, Catalog imports from `kuchnie_core.material_resolver` to type its class. That's fine because Catalog is the **downstream conformist** in this relationship. (The constraint we want to preserve: **Core does not import from Catalog**.)

- [ ] Verify `grep -r "from catalog" src/kuchnie_core/` returns no hits.
- [ ] `docs/GLOSSARY.md` updated with 11 new/refined terms.
- [ ] `docs/01_architecture.md` Context Map shows Catalog → Core arrow via `CatalogReader` Protocol.
- [ ] ADR `features/F005-material-resolver/adr.md` status = `Accepted`.
- [ ] `status.md` set to `done`.
- [ ] `features/INDEX.md` updated.
- [ ] Phase 5 gate criteria in `docs/PHASES.md` ticked.

---

## Out of Scope (anti-drift)

- ❌ **Plugin extension.** Plugin's `wood_materials.py`, `finish_colors.py`, and procedural shader code are untouched. F007's render adapter injects texture paths into the scene; plugin renders them.
- ❌ **Reflex UI.** F006 surfaces the decor picker; F005 ships the resolver.
- ❌ **Pricing data.** BOM concern.
- ❌ **Catalog import tooling beyond manual YAML.** Backlog.
- ❌ **Bulk catalog editor / web UI.** Carpenters edit YAML directly.
- ❌ **Decor preview rendering for thumbnails.** Render adapter (F007) generates renders; resolver returns paths.
- ❌ **Material role aliasing / indirection beyond slot → decor.** Direct mapping for v1.0.
- ❌ **Caching across resolver instances.** In-memory only, scoped to one MaterialResolver lifetime.
- ❌ **Resolver writes to catalog.** Read-only by Protocol design.
- ❌ **Cross-kitchen catalog optimization** (e.g., recommend decors used in past customer projects). Out of scope.
- ❌ **Reconciliation with catalog's existing Pydantic models** (from `catalog/docs/architecture/02-pydantic-models.py`). Those exist in the catalog repo's own architecture docs; F005's `DecorRecord` etc. are Core-side projections that may differ in field set. Mapping is the reader's job.

---

## References

- **Pattern source:** `docs/02_pattern_analysis.md` § Pattern 3 (Material ≠ Construction, from Winner Flex). Plugin already does this well via `Frameless_Cabinet_Style`; F005 builds the Pure-Python equivalent in Core.
- **Placement decision:** `docs/03_implementation_placement.md` § Pattern 3 — Material ≠ Construction. Cabinet stores ID refs; Catalog publishes data; Core resolves.
- **Process rules:** `docs/04_solo_dev_process.md` § Context Map (Customer/Supplier via Published Language).
- **Related ADRs:**
  - `features/F001-construction-method/adr.md` — `ConstructionMethod` provides the `*_thickness_mm` fields that the resolver uses to pick the variant.
  - `features/F003-template-registry/adr.md` — templates declare `material_role_defaults` (role → slot mapping) that the resolver consumes.
  - `features/F004-validation-gates/adr.md` — reserved codes `KIT-100` and `CAM-100` are filled by F005.
  - `features/F005-material-resolver/adr.md` — this feature's ADR.
- **Related features:**
  - **Depends on:**
    - F001 (resolver picks variant by `ConstructionMethod.*_thickness_mm`).
    - F003 (templates ship `material_role_defaults`; instantiated cabinets carry `material_refs`).
    - F004 (`register_check` API; reserved codes `KIT-100`, `CAM-100`).
  - **Enables:**
    - F006 (decor picker UI calls `list_decors_for_role` and `resolve_slot`).
    - F007 (render adapter calls `resolve_role` to get `texture_path` for Blender scene).
    - F008 (CLI cut list calls `resolve_role` for `sheet_size_mm` and paired edge specs).
  - **Conflicts with:** none. F005 is purely additive in Core and Catalog.

---

## Worked Example — End-to-End Resolution (for spec clarity)

### Decor YAML (Catalog)

```yaml
# catalog/data/kronospan/decors/kronospan_u112_pm.yaml
decor_id: kronospan_u112_pm
producer: kronospan
name: "U112 PM Dąb Bardolino"
color_hex: "#8B6F47"
grain_direction: VERTICAL
texture_path: "textures/kronospan/u112_pm.jpg"
paired_edge_id: edge_u112_pm_05

variants:
  - thickness_mm: 18
    sheet_size_mm: [2800, 2070]
    sku: "U112-PM-18-2800x2070"
  - thickness_mm: 19
    sheet_size_mm: [2800, 2070]
    sku: "U112-PM-19-2800x2070"
  - thickness_mm: 25
    sheet_size_mm: [2800, 2070]
    sku: "U112-PM-25-2800x2070"
```

### Edge YAML (Catalog)

```yaml
# catalog/data/kronospan/edges/edge_u112_pm_05.yaml
edge_id: edge_u112_pm_05
producer: kronospan
name: "Edge 0.5mm Dąb Bardolino U112 PM"
color_hex: "#8B6F47"
thickness_mm: 0.5
material: ABS

paired_decor_ids:
  - kronospan_u112_pm
```

### Kitchen YAML

```yaml
# examples/kitchen_nowak.yaml (relevant section)
default_construction_method_id: dowel_camlock_18

material_slots:
  project_body: kronospan_w980_sm        # plain white melamine
  project_front: kronospan_u112_pm        # oak finish
  project_back: kronospan_w980_sm         # same as body
  project_countertop: kronospan_k001_pe   # concrete look
  glass: clear_4mm                        # optional glass slot

rows:
  - id: row_south
    cabinets:
      - id: cab_001
        template_id: base_door_60
        # material_refs inherited from template:
        # body: project_body, front: project_front, back: project_back, shelf: project_body
        ...
```

### Python resolution

```python
from kuchnie_core.material_resolver import MaterialResolver
from catalog.yaml_reader import YamlCatalogReader

catalog = YamlCatalogReader(catalog_dir="catalog/data")
resolver = MaterialResolver(catalog=catalog, kitchen=kitchen)

# Resolve the front of cabinet cab_001
material = resolver.resolve_role(role="front", cabinet=kitchen.find_cabinet("cab_001"))

# material is:
# ResolvedMaterial(
#     decor_id="kronospan_u112_pm",
#     name="U112 PM Dąb Bardolino",
#     texture_path=Path("textures/kronospan/u112_pm.jpg"),
#     color_hex="#8B6F47",
#     grain_direction=GrainDirection.VERTICAL,
#     paired_edge_id="edge_u112_pm_05",
#     paired_edge_color_hex="#8B6F47",
#     thickness_mm=19,                    # picked because construction.front_thickness_mm=19
#     sheet_size_mm=(2800, 2070),
#     sku="U112-PM-19-2800x2070",
# )
```

### Resolution chain (role → slot → decor → variant)

```
role: "front"
  │
  ▼  cabinet.material_refs["front"]  (inherited from template)
slot: "project_front"
  │
  ▼  kitchen.material_slots["project_front"]
decor_id: "kronospan_u112_pm"
  │
  ▼  catalog.get_decor("kronospan_u112_pm")  + construction.front_thickness_mm=19
variant: 19mm, 2800×2070
  │
  ▼  catalog.get_edge("edge_u112_pm_05")  (via paired_edge_id)
edge: paired
  │
  ▼  assemble
ResolvedMaterial(...)
```

---

## Role String Conventions

The canonical role strings recognized by v1.0 are:

| Role string | Meaning | Resolves via |
|---|---|---|
| `body` | Carcass / body panels | full chain (role → slot → decor) |
| `front` | Door / drawer fronts | full chain |
| `back` | Back panel | full chain |
| `shelf` | Shelf panels | full chain (usually mapped to same slot as `body`) |
| `<role>_color` | Edge banding paired with the decor in slot `<role>` | strip `_color` suffix, resolve base role, return `paired_edge_id` of that decor |

Recipes (F002) emit role strings verbatim on each `Panel`. Templates (F003) declare `material_role_defaults` mapping these role strings to project slot names. The resolver chains them to concrete decors and paired edges.

Unknown roles raise `MaterialResolverError` at resolve time. F004's Gate 2 (Row) validates that every role emitted by recipes is declared in the cabinet's `material_refs`; Gate 4 (CAM-readiness) validates that every slot referenced is present in `kitchen.material_slots`.

---

## Open Questions

> All must be answered before coding begins.

- [x] **Q1:** Where does `CatalogReader` Protocol live? → **A:** `src/kuchnie_core/material_resolver.py` (Core). Catalog imports it to declare implementation; Core does not import from Catalog. Asymmetric dependency by design.
- [x] **Q2:** YAML or SQLite for catalog storage in v1.0? → **A:** YAML. ~12 decors at v1.0; git-friendly, diffable, matches our other YAML choices (recipes, templates, construction methods). SQLite is a Could if catalog grows past ~200 decors.
- [x] **Q3:** What if the requested thickness has no matching variant? → **A:** Raise `MaterialResolverError`. `CAM-100` check catches this gracefully and surfaces as a validation issue. Falling back silently to nearest thickness would hide real problems.
- [x] **Q4:** Edge pairing — auto-paired or always explicit? → **A:** Auto-paired by default via `decor.paired_edge_id`. Override is deferred to Could.
- [x] **Q5:** Caching strategy? → **A:** In-memory `dict[(decor_id, thickness_mm), ResolvedMaterial]` on `MaterialResolver` instance. Lives for the resolver's lifetime; recreate to invalidate. No disk cache.
- [x] **Q6:** Should `ResolvedMaterial` be Pydantic or dataclass? → **A:** Dataclass + `frozen=True`. No serialization needs; immutable; lightweight.
- [x] **Q7:** Does `Kitchen.material_slots` have required keys (`project_body`, `project_front`, …) or fully open? → **A:** Open. Templates declare what slots they reference; if a kitchen omits a slot referenced by a cabinet, `SlotDeclarationCheck` (KIT-100 variant) catches it. Open slots support `glass`, `oven_front`, custom names.
- [x] **Q8:** How does the resolver handle the worktop's material? → **A:** Worktop has its own `material_id: project_countertop` field (treat as a single slot). `resolver.resolve_slot("project_countertop", thickness_mm=38)` returns the countertop ResolvedMaterial. Worktop edge banding (front edge) follows the standard pairing rule unless overridden.
- [x] **Q9:** Grain direction conflict — decor says VERTICAL, recipe says HORIZONTAL — who wins? → **A:** Recipe wins. ResolvedMaterial returns the **decor's default** grain; the recipe's emitted `Panel.grain_direction` (when set) overrides. Capture this in the Panel emission (F002 path); resolver just publishes the default.
- [x] **Q10:** Schema version bump for `material_slots` field on Kitchen? → **A:** No bump. v1.0 schema is "in progress" until end-of-implementation; nothing has shipped. Document in ADR that v1.0 publication includes the `material_slots` field.
- [x] **Q11:** How does the resolver expose info to the decor picker UI (F006)? → **A:** `list_decors_for_role(role, producer=None) → list[DecorRecord]`. UI filters and renders thumbnails. `DecorRecord` carries enough info for picker display without resolving the full chain.
- [x] **Q12:** Does the resolver know about decor pricing? → **A:** No. Pricing is a separate concern (catalog stores price per variant, BOM logic computes total). Adding to `ResolvedMaterial` would couple unrelated concerns.

**All Open Questions resolved.** Spec is **ready** for implementation.
