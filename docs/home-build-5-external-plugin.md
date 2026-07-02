# Home Builder 5 — External Blender Plugin Analysis

> Assessment of the third-party `home_builder_5` Blender addon against the
> `kuchnie-core` manufacturing pipeline. Scope: fit, gaps, integration options.

## Executive summary

`home_builder_5` is a production-grade Blender addon for kitchen/home design
(~50,000+ lines). It ships two complete cabinet systems — **Face Frame**
(American) and **Frameless** (European) — plus a full room/wall engine, layout
documentation, and PDF export.

The **Frameless** library directly matches European construction (System 32,
18mm carcass, 3mm HDF back, 19mm fronts, overlay doors, 560/720/120 base
defaults). It is a strong **design-side** tool but has **no manufacturing
output** (no BOM, no cut list, no CNC/DXF, no Blum hardware catalog).

**Recommendation:** use the plugin for design and visualization, keep
`kuchnie-core` for manufacturing. Bridge the two via a JSON geometry manifest.

---

## Architecture overview

```
home_builder_5/
├── Core System
│   ├── Wall/Room Engine       (operators/walls.py)
│   ├── Placement System       (hb_placement.py)
│   ├── Snapping Engine        (hb_snap.py)
│   └── Layout/Documentation   (hb_layouts.py)
│
├── Product Libraries
│   ├── face_frame/    American style (face frames, stiles, rails)
│   ├── frameless/     European style (System 32, no face frames)
│   ├── closets/       Closet systems
│   └── common/        Appliances, wood hoods
│
├── UI System
│   ├── Sidebar Panels     (view3d_sidebar.py)
│   ├── Context Menus      (menus.py)
│   ├── HUD/Navigator      (viewport_hud.py, scene_navigator.py)
│   └── Catalog Browser    (catalog/)
│
└── Documentation
    ├── Layout Views  (Elevation, Plan, 3D, Multi)
    ├── Detail Library (2D drawings)
    └── PDF Export
```

---

## Feature matrix vs. kuchnie-core needs

### European cabinet construction

| Feature                | Our need   | Plugin status  | Notes                                    |
| ---------------------- | ---------- | -------------- | ---------------------------------------- |
| Frameless construction | Critical   | ✅ Full support | `frameless/types_frameless.py`           |
| System 32 (32mm grid)  | Critical   | ✅ Implemented  | Boring patterns in `GeoNodeCutpart`      |
| 18mm carcass thickness | Standard   | ✅ Configurable | `corpusThickness: 18` default            |
| 3mm HDF back panel     | Standard   | ✅ Configurable | `backThickness: 3` default               |
| 19mm MDF fronts        | Standard   | ✅ Configurable | `frontThickness: 19` default             |
| Overlay doors          | Standard   | ✅ Full overlay | `frontOverlay: 2`                        |
| 560mm base depth       | Standard   | ✅ Default      | `baseDepth: 560`                         |
| 720mm base height      | Standard   | ✅ Default      | `baseBodyHeight: 720`                    |
| 120mm plinth height    | Standard   | ✅ Default      | `plinthHeight: 120`                      |
| 300mm wall depth       | Standard   | ✅ Default      | `wallDepth: 300`                         |
| Legrabox drawers       | Blum       | ✅ Implemented  | `GeoNodeDrawerBox` class                 |
| Concealed hinges       | Blum       | ⚠️ Partial     | Door swing exists, no Blum ClipTop spec  |
| Edge banding           | Required   | ⚠️ Visual only | No thickness/material tracking           |

### Cabinet types coverage

| Type              | In our `CABINET-VARIANTS.md` | Plugin support                        |
| ----------------- | ---------------------------- | ------------------------------------- |
| Base 1-door       | ✅                            | ✅ `BaseCabinet`                       |
| Base 2-door       | ✅                            | ✅ `BaseCabinet.add_doors()`           |
| Base 1-drawer     | ✅                            | ✅ `BaseCabinet.add_drawer_door()`     |
| Base 2/3/4-drawer | ✅                            | ✅ `BaseCabinet.add_drawer_stack(n)`   |
| Corner blind      | ✅                            | ⚠️ Not explicit in frameless         |
| Corner diagonal   | ✅                            | ✅ `DiagonalCornerBaseCabinet`         |
| Corner pie cut    | ✅                            | ✅ `PieCutCornerBaseCabinet`           |
| Sink base         | ✅                            | ✅ `BaseCabinet` (configurable)        |
| Cargo / pullout   | ✅                            | ✅ `Pullout` class                     |
| Oven housing      | ✅                            | ✅ `TallCabinet` + appliance           |
| Wall cabinets     | ✅                            | ✅ `UpperCabinet`                      |
| Tall cabinets     | ✅                            | ✅ `TallCabinet`, `RefrigeratorCabinet`|

### Drawer system (Blum)

| Component                | Our spec | Plugin status              |
| ------------------------ | -------- | -------------------------- |
| TANDEMBOX antaro         | ✅        | ⚠️ Generic drawer box     |
| MERIVOBOX                | ✅        | ⚠️ Not differentiated     |
| LEGRABOX                 | ✅        | ⚠️ Generic implementation |
| Height codes (N/M/D/S/C) | ✅        | ❌ Not modeled             |
| Runner lengths           | ✅        | ❌ Not modeled             |
| Blumotion / Tip-On       | ✅        | ❌ Not modeled             |

**Gap:** drawer hardware is visual-only; no Blum catalog integration.

---

## What the plugin does well

### 1. Interactive placement

```python
# From ops_placement.py — wall snapping, gap detection, dimension typing
class hb_frameless_OT_place_cabinet(bpy.types.Operator, WallObjectPlacementMixin):
    def find_nearest_wall_from_cursor(self, context): ...
    def set_position_on_wall(self, context): ...
    def position_snapped_to_cabinet(self): ...
    def calculate_auto_quantity(self, gap_width: float) -> int: ...
```

- Snap to walls
- Snap to adjacent cabinets
- Auto-detect gaps
- Type dimensions during placement
- Auto-quantity calculation

### 2. Parametric cabinets

```python
# From types_frameless.py — full parametric control
class Cabinet(GeoNodeCage):
    def create_base_carcass(self, name): ...
    def create_tall_carcass(self, name): ...
    def create_upper_carcass(self, name): ...
```

- Geometry-nodes based (procedural)
- Driver-driven dimensions
- Real-time recalculation

### 3. Layout documentation

```python
# From hb_layouts.py — professional output
class ElevationView(LayoutView):
    def create(self, wall_obj, name, paper_size, landscape): ...
    def add_cabinet_dimensions(self): ...

class PlanView(LayoutView):
    def create(self, name, source_scene, paper_size, landscape): ...
```

- Elevation views with auto-dimensioning
- Plan views, 3D perspectives, multi-view layouts
- PDF export, title blocks, freestyle line rendering

### 4. Style system

```python
# From props_hb_frameless.py — material management
class Frameless_Cabinet_Style(PropertyGroup):
    def get_finish_material(self): ...
    def assign_style_to_cabinet(self, cabinet_obj): ...

class Frameless_Door_Style(PropertyGroup):
    def assign_style_to_front(self, front_obj): ...
```

- Cabinet styles (finish, interior material)
- Door styles (5-piece, slab)
- Pull / handle styles
- Custom finish colors

---

## Gaps and concerns

### 1. No CNC / cut list export

Our system has:

- `kitchen-cad/csv_generator.py` — cutting CSV
- `kitchen-cad/drill_engine.py` — System 32 drilling
- `kitchen-cad/generators/legrabox_side_panel.py` — DXF export

Plugin has none of this. It is a design / visualization tool, not a
manufacturing tool.

### 2. No BOM / costing

Our system has:

- `kitchen_erp/bom_generator.py` — bill of materials
- `kitchen_erp/purchasing.py` — material purchasing
- `kitchen_erp/rules_engine.py` — hardware rules

Plugin has no BOM, no costing, no purchasing calculations.

### 3. No Blum hardware specifics

Our `CABINET-VARIANTS.md` spec includes:

- Exact Blum model numbers
- Height codes (N = 83 mm, M = 116 mm, D = 199 mm)
- Runner lengths (270–650 mm)
- Color options
- Motion systems (Blumotion, Tip-On, Servo-Drive)

Plugin ships generic drawer boxes with no Blum catalog.

### 4. No material catalog integration

Our system has:

- `catalog/` — Kronospan, Kronoswiss decors
- `kuchnie_core/catalog.py` — material decomposition

Plugin uses manual color / material assignment with no catalog lookup.

### 5. Imperial units bias

```python
# From units.py
def inch(value): ...
def feet(value): ...
```

The codebase provides imperial helpers and calls `inch()` frequently. European
use requires mm throughout — audit for hardcoded inch assumptions before
relying on any specific subsystem.

---

## Integration options

### Option A — use plugin as-is for design

```
┌─────────────────────────────────────────────────────────────┐
│                    Blender Plugin                            │
│  • Interactive kitchen design                                │
│  • Wall / cabinet placement                                  │
│  • 3D visualization                                          │
│  • Elevation / plan views                                    │
│  • Client presentation                                       │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼ export geometry manifest
┌─────────────────────────────────────────────────────────────┐
│                    kuchnie-core system                       │
│  • BOM generation                                            │
│  • Cut list calculation                                      │
│  • Blum hardware specs                                       │
│  • Cost calculation                                          │
│  • CNC / DXF export                                          │
└─────────────────────────────────────────────────────────────┘
```

### Option B — extend plugin with our modules

```python
# Inside the addon:
from kitchen_cad.panel_calculator import calculate_panels
from kitchen_cad.drill_engine import apply_all_drilling
from kitchen_cad.csv_generator import generate_cutting_csv

# After cabinet placement, export panels for cutting optimization.
```

### Option C — hybrid

1. Plugin for design and visualization.
2. `kuchnie-core` for manufacturing and costing.
3. Shared JSON / YAML via `kuchnie_core` serialization.

---

## Comparison matrix

| Capability            | Plugin              | kuchnie-core     | Winner       |
| --------------------- | ------------------- | ---------------- | ------------ |
| 3D visualization      | ✅ Full Blender      | ⚠️ Basic         | Plugin       |
| Interactive placement | ✅ Wall snap, gaps   | ⚠️ Web UI only   | Plugin       |
| Elevation / plan views| ✅ Auto-dimension    | ❌ None           | Plugin       |
| PDF export            | ✅ Built-in          | ❌ None           | Plugin       |
| Client presentation   | ✅ Renders           | ⚠️ Basic         | Plugin       |
| Panel calculation     | ❌ None              | ✅ Full           | kuchnie-core |
| Cut list CSV          | ❌ None              | ✅ Full           | kuchnie-core |
| CNC / DXF export      | ❌ None              | ✅ Full           | kuchnie-core |
| BOM generation        | ❌ None              | ✅ Full           | kuchnie-core |
| Blum hardware         | ❌ Generic           | ✅ Detailed       | kuchnie-core |
| Cost calculation      | ❌ None              | ✅ Full           | kuchnie-core |
| Material catalog      | ❌ Manual            | ✅ Kronospan etc. | kuchnie-core |

---

## Recommendation

Use both systems together.

```
DESIGN PHASE (Blender plugin)
├── Draw room walls
├── Place cabinets interactively
├── Configure styles / materials
├── Generate elevations for client approval
└── Export geometry manifest (JSON)

MANUFACTURING PHASE (kuchnie-core)
├── Import geometry from plugin
├── Calculate panels          (kitchen-cad)
├── Generate cut lists        (CSV)
├── Calculate Blum hardware   (legrabox.py)
├── Generate BOM              (bom_generator.py)
├── Calculate costs           (purchasing.py)
└── Export for CNC            (DXF)
```

### Missing pieces to build

1. **Bridge module** — export plugin geometry, import into `kuchnie-core`.
2. **Blum hardware module** — add TANDEMBOX / MERIVOBOX / LEGRABOX specifics.
3. **Material catalog binding** — connect plugin to Kronospan / Kronoswiss.
4. **Unit conversion audit** — ensure mm consistency throughout.

---

## Bottom line

The plugin solves the **design / visualization** problem — a mature,
production-quality Blender addon with excellent interactive placement,
parametric cabinets, and documentation output.

`kuchnie-core` solves the **manufacturing** problem — panel calculation, cut
lists, BOM, costing, CNC export.

Together they form a complete pipeline from client design to manufacturing.
The plugin's frameless system already uses European-standard dimensions
(560 mm depth, 720 mm height, 120 mm plinth, 18 mm panels), so it is ready
for European kitchen design out of the box.
