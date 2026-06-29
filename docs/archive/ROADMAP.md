# ROADMAP

                                                                                                               
 ```                                                                                                                                                     
   WHERE WE ARE                                                                                                                                          
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━                                                                                                          
   ✅ Phase 0: Core engine (84 tests, 3 types, JSON, CSV, BOM)                                                                                           
                                                                                                                                                         
                                                                                                                                                         
   WHAT'S NEXT (two independent tracks)                                                                                                                  
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━                                                                                                          
                                                                                                                                                         
     MANUFACTURING TRACK          VISUALIZATION TRACK                                                                                                    
     (you need this daily)        (you need this to sell)                                                                                                
                                                                                                                                                         
     Phase 1: Cabinet taxonomy    Phase 5: Blender renders                                                                                               
          │                            │                                                                                                                 
     Phase 2: Machining ops       Phase 6: Web app                                                                                                       
          │                                                                                                                                              
     Phase 3: DXF export                                                                                                                                 
          │                                                                                                                                              
     Phase 4: CLI polish                                                                                                                                 
                                                                                                                                                         
                                                                                                                                                         
   RECOMMENDED ORDER FOR SOLO CABINET MAKER                                                                                                              
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━                                                                                                          
                                                                                                                                                         
     1. Phase 1+2 → model any kitchen, accurate cut lists                                                                                                
     2. Phase 3+4 → send DXF to CNC company directly                                                                                                     
     3. Phase 5   → show customers 2.5D renders                                                                                                          
     4. Phase 6   → visual editor (nice-to-have)                                                                                                         
 ```           
 
## Where we are

```
✅ Phase 0: Walking skeleton + LEGRABOX
   84 tests, 3 cabinet types, intermediate JSON, cut list CSV, BOM
```

## Dependency graph

```
Phase 1 ──► Phase 2 ──► Phase 3 ──► Phase 4
(catalog)    (machining)  (DXF)       (CLI)
                                   
Phase 1 ──► Phase 5 ──► Phase 6
(catalog)    (Blender)    (web app)
```

Phases 3–4 (manufacturing) and 5–6 (visualization) are **independent tracks**. You can work on either first depending on what's more urgent for your business.

---

## Phase 1 — Complete cabinet taxonomy

Add remaining cabinet types from your variants document.

| Type | Complexity | Blocks |
|---|---|---|
| `dolna_standard` (1-door, 2-door) | Low | — |
| `dolna_slepa_narozna` (blind corner) | Medium | new panel geometry |
| `dolna_wew_narozna` (internal corner + Optima) | High | carousel shelves |
| `dolna_zlewowa` (sink base) | Low | plumbing cutout config |
| `dolna_cargo` (pull-out larder) | Medium | cargo basket accessory |
| `dolna_piekarnik` (oven housing) | Low | fixed shelf, height range |
| `gorna_narozna` (wall corner) | Medium | angled front |
| `slupek` (tall larder / SPACE TOWER) | High | inner pull-outs |

Each type = one `decompose_<type>` function + fixture YAML + tests.

**Deliverable:** any kitchen can be modeled with cabinet types from the catalog.

---

## Phase 2 — Complete machining operations

Add drill/groove ops to existing cabinet types.

| Operation | Applies to | Source |
|---|---|---|
| Shelf pin holes (System32) | Side panels (all types with shelves) | 32mm grid, 3 holes/position, 37mm from front |
| Handle boring | Front panels (doors + drawers) | Position presets from your section 7 analysis |
| Hinge cup boring | Door fronts (35mm cup) | Blum ClipTop template |
| LED groove | Top/bottom panels (under-wall-cabinet) | Configurable position + width |
| Vent holes | Custom positions (user-specified) | Per-cabinet override |

**Deliverable:** every panel in the decomposition carries its complete machining ops.

---

## Phase 3 — DXF export

Panels + machining ops → DXF files for CNC company.

```
DecompositionResult
    └── panels[].machining_ops
            │
            ▼
    export/dxf.py → {panel_id}.dxf
            │
            ▼
    CNC company quotes + manufactures
```

**Deliverable:** one DXF per panel, with outlines + drill points + grooves. Ready to send to CNC.

---

## Phase 4 — CLI enhancements

Polish the kitchen-cli for daily use.

| Command | Output |
|---|---|
| `kitchen cutlist kitchen.json` | CSV for e-rozrys (already done, needs e-rozrys format validation) |
| `kitchen dxf kitchen.json` | DXF files per panel |
| `kitchen bom kitchen.json` | Costed BOM with pricing |
| `kitchen validate kitchen.json` | Dimension + compatibility checks |
| `kitchen estimate kitchen.json` | Cost with nesting estimation |

**Deliverable:** one command from intermediate JSON to manufacturing-ready output.

---

## Phase 5 — Blender render service

FastAPI + headless Blender for 2.5D customer renders.

```
intermediate.json → FastAPI → Blender scene builder → 2.5D image
                                │
                                ├── parametric cabinet meshes
                                ├── texture application (Kronospan, Egger)
                                └── living setup (pre-made room .blend)
```

| Component | Detail |
|---|---|
| Scene builder | intermediate.json → Blender objects (uses kuchnie_core for panel geometry) |
| Texture engine | Decor catalog → Blender materials (texture maps from Kronospan/Egger) |
| Camera presets | 2.5D isometric views, fixed lighting |
| Living setups | Pre-made .blend rooms (small kitchen, large kitchen, L-shape) |
| API | `POST /render` → image URL |

**Deliverable:** kitchen-app can request a render and get back a 2.5D image.

---

## Phase 6 — Kitchen plugin web app

Svelte layout editor for kitchen design.

| Feature | Detail |
|---|---|
| Row editor | Create rows with wall dimensions, place cabinets left-to-right |
| Cabinet sidebar | Drag cabinet types from catalog into rows |
| Global config | Worktop height, plinth, cabinet depth defaults |
| Decor picker | Swap decors per category (body, front, worktop) |
| BOM panel | Batch cost calculation on demand |
| Render button | Sends intermediate.json to render service, shows result |
| Export | Download intermediate JSON, cut list CSV, DXF |

**Deliverable:** visual kitchen design → manufacturing output, all in the browser.

---

## Suggested order for a solo cabinet maker

```
NOW          Phase 1 (fill taxonomy) + Phase 2 (machining)
             → you can model any real kitchen and get accurate cut lists

NEXT         Phase 3 (DXF) + Phase 4 (CLI polish)
             → you can send files to CNC company directly from the tool

THEN         Phase 5 (Blender renders)
             → you can show customers 2.5D visuals before manufacturing

FINALLY      Phase 6 (web app)
             → nice-to-have UX, but YAML + CLI works for solo workflow
```

---

## Not in scope (v1.0)

| Feature | Reason |
|---|---|
| Nesting optimization | CNC company does this (you buy material, they nest) |
| Island layouts | v2.0 — complex room geometry |
| Slanted walls | v2.0 — requires parametric room model |
| Multi-user / cloud | Solo developer doesn't need this |
| Real-time cost in browser | Batch is sufficient (ADR-level decision) |
