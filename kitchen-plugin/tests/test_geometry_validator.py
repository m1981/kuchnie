"""Geometry Manifest Tests.

Tests for the geometry manifest export.
"""

import sys
from pathlib import Path
import json
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from unittest.mock import MagicMock
from src.geometry_manifest import (
    export_manifest,
    _classify_object,
    _extract_object,
)


# ─── Mock bpy Object ─────────────────────────────────────────────────────────

class MockVector:
    """Mock Blender vector."""
    def __init__(self, x=0, y=0, z=0):
        self.x = x
        self.y = y
        self.z = z


class MockMatrix:
    """Mock Blender matrix that acts as identity."""
    def __matmul__(self, other):
        # Identity matrix: returns the vector as-is
        if hasattr(other, 'x'):
            return other
        # Handle tuple input
        return MockVector(other[0], other[1], other[2])


def create_mock_object(name: str, vertices: list, faces: list,
                       location=(0, 0, 0)):
    """Create a mock Blender object for testing."""
    obj = MagicMock()
    obj.name = name
    obj.location = MockVector(location[0], location[1], location[2])
    obj.rotation_euler = MockVector(0, 0, 0)
    obj.scale = MockVector(1, 1, 1)
    obj.matrix_world = MockMatrix()
    obj.children = []
    obj.parent = None

    # Mock mesh data
    mesh = MagicMock()
    mock_vertices = []
    for v in vertices:
        mock_v = MagicMock()
        mock_v.co = MockVector(v[0], v[1], v[2])
        mock_vertices.append(mock_v)
    mesh.vertices = mock_vertices

    mock_faces = []
    for f in faces:
        mock_f = MagicMock()
        mock_f.vertices = f
        mock_faces.append(mock_f)
    mesh.polygons = mock_faces

    obj.data = mesh
    obj.type = 'MESH'

    return obj


# ─── Tests ───────────────────────────────────────────────────────────────────

class TestClassifyObject:
    """Test object classification."""

    def test_classify_door(self):
        assert _classify_object("run0_base_0_base-door_door") == "door_front"

    def test_classify_drawer(self):
        assert _classify_object("run0_base_1_base-drawers_drawer0") == "drawer_front"

    def test_classify_back_panel(self):
        assert _classify_object("run0_base_0_base-door_back") == "back_panel"

    def test_classify_carcass(self):
        assert _classify_object("run0_base_0_base-door") == "carcass"

    def test_classify_countertop(self):
        assert _classify_object("countertop") == "countertop"

    def test_classify_filler(self):
        assert _classify_object("filler") == "filler"


class TestExtractObject:
    """Test object data extraction."""

    def test_extract_carcass_box(self):
        """Extract data from a box (8 vertices, 6 faces)."""
        # Simple box: 1x1x1
        verts = [
            (0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0),
            (0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1),
        ]
        faces = [
            [0, 1, 2, 3],  # bottom
            [4, 5, 6, 7],  # top
            [0, 1, 5, 4],  # front
            [1, 2, 6, 5],  # right
            [2, 3, 7, 6],  # back
            [3, 0, 4, 7],  # left
        ]

        obj = create_mock_object("test_box", verts, faces)
        data = _extract_object(obj, {}, {}, 2.0)

        assert data is not None
        assert data['vertex_count'] == 8
        assert data['face_count'] == 6
        assert data['local_dimensions_mm'][0] == pytest.approx(1000.0)  # 1m = 1000mm

    def test_extract_flat_quad(self):
        """Extract data from a flat quad (4 vertices, 1 face)."""
        verts = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)]
        faces = [[0, 1, 2, 3]]

        obj = create_mock_object("test_quad", verts, faces)
        data = _extract_object(obj, {}, {}, 2.0)

        assert data is not None
        assert data['vertex_count'] == 4
        assert data['face_count'] == 1
        assert data['local_dimensions_mm'][2] == pytest.approx(0.0)  # Z = 0 (flat)


class TestExportManifest:
    """Test manifest export."""

    def test_export_manifest(self):
        """Export manifest to JSON file."""
        # Create mock objects
        verts = [
            (0, 0, 0), (0.6, 0, 0), (0.6, 0.56, 0), (0, 0.56, 0),
            (0, 0, 0.72), (0.6, 0, 0.72), (0.6, 0.56, 0.72), (0, 0.56, 0.72),
        ]
        faces = [
            [0, 1, 2, 3], [4, 5, 6, 7],
            [0, 1, 5, 4], [1, 2, 6, 5],
            [2, 3, 7, 6], [3, 0, 4, 7],
        ]

        obj = create_mock_object("run0_base_0_base-door", verts, faces)
        objects = [obj]

        # Export to temp file
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            manifest_path = f.name

        manifest = export_manifest(objects, manifest_path, settings={"baseDepth": 560})

        # Verify manifest structure
        assert manifest['format'] == 'kitchen-geometry-manifest'
        assert manifest['version'] == '2.0'
        assert manifest['units'] == 'meters'
        assert manifest['validation_summary']['total_objects'] == 1
        assert manifest['validation_summary']['total_vertices'] == 8
        assert manifest['validation_summary']['total_faces'] == 6

        # Verify object data
        obj_data = manifest['objects'][0]
        assert obj_data['name'] == 'run0_base_0_base-door'
        assert obj_data['classification'] == 'carcass'
        assert obj_data['vertex_count'] == 8
        assert obj_data['face_count'] == 6

        # Verify file was written
        with open(manifest_path) as f:
            loaded = json.load(f)
        assert loaded['format'] == 'kitchen-geometry-manifest'
        assert loaded['version'] == '2.0'

    def test_validation_catches_flat_quad(self):
        """Validator should warn about flat quads."""
        verts = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)]
        faces = [[0, 1, 2, 3]]

        obj = create_mock_object("run0_base_0_base-door_door", verts, faces)

        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            manifest_path = f.name

        manifest = export_manifest([obj], manifest_path)

        # Should have warning about front having wrong vertex count
        issues = manifest['validation_summary']['issues']
        assert any("vertex" in i.get('check', '').lower()
                    for i in issues)
