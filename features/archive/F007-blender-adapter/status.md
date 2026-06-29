# Status — F007

> **Machine-readable.** Agents can grep all `status.md` files to build a dashboard.

```yaml
feature_id: F007
title: "Blender Render Adapter (Headless PNG + .blend Generation)"
status: proposed                  # not started — Phase 7 begins after F006 closes
phase: 7
primary_context: render           # NEW bounded context introduced by F007
                                  # Code location: kitchen-render/
                                  # Not to be confused with home_builder_5/ (the untouched plugin)
touched_contexts:
  - render                        # owns the adapter, presets, CLI subcommand

started: null
completed: null
blocked_by:
  - F001                          # geometry reads ConstructionMethod
  - F004                          # Gate 3 validates kitchen before render
  - F005                          # MaterialResolver provides texture paths
supersedes:
  - "docs/03_implementation_placement.md § 'What goes INTO the Blender plugin (extensions)'"
  # That section prescribed extending the plugin's config_parser.py.
  # F007 ADR Alternative A documents why this no longer applies to home_builder_5.
  # The section will be updated in F007's implementation close-out.
superseded_by: null

spec_status: ready                # all 15 Open Questions in spec.md answered
adr_status: proposed              # accepted on first green smoke render

adr_needed: true                  # yes — major architectural pivot (drop driving the plugin)

architectural_pivot:
  what: "Do not extend or drive home_builder_5/. Build a standalone bpy renderer."
  why_now: "Direct inspection of home_builder_5/__init__.py confirms it is fully interactive (no headless API). Earlier guidance in 03_implementation_placement.md referenced a different plugin."
  reverses: "docs/03_implementation_placement.md § 'What goes INTO the Blender plugin (extensions)'"
  documented_in: "features/F007-blender-adapter/adr.md § Decision + § Alternative A"

glossary_terms_introduced:
  - Scene                         # promote placeholder → concrete
  - WallPlacement                 # promote placeholder → concrete
  - RowPlacement                  # promote placeholder → concrete
  - Texture                       # promote placeholder → concrete
  - RenderPreset                  # new
  - RenderResult                  # new
  - BlenderEntry                  # new (the inside-Blender script)
  - SceneBuilder                  # new

new_bounded_context_created:
  name: render
  code_location: kitchen-render/
  parent_dependencies:
    - kuchnie_core                # reads Kitchen, CabinetInstance, ResolvedMaterial
  external_runtime_dependencies:
    - "Blender ≥ 3.6 LTS (subprocess)"
  does_not_depend_on:
    - home_builder_5              # explicitly untouched per Rule 4 and ADR

last_updated: 2026-06-28
last_updated_commit: "bootstrap"
```

---

## Current Activity

**Not started.** Blocked on F001 + F004 + F005 close (Phases 1, 4, 5 gates).

> Note: F002 (Recipe Engine) is **not** a blocker for F007 because v1.0 renders cabinets as visual blocks (using `CabinetInstance.width_mm` etc.) rather than panel-by-panel. A future "exploded view" preset could consume F002 panels; that's backlog.
>
> F003 (Template Registry) is also not a blocker — the renderer reads `CabinetInstance` directly, regardless of how the instance was created.
>
> F006 (Web Sidebar) is a downstream consumer, not a blocker.

When all three direct blockers close (Phase 5 gate passed), promote this feature's status to `in_progress` and write `tasks.md`. Spec and ADR are complete and reviewed.

---

## Blockers

- **F001 — Construction Method.** Geometry uses `plinth_height_mm`, `front_overlay_mm`, `front_gap_mm`, `worktop_thickness_mm` from the project's `ConstructionMethod`. Build won't be correct without it.
- **F004 — Validation Gates.** Outer CLI runs Gate 3 (`KitchenValidationGate`) before spawning Blender. Refuses to render on ERROR.
- **F005 — Material Resolver.** Adapter calls `resolver.resolve_role()` per panel; loads texture from `ResolvedMaterial.texture_path`. Without F005, every panel would need hand-resolved decor data — defeats the architecture.

---

## Critical Decisions Embedded in F007

> Future LLM sessions should treat these as locked, not topics to revisit.

| Decision | Locked in by |
|---|---|
| `home_builder_5/` is not modified, driven, or imported | ADR Alternative A, D |
| Subprocess invocation (not `pip install bpy`) | ADR Alternative B |
| New bounded context `kitchen-render/` | ADR Decision + Alternative R |
| Eevee default, Cycles opt-in | ADR Alternative H |
| Closed-cabinet geometry (no open doors, no interior) | Spec Won't list + ADR Alternative L |
| Walls derived from rows (no explicit room geometry in v1.0) | Spec Q12 + Open Q12 |
| `.blend` file is one-way output (not a round-trip source) | ADR Alternative V |
| `kitchen-cli render` shares the CLI binary with F008 | ADR Alternative P + Spec Q14 |

---

## Decision Log (in-flight)

> Promote to ADR if any decision affects more than this feature.

- _(empty until work starts)_
