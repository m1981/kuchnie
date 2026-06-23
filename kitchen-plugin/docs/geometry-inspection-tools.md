# Geometry Inspection Tools

Practical workflow for generating and validating kitchen geometry.

For architecture details, manifest schema, and validation logic, see
[architecture.md](architecture.md).

---

## Generate Kitchen with Manifest

```bash
blender --background --python src/main.py -- configs/l_shape.json
```

This produces:

- `output/meshes/l_shape_manifest.json` — Primary manifest (always)
- No .blend unless you add `--export-blend`

## Validate Manifest (No Blender Required)

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

## Summarize Manifest (LLM-Friendly)

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

Validation: 22 passed, 2 failed, 1 warnings
```

## Optional Visual Export

Save a .blend file to open in Blender for visual inspection:

```bash
blender --background --python src/main.py -- configs/l_shape.json --export-blend
```

## Validate All Reference Kitchens

```bash
make validate
```

Or manually:

```bash
for manifest in output/meshes/ref_*_manifest.json; do
    python scripts/validate_manifest.py "$manifest"
done
```
