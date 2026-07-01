# Cold Review: Home Builder 5 → kuchnie_core Pipeline

## Architecture Analysis

### Home Builder 5 Data Model

```
Blender Scene
  └─ Room Scene
       └─ Cabinet (Cage)
            │  Custom Properties:
            │    IS_FRAMELESS_CABINET_CAGE = True
            │    CABINET_TYPE = 'BASE' | 'TALL' | 'UPPER'
            │    MENU_ID = 'HOME_BUILDER_MT_cabinet_commands'
            │
            │  Geometry Node Inputs:
            │    Dim X = width (meters)
            │    Dim Y = depth (meters)
            │    Dim Z = height (meters)
            │
            └─ Bay (Cage)
                 │  IS_FRAMELESS_BAY_CAGE = True
                 │
                 └─ Splitter Vertical (Drawer Stack)
                      │  IS_FRAMELESS_SPLITTER_VERTICAL_CAGE = True
                      │  opening_sizes = [150mm, 300mm, 0]  ← drawer heights
                      │
                      └─ Drawer Opening
                           │  IS_FRAMELESS_OPENING_CAGE = True
                           │
                           └─ Drawer Front
                                │  IS_FRAMELESS_FRONT = True
                                │
                                └─ Pull (Handle)
```

### Data Stored on Blender Objects

| Property | Where | Type | Example |
|----------|-------|------|---------|
| `IS_FRAMELESS_CABINET_CAGE` | Cabinet root | bool | True |
| `CABINET_TYPE` | Cabinet root | str | 'BASE' |
| `Dim X` | Geometry node input | float (meters) | 0.6 |
| `Dim Y` | Geometry node input | float (meters) | 0.56 |
| `Dim Z` | Geometry node input | float (meters) | 0.72 |
| `Toe Kick Height` | Property | float (meters) | 0.12 |
| `opening_sizes` | Splitter | list[float] | [0.15, 0.3, 0] |
| `Cabinet Part Name` | Part | str | 'K8685-CH-18-SM' |

### What's Available in Blender Scene

| Data | Available? | How to Extract |
|------|-----------|----------------|
| Cabinet dimensions | ✅ Yes | `obj.inputs['Dim X'].default_value` |
| Cabinet type (base/upper/tall) | ✅ Yes | `obj['CABINET_TYPE']` |
| Drawer count | ✅ Yes | Count children with `IS_FRAMELESS_OPENING_CAGE` |
| Drawer heights | ✅ Yes | `opening_sizes` on splitter |
| Toe kick height | ✅ Yes | `obj['Toe Kick Height']` |
| Material codes | ⚠️ Partial | `Cabinet Part Name` on parts |
| Handle type | ⚠️ Partial | Pull objects stored separately |
| Shelf count | ✅ Yes | Count `IS_FRAMELESS_INTERIOR_PART` |

---

## Gap Analysis

### What kuchnie_core Needs vs What Blender Has

| kuchnie_core Field | Blender Source | Gap? |
|-------------------|----------------|------|
| `id` | Auto-generated name | ✗ Need to assign |
| `type` | `CABINET_TYPE` + children | ✗ Need mapping |
| `width_mm` | `Dim X × 1000` | ✓ Convert m→mm |
| `height_mm` | `Dim Z × 1000` | ✓ Convert m→mm |
| `depth_mm` | `Dim Y × 1000` | ✓ Convert m→mm |
| `body_material` | Part names on carcass | ⚠️ Need extraction |
| `back_material` | Part name on back | ⚠️ Need extraction |
| `front_material` | Part name on front | ⚠️ Need extraction |
| `thickness_side_mm` | Settings (18mm) | ✓ From scene props |
| `thickness_back_mm` | Settings (3mm) | ✓ From scene props |
| `drawers[]` | Splitter children | ⚠️ Need extraction |
| `shelves[]` | Interior parts | ⚠️ Need extraction |
| `fronts[]` | Opening children | ⚠️ Need extraction |
| `handles{}` | Pull objects | ⚠️ Need extraction |

### Type Mapping

| Blender `CABINET_TYPE` + Children | kuchnie_core `type` |
|-----------------------------------|---------------------|
| `BASE` + drawer stack | `dolna_szufladowa` |
| `BASE` + doors | `dolna_drzwiowa` |
| `BASE` + drawer + doors | `dolna_szufladowa` (mixed) |
| `UPPER` + doors | `gorna_drzwiowa` |
| `TALL` + doors | `wysoka_drzwiowa` |
| `BASE` + corner | `narożna` |

---

## Proposed Solution: Blender Export Operator

Add a new operator to Home Builder 5 that exports cabinet data in kuchnie_core format.

### Export Operator

```python
# home_builder_5/operators/ops_export_kuchnie.py

class HB_OT_export_kuchnie(bpy.types.Operator):
    """Export kitchen to kuchnie_core YAML format."""
    bl_idname = "home_builder.export_kuchnie"
    bl_label = "Export for Manufacturing"
    
    filepath: bpy.props.StringProperty(subtype='FILE_PATH')
    
    def execute(self, context):
        kitchen = self._extract_kitchen(context)
        self._save_yaml(kitchen, self.filepath)
        return {'FINISHED'}
    
    def _extract_kitchen(self, context) -> dict:
        """Extract kitchen data from Blender scene."""
        settings = context.scene.hb_frameless
        
        kitchen = {
            'version': '2.0',
            'project_name': context.scene.name,
            'settings': {
                'base_height': settings.base_cabinet_height * 1000,
                'base_depth': settings.base_cabinet_depth * 1000,
                'wall_height': settings.wall_cabinet_height * 1000,
                'wall_depth': settings.wall_cabinet_depth * 1000,
                'plinth_height': settings.default_toe_kick_height * 1000,
                'corpus_thickness': 18,
                'back_thickness': 3,
                'front_thickness': 19,
            },
            'materials': {
                'body': self._get_body_material(settings),
                'back': 'HDF_3mm',
                'front': self._get_front_material(settings),
            },
            'rows': [],
        }
        
        # Group cabinets by wall
        for obj in context.scene.objects:
            if obj.get('IS_FRAMELESS_CABINET_CAGE'):
                cab = self._extract_cabinet(obj, settings)
                # TODO: group by wall
                kitchen['rows'].append({
                    'label': 'Wall',
                    'wall_width_mm': cab['width_mm'],
                    'cabinets': [cab],
                })
        
        return kitchen
    
    def _extract_cabinet(self, obj, settings) -> dict:
        """Extract single cabinet data."""
        dims = self._get_dimensions(obj)
        cab_type = self._detect_type(obj)
        
        cab = {
            'id': obj.name,
            'type': cab_type,
            'description': f"From Blender: {obj.name}",
            'width_mm': dims['width'],
            'height_mm': dims['height'],
            'depth_mm': dims['depth'],
            'body_material': 'UNKNOWN',
            'back_material': 'HDF_3mm',
            'front_material': 'UNKNOWN',
            'thickness_side_mm': 18,
            'thickness_back_mm': 3,
            'thickness_front_mm': 19,
            'drawers': self._extract_drawers(obj),
            'shelves': self._extract_shelves(obj),
            'fronts': self._extract_fronts(obj),
            'handles': self._extract_handles(obj),
        }
        
        return cab
    
    def _get_dimensions(self, obj) -> dict:
        """Extract dimensions from geometry node inputs."""
        # Dimensions are in meters, convert to mm
        width = obj.inputs['Dim X'].default_value * 1000
        depth = obj.inputs['Dim Y'].default_value * 1000
        height = obj.inputs['Dim Z'].default_value * 1000
        return {'width': width, 'depth': depth, 'height': height}
    
    def _detect_type(self, obj) -> str:
        """Detect cabinet type from structure."""
        cab_type = obj.get('CABINET_TYPE', 'BASE')
        
        # Check children for drawer stack
        has_drawers = False
        has_doors = False
        
        for child in obj.children:
            if child.get('IS_FRAMELESS_SPLITTER_VERTICAL_CAGE'):
                has_drawers = True
            if child.get('IS_FRAMELESS_OPENING_CAGE'):
                # Check if it's a drawer or door
                for grandchild in child.children:
                    if grandchild.get('IS_FRAMELESS_FRONT'):
                        # Drawer fronts have different geometry
                        has_drawers = True
                    else:
                        has_doors = True
        
        if cab_type == 'BASE':
            if has_drawers and not has_doors:
                return 'dolna_szufladowa'
            elif has_doors and not has_drawers:
                return 'dolna_drzwiowa'
            else:
                return 'dolna_szufladowa'  # mixed
        elif cab_type == 'UPPER':
            return 'gorna_drzwiowa'
        elif cab_type == 'TALL':
            return 'wysoka_drzwiowa'
        
        return 'dolna_drzwiowa'
    
    def _extract_drawers(self, obj) -> list:
        """Extract drawer configurations."""
        drawers = []
        drawer_idx = 0
        
        for child in obj.children:
            if child.get('IS_FRAMELESS_SPLITTER_VERTICAL_CAGE'):
                sizes = child.get('opening_sizes', [])
                for i, size in enumerate(sizes):
                    if size > 0:  # 0 means equal distribution
                        drawers.append({
                            'id': f'S{i+1}',
                            'height_mm': size * 1000,
                            'system': 'tandembox_antaro',  # default
                            'height_code': self._height_code(size * 1000),
                            'nl': 500,  # default
                        })
        
        return drawers
    
    def _height_code(self, height_mm: float) -> str:
        """Map drawer height to Blum height code."""
        if height_mm <= 83:
            return 'N'
        elif height_mm <= 116:
            return 'M'
        elif height_mm <= 128:
            return 'K'
        elif height_mm <= 177:
            return 'C'
        else:
            return 'F'
```

---

## Data Flow After Integration

```
┌─────────────────────────────────────────────────────────────────┐
│ BLENDER (Home Builder 5)                                        │
│                                                                 │
│  User designs kitchen visually                                  │
│  │                                                              │
│  ▼                                                              │
│  File > Export > Export for Manufacturing                        │
│  │                                                              │
│  ▼                                                              │
│  kitchen.yaml                                                   │
│  - Cabinet types (dolna_szufladowa, etc.)                       │
│  - Dimensions (mm)                                              │
│  - Drawer configs (system, height_code, nl)                     │
│  - Material codes (from part names)                             │
└──────────────┬──────────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────────┐
│ kuchnie_core                                                    │
│                                                                 │
│  load_kitchen("kitchen.yaml")                                   │
│  │                                                              │
│  ▼                                                              │
│  Kitchen → decompose_kitchen() → DecompositionResult[]          │
│  │                                                              │
│  ▼                                                              │
│  export_cutlist_csv() → cut_list.csv                            │
│  kitchen_bom() → hardware_bom.csv                               │
└─────────────────────────────────────────────────────────────────┘
```

---

## Implementation Plan

### Step 1: Add Export Operator to Home Builder 5

Create `operators/ops_export_kuchnie.py` with:
- `_extract_kitchen()` — main extraction
- `_extract_cabinet()` — per-cabinet extraction
- `_extract_drawers()` — drawer configuration
- `_extract_shelves()` — shelf count
- `_extract_fronts()` — front configuration
- `_extract_handles()` — handle specs

### Step 2: Material Code Extraction

The hardest part — extracting material codes from Blender parts.

**Options:**
1. Store material codes as custom properties on parts
2. Parse part names (e.g., "K8685-CH-18-SM")
3. Use scene-level material assignment

**Recommendation:** Store material codes as custom properties during cabinet creation.

### Step 3: Type Detection

Map Blender's `CABINET_TYPE` + children structure to kuchnie_core types.

**Logic:**
```
BASE + drawer_stack → dolna_szufladowa
BASE + doors → dolna_drzwiowa
UPPER + doors → gorna_drzwiowa
TALL + doors → wysoka_drzwiowa
```

### Step 4: Drawer Height → Blum Height Code

Map drawer height to LEGRABOX/TANDEMBOX height code:
```
≤ 83mm  → N
≤ 116mm → M
≤ 128mm → K
≤ 177mm → C
> 177mm → F
```

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Material codes not stored | Can't generate BOM | Add property storage during creation |
| Type detection wrong | Wrong decomposition | Validate against known patterns |
| Dimensions in meters | mm conversion errors | Explicit conversion with validation |
| Drawer heights not exact | Wrong Blum height code | Round to nearest valid height |

---

## Recommendation

**Yes, Home Builder 5 can be adapted.** The data is available in the Blender scene — we just need to extract it.

**Approach:**
1. Add export operator to Home Builder 5
2. Extract cabinet data from custom properties + geometry node inputs
3. Map to kuchnie_core format
4. Save as YAML

**Effort:** ~2-3 days for basic implementation, ~1 week for full material code support.

Want me to implement the export operator?
