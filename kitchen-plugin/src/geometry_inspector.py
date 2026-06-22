"""Geometry Inspector — Export detailed geometry for validation.

Exports each object with:
- Local vertex coordinates (not world-transformed)
- Face definitions with vertex indices
- Object transform (position, rotation)
- Parent-child hierarchy
- Construction metadata

Output: JSON that can be analyzed to verify exact board positions.
"""

import json
from pathlib import Path
from typing import Any


def export_geometry_inspection(objects: list, path: str,
                                settings: dict | None = None) -> dict:
    """Export detailed geometry inspection.

    Args:
        objects: List of bpy.types.Object
        path: Output JSON file path
        settings: Optional settings dict

    Returns:
        Inspection dict with full geometry details
    """
    inspection = {
        "format": "kitchen-geometry-inspection",
        "version": "1.0",
        "units": "meters",
        "coordinate_system": {
            "x": "width (left to right)",
            "y": "depth (front to back, into room)",
            "z": "height (bottom to top)",
            "origin": "front-left-bottom corner of carcass"
        },
        "settings": settings or {},
        "objects": [],
        "hierarchy": [],
    }

    # Build object map for hierarchy
    obj_map = {}

    for obj in objects:
        obj_data = _extract_detailed_object(obj)
        if obj_data:
            inspection["objects"].append(obj_data)
            obj_map[obj.name] = obj_data

    # Build hierarchy
    for obj_data in inspection["objects"]:
        parent_name = obj_data.get("parent")
        if parent_name:
            inspection["hierarchy"].append({
                "parent": parent_name,
                "child": obj_data["name"],
                "relationship": "child"
            })

    # Write to file
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, 'w') as f:
        json.dump(inspection, f, indent=2)

    print(f"Geometry inspection: {out}")
    print(f"  Objects: {len(inspection['objects'])}")

    return inspection


def _extract_detailed_object(obj) -> dict | None:
    """Extract detailed geometry data from a Blender object."""
    try:
        name = obj.name

        # Get mesh data
        mesh = obj.data

        # Local vertices (NOT world-transformed)
        local_vertices = []
        if hasattr(mesh, 'vertices'):
            for v in mesh.vertices:
                local_vertices.append([
                    round(v.co.x, 6),
                    round(v.co.y, 6),
                    round(v.co.z, 6)
                ])

        # Faces
        faces = []
        if hasattr(mesh, 'polygons'):
            for p in mesh.polygons:
                faces.append(list(p.vertices))

        # Calculate local bounds
        if local_vertices:
            xs = [v[0] for v in local_vertices]
            ys = [v[1] for v in local_vertices]
            zs = [v[2] for v in local_vertices]
            bounds = {
                "min": [round(min(xs), 6), round(min(ys), 6), round(min(zs), 6)],
                "max": [round(max(xs), 6), round(max(ys), 6), round(max(zs), 6)]
            }
            dimensions = [
                round(max(xs) - min(xs), 6),
                round(max(ys) - min(ys), 6),
                round(max(zs) - min(zs), 6)
            ]
        else:
            bounds = {"min": [0, 0, 0], "max": [0, 0, 0]}
            dimensions = [0, 0, 0]

        # Get parent name
        parent_name = obj.parent.name if obj.parent else None

        # Classify object
        obj_type = _classify_object(name)

        return {
            "name": name,
            "type": obj_type,
            "parent": parent_name,
            "transform": {
                "location": _vec_to_list(obj.location),
                "rotation": _vec_to_list(obj.rotation_euler),
                "scale": _vec_to_list(obj.scale),
            },
            "vertex_count": len(local_vertices),
            "face_count": len(faces),
            "local_bounds": bounds,
            "local_dimensions_m": dimensions,
            "local_dimensions_mm": [round(d * 1000, 2) for d in dimensions],
            "vertices": local_vertices,
            "faces": faces,
        }
    except Exception as e:
        return {
            "name": getattr(obj, 'name', 'unknown'),
            "error": str(e),
        }


def _classify_object(name: str) -> str:
    """Classify object type from name."""
    name_lower = name.lower()
    if "_door" in name_lower:
        return "door_front"
    elif "_drawer" in name_lower:
        return "drawer_front"
    elif "_back" in name_lower:
        return "back_panel"
    elif "carcass" in name_lower or "run" in name_lower:
        return "carcass"
    elif "countertop" in name_lower:
        return "countertop"
    elif "filler" in name_lower:
        return "filler"
    elif "plinth" in name_lower:
        return "plinth"
    else:
        return "other"


def _vec_to_list(vec) -> list:
    """Convert Blender vector to list."""
    return [round(vec.x, 6), round(vec.y, 6), round(vec.z, 6)]


def print_inspection_summary(inspection: dict) -> None:
    """Print human-readable summary of inspection."""
    print("\n" + "=" * 80)
    print("GEOMETRY INSPECTION SUMMARY")
    print("=" * 80)

    print(f"\nCoordinate System:")
    print(f"  X: {inspection['coordinate_system']['x']}")
    print(f"  Y: {inspection['coordinate_system']['y']}")
    print(f"  Z: {inspection['coordinate_system']['z']}")
    print(f"  Origin: {inspection['coordinate_system']['origin']}")

    print(f"\nObjects: {len(inspection['objects'])}")

    for obj in inspection['objects']:
        name = obj['name']
        obj_type = obj.get('type', 'unknown')
        dims = obj.get('local_dimensions_mm', [0, 0, 0])
        verts = obj.get('vertex_count', 0)
        faces = obj.get('face_count', 0)
        parent = obj.get('parent')
        transform = obj.get('transform', {}).get('location', [0, 0, 0])

        print(f"\n{'─' * 80}")
        print(f"  {name}")
        print(f"  Type: {obj_type}")
        print(f"  Parent: {parent or 'none (root)'}")
        print(f"  Dims: {dims[0]:.1f} × {dims[1]:.1f} × {dims[2]:.1f} mm")
        print(f"  Mesh: {verts} vertices, {faces} faces")
        print(f"  Position: ({transform[0]:.4f}, {transform[1]:.4f}, {transform[2]:.4f}) m")

        # Print vertex coordinates (first few and last few)
        vertices = obj.get('vertices', [])
        if vertices:
            print(f"  Vertices (local coords):")
            for i, v in enumerate(vertices[:4]):
                print(f"    [{i}] ({v[0]:.4f}, {v[1]:.4f}, {v[2]:.4f}) m = ({v[0]*1000:.1f}, {v[1]*1000:.1f}, {v[2]*1000:.1f}) mm")
            if len(vertices) > 8:
                print(f"    ... ({len(vertices) - 8} more)")
            for i, v in enumerate(vertices[-4:], len(vertices) - 4):
                print(f"    [{i}] ({v[0]:.4f}, {v[1]:.4f}, {v[2]:.4f}) m = ({v[0]*1000:.1f}, {v[1]*1000:.1f}, {v[2]*1000:.1f}) mm")

    print(f"\n{'=' * 80}")


def analyze_geometry(inspection: dict) -> list:
    """Analyze geometry for common issues.

    Returns list of issues found.
    """
    issues = []

    for obj in inspection['objects']:
        name = obj['name']
        obj_type = obj.get('type', 'unknown')
        dims = obj.get('local_dimensions_mm', [0, 0, 0])
        verts = obj.get('vertices', [])
        faces = obj.get('faces', [])

        # Check for zero dimensions
        for i, (dim_name, dim_val) in enumerate(zip(["width", "depth", "height"], dims)):
            if dim_val < 0.1:
                issues.append(f"{name}: {dim_name} is ~0mm")

        # Check for thick fronts (should have 8 vertices)
        if obj_type in ("door_front", "drawer_front"):
            if len(verts) < 8:
                issues.append(f"{name}: front has {len(verts)} vertices (expected 8 for box)")

            # Check thickness (should be ~19mm)
            if dims[1] < 10:  # Y dimension
                issues.append(f"{name}: front thickness {dims[1]:.1f}mm is too thin")

        # Check carcass has inner cavity
        if obj_type == "carcass":
            if len(verts) < 16:
                issues.append(f"{name}: carcass has {len(verts)} vertices (expected 16 for hollow box)")

        # Check back panel is thin
        if obj_type == "back_panel":
            if dims[1] > 10:  # Should be ~3mm
                issues.append(f"{name}: back panel thickness {dims[1]:.1f}mm is too thick")

    return issues
