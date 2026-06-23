# Geometry Inspection Tools

Tools for analyzing and validating 3D cabinet geometry.

## Primary Output: JSON Manifest

The primary output of every build is a **structured JSON manifest** that contains:

- All vertex coordinates (local + world)
- Object hierarchy (parent-child)
- Expected vs actual dimensions (inline validation)
- Layout metadata (runs, turns, directions)
- Construction parameters (board thicknesses)
- Units and coordinate system (explicit)

**The manifest is the single source of truth for validation.** .blend is an optional visual export.

---

## Workflow

### 1. Generate Kitchen with Manifest

```bash
blender --background --python src/main.py -- configs/l_shape.json --validate
```

This produces:

- `output/meshes/l_shape_manifest.json` — Primary manifest (always)
- `output/meshes/l_shape.blend` — Visual inspection (if `--export-blend`)

### 2. Validate Manifest (No Blender Required)

```bash
python scripts/validate_manifest.py output/meshes/l_shape_manifest.json
```

Output:

```
MANIFEST VALIDATION REPORT
================================================================================

Total objects: 48
Passed: 46
Failed: 2
Warnings: 1
Status: ❌ INVALID

❌ Errors (2):
  [width] run1_countertop: width mismatch: expected 1850.0mm, got 1790.0mm (diff: 60.0mm)
  [overlap] run1_base_3_filler: Overlaps with run1_base_2_base-door: X=18.0mm

⚠️  Warnings (1):
  [vertex_count] run0_base_0_filler: Filler has 4 vertices (expected 8 for solid box)
================================================================================
```

### 3. Summarize Manifest (LLM-Friendly)

```bash
python scripts/summarize_manifest.py output/meshes/l_shape_manifest.json
```

Output:

```
Kitchen: L-shape
Layout: 2 runs, 12 cabinets

Runs:
  0. back wall: east — 3550mm, 6 cabinets
  1. left wall: south (turn: left) — 1850mm, 6 cabinets

Objects: 48 total (24 primary, 24 children)

By type:
  back_panel: 12
  carcass: 24
  door_front: 8
  drawer_front: 4

Primary objects:
  Name                                     W×D×H (mm)             Status
  ──────────────────────────────────────── ─────────────────────── ──────────
  run0_base_0_filler                       50×560×720              ⚠️
  run0_base_1_tall-oven                    600×560×2000            ✓
  ...

Validation: 22 passed, 2 failed, 1 warnings
```

---

## Manifest Schema

The manifest follows the schema defined in `schemas/manifest_v2.schema.json`.

### Key Fields

| Field                | Type   | Description                          |
| -------------------- | ------ | ------------------------------------ |
| `format`             | string | Always `"kitchen-geometry-manifest"` |
| `version`            | string | Always `"2.0"`                       |
| `units`              | string | Always `"meters"`                    |
| `coordinate_system`  | object | Z-up, right-hand                     |
| `settings`           | object | Kitchen settings (mm values)         |
| `layout`             | object | Run metadata, directions, turns      |
| `objects`            | array  | All geometry objects                 |
| `validation_summary` | object | Pass/fail counts and issues          |

### Object Fields

| Field                  | Type        | Description                                  |
| ---------------------- | ----------- | -------------------------------------------- |
| `name`                 | string      | Unique object name                           |
| `classification`       | string      | carcass, board, door_front, back_panel, etc. |
| `level`                | string      | base, upper, tall                            |
| `parent`               | string/null | Parent object name                           |
| `transform.location_m` | [x,y,z]     | Position in meters                           |
| `local_dimensions_mm`  | [w,d,h]     | Object dimensions in mm                      |
| `world_bounds`         | object      | World-space bounding box                     |
| `vertex_count`         | int         | Number of vertices                           |
| `face_count`           | int         | Number of faces                              |
| `validation`           | object      | Inline pass/fail checks                      |

---

## Validation Checks

The manifest validator checks:

| Check                  | Severity | Description                                   |
| ---------------------- | -------- | --------------------------------------------- |
| **Dimension mismatch** | error    | Actual ≠ expected (within 2mm tolerance)      |
| **Object overlap**     | error    | World bounds intersect (min dimension ≥ 50mm) |
| **Zero dimensions**    | error    | Width/depth/height is ~0mm                    |
| **Vertex count**       | warning  | Board < 8 vertices, front < 8 vertices        |
| **Face count**         | warning  | Board < 6 faces, front < 6 faces              |
| **Standard widths**    | warning  | Not a European standard width                 |
| **Run continuity**     | error    | End of one run ≠ start of next                |
| **Direction mismatch** | error    | Turn doesn't produce expected direction       |
| **Back thickness**     | warning  | Back panel too thick                          |
| **Front thickness**    | warning  | Front panel too thin                          |

**Overlap detection:**

- Filters out expected small overlaps (door overlays, 2-4mm)
- Only reports overlaps where minimum dimension ≥ 50mm
- Skips boards, fronts, backs, and countertops in overlap checks

---

## Comparison: Old vs New Pipeline

### Old Pipeline (Deprecated)

```
config → Blender → OBJ/glTF → parse scripts → guess units → compare → report
                      ↑
               6 lossy steps before validation
```

Problems:

- OBJ has no units (hardcoded `*1000`)
- Coordinate system detection is fragile guesswork
- Multi-object index remapping bug
- glTF Y-up → Z-up conversion failure point
- Can't trace back to which build step broke

### New Pipeline (Current)

```
config → Blender → JSON manifest → validator → report
                   (exact data)    (structured)
```

Benefits:

- Units explicit: `"units": "meters"`
- Coordinate system documented once
- Local + world coordinates, exact transforms
- Expected-vs-actual validation inline
- Layout metadata preserved
- LLM agent reads plain JSON
- Validation at the source, not after export

---

## Deprecated Scripts (Removed)

The following scripts were removed as part of the manifest-first migration:

| Script                      | Replaced By                     |
| --------------------------- | ------------------------------- |
| `analyze_reference_obj.py`  | `scripts/validate_manifest.py`  |
| `convert_obj_to_gltf.py`    | Not needed (manifest is direct) |
| `analyze_gltf_v2.py`        | `scripts/validate_manifest.py`  |
| `compare_with_reference.py` | Inline validation in manifest   |
| `validate_obj.py`           | `scripts/validate_manifest.py`  |
| `src/geometry_inspector.py` | `src/geometry_manifest.py`      |
| `src/geometry_validator.py` | `src/manifest_validator.py`     |

---

## Optional Visual Export

For visual inspection, you can save a .blend file:

```bash
# Blender file (full fidelity)
blender --background --python src/main.py -- configs/l_shape.json --export-blend
```

**Note:** OBJ and glTF exports were removed. The manifest replaced them for all
validation and inspection purposes. .blend is for opening in Blender only.
