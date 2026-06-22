#!/usr/bin/env python3
"""Reference Object Analyzer.

Analyzes myster-box.obj as a reference to establish ground truth
for our coordinate system and measurement tools.

Usage:
    python scripts/analyze_reference_obj.py output/meshes/myster-box.obj
"""

import json
import struct
import base64
from pathlib import Path
import sys


def parse_obj(path: str) -> dict:
    """Parse OBJ file."""
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
                if current_object:
                    objects.append(current_object)
                current_object = {
                    'name': parts[1] if len(parts) > 1 else 'unnamed',
                    'vertices': [],
                    'faces': [],
                    'vertex_offset': len(vertices),
                }

            elif parts[0] == 'v':
                if len(parts) >= 4:
                    x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
                    vertices.append((x, y, z))
                    if current_object:
                        current_object['vertices'].append((x, y, z))

            elif parts[0] == 'f':
                face_verts = []
                for p in parts[1:]:
                    indices = p.split('/')
                    v_idx = int(indices[0]) if indices[0] else 0
                    if v_idx < 0:
                        v_idx = len(vertices) + v_idx
                    face_verts.append(v_idx - 1)
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


def detect_coordinate_system(obj_data: dict) -> dict:
    """Detect coordinate system from object positions."""

    all_verts = obj_data['vertices']
    if not all_verts:
        return {"system": "unknown", "confidence": 0}

    # Calculate bounds
    xs = [v[0] for v in all_verts]
    ys = [v[1] for v in all_verts]
    zs = [v[2] for v in all_verts]

    x_range = max(xs) - min(xs)
    y_range = max(ys) - min(ys)
    z_range = max(zs) - min(zs)

    # Heuristic: Z-up systems typically have Z as height (largest range for cabinets)
    # Y-up systems have Y as height
    # Also check if there are negative values (suggesting depth axis)

    x_negative = min(xs) < 0
    y_negative = min(ys) < 0
    z_negative = min(zs) < 0

    # For kitchen cabinets:
    # - Width (X): usually 300-1200mm
    # - Depth (Y or Z): usually 300-600mm
    # - Height (Z or Y): usually 720-2000mm

    # Check if Z looks like height (larger range, positive)
    if z_range > x_range and z_range > y_range and not z_negative:
        system = "Z-up"
        confidence = 0.8
    # Check if Y looks like height
    elif y_range > x_range and y_range > z_range and not y_negative:
        system = "Y-up"
        confidence = 0.7
    else:
        # Check based on typical cabinet dimensions
        # If we see ~720mm in one axis, that's likely height
        for axis, range_val in [('X', x_range), ('Y', y_range), ('Z', z_range)]:
            if 700 < range_val < 750:  # ~720mm height
                if axis == 'Z':
                    system = "Z-up"
                    confidence = 0.9
                elif axis == 'Y':
                    system = "Y-up"
                    confidence = 0.9
                break
        else:
            system = "unknown"
            confidence = 0.5

    return {
        "system": system,
        "confidence": confidence,
        "bounds": {
            "x": {"min": min(xs), "max": max(xs), "range": x_range, "has_negative": x_negative},
            "y": {"min": min(ys), "max": max(ys), "range": y_range, "has_negative": y_negative},
            "z": {"min": min(zs), "max": max(zs), "range": z_range, "has_negative": z_negative},
        }
    }


def analyze_object(obj: dict, coord_system: str) -> dict:
    """Analyze a single object."""

    verts = obj['vertices']
    if not verts:
        return {"name": obj['name'], "error": "no vertices"}

    xs = [v[0] for v in verts]
    ys = [v[1] for v in verts]
    zs = [v[2] for v in verts]

    # Calculate dimensions based on coordinate system
    if coord_system == "Z-up":
        width = max(xs) - min(xs)
        depth = max(ys) - min(ys)
        height = max(zs) - min(zs)
    else:  # Y-up
        width = max(xs) - min(xs)
        height = max(ys) - min(ys)
        depth = max(zs) - min(zs)

    return {
        "name": obj['name'],
        "vertex_count": len(verts),
        "face_count": len(obj['faces']),
        "bounds": {
            "x": {"min": min(xs), "max": max(xs)},
            "y": {"min": min(ys), "max": max(ys)},
            "z": {"min": min(zs), "max": max(zs)},
        },
        "dimensions": {
            "width": width,
            "depth": depth,
            "height": height,
        },
        "center": {
            "x": (min(xs) + max(xs)) / 2,
            "y": (min(ys) + max(ys)) / 2,
            "z": (min(zs) + max(zs)) / 2,
        }
    }


def create_visualization(objects: list, coord_system: str) -> str:
    """Create ASCII visualization of objects."""

    lines = []
    lines.append("=" * 80)
    lines.append("OBJECT LAYOUT VISUALIZATION")
    lines.append("=" * 80)

    if coord_system == "Z-up":
        lines.append("\nCoordinate System: Z-up (X=width, Y=depth, Z=height)")
        lines.append("\nTop View (X-Y plane, looking down):")
    else:
        lines.append("\nCoordinate System: Y-up (X=width, Y=height, Z=depth)")
        lines.append("\nTop View (X-Z plane, looking down):")

    # Find overall bounds
    all_x = []
    all_y = []
    for obj in objects:
        bounds = obj.get('bounds', {})
        all_x.extend([bounds.get('x', {}).get('min', 0), bounds.get('x', {}).get('max', 0)])
        if coord_system == "Z-up":
            all_y.extend([bounds.get('y', {}).get('min', 0), bounds.get('y', {}).get('max', 0)])
        else:
            all_y.extend([bounds.get('z', {}).get('min', 0), bounds.get('z', {}).get('max', 0)])

    x_min, x_max = min(all_x), max(all_x)
    y_min, y_max = min(all_y), max(all_y)

    # Create grid
    grid_width = 60
    grid_height = 30

    grid = [[' ' for _ in range(grid_width)] for _ in range(grid_height)]

    # Plot objects
    for obj in objects:
        bounds = obj.get('bounds', {})
        x1 = int((bounds.get('x', {}).get('min', 0) - x_min) / (x_max - x_min + 0.001) * (grid_width - 1))
        x2 = int((bounds.get('x', {}).get('max', 0) - x_min) / (x_max - x_min + 0.001) * (grid_width - 1))

        if coord_system == "Z-up":
            y1 = int((bounds.get('y', {}).get('min', 0) - y_min) / (y_max - y_min + 0.001) * (grid_height - 1))
            y2 = int((bounds.get('y', {}).get('max', 0) - y_min) / (y_max - y_min + 0.001) * (grid_height - 1))
        else:
            y1 = int((bounds.get('z', {}).get('min', 0) - y_min) / (y_max - y_min + 0.001) * (grid_height - 1))
            y2 = int((bounds.get('z', {}).get('max', 0) - y_min) / (y_max - y_min + 0.001) * (grid_height - 1))

        # Fill grid
        for y in range(min(y1, y2), max(y1, y2) + 1):
            for x in range(min(x1, x2), max(x1, x2) + 1):
                if 0 <= y < grid_height and 0 <= x < grid_width:
                    grid[y][x] = '█'

    # Add labels
    for i, obj in enumerate(objects):
        bounds = obj.get('bounds', {})
        cx = (bounds.get('x', {}).get('min', 0) + bounds.get('x', {}).get('max', 0)) / 2
        if coord_system == "Z-up":
            cy = (bounds.get('y', {}).get('min', 0) + bounds.get('y', {}).get('max', 0)) / 2
        else:
            cy = (bounds.get('z', {}).get('min', 0) + bounds.get('z', {}).get('max', 0)) / 2

        gx = int((cx - x_min) / (x_max - x_min + 0.001) * (grid_width - 1))
        gy = int((cy - y_min) / (y_max - y_min + 0.001) * (grid_height - 1))

        if 0 <= gy < grid_height and 0 <= gx < grid_width:
            label = obj['name'][:5]
            for j, ch in enumerate(label):
                if gx + j < grid_width:
                    grid[gy][gx + j] = ch

    # Print grid
    for row in grid:
        lines.append(''.join(row))

    return '\n'.join(lines)


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/analyze_reference_obj.py <file.obj>")
        sys.exit(1)

    obj_path = sys.argv[1]
    if not Path(obj_path).exists():
        print(f"Error: file not found: {obj_path}")
        sys.exit(1)

    # Parse OBJ
    obj_data = parse_obj(obj_path)

    # Detect coordinate system
    coord_info = detect_coordinate_system(obj_data)

    print("=" * 80)
    print("REFERENCE OBJECT ANALYSIS")
    print("=" * 80)

    print(f"\nFile: {obj_path}")
    print(f"Total vertices: {len(obj_data['vertices'])}")
    print(f"Total faces: {len(obj_data['faces'])}")
    print(f"Objects: {len(obj_data['objects'])}")

    print(f"\nCoordinate System Detection:")
    print(f"  System: {coord_info['system']}")
    print(f"  Confidence: {coord_info['confidence']:.0%}")

    bounds = coord_info['bounds']
    print(f"\nOverall Bounds:")
    print(f"  X: {bounds['x']['min']*1000:.1f} to {bounds['x']['max']*1000:.1f} mm ({bounds['x']['range']*1000:.1f}mm)")
    print(f"  Y: {bounds['y']['min']*1000:.1f} to {bounds['y']['max']*1000:.1f} mm ({bounds['y']['range']*1000:.1f}mm)")
    print(f"  Z: {bounds['z']['min']*1000:.1f} to {bounds['z']['max']*1000:.1f} mm ({bounds['z']['range']*1000:.1f}mm)")

    # Analyze each object
    print(f"\n{'=' * 80}")
    print("OBJECT DETAILS")
    print("=" * 80)

    analyzed_objects = []
    for obj in obj_data['objects']:
        analysis = analyze_object(obj, coord_info['system'])
        analyzed_objects.append(analysis)

        print(f"\n{analysis['name']}:")
        print(f"  Vertices: {analysis['vertex_count']}")
        print(f"  Faces: {analysis['face_count']}")

        dims = analysis['dimensions']
        print(f"  Dimensions:")
        print(f"    Width:  {dims['width']*1000:.1f} mm")
        print(f"    Depth:  {dims['depth']*1000:.1f} mm")
        print(f"    Height: {dims['height']*1000:.1f} mm")

        bounds = analysis['bounds']
        print(f"  Bounds:")
        print(f"    X: {bounds['x']['min']*1000:.1f} to {bounds['x']['max']*1000:.1f} mm")
        print(f"    Y: {bounds['y']['min']*1000:.1f} to {bounds['y']['max']*1000:.1f} mm")
        print(f"    Z: {bounds['z']['min']*1000:.1f} to {bounds['z']['max']*1000:.1f} mm")

    # Create visualization
    print(f"\n{create_visualization(analyzed_objects, coord_info['system'])}")

    # Summary
    print(f"\n{'=' * 80}")
    print("SUMMARY")
    print("=" * 80)

    print(f"\nThis reference object contains:")
    for obj in analyzed_objects:
        dims = obj['dimensions']
        print(f"  - {obj['name']}: {dims['width']*1000:.0f} × {dims['depth']*1000:.0f} × {dims['height']*1000:.0f} mm")


if __name__ == "__main__":
    main()
