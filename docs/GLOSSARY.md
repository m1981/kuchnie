# Ubiquitous Language Glossary

> **This file is the single source of truth for what domain words mean.**
>
> When a term has different meanings in different bounded contexts, every meaning is listed with its context. **Cross-context translation lives in adapters, not in concepts.**
>
> **Agents:** if a term is not here, do not invent its meaning. Ask the user.
> **Developer:** if you introduce a new domain class in code, add it here in the same commit.

---

## How to read entries

```
## TermName
- **Context:** which bounded context owns this meaning
- **Definition:** what it means (one paragraph max)
- **Not to be confused with:** disambiguators (other contexts, similar words)
- **File of record:** canonical Python class or YAML schema
- **Introduced by:** feature ID (e.g. F001) that brought this term in
- **Related ADR:** decision document, if any
```

---

## Bounded Contexts (corrected 2026-06-29 — see `docs/archive/01_DECISIONS.md`)

> **The One Rule.** Cross-subsystem imports must go through `kuchnie_core` only. The table below shows where each concept is **owned**; consumers should import via `kuchnie_core`, never directly from a sibling.

| Short name | Location | Owns words like |
|---|---|---|
| **Catalog** | `catalog/` | Decor, Edge, Variant, Pairing, Producer, Worktop, Availability |
| **Core (glue)** | `kuchnie-core/src/kuchnie_core/` | Kitchen, Run, ConstructionMethod, MaterialResolver, ValidationGate, the YAML schema |
| **CAM** | `kitchen-cam/` | CorpusSpec, Panel, DrillPoint, EdgeBand, BaseDoorConfig (& siblings) |
| **Adapter / 3D Render** | `home-builder-adapter/` (renamed per ADR-009) | Cabinet (placement-aware, via the `extract.py` ACL) — Wall/Room/Layout/CabinetGeometry now live in external `home_builder_5`; KitchenStandards and ManifestValidator moved into `kuchnie_core` |
| **Compositor / 2.5D Render** | `krono-compositor-mvp/` | SceneCompositor, ZoneConfig (mask→texture), Pass (base/uv/mask/reflection/handle) |
| **Web** | `kitchen-erp/` | BOMAssembly, BOMPart, PurchasingStrategy, RulesEngine (hardware tags), CabinetUI |
| **External (untouched)** | `home_builder_5/` (separate repo, **GPL**, not in v1.0 scope) | Community Blender addon — reference only, **not imported, never imported in v1.0** |

> Note: every "File of record" entry below points at the actual owning module per the table above. Some entries say `Core` for the glue type but the implementation lives in a sibling — that's intentional and matches the cross-import rule.

---

# A

## Accessory
- **Context:** Core
- **Definition:** A non-panel item that ships with a cabinet — hinges, runners, pulls, dampers, shelf pins. Has a SKU, quantity, and supplier reference. Does not get cut from a board.
- **Not to be confused with:**
  - `HardwareSet` (Web context — a UI bundle of accessories)
  - Blender plugin's `GeoNodeHardware` (visual proxy only)
- **File of record:** `kuchnie-core/src/kuchnie_core/model.py::Accessory`
- **Introduced by:** (pre-existing)

## ACL (Anti-Corruption Layer)
- **Context:** Architecture (cross-context)
- **Definition:** A translation layer that protects our domain model from an upstream legacy model. We use one between Core and `home_builder_5`'s Blender scene: `home-builder-adapter` (renamed per ADR-009) walks the scene tree and converts it into a `kuchnie_core.Kitchen`.
- **File of record:** `home-builder-adapter/src/extract.py`
- **Related ADR:** see `docs/archive/04_PROCESS.md` § Context Map

# B

## BackType
- **Context:** Core
- **Definition:** How the back panel attaches to the carcass — `groove`, `rabbet`, `stapled`. Part of `ConstructionMethod`.
- **File of record:** `kuchnie-core/src/kuchnie_core/construction.py::ConstructionMethod.back_attachment` (a string field today, not yet a formal enum)
- **Introduced by:** F001

## BOM (Bill of Materials)
- **Context:** Web (presentation), Core (calculation)
- **Definition:** Aggregated list of all panels, edges, accessories, and worktops required for a kitchen, with quantities, materials, and prices. Generated from a `DecompositionResult`.
- **Not to be confused with:** cut list (which is panel-only, for CNC nesting)
- **File of record:** `kuchnie-core/src/kuchnie_core/bom.py::BOM`
- **Introduced by:** (pre-existing)

# C

## Cabinet (ambiguous — see CabinetInstance, CabinetTemplate, CabinetUI)
- This word alone is ambiguous. Always qualify it:
  - **In Core:** mean `CabinetInstance` (placed instance) or `CabinetTemplate` (definition).
  - **In Web:** mean `CabinetUI`.
  - **In Plugin:** mean Blender's `Cabinet` class (geometry container — read-only to us).
- **Rule:** in code and prose, use the qualified form. Never just "Cabinet" in domain documents.

## CabinetInstance
- **Context:** Core
- **Definition:** A concrete placed cabinet in a kitchen. Has dimensions, a reference to a `CabinetTemplate`, a `ConstructionMethod`, material references, and a list of `SubAssembly`. The thing that gets manufactured.
- **Not to be confused with:**
  - `CabinetTemplate` (the recipe/macro)
  - `CabinetUI` (display wrapper in Web)
- **File of record:** `kuchnie-core/src/kuchnie_core/model.py::CabinetInstance`
- **Introduced by:** (pre-existing, refactored by F001)

## CabinetTemplate
- **Context:** Core
- **Definition:** A reusable cabinet "macro" — type, default dimensions, default sub-assemblies, allowed dimension ranges, recipe reference. The thing you pick from a sidebar. Borrowed pattern from PRO100.
- **Not to be confused with:** `CabinetInstance` (a placed instance of a template)
- **File of record:** (planned — not yet implemented; F003 template-registry was archived before landing)
- **Introduced by:** F003
- **Related ADR:** `features/archive/F003-template-registry/adr.md`

## CabinetUI
- **Context:** Web
- **Definition:** Reflex-side wrapper for displaying a `CabinetInstance` in the UI. Holds derived values for rendering (formatted dimensions, color hex, thumbnail path). Has no domain authority.
- **File of record:** `kitchen-erp/kitchen_erp/ui/state.py::CabinetUI`
- **Introduced by:** (pre-existing)

## CAM (Computer-Aided Manufacturing)
- **Context:** CAD
- **Definition:** The output stage where the system produces files for the CNC company — cut list CSV (compatible with e-rozkroj / e-rozrys), drill pattern CSV, DXF for panels with cutouts.
- **File of record:** `kitchen-cam/src/kitchen_cam/` (export modules)
- **Introduced by:** F008

## CAM Readiness
- **Context:** Core (validation)
- **Definition:** Gate 4 of the validation gates. A kitchen is CAM-ready when every panel has positive dimensions, every edge is assigned, every machining feature is fully resolved, and no cutout exceeds panel bounds. Refuse export if any check fails.
- **File of record:** (planned — not yet implemented; closest existing check is `kuchnie-core/src/kuchnie_core/validator.py`, which validates geometry manifests, not CAM cut-readiness)
- **Introduced by:** F004

## ConstructionMethod
- **Context:** Core
- **Definition:** A reusable specification of HOW a cabinet is built — panel thicknesses, joinery type, back attachment, overlays, drilling system, gaps. Independent of WHAT the cabinet is (its `CabinetTemplate`).
- **Not to be confused with:**
  - Plugin's `draw_construction()` UI panel (just visual grouping in Blender)
  - The `corpusThickness` setting in `config_parser.py` (legacy flat dict)
- **File of record:** `kuchnie-core/src/kuchnie_core/construction.py::ConstructionMethod`
- **Introduced by:** F001
- **Related ADR:** `features/archive/F001-construction-method/adr.md`

## CutPiece
- **Context:** CAD
- **Definition:** A single row in the cut list CSV — one panel with length, width, thickness, material, edge banding spec, grain direction. The format the CNC company expects.
- **File of record:** `kuchnie-core/src/kuchnie_core/export/cutlist_csv.py::CutPiece`
- **Introduced by:** (pre-existing)

# D

## DecompositionResult
- **Context:** Core
- **Definition:** The output of decomposing a `CabinetInstance` into its panels and accessories. Used as input to BOM calculation and cut list generation.
- **File of record:** `kuchnie-core/src/kuchnie_core/model.py::DecompositionResult`
- **Introduced by:** (pre-existing)

## Decor
- **Context:** Catalog (definitive), Core (by reference)
- **Definition:** A surface finish from a producer (e.g., "Kronospan U112 PM Oak Bardolino"). Identified by `decor_id: str`. Carries name, color hex, texture path, grain direction, paired edges.
- **Not to be confused with:**
  - `Material` (Web context — a UI summary)
  - `Variant` (Catalog — a finish-thickness combination)
- **File of record:** `catalog/models/domain.py::DecorWithVariants`
- **Introduced by:** (pre-existing)
- **Rule:** other contexts hold only `decor_id`, never embed decor data.

## DrillPoint
- **Context:** CAD
- **Definition:** A single drill operation on a panel — position (x, y), face (front/rear/edge), diameter, depth, type (system32, hinge, dowel, handle).
- **File of record:** `kuchnie-core/src/kuchnie_core/model.py::MachiningOp` (no dedicated `DrillPoint` class exists; a drill is a `MachiningOp` with `type="drill"`, using its `x_mm`/`y_mm`/`diameter_mm`/`depth_mm`/`drill_type` fields)
- **Introduced by:** (pre-existing)

# E

## Edge / EdgeBand
- **Context:** Catalog (definitive), Core (by reference)
- **Definition:** A roll of edge banding material (ABS, PVC, melamine) paired with one or more decors. Has thickness, width, color hex.
- **File of record:** Catalog has no dedicated `Edge` model yet; Core's DTO is canonical today: `kuchnie-core/src/kuchnie_core/materials/models.py::EdgeInfo`
- **Introduced by:** (pre-existing)

## EdgeSide
- **Context:** Core / CAD
- **Definition:** Which sides of a panel receive edge banding — `front`, `back`, `left`, `right`.
- **File of record:** `kuchnie-core/src/kuchnie_core/model.py::Panel.banded_edges` (dict keys today, not yet a formal enum)

# F

## Feature (project sense)
- **Context:** Process
- **Definition:** A planned chunk of work tracked under `features/F00X/`. Has a `spec.md`, optionally an `adr.md`, `tasks.md`, and `status.md`.
- **Not to be confused with:** `MachiningFeature` (CAD — drill/groove/rabbet on a panel)
- **File of record:** `features/archive/INDEX.md`

# G

## GeoNode (plugin terminology — for reference only)
- **Context:** Render (plugin internal)
- **Definition:** A Blender Geometry Node-driven object. Used internally by `home_builder_5/`. **Not exposed to our domain model.**
- **Note:** if discussing this, you are deep in the plugin. Step back.

# H

## HardwareSet
- **Context:** Web
- **Definition:** A UI-side bundle of accessories used together (e.g., "Blum Tandembox M, 500mm, silk-white"). Resolves to multiple `Accessory` objects in Core.
- **File of record:** `kitchen-erp/kitchen_erp/core/models.py::HardwareSet`

# J

## JoineryType
- **Context:** Core
- **Definition:** How panels join — `dowel_confirmat`, `camlock`, `dado`, `glue`. Part of `ConstructionMethod`.
- **File of record:** `kuchnie-core/src/kuchnie_core/construction.py::ConstructionMethod.joinery_type` (a string field today, not yet a formal enum)
- **Introduced by:** F001

# K

## Kitchen
- **Context:** Core
- **Definition:** The top-level domain aggregate. Contains rows, worktop segments, global construction method, global material references. The thing serialized to `kitchen_config.yaml`.
- **Not to be confused with:** `Project` (Web — wraps a Kitchen with customer/admin data)
- **File of record:** `kuchnie-core/src/kuchnie_core/model.py::Kitchen`
- **Introduced by:** (pre-existing)

## kitchen_config.yaml
- **Context:** Core (published language)
- **Definition:** The stable, versioned YAML schema used to serialize a `Kitchen`. The interchange format between Core, CAD, Web, and the render adapter.
- **File of record:** `kuchnie-core/src/kuchnie_core/schema.py::KitchenSchema` (the schema is published as Pydantic models, not a standalone `.yaml` file)
- **Introduced by:** F001

# M

## MachiningFeature
- **Context:** CAD
- **Definition:** An associative manufacturing operation on a panel — drill, groove, rabbet, notch, pocket. Defined by position formula (re-evaluated on resize), tool spec, and operation order. Survives dimension changes. Borrowed pattern from TopSolid'Wood.
- **Not to be confused with:**
  - `MachiningOp` (legacy term from `kuchnie-core/src/kuchnie_core/model.py` — to be reconciled in F004 or F008)
  - `DrillPoint` (a single drill — a `MachiningFeature` may produce many `DrillPoint`s)
- **File of record:** (planned — not yet implemented; the associative, formula-driven behavior described here does not exist. The current non-associative equivalent is `kuchnie-core/src/kuchnie_core/model.py::MachiningOp`)
- **Introduced by:** F008

## MachiningOp
- **Context:** Core (legacy)
- **Definition:** Original lightweight machining operation in `kuchnie-core/src/kuchnie_core/model.py`. Will be aligned with `MachiningFeature` or deprecated in F008.
- **File of record:** `kuchnie-core/src/kuchnie_core/model.py::MachiningOp`
- **Status:** ⚠️ legacy — see F008 ADR for resolution.

## Material
- **Context:** Web (summary), Core (by reference)
- **Definition:** UI-level summary of a board material — name, brand, price, sheet size, has_woodgrain flag.
- **Not to be confused with:** `Decor` (Catalog — the finish), `Variant` (Catalog — finish + thickness)
- **File of record:** `kitchen-erp/kitchen_erp/core/models.py::Material`

## MaterialRef
- **Context:** Core
- **Definition:** A reference (by ID) to a catalog material. Cabinet stores `MaterialRef`s for body / front / back / shelf; never the material data itself.
- **File of record:** `kuchnie-core/src/kuchnie_core/model.py::MaterialRef`
- **Introduced by:** F005

## MaterialResolver
- **Context:** Core (service)
- **Definition:** Service that translates a `MaterialRef` or `decor_id` into a `ResolvedMaterial` (texture path + edge spec + color hex + grain) by querying the Catalog.
- **File of record:** `kuchnie-core/src/kuchnie_core/materials/resolver.py::MaterialResolver`
- **Introduced by:** F005

# P

## Panel
- **Context:** Core
- **Definition:** A single rectangular piece of board with dimensions, material reference, edge banding sides, role (side / top / bottom / shelf / back / door / drawer-front), and grain direction. **The atomic manufacturing unit** — all five commercial CAD systems converge on this.
- **Not to be confused with:** `CutPiece` (the export-format representation of a Panel)
- **File of record:** `kuchnie-core/src/kuchnie_core/model.py::Panel`
- **Introduced by:** (pre-existing)

## Pairing
- **Context:** Catalog
- **Definition:** A producer-defined valid combination of `Decor` + `Edge` (e.g., Kronospan U112 PM ships with edge E-U112).
- **File of record:** `catalog/models/domain.py::PairingOut`

## Phase
- **Context:** Process
- **Definition:** A bounded time window (target: 1 week) delivering one or more features. Phase N must pass its **gate criteria** in `docs/archive/PHASES.md` before Phase N+1 starts.
- **File of record:** `docs/archive/PHASES.md`

## Project
- **Context:** Web
- **Definition:** A customer engagement — name, address, status (consultation / quote / accepted / production), and one `Kitchen`. Web-only concept; **Core does not know about Projects**.
- **File of record:** `kitchen-erp/kitchen_erp/core/models.py::Project`

## Published Language
- **Context:** Architecture (cross-context pattern)
- **Definition:** A stable, versioned format used to communicate between contexts. Two in our system:
  1. Catalog publishes stable `decor_id` / `edge_id` strings.
  2. Core publishes `kitchen_config.yaml` v1.0 schema.

# R

## Recipe
- **Context:** Core
- **Definition:** A YAML declaration of how to decompose a `CabinetTemplate` into panels — list of panels, each with dimension formulas, edge assignments, drill patterns, and material role references. Evaluated by the CAD-side `RecipeEngine`.
- **File of record:** `recipes/*.json` (data) + `kuchnie-core/src/kuchnie_core/recipe.py` (model)
- **Introduced by:** F002
- **Related ADR:** `features/archive/F002-recipe-engine/adr.md`

## RecipeEngine
- **Context:** CAD
- **Definition:** The evaluator that takes a `Recipe`, a `CabinetInstance`, and a `ConstructionMethod`, and produces a list of `Panel` with concrete dimensions. Uses a safe expression evaluator (Python's `ast` module, not `eval`).
- **File of record:** (planned — not yet wired into decomposition; the formula evaluator exists at `kuchnie-core/src/kuchnie_core/recipe.py::evaluate_formula`, used today only in tests, not called from `decomposer.py`)
- **Introduced by:** F002

## ResolvedMaterial
- **Context:** Core
- **Definition:** The output of `MaterialResolver` — concrete texture path, edge spec, color hex, grain direction, ready for use by render adapter or cut list export.
- **File of record:** `kuchnie-core/src/kuchnie_core/materials/models.py::VariantInfo` (paired with `EdgeInfo` for edge spec; no separate `ResolvedMaterial` class exists — this is the closest current equivalent)
- **Introduced by:** F005

## Row
- **Context:** Core, Web
- **Definition:** A linear sequence of cabinets along one wall in a `Kitchen`. v1.0 excludes islands and slanted walls. Has a wall reference, start position, direction, and ordered `cabinets` list.
- **File of record:** `kuchnie-core/src/kuchnie_core/model.py::Row`
- **Introduced by:** (pre-existing)

## RowPlacement
- **Context:** Core, Web
- **Definition:** Cabinet position expressed as `(row_id, slot_index)`. The web app's coordinate model. Converted to `WallPlacement` by the render adapter.
- **File of record:** (planned — not yet implemented)
- **Introduced by:** F007

# S

## Scene
- **Context:** Render
- **Definition:** A Blender scene generated by the render adapter from a `kitchen_config.yaml`. Contains walls, placed cabinets with materials, lights, camera. Rendered to PNG.
- **File of record:** (planned — not yet implemented; would live in `home-builder-adapter/`, renamed per ADR-009)

## SubAssembly
- **Context:** Core
- **Definition:** A composable group inside a `CabinetInstance` — a drawer box, a door pair, a shelf bank, a cargo unit. Holds its own panels and accessories. Borrowed pattern from Winner Flex.
- **File of record:** `kuchnie-core/src/kuchnie_core/model.py::SubAssembly`
- **Introduced by:** F001 (refactored into existing model)

# T

## Template (see CabinetTemplate)
- Ambiguous alone. In this repo, "template" usually means `CabinetTemplate`. Process templates (`features/TEMPLATE/`) are called "feature template" explicitly.

## Texture
- **Context:** Render
- **Definition:** An image file (jpg/png) representing a `Decor`'s surface, loaded by Blender materials. Path stored in catalog and resolved by `MaterialResolver`.
- **File of record:** `catalog/public/producers/kronospan/decors/` (per-producer layout; other producers not yet added)

# U

## Ubiquitous Language
- **Context:** Process
- **Definition:** The vocabulary used consistently within a bounded context. This entire file is the canonical record. Borrowed from DDD.
- **File of record:** `docs/GLOSSARY.md` (you are here)

# V

## ValidationGate
- **Context:** Core
- **Definition:** A check that runs at a specific stage. Four gates exist: Cabinet (1), Row (2), Kitchen (3), CAMReadiness (4). Each app calls the gates relevant to its stage.
- **File of record:** (planned — not yet implemented as a four-gate pipeline; `kuchnie-core/src/kuchnie_core/validator.py` implements manifest-level checks today)
- **Introduced by:** F004

## ValidationResult
- **Context:** Core
- **Definition:** Output of a gate — list of issues (errors + warnings), each with a code, message, and affected entity ID. Truthy if no errors.
- **File of record:** `kuchnie-core/src/kuchnie_core/validator.py::ValidationResult`
- **Introduced by:** F004

## Variant
- **Context:** Catalog
- **Definition:** A specific combination of `Decor` + thickness + format (e.g., "U112 PM, 18mm, 2800×2070"). Carries the SKU and price.
- **File of record:** `catalog/models/domain.py::VariantOut`

# W

## WallPlacement
- **Context:** Render
- **Definition:** Cabinet position expressed as `(wall_id, offset_along_wall_mm, rotation_rad)`. The render adapter's coordinate model. Converted from `RowPlacement`.
- **File of record:** (planned — not yet implemented)
- **Introduced by:** F007

## WorktopSegment
- **Context:** Core
- **Definition:** A piece of countertop covering one or more adjacent base cabinets. Has length, depth, thickness, material reference, joints, cutouts (sink, hob).
- **File of record:** `kuchnie-core/src/kuchnie_core/model.py::WorktopSegment`
- **Introduced by:** (pre-existing)

---

## Update Protocol

When you introduce a new domain class or concept in code:

1. Add an entry above using the standard format.
2. Cross-reference its **bounded context**, **file of record**, and **introducing feature**.
3. Add "Not to be confused with" lines for any near-collisions.
4. Commit glossary + code in the same commit.
5. If the term replaces a legacy one, mark the old entry as `Status: ⚠️ legacy` and link to the new term.

When you read code and find a term **not in this glossary**: stop. Add it before continuing, or flag it to the user.
