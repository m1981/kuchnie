# Kitchen Plugin Architecture

## Overview

The kitchen plugin generates 3D kitchen cabinet models from JSON configuration
files. It supports I, L, and U kitchen layouts with European frameless
construction standards.

**Primary output:** A structured JSON geometry manifest for inspection and
validation. Visual exports (OBJ, glTF, .blend) are optional extras.

---

## Design Principles

| Principle                        | Rule                                                                                   |
| -------------------------------- | -------------------------------------------------------------------------------------- |
| **Manifest-first**               | Every build produces a JSON manifest with exact geometry. Visual formats are optional. |
| **Inspect where it's generated** | Validate geometry at the source (bpy output), not after lossy format export.           |
| **No unit guessing**             | All data carries explicit units. Never multiply by 1000 and hope.                      |
| **Dependencies point down**      | `core/ ← kitchen/ ← builder/ ← adapters/`. Never reverse.                              |
| **Immutable by default**         | Frozen dataclasses. No accidental mutation.                                            |
| **Z-up, right-hand**             | Architectural/BIM standard. Documented once, enforced everywhere.                      |

---

## Layer Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  Layer 5: Entry Points                                                      │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ main.py (CLI)                    tests/ (pytest)                     │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│       │                         │                    │                      │
│  ┌────▼─────────────────────────▼────────────────────▼──────────────────┐   │
│  │ Layer 4: Adapters (External)                                         │   │
│  │ ┌────────────────────┐ ┌──────────────┐ ┌─────────────────────────┐  │   │
│  │ │ geometry_builder.py│ │ exporters.py │ │ geometry_manifest.py    │  │   │
│  │ │ Blender mesh       │ │ OBJ/glTF     │ │ JSON manifest export    │  │   │
│  │ │ creation (bpy)     │ │ (optional)   │ │ (PRIMARY output)        │  │   │
│  │ └────────────────────┘ └──────────────┘ └─────────────────────────┘  │   │
│  │ ┌────────────────────┐ ┌──────────────────────────────────────────┐  │   │
│  │ │ material_manager.py│ │ manifest_validator.py                    │  │   │
│  │ │ Cycles materials   │ │ Expected-vs-actual, topology checks      │  │   │
│  │ └────────────────────┘ └──────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│       │                                                                     │
│  ┌────▼──────────────────────────────────────────────────────────────────┐   │
│  │ Layer 3: Builder (Config Parsing)                                     │   │
│  │ ┌──────────────────┐ ┌──────────────┐ ┌────────────────────────┐      │   │
│  │ │ config_parser.py │ │ validators.py│ │ wall_builder.py        │      │   │
│  │ │ JSON loading     │ │ Semantic     │ │ Config → Wall/Cabinet  │      │   │
│  │ │ defaults         │ │ validation   │ │ conversion             │      │   │
│  │ └──────────────────┘ └──────────────┘ └────────────────────────┘      │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│       │                                                                     │
│  ┌────▼──────────────────────────────────────────────────────────────────┐   │
│  │ Layer 2: Kitchen (Domain Logic)                                       │   │
│  │ ┌──────────┐ ┌───────────────┐ ┌──────────────┐ ┌─────────────────┐  │   │
│  │ │ wall.py  │ │ cabinet.py    │ │ layout.py    │ │ standards.py    │  │   │
│  │ │ Wall     │ │ Cabinet       │ │ Run          │ │ KitchenStandards│  │   │
│  │ │ Room     │ │ CabinetPlacem.│ │ LayoutEngine │ │ EUROPEAN_STD    │  │   │
│  │ └──────────┘ └───────────────┘ └──────────────┘ └─────────────────┘  │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│       │                                                                     │
│  ┌────▼──────────────────────────────────────────────────────────────────┐   │
│  │ Layer 1: Core (Pure Math)                                             │   │
│  │ ┌────────────────┐ ┌───────────────┐ ┌──────────────────────────┐     │   │
│  │ │ geometry.py    │ │ tolerances.py │ │ types.py                 │     │   │
│  │ │ Vector2D       │ │ Named         │ │ Direction                │     │   │
│  │ │ Vector3D       │ │ tolerances    │ │ CabinetType              │     │   │
│  │ │ BoundingBox    │ │               │ │ CabinetLevel             │     │   │
│  │ │ Transform2D    │ │               │ │ Dimensions               │     │   │
│  │ └────────────────┘ └───────────────┘ └──────────────────────────┘     │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Dependency Rule

```
  core/ ← kitchen/ ← builder/ ← adapters/ ← main.py
    │         │           │           │
    └─────────┴───────────┴───────────┘
        Never reverse arrows
```

| Layer       | Depends on          | External deps                             |
| ----------- | ------------------- | ----------------------------------------- |
| `core/`     | —                   | None                                      |
| `kitchen/`  | `core/`             | None                                      |
| `builder/`  | `core/`, `kitchen/` | JSON                                      |
| `adapters/` | `core/`, `kitchen/` | bpy (geometry_builder), stdlib (manifest) |
| `main.py`   | all                 | bpy, sys                                  |

---

## Data Flow

```
  JSON config
      │
      ▼
  ┌──────────────────┐
  │ config_parser.py  │  Load, apply defaults, validate schema
  └────────┬─────────┘
           │
           ▼
  ┌──────────────────┐
  │ wall_builder.py   │  Config → Wall + Cabinet objects
  └────────┬─────────┘
           │
           ▼
  ┌──────────────────┐
  │ LayoutEngine      │  Calculate positions, detect corners
  └────────┬─────────┘
           │
           ▼
  ┌──────────────────────────────────────────────────────┐
  │ geometry_builder.py (bpy)                             │
  │                                                       │
  │  Builds Blender meshes:                               │
  │  • Carcass (hollow box, 18mm walls)                   │
  │  • Back panel (3mm HDF in groove)                     │
  │  • Front panels (doors/drawers, 19mm thick)           │
  │  • Countertop (with overhangs)                        │
  │  • Fillers, plinths                                   │
  │                                                       │
  │  Applies transforms:                                  │
  │  • Position along wall (accumulated offset)           │
  │  • Rotation for wall direction (0°/90°/180°/270°)    │
  │  • Z placement (plinth, wall-mount, floor)            │
  └────────┬─────────────────────────────────────────────┘
           │
           ├──────────────────────────────────────────────────────────┐
           ▼                                                          ▼
  ┌────────────────────────────┐                       ┌──────────────────────┐
  │ geometry_manifest.py       │  ← PRIMARY OUTPUT     │ exporters.py         │
  │                            │                       │                      │
  │ Exports JSON with:         │                       │ OBJ (optional)       │
  │ • Local + world vertices   │                       │ glTF (optional)      │
  │ • Object hierarchy         │                       │ .blend (for visual   │
  │ • Expected vs actual dims  │                       │   inspection)        │
  │ • Layout metadata          │                       │                      │
  │ • Inline validation        │                       │                      │
  │ • Units, coord system      │                       │                      │
  └────────┬───────────────────┘                       └──────────────────────┘
           │
           ▼
  ┌────────────────────────────┐
  │ manifest_validator.py      │
  │                            │
  │ Reads manifest, checks:    │
  │ • Dimension tolerance      │
  │ • No overlaps              │
  │ • Clearances (≥900mm)      │
  │ • Standard widths          │
  │ • Topology (vertex count)  │
  └────────┬───────────────────┘
           │
           ▼
  ┌────────────────────────────┐
  │ LLM Agent / CI / Human     │
  │ reads structured JSON      │
  └────────────────────────────┘
```

### Why Manifest-First

The old pipeline exported geometry to OBJ/glTF, then re-parsed those formats
to check correctness. This is lossy — OBJ carries no units, no hierarchy, no
metadata. glTF is Y-up with abstract units.

The manifest captures geometry **directly from bpy** with full fidelity:

| What                | OBJ             | glTF            | Manifest                    |
| ------------------- | --------------- | --------------- | --------------------------- |
| Units               | ❌ undefined    | ⚠️ abstract     | ✅ `"units": "meters"`      |
| Coordinate system   | ❌ unspecified  | ✅ Y-up         | ✅ Z-up (our convention)    |
| Object hierarchy    | ❌ flat         | ✅ scene graph  | ✅ parent + layout metadata |
| Local coordinates   | ❌ world only   | ✅ local        | ✅ both local AND world     |
| Rotation            | ❌ lost         | ✅ Euler        | ✅ exact Euler              |
| Expected dimensions | ❌              | ❌              | ✅ inline pass/fail         |
| LLM readability     | ⚠️ needs parser | ⚠️ needs parser | ✅ plain JSON               |

**Rule: Validation reads the manifest. Visual inspection opens .blend. OBJ/glTF
are for interoperability with external tools only.**

---

## Coordinate System

```
  Z (height, up)
  │
  │   Y (depth, into room)
  │  /
  │ /
  └───────── X (width, left to right)
```

| Axis  | Direction             | Typical range |
| ----- | --------------------- | ------------- |
| **X** | Width (left to right) | 300–3000 mm   |
| **Y** | Depth (into room)     | 300–600 mm    |
| **Z** | Height (up)           | 0–2500 mm     |

**Convention:** Z-up, right-hand rule. Documented once, enforced everywhere.
Wall normal points into room. Cabinet origin at back face (wall face).

### Coordinate Spaces

```
  World Coordinates          Wall-Local              Cabinet-Local
  ─────────────────          ──────────              ─────────────
  X: east +X                 dir: along wall         +X: width (left→right)
  Y: north +Y                normal: into room       +Y: depth (front→back)
  Z: up +Z                   origin: wall start      +Z: height (bottom→top)
                                                    origin: back-left-bottom
  Transforms:                Transform2D              wall.transform applied
  layout_engine applies      (2D rotation +           then wall-local offset
  wall positions             translation)
```

---

## Manifest Schema (v2.0)

```json
{
    "format": "kitchen-geometry-manifest",
    "version": "2.0",
    "units": "meters",
    "coordinate_system": {
        "type": "Z-up",
        "handedness": "right",
        "x": "width (left to right)",
        "y": "depth (into room)",
        "z": "height (up)"
    },
    "source_config": "configs/l_shape.json",
    "settings": {
        "baseBodyHeight": 720,
        "baseDepth": 560,
        "plinthHeight": 120,
        "wallMountHeight": 1400,
        "cabinetGap": 0,
        "frontGap": 2,
        "corpusThickness": 18,
        "frontThickness": 19,
        "backThickness": 3
    },
    "layout": {
        "type": "L-shape",
        "run_count": 2,
        "total_cabinets": 12,
        "runs": [
            {
                "label": "back wall",
                "index": 0,
                "direction": "east",
                "turn": null,
                "start_position_mm": [0, 0],
                "end_position_mm": [3550, 0],
                "total_width_mm": 3550,
                "cabinets": ["run0_base_0_filler", "run0_base_1_tall-oven", "..."]
            },
            {
                "label": "left wall",
                "index": 1,
                "direction": "south",
                "turn": "left",
                "start_position_mm": [3550, 0],
                "end_position_mm": [3550, -1850],
                "total_width_mm": 1850,
                "cabinets": ["run1_base_0_base-door", "..."]
            }
        ]
    },
    "objects": [
        {
            "name": "run0_base_1_tall-oven",
            "type": "carcass",
            "classification": "tall-oven",
            "level": "tall",
            "run_label": "back wall",
            "run_index": 0,
            "cabinet_index": 1,
            "parent": null,
            "transform": {
                "location_m": [0.65, 0.0, 0.0],
                "rotation_euler_rad": [0, 0, 0],
                "scale": [1, 1, 1]
            },
            "local_bounds": {
                "min_m": [0, 0, 0],
                "max_m": [0.6, 0.56, 2.0]
            },
            "local_dimensions_mm": [600, 560, 2000],
            "world_bounds": {
                "min_m": [0.65, 0.0, 0.0],
                "max_m": [1.25, 0.56, 2.0]
            },
            "world_dimensions_mm": [600, 560, 2000],
            "vertex_count": 16,
            "face_count": 12,
            "construction": {
                "corpus_thickness_mm": 18,
                "back_thickness_mm": 3,
                "front_thickness_mm": 19,
                "internal_width_mm": 564,
                "internal_depth_mm": 547,
                "internal_height_mm": 2000
            },
            "children": [
                {
                    "name": "run0_base_1_tall-oven_back",
                    "type": "back_panel",
                    "local_dimensions_mm": [564, 3, 1997]
                },
                {
                    "name": "run0_base_1_tall-oven_door",
                    "type": "door_front",
                    "local_dimensions_mm": [604, 19, 2004]
                }
            ],
            "validation": {
                "width_ok": true,
                "depth_ok": true,
                "height_ok": true,
                "vertex_count_ok": true,
                "face_count_ok": true,
                "issues": []
            }
        }
    ],
    "validation_summary": {
        "total_objects": 48,
        "passed": 46,
        "failed": 2,
        "warnings": 1,
        "issues": [
            {
                "severity": "error",
                "object": "run1_countertop",
                "check": "width",
                "message": "Countertop width 1790mm does not match expected 1850mm",
                "expected_mm": 1850,
                "actual_mm": 1790
            },
            {
                "severity": "error",
                "object": "run1_base_3_filler",
                "check": "position",
                "message": "Filler overlaps with run1_base_2_base-door",
                "overlap_mm": 18
            },
            {
                "severity": "warning",
                "object": "run0_base_0_filler",
                "check": "vertex_count",
                "message": "Filler has 4 vertices (expected 8 for solid box)"
            }
        ]
    }
}
```

### Schema Rules

1. **All lengths in meters** in the manifest. Display tools convert to mm.
2. **`local_dimensions_mm`** is the object's own size (no parent transform).
3. **`world_dimensions_mm`** is the size after all transforms are applied.
4. **`validation`** is per-object inline. No separate pass needed.
5. **`layout`** preserves the config's run structure for spatial reasoning.
6. **`construction`** exposes board thicknesses for manufacturing validation.

---

## Module Details

### Layer 1: Core (Pure Math)

```
  Vector2D          — 2D point/vector (x, y)
  Vector3D          — 3D point/vector (x, y, z)
  BoundingBox       — Axis-aligned bounding box (min, max)
  Transform2D       — 2D rigid transform (rotation + translation)
  Direction         — Enum: EAST, NORTH, WEST, SOUTH
  CabinetType       — Enum: base-door, wall-drawers, corner-blind, ...
  CabinetLevel      — Enum: BASE, UPPER, TALL
  Dimensions        — Named tuple: width, depth, height
```

**Files:**

- `src/core/geometry.py`
- `src/core/tolerances.py`
- `src/core/types.py`

**Rule:** No imports from `kitchen/`, `adapters/`, or `bpy`. Pure math only.

---

### Layer 2: Kitchen (Domain Logic)

```
  Wall              — Line segment with start/end, direction, normal
  Room              — Collection of walls
  CornerReference   — Links two walls at a corner
  Cabinet           — Parametric cabinet definition (type, width, wall_id)
  CabinetPlacement  — Cabinet + world position + rotation
  Countertop        — Countertop with overhangs
  Run               — Sequence of cabinets along one wall
  LayoutEngine      — Calculates positions from runs
  Layout            — Complete result: room + runs + corners + placements
```

**Files:**

- `src/kitchen/wall.py`
- `src/kitchen/cabinet.py`
- `src/kitchen/layout.py`
- `src/kitchen/standards.py`
- `src/kitchen/cabinet_geometry.py` — Board-level construction math

**Rule:** No imports from `adapters/` or `bpy`. Domain logic only.

---

### Layer 3: Builder (Config Parsing)

```
  config_parser     — Load JSON, apply defaults, return config dict
  validators        — Check semantic rules (dimension ranges, gaps, room fit)
  wall_builder      — Convert config dict → Wall + Cabinet objects
```

**Files:**

- `src/config_parser.py`
- `src/validators.py`
- `src/wall_builder.py`

**Rule:** No imports from `adapters/` or `bpy`. Config → domain objects only.

---

### Layer 4: Adapters (External)

```
  geometry_builder     — bpy mesh creation (carcasses, panels, fronts)
  material_manager     — Cycles materials
  exporters            — OBJ, glTF, .blend (optional visual exports)
  geometry_manifest    — JSON manifest export (PRIMARY output)
  manifest_validator   — Read manifest, run validation checks
```

**Files:**

- `src/geometry_builder.py`
- `src/material_manager.py`
- `src/exporters.py`
- `src/geometry_manifest.py` ← NEW
- `src/manifest_validator.py` ← NEW

**Rule:** Only layer allowed to import `bpy`. Manifest export reads bpy data
but outputs stdlib JSON (no bpy dependency in output format).

---

### Layer 5: Entry Points

```
  main.py           — CLI: parse args, orchestrate build + export
  tests/            — pytest suite
```

**CLI flags:**

```
  blender --background --python src/main.py -- configs/kitchen.json \
      --export-manifest          # Always recommended (primary output)
      --export-blend             # Visual inspection
      --export-obj               # Legacy interop
      --export-gltf              # Web/viewer interop
      --validate                 # Run manifest validation after export
      --no-materials             # Skip Cycles materials (faster)
      --render-wireframe         # PNG wireframe render
```

---

## Validation Architecture

### Three-Level Validation Pipeline

```
  Level 1: SYNTAX              Level 2: SEMANTIC           Level 3: GEOMETRIC
  ─────────────────            ──────────────────          ────────────────────
  config_parser.py             validators.py               geometry_manifest.py
  manifest_validator.py        manifest_validator.py       manifest_validator.py

  "Is this valid JSON          "Do cabinets overlap?"      "Are dimensions within
   with required fields?"      "Is clearance ≥ 900mm?"     2mm of expected?"
                                "Do widths match            "Is vertex count correct
                                 standard sizes?"           for construction type?"
```

### Validation Runs on the Manifest, Not on Exported Formats

```
  BEFORE (lossy, indirect):
    bpy → OBJ → parse OBJ → guess units → compare dims → report

  AFTER (direct, lossless):
    bpy → manifest JSON → read manifest → check dims → report
          (exact data)    (structured,    (inline validation)
                           self-documenting)
```

### Validation Checks

| Check                             | Level     | What it catches                      |
| --------------------------------- | --------- | ------------------------------------ |
| Dimension within tolerance        | Geometric | Cabinet built wrong size             |
| No object overlaps                | Semantic  | Cabinets placed on top of each other |
| Walkway clearance ≥ 900mm         | Semantic  | Kitchen not walkable                 |
| Standard widths only              | Semantic  | Non-standard cabinet width           |
| Vertex count matches construction | Geometric | Missing faces, degenerate mesh       |
| Face count correct                | Geometric | Open box, missing wall               |
| World bounds within room          | Geometric | Cabinet outside room boundary        |
| Countertop overhang correct       | Geometric | Wrong overhang amount                |
| Front overlay matches settings    | Geometric | Door too small/large                 |
| Run direction continuity          | Semantic  | Broken turn logic                    |

### Tolerances

```python
TOLERANCES = {
    "position_mm": 0.1,      # Placement accuracy
    "dimension_mm": 2.0,     # Size accuracy (board cut tolerance)
    "angle_rad": 0.01,       # Rotation accuracy
    "gap_mm": 2.0,           # Standard cabinet gap
    "overlap_mm": 0.0,       # Zero tolerance for overlaps
}
```

---

## European Kitchen Standards

| Standard      | Base Cabinet | Wall Cabinet | Tall Cabinet |
| ------------- | ------------ | ------------ | ------------ |
| Body height   | 720 mm       | 600 mm       | 2100–2400 mm |
| Plinth height | 120 mm       | —            | 120 mm       |
| Total height  | 840 mm       | —            | 2220–2520 mm |
| Depth         | 560 mm       | 300–350 mm   | 560–600 mm   |
| Mount height  | —            | 1400 mm AFF  | —            |

| Construction        | Value                   |
| ------------------- | ----------------------- |
| Corpus board        | 18 mm chipboard         |
| Front panel         | 19 mm MDF/chipboard     |
| Back panel          | 3 mm HDF in groove      |
| Groove offset       | 10 mm from rear         |
| Front overlay       | 2 mm per side           |
| Door gap            | 2 mm                    |
| Countertop overhang | 20 mm front, 30 mm ends |

| Standard widths | 300, 400, 450, 500, 600, 800, 900, 1000, 1200 mm |
| --------------- | ------------------------------------------------ |

---

## Test Architecture

```
                    ╱╲
                   ╱  ╲         Visual regression (few)
                  ╱────╲        .blend snapshots, render comparison
                 ╱      ╲
                ╱────────╲     Integration: Config → Mesh → Manifest → Validate
               ╱          ╲
              ╱────────────╲   Unit: Pure geometry math (many)
```

### Test Suites

| Suite                        | Tests | Requires bpy | What it covers                      |
| ---------------------------- | ----- | ------------ | ----------------------------------- |
| `test_core_geometry.py`      | 36    | No           | Vector, BoundingBox, Transform math |
| `test_kitchen.py`            | 22    | No           | Wall, Cabinet, Layout domain logic  |
| `test_wall_centric_model.py` | 21    | No           | Wall-local positioning              |
| `test_wall_builder.py`       | 15    | No           | Config → domain object conversion   |
| `test_config_parser.py`      | 11    | No           | JSON loading, defaults              |
| `test_positions.py`          | 6     | No           | World position calculation          |
| `test_l_shape.py`            | 11    | No           | L-layout correctness                |
| `test_u_shape.py`            | 11    | No           | U-layout correctness                |
| `test_p0_*.py`               | 37    | No           | Gap semantics, coordinate system    |
| `test_p1_*.py`               | 26    | No           | Construction geometry               |
| `test_p2_*.py`               | 39    | No           | Layout integration                  |
| `test_manifest_*.py`         | NEW   | No           | Manifest schema, validation         |
| `test_blender_*.py`          | NEW   | Yes          | bpy mesh creation (skipped in CI)   |

**Total: 218+ passing (no Blender required for most)**

### Manifest Round-Trip Test

```python
def test_manifest_round_trip():
    """Config → Build → Manifest → Validate → All checks pass."""
    config = load_config("configs/ref_i_shape.json")
    objects = build_kitchen(config)
    manifest = export_manifest(objects, settings=config["settings"])

    # Verify manifest structure
    assert manifest["version"] == "2.0"
    assert manifest["units"] == "meters"

    # Verify all objects present
    assert len(manifest["objects"]) > 0

    # Verify dimensions match expected
    for obj in manifest["objects"]:
        v = obj["validation"]
        assert v["width_ok"], f"{obj['name']}: width mismatch"
        assert v["depth_ok"], f"{obj['name']}: depth mismatch"
        assert v["height_ok"], f"{obj['name']}: height mismatch"

    # Verify no overlaps
    assert manifest["validation_summary"]["failed"] == 0
```

---

## File Structure

```
kitchen-plugin/
├── src/
│   ├── core/                        # Layer 1: Pure math
│   │   ├── __init__.py
│   │   ├── geometry.py             # Vector2D, Vector3D, BoundingBox, Transform2D
│   │   ├── tolerances.py           # Named tolerances
│   │   └── types.py                # Direction, CabinetType, CabinetLevel, Dimensions
│   │
│   ├── kitchen/                     # Layer 2: Domain logic
│   │   ├── __init__.py
│   │   ├── wall.py                 # Wall, Room, CornerReference
│   │   ├── cabinet.py              # Cabinet, CabinetPlacement, Countertop
│   │   ├── cabinet_geometry.py     # Board-level construction math
│   │   ├── layout.py               # Run, LayoutEngine, Layout
│   │   └── standards.py            # KitchenStandards, EUROPEAN_STANDARDS
│   │
│   ├── config_parser.py             # Layer 3: JSON loading, defaults
│   ├── validators.py                # Layer 3: Semantic validation
│   ├── wall_builder.py              # Layer 3: Config → domain objects
│   │
│   ├── geometry_builder.py          # Layer 4: Blender mesh creation
│   ├── material_manager.py          # Layer 4: Cycles materials
│   ├── exporters.py                 # Layer 4: OBJ, glTF, .blend (optional)
│   ├── geometry_manifest.py         # Layer 4: JSON manifest export (PRIMARY) ← NEW
│   ├── manifest_validator.py        # Layer 4: Manifest validation checks ← NEW
│   │
│   └── main.py                      # Layer 5: CLI entry point
│
├── scripts/
│   └── validate_manifest.py         # Standalone manifest validation (no bpy) ← NEW
│
├── tests/
│   ├── test_core_geometry.py
│   ├── test_kitchen.py
│   ├── test_wall_centric_model.py
│   ├── test_wall_builder.py
│   ├── test_config_parser.py
│   ├── test_positions.py
│   ├── test_l_shape.py
│   ├── test_u_shape.py
│   ├── test_p0_*.py
│   ├── test_p1_*.py
│   ├── test_p2_*.py
│   ├── test_manifest_schema.py      # ← NEW
│   ├── test_manifest_validation.py  # ← NEW
│   └── test_blender_geometry.py     # ← NEW (requires bpy)
│
├── configs/
│   ├── ref_i_shape.json
│   ├── ref_l_shape.json
│   └── ref_u_shape.json
│
├── output/
│   ├── meshes/                      # .obj, .gltf, .blend, _manifest.json
│   └── renders/
│
├── schemas/
│   └── manifest_v2.schema.json      # JSON Schema for manifest ← NEW
│
└── docs/
    ├── architecture.md              # This file
    ├── 3d-format-strategy.md        # Format comparison & rationale
    ├── config-syntax.md             # JSON config reference
    ├── wall-centric-model.md        # Positioning model
    ├── european-kitchen-standards.md
    ├── cad-principles-part1.md
    ├── cad-principles-part2.md
    └── implementation-plan.md       # Migration plan ← NEW
```

---

## Design Decisions

| Decision                         | Rationale                                                     |
| -------------------------------- | ------------------------------------------------------------- |
| **Manifest is primary output**   | Exact data from bpy, no lossy format conversion, LLM-readable |
| **OBJ/glTF are optional**        | For visual interop only, never for validation                 |
| **.blend for visual inspection** | Full fidelity, no format conversion, open in Blender          |
| **Validation on manifest**       | Structured, self-documenting, no unit guessing                |
| **Z-up coordinates**             | Architectural/BIM industry standard                           |
| **Wall-centric positioning**     | Same model as IKEA, professional kitchen CAD                  |
| **Frozen dataclasses**           | Immutable = thread-safe, no accidental mutation               |
| **Named tolerances**             | Self-documenting, configurable per check                      |
| **Units in meters internally**   | Blender's native unit; manifest declares explicitly           |
| **Expected dims in manifest**    | Self-validating — manifest tells you what's wrong             |

---

## Deprecated / Removed

The following scripts are replaced by the manifest pipeline:

| Old script                          | Replacement                       | Status |
| ----------------------------------- | --------------------------------- | ------ |
| `scripts/analyze_reference_obj.py`  | Manifest + `validate_manifest.py` | Remove |
| `scripts/convert_obj_to_gltf.py`    | Not needed (manifest is direct)   | Remove |
| `scripts/analyze_gltf_v2.py`        | Manifest + `validate_manifest.py` | Remove |
| `scripts/compare_with_reference.py` | Manifest validation (inline)      | Remove |
| `scripts/validate_obj.py`           | Manifest validation (inline)      | Remove |

These scripts existed to work around OBJ/glTF limitations (no units, no
hierarchy, no metadata). The manifest carries all that information natively.

---

## Future Work

| Priority   | Task                                              | Effort    |
| ---------- | ------------------------------------------------- | --------- |
| **High**   | Implement `geometry_manifest.py` (Layer 4)        | 2–3 days  |
| **High**   | Implement `manifest_validator.py`                 | 1–2 days  |
| **High**   | Add manifest schema (`manifest_v2.schema.json`)   | 1 day     |
| **High**   | Add `test_manifest_*.py` test suites              | 1–2 days  |
| **Medium** | Enhance manifest with `construction` metadata     | 1 day     |
| **Medium** | Add overlap detection to validator                | 1 day     |
| **Medium** | Standalone `validate_manifest.py` (no bpy needed) | 1 day     |
| **Low**    | Add 3MF export for manufacturing interop          | 2–3 days  |
| **Low**    | Add STEP export for B-Rep topology validation     | 1 week    |
| **Low**    | Blender-free 3D preview (three.js from manifest)  | 1–2 weeks |
