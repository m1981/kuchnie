# CAD Pattern Analysis: Blender Plugin vs Commercial Systems

## Executive Summary

This document analyzes the Home Builder Blender plugin against the five key patterns identified from commercial CAD systems (PRO100, Polyboard, Winner Flex, TopSolid'Wood, PaletteCAD). The analysis shows the plugin implements **3 of 5 patterns well**, with **2 patterns partially implemented**.

---

## Pattern Implementation Matrix

| Pattern | Source | Plugin Status | Gap Analysis |
|---------|--------|---------------|--------------|
| **Cabinet Macros** | PRO100 | ✅ **Strong** | Full template + override system |
| **Construction Method** | Polyboard | ⚠️ **Partial** | Embedded in types, not first-class |
| **Sub-product Hierarchy** | Winner Flex | ✅ **Strong** | Bay → Opening → Interior hierarchy |
| **Feature-based Operations** | TopSolid'Wood | ⚠️ **Partial** | GeoNode modifiers, not associative |
| **Object-in-Room Model** | PaletteCAD | ✅ **Strong** | Wall → Cabinet → Part hierarchy |
| **Panel Derivation Formulas** | All five | ✅ **Strong** | Driver-based parametric system |
| **Material ≠ Construction** | Winner Flex | ✅ **Good** | Style system decouples materials |

---

## Pattern 1: Cabinet Macros (PRO100)

### What PRO100 Does
- Template cabinets with parametric overrides
- Visual drag-drop placement
- Quick dimension changes without breaking construction

### How the Plugin Implements It

**Template System:**
```python
# types_frameless.py
class BaseCabinet(Cabinet):
    """Template for base cabinets."""
    
    width = inch(18)    # Default width
    height = inch(34)   # Default height
    depth = inch(24)    # Default depth
    
    def create(self, name='Base Cabinet'):
        """Create from template with defaults."""
        self.create_base_carcass(name)
        self.add_exterior()  # Default: doors
    
    def add_doors(self):
        """Override: add doors."""
        ...
    
    def add_drawer_stack(self, count):
        """Override: add drawers."""
        ...
```

**Catalog System (PRO100-style macros):**
```python
# catalog_data.py
def _ff(cabinet_name: str, bay_qty: int = 1) -> dict:
    """Create face frame catalog entry (macro)."""
    return {
        'id': f'ff_{cabinet_name}',
        'name': cabinet_name.replace('_', ' ').title(),
        'category': 'face_frame',
        'action': 'hb_face_frame_OT_draw_cabinet',
        'params': {'cabinet_name': cabinet_name, 'bay_qty': bay_qty},
    }

# Usage: drag from catalog, then customize
ENTRIES = [
    _ff('base_cabinet'),        # Base macro
    _ff('upper_cabinet'),       # Upper macro
    _ff('tall_cabinet'),        # Tall macro
    _ff('corner_diagonal'),     # Corner macro
    _ff('sink_base'),           # Sink macro
]
```

**Override System:**
```python
# After placing from catalog, user can override:
cabinet.width = 600      # Override default 450mm
cabinet.drawers = 3      # Change from doors to 3-drawer
cabinet.toe_kick_height = 150  # Non-standard kick
```

### Assessment: ✅ STRONG

| Requirement | Status | Notes |
|-------------|--------|-------|
| Template definition | ✅ | BaseCabinet, UpperCabinet, etc. |
| Default values | ✅ | inch(18), inch(34), inch(24) |
| Parametric overrides | ✅ | All dimensions overridable |
| Visual placement | ✅ | Wall-based drag placement |
| Catalog browser | ✅ | Thumbnail-based catalog |

### Gap: Polish Market UX
PRO100 is known in Poland for its simple drag-drop UX. The plugin's Blender-based UI is more complex. For your web app, consider:
- Simplified 2D layout editor
- One-click cabinet placement
- Visual dimension handles

---

## Pattern 2: Construction Method (Polyboard)

### What Polyboard Does
- **First-class Construction Method entity**
- Separates "what" (cabinet role) from "how" (construction)
- One method change cascades to all panels

```
Cabinet Type = Role + Construction Method + Default Accessories

  role:           "base_standard"
  construction:   "dowel_camlock_18mm"    ← reusable across many types
  accessories:    [hinges, shelf_pins, ...]
```

### How the Plugin Implements It

**Current Approach (Embedded):**
```python
# types_frameless.py - Construction embedded in cabinet type
class Cabinet(GeoNodeCage):
    def create_base_carcass(self, name):
        # Construction logic hardcoded here
        
        # === SIDES ===
        if toe_kick_type == 0:  # Notch Ends to Floor
            left_side = CabinetSideNotched()
            left_side.create('Left Side', tkh, tks, mt)
            ...
        else:  # Ladder Style, Floating, Leg Levelers
            left_side = CabinetPart()
            left_side.create('Left Side')
            ...
        
        # === BOTTOM ===
        bottom = CabinetPart()
        bottom.create('Bottom')
        bottom.driver_input("Length", 'dim_x-(mt*2)', [dim_x, mt])
        ...
        
        # === BACK ===
        back = CabinetPart()
        back.create('Back')
        back.driver_input("Length", 'dim_z-tkh-mt', [dim_z, tkh, mt])
        ...
```

**What's Missing:**
```python
# POLYBOARD PATTERN (not implemented):
class ConstructionMethod:
    """First-class construction method entity."""
    
    name: str = "dowel_camlock_18mm"
    panel_thickness: float = 18.0
    back_thickness: float = 3.0
    back_recess: float = 10.0  # Groove depth
    
    # Construction rules
    side_joint: str = "dowel"      # dowel, camlock, dado, glue
    top_joint: str = "camlock"
    bottom_joint: str = "camlock"
    back_attachment: str = "groove" # groove, staple, screw
    
    # Edge banding rules
    edge_front: str = "ABS_1mm"
    edge_back: str = "none"
    edge_top: str = "ABS_0.4mm"
    edge_bottom: str = "ABS_0.4mm"
    
    def calculate_panel_dims(self, cabinet_dims):
        """Calculate all panel dimensions from cabinet dims."""
        ...

# Then cabinet type references method:
class BaseCabinet:
    role = "base_standard"
    construction = ConstructionMethod.get("dowel_camlock_18mm")
    # Construction rules come from method, not hardcoded
```

### Assessment: ⚠️ PARTIAL

| Requirement | Status | Notes |
|-------------|--------|-------|
| Separate construction entity | ❌ | Construction embedded in types |
| Reusable methods | ❌ | Each type has own construction |
| Method swap | ❌ | Cannot change method without rewriting |
| Joint type specification | ⚠️ | Not modeled (dowel vs camlock) |
| Edge banding rules | ⚠️ | Basic edge support only |

### What This Means for You

**Current plugin approach:**
- Works for single construction method
- Hard to switch from cam-lock to dowel
- Edge banding rules embedded in code

**Your system should:**
```python
# Separate construction method
class ConstructionMethod(BaseModel):
    name: str
    panel_thickness: float = 18.0
    back_thickness: float = 3.0
    back_recess: float = 10.0
    
    # Joint specifications
    side_joint: JointType = JointType.DOWEL
    top_joint: JointType = JointType.CAMLOCK
    
    # Edge rules
    edge_front: EdgeSpec = EdgeSpec(material="ABS", thickness=1.0)
    edge_back: EdgeSpec = EdgeSpec(material="none")
    
    def side_panel_dims(self, cab: Cabinet) -> PanelDims:
        """Derive side panel dimensions."""
        return PanelDims(
            length=cab.height,
            width=cab.depth,
            thickness=self.panel_thickness,
            edges=self.side_edges(),
        )
    
    def shelf_dims(self, cab: Cabinet) -> PanelDims:
        """Derive shelf panel dimensions."""
        inner_width = cab.width - 2 * self.panel_thickness
        inner_depth = cab.depth - self.back_thickness - self.back_recess
        return PanelDims(
            length=inner_width - 2 * self.shelf_clearance,
            width=inner_depth - self.shelf_clearance,
            thickness=self.panel_thickness,
        )

# Cabinet type references method
class CabinetType(BaseModel):
    role: str  # "base", "upper", "tall", "corner"
    construction: ConstructionMethod
    default_accessories: list[Accessory]
```

---

## Pattern 3: Sub-product Hierarchy (Winner Flex)

### What Winner Flex Does
- Drawer is a sub-product of cabinet
- Material assignment decoupled from construction
- Hierarchical BOM generation

### How the Plugin Implements It

**Hierarchy:**
```
Cabinet (GeoNodeCage)
├── Bay (CabinetBay)
│   ├── Opening (CabinetOpening)
│   │   ├── Door/Drawer (CabinetFront)
│   │   │   ├── Door Swing (GeoNodeDoorSwing)
│   │   │   ├── Drawer Box (GeoNodeDrawerBox)
│   │   │   └── Pull (GeoNodeHardware)
│   │   └── Interior (CabinetInterior)
│   │       ├── Shelves (CabinetShelves)
│   │       └── Rollout (InteriorSplitterVertical)
│   └── Parts (CabinetPart)
│       ├── Side Panel
│       ├── Bottom Panel
│       ├── Top Panel
│       └── Back Panel
└── Toe Kick (optional)
```

**Implementation:**
```python
# Opening creates sub-products
class hb_frameless_OT_change_bay_opening(bpy.types.Operator):
    def create_doors(self, bay, door_swing):
        """Create door sub-product."""
        opening = Doors()
        opening.create()
        opening.add_interior(CabinetShelves())
        bay.add_cage_to_bay(opening)
    
    def create_drawer(self, bay):
        """Create drawer sub-product."""
        opening = Drawer()
        opening.create()
        bay.add_cage_to_bay(opening)
    
    def create_pullout(self, bay):
        """Create pullout sub-product."""
        opening = Pullout()
        opening.create()
        bay.add_cage_to_bay(opening)
```

**Drawer Box as Sub-product:**
```python
class GeoNodeDrawerBox(GeoNodeObject):
    """Drawer box - sub-product of drawer opening."""
    
    def create(self, name):
        # Creates drawer box assembly
        # - Bottom panel
        # - Side panels
        # - Back panel
        # - Runner attachment points
```

### Assessment: ✅ STRONG

| Requirement | Status | Notes |
|-------------|--------|-------|
| Hierarchical structure | ✅ | Cabinet → Bay → Opening → Parts |
| Sub-product creation | ✅ | Doors, drawers, pullouts |
| Material decoupling | ✅ | Style system separate from construction |
| BOM hierarchy | ⚠️ | No explicit BOM generation |
| Part-level tracking | ✅ | Individual parts tracked |

### What This Means for You

The plugin's hierarchy maps directly to your intermediate format:

```yaml
# Your format should mirror this hierarchy:
kitchen:
  rows:
    - id: "row_south"
      cabinets:
        - id: "cab_001"
          type: "base-door"
          bays:
            - id: "bay_001"
              openings:
                - id: "open_001"
                  type: "doors"
                  front:
                    type: "door"
                    swing: "right"
                  interior:
                    type: "shelves"
                    count: 2
```

---

## Pattern 4: Feature-based Operations (TopSolid'Wood)

### What TopSolid'Wood Does
- Drill, groove, rabbet as associative objects
- Survive dimension changes
- Parametric positioning

### How the Plugin Implements It

**GeoNode Modifiers (Partial):**
```python
class CabinetPart(GeoNodeCutpart):
    """Panel with geometry node modifier."""
    
    def create(self, name):
        # Creates panel with parametric modifier
        # Modifier has inputs: Length, Width, Thickness
        # These are driven by expressions
    
    def add_part_modifier(self, token_type, token_name):
        """Add machining operation modifier."""
        # Adds additional geometry node modifier
        # for cuts, holes, etc.
```

**Driver-based Positioning:**
```python
# Example: Hinge holes positioned parametrically
hinge = GeoNodeHardware()
hinge.create('Hinge')
hinge.driver_location('z', 'dim_z * 0.75', [dim_z])  # 75% up
hinge.driver_location('x', 'mt + 0.1', [mt])          # 100mm from edge
```

### Assessment: ⚠️ PARTIAL

| Requirement | Status | Notes |
|-------------|--------|-------|
| Feature as object | ⚠️ | GeoNode modifiers, not explicit features |
| Associative positioning | ✅ | Driver-based parametric positioning |
| Survive dimension changes | ✅ | Drivers auto-update |
| Feature library | ❌ | No standard feature library |
| Boolean operations | ⚠️ | Basic boolean support |

### What This Means for You

**Plugin's approach:**
- Uses Blender's driver system for parametric positioning
- GeoNode modifiers for panel generation
- No explicit feature objects (drill, groove, rabbet)

**Your system should:**
```python
# Explicit feature objects
class MachiningOp(BaseModel):
    """Base class for machining operations."""
    panel_id: str
    position: tuple[float, float]  # x, y on panel
    depth: float
    diameter: float = 0.0
    
class DrillHole(MachiningOp):
    """Drilling operation."""
    type: str = "through"  # through, blind, countersink
    
class Groove(MachiningOp):
    """Groove operation."""
    length: float
    width: float
    
class Rabbet(MachiningOp):
    """Rabbet operation."""
    length: float
    width: float
    depth: float

# Panel has features
class Panel(BaseModel):
    id: str
    length: float
    width: float
    thickness: float
    edges: dict[str, EdgeBand]
    features: list[MachiningOp]  # ← Features survive dimension changes
    
    def recalculate_features(self):
        """Update feature positions when dimensions change."""
        for feature in self.features:
            feature.recalculate(self)
```

---

## Pattern 5: Object-in-Room Model (PaletteCAD)

### What PaletteCAD Does
- Room model separate from cabinet engineering
- Render-ready placement
- Engineering data decoupled

### How the Plugin Implements It

**Room Hierarchy:**
```
Project
├── Main Scene (Project Settings)
├── Room Scenes
│   ├── Room 1 (Kitchen)
│   │   ├── Wall Collection
│   │   │   ├── Wall 1 (GeoNodeWall)
│   │   │   │   ├── Cabinet 1 (GeoNodeCage)
│   │   │   │   ├── Cabinet 2 (GeoNodeCage)
│   │   │   │   └── Appliance 1 (GeoNodeCage)
│   │   │   └── Wall 2 (GeoNodeWall)
│   │   │       └── ...
│   │   └── Obstacles Collection
│   └── Room 2 (Bathroom)
└── Layout Scenes
    ├── Elevation Views
    └── Plan Views
```

**Wall → Cabinet Relationship:**
```python
class GeoNodeWall(GeoNodeObject):
    """Wall object with connections."""
    
    def create(self, name):
        # Creates wall with parametric length, height, thickness
    
    def connect_to_wall(self, wall):
        """Connect to adjacent wall (corner)."""
    
    def get_connected_wall(self, direction='left'):
        """Get connected wall."""

# Cabinet placement on wall
class hb_frameless_OT_place_cabinet(bpy.types.Operator):
    def set_position_on_wall(self, context):
        """Place cabinet on wall."""
        # 1. Find wall from cursor
        # 2. Calculate position along wall
        # 3. Snap to adjacent cabinets
        # 4. Set parent relationship
```

**Separate Render and Engineering:**
```python
# Render scene (visual)
class ElevationView(LayoutView):
    def create(self, wall_obj):
        # Creates render-ready view
        # - Camera positioning
        # - Lighting setup
        # - Material assignment
        # - Freestyle lines for technical look

# Engineering data (not visual)
# Stored in property groups, not mesh
cabinet.width = 600
cabinet.material_thickness = 18
cabinet.construction_method = "dowel"
```

### Assessment: ✅ STRONG

| Requirement | Status | Notes |
|-------------|--------|-------|
| Room model | ✅ | Project → Room → Wall hierarchy |
| Wall-based placement | ✅ | Snapping, gap detection |
| Render separation | ✅ | Layout views separate from model |
| Engineering data | ✅ | Property groups store engineering |
| Obstacle handling | ✅ | Obstacles collection |

---

## Pattern 6: Panel Derivation Formulas (All Five)

### What All Systems Do
- Formulas, not hardcoded values
- Each panel dimension is an expression
- Formula graph for dependency tracking

### How the Plugin Implements It

**Driver-based Formulas:**
```python
# types_frameless.py - create_base_carcass()

# Side panel dimensions
left_side.driver_input("Length", 'dim_z', [dim_z])
left_side.driver_input("Width", 'dim_y', [dim_y])
left_side.driver_input("Thickness", 'mt', [mt])

# Bottom panel dimensions
bottom.driver_input("Length", 'dim_x-(mt*2)', [dim_x, mt])
bottom.driver_input("Width", 'dim_y', [dim_y])
bottom.driver_input("Thickness", 'mt', [mt])

# Back panel dimensions
back.driver_input("Length", 'dim_z-tkh-mt', [dim_z, tkh, mt])
back.driver_input("Width", 'dim_x-(mt*2)', [dim_x, mt])
back.driver_input("Thickness", 'mt', [mt])

# Shelf dimensions (derived from opening)
shelf.driver_input("Length", 'dim_x-(mt*2)-clearance', [dim_x, mt, clearance])
shelf.driver_input("Width", 'dim_y-mt-back_recess-clearance', [dim_y, mt, back_recess, clearance])
```

**Solver Formulas (Face Frame):**
```python
# solver_face_frame.py - Pure Python formulas

def carcass_inner_depth(layout):
    """Available depth from cabinet front to back."""
    return layout.dim_y - layout.fft

def carcass_inner_left_x(layout):
    """X of left side panel's inner face."""
    return left_scribe_offset(layout) + left_side_thickness(layout)

def bay_x_position(layout, bay_index):
    """X coordinate of bay N's opening."""
    x = layout.lsw
    for i in range(bay_index):
        x += layout.bays[i]['width']
        if i < len(layout.mid_stiles):
            x += layout.mid_stiles[i]['width']
    return x

def bay_top_z(layout, bay_index):
    """Z of bay's top edge."""
    bay = layout.bays[bay_index]
    if layout.cabinet_type == 'UPPER':
        return layout.dim_z - bay['top_offset']
    return bay['height']
```

### Assessment: ✅ STRONG

| Requirement | Status | Notes |
|-------------|--------|-------|
| Formula-based dimensions | ✅ | Driver expressions |
| Dependency tracking | ✅ | Blender handles driver graph |
| Cascading updates | ✅ | Automatic via drivers |
| Pure Python solver | ✅ | solver_face_frame.py |
| Formula as data | ⚠️ | Drivers are code, not data |

### What This Means for You

**Plugin uses two approaches:**
1. **Blender Drivers** (types_frameless.py) - For real-time parametric updates
2. **Python Solver** (solver_face_frame.py) - For complex calculations

**Your system should use Python solver pattern:**
```python
class PanelCalculator:
    """Calculate panel dimensions from cabinet specification."""
    
    def side_panel(self, cab: Cabinet, method: ConstructionMethod) -> Panel:
        """Derive side panel dimensions."""
        return Panel(
            length=cab.height,
            width=cab.depth,
            thickness=method.panel_thickness,
            edges={
                'front': method.edge_front,
                'back': method.edge_back,
                'top': method.edge_top,
                'bottom': method.edge_bottom,
            }
        )
    
    def bottom_panel(self, cab: Cabinet, method: ConstructionMethod) -> Panel:
        """Derive bottom panel dimensions."""
        return Panel(
            length=cab.width - 2 * method.panel_thickness,
            width=cab.depth,
            thickness=method.panel_thickness,
        )
    
    def back_panel(self, cab: Cabinet, method: ConstructionMethod) -> Panel:
        """Derive back panel dimensions."""
        return Panel(
            length=cab.width - 2 * method.panel_thickness + 2 * method.back_recess,
            width=cab.height - cab.toe_kick_height - method.panel_thickness,
            thickness=method.back_thickness,
        )
    
    def shelf_panel(self, cab: Cabinet, method: ConstructionMethod) -> Panel:
        """Derive shelf panel dimensions."""
        inner_width = cab.width - 2 * method.panel_thickness
        inner_depth = cab.depth - method.back_thickness - method.back_recess
        return Panel(
            length=inner_width - 2 * self.shelf_clearance,
            width=inner_depth - self.shelf_clearance,
            thickness=method.panel_thickness,
        )
```

---

## Pattern 7: Material ≠ Construction (Winner Flex)

### What Winner Flex Does
- Swap all materials without touching construction
- Change construction without touching materials
- Clean separation

### How the Plugin Implements It

**Style System:**
```python
# props_hb_frameless.py
class Frameless_Cabinet_Style(PropertyGroup):
    """Cabinet style - materials only."""
    
    def get_finish_material(self):
        """Get finish material for exterior."""
        ...
    
    def get_interior_material(self):
        """Get material for interior."""
        ...
    
    def assign_style_to_cabinet(self, cabinet_obj):
        """Apply style to cabinet (materials only)."""
        finish_mat = self.get_finish_material()
        interior_mat = self.get_interior_material()
        
        for part in get_cabinet_parts(cabinet_obj):
            if is_exterior_part(part):
                part.material = finish_mat
            else:
                part.material = interior_mat

class Frameless_Door_Style(PropertyGroup):
    """Door style - materials and appearance."""
    
    def assign_style_to_front(self, front_obj):
        """Apply door style to front."""
        ...
```

**Separate Concerns:**
```python
# Construction (types_frameless.py)
cabinet = BaseCabinet()
cabinet.create("My Cabinet")
cabinet.width = 600
cabinet.height = 720
# Construction is set

# Materials (props_hb_frameless.py)
style = Frameless_Cabinet_Style()
style.finish_color = "Oak Natural"
style.interior_color = "White"
style.assign_style_to_cabinet(cabinet.obj)
# Materials applied separately

# Can change materials without touching construction
style.finish_color = "Walnut Dark"
style.assign_style_to_cabinet(cabinet.obj)
# Construction unchanged
```

### Assessment: ✅ GOOD

| Requirement | Status | Notes |
|-------------|--------|-------|
| Material separation | ✅ | Style system decoupled |
| Construction separation | ✅ | Types define construction |
| Material swap | ✅ | Style assignment |
| Construction swap | ❌ | Cannot change method |
| Independent updates | ✅ | Materials update independently |

---

## Validation Analysis (TopSolid'Wood Pattern)

### What TopSolid'Wood Does
- Validation at every level
- Prevents invalid states
- Guides user to correct configuration

### Plugin's Validation

**Config Validation:**
```python
# config_parser.py
def _validate(config: dict) -> None:
    """Validate config structure and values."""
    # Version validation
    version = config.get("version", "1.0")
    if version not in SUPPORTED_VERSIONS:
        raise ValueError(...)
    
    # Settings validation
    _validate_settings(config.get("settings", {}))
    
    # Cabinet validation
    for i, run in enumerate(config["runs"]):
        for section in ("base", "upper", "tall"):
            for j, cab in enumerate(run.get(section, [])):
                _validate_cabinet(cab, i, section, j, config["settings"])

def _validate_cabinet(cab, run_idx, section, cab_idx, settings):
    """Validate a single cabinet."""
    if "type" not in cab:
        raise ValueError(...)
    
    if "width" not in cab:
        raise ValueError(...)
    
    if cab["width"] <= 0:
        raise ValueError(...)
    
    # Type-specific validation
    if cab_type == "corner-blind":
        bd = cab.get("blindDepth", 300)
        if bd >= cab["width"]:
            raise ValueError(...)
    
    # Drawer validation
    if cab_type in ("base-drawers", "wall-drawers"):
        _validate_drawers(cab, ...)
```

**Dimension Validation:**
```python
def _validate_drawers(cab, run_idx, section, cab_idx, settings):
    """Validate drawer configuration."""
    max_h = settings.get("baseBodyHeight", 720)
    
    if isinstance(drawers, int):
        total_gap = front_gap * (drawers - 1)
        min_drawer_h = (max_h - total_gap) / drawers
        if min_drawer_h < MIN_DRAWER_HEIGHT:
            raise ValueError(...)
    
    elif isinstance(drawers, list):
        for i, h in enumerate(drawers):
            if h < MIN_DRAWER_HEIGHT:
                raise ValueError(...)
        
        total = sum(drawers) + front_gap * (len(drawers) - 1)
        if total > max_h:
            raise ValueError(...)
```

### Assessment: ⚠️ PARTIAL

| Validation Gate | Plugin Status | Notes |
|-----------------|---------------|-------|
| Cabinet valid | ✅ | Width, height, type checks |
| Row valid | ❌ | No wall width validation |
| Kitchen valid | ❌ | No cross-row validation |
| CAM ready | ❌ | No panel validation |

### What You Need to Add

```python
class KitchenValidator:
    """Multi-level validation."""
    
    def validate_cabinet(self, cab: Cabinet) -> list[str]:
        """Gate 1: Cabinet valid."""
        errors = []
        if cab.width < MIN_WIDTH:
            errors.append(f"Width {cab.width} < min {MIN_WIDTH}")
        if cab.height > MAX_HEIGHT:
            errors.append(f"Height {cab.height} > max {MAX_HEIGHT}")
        return errors
    
    def validate_row(self, row: Row) -> list[str]:
        """Gate 2: Row valid."""
        errors = []
        total_width = sum(c.width for c in row.cabinets)
        if total_width > row.wall_length:
            errors.append(f"Total width {total_width} > wall {row.wall_length}")
        return errors
    
    def validate_kitchen(self, kitchen: Kitchen) -> list[str]:
        """Gate 3: Kitchen valid."""
        errors = []
        for row in kitchen.rows:
            errors.extend(self.validate_row(row))
        # Cross-row validation
        return errors
    
    def validate_cam_ready(self, kitchen: Kitchen) -> list[str]:
        """Gate 4: CAM ready."""
        errors = []
        for panel in self.all_panels(kitchen):
            if panel.length <= 0:
                errors.append(f"Panel {panel.id} has non-positive length")
            if panel.width <= 0:
                errors.append(f"Panel {panel.id} has non-positive width")
            # Check all edges assigned
            # Check all holes defined
        return errors
```

---

## Summary: What to Steal vs What to Build

### Steal from Plugin

| Pattern | Implementation | Quality |
|---------|---------------|---------|
| **Cabinet Macros** | Catalog + Types | ✅ Production-ready |
| **Sub-product Hierarchy** | Bay → Opening → Part | ✅ Production-ready |
| **Panel Derivation** | Driver formulas | ✅ Production-ready |
| **Object-in-Room** | Wall → Cabinet hierarchy | ✅ Production-ready |
| **Material Separation** | Style system | ✅ Production-ready |
| **Config Validation** | config_parser.py | ✅ Production-ready |

### Build New (Plugin Doesn't Have)

| Pattern | Reason | Priority |
|---------|--------|----------|
| **Construction Method** | Embedded, not first-class | 🔴 Critical |
| **Feature Objects** | No explicit drill/groove | 🔴 Critical |
| **Multi-level Validation** | Only config validation | 🟡 Important |
| **Formula as Data** | Drivers are code | 🟡 Important |
| **BOM Generation** | Not implemented | 🔴 Critical |

### Adapted Architecture for Your System

```python
# 1. Construction Method (from Polyboard pattern)
class ConstructionMethod(BaseModel):
    name: str
    panel_thickness: float
    back_thickness: float
    back_recess: float
    side_joint: JointType
    edge_rules: dict[str, EdgeSpec]
    
    def derive_panels(self, cab: Cabinet) -> list[Panel]:
        """Derive all panels from cabinet + method."""
        ...

# 2. Panel with Features (from TopSolid pattern)
class Panel(BaseModel):
    id: str
    length: float
    width: float
    thickness: float
    edges: dict[str, EdgeBand]
    features: list[MachiningOp]  # ← Features survive changes
    
    def recalculate(self, cab: Cabinet, method: ConstructionMethod):
        """Recalculate dimensions from cabinet."""
        ...

# 3. Kitchen Validator (from TopSolid pattern)
class KitchenValidator:
    def validate_cabinet(self, cab) -> list[str]: ...
    def validate_row(self, row) -> list[str]: ...
    def validate_kitchen(self, kitchen) -> list[str]: ...
    def validate_cam_ready(self, kitchen) -> list[str]: ...

# 4. Style System (from Winner Flex pattern)
class MaterialStyle(BaseModel):
    finish: Decor
    interior: Decor
    edge: EdgeSpec
    
    def apply_to_cabinet(self, cab: Cabinet):
        """Apply materials without touching construction."""
        ...

# 5. Solver (from plugin pattern)
class PanelCalculator:
    def side_panel(self, cab, method) -> Panel: ...
    def bottom_panel(self, cab, method) -> Panel: ...
    def back_panel(self, cab, method) -> Panel: ...
    def shelf_panel(self, cab, method) -> Panel: ...
```

---

## Conclusion

The Blender plugin implements **5 of 7 patterns well**, with **Construction Method** and **Feature-based Operations** being the main gaps. Your system should:

1. **Steal** the plugin's hierarchy, macros, and material separation
2. **Build** Construction Method as first-class entity (Polyboard pattern)
3. **Build** explicit Feature objects for machining (TopSolid pattern)
4. **Build** multi-level validation (TopSolid pattern)

The plugin's **Solver pattern** (solver_face_frame.py) is directly applicable and should be the foundation of your panel calculation system.
