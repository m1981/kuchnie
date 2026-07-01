# ADR-009: Kitchen-plugin becomes home-builder-adapter

## Status

Accepted 2026-07-01

## Context

`kitchen-plugin/` began life (pre-June 29) as a standalone headless Blender kitchen
generator: config JSON → `LayoutEngine` → `CabinetGeometry` → bpy geometry → manifest
export. 4,523 LOC, 23 test files, layered DDD architecture.

Its role oscillated three times in a single day:

1. **Commit `6bc1451` (2026-06-29 11:52)** — F001–F008 planning docs treated it as
   legacy. Future rebuild proposed in new packages (`kitchen-cad/`, `kitchen-render/`).
2. **Commit `288e0e4` (2026-06-29 12:46)** — `06_kitchen_plugin_discovery.md`
   rediscovered it as "our most mature subsystem, 60–70% of F001–F008 already
   implemented here." `07_integration_plan.md` proposed **Option A: adopt as
   foundation.**
3. **Commit `878ccb3` (2026-06-30 00:21)** — `00-brief2.md` introduced
   `home_builder_5` — a **licensed, third-party, commercial Blender addon** at
   `/Users/michal/PycharmProjects/home_builder_5` — for interactive kitchen layout.
   Rationale (user's own words): *"I'm not good in GUI."* F007 ADR added Rule 4:
   `home_builder_5/` is external, untouched.

No commit after `878ccb3` resolved the resulting overlap. `kitchen-plugin` and
`home_builder_5` both perform interactive-layout + cabinet-geometry building in
Blender. `kitchen-plugin` was left in limbo.

### What `home_builder_5` provides (per `COLD-REVIEW-HOME-BUILDER-5.md`)

Blender scene tree with custom properties:

- `IS_FRAMELESS_CABINET_CAGE`, `IS_FRAMELESS_BAY_CAGE`, `IS_FRAMELESS_OPENING_CAGE`
- `CABINET_TYPE` ∈ {BASE, TALL, UPPER}
- `Dim X`, `Dim Y`, `Dim Z` (width/depth/height in meters)
- `Toe Kick Height`
- `opening_sizes` (drawer stack heights)
- `Cabinet Part Name` (partial material code)

This is **basic geometry + typology only**. It does **not** encode:

- Construction method (dowel/cam-lock/groove; 18/22mm)
- Blum drawer system codes (LEGRABOX C/M/N, Tandembox, Merivobox)
- Blum hinge model (ClipTop 110°/95°/155°, overlay)
- Kronospan/Egger decor codes + material role (front/carcass/back/worktop)
- Edge banding assignment
- Grain direction
- Machining features (System32 shelf pins, LED grooves, vent holes)
- Cost data
- CNC output constraints (e-rozkroj CSV, DXF layers)

Roughly **80% of the domain data the pipeline needs is invisible to `home_builder_5`**.
It replaces the GUI + basic geometry. It does not replace the domain.

### Non-negotiable architectural constraint

`kuchnie_core` must remain **pure Python** (Pydantic + PyYAML only, no `bpy`). It is
consumed by `catalog/`, `kitchen-app`, `krono-compositor-mvp`, CAM tools, and tests —
none of which want a 500 MB Blender dependency.

## Decision

**Rename `kitchen-plugin/` → `home-builder-adapter/`.**

Apply the **Ports & Adapters (Hexagonal)** pattern already used successfully in
`krono-compositor-mvp/`:

- **Pure domain code** (no `bpy`) → migrates into `kuchnie_core/`.
- **Adapter code** (`bpy` required) → stays in the renamed package, reduced to ~500 LOC.

```
┌────────────────────────────────────────────────────────────────┐
│                    kuchnie_core (pure)                         │
│  Kitchen · Row · CabinetInstance · Panel · ConstructionMethod  │
│  Standards · Validator · Serialize · BOM                       │
│  Pure Python. No bpy. Consumed by all downstream components.   │
└──────────────▲─────────────────────────────────▲───────────────┘
               │ imports                          │ imports
               │                                  │
┌──────────────┴──────────────┐    ┌──────────────┴──────────────┐
│  home-builder-adapter/       │    │  kitchen-app / catalog /    │
│  (bpy required)              │    │  krono-compositor-mvp       │
│                              │    │                             │
│  Walks .blend scene tree  →  │    │  Read/write Kitchen via     │
│  produces kuchnie_core.      │    │  HTTP, DB, files            │
│  Kitchen. Runs validator.    │    │                             │
└──────────────────────────────┘    └─────────────────────────────┘
```

### Migration mapping

| From (kitchen-plugin) | To | Rationale |
|---|---|---|
| `src/core/geometry.py` | `kuchnie_core/geometry.py` | Vector2D/3D, BoundingBox, Transform2D — pure math primitives |
| `src/kitchen/standards.py` | `kuchnie_core/standards.py` | European 32mm-system standards, 900mm walkway clearance |
| `src/kitchen/cabinet_geometry.py` | Merge into `kuchnie_core/construction.py` | Construction math (18/19/3mm defaults, groove offsets, overlays) becomes the concrete implementation of `ConstructionMethod` |
| `src/manifest_validator.py` | `kuchnie_core/validator.py` | Dimension/overlap/clearance/run-continuity validation |
| `tests/test_p*_*.py` (pure) | `tests/kuchnie_core/` | Preserve validation IP (23 test files' worth) |
| `src/geometry_manifest.py` (schema) | Reference `kuchnie_core` schema | Schema of adapter output aligns with canonical intermediate format |

### Code that dies

| File | Reason |
|---|---|
| `src/geometry_builder.py` | `home_builder_5` builds geometry |
| `src/wall_builder.py`, `src/kitchen/wall.py`, `src/kitchen/cabinet.py`, `src/kitchen/layout.py` | `home_builder_5` owns walls, rooms, layout |
| `src/config_parser.py`, `src/validators.py` (config-level) | Input is a Blender scene, not JSON |
| `src/material_manager.py` | RGB Cycles colors; `krono-compositor-mvp` handles textures via decor codes |
| `src/exporters.py::render_wireframe` | Rendering lives in `krono-compositor-mvp` |
| `src/main.py --export-blend / --render-wireframe` flags | Adapter is extract-only |

### Code that stays (renamed package)

- `src/extract.py` (**new**) — walks `IS_FRAMELESS_*_CAGE` tree, converts m→mm,
  produces `kuchnie_core.Kitchen`
- `src/cli.py` (**new**) — `home-builder-adapter path/to/scene.blend > kitchen.json`
- `pyproject.toml` — declares `bpy` as the only heavy dependency; depends on
  `kuchnie_core`

Net result: **~70% of current LOC deleted, ~30% migrated, ~500 LOC of new adapter code.**

## Consequences

**Positive**

- `kuchnie_core` stays `bpy`-free — everyone downstream can import it cheaply.
- Domain IP (construction math, validation rules, standards) survives regardless of
  `home_builder_5` licensing changes.
- Adapter is small (~500 LOC) — replaceable if we ever switch tools (Sketchup, native
  Blender, custom GUI).
- Consistent with the Hexagonal pattern already proven in `krono-compositor-mvp/`.
- `home_builder_5`'s vocabulary (`IS_FRAMELESS_CABINET_CAGE`, `CABINET_TYPE`,
  `opening_sizes`) never leaks into the domain (Anti-Corruption Layer).

**Negative**

- One-time migration effort (~1 focused week with LLM assistance).
- `home_builder_5`'s data model dictates what the adapter can extract; the
  "missing 80%" (hardware, decors, machining, construction method) must be added
  by a downstream enrichment step. **This is the scope of a follow-up ADR
  covering `kitchen-app`'s role.**
- Renaming will invalidate historical import paths in archived docs (acceptable —
  they live in `docs/archive/`).

**Neutral (deferred)**

- The relationship between the adapter output and `kitchen-cad`'s Pydantic panel
  configs is out of scope here; that duplication is addressed in a separate ADR.

## Alternatives considered

**Option 2: Merge kitchen-plugin's entire code into `kuchnie_core`.**
Rejected because `bpy` is a poisonous dependency. Contaminating `kuchnie_core`
would force Blender installation on all downstream consumers (`catalog/`,
`kitchen-app`, CI, tests) and add 500 MB to every deployment. Conditional imports
would work but are fragile.

**Option 3: Delete kitchen-plugin entirely.**
Rejected because it discards real domain IP: the 900mm walkway rule, standard
width validation, European frameless construction math (18/19/3mm defaults,
groove offsets, overlays), and 23 test files encoding edge cases already
discovered and fixed. Saving ~500 LOC of adapter code at the cost of throwing
away validated domain knowledge is a bad trade.

**Option 4: Keep both `kitchen-plugin` and `home_builder_5` as parallel paths
(fallback / resilience).**
Rejected because a solo developer cannot maintain two parallel implementations of
the same responsibility. Every additional maintenance surface rots. If
`home_builder_5` access is ever lost, a replacement adapter (~500 LOC) can be
written in ~1 week — the domain code will still be in `kuchnie_core`. That is
the real insurance policy.

## References

- Brief: `docs/00-brief-understanding.md`, `git show 878ccb3:docs/00-brief2.md`
- Discovery: `docs/archive/06_kitchen_plugin_discovery.md`
- Integration plan (superseded by this ADR): `docs/archive/07_integration_plan.md`
- Home Builder data model: `docs/archive/COLD-REVIEW-HOME-BUILDER-5.md`
- Pattern precedent: `krono-compositor-mvp/docs/architecture.md`
  (Clean Architecture / DDD layers)
- Related ADRs:
  - ADR-001 (Panel is the atomic unit) — reinforced; the adapter emits `Kitchen`
    with panel-atomic decomposition applied downstream.
  - ADR-002 (Construction method separate from cabinet instance) — the migrated
    `cabinet_geometry.py` becomes the concrete implementation.
  - ADR-004 (Intermediate format is logical) — `kuchnie_core.Kitchen` is the
    single canonical intermediate format; the adapter conforms to it.
