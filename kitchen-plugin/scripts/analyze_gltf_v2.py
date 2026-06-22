#!/usr/bin/env python3
"""Robust glTF Analyzer with Coordinate Conversion.

Converts glTF Y-up coordinates to Z-up (our system) for easy analysis.

glTF coordinate system: Y-up, right-handed
Our coordinate system: Z-up, right-handed

Conversion:
  glTF X → Our X (width)
  glTF Y → Our Z (height)
  glTF -Z → Our Y (depth, into room)

Usage:
    python scripts/analyze_gltf_v2.py output/meshes/kitchen.gltf
"""

import json
import sys
import struct
import base64
from pathlib import Path


def load_gltf(path: str) -> dict:
    """Load and parse glTF file."""
    with open(path, 'r') as f:
        return json.load(f)


def get_buffer_data(gltf: dict, accessor_idx: int, base_path: str) -> bytes:
    """Get raw buffer data for an accessor."""
    accessor = gltf['accessors'][accessor_idx]
    buffer_view = gltf['bufferViews'][accessor['bufferView']]
    buffer_idx = buffer_view['buffer']
    buffer = gltf['buffers'][buffer_idx]

    uri = buffer.get('uri', '')
    if uri.startswith('data:'):
        data = base64.b64decode(uri.split(',')[1])
    else:
        data = Path(base_path).parent.joinpath(uri).read_bytes()

    return data


def read_vec3(gltf: dict, accessor_idx: int, base_path: str) -> list:
    """Read vec3 positions from accessor, converted to Z-up."""
    accessor = gltf['accessors'][accessor_idx]
    data = get_buffer_data(gltf, accessor_idx, base_path)

    buffer_view = gltf['bufferViews'][accessor['bufferView']]
    byte_offset = buffer_view.get('byteOffset', 0) + accessor.get('byteOffset', 0)
    count = accessor['count']

    vectors = []
    for i in range(count):
        x, y, z = struct.unpack_from('<fff', data, byte_offset + i * 12)
        # Convert Y-up to Z-up:
        # glTF (x, y, z) → Our (x, -z, y)
        vectors.append((x, -z, y))

    return vectors


def read_indices(gltf: dict, accessor_idx: int, base_path: str) -> list:
    """Read indices from accessor."""
    accessor = gltf['accessors'][accessor_idx]
    data = get_buffer_data(gltf, accessor_idx, base_path)

    buffer_view = gltf['bufferViews'][accessor['bufferView']]
    byte_offset = buffer_view.get('byteOffset', 0) + accessor.get('byteOffset', 0)
    count = accessor['count']
    component_type = accessor['componentType']

    indices = []
    for i in range(count):
        if component_type == 5123:  # UNSIGNED_SHORT
            idx = struct.unpack_from('<H', data, byte_offset + i * 2)[0]
        elif component_type == 5125:  # UNSIGNED_INT
            idx = struct.unpack_from('<I', data, byte_offset + i * 4)[0]
        else:
            idx = 0
        indices.append(idx)

    return indices


def analyze_gltf(path: str) -> dict:
    """Analyze glTF file with coordinate conversion."""
    gltf = load_gltf(path)
    base_path = path

    result = {
        "format": "gltf-analysis",
        "coordinate_system": "Z-up (converted from Y-up)",
        "objects": []
    }

    # Build node tree
    nodes = gltf.get('nodes', [])
    meshes = gltf.get('meshes', [])

    # Find root nodes
    scene = gltf.get('scenes', [{}])[gltf.get('scene', 0)]
    root_node_indices = scene.get('nodes', [])

    def process_node(node_idx: int, parent_name: str = None, parent_translation: tuple = (0, 0, 0)):
        """Process a node and its children."""
        node = nodes[node_idx]
        name = node.get('name', f'node_{node_idx}')
        mesh_idx = node.get('mesh')
        children = node.get('children', [])

        # Get translation (convert Y-up to Z-up)
        t = node.get('translation', [0, 0, 0])
        # glTF (tx, ty, tz) → Our (tx, -tz, ty)
        translation = (t[0], -t[2], t[1])

        # Calculate world translation
        world_translation = (
            parent_translation[0] + translation[0],
            parent_translation[1] + translation[1],
            parent_translation[2] + translation[2]
        )

        obj_data = {
            "name": name,
            "parent": parent_name,
            "local_translation": translation,
            "world_translation": world_translation,
            "mesh": None
        }

        # Process mesh if present
        if mesh_idx is not None and mesh_idx < len(meshes):
            mesh = meshes[mesh_idx]
            obj_data["mesh"] = process_mesh(mesh, base_path, world_translation)

        result["objects"].append(obj_data)

        # Process children
        for child_idx in children:
            process_node(child_idx, name, world_translation)

    def process_mesh(mesh: dict, base_path: str, world_translation: tuple) -> dict:
        """Process mesh data."""
        mesh_data = {
            "primitives": []
        }

        for prim in mesh.get('primitives', []):
            attributes = prim.get('attributes', {})
            indices_idx = prim.get('indices')

            prim_data = {
                "vertices": [],
                "faces": [],
                "bounds": None
            }

            # Read vertices
            pos_idx = attributes.get('POSITION')
            if pos_idx is not None:
                vertices = read_vec3(gltf, pos_idx, base_path)
                prim_data["vertices"] = vertices

                # Calculate bounds
                xs = [v[0] for v in vertices]
                ys = [v[1] for v in vertices]
                zs = [v[2] for v in vertices]

                prim_data["bounds"] = {
                    "min": (min(xs), min(ys), min(zs)),
                    "max": (max(xs), max(ys), max(zs)),
                    "dimensions": (max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs))
                }

            # Read indices
            if indices_idx is not None:
                indices = read_indices(gltf, indices_idx, base_path)
                # Convert to face list (triangles)
                faces = []
                for i in range(0, len(indices), 3):
                    if i + 2 < len(indices):
                        faces.append((indices[i], indices[i+1], indices[i+2]))
                prim_data["faces"] = faces

            mesh_data["primitives"].append(prim_data)

        return mesh_data

    # Process all root nodes
    for node_idx in root_node_indices:
        process_node(node_idx)

    return result


def print_analysis(analysis: dict) -> None:
    """Print analysis results in human-readable format."""
    print("\n" + "=" * 90)
    print("GLTF GEOMETRY ANALYSIS (Z-up coordinates)")
    print("=" * 90)

    for obj in analysis["objects"]:
        name = obj["name"]
        parent = obj.get("parent")
        translation = obj.get("world_translation", (0, 0, 0))
        mesh = obj.get("mesh")

        print(f"\n{'─' * 90}")
        print(f"  {name}")
        if parent:
            print(f"    Parent: {parent}")
        print(f"    World Position: ({translation[0]*1000:.1f}, {translation[1]*1000:.1f}, {translation[2]*1000:.1f}) mm")

        if mesh:
            for i, prim in enumerate(mesh.get("primitives", [])):
                vertices = prim.get("vertices", [])
                faces = prim.get("faces", [])
                bounds = prim.get("bounds")

                print(f"    Mesh: {len(vertices)} vertices, {len(faces)} faces")

                if bounds:
                    dims = bounds["dimensions"]
                    print(f"    Local Dims: {dims[0]*1000:.1f} × {dims[1]*1000:.1f} × {dims[2]*1000:.1f} mm")

                # Print vertex coordinates
                if vertices:
                    print(f"    Vertices (local):")
                    for j, v in enumerate(vertices[:4]):
                        print(f"      [{j:2d}] ({v[0]*1000:8.2f}, {v[1]*1000:8.2f}, {v[2]*1000:8.2f}) mm")
                    if len(vertices) > 8:
                        print(f"      ... ({len(vertices) - 8} more)")
                    if len(vertices) > 4:
                        for j, v in enumerate(vertices[-4:], len(vertices) - 4):
                            print(f"      [{j:2d}] ({v[0]*1000:8.2f}, {v[1]*1000:8.2f}, {v[2]*1000:8.2f}) mm")

                # Calculate world bounds
                if vertices:
                    world_verts = [
                        (v[0] + translation[0], v[1] + translation[1], v[2] + translation[2])
                        for v in vertices
                    ]
                    wx = [v[0] for v in world_verts]
                    wy = [v[1] for v in world_verts]
                    wz = [v[2] for v in world_verts]
                    print(f"    World Bounds:")
                    print(f"      X: {min(wx)*1000:.1f} to {max(wx)*1000:.1f} mm")
                    print(f"      Y: {min(wy)*1000:.1f} to {max(wy)*1000:.1f} mm")
                    print(f"      Z: {min(wz)*1000:.1f} to {max(wz)*1000:.1f} mm")

    # Validation
    print(f"\n{'=' * 90}")
    print("VALIDATION")
    print("=" * 90)

    issues = []
    for obj in analysis["objects"]:
        name = obj["name"]
        mesh = obj.get("mesh")

        if not mesh:
            continue

        for i, prim in enumerate(mesh.get("primitives", [])):
            vertices = prim.get("vertices", [])
            faces = prim.get("faces", [])

            # Check for degenerate faces
            for j, face in enumerate(faces):
                if len(set(face)) < 3:
                    issues.append(f"{name}: Face {j} is degenerate (less than 3 unique vertices)")

            # Check for zero-size dimensions
            bounds = prim.get("bounds")
            if bounds:
                dims = bounds["dimensions"]
                for k, (dim_name, dim_val) in enumerate(zip(["X", "Y", "Z"], dims)):
                    if dim_val < 0.0001:
                        issues.append(f"{name}: {dim_name} dimension is ~0")

    if issues:
        print(f"\n❌ Found {len(issues)} issues:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("\n✓ No issues found")


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/analyze_gltf_v2.py <file.gltf>")
        sys.exit(1)

    path = sys.argv[1]
    if not Path(path).exists():
        print(f"Error: file not found: {path}")
        sys.exit(1)

    analysis = analyze_gltf(path)
    print_analysis(analysis)


if __name__ == "__main__":
    main()
