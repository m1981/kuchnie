"""Geometry Validator — Inspect and validate generated cabinet geometry.

Exports detailed JSON manifest for offline validation without Blender.
This allows checking dimensions, positions, and construction details
before importing into Blender or other 3D tools.

Output format: JSON with full geometry details for each object.
"""

import json
from pathlib import Path
from typing import Any


def validate_and_export_manifest(objects: list, path: str,
                                 settings: dict | None = None) -> dict:
    """Export detailed geometry manifest for validation.

    Args:
        objects: List of bpy.types.Object (or mock objects for testing)
        path: Output JSON file path
        settings: Optional settings dict to include in manifest

    Returns:
        Manifest dict with all geometry details
    """
    manifest = {
        "format": "kitchen-geometry-manifest",
        "version": "1.0",
        "units": "meters",
        "settings": settings or {},
        "summary": {
            "total_objects": 0,
            "total_vertices": 0,
            "total_faces": 0,
            "objects_by_type": {},
        },
        "objects": [],
        "validation": {
            "warnings": [],
            "errors": [],
        },
    }

    for obj in objects:
        obj_data = _extract_object_data(obj)
        if obj_data:
            manifest["objects"].append(obj_data)
            manifest["summary"]["total_objects"] += 1
            manifest["summary"]["total_vertices"] += obj_data["vertex_count"]
            manifest["summary"]["total_faces"] += obj_data["face_count"]

            # Count by type
            obj_type = obj_data.get("type", "unknown")
            manifest["summary"]["objects_by_type"][obj_type] = \
                manifest["summary"]["objects_by_type"].get(obj_type, 0) + 1

    # Run validation checks
    _validate_manifest(manifest)

    # Write to file
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, 'w') as f:
        json.dump(manifest, f, indent=2)

    print(f"Geometry manifest: {out}")
    print(f"  Objects: {manifest['summary']['total_objects']}")
    print(f"  Vertices: {manifest['summary']['total_vertices']}")
    print(f"  Faces: {manifest['summary']['total_faces']}")

    if manifest["validation"]["warnings"]:
        print(f"  Warnings: {len(manifest['validation']['warnings'])}")
    if manifest["validation"]["errors"]:
        print(f"  ERRORS: {len(manifest['validation']['errors'])}")

    return manifest


def _extract_object_data(obj) -> dict | None:
    """Extract detailed data from a Blender object."""
    try:
        name = obj.name
        location = _vec_to_list(obj.location)
        rotation = _vec_to_list(obj.rotation_euler)
        scale = _vec_to_list(obj.scale)

        # Get mesh data
        mesh = obj.data
        vertices = []
        faces = []
        bounds = {"min": [float('inf')] * 3, "max": [float('-inf')] * 3}

        if hasattr(mesh, 'vertices'):
            for v in mesh.vertices:
                # World position
                world_v = obj.matrix_world @ v.co
                vx, vy, vz = world_v.x, world_v.y, world_v.z
                vertices.append([vx, vy, vz])

                # Update bounds
                for i in range(3):
                    bounds["min"][i] = min(bounds["min"][i], [vx, vy, vz][i])
                    bounds["max"][i] = max(bounds["max"][i], [vx, vy, vz][i])

        if hasattr(mesh, 'polygons'):
            for p in mesh.polygons:
                faces.append(list(p.vertices))

        # Calculate dimensions from bounds
        dimensions = [
            bounds["max"][0] - bounds["min"][0],
            bounds["max"][1] - bounds["min"][1],
            bounds["max"][2] - bounds["min"][2],
        ]

        # Classify object type
        obj_type = _classify_object(name)

        return {
            "name": name,
            "type": obj_type,
            "location": location,
            "rotation": rotation,
            "scale": scale,
            "vertex_count": len(vertices),
            "face_count": len(faces),
            "bounds": bounds,
            "dimensions_m": dimensions,
            "dimensions_mm": [d * 1000 for d in dimensions],
            "vertices": vertices,
            "faces": faces,
        }
    except Exception as e:
        return {
            "name": getattr(obj, 'name', 'unknown'),
            "error": str(e),
            "vertex_count": 0,
            "face_count": 0,
        }


def _classify_object(name: str) -> str:
    """Classify object type from name."""
    name_lower = name.lower()
    if "_door" in name_lower:
        return "door"
    elif "_drawer" in name_lower:
        return "drawer"
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


def _validate_manifest(manifest: dict) -> None:
    """Run validation checks on manifest."""
    warnings = manifest["validation"]["warnings"]
    errors = manifest["validation"]["errors"]

    for obj in manifest["objects"]:
        name = obj.get("name", "unknown")

        # Check for zero-size dimensions
        dims = obj.get("dimensions_mm", [0, 0, 0])
        for i, (dim_name, dim_val) in enumerate(zip(["width", "depth", "height"], dims)):
            if dim_val < 0.001:
                warnings.append(f"{name}: {dim_name} is ~0mm")

        # Check vertex count
        if obj.get("vertex_count", 0) == 0:
            errors.append(f"{name}: has no vertices")
        elif obj.get("vertex_count", 0) < 4:
            warnings.append(f"{name}: only {obj['vertex_count']} vertices (flat quad?)")

        # Check face count
        if obj.get("face_count", 0) == 0:
            errors.append(f"{name}: has no faces")

        # Check for thick fronts (should have 8 vertices for box)
        if obj.get("type") in ("door", "drawer"):
            if obj.get("vertex_count", 0) < 8:
                warnings.append(
                    f"{name}: front has {obj.get('vertex_count', 0)} vertices "
                    f"(expected 8 for thick box)"
                )


def _vec_to_list(vec) -> list:
    """Convert Blender vector to list."""
    return [vec.x, vec.y, vec.z]


def print_manifest_summary(manifest: dict) -> None:
    """Print human-readable summary of manifest."""
    print("\n" + "=" * 70)
    print("GEOMETRY MANIFEST SUMMARY")
    print("=" * 70)

    summary = manifest["summary"]
    print(f"\nTotal Objects: {summary['total_objects']}")
    print(f"Total Vertices: {summary['total_vertices']}")
    print(f"Total Faces: {summary['total_faces']}")

    print("\nObjects by Type:")
    for obj_type, count in sorted(summary["objects_by_type"].items()):
        print(f"  {obj_type}: {count}")

    print("\nObject Details:")
    print("-" * 70)
    for obj in manifest["objects"]:
        name = obj["name"]
        obj_type = obj.get("type", "unknown")
        dims = obj.get("dimensions_mm", [0, 0, 0])
        verts = obj.get("vertex_count", 0)
        faces = obj.get("face_count", 0)

        print(f"\n  {name}")
        print(f"    Type: {obj_type}")
        print(f"    Dims: {dims[0]:.1f} × {dims[1]:.1f} × {dims[2]:.1f} mm")
        print(f"    Mesh: {verts} vertices, {faces} faces")

    # Validation results
    warnings = manifest.get("validation", {}).get("warnings", [])
    errors = manifest.get("validation", {}).get("errors", [])

    if warnings or errors:
        print("\n" + "-" * 70)
        print("VALIDATION RESULTS:")
        for error in errors:
            print(f"  ❌ ERROR: {error}")
        for warning in warnings:
            print(f"  ⚠️  WARNING: {warning}")

    print("=" * 70)
