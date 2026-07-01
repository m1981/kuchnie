# kuchnie_core — Architecture & Contracts

## Purpose

`kuchnie_core` is the **manufacturing decomposition engine**.  
It takes a DESIGN-level description (cabinet list with dimensions) and produces MANUFACTURING-level output (cut list, drilling, hardware BOM).

```
DESIGN                          MANUFACTURING
┌─────────────┐                ┌─────────────────┐
│ Kitchen     │                │ Cut list CSV    │
│  └─ Row     │  ──────────►   │ DXF per panel   │
│     └─ Cab  │  kuchnie_core  │ Hardware BOM    │
└─────────────┘                └─────────────────┘
```

---

## Collaborators (Who calls kuchnie_core?)

| Collaborator | Role | Calls | Receives |
|--------------|------|-------|----------|
| **kitchen-app** (Reflex UI) | Web configurator | `decompose()`, `calculate_bom()` | `DecompositionResult`, `BOM` |
| **kitchen-cad** | Panel calculator | `Panel`, `MachiningOp` | (consumes types) |
| **Home Builder 5** (Blender) | 3D visualization | `Kitchen`, `Row`, `CabinetInstance` | (provides layout) |
| **catalog/** (SQLite) | Material database | `SqliteMaterialCatalog` | `VariantInfo`, `EdgeInfo` |
| **YAML fixtures** | Cabinet definitions | `load_cabinet()`, `load_kitchen()` | `CabinetInstance`, `Kitchen` |

---

## Data Flow (Execution Paths)

### Flow 1: Single Cabinet Decomposition
```
YAML file
  │
  ▼
load_cabinet(path)
  │
  ▼
CabinetInstance
  │
  ▼
decompose(cab)
  │  ┌─────────────────────────────────┐
  │  │ TYPE_REGISTRY[cab.type](cab)    │
  │  │                                 │
  │  │ decompose_dolna_szufladowa()    │
  │  │ decompose_gorna_drzwiowa()      │
  │  │ decompose_dolna_legrabox()      │
  │  └─────────────────────────────────┘
  │
  ▼
DecompositionResult
  ├─ panels: list[Panel]
  └─ accessories: list[Accessory]
```

### Flow 2: Kitchen Decomposition
```
YAML file (kitchen)
  │
  ▼
load_kitchen(path)
  │
  ▼
Kitchen
  ├─ rows: list[Row]
  │    └─ cabinets: list[CabinetInstance]
  └─ worktops: list[WorktopSegment]
  │
  ▼
decompose_kitchen(kitchen)
  │  ┌─────────────────────────────────┐
  │  │ for cab in row.cabinets:        │
  │  │   decompose(cab)                │
  │  └─────────────────────────────────┘
  │
  ▼
dict[cabinet_id → DecompositionResult]
  │
  ▼
all_panels(kitchen)       → list[Panel]
all_accessories(kitchen)  → list[Accessory]
kitchen_bom(kitchen)      → BOM
```

### Flow 3: BOM Calculation
```
DecompositionResult
  │
  ▼
calculate_bom(result, board_prices?, edge_prices?)
  │
  ▼
BOM
  ├─ cabinet_id: str
  ├─ items: list[BOMItem]
  │    ├─ category: "panel" | "edge" | "accessory"
  │    ├─ name: str
  │    ├─ quantity: float
  │    ├─ unit_price: float
  │    └─ total: float
  └─ total_cost: float
```

### Flow 4: Export
```
Kitchen
  │
  ▼
export_cutlist_csv(kitchen, path)
  │  ┌─────────────────────────────────┐
  │  │ all_panels(kitchen)             │
  │  │ aggregate_panels(panels)        │
  │  │ → CutPiece[]                    │
  │  └─────────────────────────────────┘
  │
  ▼
CSV file (cut list for CNC)
```

---

## Contracts (Input/Output Specifications)

### Contract 1: CabinetInstance

**Input:** YAML file or programmatic construction

**Required fields:**
| Field | Type | Constraints |
|-------|------|-------------|
| `id` | str | Non-empty |
| `type` | str | Must be in `TYPE_REGISTRY` |
| `description` | str | Any |
| `width_mm` | int | > 0, > 2×thickness_side_mm |
| `height_mm` | int | > 0 |
| `depth_mm` | int | > 0 |
| `body_material` | str | Material code |
| `back_material` | str | Material code |
| `front_material` | str | Material code |

**Validation (enforced by `__post_init__`):**
- `width_mm > 0`
- `height_mm > 0`
- `depth_mm > 0`
- `thickness_side_mm > 0`
- `width_mm > 2 × thickness_side_mm` (internal width must be positive)

**Output:** Validated `CabinetInstance` or `ValueError`

---

### Contract 2: decompose(cab)

**Input:** `CabinetInstance`

**Preconditions:**
- `cab.type` must be in `TYPE_REGISTRY`
- All dimensions must be positive
- Internal width must be positive

**Output:** `DecompositionResult`

**Postconditions:**
- All `Panel.width_mm > 0`
- All `Panel.height_mm > 0`
- All `Panel.thickness_mm > 0`
- `len(result.panels) > 0`

**Raises:** `KeyError` if `cab.type` not in registry

---

### Contract 3: ConstructionMethod

**Input:** Thickness parameters + joinery rules

**Derived formulas (all return positive for valid inputs):**
| Method | Formula | Example |
|--------|---------|---------|
| `carcass_bottom_width(w)` | `w - 2×side` | `800 - 36 = 764` |
| `back_panel_width(w)` | `w - 2×side + 2×groove` | `800 - 36 + 16 = 780` |
| `back_panel_height(h)` | `h + groove` | `620 + 8 = 628` |
| `shelf_width(w)` | `bottom_w - 2` | `764 - 2 = 762` |
| `door_width(w, n)` | `(w - gap×(n+1)) / n` | `(800 - 9) / 2 = 395.5` |
| `door_height(h)` | `h - 6` | `720 - 6 = 714` |

**Validation:** `validate_cabinet_width(w)` → list of errors

---

### Contract 4: DrawerSystem

**Input:** KB (internal width), NL (nominal length), height_code

**Methods:**
| Method | Returns | Valid Range |
|--------|---------|-------------|
| `lw(kb)` | `kb - 2×clearance` | > 0 (raises ValueError) |
| `side_height(code)` | float | > 0 |
| `back_panel_height(code)` | float | > 0 |
| `base_panel_width(lw)` | `lw - 35` | > 0 |
| `back_panel_width(lw)` | `lw - 38` | > 0 |

**Validation:**
- `is_valid_combo(code, nl)` → bool
- `decompose_drawer_box()` raises `ValueError` for invalid code/NL

---

### Contract 5: BlumHinge

**Input:** Cabinet ID, door ID, quantity

**Output:** `Accessory` with:
- `type = "hinge"`
- `quantity = count`
- `name` includes hinge spec

**Hinge count formula:**
| Door Height | Hinges |
|-------------|--------|
| ≤ 1200mm | 2 |
| 1201-1800mm | 3 |
| > 1800mm | 4 |

---

### Contract 6: RecipeSchema

**Input:** JSON dict with:
```json
{
  "cabinet_type": "dolna_szufladowa",
  "panels": [
    {
      "id": "side",
      "name": "Lewy bok",
      "width_formula": "depth",
      "height_formula": "height - plinth",
      "thickness_formula": "side_thickness"
    }
  ]
}
```

**Validation:**
- `cabinet_type` required
- `panels` required, non-empty
- Each panel: `id`, `name`, `width_formula`, `height_formula`, `thickness_formula` required

**Formula evaluator:**
- Allowed: `+`, `-`, `*`, `/`, `//`, `%`, parentheses, unary `-`
- NOT allowed: function calls, attribute access, comparisons
- Variables from context dict
- Returns `float`
- Raises `RecipeValidationError` for invalid syntax or missing variables

---

## Type Summary

### Core Domain Types
```
Kitchen
  └─ Row
       └─ CabinetInstance
            └─ [decompose()] → DecompositionResult
                                 ├─ Panel
                                 │    ├─ EdgeBand (per edge)
                                 │    └─ MachiningOp[] (drills, grooves)
                                 └─ Accessory
```

### Hardware Types
```
ConstructionMethod      — panel thicknesses + joinery rules
DrawerSystem            — Blum drawer system (TANDEMBOX/MERIVOBOX/LEGRABOX)
BlumHinge               — Blum hinge (ClipTop 110°/95°/155°)
```

### Recipe Types
```
RecipeSchema            — complete cabinet recipe (JSON)
PanelRecipe             — one panel's formulas
evaluate_formula()      — safe AST-based evaluator
```

### Export Types
```
BOM                     — bill of materials
BOMItem                 — single line item
CutPiece                — aggregated panel for cut list
```

---

## External Dependencies

| Dependency | Used By | Purpose |
|------------|---------|---------|
| `sqlite3` | `materials/` | Catalog DB access |
| `yaml` | `loader.py` | YAML parsing |
| `csv` | `export/` | CSV export |
| `json` | `serialize.py` | JSON roundtrip |
| `ast` | `recipe.py` | Safe formula parsing |

**No external packages required** — pure Python stdlib.

---

## Error Handling

| Error | Raised By | Cause |
|-------|-----------|-------|
| `ValueError` | `CabinetInstance.__post_init__` | Invalid dimensions |
| `ValueError` | `DrawerSystem.lw()` | KB too small |
| `ValueError` | `DrawerSystem.decompose_drawer_box()` | Invalid height_code or NL |
| `KeyError` | `TYPE_REGISTRY[type]` | Unknown cabinet type |
| `KeyError` | `DrawerSystemFactory.get()` | Unknown drawer system |
| `KeyError` | `HingeFactory.get()` | Unknown hinge |
| `RecipeValidationError` | `evaluate_formula()` | Invalid formula or missing variable |
| `RecipeValidationError` | `RecipeSchema.from_dict()` | Missing required fields |
| `FileNotFoundError` | `load_cabinet()` | YAML file not found |
