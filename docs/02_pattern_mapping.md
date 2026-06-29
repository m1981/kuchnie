# Pattern Mapping: Professional CAD Systems → Home Builder Plugin

## Purpose

Map the universal patterns from professional kitchen CAD systems (PRO100, Polyboard, Winner Flex, TopSolid'Wood, PaletteCAD) to features in the Home Builder Blender plugin. Identify what to **borrow**, what to **extend**, and what to **build separately**.

---

## 1. Pattern-to-Plugin Feature Matrix

### 1.1 PRO100 Pattern: Cabinet Macros (Template + Parametric Overrides)

**What it is:** Visual drag-drop with reusable cabinet templates that accept dimension overrides.

**Where in plugin:**

| Feature | Plugin Location | Quality | Notes |
|---------|----------------|---------|-------|
| Cabinet templates | `product_libraries/face_frame/types_face_frame.py` | ✅ Excellent | `BaseFaceFrameCabinet`, `UpperFaceFrameCabinet`, etc. |
| Bay presets | `product_libraries/face_frame/bay_presets.py` | ✅ Excellent | `L()`, `H()`, `V()` composable presets |
| Catalog browser | `catalog/catalog_data.py` + `ui_catalog.py` | ✅ Good | Thumbnail grid, search, categories |
| Parametric overrides | `props_hb_face_frame.py` (cabinet_props) | ✅ Excellent | Per-instance dimension overrides |
| Drag-drop placement | `operators/ops_placement.py` | ✅ Excellent | Wall snap, gap detection, type-to-confirm |

**Verdict:** **Plugin has this pattern fully implemented.** It's actually better than PRO100 because it uses parametric (Geometry Nodes) underneath, not just dimension snapshots.

**Action:** ✅ **Borrow as-is** for plugin extension. Don't reimplement in your web app — too complex.

---

### 1.2 Polyboard Pattern: Construction Method as First-Class Entity

**What it is:** Separate "what a cabinet is" (role) from "how it's built" (construction method).

**Where in plugin:**

| Feature | Plugin Location | Quality | Notes |
|---------|----------------|---------|-------|
| Material thickness defaults | `config_parser.py` DEFAULTS dict | ⚠️ Partial | Global, not per-method |
| Toe kick parameters | `Frameless_Scene_Props` (toe_kick_*) | ⚠️ Embedded | In scene props, not separate object |
| Construction parameters | `Frameless_Scene_Props` (base_top_*) | ⚠️ Embedded | Mixed with other settings |
| Drawer construction | `props_hb_frameless.py` (drawer_*) | ⚠️ Embedded | Per-cabinet, not per-method |
| Edge banding rules | None explicit | ❌ Missing | Visual only, no thickness/material |
| Joinery type | None | ❌ Missing | No dowel vs cam-lock distinction |

**Critical Gap Analysis:**

```python
# CURRENT (plugin) — construction embedded in cabinet
class BaseFaceFrameCabinet(FaceFrameCabinet):
    def _build_carcass_parts(self, bay_qty):
        # Hardcoded: which panels, which joinery, which thickness
        side_left = self._make_side(thickness=18)
        side_right = self._make_side(thickness=18)
        bottom = self._make_bottom(thickness=18)
        # ... hardcoded construction logic

# POLYBOARD STYLE — construction as data
class ConstructionMethod:
    """First-class construction method."""
    id: str                          # "dowel_18mm_camlock"
    panel_thickness: int             # 18
    back_recess: int                 # 10
    back_thickness: int              # 3
    joinery_type: str                # "dowel" | "camlock" | "dado"
    edge_band_thickness: float       # 0.4 | 1.0 | 2.0
    edge_band_material: str          # "ABS" | "PVC" | "veneer"
    side_to_bottom: str              # "side_over_bottom" | "bottom_over_side"
    back_attachment: str             # "rabbet" | "groove" | "nailed"

class CabinetType:
    """References a construction method."""
    role: str                        # "base_door"
    construction_id: str             # → ConstructionMethod
    default_dimensions: Dimensions
    panel_recipe: PanelRecipe        # Which panels, sized by formulas
```

**Verdict:** **Plugin lacks this pattern.** Construction is hardcoded in cabinet class methods.

**Action:** ❌ **Build in your system.** This is your biggest leverage point.

**Implementation strategy:**
```
kuchnie_core/
├── construction/
│   ├── method.py          # ConstructionMethod class
│   ├── catalog.py         # Known methods (Polish standard, IKEA, etc.)
│   └── joinery.py         # Joinery-specific rules
└── cabinet/
    └── type.py            # Cabinet type references method
```

---

### 1.3 Winner Flex Pattern: Sub-Product Hierarchy

**What it is:** Drawer is a sub-product of a cabinet. Hierarchy mirrors physical assembly.

**Where in plugin:**

| Feature | Plugin Location | Quality | Notes |
|---------|----------------|---------|-------|
| Cabinet → Bay hierarchy | `types_face_frame.py` `FaceFrameCabinet` | ✅ Excellent | Parent-child object tree |
| Bay → Opening hierarchy | `FaceFrameOpening`, `FaceFrameBay` | ✅ Excellent | Clean nesting |
| Opening → Front/Interior | `CabinetDoor`, `CabinetDrawerFront`, etc. | ✅ Excellent | Type-specific subclasses |
| Drawer as sub-product | `CabinetDrawerFront.add_drawer_box()` | ✅ Good | Drawer box created with front |
| Material decoupling | `Frameless_Cabinet_Style.assign_style_to_cabinet()` | ✅ Excellent | Style applied post-construction |
| Interior splitters | `InteriorSplitterVertical/Horizontal` | ✅ Excellent | Nested interior tree |

**Hierarchy in plugin:**
```
Cabinet (root)
├── Bay 1
│   ├── Opening 1
│   │   ├── Front (Door / Drawer / Pullout)
│   │   │   ├── Pull (hardware sub-product)
│   │   │   └── Drawer Box (if drawer)
│   │   └── Interior
│   │       ├── Shelves
│   │       └── Splitters (recursive)
│   └── Opening 2
└── Bay 2
```

**Verdict:** **Plugin matches Winner Flex's pattern perfectly.** Material assignment is properly decoupled via the Style system.

**Action:** ✅ **Borrow the hierarchy concept** for your domain model. Use Pydantic instead of Blender objects.

---

### 1.4 TopSolid'Wood Pattern: Feature-Based Operations

**What it is:** Drills, grooves, rabbets as associative objects that survive dimension changes.

**Where in plugin:**

| Feature | Plugin Location | Quality | Notes |
|---------|----------------|---------|-------|
| Cutpart modifier | `hb_types.py` `GeoNodeCutpart` | ✅ Excellent | Panel with associative ops |
| Part modifier system | `CabinetPartModifier` | ✅ Excellent | Stackable node-based operations |
| Drill operations | `add_node('drill', ...)` | ✅ Good | Associative drilling |
| Groove operations | `add_node('groove', ...)` | ✅ Good | Associative grooves |
| Notch operations | Panel notch nodes | ✅ Good | Toe-kick notches survive resize |
| Rabbet/dado | Edge nodes | ⚠️ Partial | Visual, not parametric |
| Edge banding tracking | Visual properties only | ❌ Missing | No thickness/material data |
| Machining export | None | ❌ Missing | No DXF/G-code output |

**Plugin's mechanism:**
```python
# From hb_types.py — operations as composable nodes
class CabinetPartModifier(GeoNodeObject):
    def add_node(self, token_type: str, token_name: str):
        """Add a machining node (drill, groove, notch) to the panel."""
        # Survives dimension changes because it's parametric
    
    def driver_input(self, input_name: str, expression: str, variables=[]):
        """Connect node input to formula."""
        # Example: drill position = panel.width / 2
```

**Verdict:** **Plugin has the *visual* version of this pattern.** Operations survive dimension changes in 3D, but there's no export for CNC.

**Action:** 
- ✅ **Borrow** the associative concept (operations attached to panels, not coordinates)
- ❌ **Build** the CAM export layer separately

**Strategy:**
```
Your system:
├── Domain
│   └── MachiningOp (Pydantic)
│       ├── DrillOp(panel_id, x_formula, y_formula, depth, diameter)
│       ├── GrooveOp(panel_id, start, end, depth, width)
│       └── RabbetOp(panel_id, edge, depth, width)
│
├── Plugin extension (visualization)
│   └── Read ops from your domain → display in Blender
│
└── CAM export (manufacturing)
    ├── csv_exporter.py    # e-rozrys format
    ├── dxf_exporter.py    # DXF with machining
    └── drill_csv.py       # Drill list
```

---

### 1.5 PaletteCAD Pattern: Object-in-Room Model

**What it is:** Render-ready placement separate from engineering data.

**Where in plugin:**

| Feature | Plugin Location | Quality | Notes |
|---------|----------------|---------|-------|
| Multi-scene project | `hb_project.py` | ✅ Excellent | Room/Layout/Detail scenes |
| Room scenes | `operators/rooms.py` | ✅ Excellent | Multiple rooms per project |
| Wall placement | `operators/walls.py` | ✅ Excellent | Interactive wall drawing |
| Object placement | `hb_placement.py` `PlacementMixin` | ✅ Excellent | Snap to walls, cabinets |
| Layout views | `hb_layouts.py` `ElevationView`, `PlanView` | ✅ Excellent | Render-ready 2D output |
| Render settings | `LayoutView._setup_render_settings()` | ✅ Excellent | Separate from engineering |
| Title blocks | `hb_layouts.py` `TitleBlock` | ✅ Good | Drawing standards |
| Detail library | `hb_detail_library.py` | ✅ Good | Reusable 2D details |
| Camera setup | `LayoutView.create_camera()` | ✅ Excellent | Per-view cameras |
| Freestyle linesets | `_setup_freestyle_linesets()` | ✅ Excellent | Drafting-quality lines |

**Verdict:** **Plugin is exceptional at this pattern.** Better than most commercial tools for documentation.

**Action:** ✅ **Definitely borrow** — this is the plugin's strongest area. Use as Blender extension for visualization phase.

---

## 2. The Convergent Hierarchy: Plugin Mapping

The universal hierarchy from professional CAD systems:

```
Kitchen
 └─ Wall / Row
     └─ Cabinet Instance
         └─ Sub-assembly
             └─ Panel
                 ├─ Edge
                 └─ Machining Operations
```

**Plugin's implementation:**

```
Project Scene                      ← Kitchen
 └─ Room Scene
     └─ Wall (GeoNodeWall)         ← Wall/Row
         └─ Cabinet (FaceFrameCabinet / Cabinet)  ← Cabinet Instance
             └─ Bay (FaceFrameBay / CabinetBay)
                 └─ Opening (FaceFrameOpening / CabinetOpening)  ← Sub-assembly
                     ├─ Front (CabinetDoor / CabinetDrawerFront)
                     │   ├─ Pull (hardware)
                     │   └─ DrawerBox (if drawer)
                     └─ Interior
                         ├─ Shelves
                         └─ Splitters
                             └─ Part (GeoNodeCutpart)  ← Panel
                                 ├─ Edges (visual only)
                                 └─ Modifier nodes  ← Machining Ops
```

**Atomic unit:** `GeoNodeCutpart` — the plugin's panel equivalent.

**Gap:** Plugin's panels have visual edges but no manufacturing-grade edge data (thickness, material, supplier code).

---

## 3. The Three Critical Patterns: Plugin Status & Strategy

### 3.1 Construction Method — **BUILD IN YOUR SYSTEM**

**Plugin status:** ❌ Not separated. Construction logic embedded in cabinet classes.

**Why it matters for you:**
- Polish market has specific standards (different from American face-frame)
- You'll have 2-3 construction methods max (standard 18mm chipboard, premium plywood, etc.)
- Changing a method should cascade automatically

**Where to build:**

```python
# kuchnie_core/construction/method.py
from pydantic import BaseModel
from typing import Literal

class EdgeBandSpec(BaseModel):
    """Edge banding specification."""
    material: Literal["ABS", "PVC", "melamine", "veneer"]
    thickness_mm: float          # 0.4, 1.0, 2.0
    color: str                   # decor code or "matching"

class JoinerySpec(BaseModel):
    """Joinery specification."""
    type: Literal["dowel", "camlock", "dado", "screw"]
    fastener_spacing_mm: float = 32  # System 32 default
    dowel_diameter_mm: float = 8
    camlock_offset_mm: float = 9

class ConstructionMethod(BaseModel):
    """First-class construction method."""
    id: str
    name: str                                # "Standard 18mm Chipboard"
    
    # Material thicknesses
    side_thickness_mm: int = 18
    top_bottom_thickness_mm: int = 18
    shelf_thickness_mm: int = 18
    back_thickness_mm: int = 3
    front_thickness_mm: int = 19
    
    # Back panel
    back_recess_mm: int = 10
    back_attachment: Literal["rabbet", "groove", "nailed"] = "groove"
    
    # Construction
    side_to_bottom: Literal["side_over_bottom", "bottom_over_side"] = "side_over_bottom"
    joinery: JoinerySpec
    edge_band: EdgeBandSpec
    
    # System 32
    system32_offset_mm: int = 37        # First hole from edge
    system32_spacing_mm: int = 32       # Hole spacing
    
    # Gaps
    front_gap_mm: float = 2.0
    cabinet_gap_mm: float = 0.0

# Predefined methods
STANDARD_PL = ConstructionMethod(
    id="standard_pl_18mm",
    name="Standard Polish 18mm",
    joinery=JoinerySpec(type="camlock"),
    edge_band=EdgeBandSpec(material="ABS", thickness_mm=1.0, color="matching"),
)

PREMIUM_PL = ConstructionMethod(
    id="premium_pl_18mm",
    name="Premium Polish 18mm Dowel",
    joinery=JoinerySpec(type="dowel"),
    edge_band=EdgeBandSpec(material="ABS", thickness_mm=2.0, color="matching"),
)
```

---

### 3.2 Panel Derivation Formulas — **HYBRID (Plugin Has It, Use It)**

**Plugin status:** ✅ **Excellent.** Uses Geometry Nodes drivers as formula engine.

**Plugin's mechanism:**
```python
# Plugin uses driver expressions as formulas
door.driver_input(
    "Width",
    "var_width - 2 * var_gap",  # ← This IS a formula
    variables=[
        door.var_input("Width", "var_width"),
        door.var_prop("front_gap", "var_gap"),
    ]
)
```

**But here's the catch:** Formulas live inside Blender's driver system. They're not portable.

**Strategy: Formulas as data in your domain, evaluated in two places:**

```python
# kuchnie_core/cabinet/recipe.py
from pydantic import BaseModel

class PanelFormula(BaseModel):
    """A formula that derives a panel dimension."""
    expression: str               # "cabinet.width - 2 * method.side_thickness"
    
    def evaluate(self, context: dict) -> float:
        # Safe expression evaluation (not eval!)
        return safe_eval(self.expression, context)

class PanelRecipe(BaseModel):
    """Recipe for a single panel."""
    role: str                     # "left_side", "shelf", "back"
    material_source: str          # "method.side_material" or "front_material"
    
    width_formula: PanelFormula
    height_formula: PanelFormula
    thickness_formula: PanelFormula
    
    edge_bands: list[EdgeBandAssignment]
    machining_ops: list[MachiningOpTemplate]

class CabinetRecipe(BaseModel):
    """Complete recipe for a cabinet type."""
    role: str                     # "base_door"
    construction_id: str          # → ConstructionMethod
    panels: list[PanelRecipe]
    
    # Constraints
    min_width_mm: int
    max_width_mm: int
    min_height_mm: int
    max_height_mm: int
```

**Then evaluate in two contexts:**

```python
# Context 1: BOM/Cut list generation (pure Python)
def decompose_cabinet(cabinet: Cabinet) -> list[Panel]:
    recipe = get_recipe(cabinet.type)
    method = get_construction_method(recipe.construction_id)
    
    context = {
        "cabinet": cabinet.dict(),
        "method": method.dict(),
    }
    
    panels = []
    for panel_recipe in recipe.panels:
        panel = Panel(
            width=panel_recipe.width_formula.evaluate(context),
            height=panel_recipe.height_formula.evaluate(context),
            thickness=panel_recipe.thickness_formula.evaluate(context),
        )
        panels.append(panel)
    
    return panels

# Context 2: Blender scene generation
def generate_blender_scene(cabinet: Cabinet):
    panels = decompose_cabinet(cabinet)  # Same function!
    for panel in panels:
        create_blender_panel(panel)  # Plugin uses GeoNodes for parametric
```

**Verdict:** 
- ✅ **Borrow** plugin's Geometry Nodes for visual parametric (when in Blender)
- ✅ **Build** formula engine in domain (for BOM, cut list, validation)
- Both evaluate the same formulas with same inputs

---

### 3.3 Material ≠ Construction — **PLUGIN ALREADY DOES THIS WELL**

**Plugin status:** ✅ **Excellent.** Style system is properly decoupled.

**Plugin's structure:**
```python
# Construction (geometry) defined here
class BaseFaceFrameCabinet:
    def create(self, name, bay_qty):
        # Pure geometry, no materials
        self._build_carcass_parts(bay_qty)

# Materials applied separately
class Frameless_Cabinet_Style:
    def assign_style_to_cabinet(self, cabinet_obj):
        # Materials applied to existing geometry
        for part in get_parts(cabinet_obj):
            part.material = self.get_finish_material()
```

**Your intermediate format already does this:**
```yaml
materials:
  corpus:
    decor: "Kronospan U112 PM"  # ← Material reference
  front:
    decor: "Egger H3303 ST10"
rows:
  - cabinets:
    - id: "cab_001"
      type: "base-door"         # ← Construction reference
      width: 600
```

**Verdict:** ✅ **Keep it this way.** Both plugin and your system already follow this pattern.

**Action:** Just ensure the boundary stays clean:
- Construction never mentions decor names
- Materials never mention dimensions
- Connection only at assembly time

---

## 4. Validation Strategy (TopSolid'Wood Pattern)

**Plugin status:** ⚠️ **Partial.** Has dimension validation but no manufacturing validation.

**Plugin's validation:**
- `config_parser._validate()` — config structure
- `props_hb_frameless.py` update callbacks — UI-level
- No CAM-ready validation
- No row/wall validation

**Validation gates needed (build in your system):**

```python
# kuchnie_core/validation/gates.py

class CabinetValidator:
    """Gate 1: Cabinet is valid."""
    def validate(self, cabinet: Cabinet) -> list[ValidationIssue]:
        issues = []
        recipe = get_recipe(cabinet.type)
        
        # Min/max dimensions
        if cabinet.width < recipe.min_width_mm:
            issues.append(f"Width {cabinet.width}mm below min {recipe.min_width_mm}mm")
        
        # Required accessories
        for required in recipe.required_accessories:
            if required not in cabinet.accessories:
                issues.append(f"Missing required accessory: {required}")
        
        return issues

class RowValidator:
    """Gate 2: Row is valid."""
    def validate(self, row: Row, wall_width: float) -> list[ValidationIssue]:
        issues = []
        
        # Total width check
        total = sum(c.width for c in row.cabinets)
        if total > wall_width:
            issues.append(f"Row width {total}mm exceeds wall {wall_width}mm")
        
        # Overlap check
        # Gap accounting
        # ...
        return issues

class KitchenValidator:
    """Gate 3: Kitchen is valid."""
    def validate(self, kitchen: Kitchen) -> list[ValidationIssue]:
        # Row conflicts
        # Worktop coverage
        # Plumbing/hob placement
        # ...

class CAMReadyValidator:
    """Gate 4: Ready for manufacturing."""
    def validate(self, kitchen: Kitchen) -> list[ValidationIssue]:
        issues = []
        for cabinet in kitchen.all_cabinets():
            panels = decompose_cabinet(cabinet)
            for panel in panels:
                if panel.width <= 0 or panel.height <= 0:
                    issues.append(f"Invalid panel dimensions: {panel.id}")
                if not panel.material:
                    issues.append(f"Panel missing material: {panel.id}")
                for edge in panel.edges:
                    if not edge.assigned:
                        issues.append(f"Edge not assigned: {panel.id}/{edge.side}")
                for op in panel.machining_ops:
                    if not op.is_valid():
                        issues.append(f"Invalid machining op: {op.id}")
        return issues
```

---

## 5. Final Architecture: Where Each Feature Lives

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          YOUR FEATURE PLACEMENT MAP                             │
└─────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────┐  ┌──────────────────────────┐  ┌──────────────────────────┐
│   WEB APP (iPad/Desktop)  │  │   BLENDER PLUGIN (Desktop)│  │   CLI / BACKEND (Python) │
│   You build (Reflex)      │  │   You extend the plugin   │  │   You build (kuchnie_core)│
├──────────────────────────┤  ├──────────────────────────┤  ├──────────────────────────┤
│                          │  │                          │  │                          │
│  USE CASE 1: First Visit │  │  USE CASE 2.5: Editing   │  │  USE CASE 3: CAM Prep    │
│                          │  │  USE CASE 2: Rendering   │  │                          │
│  ✅ Predefined layouts    │  │  ✅ Wall drawing          │  │  ✅ Cut list CSV         │
│  ✅ Decor selection       │  │  ✅ Cabinet placement     │  │  ✅ Drill CSV            │
│  ✅ Quick mockup          │  │  ✅ Multi-scene layout    │  │  ✅ DXF export           │
│                          │  │  ✅ Elevation views       │  │  ✅ BOM generation       │
│  USE CASE 2: Cost Est.   │  │  ✅ Plan views            │  │  ✅ Cost calculation     │
│                          │  │  ✅ 3D renders            │  │  ✅ Validation gates     │
│  ✅ Row-based layout      │  │  ✅ Material catalog UI   │  │                          │
│  ✅ Cabinet config        │  │  ✅ Construction tweaks   │  │  Domain Layer:           │
│  ✅ Dimension overrides   │  │  ✅ Obstacle handling     │  │  ✅ ConstructionMethod   │
│  ✅ Real-time cost        │  │  ✅ Vent holes / LED      │  │  ✅ CabinetRecipe        │
│                          │  │                          │  │  ✅ PanelFormula         │
│  Communicates via:       │  │  Reads/writes:           │  │  ✅ MachiningOp          │
│  → kitchen_config.yaml   │  │  → kitchen_config.yaml   │  │  ✅ Validator gates      │
│                          │  │                          │  │                          │
└──────────────────────────┘  └──────────────────────────┘  └──────────────────────────┘
              │                          │                          │
              └──────────────────────────┴──────────────────────────┘
                                         │
                                         ▼
                    ┌────────────────────────────────────────┐
                    │   INTERMEDIATE FORMAT (your contract)  │
                    │   kitchen_config.yaml                  │
                    │   - Owned by you                       │
                    │   - Versioned (semver)                 │
                    │   - All three systems read/write it    │
                    └────────────────────────────────────────┘
```

---

## 6. Plugin Extension Strategy (Solo Developer)

Since you're solo and GUI is hard, **lean heavily on the plugin** for the visual editing phase.

### 6.1 What to add to the plugin (small extension)

Create a small plugin module that:

```python
# home_builder_5/product_libraries/kuchnie/
├── __init__.py
├── io_kuchnie.py           # Import/export kitchen_config.yaml
├── ops_kuchnie.py          # Operators
├── ui_kuchnie.py           # Sidebar panel
└── decor_browser.py        # Kronospan/Egger picker
```

**Operators to add:**

| Operator | Purpose |
|----------|---------|
| `kuchnie_OT_import_config` | Read kitchen_config.yaml → build scene |
| `kuchnie_OT_export_config` | Save scene → kitchen_config.yaml |
| `kuchnie_OT_apply_decor` | Apply Kronospan/Egger decor to selected |
| `kuchnie_OT_add_obstacle` | Mark pipe/socket/vent location |
| `kuchnie_OT_add_led_groove` | Add LED groove specification |
| `kuchnie_OT_validate_cam` | Run CAM-ready validation |
| `kuchnie_OT_render_for_customer` | Render preset views for customer |

**No new geometry types needed** — reuse plugin's `Frameless_Scene_Props` and `types_frameless.py`.

### 6.2 What stays in your code (no plugin)

```
kuchnie_core/                       ← Pure Python, no Blender
├── construction/
│   ├── method.py                   # ConstructionMethod
│   └── catalog.py                  # Predefined methods
├── cabinet/
│   ├── recipe.py                   # CabinetRecipe + PanelFormula
│   └── types.py                    # Cabinet type registry
├── decor/
│   ├── catalog.py                  # Kronospan/Egger database
│   └── pairing.py                  # Decor + edge pairings
├── hardware/
│   ├── blum.py                     # Blum drawer systems
│   └── handles.py                  # Handle catalog
├── domain/
│   ├── kitchen.py                  # Kitchen, Row, Cabinet, Panel
│   └── machining.py                # MachiningOp types
├── validation/
│   ├── gates.py                    # Validator gates
│   └── rules.py                    # Validation rules
├── export/
│   ├── cutlist_csv.py              # e-rozrys format
│   ├── drill_csv.py                # Drill list
│   └── dxf.py                      # DXF for CNC
└── io/
    └── kitchen_config.py           # YAML/JSON serialization
```

---

## 7. Decision Summary

| Pattern | Plugin Status | Your Action | Where |
|---------|--------------|-------------|-------|
| **Cabinet Macros** (PRO100) | ✅ Excellent | Borrow as-is | Plugin extension |
| **Construction Method** (Polyboard) | ❌ Missing | Build in domain | `kuchnie_core/construction/` |
| **Sub-product Hierarchy** (Winner Flex) | ✅ Excellent | Mirror in domain | `kuchnie_core/domain/` (Pydantic) |
| **Feature Operations** (TopSolid) | ⚠️ Visual only | Build CAM layer | `kuchnie_core/export/` |
| **Object-in-Room** (PaletteCAD) | ✅ Excellent | Use plugin's | Plugin (for visual editing) |
| **Panel Formulas** | ✅ In drivers | Build portable engine | `kuchnie_core/cabinet/recipe.py` |
| **Material Decoupling** | ✅ Excellent | Keep both clean | Both |
| **Validation Gates** | ⚠️ UI only | Build all 4 gates | `kuchnie_core/validation/` |

---

## 8. Recommended Build Order

**Week 1-2: Domain foundation**
1. `ConstructionMethod` (Polyboard pattern)
2. `CabinetRecipe` + `PanelFormula` engine
3. Migrate existing cabinet types to recipes

**Week 3-4: Manufacturing pipeline**
4. `MachiningOp` types
5. Cut list CSV exporter (e-rozrys)
6. Drill CSV exporter
7. Validation gates 1-4

**Week 5-6: Decor + hardware**
8. Kronospan/Egger decor catalog (from existing `catalog/`)
9. Blum hardware catalog
10. Pricing database

**Week 7-8: Plugin integration**
11. `kuchnie` plugin extension (import/export YAML)
12. Decor picker UI in plugin
13. Obstacle/LED groove operators
14. CAM validation operator

**Week 9-10: Web app**
15. Predefined layouts (use plugin for rendering)
16. Cost estimation UI
17. Decor selection UI

**Week 11+: Polish**
18. Customer-facing renders
19. PDF generation
20. CNC company integration

---

## 9. Final Note on License

The plugin is on commercial license but you're using it for personal projects. **Document this clearly** in your project:

```
This system uses Home Builder 5 (Blender plugin) under personal-use terms.
The plugin handles:
- Visual editing
- Render generation
- Documentation views

Our code handles:
- Domain logic (construction, recipes)
- Manufacturing exports (cut lists, DXF)
- Web configurator (Reflex)
- CLI tools

The intermediate format (kitchen_config.yaml) is our contract.
The plugin is a "consumer" of this format, replaceable if needed.
```

**This isolation is critical** — if you ever need to commercialize, you can swap the plugin for a custom Blender script without rewriting domain logic.
