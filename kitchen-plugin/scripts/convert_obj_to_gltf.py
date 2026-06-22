#!/usr/bin/env python3
"""Convert OBJ to glTF 2.0 format.

Reads OBJ file and creates a glTF 2.0 JSON file that can be analyzed
with our analyze_gltf_v2.py tool.

Usage:
    python scripts/convert_obj_to_gltf.py output/meshes/myster-box.obj
"""

import json
import struct
import base64
import re
from pathlib import Path
import sys


def parse_obj(path: str) -> dict:
    """Parse OBJ file and extract geometry data."""
    vertices = []
    normals = []
    texcoords = []
    faces = []
    objects = []
    current_object = None
    current_material = None

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
                    'material': current_material,
                }

            elif parts[0] == 'v':
                # Vertex
                if len(parts) >= 4:
                    x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
                    vertices.append((x, y, z))
                    if current_object:
                        current_object['vertices'].append((x, y, z))

            elif parts[0] == 'vn':
                # Normal
                if len(parts) >= 4:
                    nx, ny, nz = float(parts[1]), float(parts[2]), float(parts[3])
                    normals.append((nx, ny, nz))

            elif parts[0] == 'vt':
                # Texture coordinate
                if len(parts) >= 3:
                    u, v = float(parts[1]), float(parts[2])
                    texcoords.append((u, v))

            elif parts[0] == 'f':
                # Face (handle v/vt/vn format)
                face_verts = []
                for p in parts[1:]:
                    # Handle v/vt/vn format
                    indices = p.split('/')
                    v_idx = int(indices[0]) if indices[0] else 0
                    if v_idx < 0:
                        v_idx = len(vertices) + v_idx
                    face_verts.append(v_idx - 1)  # OBJ is 1-indexed
                faces.append(face_verts)
                if current_object:
                    current_object['faces'].append(face_verts)

            elif parts[0] == 'usemtl':
                current_material = parts[1] if len(parts) > 1 else None

    if current_object:
        objects.append(current_object)

    return {
        'vertices': vertices,
        'normals': normals,
        'texcoords': texcoords,
        'faces': faces,
        'objects': objects,
    }


def convert_obj_to_gltf(obj_path: str, output_path: str = None) -> dict:
    """Convert OBJ file to glTF 2.0 format."""

    # Parse OBJ
    obj_data = parse_obj(obj_path)

    if not output_path:
        output_path = Path(obj_path).with_suffix('.gltf')

    # glTF uses Y-up, OBJ typically uses Y-up too
    # We'll keep the same coordinate system

    # Build glTF structure
    gltf = {
        "asset": {
            "version": "2.0",
            "generator": "OBJ-to-glTF Converter"
        },
        "scene": 0,
        "scenes": [{"name": "Scene", "nodes": []}],
        "nodes": [],
        "meshes": [],
        "accessors": [],
        "bufferViews": [],
        "buffers": []
    }

    # Build buffer data
    buffer_data = b''
    byte_offset = 0
    node_idx = 0

    for obj in obj_data['objects']:
        if not obj['vertices'] or not obj['faces']:
            continue

        # Get vertices for this object
        verts = obj['vertices']
        faces = obj['faces']

        # Encode vertices
        vert_bytes = b''
        for v in verts:
            vert_bytes += struct.pack('fff', *v)

        # Encode indices (convert quads to triangles if needed)
        idx_bytes = b''
        for face in faces:
            if len(face) == 3:
                # Triangle
                for idx in face:
                    idx_bytes += struct.pack('H', idx)
            elif len(face) == 4:
                # Quad - split into two triangles
                idx_bytes += struct.pack('HHH', face[0], face[1], face[2])
                idx_bytes += struct.pack('HHH', face[0], face[2], face[3])
            else:
                # Polygon - fan triangulation
                for i in range(1, len(face) - 1):
                    idx_bytes += struct.pack('HHH', face[0], face[i], face[i + 1])

        # Calculate bounds
        xs = [v[0] for v in verts]
        ys = [v[1] for v in verts]
        zs = [v[2] for v in verts]

        # Add mesh
        gltf["meshes"].append({
            "name": obj['name'],
            "primitives": [{
                "attributes": {"POSITION": len(gltf["accessors"])},
                "indices": len(gltf["accessors"]) + 1
            }]
        })

        # Add vertex accessor
        gltf["accessors"].append({
            "bufferView": len(gltf["bufferViews"]),
            "componentType": 5126,  # FLOAT
            "count": len(verts),
            "type": "VEC3",
            "byteOffset": 0,
            "min": [min(xs), min(ys), min(zs)],
            "max": [max(xs), max(ys), max(zs)]
        })

        gltf["bufferViews"].append({
            "buffer": 0,
            "byteOffset": byte_offset,
            "byteLength": len(vert_bytes),
            "target": 34962
        })

        # Add index accessor
        idx_count = 0
        for face in faces:
            if len(face) == 3:
                idx_count += 3
            elif len(face) == 4:
                idx_count += 6
            else:
                idx_count += (len(face) - 2) * 3

        gltf["accessors"].append({
            "bufferView": len(gltf["bufferViews"]),
            "componentType": 5123,  # UNSIGNED_SHORT
            "count": idx_count,
            "type": "SCALAR",
            "byteOffset": 0
        })

        gltf["bufferViews"].append({
            "buffer": 0,
            "byteOffset": byte_offset + len(vert_bytes),
            "byteLength": len(idx_bytes),
            "target": 34963
        })

        # Add node
        gltf["nodes"].append({
            "name": obj['name'],
            "mesh": len(gltf["meshes"]) - 1
        })
        gltf["scenes"][0]["nodes"].append(node_idx)
        node_idx += 1

        buffer_data += vert_bytes + idx_bytes
        byte_offset += len(vert_bytes) + len(idx_bytes)

    # Add buffer
    gltf["buffers"].append({
        "uri": "data:application/octet-stream;base64," + base64.b64encode(buffer_data).decode(),
        "byteLength": len(buffer_data)
    })

    # Write glTF
    with open(output_path, 'w') as f:
        json.dump(gltf, f, indent=2)

    return gltf


def print_conversion_summary(obj_path: str, gltf: dict) -> None:
    """Print summary of conversion."""
    print(f"\n{'=' * 80}")
    print(f"OBJ → glTF CONVERSION")
    print(f"{'=' * 80}")
    print(f"\nInput:  {obj_path}")
    print(f"Output: {Path(obj_path).with_suffix('.gltf')}")

    print(f"\nMeshes: {len(gltf['meshes'])}")
    for i, mesh in enumerate(gltf['meshes']):
        name = mesh['name']
        acc_idx = mesh['primitives'][0]['attributes']['POSITION']
        acc = gltf['accessors'][acc_idx]
        print(f"  [{i}] {name}: {acc['count']} vertices")

    print(f"\nBuffer: {gltf['buffers'][0]['byteLength']} bytes")

    # Show bounds
    print(f"\nBounds:")
    for i, mesh in enumerate(gltf['meshes']):
        acc_idx = mesh['primitives'][0]['attributes']['POSITION']
        acc = gltf['accessors'][acc_idx]
        min_v = acc['min']
        max_v = acc['max']
        dims = [max_v[j] - min_v[j] for j in range(3)]
        print(f"  {mesh['name']}:")
        print(f"    X: {min_v[0]*1000:.1f} to {max_v[0]*1000:.1f} mm ({dims[0]*1000:.1f}mm)")
        print(f"    Y: {min_v[1]*1000:.1f} to {max_v[1]*1000:.1f} mm ({dims[1]*1000:.1f}mm)")
        print(f"    Z: {min_v[2]*1000:.1f} to {max_v[2]*1000:.1f} mm ({dims[2]*1000:.1f}mm)")


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/convert_obj_to_gltf.py <file.obj> [output.gltf]")
        sys.exit(1)

    obj_path = sys.argv[1]
    if not Path(obj_path).exists():
        print(f"Error: file not found: {obj_path}")
        sys.exit(1)

    output_path = sys.argv[2] if len(sys.argv) > 2 else None

    gltf = convert_obj_to_gltf(obj_path, output_path)
    print_conversion_summary(obj_path, gltf)

    print(f"\nRun: python scripts/analyze_gltf_v2.py {Path(obj_path).with_suffix('.gltf')}")


if __name__ == "__main__":
    main()
