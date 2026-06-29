# Architecture Diagram — Counterparties, Responsibilities, Data Flow

> **Purpose:** Before committing to Option A and rewriting specs, verify the integration design is **organic** for the three use cases in `00-brief.md`. If a use case requires twisting the architecture or crossing boundaries in unnatural directions, the design is wrong.
>
> **Verdict (preview):** The design is organic, BUT it surfaces one nuance the previous planning missed — **F004 actually has two distinct validation phases** (logical pre-build + geometric post-build). See § 6.

---

## 1. The Counterparties (Static Structure)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  USER                                                                       │
│   │                                                                         │
│   │   ┌───────────────────────┐                                             │
│   ├──▶│   iPad / Browser      │ ◀──── UC1 first visit, UC2 cost estimate   │
│   │   └──────┬────────────────┘                                             │
│   │          │ HTTP / WebSocket                                             │
│   │          ▼                                                              │
│   │   ┌──────────────────────────────────────────────────────────┐          │
│   │   │           kitchen-app/  (Reflex, Python)                 │          │
│   │   │   ┌──────────────────────────────────────────────────┐   │          │
│   │   │   │  Pages: Layouts gallery, Configurator, Sidebar   │   │          │
│   │   │   │  State: Kitchen (in memory), CostEstimate        │   │          │
│   │   │   └──────┬───────────────────────┬─────────────────┬─┘   │          │
│   │   └──────────┼───────────────────────┼─────────────────┼─────┘          │
│   │              │ import (in-process)   │                 │                │
│   │              ▼                       ▼                 ▼                │
│   │     ┌────────────────────┐   ┌──────────────┐   ┌────────────────────┐  │
│   │     │  kuchnie_core/     │   │ kitchen-cad/ │   │  catalog/          │  │
│   │     │                    │   │              │   │                    │  │
│   │     │  - Project         │   │ - CostEstim. │   │  - YAML readers    │  │
│   │     │  - Kitchen         │   │ - BOMBuilder │   │  - Producer        │  │
│   │     │  - Cabinet*        │   │ - CutList    │   │  - Decor           │  │
│   │     │  - Run* (was Row)  │   │   Exporter   │   │  - Edge            │  │
│   │     │  - Wall*, Room*,   │◀──┤ - DrillPat.  │   │  - Pairing         │  │
│   │     │    Layout*         │   │   Exporter   │   │  - Variant         │  │
│   │     │  - Panel           │   │ - DXFExporter│   │                    │  │
│   │     │  - SubAssembly     │   │ - MachiningF.│   │  Implements:       │  │
│   │     │  - CabinetGeometry*│   │ - PatternRes.│   │  CatalogReader     │  │
│   │     │                    │   │ - kitchen-cli│   │  (Protocol from    │  │
│   │     │  Registries:       │   │   binary     │   │   Core)            │  │
│   │     │  - Construction-   │   │              │   └────────┬───────────┘  │
│   │     │    Method (F001)   │   └─────┬────────┘            │              │
│   │     │  - Recipe (F002)   │         │ subprocess          │ in-process   │
│   │     │  - Template (F003) │         │ (CLI binary)        │ via Protocol │
│   │     │  - ValidGate (F004)│         │                     │              │
│   │     │  - MaterialReslv.  │◀────────┴─────────────────────┘              │
│   │     │    (F005)          │                                              │
│   │     │                    │ subprocess via                               │
│   │     │  Workflow:         │ render endpoint                              │
│   │     │  - BOM             ├──────────────────┐                           │
│   │     │  - YAML loader     │                  ▼                           │
│   │     │  - YAML serializer │   ┌──────────────────────────────────────┐   │
│   │     │                    │   │  kitchen-plugin/   (Python + bpy)    │   │
│   │     └────┬───────────────┘   │                                      │   │
│   │          │ imports           │  Layer 4 (bpy):                      │   │
│   │          │ (Cabinet,         │   - geometry_builder                 │   │
│   │          │  Layout types)    │   - material_manager  ◀─── reads     │   │
│   │          │                   │   - geometry_manifest      Resolved- │   │
│   │          ▼                   │   - manifest_validator     Material  │   │
│   │   * = absorbed from          │   - exporters (.blend, PNG)          │   │
│   │       kitchen-plugin into    │                                      │   │
│   │       kuchnie_core           │  Layer 3 (config):                   │   │
│   │       (per § 4 of doc 07)    │   - config_parser (YAML loader)      │   │
│   │                              │   - validators                       │   │
│   │                              │   - wall_builder                     │   │
│   │                              │                                      │   │
│   │                              │  Layer 5: main.py CLI entry          │   │
│   │                              └──────────────────────────────────────┘   │
│   │                                                                         │
│   │   ┌──────────────────────────┐                                          │
│   ├──▶│   Terminal / shell       │ ◀──── UC3 CAM preparation                │
│   │   └────────┬─────────────────┘                                          │
│   │            │ runs                                                       │
│   │            ▼                                                            │
│   │   ┌────────────────────────────┐                                        │
│   │   │  kitchen-cli  (binary in   │                                        │
│   │   │   kitchen-cad/)            │                                        │
│   │   │                            │                                        │
│   │   │  Subcommands:              │                                        │
│   │   │  - cut-list                │                                        │
│   │   │  - drill-pattern           │                                        │
│   │   │  - dxf                     │                                        │
│   │   │  - bom                     │                                        │
│   │   │  - cost-estimate           │                                        │
│   │   │  - render (delegates to    │                                        │
│   │   │    kitchen-plugin's        │                                        │
│   │   │    main.py via subprocess) │                                        │
│   │   └────────────────────────────┘                                        │
│   │                                                                         │
│   │   ┌──────────────────────────┐                                          │
│   ├──▶│  CNC company             │ ◀──── receives CSV + DXF                 │
│   │   └──────────────────────────┘                                          │
│   │                                                                         │
│   │   ┌──────────────────────────┐                                          │
│   └──▶│  Customer (Wrocław)      │ ◀──── receives screenshots, renders      │
│       └──────────────────────────┘                                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

LEGEND
══════
  →           import (in-process Python call, no IPC)
  ◀── subprocess  fork+exec; data passed via YAML file argument
  Protocol    interface defined in Core, implemented in Catalog (ACL pattern)
  *           identifier absorbed from kitchen-plugin into kuchnie_core
              (Cabinet, Run, Wall, Room, Layout, CabinetGeometry — see doc 07 § 5)
```

### Responsibility Boundaries (one-line summary each)

| Component | One-line responsibility |
|---|---|
| **kitchen-app** | All UI state. Owns the in-memory `Kitchen` document while user is editing. Knows nothing about CSV/DXF/bpy. |
| **kuchnie_core** | The domain language. Owns the **types** (Cabinet, Wall, Layout, Panel, Kitchen, BOM) and the **registries** (ConstructionMethod, Recipe, Template, ValidationGate, MaterialResolver). No bpy, no Reflex, no FastAPI. |
| **catalog** | The Kronospan/Egger material data. Implements Core's `CatalogReader` Protocol. Knows nothing about Cabinets or Recipes. |
| **kitchen-cad** | All manufacturing outputs (CSV cut list, DXF, drill patterns, BOM, cost). Owns the `kitchen-cli` binary. Imports Core types; never imports Web or Render. |
| **kitchen-plugin** | The 3D geometry + render subsystem. Builds bpy meshes from a Kitchen YAML, emits a manifest JSON, optional `.blend` + PNG. Imports Core types (after Layer 1+2 absorption); does NOT import CAD or Web. |
| **kitchen-cli** | A subcommand-registry binary. Each subcommand is a thin function: load Kitchen YAML, call services in Core/CAD/kitchen-plugin, write output file. |

### What kitchen-plugin owns AFTER Layer 1+2 absorption

If you confirm Option B from doc 07 § 4 (recommended), kitchen-plugin's responsibilities shrink to:

- **bpy adapters only:** `geometry_builder`, `material_manager`, `geometry_manifest`, `manifest_validator`, `exporters`
- **CLI entry:** `main.py` (invoked by `kitchen-cli render` and directly)
- **Config parsing:** `config_parser` (reads YAML, produces Core's `Kitchen`)

Everything currently in `kitchen-plugin/src/core/` and `kitchen-plugin/src/kitchen/` (Vector2D/3D, Cabinet, Wall, Room, Run, Layout, CabinetGeometry, KitchenStandards) moves to `src/kuchnie_core/` because those are pure-Python domain types with no bpy. The Web app + CLI also need them — they shouldn't have to import from kitchen-plugin to get `Cabinet`.

---

## 2. Data Types Crossing Boundaries

This is the **single most important table** for verifying the design is organic. If a data type has to be translated at every boundary, the design is wrong.

| Type | Where it lives | Who reads it | Who writes it | Crossing-boundary form |
|---|---|---|---|---|
| **Kitchen** (the document) | `kuchnie_core/kitchen.py` | All | kitchen-app, YAML loader | YAML file |
| **Cabinet** (one cabinet) | `kuchnie_core/cabinet.py` | All | RecipeEngine, kitchen-app | Pydantic dataclass (in-process); part of Kitchen YAML on disk |
| **Run** (a row of cabinets) | `kuchnie_core/layout.py` | LayoutEngine, BOM | kitchen-app | Part of Kitchen YAML |
| **Layout** (all walls + placed cabinets) | `kuchnie_core/layout.py` | kitchen-plugin (renders), kitchen-cad (cuts) | LayoutEngine | In-process dataclass |
| **Panel** (atomic manufacturing unit) | `kuchnie_core/panel.py` | kitchen-cad exporters, kitchen-plugin geometry_builder | RecipeEngine | In-process dataclass; one row in CSV cut list |
| **ConstructionMethod** | `kuchnie_core/construction/` | RecipeEngine, CabinetGeometry, F008 patterns | YAML on disk (registry) | YAML file |
| **CabinetTemplate** | `kuchnie_core/templates/` | kitchen-app sidebar, RecipeEngine | YAML on disk | YAML file |
| **Recipe** | `kuchnie_core/recipes/` | RecipeEngine | YAML on disk | YAML file |
| **ResolvedMaterial** | `kuchnie_core/material_resolver.py` (return type) | kitchen-plugin material_manager, kitchen-cad exporters | MaterialResolver | In-process frozen dataclass |
| **DecorRecord / EdgeRecord / Variant** | catalog/ | MaterialResolver | YAML reader in catalog/ | In-process via Protocol |
| **MachiningFeature** | `kitchen-cad/features.py` | DXF/Drill exporters | PatternResolver | In-process |
| **Issue / ValidationResult** | `kuchnie_core/validation/` | All consumers (kitchen-app shows errors; CLI exits nonzero) | All gate implementations | In-process |
| **Manifest** (post-render JSON) | kitchen-plugin produces | kitchen-app (could check post-render dims), tests | kitchen-plugin/geometry_manifest | JSON file on disk |

**Observation:** every type either lives in Core (and is imported everywhere) or is a "leaf" output (CSV, DXF, manifest.json, PNG, .blend). **No type is invented twice in two contexts.** This is the litmus test for an organic design. ✅

---

## 3. Use Case 1 — First Visit (2.5D Preview at Customer's Home)

> Carpenter on iPad. Predefined layouts. Sidebar to change decors. Generate 2.5D high-quality image. Screenshot, repeat.

```
┌─────────┐                                                                           
│   USER  │  taps iPad                                                                 
└────┬────┘                                                                            
     │ 1. Opens kitchen-app on iPad                                                    
     ▼                                                                                 
┌─────────────────┐                                                                    
│  kitchen-app    │  (Reflex page renders)                                             
│                 │                                                                    
│  GET /layouts   │ 2. Calls TemplateRegistry.list_kitchens(category="predefined")     
│        ─────────┼───────────────┐                                                    
└─────────────────┘               ▼                                                    
                          ┌─────────────────┐                                          
                          │ kuchnie_core    │ 3. Loads YAMLs from                      
                          │ TemplateRegistry├───▶ src/kuchnie_core/templates/kitchens/ 
                          └────────┬────────┘     (predefined L/U/I-shape examples)    
                                   │                                                   
                                   ▼ list[KitchenTemplate]                             
┌─────────────────┐                                                                    
│  kitchen-app    │ 4. User taps "L-shape 3.2m". App instantiates a new Kitchen:       
│                 │     - reads predefined Kitchen YAML                                
│                 │     - assigns default material_slots = {                           
│                 │         project_body: "kronospan_u112_pm_default",                 
│                 │         project_front: "kronospan_u112_pm_default", ...}           
└────────┬────────┘                                                                    
         │                                                                             
         │ 5. User opens decor sidebar.                                                
         │    App calls MaterialResolver.list_decors_for_role("front")                 
         ▼                                                                             
┌──────────────────────┐                                                               
│ MaterialResolver     │ 6. queries catalog/ via CatalogReader Protocol                
│ (kuchnie_core)       ├──────▶ ┌──────────┐                                           
└──────────────────────┘        │ catalog/ │ 7. returns list of decor swatches         
                                └──────────┘    (Kronospan + Egger filtered to fronts) 
         │                                                                             
         ▼ list[DecorRecord]                                                           
┌─────────────────┐                                                                    
│  kitchen-app    │ 8. Renders swatches. User picks "Egger H3303 ST10 Sand Beige".     
│                 │    App mutates kitchen.material_slots["project_front"] =          
│                 │      "egger_h3303_st10"                                            
│                 │                                                                    
│                 │ 9. User taps "Generate 2.5D render".                               
│                 │    App writes kitchen.yaml to a temp file.                         
│                 │    App POSTs to render endpoint (Reflex backend route).            
└────────┬────────┘                                                                    
         │                                                                             
         ▼                                                                             
┌──────────────────────────────────────────────┐                                       
│  Render endpoint (Reflex backend)             │                                      
│                                              │ 10. subprocess.run([                  
│                                              │       "blender", "--background",      
│                                              │       "--python",                     
│                                              │       "kitchen-plugin/src/main.py",   
│                                              │       "--", "/tmp/kitchen.yaml",      
│                                              │       "--render", "preview_25d"])     
└──────────┬───────────────────────────────────┘                                       
           │                                                                           
           ▼                                                                           
┌──────────────────────────────────────────────────────────────────────────────┐       
│  kitchen-plugin (running under Blender headless)                             │       
│                                                                              │       
│  11. config_parser.py loads kitchen.yaml → kuchnie_core.Kitchen              │       
│  12. wall_builder.build_domain_layout() → kuchnie_core.Layout                │       
│  13. RecipeEngine(kitchen).decompose() → list[Panel] per cabinet             │       
│      (F002 — kitchen-plugin imports RecipeEngine from Core)                  │       
│  14. geometry_builder.build_kitchen_from_layout(layout) → list[bpy.Object]   │       
│  15. material_manager.create_materials() reads MaterialResolver:             │       
│        for each cabinet:                                                     │       
│          for each role in ("body", "front", "back"):                         │       
│            rm = resolver.resolve_role(role, cabinet)                         │       
│            bpy.material.use_texture(rm.texture_path)                         │       
│  16. exporters.render_25d(camera_preset="elevation") → /tmp/preview.png      │       
│  17. geometry_manifest.export() → /tmp/manifest.json (with validation flags) │       
└──────────┬───────────────────────────────────────────────────────────────────┘       
           │                                                                           
           ▼ exit 0 + paths                                                            
┌─────────────────────────────────────┐                                                
│  Render endpoint                    │ 18. Reads /tmp/preview.png                     
│                                     │     Returns base64 or URL to client            
└──────────┬──────────────────────────┘                                                
           │                                                                           
           ▼                                                                           
┌─────────────────┐                                                                    
│  kitchen-app    │ 19. Displays preview in browser/iPad.                              
│                 │     User screenshots iPad. Goes back to step 8 for next decor.     
└─────────────────┘                                                                    
```

**Organic check for UC1:**

✅ **Every cross-boundary call is necessary.** Web → Core (registries), Web → Render (subprocess), Render → Core (registries for typing + decomposition).
✅ **No data is invented twice.** Kitchen is YAML, Cabinet/Layout are Core types, Render reads them directly.
✅ **Subprocess boundary is at the right place** (between web request handler and Blender). bpy stays inside its process; web stays out of bpy.

⚠️ **Latency concern:** Steps 10–17 take 5–30 seconds depending on render complexity. For "fast iteration over decors" (UC1), this is the critical-path. **Mitigation:** F007 must define a `preview_25d` render preset that is much faster than full photoreal — e.g., low-res + cycles single-pass + cached textures. The `kitchen-plugin/ROADMAP.md` lists "Next Phase: Material System + Rendering" with render presets — F007 fits there exactly.

⚠️ **Concurrent users:** if you ever have multiple users (won't happen — solo dev), the subprocess fires per request. Each takes a CPU core + ~2GB RAM. Fine for a solo dev on a laptop; would need queuing on a server.

---

## 4. Use Case 2 — Cost Estimation + BOM (Web Configurator)

> Open web app. 2D layout with rows. Add cabinets from sidebar. Global dimensions. Per-cabinet overrides. Auto cost update. Click generate renders.

```
┌─────────┐                                                                            
│   USER  │                                                                            
└────┬────┘                                                                            
     │ 1. Opens kitchen-app/configurator                                               
     ▼                                                                                 
┌─────────────────┐                                                                    
│  kitchen-app    │ 2. Starts empty Kitchen (or loads saved one)                       
│  Configurator   │ 3. User enters wall measurements →                                 
│                 │      creates Walls + Room via LayoutEngine                         
│                 │      (LayoutEngine is in Core after migration)                     
│                 │                                                                    
│                 │ 4. User drags "base-door 600" from sidebar onto wall 1.            
│                 │    App calls TemplateRegistry.instantiate("base_door_60")          
│                 │    → CabinetInstance (clone of template defaults)                  
│                 │    → appends to run[0]                                             
│                 │                                                                    
│                 │ 5. LayoutEngine.calculate_layout(runs, ...) re-runs:               
│                 │    → updates positions; checks overlaps; flags gap issues          
└────┬────────────┘                                                                    
     │                                                                                 
     │ 6. After every change: cost panel auto-updates.                                 
     │    App calls cost_estimator.estimate(kitchen)                                   
     ▼                                                                                 
┌──────────────────────────┐                                                           
│ kitchen-cad/             │                                                           
│   cost_estimator.py      │ 7. For each cabinet:                                      
│                          │      panels = RecipeEngine.decompose(cab, method)         
│                          │    Aggregate panels by (decor_id, thickness):             
│                          │      total_m2_per_sku = sum(panel area + waste_factor)    
│                          │    For each sku:                                          
│                          │      rm = MaterialResolver.resolve_role(...)              
│                          │      sheets_needed = ceil(total_m2 / rm.sheet_size_m2)    
│                          │      cost += sheets_needed × board_price[sku]             
│                          │    Add accessory cost (hinges, drawers, handles)          
│                          │    Add edge banding linear meters                         
└──────────┬───────────────┘                                                           
           │                                                                           
           ▼ CostEstimate                                                              
┌─────────────────┐                                                                    
│  kitchen-app    │ 8. Renders "Estimated: 12,450 zł" in sidebar.                      
│                 │ 9. User customizes one cabinet (width 800 → 1000).                 
│                 │    Template constraint check passes (max=1200).                    
│                 │    Re-run from step 5. Cost updates: "Estimated: 13,100 zł".       
│                 │                                                                    
│                 │ 10. User taps "Generate renders".                                  
│                 │     Same as UC1 step 9-19, but with full-quality render preset.    
└─────────────────┘                                                                    
```

**Organic check for UC2:**

✅ **cost_estimator lives in kitchen-cad** (it's CAM-side knowledge — board sizes, accessory pricing). Web app imports it directly. Clean dependency.
✅ **RecipeEngine is called from web** to get panels. Same RecipeEngine the renderer + CLI use. **One source of truth for "what panels does this cabinet decompose into."**
✅ **LayoutEngine is called from web** for live overlap detection. Same engine kitchen-plugin uses at render time. ✅ Single answer.

⚠️ **Cost-update performance:** if user is dragging cabinets, cost recalculates per drop. For ~30 cabinets, recipe decomposition + material resolution + aggregation should run in <100ms. Asteval is the slow part — Cython-compiled formulas would be faster. **Acceptable for v1.0.**

⚠️ **Where does pricing data live?** The board prices ("EUR 12.50 per m² for Kronospan U112 PM 18mm") aren't in `catalog/` today. F008's cost-estimate spec needs to declare: is pricing a catalog field (`Variant.price_per_sheet`), or a separate `pricing/` YAML config, or fetched from a price-list URL? **This is an Open Question for F008 implementation.** ← **NEW finding from this diagram.**

---

## 5. Use Case 3 — CAM Preparation (CLI for CNC Export)

> Customer accepted. CLI generates CSV cut list, drill pattern CSV, DXF panels. Send to CNC.

```
┌─────────┐                                                                            
│   USER  │ (in terminal, working with accepted kitchen.yaml)                          
└────┬────┘                                                                            
     │                                                                                 
     │ 1. $ kitchen-cli cost-estimate kitchen.yaml --waste 0.15                        
     ▼                                                                                 
┌─────────────────────────────────────────────────────────────────────────────┐        
│  kitchen-cli  (kitchen-cad/src/kitchen_cad/cli/__main__.py)                 │        
│                                                                             │        
│   2. registered subcommands:                                                │        
│      - cost-estimate  → kitchen_cad.cli.cost_estimate.run                   │        
│      - cut-list       → kitchen_cad.cli.cut_list.run                        │        
│      - drill-pattern  → kitchen_cad.cli.drill_pattern.run                   │        
│      - dxf            → kitchen_cad.cli.dxf.run                             │        
│      - bom            → kitchen_cad.cli.bom.run                             │        
│      - render         → kitchen_render.cli.render.run                       │        
│                          (F007 contributes this subcommand at import time)  │        
│                                                                             │        
│   3. for "cost-estimate":                                                   │        
│      kitchen = kuchnie_core.loader.load_yaml("kitchen.yaml")                │        
│      estimate = cost_estimator.estimate(kitchen, waste_factor=0.15)         │        
│      print(format_estimate(estimate))                                       │        
└─────────────────────────────────────────────────────────────────────────────┘        
     │                                                                                 
     │ 4. $ kitchen-cli cut-list kitchen.yaml --output cuts.csv                        
     ▼                                                                                 
┌─────────────────────────────────────────────────────────────────────────────┐        
│  kitchen-cli cut-list                                                       │        
│                                                                             │        
│   5. kitchen = load_yaml(...)                                               │        
│   6. RUN VALIDATION GATES (PRE-BUILD — F004 logical gates):                 │        
│        gate_cabinet.validate(kitchen) → issues                              │        
│        gate_row.validate(kitchen) → issues                                  │        
│        gate_kitchen.validate(kitchen) → issues                              │        
│        gate_cam.validate(kitchen) → issues  (CAM-100: every panel role     │        
│                                              has a resolvable decor)        │        
│        if any ERROR: print issues, exit 1                                   │        
│   7. decomposition = RecipeEngine(kitchen).decompose_all()                  │        
│   8. cuts = []                                                              │        
│      for panel in decomposition.panels:                                     │        
│          rm = MaterialResolver.resolve_role(panel.material_role, ...)       │        
│          edge_top = resolver.resolve_role(panel.edges.top, ...).            │        
│                       paired_edge_id  (← F005 _color suffix convention)     │        
│          cuts.append(CutPiece(                                              │        
│            panel_id, length, width, thickness,                              │        
│            material_decor_id=rm.decor_id,                                   │        
│            material_sheet_size=rm.sheet_size_mm,                            │        
│            edge_top=edge_top, edge_bottom=..., edge_left=..., edge_right=...│        
│            grain_direction=rm.grain_direction, ...))                        │        
│      CutListExporter.write(cuts, "cuts.csv")  (UTF-8 BOM, e-rozkroj cols)   │        
└─────────────────────────────────────────────────────────────────────────────┘        
     │                                                                                 
     │ 9. $ kitchen-cli drill-pattern kitchen.yaml --output drills.csv                 
     ▼                                                                                 
┌─────────────────────────────────────────────────────────────────────────────┐        
│  kitchen-cli drill-pattern                                                  │        
│                                                                             │        
│  10. load + validate (same gates as step 5-6)                               │        
│  11. for each panel:                                                        │        
│        method = ConstructionMethod.get(cabinet.construction_method_id)      │        
│        for pattern_ref in panel.drill_pattern_refs:                         │        
│            features = PatternResolver.resolve(                              │        
│                pattern_ref, panel, method)                                  │        
│            # e.g., pattern_ref="system32" → list[MachiningFeature]         │        
│            #   (5mm drill holes every 32mm on side panels, dist 37mm       │        
│            #    from front edge)                                            │        
│        DrillPatternExporter.append(features)                                │        
│      write drills.csv                                                       │        
└─────────────────────────────────────────────────────────────────────────────┘        
     │                                                                                 
     │ 12. $ kitchen-cli dxf kitchen.yaml --output panels-dxf/                         
     ▼                                                                                 
┌─────────────────────────────────────────────────────────────────────────────┐        
│  kitchen-cli dxf                                                            │        
│                                                                             │        
│  13. load + validate                                                        │        
│  14. for each panel:                                                        │        
│        features = PatternResolver.resolve_all(panel, method)                │        
│        DXFExporter.write(panel, features, f"panels-dxf/{panel.id}.dxf")     │        
│        # DXF layers: PANEL_OUTLINE, EDGE_BAND_*, DRILL_*, GROOVE_*          │        
└─────────────────────────────────────────────────────────────────────────────┘        
     │                                                                                 
     │ 15. User reviews CSVs and DXFs in spreadsheet / LibreCAD                        
     │ 16. Sends to CNC company via email                                              
     │ 17. CNC company replies with quote                                              
     ▼                                                                                 
┌──────────────────┐                                                                   
│   CNC company    │  18. Manufactures panels, delivers cut + drilled boards          
└──────────────────┘                                                                   
```

**Organic check for UC3:**

✅ **Same RecipeEngine + ConstructionMethod + MaterialResolver as UC1/UC2.** No duplication of "what panels does this cabinet have?"
✅ **CLI subcommand registry** allows F007 (render adapter, lives in kitchen-plugin) to contribute the `render` subcommand without kitchen-cad importing from kitchen-plugin. Inversion of control.
✅ **DRY: validation runs on every CLI subcommand.** F004's gates are called once at the top; if they fail, no subcommand proceeds.

⚠️ **CAM Gate (CAM-100) needs to be precise.** What does "every panel role has a resolvable decor" mean exactly?
  - Every `role` emitted by recipe has a matching slot in `cabinet.material_refs`?
  - Every slot name in `cabinet.material_refs` has a matching key in `kitchen.material_slots`?
  - Every decor_id in `kitchen.material_slots` exists in catalog?
  - Every decor has a `paired_edge_id` (otherwise `_color` resolution fails)?
  - Every decor has a `Variant` matching the cabinet's `construction_method.corpus_thickness_mm`?

  All five. **F005 spec must enumerate these as the CAM-100 acceptance criteria.** ← **NEW finding from this diagram.**

---

## 6. The Two-Phase Validation Story (Critical Refinement)

While walking through the use cases I realized **F004's "4 gates" framing missed one phase**. There are actually **two distinct validation phases** in the system:

### Phase A — Logical gates (pre-build, pure data)

**Where:** `kuchnie_core/validation/gates/`
**Inputs:** `Kitchen` + `CabinetInstance`s + `Recipe` outputs (Panel list)
**Required for:** every CLI subcommand, every cost-estimate, before any render
**Examples:** dimensions in template constraints (Cabinet gate), no overlaps (Row gate), no walkway < 900mm (Kitchen gate), material refs resolve (CAM gate)
**Speed:** instant (<10ms)

This is what F004 ADR currently describes. Maps roughly to:
- kitchen-plugin's `validators.py` checks (config-level)
- Cabinet, Row, Kitchen, CAM-readiness gates

### Phase B — Geometric gate (post-build, bpy required)

**Where:** `kitchen-plugin/src/manifest_validator.py`
**Inputs:** `manifest.json` (the report card kitchen-plugin emits after building bpy objects)
**Required for:** verifying render output is correct (dims match expected after bpy boolean ops)
**Examples:** built dimension within tolerance of expected, no bpy mesh overlaps, vertex/face counts sane
**Speed:** runs after Blender (~5-10s per kitchen)

This is what kitchen-plugin's `manifest_validator.py` already does. F004 ADR never mentioned it. It's needed because bpy mesh operations (booleans, modifiers) can produce subtly wrong dimensions that the logical gates can't catch — the logical gates don't have actual built geometry.

### Implication for F004 rewrite

F004 becomes:
- 4 **logical** gates (Cabinet, Row, Kitchen, CAM) in Core, called by every consumer
- 1 **geometric** gate (Manifest) in kitchen-plugin, called only after render

**The 4 logical gates are mandatory before every export.** The Manifest gate is mandatory only after every render (kitchen-plugin already enforces this internally).

`Issue` and `ValidationResult` types live in Core (used by both phases). Codes are namespaced:
- DIM-001..099 = Cabinet logical
- ROW-001..099 = Row logical
- KIT-001..099 = Kitchen logical (KIT-100 reserved for F005)
- CAM-001..099 = CAM logical (CAM-100 reserved for F005)
- MFR-001..099 = Manifest geometric (new — for kitchen-plugin's bpy-output checks)

---

## 7. Organic-Design Verdict

| Check | Result |
|---|---|
| Every use case ends with the user getting what they wanted (image/CSV/DXF) without architectural detours | ✅ |
| Every data type lives in exactly one place; consumers import it | ✅ |
| Subprocess boundaries are at the right places (only where bpy needs its own process) | ✅ |
| No web → bpy direct call; always via render endpoint subprocess | ✅ |
| No CLI → web call; CLI is fully headless | ✅ |
| Same RecipeEngine called from web, CLI, render — single source of truth | ✅ |
| Same MaterialResolver called from web, CLI, render | ✅ |
| Same ValidationGates called from web (live), CLI (gate-on-export), render (config-time) | ✅ — after F004 rewrite |
| Catalog can be replaced (e.g., add a second supplier) without changing Core or callers | ✅ — Protocol pattern |
| ConstructionMethod can be swapped without changing CabinetGeometry constructor signature | ⚠️ — requires F001 refactor of kitchen-plugin/src/kitchen/cabinet_geometry.py constructor |
| kitchen-plugin can render without knowing anything about Polish materials | ✅ — gets ResolvedMaterial from Core |
| Web sidebar can render swatch previews without invoking bpy | ✅ — uses ResolvedMaterial.texture_path directly in HTML |
| **A new cabinet type is added by editing one YAML, not Python** | ✅ — after F002 + F003 extraction (currently false; that's the work) |
| **A new joinery method is added by editing one YAML, not Python** | ✅ — after F001 extraction (currently false; that's the work) |
| **A new material supplier is added by editing catalog YAMLs + 1 Producer entry** | ✅ — F005 ACL pattern |
| Layout overlaps are caught in the same place whether user is in web or CLI | ✅ — F004 Row gate |
| Cost estimate is consistent between web preview and CLI export | ✅ — same cost_estimator |

**Two new findings from this exercise:**
1. **Pricing data location** (UC2) — `Variant.price_per_sheet`? Separate `pricing/` YAML? Needs F008 decision.
2. **CAM-100 acceptance criteria** (UC3) — F005 spec must enumerate the 5 sub-checks.

**Both are now logged here and will be reflected when F005 and F008 specs are rewritten.**

---

## 8. The One Diagram That Matters

The single mental model the solo dev should carry:

```
                  ┌──────────────────────────────────────────┐
                  │     SINGLE KITCHEN YAML (on disk)        │
                  │  - walls, runs, cabinets                 │
                  │  - material_slots (kitchen-level)        │
                  │  - construction_method_id                │
                  └──────────────────┬───────────────────────┘
                                     │
                ┌────────────────────┼────────────────────┐
                │                    │                    │
                ▼                    ▼                    ▼
        ┌──────────────┐     ┌───────────────┐     ┌──────────────┐
        │  Web app     │     │   CLI         │     │   Render     │
        │  (UC1, UC2)  │     │   (UC3)       │     │   (UC1, UC2) │
        └──────┬───────┘     └───────┬───────┘     └───────┬──────┘
               │                     │                     │
               ▼                     ▼                     ▼
        ┌──────────────┐     ┌───────────────┐     ┌──────────────┐
        │  HTML +      │     │   CSV + DXF + │     │   .png +     │
        │  swatches    │     │   BOM         │     │   manifest   │
        └──────────────┘     └───────────────┘     └──────────────┘

The Kitchen YAML is the universal currency.
All three outputs are produced from the same source.
All three flows pass through the same validation gates.
All three resolve materials through the same MaterialResolver.
All three decompose cabinets through the same RecipeEngine.

If you find yourself writing different decomposition logic for two flows,
you have a bug.
```

This is the goal. If the diagram-walk above shows any place where this single-currency property breaks down, we have a design problem.

**Walking through it just now: it doesn't break.** ✅

---

## 9. What This Confirms / Refines vs Doc 07

| Doc 07 said | Diagram walk confirms / refines |
|---|---|
| kitchen-plugin's Layer 1+2 → kuchnie_core | ✅ Confirmed. Web, CLI, and Render all need `Cabinet`/`Layout`/`Run` types — these MUST be in Core. |
| F004 has 4 gates | ⚠️ **Refined: 4 logical (Core) + 1 geometric (kitchen-plugin manifest_validator). Distinct phases.** |
| F005 spec is mostly done | ⚠️ **Refined: CAM-100 needs 5-bullet sub-checks enumerated.** |
| F008 cost-estimate is straightforward | ⚠️ **Refined: pricing data location is an Open Question.** |
| kitchen-plugin renames or stays | Confirmed irrelevant — name doesn't affect data flow. Keep as `kitchen-plugin/` for less churn. |

---

## 10. Ready for Your Decision

This is the design. Walk it against your customer workflow mentally — does it feel organic?

If yes:
- Confirm Option A
- Confirm the bounded-context map (§ 1)
- Confirm Layer 1+2 promotion (kitchen-plugin/src/{core,kitchen}/ → src/kuchnie_core/)
- Confirm the two-phase validation refinement (§ 6)
- Then I'll proceed with the 5 hours of spec rewrites per doc 07 § 6

If something feels forced:
- Point at it specifically — which step in which UC?
- We'll re-design that seam before committing.

Two specific seams worth eyeballing:

**Seam A — render endpoint in Reflex.** kitchen-app spawns Blender via subprocess. Is this acceptable for the iPad use case (UC1)? Or do you want a separate "render service" daemon (more complex but faster)? For v1.0 solo dev I'd say subprocess-per-request is fine, but flag it now if you disagree.

**Seam B — Layer 1+2 promotion timing.** Doing this NOW (before F001) means a one-time refactor of kitchen-plugin's 22 tests. Doing it LATER means F001-F004 specs reference paths that will change. I strongly recommend NOW, but flag if you'd rather defer.
