# Krono Compositor Discovery — UC1 Was Already Solved

> **Short answer to your question:** Yes, 2.5D rendering exists. It's the entire `krono-compositor-mvp/` subsystem — a production-ready, layered, tested real-time compositor that solves UC1 at **~500ms per material swap**, not the 5–30s I assumed in doc 08.
>
> **Seam A was a phantom concern.** The previous architectural diagram described "subprocess to kitchen-plugin per render request" — wrong. Reality: **two-phase render** (heavy Blender pass once, light OpenCV composite per swap).
>
> **Option A agreement holds and gets stronger:** the integration plan was already correct (adopt existing working code instead of building new). But we need to add krono-compositor-mvp as a 6th bounded context, and resolve **two new deduplications** the planning missed.

---

## 1. What krono-compositor-mvp Actually Is

A **two-phase 2.5D real-time image compositor** with a complete clean-architecture implementation:

```
Phase 1 — OFFLINE (once per scene + camera angle, ~30-60s in Blender)
═════════════════════════════════════════════════════════════════════
gen_kitchen.py reads layout.json
  → builds 3D kitchen scene in Blender (Cycles)
  → renders 5 distinct passes:
      • base_pass.png     (782K) — diffuse + AO + shadows, no textures
      • uv_pass.exr       (5.3M) — 32-bit float UV coordinates per pixel
      • id_mask.png       (176K) — hex-color masks: which pixel = which zone
      • reflection_pass.png (945K) — specular reflections layer
      • handle_pass.png   (446K) — RGBA with handle shadows
  → also saves kitchen_scene.blend for editing
  → ~7MB per scene angle, cached on disk

Phase 2 — ONLINE (per HTTP request, ~300-500ms in OpenCV)
═════════════════════════════════════════════════════════════════════
POST /api/v1/render { scene_id, angle_id, zones: [{mask_color, texture_id, zone_type}] }
  → SceneCompositor reads cached 5 passes
  → for each zone:
      • read texture JPEG (from assets/textures/)
      • tile at physical UV scale (1.0 unit = 1000mm)
      • cv2.remap via uv_pass (BORDER_WRAP)
      • cv2.inRange mask extraction (±5 tolerance)
      • multiply blend (texture × base shadows)
  → screen blend reflections (if provided)
  → alpha composite handles (if provided)
  → SSAA downscale (50%, INTER_AREA → smooth edges)
  → return JPEG bytes
```

### Code Footprint

```
krono-compositor-mvp/
├── gen_kitchen.py        446 LOC  — Blender 5-pass renderer
├── main.py                ~30 LOC  — FastAPI entry point
├── layout.json           ~50 LOC  — scene definition input
└── src/compositor/
    ├── domain/interfaces.py        — Protocol contracts (ImageReader, UVWarper, ...)
    ├── infrastructure/opencv_impl.py — OpenCV implementations (5KB)
    ├── application/scene_compositor.py — SceneCompositor orchestration (3KB)
    └── presentation/
        ├── api.py                  — FastAPI routes: /api/v1/{catalog,render}
        ├── schemas.py              — Pydantic models (ZoneRequest, RenderRequest)
        └── catalog_db.py           — Hardcoded Polish materials catalog
─────────────────────────────────────────────
Total compositor src/ = 483 LOC
+ gen_kitchen.py = 446 LOC
+ main.py = ~30 LOC
+ tests/ (4 test suites: infrastructure, application, integration, performance)
```

### Layered Architecture (Clean Architecture per the README)

| Layer | Files | Purpose |
|---|---|---|
| **Domain** | `interfaces.py` | Protocol contracts. Zero dependencies. |
| **Infrastructure** | `opencv_impl.py` | OpenCV concrete implementations of every Protocol. |
| **Application** | `scene_compositor.py` | `SceneCompositor.render_scene()` — orchestrates the compositing pipeline. |
| **Presentation** | `api.py`, `schemas.py`, `catalog_db.py` | FastAPI + Pydantic. The HTTP boundary. |

### Tech Stack

- Python 3.11, FastAPI, OpenCV, NumPy
- Alpine.js + Tailwind (CDN, zero build steps) for the demo frontend
- Blender headless via subprocess (just like kitchen-plugin)
- pytest with 4 test suites including performance

### What Already Exists in the Compositor's Catalog

`catalog_db.py` — Polish materials, hardcoded but real:

```python
CATALOG = {
    "price_groups": [
        {"id": 1, "name": "Grupa Cenowa 1"},
        {"id": 2, "name": "Grupa Cenowa 2"}
    ],
    "materials": [
        {"id": "dab_szlachetny",       "price_group": 1, "allowed_zone": "ANY",
         "texture_width_mm": 1200.0, "hex_color": "#A88B68"},
        {"id": "zielony_kamienny",     "price_group": 1, "allowed_zone": "FRONT_ONLY",
         "texture_width_mm": 1000.0, "hex_color": "#4A5D5E"},
        {"id": "marmur_bianco",        "price_group": 1, "allowed_zone": "ANY",
         "texture_width_mm": 2000.0, "hex_color": "#F5F5F5"},
        {"id": "czarny_strukturalny",  "price_group": 1, "allowed_zone": "COUNTERTOP_ONLY",
         "texture_width_mm": 2000.0, "hex_color": "#222222"},
        {"id": "dab_casella_jasny",    "price_group": 2, "allowed_zone": "ANY",
         "texture_width_mm": 1200.0, "hex_color": "#D4B895"},
        {"id": "alabast",              "price_group": 2, "allowed_zone": "FRONT_ONLY",
         "texture_width_mm": 1000.0, "hex_color": "#EAE8DC"}
    ],
    "scenes": [
        { "scene_id": "kitchen_01", "name": "Nowoczesna Kuchnia (Modern)",
          "angles": [{"angle_id": "main", "name": "Widok Główny (Front View)"}] }
    ]
}
```

**This is a real Polish-market catalog**, with `price_group`, `allowed_zone` (FRONT_ONLY, COUNTERTOP_ONLY, ANY), `texture_width_mm` (for physical UV scaling — 1.0 UV unit = 1000mm). It's a partial implementation of F005's MaterialResolver concept, scoped to image-textured rendering.

---

## 2. How This Actually Works for UC1

```
                                    ─── ONE-TIME, when carpenter prepares for a visit ───
                                    ───  (or first-time per kitchen layout)            ───

USER (carpenter at home, day before visit):
  $ blender -b -P krono-compositor-mvp/gen_kitchen.py
  → reads layout.json
  → spits out 5 passes to assets/scenes/kitchen_01/main/
  → ~30-60s of Blender rendering on the laptop
  → never re-runs unless layout changes

                                    ─── LIVE, on iPad at customer's home ───

USER (carpenter on iPad at customer's house):
  taps iPad
    │
    ▼
  Browser opens http://laptop-on-customer-wifi:8000/
    │
    ▼
  Alpine.js SPA loads
    │ GET /api/v1/catalog
    ▼
  FastAPI returns materials list (Polish, with price groups)
    │
    ▼
  User picks "Dąb Szlachetny" for FRONT zone
    │ POST /api/v1/render
    │   { scene_id: kitchen_01, angle_id: main,
    │     zones: [ {mask_color_hex: "#FF0000", texture_id: "dab_szlachetny",
    │                zone_type: "FRONT"} ] }
    ▼
  FastAPI → SceneCompositor.render_scene()
    │ reads cached base/uv/mask/reflection/handle passes
    │ does the OpenCV pipeline (UV warp, mask, multiply, screen, alpha, SSAA)
    │ ~300-500ms
    ▼
  JPEG returned
    │
    ▼
  Frontend swaps the displayed image with mouse-zoom support
  User screenshots iPad (manual)
  User picks next material → loops at 500ms per iteration
```

**This is faster than I assumed by an order of magnitude** (500ms vs 5-30s). And it's already working today.

---

## 3. The Two Render Subsystems — They Are Different Jobs

We have TWO separate Blender-using render systems. They are **not duplicates of each other** — they do different jobs:

| | **krono-compositor-mvp** | **kitchen-plugin** |
|---|---|---|
| **Purpose** | Live customer-facing 2.5D preview with material swap | Engineering 3D scene + photoreal renders |
| **Render speed** | ~500ms per material swap (after one-time 30-60s setup) | ~5-30s per full render |
| **Output format** | JPEG via HTTP API | .blend, manifest.json, optional PNG/wireframe |
| **Lifecycle** | Renders 5 passes ONCE, then composites textures unlimited times | Renders fresh every time |
| **Material model** | Image textures, UV-mapped onto fixed geometry | RGB colors per object (no textures yet) |
| **Geometry model** | `layout.json` — flat list of cabinets + countertop with `id_hex` masks | `configs/*.json` — runs/walls/cabinets/corners (richer) |
| **Interactive?** | Yes — designed for live decor swap during customer visit | No — CLI-driven; user waits for render |
| **Frontend** | FastAPI + Alpine.js SPA already | None (CLI only) |
| **Maps to which UC?** | UC1 (first visit live preview), UC2 sidebar decor swap | UC2 step 7-10 ("generate renders" for customer presentation), engineering review |
| **Tested?** | 4 test suites (incl. performance test at 4K) | 22 test files |
| **Bpy version** | Uses Cycles | Uses Eevee/Cycles via configurable engine |

**Verdict:** they coexist by design. The compositor optimizes for **iteration speed**; kitchen-plugin optimizes for **engineering correctness and full-quality photoreal output**. Different stages of the workflow.

---

## 4. New Deduplications Surfaced By This Discovery

The two render subsystems do, however, **duplicate** some upstream concerns:

### Deduplication #1 — Two Blender Cabinet-Building Scripts

Both `gen_kitchen.py` (compositor, 446 LOC) and `geometry_builder.py` (kitchen-plugin) build cabinet meshes from JSON. They use different input schemas and produce different outputs, but the geometric primitives (a box for a carcass, a flat plane for a door, a handle) are duplicated.

**Mitigation options:**

| Option | Description | Pros | Cons |
|---|---|---|---|
| **D1.A** | Leave both, treat as accepted duplication | Zero churn | Real geometric bug fixed in one but not the other |
| **D1.B** | Have compositor's `gen_kitchen.py` import kitchen-plugin's geometry_builder and re-use it for the 5-pass renders | Single geometry implementation | Couples compositor to kitchen-plugin; harder to ship compositor standalone |
| **D1.C** | Extract a shared "kitchen-geometry" library that both use (a small `kuchnie_geom/` package) | Clean separation; both render systems consume the same geometric primitives | Slight over-engineering for 2 consumers |

**My lean:** D1.B. The compositor is **downstream** of kitchen-plugin in any logical workflow (you design the kitchen with the layout engine, then either render it interactively via compositor or in full quality via kitchen-plugin). Couple them in that direction. Keep gen_kitchen.py as the **5-pass camera/lighting/render-engine setup** but delegate cabinet mesh construction to kitchen-plugin's `geometry_builder`. Estimated ~half-day refactor.

### Deduplication #2 — Two Material Catalogs (Compositor's vs Planned F005's)

| | Compositor's `catalog_db.py` | Planned F005 `catalog/` |
|---|---|---|
| Storage | Hardcoded Python dict | YAML files |
| Material model | `id`, `name`, `price_group`, `allowed_zone`, `texture_width_mm`, `hex_color` | `decor_id`, `producer`, `paired_edge_id`, `variants[]` (thickness, sheet_size, sku), `grain_direction`, `texture_path` |
| Audience | Real-time renderer (needs texture image + UV scale) | Manufacturing pipeline (needs sheet size, edge banding, grain, SKU) |
| Polish vendors | Yes (already real: dab_szlachetny, marmur_bianco, etc.) | Yes (planned: Kronospan, Egger) |
| Producer field | No (just `id`) | Yes (`Kronospan` / `Egger`) |
| Has variants per thickness | No | Yes |
| Has paired edges | No | Yes |

**These are two slices of the same domain.** The compositor needs the **render-time** subset (texture image + UV width); F005 needs the **manufacturing** subset (sheet sizes, edges, SKUs). Both share an identity (the decor name).

**Resolution options:**

| Option | Description | Pros | Cons |
|---|---|---|---|
| **D2.A** | One unified `catalog/` YAML per decor with ALL fields (render + manufacturing) | Single source of truth | Compositor's catalog_db.py must be replaced with a YAML reader |
| **D2.B** | Two catalogs, with cross-references (`catalog/decors/dab_szlachetny.yaml` declares `compositor_texture_id: "dab_szlachetny"`) | Compositor stays standalone | Two catalogs to keep in sync forever |
| **D2.C** | F005 catalog is canonical; compositor's catalog_db.py becomes a thin "render projection" generated/derived from F005 YAMLs at boot | Single source; compositor still ships its own API surface | Some startup-time translation logic |

**My lean:** D2.A merged with D2.C. The F005 catalog is the authoritative source. Each `catalog/decors/<id>.yaml` has both render-side and manufacturing-side fields. The compositor's `catalog_db.py` becomes a derivation: at FastAPI startup, it loads the YAML catalog and projects to its API schema.

Example unified decor YAML:

```yaml
decor_id: kronospan_u112_pm
name: Dąb Szlachetny
producer: Kronospan
sku: U112-PM
hex_color: "#A88B68"
grain_direction: vertical

# Render-side (consumed by compositor)
compositor:
  texture_path: textures/dab_szlachetny.jpg
  texture_width_mm: 1200.0
  allowed_zones: [FRONT, COUNTERTOP, BODY]
  price_group: 1

# Manufacturing-side (consumed by F005 resolver, F008 exporter)
manufacturing:
  paired_edge_id: edge_dab_szlachetny_05
  variants:
    - thickness_mm: 18, sheet_size_mm: [2800, 2070], sku: U112-PM-18-PE
    - thickness_mm: 16, sheet_size_mm: [2800, 2070], sku: U112-PM-16-PE
```

The compositor reads only the `compositor:` block; F005 reads only the `manufacturing:` block.

---

## 5. The Updated Bounded Context Map

Adds the 6th context for the real-time render subsystem:

| Context | Path | Owns | Role in UCs |
|---|---|---|---|
| **Catalog** | `catalog/` | Decor (with render + manufacturing fields), Edge, Pairing, Producer, Variant | Read by everything |
| **Domain Core** | `src/kuchnie_core/` | Cabinet, Wall, Run, Room, Layout (Layer 1+2 absorbed), CabinetGeometry, KitchenStandards, Recipe, Template, ConstructionMethod, ValidationGate, MaterialResolver | All UCs |
| **3D Engineering Renderer** | `kitchen-plugin/` | bpy adapters, Cycles full-quality scene, manifest output, manifest_validator (Phase B) | UC2 step 7-10, engineering review |
| **2.5D Live Renderer** | `krono-compositor-mvp/` | 5-pass Blender renderer + OpenCV compositor + FastAPI render API | **UC1 live preview, UC2 sidebar decor swap** |
| **CAD/CAM** | `kitchen-cad/` | CSV/DXF/BOM/cost exporters, MachiningFeature, PatternResolver, `kitchen-cli` binary | UC3 |
| **Web Configurator** | `kitchen-app/` | Reflex UI (2D layout, cabinet sidebar, decor sidebar, cost panel) | UC2 layout building |
| **External reference** | `home_builder_5/` | Untouched community Blender addon | Reference only |

### Dependency Direction (must stay acyclic)

```
catalog/                  ← read by Domain Core via Protocol; read by Compositor at boot
                          ← read by CAD via MaterialResolver

kuchnie_core/             ← imports catalog (via Protocol only)
                          ← imported by all renderers and apps

kitchen-plugin/           ← imports kuchnie_core (Cabinet, Layout, MaterialResolver)
                          ← bpy required

krono-compositor-mvp/     ← imports kuchnie_core (Cabinet, Layout — only for gen_kitchen.py if D1.B)
                          ← optionally imports kitchen-plugin.geometry_builder (per D1.B)
                          ← serves HTTP — exposes /api/v1/{catalog,render}

kitchen-cad/              ← imports kuchnie_core (everything)
                          ← imports catalog (via Protocol)
                          ← does NOT import any renderer

kitchen-app/              ← imports kuchnie_core (layout, templates, resolver)
                          ← imports kitchen-cad (cost-estimator)
                          ← imports catalog (via Protocol)
                          ← CALLS krono-compositor-mvp via HTTP for live preview
                          ← CALLS kitchen-cad subcommand `render` for full-quality renders
                          ← CALLS kitchen-cad subcommands for CAM
```

### Two Render Calls From kitchen-app

This is the key new wiring revelation:

| User action in kitchen-app | Backend call |
|---|---|
| Drag cabinet, change dimension, swap decor in sidebar | HTTP POST to compositor `/api/v1/render` — ~500ms |
| "Lock layout" / "Generate Blender render" | subprocess `kitchen-cli render kitchen.yaml` (which delegates to kitchen-plugin) — ~30s |

The compositor is the **fast path** (interactive). kitchen-plugin is the **slow path** (presentation/engineering). They serve different urgencies in the same workflow.

---

## 6. Refined UC1 Flow (Correcting Doc 08 § 3)

The previous UC1 diagram showed `kitchen-app → render endpoint → subprocess kitchen-plugin`. **Wrong path for live decor swap.** Corrected:

```
─── PHASE 0: Scene Bake (once per kitchen layout) ────────────────
USER (carpenter, day before customer visit OR after layout change):
  Confirms layout in kitchen-app.
  kitchen-app calls subprocess: `kitchen-cli bake-scene kitchen.yaml --angle main`
    │
    ▼
  kitchen-cli (kitchen-cad/cli/bake_scene.py):
    Renders compositor's 5 passes into assets/scenes/<kitchen_id>/<angle>/
    Reuses kitchen-plugin's geometry (per D1.B) to build the bpy scene
    Configures Cycles for 5-pass output (art passes vs math passes per
      compositor's PIPELINE_RULES.md — denoising on art, off on math)
  ~30-60s once.

─── PHASE 1: Live customer interaction (every decor swap) ────────
USER (carpenter at customer's home, on iPad):
  Browser opens kitchen-app (running on laptop on customer's wifi).
  User taps sidebar: change FRONT decor to "Dąb Szlachetny".
  kitchen-app updates kitchen.material_slots["project_front"] = "kronospan_u112_pm"
    │
    ▼
  kitchen-app calls compositor HTTP API:
    POST http://localhost:8000/api/v1/render
      scene_id: <kitchen_id>
      zones: [for each role: {mask_color_hex, texture_id, zone_type}]
    │
    ▼
  Compositor (FastAPI in same Python process OR separate, decision pending):
    SceneCompositor.render_scene(...) — ~300-500ms
    Returns JPEG
    │
    ▼
  kitchen-app embeds returned JPEG in browser.
  User screenshots iPad (manual). Loops.

─── PHASE 2: Engineering render (on customer acceptance) ─────────
USER:
  Customer happy. Click "Generate full render for review".
  kitchen-app calls subprocess: `kitchen-cli render kitchen.yaml --output review.png`
  kitchen-cli delegates to kitchen-plugin (via subcommand registry per F007/F008).
  ~30s photoreal render returned.

─── PHASE 3: CAM export ───────────────────────────────────────────
USER: (as in UC3) — `kitchen-cli cut-list`, `drill-pattern`, `dxf`, etc.
```

**This is the actual organic flow.** Two render speeds, two render purposes, single Kitchen YAML.

---

## 7. Did This Influence the Current Agreement?

### What stays the same

- ✅ Option A confirmed (adopt existing working code, don't rebuild)
- ✅ Layer 1+2 promotion (`kitchen-plugin/src/{core,kitchen}/` → `src/kuchnie_core/`) — still correct, still needed
- ✅ The "Kitchen YAML as universal currency" principle — still correct
- ✅ RecipeEngine, MaterialResolver, ValidationGate registries — still go in Core
- ✅ CSV/DXF/BOM/cost exporters still go in kitchen-cad
- ✅ Reflex still the right choice for kitchen-app (Python end-to-end)
- ✅ F004 two-phase validation (logical + geometric) — still correct
- ✅ home_builder_5/ untouched — still correct

### What changes

| Item | Before | After |
|---|---|---|
| Bounded contexts | 5 (+ external plugin) | **6** (+ external plugin) — adds **2.5D Live Renderer** |
| UC1 latency | Wrongly assumed 5-30s per decor swap | **~500ms per swap** (compositor's 2-phase design) |
| F005 spec | Just plan a YAML catalog | **Merge with compositor's `catalog_db.py` Polish data; add unified render+manufacturing schema** |
| F007 ADR | "Adopt kitchen-plugin as the renderer" | **Adopt kitchen-plugin for engineering renders; adopt krono-compositor-mvp for live previews; bake-scene CLI subcommand bridges them** |
| F008 subcommands | `cut-list, drill-pattern, dxf, bom, cost-estimate, render` | **+ `bake-scene`** (renders the 5 passes the compositor consumes) |
| F006 (Web sidebar) | "Reflex calls render endpoint" | **Reflex calls compositor HTTP API for live, kitchen-cli for full render** — two distinct render paths |
| Deduplication tasks | None tracked | **D1** (two Blender scripts) and **D2** (two catalogs) added |

### What was outright wrong in doc 08

- **§ 3 (UC1) flow** — described single-subprocess-per-render. Actually two-phase (bake once + composite-many).
- **§ 7 (organic-design verdict)** — `kitchen-plugin can render without knowing anything about Polish materials` is ✅ correct, but missing: `compositor can render at 500ms per swap`. Compositor wasn't in the model.
- **§ 8 (the one diagram that matters)** — shown three output paths (HTML+swatches, CSV+DXF+BOM, PNG+manifest). Missing: **the JPEG-via-compositor path is a fourth output**, and it's the most-used one in UC1.

---

## 8. New Open Questions Surfaced

These are decisions you (the user) need to make. I have leanings but won't lock anything in without your call:

### Q1 — How to handle the catalog unification (D2)?

**My lean: D2.A merged with D2.C** — unified YAML catalog in `catalog/`, compositor projects at boot. Compositor's `catalog_db.py` becomes a derivation layer.

### Q2 — How to handle the Blender script duplication (D1)?

**My lean: D1.B** — compositor's `gen_kitchen.py` imports kitchen-plugin's `geometry_builder` for the actual mesh construction; keeps its own pass-rendering setup (lighting, camera, render engine config, 5-pass output).

### Q3 — Where does the compositor's HTTP server run?

Three deployment models:
- **Q3.A** — separate process: `uv run python krono-compositor-mvp/main.py` runs FastAPI on port 8000; kitchen-app's Reflex backend calls `http://localhost:8000/api/v1/render`. Two processes.
- **Q3.B** — mounted FastAPI in Reflex: kitchen-app's Reflex backend exposes the compositor's routes directly. One process.
- **Q3.C** — compositor as a Python library only (no HTTP): kitchen-app imports `SceneCompositor` directly, calls `.render_scene()` in-process. No HTTP boundary. The Alpine.js demo frontend gets dropped.

**My lean: Q3.C for v1.0** — the HTTP boundary was useful when the compositor was standalone with its own demo frontend, but with kitchen-app as the single UI, the in-process call is simpler. Drop the Alpine.js demo (keep it in git history for reference). Re-introduce HTTP if you ever serve over network (e.g., separate iPad app talking to a laptop daemon).

### Q4 — When does the bake-scene step happen?

**Q4.A** — Eager: every layout change in kitchen-app fires a bake-scene in background. User can swap decors instantly. But 30-60s of CPU work per layout edit.
**Q4.B** — Lazy: user explicitly clicks "Lock layout for presentation" → bake-scene runs, then sidebar swatch swaps become live.
**Q4.C** — Triggered on demand: first decor swap after layout change auto-fires bake-scene with a "Preparing scene..." indicator.

**My lean: Q4.B** — explicit. The workflow in 00-brief.md step 1-5 has the carpenter doing measurements + layout offline before the visit; baking happens in that phase. Sidebar swapping at customer's home is in the live phase.

### Q5 — How do we trigger compositor pass re-bake when ConstructionMethod or panel dimensions change?

**Q5.A** — Manual: user re-triggers bake-scene. Acceptable for solo dev.
**Q5.B** — Cache invalidation: kitchen-app computes a layout-affecting hash of the kitchen.yaml and invalidates the cache if changed.

**My lean: Q5.B** for v1.0 — cheap to implement, prevents the carpenter staring at stale geometry while picking decors. Hash on cabinet positions + dimensions + construction_method; ignore material_slots (those don't affect geometry).

### Q6 — Does kitchen-app become the new compositor frontend, or do they coexist with their own UIs?

The compositor has a working Alpine.js + Tailwind frontend today. kitchen-app is planned as Reflex.

**Q6.A** — kitchen-app fully owns the UI; compositor is headless service. Alpine.js demo gets retired.
**Q6.B** — Both exist; Alpine.js demo for "quick standalone preview" use, kitchen-app for full configurator.
**Q6.C** — kitchen-app embeds an iframe to the compositor's Alpine.js page for the decor-swap part.

**My lean: Q6.A** — single UI is cleaner. The Alpine.js code is preserved in git as a working reference. ~150 lines of HTML — easy to recreate in Reflex if we ever want to.

---

## 9. Process Improvement Acknowledgement

This is the **second time** in two sessions you've caught a major piece of existing code that the planning ignored:

- **First catch:** `kitchen-plugin/` — directory name read as "Blender plugin, external" when it was actually our most mature subsystem.
- **Second catch:** `krono-compositor-mvp/` — only noticed because you asked specifically about 2.5D rendering.

The pattern: **I (the LLM) am pattern-matching directory names instead of exploring them.** The fix, added to `04_solo_dev_process.md` in the cleanup commit:

```
PRE-PLANNING CHECKLIST (mandatory before any architectural planning):
  1. ls $PROJECT_ROOT — list every sibling directory
  2. For each directory > 200 LOC:
     a. read its README.md if present
     b. run `pysum` on its src/ dir
     c. read its pyproject.toml or package.json
  3. DO NOT assume any directory is "external", "legacy", "unrelated", or
     "out of scope" based on name alone.
  4. If you have NOT done step 2 for every sibling, you are not allowed
     to produce a "bounded context map".

  Sibling directories in kuchnie/ project root (as of 2026-06-29):
    catalog/                 ← Polish material catalog (partial)
    kitchen-app/             ← planned Reflex web UI (skeleton)
    kitchen-cad/             ← planned CAD/CAM exporters (skeleton)
    kitchen-plugin/          ← MATURE: 4523 LOC, 22 tests, 3D engineering renderer
    krono-compositor-mvp/    ← MATURE: 909 LOC, 4 test suites, 2.5D live compositor
    material-configurator/   ← (docs/ only — exploratory; verify if planning ever
                                produced code)
    src/kuchnie_core/        ← legacy decomposers + serialize.py contract
```

I owe you a verification of `material-configurator/` too — let me check that next so we don't make this mistake a third time.

---

## 10. Bottom Line

> **Seam A is not a problem.** You already solved it with the krono-compositor-mvp 2-phase architecture. UC1 latency is ~500ms per material swap, not 5-30s. The previous architecture diagram (doc 08) had the wrong mental model.
>
> **Option A holds and gets stronger.** The integration plan is the same: adopt existing working code via clean dependency direction. But the bounded context map grows to 6, and 2 new deduplications (Blender scripts; catalog) need decisions.
>
> **No new core architectural changes** — just acknowledgment of what already exists and how to wire it in.
>
> **Next steps before any spec rewrite:**
> 1. Verify `material-configurator/` is or isn't another mature subsystem we missed.
> 2. Answer Q1–Q6 in § 8 above.
> 3. Then I update docs 07 + 08 with the corrections, and only THEN start spec rewrites.
