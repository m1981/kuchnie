# Geometry Inspection Tools

Tools for analyzing and validating 3D cabinet geometry in OBJ and glTF formats.

## Coordinate System

Our system uses **Z-up** coordinates:

```
Z (height)
│
│   Y (depth, into room)
│  /
│ /
└───────── X (width, left to right)
```

| Axis | Direction | Typical Range |
|------|-----------|---------------|
| **X** | Width (left to right) | 300-1200mm |
| **Y** | Depth (into room) | 300-600mm |
| **Z** | Height (up) | 0-2000mm |

### glTF Coordinate System

glTF uses **Y-up** coordinates. Our tools automatically convert:

| Our (Z-up) | glTF (Y-up) |
|------------|-------------|
| X | X |
| Y | -Z |
| Z | Y |

---

## Tools Overview

| Tool | Purpose | Input | Output |
|------|---------|-------|--------|
| `analyze_reference_obj.py` | Analyze OBJ files | `.obj` | Console report |
| `convert_obj_to_gltf.py` | Convert OBJ to glTF | `.obj` | `.gltf` |
| `analyze_gltf_v2.py` | Analyze glTF with Z-up conversion | `.gltf` | Console report |
| `compare_with_reference.py` | Compare against reference dimensions | `.json` + `.gltf` | Comparison report |

---

## Tool 1: analyze_reference_obj.py

Analyzes OBJ files and provides detailed geometry information.

### Usage

```bash
python3 scripts/analyze_reference_obj.py output/meshes/myster-box.obj
```

### Output

```
================================================================================
REFERENCE OBJECT ANALYSIS
================================================================================

File: output/meshes/myster-box.obj
Total vertices: 2152
Total faces: 2080
Objects: 4

Coordinate System Detection:
  System: Z-up
  Confidence: 80%

Overall Bounds:
  X: -600.0 to 0.0 mm (600.0mm)
  Y: 0.0 to 638.6 mm (638.6mm)
  Z: 0.0 to 860.0 mm (860.0mm)

OBJECT DETAILS
================================================================================

Cabinet1:
  Vertices: 24
  Faces: 20
  Dimensions:
    Width:  600.0 mm
    Depth:  590.0 mm
    Height: 700.0 mm
```

### What It Shows

- **Coordinate System Detection**: Automatically detects if model uses Y-up or Z-up
- **Object Details**: Name, vertex count, face count
- **Dimensions**: Width × Depth × Height in mm
- **Bounds**: Min/max coordinates for each axis
- **Visualization**: ASCII top-view of objects

---

## Tool 2: convert_obj_to_gltf.py

Converts OBJ files to glTF 2.0 format for analysis.

### Usage

```bash
python3 scripts/convert_obj_to_gltf.py output/meshes/myster-box.obj
```

### Output

- Creates `.gltf` file in same directory
- Shows conversion summary with mesh names and bounds

### When to Use

- When you have an OBJ file and want to analyze it with `analyze_gltf_v2.py`
- When you need to inspect vertex-by-vertex coordinates

---

## Tool 3: analyze_gltf_v2.py

Analyzes glTF files with automatic Y-up to Z-up coordinate conversion.

### Usage

```bash
python3 scripts/analyze_gltf_v2.py output/meshes/single_cabinet_test.gltf
```

### Output

```
==========================================================================================
GLTF GEOMETRY ANALYSIS (Z-up coordinates)
==========================================================================================

──────────────────────────────────────────────────────────────────────────────────────────
  cabinet_corpus
    World Position: (0.0, 0.0, 120.0) mm
    Mesh: 16 vertices, 24 faces
    Local Dims: 600.0 × 560.0 × 720.0 mm
    Vertices (local):
      [ 0] (    0.00,    -0.00,     0.00) mm
      [ 1] (  600.00,    -0.00,     0.00) mm
      ...
    World Bounds:
      X: 0.0 to 600.0 mm
      Y: 0.0 to 560.0 mm
      Z: 120.0 to 840.0 mm

==========================================================================================
VALIDATION
==========================================================================================

✓ No issues found
```

### What It Shows

- **World Position**: Object position in Z-up coordinates
- **Local Dims**: Object dimensions (width × depth × height)
- **Vertices**: All vertex coordinates (converted to Z-up)
- **World Bounds**: Min/max coordinates in world space
- **Validation**: Checks for geometry issues

### Key Features

- Automatic Y-up → Z-up conversion
- Shows vertex-by-vertex coordinates
- Validates geometry for common issues

---

## Tool 4: compare_with_reference.py

Compares generated cabinet geometry against reference dimensions.

### Usage

```bash
# First generate the glTF file
/Applications/Blender.app/Contents/MacOS/Blender --background --python src/main.py -- configs/single_cabinet_test.json --export-gltf --no-materials

# Then compare
python3 scripts/compare_with_reference.py configs/single_cabinet_test.json
```

### Output

```
================================================================================
COMPARISON: Generated vs Expected
================================================================================

Summary: 4 OK, 0 Mismatch, 0 Missing

✓ run0_base_0_base-door
    Carcass (18mm walls)
    Dims: 600.0 × 560.0 × 720.0 mm

✓ run0_base_0_base-door_back
    Back panel (3mm HDF)
    Dims: 564.0 × 3.0 × 717.0 mm

✓ run0_base_0_base-door_door
    Door with 2mm overlay
    Dims: 604.0 × 19.0 × 724.0 mm

✓ countertop
    Countertop with overhangs
    Dims: 660.0 × 580.0 × 30.0 mm

================================================================================
REFERENCE OBJECT ANALYSIS
================================================================================

Reference: myster-box.obj
Coordinate System: Z-up

Reference Dimensions:
  Cabinet1: 600 × 590 × 700 mm
  Cabinet1_Door: 599 × 18 × 698 mm

================================================================================
CABINET COMPARISON
================================================================================

Reference Cabinet1: 600 × 590 × 700 mm
Our Corpus:         600 × 560 × 720 mm

Differences:
  Width:  0.0mm ✓
  Depth:  30.0mm ❌
  Height: 20.0mm ❌
```

### What It Shows

- **Generated vs Expected**: Compares each component against expected dimensions
- **Reference Analysis**: Shows reference object dimensions
- **Cabinet Comparison**: Highlights differences between our cabinet and reference

---

## Reference Object: myster-box.obj

The reference object (`output/meshes/myster-box.obj`) serves as ground truth.

### Components

| Component | Width | Depth | Height | Description |
|-----------|-------|-------|--------|-------------|
| Cabinet1 | 600mm | 590mm | 700mm | Main cabinet body |
| Cabinet1_Door | 599mm | 18mm | 698mm | Door panel |
| Handle | 8mm | 30mm | 144mm | Handle |
| Baseboard1 | 600mm | 18mm | 160mm | Base panel |

### Key Measurements

- **Door gap**: 1mm (door at Y=591-609, cabinet at Y=0-590)
- **Door thickness**: 18mm
- **Baseboard**: 160mm tall, 18mm thick

---

## Typical Workflow

### 1. Generate Cabinet Geometry

```bash
/Applications/Blender.app/Contents/MacOS/Blender --background --python src/main.py -- configs/single_cabinet_test.json --export-gltf --export-obj --no-materials
```

### 2. Analyze Generated Geometry

```bash
python3 scripts/analyze_gltf_v2.py output/meshes/single_cabinet_test.gltf
```

### 3. Compare with Reference

```bash
python3 scripts/compare_with_reference.py configs/single_cabinet_test.json
```

### 4. Inspect Reference Object

```bash
python3 scripts/analyze_reference_obj.py output/meshes/myster-box.obj
```

---

## Expected Dimensions

### Our Cabinet (European Standard)

| Component | Width | Depth | Height | Notes |
|-----------|-------|-------|--------|-------|
| Carcass | 600mm | 560mm | 720mm | 18mm walls |
| Back Panel | 564mm | 3mm | 717mm | Internal width, HDF |
| Door | 604mm | 19mm | 724mm | 2mm overlay |
| Countertop | 660mm | 580mm | 30mm | 30mm overhang ends |

### Reference Cabinet (myster-box.obj)

| Component | Width | Depth | Height | Notes |
|-----------|-------|-------|--------|-------|
| Cabinet1 | 600mm | 590mm | 700mm | Different depth/height |
| Door | 599mm | 18mm | 698mm | Slightly smaller |
| Baseboard | 600mm | 18mm | 160mm | Base panel |

---

## Troubleshooting

### "Object not found" in comparison

The object names in glTF depend on the config file. Check actual names with:

```bash
python3 -c "import json; gltf = json.load(open('output/meshes/file.gltf')); print([n['name'] for n in gltf['nodes']])"
```

### Wrong coordinate system detected

The coordinate system detection uses heuristics. If wrong, you can manually specify:

```python
# In your analysis script
analysis = analyze_gltf(path, force_z_up=True)
```

### Dimensions don't match

Check if you're comparing against the correct reference:
- **European standard**: 600×560×720mm
- **Reference object**: 600×590×700mm

---

## File Locations

All tools are in: `/Users/michal/PycharmProjects/kuchnie/kitchen-plugin/scripts/`

Generated files are in: `/Users/michal/PycharmProjects/kuchnie/kitchen-plugin/output/meshes/`
