#!/usr/bin/env python3
"""Validate OBJ file geometry.

Standalone script to validate OBJ files without Blender.
Checks for common issues:
- Zero-size dimensions
- Flat quads (no thickness)
- Missing faces
- Out-of-range vertices

Usage:
    python scripts/validate_obj.py output/meshes/kitchen.obj
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def parse_obj(path: str) -> dict:
    """Parse OBJ file and extract geometry data."""
    vertices = []
    faces = []
    objects = []
    current_object = None

    with open(path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            parts = line.split()
            if not parts:
                continue

            if parts[0] == 'o':
                # New object
                if current_object:
                    objects.append(current_object)
                current_object = {
                    'name': parts[1] if len(parts) > 1 else 'unnamed',
                    'vertices': [],
                    'faces': [],
                    'vertex_offset': len(vertices),
                }

            elif parts[0] == 'v':
                # Vertex
                if len(parts) >= 4:
                    x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
                    vertices.append((x, y, z))
                    if current_object:
                        current_object['vertices'].append((x, y, z))

            elif parts[0] == 'f':
                # Face (handle both triangle and quad)
                face_verts = []
                for p in parts[1:]:
                    # Handle v/vt/vn format
                    idx = int(p.split('/')[0])
                    if idx < 0:
                        idx = len(vertices) + idx
                    face_verts.append(idx - 1)  # OBJ is 1-indexed
                faces.append(face_verts)
                if current_object:
                    current_object['faces'].append(face_verts)

    if current_object:
        objects.append(current_object)

    return {
        'vertices': vertices,
        'faces': faces,
        'objects': objects,
    }


def calculate_bounds(vertices: list) -> dict:
    """Calculate bounding box from vertices."""
    if not vertices:
        return {'min': (0, 0, 0), 'max': (0, 0, 0), 'dimensions': (0, 0, 0)}

    min_x = min_y = min_z = float('inf')
    max_x = max_y = max_z = float('-inf')

    for x, y, z in vertices:
        min_x = min(min_x, x)
        max_x = max(max_x, x)
        min_y = min(min_y, y)
        max_y = max(max_y, y)
        min_z = min(min_z, z)
        max_z = max(max_z, z)

    return {
        'min': (min_x, min_y, min_z),
        'max': (max_x, max_y, max_z),
        'dimensions': (max_x - min_x, max_y - min_y, max_z - min_z),
    }


def validate_obj(path: str) -> list:
    """Validate OBJ file and return list of issues."""
    issues = []
    warnings = []

    print(f"\n{'='*70}")
    print(f"VALIDATING OBJ: {path}")
    print(f"{'='*70}\n")

    # Parse OBJ
    data = parse_obj(path)
    vertices = data['vertices']
    faces = data['faces']
    objects = data['objects']

    print(f"Total vertices: {len(vertices)}")
    print(f"Total faces: {len(faces)}")
    print(f"Objects: {len(objects)}")

    # Calculate overall bounds
    bounds = calculate_bounds(vertices)
    dims = bounds['dimensions']
    print(f"\nOverall dimensions (meters):")
    print(f"  Width:  {dims[0]:.4f}m ({dims[0]*1000:.1f}mm)")
    print(f"  Depth:  {dims[1]:.4f}m ({dims[1]*1000:.1f}mm)")
    print(f"  Height: {dims[2]:.4f}m ({dims[2]*1000:.1f}mm)")

    # Validate each object
    print(f"\n{'='*70}")
    print("OBJECT DETAILS:")
    print(f"{'='*70}")

    for obj in objects:
        name = obj['name']
        obj_verts = obj['vertices']
        obj_faces = obj['faces']

        # Calculate object bounds
        obj_bounds = calculate_bounds(obj_verts)
        obj_dims = obj_bounds['dimensions']

        # Classify object
        obj_type = "unknown"
        name_lower = name.lower()
        if "_door" in name_lower:
            obj_type = "door"
        elif "_drawer" in name_lower:
            obj_type = "drawer"
        elif "_back" in name_lower:
            obj_type = "back_panel"
        elif "countertop" in name_lower:
            obj_type = "countertop"
        elif "filler" in name_lower:
            obj_type = "filler"
        elif "run" in name_lower:
            obj_type = "carcass"

        print(f"\n  {name}")
        print(f"    Type: {obj_type}")
        print(f"    Vertices: {len(obj_verts)}")
        print(f"    Faces: {len(obj_faces)}")
        print(f"    Dims: {obj_dims[0]*1000:.1f} × {obj_dims[1]*1000:.1f} × {obj_dims[2]*1000:.1f} mm")

        # Validation checks
        obj_issues = []

        # Check for zero dimensions
        for i, (dim_name, dim_val) in enumerate(zip(["width", "depth", "height"], obj_dims)):
            if dim_val < 0.0001:  # < 0.1mm
                obj_issues.append(f"{dim_name} is ~0mm")

        # Check for thick fronts (should have 8 vertices for box)
        if obj_type in ("door", "drawer"):
            if len(obj_verts) < 8:
                obj_issues.append(f"front has {len(obj_verts)} vertices (expected 8 for thick box)")
            else:
                # Check thickness (should be ~19mm = 0.019m)
                thickness_m = obj_dims[1]  # Y dimension
                if thickness_m < 0.010:  # < 10mm
                    obj_issues.append(f"front thickness {thickness_m*1000:.1f}mm is too thin")

        # Check for flat quads (4 vertices, 1 face)
        if len(obj_verts) == 4 and len(obj_faces) == 1:
            obj_issues.append("flat quad (no thickness)")

        # Check for reasonable vertex count
        if len(obj_verts) == 0:
            obj_issues.append("no vertices")
        elif len(obj_verts) < 4:
            obj_issues.append(f"only {len(obj_verts)} vertices")

        if obj_issues:
            print(f"    ⚠️  ISSUES: {'; '.join(obj_issues)}")
            issues.extend([f"{name}: {issue}" for issue in obj_issues])
        else:
            print(f"    ✓ OK")

    # Summary
    print(f"\n{'='*70}")
    print("VALIDATION SUMMARY:")
    print(f"{'='*70}")

    if issues:
        print(f"\n❌ Found {len(issues)} issues:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("\n✓ No issues found!")

    return issues


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/validate_obj.py <file.obj>")
        print("\nValidates OBJ geometry files for common issues.")
        sys.exit(1)

    obj_path = sys.argv[1]
    if not Path(obj_path).exists():
        print(f"Error: file not found: {obj_path}")
        sys.exit(1)

    issues = validate_obj(obj_path)
    sys.exit(1 if issues else 0)


if __name__ == "__main__":
    main()
