# Blender Plugin Architecture Analysis

## Executive Summary

This document analyzes the architectural patterns used in the Home Builder Blender plugin. The plugin follows a **layered architecture** with clear separation between domain logic, Blender integration, and user interface. It demonstrates mature patterns for building complex parametric CAD tools within Blender's ecosystem.

---

## 1. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              BLENDER PLUGIN                                     │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                         UI LAYER                                        │   │
│  │  • Sidebars (view3d_sidebar.py)                                         │   │
│  │  • Menus (menus.py, menu_apend.py)                                      │   │
│  │  • HUD (viewport_hud.py, scene_navigator.py)                            │   │
│  │  • Catalog Browser (catalog/)                                           │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                    │                                           │
│                                    ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                      OPERATOR LAYER                                     │   │
│  │  • Wall Operators (operators/walls.py)                                  │   │
│  │  • Cabinet Operators (operators/ops_placement.py)                       │   │
│  │  • Layout Operators (operators/layouts.py)                              │   │
│  │  • Detail Operators (operators/details.py)                              │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                    │                                           │
│                                    ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                       DOMAIN LAYER                                      │   │
│  │  • Types (types_face_frame.py, types_frameless.py)                      │   │
│  │  • Solvers (solver_face_frame.py)                                       │   │
│  │  • Layout Engine (layout.py, wall.py)                                   │   │
│  │  • Styles (style_options.py, wood_materials.py)                         │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                    │                                           │
│                                    ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                    INFRASTRUCTURE LAYER                                 │   │
│  │  • Geometry Nodes (hb_types.py)                                         │   │
│  │  • Snapping (hb_snap.py)                                                │   │
│  │  • Placement (hb_placement.py)                                          │   │
│  │  • Units (units.py)                                                     │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Core Architectural Patterns

### 2.1 Operator Pattern (Command Pattern)

**Location:** `operators/*.py`

**Purpose:** Encapsulates user actions as objects, enabling undo/redo, modal operations, and UI integration.

**Structure:**
```python
class SomeOperator(bpy.types.Operator):
    """Blender operator base class."""
    
    bl_idname = "namespace.operation_name"  # Unique identifier
    bl_label = "Display Name"               # UI label
    bl_options = {'REGISTER', 'UNDO'}       # Options
    
    # Properties (exposed to UI)
    some_property: FloatProperty(default=1.0)
    
    @classmethod
    def poll(cls, context):
        """Check if operator can execute."""
        return context.object is not None
    
    def execute(self, context):
        """Run the operation."""
        return {'FINISHED'}
    
    def invoke(self, context, event):
        """Called from UI click, can show dialog."""
        return self.execute(context)
    
    def modal(self, context, event):
        """Handle continuous input (mouse move, etc.)."""
        return {'FINISHED'}
    
    def draw(self, context):
        """Draw UI for dialog."""
        layout = self.layout
```

**Variants Identified:**

| Variant | Purpose | Example |
|---------|---------|---------|
| **Simple** | One-shot action | `hb_frameless_OT_delete_cabinet` |
| **Modal** | Continuous interaction | `hb_face_frame_OT_place_cabinet` |
| **Dialog** | Properties + OK/Cancel | `hb_frameless_OT_cabinet_prompts` |
| **Placement** | Wall-based placement | `hb_frameless_OT_place_cabinet` |

**Key Pattern: PlacementMixin**

```python
class PlacementMixin:
    """Shared behavior for wall-based object placement."""
    
    def init_placement(self, context):
        """Initialize placement state."""
    
    def update_snap(self, context, event):
        """Update snapping position."""
    
    def start_typing(self, target, initial_value=''):
        """Enter dimension typing mode."""
    
    def handle_typing_event(self, event) -> bool:
        """Process keyboard input."""
    
    def find_placement_gap(self, wall_obj, cursor_x, object_width):
        """Find available space on wall."""
    
    def get_wall_children_sorted(self, wall_obj):
        """Get sorted cabinets on wall."""
```

**Benefits:**
- Reusable placement logic across different operator types
- Consistent user experience
- Testable business logic separated from Blender specifics

---

### 2.2 Property Group Pattern (Data Model)

**Location:** `props_hb_frameless.py`, `props_hb_face_frame.py`, `hb_props.py`

**Purpose:** Define Blender's data model with typed properties, callbacks, and serialization.

**Structure:**
```python
class SomePropertyGroup(bpy.types.PropertyGroup):
    """Blender property group for data storage."""
    
    # Scalar properties
    name: StringProperty(name="Name")
    width: FloatProperty(name="Width", min=0.01, max=10.0, default=0.6)
    count: IntProperty(name="Count", min=1, max=10, default=1)
    is_active: BoolProperty(name="Active", default=False)
    
    # Enum properties
    style: EnumProperty(
        name="Style",
        items=[
            ('OPTION_A', "Option A", "Description A"),
            ('OPTION_B', "Option B", "Description B"),
        ],
        default='OPTION_A'
    )
    
    # Collection properties (lists)
    items: CollectionProperty(type=ChildPropertyGroup)
    
    # Pointer properties (references)
    material: PointerProperty(type=bpy.types.Material)
    
    # Computed properties
    @property
    def computed_value(self):
        return self.width * self.count
    
    # Update callbacks
    width: FloatProperty(
        name="Width",
        update=lambda self, context: self._on_width_change(context)
    )
    
    def _on_width_change(self, context):
        """Called when width changes."""
        pass
    
    # Registration
    @classmethod
    def register(cls):
        """Register with Blender types."""
        bpy.types.Scene.my_props = PointerProperty(type=cls)
    
    @classmethod
    def unregister(cls):
        """Unregister from Blender types."""
        del bpy.types.Scene.my_props
```

**Property Hierarchy:**

```
Scene Properties
├── Face_Frame_Scene_Props
│   ├── Cabinet styles (CollectionProperty)
│   ├── Door styles (CollectionProperty)
│   ├── Default dimensions
│   └── Library paths
│
├── Frameless_Scene_Props
│   ├── Cabinet styles
│   ├── Door styles
│   ├── Crown details
│   ├── Toe kick details
│   └── Elevation templates
│
└── Home_Builder_Scene_Props
    ├── Global settings
    ├── Annotation settings
    └── Wall material

Object Properties
├── Home_Builder_Object_Props
│   ├── Custom properties (dict-like)
│   ├── Calculators
│   └── Drivers
│
├── Face_Frame_Cabinet_Props
│   ├── Dimensions
│   ├── Styles
│   ├── Corner settings
│   └── Finished ends
│
└── Face_Frame_Bay_Props
    ├── Width
    ├── Height
    ├── Kick height
    └── Interior items
```

---

### 2.3 GeoNode Pattern (Parametric Geometry)

**Location:** `hb_types.py`

**Purpose:** Wrap Blender's Geometry Nodes system for parametric, non-destructive modeling.

**Base Class:**
```python
class GeoNodeObject:
    """Base class for geometry node driven objects."""
    
    def __init__(self, obj: Optional[bpy.types.Object] = None):
        self.obj = obj
    
    def create(self, geo_node_name: str, name: str):
        """Create object with geometry node modifier."""
    
    def add_property(self, name: str, type, value, combobox_items=[]):
        """Add custom property to object."""
    
    def set_property(self, prop_name: str, value):
        """Set custom property value."""
    
    def get_property(self, prop_name: str, default=None):
        """Get custom property value."""
    
    # Driver system
    def driver_input(self, input_name: str, expression: str, variables=[]):
        """Add driver to geometry node input."""
    
    def driver_hide(self, expression: str, variables=[]):
        """Add driver to visibility."""
    
    def var_input(self, input_name: str, name: str):
        """Create variable referencing geometry node input."""
    
    def var_prop(self, prop_name: str, name: str):
        """Create variable referencing custom property."""
```

**Specialized Types:**

```
GeoNodeObject (Base)
├── GeoNodeCage          → Container with dimensions
├── GeoNodeCutpart       → Panel with edge banding
├── GeoNodeWall          → Wall with connections
├── GeoNodeRectangle     → 2D rectangle
├── GeoNodeDoorSwing     → Door with swing angle
├── GeoNodeDrawerBox     → Drawer box assembly
├── GeoNodeHardware      → Handles, pulls
├── GeoNodeDimension     → Annotation dimension
├── GeoNodeArrow         → Annotation arrow
└── GeoNodeText          → Annotation text
```

**Driver System:**

```python
# Example: Door width driven by opening width
door = CabinetDoor()
door.create("Door")

# Create driver: door_width = opening_width - 2 * gap
opening = CabinetOpening()
door.driver_input(
    "Width",
    "var_width - 2 * var_gap",
    variables=[
        door.var_input("Width", "var_width"),  # From opening
        door.var_prop("front_gap", "var_gap"),  # From property
    ]
)
```

**Benefits:**
- Non-destructive parametric modeling
- Real-time updates when dimensions change
- Complex relationships via driver expressions
- Blender handles the geometry evaluation

---

### 2.4 Solver Pattern (Layout Calculation)

**Location:** `solver_face_frame.py`

**Purpose:** Calculate positions, dimensions, and relationships for complex assemblies.

**Structure:**
```python
class FaceFrameLayout:
    """Solver for face frame cabinet layout."""
    
    def __init__(self, cabinet_obj):
        self.cabinet_obj = cabinet_obj
        self._read_bay_data()
    
    def _read_bay(self, bay_obj):
        """Read bay dimensions from object."""
    
    def _read_tree_root(self, bay_obj):
        """Read opening tree structure."""
```

**Solver Functions:**

```python
# Dimension queries
def carcass_inner_depth(layout: FaceFrameLayout) -> float
def left_scribe_offset(layout: FaceFrameLayout) -> float
def bay_x_position(layout: FaceFrameLayout, bay_index: int) -> float
def bay_top_z(layout: FaceFrameLayout, bay_index: int) -> float

# Position calculations
def left_side_position(layout: FaceFrameLayout) -> Vector
def mid_stile_position(layout: FaceFrameLayout, gap_index: int) -> Vector
def opening_position(layout: FaceFrameLayout, bay_index: int, opening_index: int) -> tuple

# Geometry generation
def bay_openings(layout: FaceFrameLayout, bay_index: int) -> list[dict]
def front_leaves(layout, rect, cab_props, opening_props) -> list[dict]
def interior_item_descriptors(layout, rect, cab_props, opening_props) -> list[dict]

# Coordinate transforms
def face_frame_world_basis(cabinet_obj, layout) -> Matrix
def ff_local_to_world(cabinet_obj, layout, ff_x, ff_z) -> Vector
def mouse_to_ff_local(cabinet_obj, layout, region, rv3d, mouse_xy) -> tuple
```

**Key Pattern: Proxy Objects for Overrides**

```python
class _ZeroSwingProxy:
    """Proxy that overrides swing to 0."""
    
    def __init__(self, inner):
        self._inner = inner
    
    def __getattr__(self, name):
        if name == 'swing':
            return 0
        return getattr(self._inner, name)

class _ForceHingeProxy:
    """Proxy that forces hinge type."""
    
    def __init__(self, inner, hinge):
        self._inner = inner
        self._hinge = hinge
    
    def __getattr__(self, name):
        if name == 'hinge':
            return self._hinge
        return getattr(self._inner, name)
```

**Benefits:**
- Complex calculations centralized
- Easy to test independently
- Proxy pattern for configuration overrides
- Separation of "what" from "where"

---

### 2.5 Registry Pattern (Plugin System)

**Location:** `accessory_registry.py`, `appliance_spec_registry.py`

**Purpose:** Allow dynamic registration of components without modifying core code.

**Structure:**
```python
# Registry storage
_providers = {}

def register_provider(host: str, fn: Callable):
    """Register a provider function for a host."""
    _providers[host] = fn

def unregister_provider(host: str):
    """Unregister a provider."""
    _providers.pop(host, None)

def has_provider(host: str) -> bool:
    """Check if provider exists."""
    return host in _providers

def get_items(host: str) -> list:
    """Get items from provider."""
    if host in _providers:
        return _providers[host]()
    return []

def all_items() -> list:
    """Get all items from all providers."""
    items = []
    for provider in _providers.values():
        items.extend(provider())
    return items

def find(code: str) -> Optional[dict]:
    """Find item by code."""
    for item in all_items():
        if item.get('code') == code:
            return item
    return None
```

**Usage Example:**

```python
# In face_frame module
def _get_face_frame_accessories():
    """Provide face frame accessories."""
    return [
        {'code': 'shelf', 'name': 'Adjustable Shelf', 'category': 'shelving'},
        {'code': 'drawer_box', 'name': 'Drawer Box', 'category': 'drawers'},
        # ...
    ]

# Registration
accessory_registry.register_provider('face_frame', _get_face_frame_accessories)

# Query
items = accessory_registry.get_items('face_frame')
shelf = accessory_registry.find('shelf')
```

**Benefits:**
- Loose coupling between modules
- Easy to extend with new components
- No modification of core code required
- Supports multiple product libraries

---

### 2.6 Library Pattern (Asset Management)

**Location:** `catalog/`, `hb_assets.py`, `hb_detail_library.py`

**Purpose:** Manage reusable assets (cabinets, details, materials) with persistence.

**Structure:**
```
Library System
├── Catalog Browser (catalog/)
│   ├── catalog_data.py      → Item definitions
│   ├── previews_catalog.py  → Thumbnail management
│   ├── props_catalog.py     → State management
│   ├── ops_catalog.py       → Operations
│   └── ui_catalog.py        → UI drawing
│
├── Asset Libraries (hb_assets.py)
│   ├── Library paths
│   ├── Asset registration
│   └── Catalog mapping
│
└── Detail Library (hb_detail_library.py)
    ├── Save/Load functions
    ├── Index management
    └── User library path
```

**Catalog Data Structure:**
```python
def _ff(cabinet_name: str, bay_qty: int = 1) -> dict:
    """Create face frame catalog entry."""
    return {
        'id': f'ff_{cabinet_name}',
        'name': cabinet_name.replace('_', ' ').title(),
        'category': 'face_frame',
        'action': 'hb_face_frame_OT_draw_cabinet',
        'params': {'cabinet_name': cabinet_name, 'bay_qty': bay_qty},
        'tags': ['face_frame', cabinet_name],
    }

# Entries
ENTRIES = [
    _ff('base_cabinet'),
    _ff('upper_cabinet'),
    _ff('tall_cabinet'),
    _ff('corner_diagonal'),
    # ...
]
```

**User Library Pattern:**
```python
def save_cabinet_group_to_library(context, name: str, description: str = ''):
    """Save selected cabinet group to user library."""
    # 1. Collect objects
    objects = _collect_objects_recursive(cabinet_group)
    
    # 2. Save to .blend file
    filepath = os.path.join(get_user_library_path(), f"{name}.blend")
    bpy.data.libraries.write(filepath, set(objects))
    
    # 3. Generate thumbnail
    _create_thumbnail(context, cabinet_group, filepath, name)
    
    # 4. Update index
    index = load_library_index()
    index[name] = {'filepath': filepath, 'description': description}
    save_library_index(index)

def load_cabinet_group_from_library(context, filepath: str):
    """Load cabinet group from library."""
    # 1. Load objects from .blend
    with bpy.data.libraries.load(filepath) as (data_from, data_to):
        data_to.objects = data_from.objects
    
    # 2. Link to scene
    for obj in data_to.objects:
        context.collection.objects.link(obj)
```

---

### 2.7 Scene/Room Pattern (Multi-Scene Organization)

**Location:** `hb_project.py`, `operators/rooms.py`, `operators/scene_navigator.py`

**Purpose:** Organize complex projects with multiple rooms and layout views.

**Structure:**
```
Project
├── Main Scene (Project Settings)
├── Room Scenes
│   ├── Room 1 (Kitchen)
│   │   ├── Wall Collection
│   │   ├── Cabinet Collection
│   │   └── Appliance Collection
│   ├── Room 2 (Bathroom)
│   └── Room 3 (Bedroom)
├── Layout Scenes
│   ├── Elevation Views
│   ├── Plan Views
│   └── 3D Views
└── Detail Scenes
    ├── Detail 1
    └── Detail 2
```

**Scene Detection:**
```python
def is_main_scene(scene: bpy.types.Scene) -> bool:
    """Check if scene is the main project scene."""
    return scene.get('is_main_scene', False)

def is_room_scene(scene: bpy.types.Scene) -> bool:
    """Check if scene is a room scene."""
    return scene.get('is_room_scene', False)

def get_room_scenes() -> list:
    """Get all room scenes."""
    return [s for s in bpy.data.scenes if is_room_scene(s)]
```

**Scene Navigator:**
```python
class home_builder_OT_scene_navigator(bpy.types.Operator):
    """Navigate between scenes with visual UI."""
    
    def invoke(self, context, event):
        # Build layout from all scenes
        entries = _build_layout(...)
        return {'RUNNING_MODAL'}
    
    def modal(self, context, event):
        # Handle mouse clicks on scene buttons
        if event.type == 'LEFTMOUSE':
            handle_navigator_click(context, mx, my, entries)
        return {'PASS_THROUGH'}
```

---

### 2.8 Style System Pattern (Material Management)

**Location:** `style_options.py`, `wood_materials.py`, `finish_colors.py`, `props_hb_face_frame.py`

**Purpose:** Manage materials, finishes, and styles across the project.

**Hierarchy:**
```
Style System
├── Cabinet Style
│   ├── Finish (wood + color + varnish + glaze)
│   ├── Interior Material
│   ├── Edge Banding
│   └── Door Styles (Collection)
│       ├── Door Style 1
│       │   ├── Series (e.g., "Shaker")
│       │   ├── Shape (e.g., "Recessed")
│       │   ├── Panel (e.g., "Flat")
│       │   ├── Frame Dimensions
│       │   └── Material Overrides
│       └── Door Style 2
│
├── Finish Colors
│   ├── Stain Colors (JSON database)
│   ├── Paint Colors (JSON database)
│   └── Custom Colors (User-defined)
│
└── Wood Materials
    ├── Procedural (Generated in Blender)
    └── Catalog (From image textures)
```

**Style Assignment:**
```python
class Frameless_Cabinet_Style(PropertyGroup):
    def assign_style_to_cabinet(self, cabinet_obj):
        """Apply this style to a cabinet."""
        # 1. Get finish material
        finish_mat = self.get_finish_material()
        interior_mat = self.get_interior_material()
        
        # 2. Apply to all parts
        for part in get_cabinet_parts(cabinet_obj):
            if is_exterior_part(part):
                part.material = finish_mat
            else:
                part.material = interior_mat
        
        # 3. Apply to fronts
        for front in get_cabinet_fronts(cabinet_obj):
            door_style = self.get_active_door_style()
            door_style.assign_style_to_front(front)
```

**Finish Resolution:**
```python
def colors_for_wood(wood: str) -> list[str]:
    """Get available colors for a wood type."""
    data = get_wood_data(wood)
    return data.get('colors', [])

def varnishes_for_color(color: str) -> list[str]:
    """Get available varnishes for a color."""
    data = get_color_data(color)
    return data.get('varnishes', [])

def hinges_for_overlay(overlay: str) -> list[str]:
    """Get hinge options for overlay type."""
    return {
        'full': ['full_overlay_110', 'full_overlay_95'],
        'half': ['half_overlay_110', 'half_overlay_95'],
        'inset': ['inset_110', 'inset_95'],
    }.get(overlay, [])
```

---

### 2.9 Mixin Pattern (Shared Behavior)

**Location:** `hb_placement.py`

**Purpose:** Provide reusable behavior across multiple operator classes.

**Structure:**
```python
class PlacementMixin:
    """Mixin for wall-based object placement."""
    
    def init_placement(self, context):
        """Initialize placement state."""
        self.placement_state = PlacementState.INITIAL
        self.snap_point = None
        self.wall_obj = None
    
    def update_snap(self, context, event):
        """Update snapping position."""
        # Common snapping logic
        pass
    
    def start_typing(self, target, initial_value=''):
        """Enter dimension typing mode."""
        self.typing_target = target
        self.typed_value = initial_value
    
    def handle_typing_event(self, event) -> bool:
        """Process keyboard input."""
        if event.type == 'BACKSPACE':
            self.typed_value = self.typed_value[:-1]
            return True
        elif event.type in '0123456789.':
            self.typed_value += event.ascii
            return True
        return False

class DimensionOperatorMixin:
    """Mixin for dimension annotation placement."""
    
    def init_dimension_state(self):
        """Initialize dimension state."""
        self.dim_start = None
        self.dim_end = None
        self.dim_leader = None
    
    def handle_dimension_event(self, context, event) -> str:
        """Process dimension input events."""
        # Common dimension logic
        pass
```

**Usage:**
```python
class hb_frameless_OT_place_cabinet(bpy.types.Operator, PlacementMixin):
    """Place cabinet on wall."""
    
    def invoke(self, context, event):
        self.init_placement(context)
        return {'RUNNING_MODAL'}
    
    def modal(self, context, event):
        self.update_snap(context, event)
        # Cabinet-specific logic
        return {'PASS_THROUGH'}

class hb_face_frame_OT_place_cabinet(bpy.types.Operator, PlacementMixin):
    """Place face frame cabinet on wall."""
    
    def invoke(self, context, event):
        self.init_placement(context)
        return {'RUNNING_MODAL'}
```

---

### 2.10 Layout View Pattern (Documentation)

**Location:** `hb_layouts.py`, `operators/layouts.py`

**Purpose:** Generate 2D documentation views from 3D model.

**Class Hierarchy:**
```
LayoutView (Base)
├── ElevationView    → Side/front views with dimensions
├── PlanView         → Top-down floor plan
├── View3D           → 3D perspective view
└── MultiView        → Combined multiple views
```

**View Creation:**
```python
class LayoutView:
    """Base class for layout views."""
    
    def __init__(self, scene=None):
        self.scene = scene
    
    def create(self, name: str) -> bpy.types.Scene:
        """Create new scene for this view."""
        self.scene = bpy.data.scenes.new(name)
        self._setup_render_settings()
        self._create_freestyle_collections()
        return self.scene
    
    def create_camera(self, name, location, rotation) -> bpy.types.Object:
        """Create camera for this view."""
        # Camera creation logic
        pass
    
    def set_paper_size(self, paper_size='LETTER', landscape=True, dpi=None):
        """Set paper dimensions for rendering."""
        # Paper size logic
        pass

class ElevationView(LayoutView):
    """Elevation view with auto-dimensioning."""
    
    def create(self, wall_obj, name=None, paper_size='LETTER', landscape=True):
        """Create elevation view for a wall."""
        # 1. Create scene
        scene = super().create(name or f"{wall_obj.name} Elevation")
        
        # 2. Create camera
        self._fit_camera_to_content(wall_obj)
        
        # 3. Create collections (solid, dashed)
        self._create_content_collections(wall_obj, view_name)
        
        # 4. Add dimensions
        self.add_cabinet_dimensions()
        
        return scene
    
    def add_cabinet_dimensions(self):
        """Add dimension annotations for cabinets."""
        for cabinet_info in self._get_cabinets_on_wall():
            self._create_cabinet_dimension(cabinet_info, ...)
```

---

## 3. Module Dependency Graph

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           DEPENDENCY GRAPH                              │
└─────────────────────────────────────────────────────────────────────────┘

    __init__.py
         │
         ├── hb_props ──────────────────────┐
         │                                  │
         ├── hb_project ────────────────────┤
         │                                  │
         ├── hb_types ──────────────────────┤
         │                                  │
         ├── units ─────────────────────────┤
         │                                  │
         ├── hb_utils ──────────────────────┤
         │                                  │
         ├── hb_snap ───────────────────────┤
         │                                  │
         ├── hb_placement ──────────────────┤
         │                                  │
         ├── hb_details ────────────────────┤
         │                                  │
         ├── hb_layouts ────────────────────┤
         │                                  │
         ├── hb_detail_library ─────────────┤
         │                                  │
         ├── hb_assets ─────────────────────┤
         │                                  │
         ├── accessory_registry ────────────┤
         │                                  │
         ├── operators/walls ───────────────┤
         │                                  │
         ├── operators/doors_windows ───────┤
         │                                  │
         ├── operators/layouts ─────────────┤
         │                                  │
         ├── operators/details ─────────────┤
         │                                  │
         ├── product_libraries/face_frame ──┤
         │    ├── types_face_frame          │
         │    ├── solver_face_frame         │
         │    ├── props_hb_face_frame       │
         │    └── operators/*               │
         │                                  │
         ├── product_libraries/frameless ───┤
         │    ├── types_frameless           │
         │    ├── props_hb_frameless        │
         │    └── operators/*               │
         │                                  │
         ├── product_libraries/common ──────┤
         │    └── types_appliances          │
         │                                  │
         └── catalog/ ──────────────────────┘
              ├── catalog_data
              ├── previews_catalog
              ├── props_catalog
              └── ui_catalog
```

---

## 4. Key Design Decisions

### 4.1 Geometry Nodes Over Traditional Mesh

**Decision:** Use Blender's Geometry Nodes for parametric objects.

**Rationale:**
- Non-destructive editing
- Real-time parameter updates
- Driver integration for complex relationships
- Better performance than Python mesh manipulation

**Trade-offs:**
- Requires Blender 3.0+
- More complex setup
- Debugging is harder
- Node groups must be bundled

### 4.2 Multi-Scene Organization

**Decision:** Separate scenes for rooms, layouts, and details.

**Rationale:**
- Isolate different concerns
- Independent render settings
- Clean organization for complex projects
- Supports multi-view documentation

**Trade-offs:**
- More complex scene management
- Cross-scene references needed
- User must understand scene concept

### 4.3 Property Groups Over Custom Data

**Decision:** Use Blender's PropertyGroup system for all data.

**Rationale:**
- Automatic serialization
- UI integration
- Undo/redo support
- Network replication (for Blender's multiplayer)

**Trade-offs:**
- Limited data types
- Registration overhead
- Cannot store arbitrary Python objects

### 4.4 Mixins Over Composition

**Decision:** Use multiple inheritance (mixins) for shared behavior.

**Rationale:**
- Blender operators require single base class
- Mixins provide shared methods
- Clear inheritance hierarchy

**Trade-offs:**
- Diamond problem potential
- Method resolution order complexity
- Harder to test in isolation

### 4.5 Solver Pattern Over Direct Calculation

**Decision:** Separate solver objects for layout calculation.

**Rationale:**
- Complex calculations centralized
- Easy to test independently
- Supports caching
- Clear separation of concerns

**Trade-offs:**
- Additional abstraction layer
- Solver must stay in sync with objects
- Memory overhead for solver state

---

## 5. Anti-Patterns Identified

### 5.1 God Object: `props_hb_face_frame.py`

**Problem:** Single file with 1000+ lines containing many property groups and callbacks.

**Impact:** Hard to maintain, difficult to find specific code.

**Recommendation:** Split into separate files per property group.

### 5.2 Circular Imports

**Problem:** Some modules import each other (e.g., `types_face_frame` ↔ `props_hb_face_frame`).

**Impact:** Import order issues, potential runtime errors.

**Recommendation:** Use dependency injection or extract shared interfaces.

### 5.3 Magic Numbers

**Problem:** Hardcoded values without named constants (e.g., `0.001`, `0.015`).

**Impact:** Difficult to understand intent, hard to change.

**Recommendation:** Extract to named constants with documentation.

### 5.4 Inconsistent Naming

**Problem:** Mix of `snake_case`, `camelCase`, and `PascalCase`.

**Impact:** Reduced readability, potential confusion.

**Recommendation:** Follow PEP 8 consistently.

### 5.5 Duplicated Code

**Problem:** Similar placement logic in face_frame and frameless operators.

**Impact:** Bug fixes must be applied in multiple places.

**Recommendation:** Extract shared logic to base classes or mixins.

---

## 6. Recommendations for Your System

### 6.1 What to Borrow

| Pattern | Applicability | Notes |
|---------|---------------|-------|
| **Property Groups** | ✅ High | Use Pydantic models instead |
| **GeoNode Pattern** | ⚠️ Medium | Adapt for pure Python geometry |
| **Solver Pattern** | ✅ High | Directly applicable |
| **Registry Pattern** | ✅ High | Use for accessories/hardware |
| **Library Pattern** | ✅ High | Adapt for material catalog |
| **Style System** | ✅ High | Use for decor management |

### 6.2 What to Avoid

| Pattern | Reason |
|---------|--------|
| **Operator Pattern** | Blender-specific, not needed |
| **Multi-Scene** | Use file-based separation instead |
| **Driver System** | Use explicit calculations |
| **Mixin Inheritance** | Use composition instead |

### 6.3 Adapted Architecture

```
Your System
├── Domain Layer (Pure Python)
│   ├── Models (Pydantic)
│   │   ├── Kitchen
│   │   ├── Row
│   │   ├── Cabinet
│   │   └── Panel
│   │
│   ├── Solvers (Inspired by solver_face_frame.py)
│   │   ├── LayoutSolver
│   │   ├── PanelCalculator
│   │   └── CostCalculator
│   │
│   └── Registry (Inspired by accessory_registry.py)
│       ├── MaterialRegistry
│       ├── HardwareRegistry
│       └── CabinetTypeRegistry
│
├── Application Layer
│   ├── Services
│   │   ├── KitchenService
│   │   ├── RenderService
│   │   └── ExportService
│   │
│   └── Commands
│       ├── CreateKitchen
│       ├── AddCabinet
│       └── GenerateBOM
│
├── Infrastructure Layer
│   ├── Blender Integration
│   │   ├── SceneBuilder (Adapted from plugin)
│   │   ├── MaterialApplier
│   │   └── Renderer
│   │
│   ├── File Export
│   │   ├── CutListCSV
│   │   ├── DrillCSV
│   │   └── DXFExport
│   │
│   └── Database
│       ├── MaterialCatalog
│       └── PricingDatabase
│
└── Presentation Layer
    ├── Web UI (Reflex)
    │   ├── LayoutEditor
    │   ├── CabinetConfigurator
    │   └── DecorSelector
    │
    └── CLI
        ├── kitchen-cli cut-list
        ├── kitchen-cli drill
        └── kitchen-cli estimate
```

---

## 7. Conclusion

The Home Builder plugin demonstrates mature architectural patterns for complex Blender addons. The key patterns (Solver, Registry, Library, Style System) are directly applicable to your kitchen design system. The main adaptation needed is removing Blender-specific code and replacing it with pure Python implementations using Pydantic models and explicit calculations.

The plugin's strength lies in its:
1. **Clear separation** between domain logic and Blender integration
2. **Parametric approach** using Geometry Nodes and drivers
3. **Extensible design** via registries and libraries
4. **Comprehensive solver** for layout calculations

Your system should maintain these strengths while using modern Python practices (type hints, Pydantic, clean architecture) instead of Blender's older patterns (PropertyGroups, operators).
