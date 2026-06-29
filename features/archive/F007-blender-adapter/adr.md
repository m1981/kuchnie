# ADR — F007 — Standalone Headless Blender Renderer, `home_builder_5/` Untouched

**Date:** 2026-06-28
**Status:** `Proposed`
**Feature:** F007
**Author:** solo dev

---

## Context

`docs/03_implementation_placement.md` § "What goes INTO the Blender plugin (extensions)" prescribed minimal extensions to "the Blender plugin": adding `config_parser.py` schema bump, texture path resolution, and a headless render entry-point. That guidance was written based on analysis of a `kitchen-plugin/` directory from `/Users/michal/PycharmProjects/kuchnie/kitchen-plugin/` — a different project containing a small, headless-capable Python renderer.

The **actual** target plugin in this repository is `home_builder_5/` (`/Users/michal/PycharmProjects/home_builder_5/`). A direct inspection of its `__init__.py` and `all.md` reveals:

- **~50,000 lines of code** across operators, UI panels, property groups, geometry-node wrappers, asset libraries, layout views, and product libraries (`face_frame`, `frameless`, `closets`, `common`).
- **Fully interactive**: every entry point is a `bpy.types.Operator` invoked from the UI (`HOME_BUILDER_OT_*`, `home_builder_walls_OT_*`, etc.), expecting modal context, mouse events, keyboard input.
- **No `config_parser.py`**, **no `kitchen_config.yaml` consumer**, **no documented headless mode**, **no `main()` entry that builds a kitchen from data**.
- **Heavy reliance on Blender's Property Groups** (`bpy.types.Scene.home_builder`, etc.) — state lives on the Blender scene, not in plain Python.
- **Driver-driven geometry nodes**: cabinets are GeoNode-modified objects whose dimensions are bound to scene/object properties via Blender's driver system.

Forcing this codebase to run headlessly would mean: scripting modal operators (which often fail without UI context), manipulating bpy property groups from scripts, working around driver evaluation timing, and likely forking the addon to remove modal-only paths. For a solo developer, this is a multi-week sink with high regression risk.

Meanwhile, what F007 actually needs is **a closed-cabinet preview render** — boxes with textures, sensible lighting, a few camera angles. This is `bpy` mesh primitives, image texture nodes, a camera, and a sun light. A few hundred lines of code.

The decision needs to be made **now** because: (1) F006 (Web Sidebar) will shell out to `kitchen-cli render`; the contract has to be stable; (2) F008 (CLI) shares the same CLI entry point; coordination requires the render path to be known; (3) the architectural pivot away from the earlier "extend the plugin" prescription needs to be documented before LLM sessions act on the older guidance.

---

## Decision

We will introduce **`kitchen-render/`** as a new bounded context — a standalone Blender-Python renderer that:

1. Reads a `Kitchen` (Core), validates via F004 Gate 3, calls F005's `MaterialResolver` per panel role, and builds a Blender scene using **pure `bpy` mesh primitives**.
2. Invokes Blender as a **subprocess** (`blender --background --factory-startup --python blender_entry.py -- ...`). Not via `pip install bpy`.
3. Renders to PNG using **Eevee** by default (fast preview); Cycles available as opt-in.
4. Saves a `.blend` file as a free side effect — the carpenter can open it in Blender (optionally with `home_builder_5/` enabled) for manual tweaking.
5. Ships **three presets**: `front_view`, `perspective`, `plan` — each a YAML defining camera, lighting, resolution, engine.
6. Has a **derived-wall** model — walls are inferred from rows; no explicit room geometry in v1.0.
7. Uses **closed-cabinet geometry** — corpus box + visible front panel boxes + worktop + plinth. No interior, no open doors, no handles.

`home_builder_5/` is **not touched**. F007 does not import from it, does not drive its operators, does not use its geometry-node types or property groups. The addon remains useful to the carpenter for manual scene editing after F007 produces a `.blend` — this is the only intersection.

The `kitchen-render/` package layout, the CLI subcommand (`kitchen-cli render`), the preset YAML schema, and the `RowPlacement` → `WallPlacement` converter become the published surface of this bounded context.

The reference in `docs/03_implementation_placement.md` to "extending the Blender plugin's `config_parser.py`" is superseded by this ADR. That document will be updated in the close-out commit to point here.

---

## Alternatives Considered

| Option | Why rejected |
|---|---|
| **A. Drive `home_builder_5/` operators headlessly via `bpy.ops.home_builder_walls_OT_draw_walls(...)` etc.** | Modal operators expect mouse/keyboard events and an active 3D viewport. Many simply fail outside UI context. The few that work require extensive workarounds and break on every plugin version bump. Multi-week effort, high regression risk. |
| **B. Use `pip install bpy` and run in-process** | The `bpy` PyPI package is ~1GB, pinned to a specific Blender build, and conflicts with the installed Blender. Cross-platform support is patchy. Subprocess invocation is the industry-standard pattern for headless Blender work. |
| **C. Extend `home_builder_5/` with a `config_parser.py` and headless entry point** | The earlier `03_implementation_placement.md` prescription. Was written for a different (simpler) plugin. Applied to `home_builder_5/` it means forking a 50K-LOC interactive addon. Cost wildly disproportionate to value (a closed-box preview). |
| **D. Use `home_builder_5/`'s `GeoNode*` types from `hb_types.py` without invoking operators** | Would couple our renderer to plugin internals. Plugin maintainers can rename or restructure these freely; we'd be on a permanent breakage treadmill. |
| **E. Use a non-Blender renderer (PyRender, Mitsuba, Three.js server-side, USD Hydra)** | Blender is already installed for the carpenter's workflow. Adding another renderer means another install, another texture pipeline, another debugging surface. Blender's bpy is sufficient and familiar. |
| **F. Build a web-based WebGL viewer** (Three.js, model-viewer, online preview) | Out of scope for v1.0. Carpenter wants a PNG to send to customer; a web viewer requires hosting and is a different feature class. |
| **G. Use Blender's `gltf` / USD export as the renderer's output** (no PNG) | Customer needs a flat image to look at on a phone. 3D output is a Could (AR preview). |
| **H. Use Cycles by default** | 5-30× slower than Eevee for kitchen scenes. Customer preview doesn't need photorealism. Cycles is opt-in via `--engine cycles`. |
| **I. Render asynchronously / in parallel for multiple presets** | Solo dev workflow; 18-second render is fine. Parallel renders compete for the same Blender process anyway. |
| **J. Cache renders keyed by kitchen hash** | Re-rendering is cheap (seconds); cache invalidation needs to track all transitive inputs (decor texture changes, preset changes, gate output). Not worth the complexity. |
| **K. Use procedural materials** (port `home_builder_5/`'s `wood_materials.py` shader graphs) | F005 already publishes texture paths; F007 just sets the texture on a Principled BSDF. Procedural shaders are slower to set up and harder to match Kronospan's actual decor appearance. Texture lookups win. |
| **L. Render open-door / open-drawer variants in default presets** | Adds geometry complexity (door pivots, drawer slide positions) and another animation layer. Backlog — useful for some customer presentations but not v1.0 minimum. |
| **M. Detailed handle modeling** | Handle catalog and CAD data are post-v1.0. Cabinets render flush (handleless) — clean, modern aesthetic that doesn't lie about what we'll manufacture. |
| **N. Multi-room scenes** ("show me kitchen + bath together") | v1.0 = one kitchen per render. Multi-room is a different domain concept. |
| **O. Live preview (server watches YAML, re-renders on change)** | File watchers, hot-reload, render queue — significant infra for a workflow that takes 18 seconds per render. Not worth it for solo dev. |
| **P. Render entry-point as a separate CLI binary** (not a subcommand of `kitchen-cli`) | One binary is easier to install and remember. `kitchen-cli render`, `kitchen-cli cut-list`, `kitchen-cli dxf` share a common surface and naming. |
| **Q. Validation Gate runs inside Blender subprocess** | Validation is fast and self-contained; running it before subprocess spawn lets us exit early on ERROR without paying Blender's startup cost (~3s). |
| **R. Render adapter inside `kitchen-cad/`** (don't create new package) | Mixes manufacturing and rendering concerns. `kitchen-cad/` deals with cuts and drills; `kitchen-render/` deals with images. Separation makes both packages easier to reason about. |
| **S. Render adapter inside `src/kuchnie_core/`** | Core stays pure-Python with no Blender dependency. Even an optional `bpy` import would pollute Core's import graph. Strict separation. |
| **T. Make geometry exact to F002 recipes** (every panel rendered as a separate object) | Useful for "exploded view" mode — backlog. v1.0 renders cabinets as visual blocks, not panel-by-panel. Render is a customer-facing image, not a fabrication preview. |
| **U. Multiple output formats** (PNG, JPG, EXR) | PNG only in v1.0. Format conversion is a separate utility. |
| **V. Embed kitchen YAML inside the `.blend` file** | Round-trip editing means `.blend` becomes a second truth alongside YAML. One-way pipeline (YAML → .blend) is simpler. Backlog if a "tweak in Blender, re-export to YAML" workflow is ever needed. |

---

## Consequences

### Positive
- **`home_builder_5/` stays untouched.** No fork, no compatibility burden, no upgrade risk. Rule 4 holds.
- **F007 scope is bounded** — a few hundred lines of `bpy` mesh + materials + camera code. Implementable in 5–7 days.
- **Subprocess boundary is testable.** Outer Python is unit-testable without Blender; smoke test invokes Blender once.
- **Carpenter's manual workflow is preserved.** Saved `.blend` opens cleanly in Blender; carpenter can enable `home_builder_5/` for further editing.
- **No leakage between bounded contexts.** Render adapter consumes Core's published API; never writes back.
- **Predictable render time.** Eevee scenes complete in 10–30 seconds; carpenter knows what to expect.
- **Same `kitchen-cli` binary for render and CAM export** — one tool, multiple subcommands, single install.

### Negative
- **Two visual styles coexist** — our renderer's output vs `home_builder_5/`'s output if carpenter later opens the addon and uses its tools. Materials may not match exactly between the two. Mitigated by clearly documenting that `home_builder_5/` is a "manual editing tool" not the authoritative renderer.
- **Wall geometry is derived (not declared)** — limits creative room layouts. Acceptable for v1.0's rectangular-room use case; backlog for complex rooms.
- **Subprocess invocation has Blender-locator complexity** — `$BLENDER_PATH`, `which blender`, version check. Edge cases on Windows and macOS Homebrew installs. Documented in README.
- **The earlier `03_implementation_placement.md` guidance is now stale** — must be updated in the close-out commit to reference this ADR.

### Neutral
- **Cabinets render as closed boxes** — accurate to manufacturing reality, but less "showroom-y" than open-cabinet displays. Most kitchen designers present closed cabinets to customers anyway.
- **Edge banding invisible at preview scale** — true to physical reality at preview resolution.
- **Blender becomes a hard runtime dependency** for the render path (not for cut-list / DXF). Documented in install instructions.
- **The .blend output is provided "as is"** — carpenter can edit but our renderer doesn't validate edits. One-way pipeline.

---

## Affected Files (canonical)

### Created
- `kitchen-render/` — new package root
- `kitchen-render/README.md`
- `kitchen-render/pyproject.toml` (or equivalent)
- `kitchen-render/src/kitchen_render/__init__.py`
- `kitchen-render/src/kitchen_render/cli.py` — outer CLI (subprocess spawner)
- `kitchen-render/src/kitchen_render/blender_entry.py` — runs inside Blender
- `kitchen-render/src/kitchen_render/scene_builder.py`
- `kitchen-render/src/kitchen_render/geometry.py`
- `kitchen-render/src/kitchen_render/materials.py`
- `kitchen-render/src/kitchen_render/placement.py` — `RowPlacement` → `WallPlacement`
- `kitchen-render/src/kitchen_render/lighting.py`
- `kitchen-render/src/kitchen_render/camera.py`
- `kitchen-render/src/kitchen_render/presets.py`
- `kitchen-render/src/kitchen_render/blender_locator.py`
- `kitchen-render/presets/front_view.yaml`
- `kitchen-render/presets/perspective.yaml`
- `kitchen-render/presets/plan.yaml`
- `tests/render/test_placement.py`
- `tests/render/test_presets.py`
- `tests/render/test_cli.py`
- `tests/render/test_blender_detection.py`
- `tests/render/integration/test_smoke_render.py`
- `docs/rendering.md`

### Modified
- `docs/GLOSSARY.md` — 8 new/refined entries
- `docs/01_architecture.md` — Context Map adds `kitchen-render/` bounded context with arrow to Blender subprocess
- `docs/03_implementation_placement.md` — Update the "What goes INTO the Blender plugin (extensions)" section to reference this ADR and the pivot
- `docs/PHASES.md` — Phase 7 gate criteria updated ("plugin loaded headless" → "kitchen-render produces PNG via Blender subprocess")
- `kitchen-cli` entry point gains `render` subcommand (coordinate with F008 which owns the entry point)

### Deleted or stubbed
- None. `home_builder_5/` is untouched.

### Verified untouched
- Every file under `home_builder_5/` (except `home_builder_5/docs/` and `home_builder_5/features/` which house our planning artifacts and are unrelated to the plugin itself).

---

## LLM Hints

> Direct instructions for future LLM sessions in this decision area.

- **When asked "should we drive `home_builder_5/` operators?"** → **No.** Modal operators don't work headlessly. The addon is interactive-only. See Alternative A.
- **When asked "should we use `pip install bpy`?"** → **No.** Subprocess invocation is the boundary. See Alternative B.
- **When asked "should we modify `home_builder_5/` to add a headless mode?"** → **No.** 50K-LOC interactive addon. The earlier `03_implementation_placement.md` guidance about extending the plugin was for a different project. See Alternative C.
- **When asked "should we use plugin's GeoNode types?"** → **No.** Tight coupling to plugin internals. See Alternative D.
- **When asked "where does the render adapter live?"** → `kitchen-render/` — a new bounded context, sibling to `kitchen-cad/`, `kitchen-app/`, `catalog/`. See Alternative R.
- **When asked "should rendering live in `kuchnie_core/`?"** → **No.** Core stays pure Python, no Blender import. See Alternative S.
- **When asked "Eevee or Cycles?"** → **Eevee by default.** Cycles via `--engine cycles` for opt-in photoreal. See Alternative H.
- **When asked "should we cache renders?"** → **No.** Re-render is cheap; cache invalidation is hard. See Alternative J.
- **When asked "can we render open doors / drawers?"** → Not in v1.0. Backlog. Closed cabinets is the visual default. See Alternative L.
- **When asked "should we detail handles?"** → Not in v1.0. Flush handleless render. See Alternative M.
- **When asked "should we render the room (walls, floor, ceiling) in detail?"** → Walls derived from rows, floor as flat plane. No ceiling. v1.0 minimum. Complex rooms are backlog.
- **When asked "should the .blend file be the source of truth?"** → **No.** YAML is the truth. `.blend` is a one-way render artifact. See Alternative V.
- **When asked "should rendering be a separate CLI binary?"** → **No.** `kitchen-cli render` subcommand. Coordinate with F008. See Alternative P.
- **When asked "should the render adapter validate the kitchen?"** → It calls F004's Gate 3. Does not implement its own validation. See Alternative Q.
- **When asked "should we render in parallel?"** → **No.** Sync subprocess. See Alternative I.
- **When asked "can the carpenter open the .blend and edit, then re-export YAML?"** → Not supported in v1.0. One-way pipeline. Backlog if requested.
- **When asked "should we support multi-room kitchens?"** → Not in v1.0. One `Kitchen` per render. See Alternative N.
- **When asked "should we model edge banding visually?"** → No. Too small to see at preview resolution.
- **When asked "where do textures come from?"** → F005's `ResolvedMaterial.texture_path`. Adapter loads via `bpy.data.images.load()`. Never inline a procedural shader. See Alternative K.
- **Do not propose:**
  - Modifying any file in `home_builder_5/` (the addon itself).
  - Adding `home_builder_5/` as a dependency of `kitchen-render/`.
  - Importing `bpy` at the top of `cli.py` (only `blender_entry.py` runs inside Blender).
  - Embedding kitchen YAML inside the .blend file.
  - HTTP/web rendering server.
  - Real-time preview / hot-reload.
  - Render farms or cloud rendering.
- **Related ADRs:**
  - **F001 (Construction Method)** — adapter reads `ConstructionMethod` for plinth height, front overlay, gap dimensions, worktop thickness.
  - **F003 (Template Registry)** — adapter doesn't need templates directly; cabinet dimensions and sub-assemblies are already on `CabinetInstance`.
  - **F004 (Validation Gates)** — Gate 3 (Kitchen) runs in outer CLI before subprocess spawn. ERROR refuses to render.
  - **F005 (Material Resolver)** — adapter calls `resolver.resolve_role()` per panel role; loads texture from `texture_path`. Core invariant: no decor data in adapter code; only resolved data.
  - **F006 (Web Sidebar)** — may shell out to `kitchen-cli render` to populate a preview. F006's UX decision.
  - **F008 (CLI Cut List / DXF)** — owns the `kitchen-cli` entry point; F007 contributes the `render` subcommand.

---

## Sign-off

- [ ] `docs/GLOSSARY.md` updated with 8 entries.
- [ ] `docs/03_implementation_placement.md` "What goes INTO the Blender plugin" section updated with pointer to this ADR.
- [ ] `docs/PHASES.md` Phase 7 gate criteria updated.
- [ ] `kitchen-render/` package created with all listed modules.
- [ ] Three presets shipped: `front_view`, `perspective`, `plan`.
- [ ] `examples/kitchen_nowak.yaml` renders successfully with each preset.
- [ ] Unit tests pass without Blender installed.
- [ ] Smoke test (`pytest -m blender`) passes with Blender installed.
- [ ] `git diff --stat home_builder_5/__init__.py` returns no changes in this feature's diff (excluding `home_builder_5/docs/` and `home_builder_5/features/` which house planning artifacts).
- [ ] `kitchen-cli render` subcommand integrated with F008's CLI entry point (or scaffolded for it).
- [ ] Status moved from `Proposed` → `Accepted` after first green smoke render produces a valid PNG and `.blend`.
