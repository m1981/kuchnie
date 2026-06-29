# Implementation Placement: Where Each "Best-Of" Pattern Belongs

> **Question this document answers:** For each pattern stolen from PRO100 / Polyboard / Winner Flex / TopSolid'Wood / PaletteCAD — should it live in (a) the Blender plugin, (b) `kuchnie_core`, (c) `kitchen-cad`, (d) `kitchen-app`, or (e) `catalog/`?

> **Companion docs:** `01_architecture.md` (plugin internals), `02_pattern_analysis.md` (plugin vs. commercial CAD).

---

## TL;DR — The Placement Rule

```
┌────────────────────────────────────────────────────────────────────────┐
│  RULE OF THUMB                                                         │
│                                                                        │
│  • Plugin = RENDERER (visual output only, headless Blender)            │
│  • kuchnie_core = TRUTH (single source of cabinet/panel/material)      │
│  • kitchen-cad = MANUFACTURING (panels, drilling, DXF, CSV)            │
│  • kitchen-app = CONFIGURATION (web UI, BOM, cost, project mgmt)       │
│  • catalog/ = REFERENCE DATA (decors, edges, pairings)                 │
│                                                                        │
│  If a pattern changes the DOMAIN MODEL → kuchnie_core                  │
│  If a pattern changes WHAT RENDERS    → plugin extension               │
│  If a pattern changes WHAT'S CUT      → kitchen-cad                    │
│  If a pattern changes WHAT USER SEES  → kitchen-app                    │
│  If a pattern changes MATERIAL DATA   → catalog/                       │
└────────────────────────────────────────────────────────────────────────┘
```

---

## Decision Matrix

| Pattern | Source | Plugin Status | Primary Home | Why There | Touched Apps |
|---|---|---|---|---|---|
| **Construction Method** | Polyboard | ⚠️ Missing as entity | `kuchnie_core` | Domain truth, used by all | core → cad, app, plugin |
| **Panel Derivation Formulas** | All five | ✅ Has (as drivers) | `kuchnie_core` + `kitchen-cad` | Recipe data lives in core, calc engine in cad | core, cad |
| **Material ≠ Construction** | Winner Flex | ✅ Has (Style system) | `catalog/` + `kuchnie_core` | Already separated — keep discipline | catalog, core |
| **Cabinet Macros** | PRO100 | ✅ Has (bay presets) | `kuchnie_core` (data) + `kitchen-app` (UI) | Templates are data, UX is in web | core, app |
| **Sub-product Hierarchy** | Winner Flex | ✅ Has (Bay/Opening) | `kuchnie_core` | Pure model concern | core |
| **Feature-based Operations** | TopSolid | ⚠️ Visual only | `kitchen-cad` | Manufacturing concern | cad |
| **Object-in-Room Model** | PaletteCAD | ✅ Has (multi-scene) | `kitchen-app` (rows) + plugin (3D) | Placement differs per use case | app, plugin |
| **Validation Gates** | TopSolid | ⚠️ Partial | `kuchnie_core` | Each layer validates own concern | core (+ all consumers) |

---

## Pattern 1 — Construction Method (Polyboard)

### What the plugin has

The plugin **mixes construction rules into cabinet type classes**. Look at `frameless/types_frameless.py`:

```python
class BaseCabinet(Cabinet):
    def create(self, name='Base Cabinet'):
        self.create_base_carcass(name)   # ← construction logic embedded
        self.add_exterior()
```

And `config_parser.py` has global settings:

```python
DEFAULTS = {
    "corpusThickness": 18,
    "frontThickness": 19,
    "backThickness": 3,
    "grooveOffset": 10,
    "frontOverlay": 2,
}
```

Construction parameters are **global per project**, not a swappable object. If you want to switch from groove-back to nailed-back, you can't — it's hardcoded in `create_base_carcass()`.

The UI exposes `draw_construction()` panel, but that's just visual grouping — there's no `ConstructionMethod` entity.

### Where to implement

**Primary home: `kuchnie_core/construction.py` (NEW)**

```python
# kuchnie_core/construction.py
@dataclass(frozen=True)
class ConstructionMethod:
    """How a cabinet is assembled — independent of what it is."""
    id: str                       # "dowel_camlock_18"
    name: str                     # "Dowel + Cam-lock, 18mm"
    
    # Panel thicknesses
    side_thickness_mm: int        # 18
    top_thickness_mm: int         # 18
    bottom_thickness_mm: int      # 18
    back_thickness_mm: int        # 3
    shelf_thickness_mm: int       # 18
    front_thickness_mm: int       # 19
    
    # Joinery
    side_to_top: JoineryType      # DOWEL_CAMLOCK | CONFIRMAT | DADO
    back_attachment: BackType     # GROOVE | NAILED | RABBET
    back_recess_mm: int           # 10 (groove offset from rear)
    
    # Overlays / gaps
    front_overlay_mm: int         # 2
    front_gap_mm: int             # 2
    cabinet_gap_mm: int           # 0
    
    # Drilling system
    drilling_system: str          # "system32"
    system32_offset_mm: int       # 37
    system32_spacing_mm: int      # 32

# Cabinet references method, doesn't embed rules
@dataclass
class CabinetInstance:
    id: str
    type_id: str                            # "base_door_single"
    construction_method_id: str             # ← reference, not rules
    width_mm: int
    height_mm: int
    depth_mm: int
    material_refs: MaterialRefs             # separate concern
```

**Why `kuchnie_core` and not plugin extension:**

1. Construction method is used by **all three consumers**: kitchen-cad (panel sizes), plugin (3D visualization), kitchen-app (BOM thickness lookups). One source of truth.
2. Pure data — no Blender dependency.
3. Swap method once → all panels recalculate everywhere.

**What changes downstream:**

| Consumer | Change |
|---|---|
| `kitchen-cad/panel_calculator.py` | Read `cabinet.construction_method.side_thickness_mm` instead of `SETTINGS["corpusThickness"]` |
| `kitchen-cad/drill_engine.py` | Read `construction_method.system32_offset_mm` |
| Blender plugin (your renderer adapter) | Pass construction params into Blender scene as object properties |
| `kitchen-app` (Reflex) | Show construction method dropdown in project settings |

**Plugin extension needed?** Minimal. The plugin already accepts `corpusThickness`, `frontThickness`, etc. as scene settings — you just feed it from your `ConstructionMethod` object.

---

## Pattern 2 — Panel Derivation Formulas (all five systems)

### What the plugin has

The plugin uses **two parallel approaches** that don't talk to each other:

1. **Geometry Node drivers** (Blender-native, runtime expressions):
   ```python
   # hb_types.py
   def driver_input(self, input_name, expression, variables=[]):
       """e.g. expression='var_width - 2 * var_thickness'"""
   ```
2. **Python solver functions** (`solver_face_frame.py`):
   ```python
   def carcass_inner_depth(layout) -> float:
       return layout.depth - layout.back_thickness - layout.back_recess
   ```

Both are **code, not data**. You can't preview a recipe, swap one, or version it without editing Python.

### What you already started

`kitchen-app/kitchen_erp/recipe_loader.py`:
```python
def eval_formula(formula: str, cabinet_dims: dict[str, float]) -> float
def get_recipe(recipe_id: str) -> dict[str, Any]
```

This is the right direction — formulas stored as data (JSON), evaluated against cabinet dims. ⚠️ But it uses `eval()` (security concern noted in earlier analysis).

### Where to implement

**Primary home: `kuchnie_core/recipes/` (NEW package) + `kitchen-cad` (engine)**

Split into two parts:

#### Part A — Recipe data (kuchnie_core)

```yaml
# kuchnie_core/recipes/base_door_single.yaml
recipe_id: base_door_single
panels:
  - role: side_left
    formula:
      width:  "cabinet.depth"
      height: "cabinet.height - plinth.height"
      thickness: "construction.side_thickness_mm"
    edges:
      front: "front_color"
      rear:  "body_color"
      top:   "body_color"
      bottom: "body_color"
  
  - role: top
    formula:
      width:  "cabinet.width - 2 * construction.side_thickness_mm"
      depth:  "cabinet.depth - construction.back_thickness_mm - construction.back_recess_mm"
      thickness: "construction.top_thickness_mm"
  
  - role: shelf
    quantity_formula: "cabinet.shelf_count"
    formula:
      width:  "top.width - 4"   # 2mm clearance each side
      depth:  "top.depth - 10"
      thickness: "construction.shelf_thickness_mm"
  
  - role: door
    quantity_formula: "cabinet.door_count"
    formula:
      width:  "(cabinet.width - (cabinet.door_count - 1) * construction.front_gap_mm) / cabinet.door_count"
      height: "cabinet.height - 2 * construction.front_overlay_mm"
      thickness: "construction.front_thickness_mm"

drilling:
  - role: side_left
    pattern: system32
    columns: [front, rear]
  - role: side_left
    pattern: hinges
    count_formula: "cabinet.height > 900 ? 3 : 2"
```

#### Part B — Formula engine (kitchen-cad)

Replace the unsafe `eval()` in `recipe_loader.py` with a safe evaluator:

```python
# kitchen-cad/src/kitchen_cad/formula_engine.py
import asteval  # safe expression evaluator

class FormulaContext:
    """Read-only context for formula evaluation."""
    def __init__(
        self,
        cabinet: CabinetInstance,
        construction: ConstructionMethod,
        derived: dict[str, float],  # previously-calculated panels
    ):
        ...

class RecipeEngine:
    def calculate_panels(
        self,
        recipe: Recipe,
        cabinet: CabinetInstance,
        construction: ConstructionMethod,
    ) -> list[Panel]:
        """Evaluate all formulas in dependency order."""
```

**Why split across two apps:**

| Concern | Lives in | Reason |
|---|---|---|
| Recipe definitions (YAML) | `kuchnie_core/recipes/` | They're domain truth |
| Recipe **data model** (Pydantic) | `kuchnie_core/model.py` | Other apps need to type-check |
| Formula **evaluation engine** | `kitchen-cad` | Heavy logic, only manufacturing needs it |
| Recipe **selection UI** | `kitchen-app` | User picks "drawer stack 3" → recipe `base_drawer_3x` |

**Plugin extension needed?** No. Plugin receives already-calculated panel dimensions. Don't push formula eval into Blender.

---

## Pattern 3 — Material ≠ Construction (Winner Flex)

### What the plugin has

✅ **Already done well.** `Frameless_Cabinet_Style` is decoupled from `Cabinet`:

```python
class Frameless_Cabinet_Style(PropertyGroup):
    def assign_style_to_cabinet(self, cabinet_obj):
        """Apply finish, interior, door style — no geometry change."""
```

You can swap oak → white gloss without touching construction. ✅

### Where to implement (maintain discipline)

**Primary home: `catalog/` (material data) + `kuchnie_core` (references)**

The **separation already exists** in your stack:

```
catalog/                          → Decor, Edge, Material, Pairing entities
  └── kronospan / egger YAML
kuchnie_core/model.py             → Cabinet holds material_ref (not material data)
kitchen-app                       → User picks decor → stores ID reference
plugin (your adapter)             → Receives decor ID → looks up texture path
kitchen-cad                       → Receives decor ID → looks up edge spec for CSV
```

**Action items to maintain discipline:**

1. ❌ **Don't** let cabinets store decor properties (color hex, texture path) directly.
2. ✅ **Do** store only `decor_id: str` — let each app resolve via `catalog/`.
3. ❌ **Don't** let the Blender plugin embed material logic (it currently has `wood_materials.py` with hardcoded procedural shaders — replace with texture lookup from catalog).
4. ✅ **Do** add a `MaterialResolver` service in `kuchnie_core` that each app calls.

```python
# kuchnie_core/material_resolver.py
class MaterialResolver:
    def __init__(self, catalog_db: CatalogDB):
        self.catalog = catalog_db
    
    def resolve(self, decor_id: str) -> ResolvedMaterial:
        """Decor ID → texture path + edge spec + color hex."""
        decor = self.catalog.find_decor(decor_id)
        return ResolvedMaterial(
            texture_path=decor.texture_path,
            edge_id=self.catalog.find_paired_edge(decor_id).id,
            color_hex=decor.color_hex,
            grain_direction=decor.grain_direction,
        )
```

**Plugin extension needed?** Minor — replace plugin's hardcoded `wood_materials.py` with a thin adapter that reads texture paths from your `ResolvedMaterial`.

---

## Pattern 4 — Cabinet Macros (PRO100)

### What the plugin has

✅ **Strong implementation** via `bay_presets.py`:

```python
def default_bay_config(cabinet_name, bay_width):
    """Returns L(...) / H(...) / V(...) tree — the macro."""

def apply_bay_preset(bay_obj, config):
    """Apply preset, allowing per-instance overrides."""
```

And `catalog/catalog_data.py` defines reusable templates:

```python
def _ff(cabinet_name, bay_qty=1):
    return {
        'id': f'ff_{cabinet_name}',
        'action': 'hb_face_frame_OT_draw_cabinet',
        'params': {'cabinet_name': cabinet_name, 'bay_qty': bay_qty},
    }
```

This is the "drag from sidebar" pattern your use case requires.

### Where to implement

**Primary home: `kuchnie_core/templates/` (data) + `kitchen-app` (sidebar UI)**

```python
# kuchnie_core/templates.py
@dataclass(frozen=True)
class CabinetTemplate:
    """A 'macro' — predefined cabinet with overridable dims."""
    id: str                          # "base_door_60_3shelves"
    label: str                       # "Base 600mm, single door, 3 shelves"
    category: str                    # "base" | "wall" | "tall" | "corner"
    recipe_id: str                   # → kuchnie_core/recipes/
    construction_method_id: str      # → default, user can override at project level
    
    # Default dimensions (overridable per instance)
    default_width_mm: int
    default_height_mm: int
    default_depth_mm: int
    
    # Allowed ranges
    width_min_mm: int
    width_max_mm: int
    
    # Default sub-products
    shelves: int = 0
    drawers: int = 0
    doors: int = 1
    door_swing: str = "right"
    
    # Thumbnail
    thumbnail_path: str = ""

# Template registry — loaded from YAML at startup
class TemplateRegistry:
    def list_by_category(self, category: str) -> list[CabinetTemplate]: ...
    def find(self, template_id: str) -> CabinetTemplate: ...
    def instantiate(self, template_id: str, overrides: dict) -> CabinetInstance: ...
```

**Why split:**

| Concern | App | Reason |
|---|---|---|
| Template **definitions** | `kuchnie_core/templates/*.yaml` | Used by web app, CAD, plugin |
| Template **registry / loader** | `kuchnie_core/templates.py` | Pure Python |
| Sidebar **UI** | `kitchen-app` (Reflex) | Visual, user-facing |
| Template **thumbnails** | `kitchen-app/assets/` | Static files for web |

**Plugin extension needed?** No. Plugin receives instantiated `CabinetInstance` with concrete dimensions — it doesn't need to know about templates.

---

## Pattern 5 — Sub-product Hierarchy (Winner Flex)

### What the plugin has

✅ **Strong.** The hierarchy is real:

```
Cabinet → CabinetBay → CabinetOpening → CabinetFront / CabinetInterior
                                    └─ CabinetDoor / CabinetDrawerFront / Pullout
                                    └─ CabinetShelves / InteriorSplitterVertical
```

Each level is its own class with own properties.

### Where to implement

**Primary home: `kuchnie_core/model.py` (extend existing)**

Your current model has `CabinetInstance → Panel/Accessory`. That's too flat. Add the middle layer:

```python
# kuchnie_core/model.py
@dataclass
class CabinetInstance:
    id: str
    template_id: str
    construction_method_id: str
    dimensions: Dimensions
    material_refs: MaterialRefs
    sub_assemblies: list[SubAssembly]   # ← NEW

@dataclass
class SubAssembly:
    """A drawer box, a door pair, a shelf bank — composable unit."""
    id: str
    kind: SubAssemblyKind   # DOOR | DRAWER_BOX | SHELF_BANK | CARGO
    position: Position      # where in cabinet
    panels: list[Panel]     # the actual cut parts
    accessories: list[Accessory]   # hinges, runners, pulls

# DecompositionResult now nests:
# Kitchen → Row → CabinetInstance → SubAssembly → Panel/Accessory
```

**Why `kuchnie_core` only:**

- This is a **pure model concern**.
- The Blender plugin already nests this way internally (Bay/Opening) — your adapter just maps `SubAssembly` → Blender's Bay/Opening.
- The CAD app flattens to `Panel[]` for cutting, but BOM benefits from grouping ("this drawer needs box + runners + pull").

**Plugin extension needed?** No, plugin already has the hierarchy.

---

## Pattern 6 — Feature-based Operations (TopSolid'Wood)

### What the plugin has

⚠️ **Visual only.** The plugin has notches and grooves as Geometry Node modifiers:

```python
def _set_notch(panel_obj, active, x, y, route_depth)
def _set_groove(panel_obj, active, x0, y0, x1, y1, depth, flip_z)
```

These are **rendering features**, not manufacturing features. They don't track:
- Tool diameter
- Feed direction
- Survivability under cabinet resize
- Export to CNC machine codes

### Where to implement

**Primary home: `kitchen-cad/src/kitchen_cad/drill_engine.py` (extend)**

You already have:
```python
class DrillPoint(BaseModel): ...
class DrillFace(str, Enum): ...
class DrillType(str, Enum): ...
def apply_system32(panels, spec) -> list[Panel]
def apply_hinges(panels, spec) -> list[Panel]
def apply_handles(panels, spec) -> list[Panel]
```

**Extend to first-class associative features:**

```python
# kitchen-cad/src/kitchen_cad/features.py (NEW)
@dataclass(frozen=True)
class MachiningFeature:
    """Associative operation that re-evaluates when panel dims change."""
    id: str
    feature_type: FeatureType   # DRILL | GROOVE | RABBET | NOTCH | POCKET
    panel_role: str             # "side_left" | "back" | etc.
    
    # Position formula (re-evaluated on resize)
    position_formula: dict[str, str]   # {"x": "panel.width / 2", "y": "..."}
    
    # Tool spec
    tool_diameter_mm: float
    tool_depth_mm: float
    feed_direction: FeedDirection
    
    # Manufacturing
    operation_order: int
    machine_code: str | None       # for CNC G-code generation

class FeatureEngine:
    def apply_to_panels(
        self,
        panels: list[Panel],
        features: list[MachiningFeature],
        cabinet: CabinetInstance,
    ) -> list[Panel]:
        """Re-evaluate all features against current panel dims."""
```

**Why `kitchen-cad` only:**

- This is the **manufacturing concern** par excellence.
- Plugin doesn't need this — it just needs to know where to render the visual hole.
- Export pipeline (CSV / DXF) consumes features directly.

**Plugin extension needed?** Lightweight. Plugin's adapter receives a list of `(x, y, diameter)` per panel — no associativity logic in Blender.

---

## Pattern 7 — Object-in-Room Model (PaletteCAD)

### What the plugin has

✅ **Strong.** Multi-scene + CabinetPlacement separation:

```python
# kitchen-plugin/src/kitchen/cabinet.py
class CabinetPlacement:
    """Cabinet positioned on a wall — placement ≠ definition."""
    cabinet: Cabinet
    wall_id: str
    offset_along_wall: float
    rotation: float
```

### Where to implement

**Already correctly split.** No new placement needed — but be aware of the **two coordinate models**:

| App | Model | Why |
|---|---|---|
| `kitchen-app` (web) | **Row-based** (1D position in row) | Use case excludes islands/slants in v1.0 — simpler UX |
| `kuchnie_core` | **Row-based** (matches web) | Single source of truth |
| Plugin / renderer | **Wall-based** (2D position + rotation) | 3D scene needs full transform |
| `kitchen-cad` | **None needed** | Cuts panels — doesn't care about placement |

**The adapter pattern:** Your Blender adapter converts row-based → wall-based when generating the scene.

```python
# kuchnie_core/placement.py (NEW)
@dataclass
class RowPlacement:
    """Web-app placement: which row, which slot."""
    row_id: str
    slot_index: int

# In the Blender adapter:
def row_to_wall_placement(
    row: Row,
    cabinet: CabinetInstance,
    slot_index: int,
) -> WallPlacement:
    """Convert row+slot → wall+offset+rotation for Blender."""
    offset = sum(c.width_mm for c in row.cabinets[:slot_index])
    return WallPlacement(
        wall_id=row.wall_id,
        offset_along_wall=offset,
        rotation=row.wall_angle,
    )
```

**Plugin extension needed?** No — plugin already supports wall-based placement.

---

## Pattern 8 — Validation Gates (TopSolid'Wood)

### What the plugin has

⚠️ **Partial.** Plugin validates its own config and manifest:

```python
# config_parser.py: _validate_cabinet(), _validate_drawers()
# manifest_validator.py: check_dimensions(), check_overlaps(), check_run_continuity()
```

But validation is **scattered** and **plugin-specific**. Not reusable by your web app or CLI.

### Where to implement

**Primary home: `kuchnie_core/validation/` (NEW package)**

Mirror TopSolid's four-gate model:

```python
# kuchnie_core/validation/gates.py

class ValidationGate(Protocol):
    def validate(self, target) -> ValidationResult: ...

class CabinetValidationGate:
    """Gate 1: single cabinet sanity."""
    def validate(self, cabinet: CabinetInstance) -> ValidationResult:
        # dims within template's min/max
        # required sub-assemblies present
        # construction method compatible with template
        ...

class RowValidationGate:
    """Gate 2: row-level layout."""
    def validate(self, row: Row, wall_length_mm: int) -> ValidationResult:
        # sum of widths ≤ wall length
        # no overlapping cabinets
        # corner cabinets have adjacent space
        ...

class KitchenValidationGate:
    """Gate 3: whole-kitchen consistency."""
    def validate(self, kitchen: Kitchen) -> ValidationResult:
        # worktop segments cover all base rows
        # plumbing position has sink-base
        # hob position has cooktop-base
        # appliances fit declared cabinets
        ...

class CAMReadinessGate:
    """Gate 4: ready for manufacturing."""
    def validate(self, decomposition: DecompositionResult) -> ValidationResult:
        # all panels have positive dimensions
        # all edges assigned
        # all holes have valid positions
        # cutouts within panel bounds
        # construction method fully resolved
        ...
```

**Each consumer calls the gates relevant to its stage:**

| App | Gates Called |
|---|---|
| `kitchen-app` (on edit) | Gate 1 (Cabinet), Gate 2 (Row) |
| `kitchen-app` (on "generate render") | Gate 1, 2, 3 (Kitchen) |
| Plugin renderer | Gate 3 (assumes input is valid) |
| `kitchen-cad` CLI | All four — refuse to export if any gate fails |

**Plugin extension needed?** Drop plugin's `manifest_validator.py` — replace with a thin wrapper calling Gate 3 + 4.

---

## Cross-Cutting: Where Each App Stops

```
                    ┌─────────────────────────────────────────┐
                    │            kuchnie_core                  │
                    │   (THE truth: types, recipes, methods)   │
                    │                                          │
                    │   ✓ Construction Method                  │
                    │   ✓ Recipes (formula data)               │
                    │   ✓ Templates (cabinet macros)           │
                    │   ✓ Sub-assembly hierarchy               │
                    │   ✓ Validation gates                     │
                    │   ✓ Material resolver                    │
                    └─────────────────────────────────────────┘
                              ▲           ▲           ▲
                              │           │           │
              ┌───────────────┘           │           └────────────────┐
              │                           │                             │
    ┌─────────┴─────────┐    ┌────────────┴────────────┐    ┌──────────┴──────────┐
    │   kitchen-app     │    │      kitchen-cad        │    │   plugin adapter    │
    │   (Reflex web)    │    │   (manufacturing CLI)   │    │  (headless Blender) │
    │                   │    │                         │    │                     │
    │ ✓ Sidebar UI for  │    │ ✓ Formula engine        │    │ ✓ Scene builder     │
    │   templates       │    │ ✓ Feature engine        │    │ ✓ Material texture  │
    │ ✓ Row editor      │    │   (drill/groove/rabbet) │    │   lookup            │
    │ ✓ Cost display    │    │ ✓ CSV export (e-rozkroj)│    │ ✓ Render            │
    │ ✓ BOM view        │    │ ✓ DXF export            │    │                     │
    │ ✓ Decor picker    │    │ ✓ Edge banding tracking │    │ ✗ NO domain logic   │
    └───────────────────┘    └─────────────────────────┘    └─────────────────────┘
              │                           │                             │
              └───────────────┬───────────┴────────────────┬────────────┘
                              │                            │
                    ┌─────────┴────────────────┐  ┌────────┴──────────┐
                    │       catalog/           │  │  home_builder_5   │
                    │   (Kronospan, Egger)     │  │    (plugin proper)│
                    │                          │  │                   │
                    │ ✓ Decors                 │  │ Stays as-is.      │
                    │ ✓ Edges                  │  │ Your adapter      │
                    │ ✓ Pairings               │  │ talks to it via   │
                    │ ✓ Texture paths          │  │ JSON config.      │
                    └──────────────────────────┘  └───────────────────┘
```

---

## What goes INTO the Blender plugin (extensions)

The plugin is **mostly fine as-is** for your use case. Minimal extensions only:

| Extension | Why | Effort |
|---|---|---|
| `config_parser.py` schema bump | Accept your `kitchen_config.yaml` directly | S |
| Texture path resolution | Read decor IDs, load Kronospan/Egger textures | M |
| Headless render entry-point | CLI: `blender --background --python render.py -- config.yaml` | S |
| Remove face_frame at runtime | Speed up loading — you don't need American style | XS |

**What does NOT go into the plugin:**

- ❌ Construction Method logic (lives in `kuchnie_core`)
- ❌ Recipe evaluation (lives in `kitchen-cad`)
- ❌ Validation gates (lives in `kuchnie_core`)
- ❌ BOM / cost calculation (lives in `kitchen-app`)
- ❌ DXF / CSV export (lives in `kitchen-cad`)
- ❌ Material catalog (lives in `catalog/`)

---

## Implementation Priority (Solo Dev, 8-Week Plan)

| Wk | Focus | Patterns Touched | Deliverable |
|---|---|---|---|
| 1 | `kuchnie_core` foundations | Construction Method, Sub-assembly hierarchy | `ConstructionMethod`, refactored `CabinetInstance` |
| 2 | Recipe data + engine | Panel Derivation Formulas | YAML recipes, safe formula evaluator in `kitchen-cad` |
| 3 | Templates + macros | Cabinet Macros | `TemplateRegistry`, 10-15 base templates |
| 4 | Validation gates | Validation | All 4 gates with tests |
| 5 | Material resolver | Material ≠ Construction | `catalog/` integration |
| 6 | Web app sidebar | Cabinet Macros (UI) | Reflex sidebar with template browse |
| 7 | Blender adapter | Object-in-Room | `row → wall placement` converter, headless render CLI |
| 8 | CLI manufacturing | Feature-based Operations | `kitchen-cli cut-list`, `kitchen-cli dxf` |

---

## Decision Summary

> **For each pattern: "Where does this live?" — short answer:**

| Pattern | Answer |
|---|---|
| Construction Method | `kuchnie_core` — pure domain |
| Panel Formulas | `kuchnie_core` (data) + `kitchen-cad` (engine) |
| Material ≠ Construction | `catalog/` (data) — maintain existing separation |
| Cabinet Macros | `kuchnie_core` (templates) + `kitchen-app` (sidebar) |
| Sub-product Hierarchy | `kuchnie_core` only |
| Feature-based Ops | `kitchen-cad` only |
| Object-in-Room | `kitchen-app` (row-based) + plugin adapter (wall-based) |
| Validation Gates | `kuchnie_core` (each app calls relevant gates) |

> **For the Blender plugin: how much extension?** — **Minimal.** It stays a renderer. Your domain logic lives in `kuchnie_core`. The plugin receives JSON, builds the scene, renders.
