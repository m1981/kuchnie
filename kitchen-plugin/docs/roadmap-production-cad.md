# Roadmap: From Kitchen Generator to Production-Ready Kitchen CAD

## Where We Are

```
  JSON config → Blender geometry → Manifest (validation) → .blend file
                                        ↓
                              Customer can't see anything useful
```

We can generate parametric cabinet geometry and validate it. But the output
is wireframe Blender scenes with no materials, no realistic rendering, and
no production data.

## Where We Need to Get

```
  JSON config → Parametric geometry → Realistic render (customer-facing)
                    ↓                        ↓
              Production data          Material variants
              (BOM, cut list,          (customer chooses)
               CNC, hardware)
                    ↓
              Manufacturing
              (panel saw → CNC → edge bander → assembly)
```

This is what IMOS, CET by Configura, and Winner do. The gap is large but
the architecture is sound — we need to build the right layers on top.

---

## Phase 1: Realistic Customer Renders

**Goal:** Customer sees a photorealistic kitchen and can choose materials.

### 1.1 Material System

IMOS/CET/Winner all use a **material catalog** — not hardcoded colors.

```
Current:
  materials: { "carcass": { "color": [0.9, 0.9, 0.88] } }

Target:
  materials: {
    "carcass": {
      "id": "white-melamine-18",
      "name": "White Melamine 18mm",
      "color": "#F5F5F0",
      "roughness": 0.4,
      "texture": "textures/melamine_white_1k.jpg",
      "bump": "textures/melamine_bump_1k.jpg",
      "thickness_mm": 18,
      "board_type": "chipboard",
      "edge_material": "white-abs-1mm"
    },
    "front": {
      "id": "cashmere-mdf-19",
      "name": "Cashmere Matt MDF 19mm",
      "color": "#D4C5B2",
      "roughness": 0.15,
      "texture": "textures/mdf_cashmere_1k.jpg",
      "thickness_mm": 19,
      "board_type": "mdf",
      "edge_material": "cashmere-abs-1mm"
    }
  }
```

**What to implement:**
- Material catalog JSON schema (`schemas/material_catalog.schema.json`)
- PBR texture loading (color, roughness, normal/bump maps)
- Material assignment by component type (carcass, front, back, counter)
- Texture UV mapping for board patterns (grain direction)
- Material swap at runtime (customer changes front color)

**Effort:** 2–3 weeks

### 1.2 Scene Setup for Rendering

IMOS/CET/Winner renders show kitchens in a room context — walls, floor,
countertop, appliances, lighting. We need at minimum:

```
Scene components:
  ├── Kitchen geometry (our existing output)
  ├── Room shell (floor, walls, ceiling)
  ├── Lighting (HDRI environment + accent lights)
  ├── Camera positions (standard views: front, corner, bird's eye)
  └── Background / environment
```

**What to implement:**
- Room template system (L-shaped room, U-shaped room, galley)
- Camera presets (front elevation, 3/4 view, top-down)
- HDRI environment lighting (Blender Cycles world shader)
- Shadow catcher floor plane
- Render presets (quality vs speed)

**Effort:** 1–2 weeks

### 1.3 Render Pipeline

```
  Config → Build geometry → Apply materials → Set up scene → Render → Image
                                        ↓
                              Multiple views in one pass:
                              - Front elevation (2D-ish)
                              - 3/4 perspective (hero shot)
                              - Top-down plan view
```

**What to implement:**
- Multi-view render script (batch all views in one Blender run)
- Resolution presets (preview: 800×600, customer: 1920×1080, print: 4K)
- Denoising for faster renders
- Output naming convention (`{config}_front.png`, `{config}_perspective.png`)
- Optional: Cycles vs EEVEE toggle (quality vs speed)

**Effort:** 1 week

### 1.4 Material Variant Generation

Customers want to compare options: "What does it look like in white vs grey?"

```
  Config + Material Variant A → Render A
  Config + Material Variant B → Render B
  Config + Material Variant C → Render C
                                  ↓
                        Side-by-side comparison grid
```

**What to implement:**
- Variant definition in config:
  ```json
  "variants": [
    { "name": "White", "front": "white-melamine", "counter": "white-quartz" },
    { "name": "Grey", "front": "grey-mdf", "counter": "grey-granite" }
  ]
  ```
- Batch render per variant
- Comparison grid generator (ImageMagick or Python PIL)

**Effort:** 1 week

---

## Phase 2: Production Data Output

**Goal:** Every design produces a complete manufacturing data package.

### 2.1 Bill of Materials (BOM)

IMOS/CET/Winner generate a BOM that purchasing and production use directly.

```json
{
  "format": "kitchen-bom",
  "version": "1.0",
  "project": "L-Shape Kitchen 3.2m + 1.8m",
  "generated_at": "2025-01-15T10:30:00Z",
  "summary": {
    "total_panels": 28,
    "total_board_area_m2": 12.4,
    "total_edge_length_m": 45.2,
    "total_hinges": 16,
    "total_drawer_slides": 8,
    "total_handles": 10
  },
  "panels": [
    {
      "part_id": "P001",
      "name": "run0_base_0_left_side",
      "cabinet": "run0_base_0_base-door",
      "material": "white-melamine-18",
      "width_mm": 560,
      "height_mm": 720,
      "thickness_mm": 18,
      "quantity": 1,
      "grain_direction": "vertical",
      "edge_banding": [
        { "side": "front", "material": "white-abs-1mm", "thickness_mm": 1 },
        { "side": "top", "material": "white-abs-1mm", "thickness_mm": 1 }
      ],
      "drilling": [
        { "type": "shelf_pin", "x_mm": 280, "y_mm": 350, "diameter_mm": 5, "depth_mm": 12 },
        { "type": "shelf_pin", "x_mm": 280, "y_mm": 450, "diameter_mm": 5, "depth_mm": 12 }
      ],
      "cutout": [
        { "type": "back_groove", "offset_from_rear_mm": 10, "width_mm": 3.2, "depth_mm": 9 }
      ]
    }
  ],
  "hardware": [
    {
      "type": "hinge",
      "product_code": "BLM-71B3550",
      "description": "Blum CLIP top 110° hinge",
      "quantity": 4,
      "cabinets": ["run0_base_0_base-door"]
    },
    {
      "type": "drawer_slide",
      "product_code": "BLM-550H5330B",
      "description": "Blum TANDEMBOX 500mm",
      "quantity": 3,
      "cabinets": ["run0_base_1_base-drawers"]
    }
  ]
}
```

**What to implement:**
- Panel extraction from geometry (each cabinet → 6 panels: top, bottom, left, right, back, front)
- Edge banding metadata per panel edge
- Hardware catalog (hinges, slides, handles, shelf pins)
- BOM aggregation (group identical parts, sum quantities)
- BOM export (JSON + CSV for spreadsheets)

**Effort:** 2–3 weeks

### 2.2 Cut List with Optimization

A cut list tells the panel saw what to cut. Optimization minimizes waste.

```
Sheet stock: 2800mm × 2070mm (standard European board size)

Current approach: cut each panel individually
Optimized approach: nest panels on sheets to minimize waste

  ┌─────────────────────────────────────────────────────────┐
  │ Sheet 1: White Melamine 18mm                            │
  │                                                         │
  │  ┌──────────┐ ┌──────────┐ ┌────────┐ ┌──────────┐     │
  │  │ Left side│ │ Right    │ │ Bottom │ │ Top      │     │
  │  │ 560×720  │ │ 560×720  │ │ 564×547│ │ 564×547  │     │
  │  └──────────┘ └──────────┘ └────────┘ └────────┘       │
  │                                                         │
  │  Waste: 12.4%                                           │
  └─────────────────────────────────────────────────────────┘
```

**What to implement:**
- Panel nesting algorithm (2D bin packing)
- Sheet stock definition (sizes, materials)
- Kerf width (saw blade thickness)
- Grain direction constraint (panels must align with board grain)
- Waste percentage calculation
- Cut sequence optimization (minimize saw head movement)

**Effort:** 2–3 weeks (nesting algorithm is the hard part)

### 2.3 CNC Output

For manufacturers with CNC routers (HOMAG, Biesse, SCM, Felder):

```
CNC operations per panel:
  1. Through-cuts (panel outline)
  2. Drilling (shelf pins, hinge cups, drawer slide screws)
  3. Grooving (back panel groove, dado joints)
  4. Routing (edge profiles, decorative cuts)

Output formats:
  ├── DXF (2D profiles for panel saws)
  ├── HOPS (HOMAG CNC programs)
  ├── WoodWOP (HOMAG parametric programs)
  ├── bSolid (Biesse programs)
  └── ISO G-code (universal CNC)
```

**What to implement:**
- DXF export per panel (outline + drilling points)
- G-code generation for basic operations (drilling, grooving)
- Tool library (drill bits, saw blades, router bits)
- Machine-specific post-processors (HOMAG, Biesse)

**Effort:** 4–6 weeks (CNC is complex, start with DXF)

### 2.4 Hardware Placement

IMOS/CET/Winner place hardware automatically based on rules:

```
Hinge rules:
  - Door height < 700mm → 2 hinges
  - Door height 700-1200mm → 3 hinges
  - Door height > 1200mm → 4 hinges
  - Top hinge: 100mm from top edge
  - Bottom hinge: 100mm from bottom edge
  - Middle hinges: evenly distributed

Drawer slide rules:
  - Slide length = drawer depth - 25mm (standard)
  - Mounting: 37mm below drawer bottom (Blum TANDEMBOX)
  - Screws: 4 per slide (2 front, 2 rear)

Shelf pin rules:
  - 32mm system spacing
  - First row: 64mm from bottom
  - Rows every 32mm up to 64mm from top
  - 2 pins per shelf side (front and rear)
```

**What to implement:**
- Hardware rule engine (configurable per manufacturer)
- Hinge placement calculator
- Drawer slide placement calculator
- Shelf pin pattern generator
- Handle placement (door center, drawer center, or offset)

**Effort:** 1–2 weeks

---

## Phase 3: The "Secret Sauce" — Design Intelligence

This is what separates IMOS/CET/Winner from simple 3D generators.

### 3.1 Constraint-Based Layout

Current: cabinets are placed at fixed positions from config.
Target: cabinets snap to walls, fill gaps, auto-adjust to room size.

```
Current (static):
  "base": [
    { "type": "base-door", "width": 600 },
    { "type": "base-drawers", "width": 600 },
    { "type": "filler", "width": 100 }
  ]

Target (constrained):
  "base": [
    { "type": "base-door", "width": "auto" },        ← fills available space
    { "type": "base-drawers", "width": 600 },
    { "type": "filler", "width": "remaining" }        ← whatever is left
  ]
```

**What to implement:**
- Constraint types: fixed, auto, remaining, fill
- Dependency solver (resolve constraints in order)
- Standard width matching (auto → nearest standard width)
- Gap distribution (evenly space fillers)

**Effort:** 2–3 weeks

### 3.2 Corner Intelligence

This is the **#1 bug right now** — U-shape corners overlap.

```
Corner types in professional software:
  ┌─────────────────────────────────────────────────────────┐
  │                                                         │
  │  1. BLIND CORNER                                        │
  │     ┌───────────────┐                                   │
  │     │               │                                   │
  │     │   ┌───────────┤                                   │
  │     │   │  hidden   │ ← dead space behind               │
  │     │   │  space    │                                   │
  │     │   │           │                                   │
  │     └───┘           │                                   │
  │         └───────────┘                                   │
  │                                                         │
  │  2. DIAGONAL CORNER                                     │
  │     ┌───────────────┐                                   │
  │     │           ╱   │                                   │
  │     │         ╱     │                                   │
  │     │       ╱       │                                   │
  │     │     ╱         │                                   │
  │     │   ╱           │                                   │
  │     │ ╱             │                                   │
  │     └───────────────┘                                   │
  │                                                         │
  │  3. SUPER-CORNER (LeMans, Kessebohmer)                  │
  │     ┌───────────────┐                                   │
  │     │   ┌───────┐   │                                   │
  │     │   │ pull  │   │ ← swivel-out shelves              │
  │     │   │  out  │   │                                   │
  │     │   │ shelf │   │                                   │
  │     │   └───────┘   │                                   │
  │     └───────────────┘                                   │
  │                                                         │
  │  4. L-SHAPE CORNER CABINET                              │
  │     ┌───────────────┐                                   │
  │     │               │                                   │
  │     │   ┌───────────┘                                   │
  │     │   │           ← single cabinet spanning both walls│
  │     │   │           │                                   │
  │     └───┘           │                                   │
  │                                                         │
  └─────────────────────────────────────────────────────────┘
```

**What to implement:**
- Corner detection: identify where two runs meet at 90°
- Corner space calculation: how much space is available at the junction
- Last-cabinet-before-corner: reduce width or replace with corner cabinet
- First-cabinet-after-corner: offset start position by corner depth
- Corner cabinet types: blind, diagonal, L-shape, super-corner
- Corner filler: auto-generate filler for gap between corner and adjacent

**Critical fix (immediate):** The last cabinet before a corner turn must be
trimmed or replaced so it doesn't extend into the corner space.

```
Current (broken):
  Run 1 (east):  [600] [600] [800] [600] [900] ← extends to corner
  Run 2 (south): [900 corner-blind] [600] [400]
                 ↑ overlaps by 560mm

Fixed:
  Run 1 (east):  [600] [600] [800] [600] [900] ← still 900mm
  Run 2 (south): [900 corner] [600] [400]
                 ↑ corner cabinet starts AFTER run1's last cabinet ends
```

**Effort:** 3–4 weeks (corner logic is the hardest part)

### 3.3 Appliance Integration

Professional tools include standard appliance models:

```
Appliance types:
  ├── Built-in oven (600mm wide, standard heights)
  ├── Cooktop (600/800/900mm)
  ├── Range hood (600/900mm)
  ├── Fridge (600/700mm wide, various heights)
  ├── Dishwasher (600mm)
  ├── Sink (various sizes, undermount/topmount)
  └── Microwave (built-in, 600mm)

Integration:
  - Appliance catalog (dimensions, cutout requirements)
  - Auto-deduction from cabinet (oven cabinet has no internal shelves)
  - Sink cutout in countertop
  - Hood clearance calculation
```

**What to implement:**
- Appliance catalog JSON schema
- Standard appliance dimensions (European standards)
- Appliance placeholder geometry (simple box with label)
- Countertop sink cutout generation
- Clearance validation (oven above plinth, hood above cooktop)

**Effort:** 2 weeks

### 3.4 Design Rules Engine

IMOS/CET/Winner enforce design rules automatically:

```python
DESIGN_RULES = {
    # Safety
    "min_walkway_width_mm": 900,        # Between opposing cabinets
    "min_work_triangle_mm": 3600,       # Sum of sink-stove-fridge distances
    "max_work_triangle_mm": 7900,
    "hood_clearance_gas_mm": 650,       # Above gas cooktop
    "hood_clearance_electric_mm": 550,  # Above electric cooktop

    # Ergonomics
    "base_counter_height_mm": 850-920,  # Worktop height (user-dependent)
    "wall_cabinet_reach_mm": 1850,      # Max height for wall cabinet bottom
    "drawer_min_height_mm": 120,        # Minimum usable drawer height

    # Construction
    "max_span_without_support_mm": 800, # Shelf sag limit
    "min_filler_width_mm": 50,          # Minimum useful filler
    "max_cabinet_width_mm": 1200,       # Maximum single cabinet

    # Aesthetics
    "symmetry_tolerance_mm": 50,        # Balance check for visual symmetry
    "filler_placement": "ends_only",    # Fillers at run ends, not middle
}
```

**What to implement:**
- Rule definition schema
- Rule engine (evaluate rules against layout)
- Warning vs error severity
- Auto-fix suggestions ("Move filler to end of run")

**Effort:** 2 weeks

---

## Phase 4: Customer Interaction Layer

### 4.1 Configuration UI

IMOS/CET/Winner have drag-and-drop interfaces. We can start simpler:

```
Levels of customer interaction:

  Level 1 (NOW): JSON config → render → customer sees result
  Level 2 (NEXT): Web form → generates JSON → render → customer iterates
  Level 3 (FUTURE): Interactive 2D plan → auto-generates 3D → real-time preview
  Level 4 (GOAL): Drag-and-drop cabinets in 3D → real-time render
```

**Level 2 — Web Form:**

```
┌─────────────────────────────────────────────────────────────┐
│ Kitchen Layout Generator                                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ Layout: ( ) I-shape  (●) L-shape  ( ) U-shape               │
│                                                             │
│ Back wall: 3200mm                                           │
│ Left wall: 1800mm                                           │
│                                                             │
│ Base cabinets:                                              │
│   [Filler 50mm] [Oven 600mm] [Drawers 600mm] [Sink 800mm]  │
│   [+ Add cabinet]                                           │
│                                                             │
│ Front style: [Cashmere Matt ▼]                              │
│ Countertop:  [White Quartz ▼]                               │
│                                                             │
│ [Generate Preview] [Compare Variants] [Download BOM]        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Effort:** 2–4 weeks (depends on web framework)

### 4.2 Multi-Config Comparison

```
┌─────────────────────────────────────────────────────────────┐
│ Compare Kitchen Variants                                    │
├──────────────┬──────────────┬──────────────┬────────────────┤
│ Option A     │ Option B     │ Option C     │ Option D       │
│              │              │              │                │
│ [render]     │ [render]     │ [render]     │ [render]       │
│              │              │              │                │
│ White        │ Cashmere     │ Grey         │ Dark Grey      │
│ Laminate     │ Matt MDF     │ Matt MDF     │ Gloss          │
│              │              │              │                │
│ €4,200       │ €5,100       │ €5,300       │ €6,800         │
│              │              │              │                │
│ [Select]     │ [Select]     │ [Select]     │ [Select]       │
└──────────────┴──────────────┴──────────────┴────────────────┘
```

**Effort:** 1–2 weeks (batch renders + image grid)

---

## Implementation Roadmap

```
  PHASE 1: REALISTIC RENDERS (customer-facing)
  ─────────────────────────────────────────────
  Q1:
    Week 1-2:   Material catalog schema + PBR textures
    Week 3:     Scene setup (room, lighting, camera presets)
    Week 4:     Multi-view render pipeline
    Week 5:     Material variant generation
    Week 6:     Comparison grid output

  PHASE 2: PRODUCTION DATA (manufacturer-facing)
  ──────────────────────────────────────────────
  Q2:
    Week 1-2:   Panel extraction from geometry
    Week 3-4:   BOM generation (panels + hardware)
    Week 5-6:   Cut list with optimization
    Week 7-8:   DXF export for panel saws

  PHASE 3: DESIGN INTELLIGENCE (the "secret sauce")
  ─────────────────────────────────────────────────
  Q3:
    Week 1-2:   Fix corner handling (CRITICAL)
    Week 3-4:   Plinth platform system
    Week 5-6:   Hardware placement rules
    Week 7-8:   Constraint-based layout
    Week 9-10:  Design rules engine
    Week 11-12: Appliance integration

  PHASE 4: CUSTOMER INTERACTION
  ─────────────────────────────
  Q4:
    Week 1-4:   Web configuration form
    Week 5-6:   Multi-variant comparison
    Week 7-8:   Cost estimation
    Week 9-12:  Interactive 2D plan (stretch goal)
```

---

## Architecture Changes Needed

### New Modules

```
src/
├── core/                          # Existing
├── kitchen/                       # Existing
├── rendering/                     # NEW: Phase 1
│   ├── material_catalog.py        # Material definitions + textures
│   ├── scene_setup.py             # Room, lighting, camera
│   ├── render_pipeline.py         # Multi-view batch rendering
│   └── variant_generator.py       # Material variant comparison
│
├── production/                    # NEW: Phase 2
│   ├── panel_extractor.py         # Geometry → panels
│   ├── bom_generator.py           # Panel + hardware BOM
│   ├── cut_list.py                # Cut optimization
│   ├── dxf_export.py              # DXF for panel saws
│   └── cnc_export.py              # G-code for CNC routers
│
├── hardware/                      # NEW: Phase 3
│   ├── catalog.py                 # Hardware catalog (hinges, slides)
│   ├── hinge_placer.py            # Automatic hinge placement
│   ├── slide_placer.py            # Drawer slide placement
│   └── shelf_pin_placer.py        # 32mm system shelf pins
│
├── rules/                         # NEW: Phase 3
│   ├── design_rules.py            # Rule definitions
│   ├── rule_engine.py             # Rule evaluation
│   └── auto_fix.py                # Suggested corrections
│
├── geometry_builder.py            # Existing (needs corner fix)
├── geometry_manifest.py           # Existing
└── main.py                        # Existing (needs new flags)
```

### New CLI Flags

```bash
# Render pipeline
blender --background --python src/main.py -- config.json \
    --render \
    --render-views front,perspective,top \
    --render-resolution 1920x1080 \
    --material-variant "White"

# Production data
blender --background --python src/main.py -- config.json \
    --export-bom \
    --export-cutlist \
    --export-dxf

# Design validation
blender --background --python src/main.py -- config.json \
    --validate \
    --check-rules
```

### New Config Sections

```json
{
  "version": "2.0",
  "name": "Customer Kitchen",

  "materials": {
    "catalog": "materials/european_standard.json",
    "carcass": "white-melamine-18",
    "front": "cashmere-mdf-19",
    "counter": "white-quartz-30",
    "plinth": "white-melamine-18"
  },

  "variants": [
    {
      "name": "White Modern",
      "front": "white-melamine-19",
      "counter": "white-quartz-30",
      "handle": "gola-white-1200"
    },
    {
      "name": "Grey Matt",
      "front": "grey-mdf-19",
      "counter": "grey-granite-30",
      "handle": "rail-grey-160"
    }
  ],

  "room": {
    "width_mm": 3500,
    "depth_mm": 2500,
    "height_mm": 2500,
    "wall_color": "#FFFFFF",
    "floor_material": "oak-parquet"
  },

  "hardware": {
    "hinge_brand": "blum",
    "slide_brand": "blum",
    "handle_style": "rail"
  },

  "production": {
    "sheet_stock": [
      { "material": "white-melamine-18", "width_mm": 2800, "height_mm": 2070 }
    ],
    "edge_stock": [
      { "material": "white-abs-1mm", "width_mm": 23, "length_m": 100 }
    ],
    "cnc_machine": "homag-centateq"
  },

  "settings": { ... },
  "runs": [ ... ]
}
```

---

## What IMOS/CET/Winner Do That We Should Study

### IMOS Approach

```
IMOS data flow:
  Product catalog → 3D model → BOM → CNC program → Machine

Key insight: The 3D model is NOT the primary output.
The BOM and CNC programs are. The 3D model is a visualization
of the production data, not the other way around.

Lesson for us:
  Our manifest should evolve to include production data.
  The render is a VIEW of the data, not the data itself.
```

### CET by Configura Approach

```
CET data flow:
  Component catalog → Drag & drop → Auto-connect → Render + Quote

Key insight: Components are SMART OBJECTS with rules.
A cabinet knows:
  - What walls it can go on
  - What it needs next to it (filler, corner unit)
  - What hardware it requires
  - What it costs

Lesson for us:
  Our Cabinet objects should carry production metadata.
  Not just dimensions, but requirements and constraints.
```

### Winner Approach

```
Winner data flow:
  Customer meeting → Quick sketch → 3D render → Quote → Order → Production

Key insight: Speed of iteration matters more than accuracy.
The customer sees 5 variants in 10 minutes, not 1 variant in 1 hour.

Lesson for us:
  Fast renders (EEVEE, 800×600) for iteration.
  High-quality renders (Cycles, 4K) for final approval.
  Material swaps should be instant, not require rebuild.
```

---

## Key References

| Resource | What it teaches |
|---|---|
| IMOS documentation | CAD → CAM pipeline for furniture |
| Configura CET SDK | Component-based parametric design |
| Blum product catalog | Hardware specifications and mounting rules |
| HOMAG WoodWOP | CNC program format for wood routers |
| European 32mm system standard | Shelf pin, hinge, and slide positioning |
| DIN 68871 | German standard for kitchen dimensions |
| EN 14749 | European standard for domestic kitchen furniture |
| NestPy / RectBinPack | 2D bin packing algorithms for cut optimization |
