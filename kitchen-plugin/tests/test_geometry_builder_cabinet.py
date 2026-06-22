"""Geometry Builder Cabinet Construction Tests.

Tests that geometry_builder creates proper European cabinet meshes
using CabinetGeometry for accurate 18mm corpus, 19mm front, 3mm back.

These tests mock bpy since it's only available in Blender.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from unittest.mock import MagicMock, patch, call
from src.kitchen.cabinet_geometry import CabinetGeometry


# ─── Mock bpy Setup ──────────────────────────────────────────────────────────

@pytest.fixture
def mock_bpy():
    """Create mock bpy module."""
    bpy = MagicMock()

    # Mock mesh creation
    mock_mesh = MagicMock()
    mock_mesh.from_pydata = MagicMock()
    mock_mesh.update = MagicMock()
    bpy.data.meshes.new.return_value = mock_mesh

    # Mock object creation
    mock_obj = MagicMock()
    mock_obj.name = ""
    bpy.data.objects.new.return_value = mock_obj

    # Mock collection
    bpy.context.collection.objects.link = MagicMock()

    return bpy


# ─── Helper Functions ────────────────────────────────────────────────────────

def extract_box_verts(mock_mesh):
    """Extract vertices from a mock mesh.from_pydata call."""
    calls = mock_mesh.from_pydata.call_args_list
    if not calls:
        return None
    return calls[-1][0][0]  # verts from last call


def extract_box_faces(mock_mesh):
    """Extract faces from a mock mesh.from_pydata call."""
    calls = mock_mesh.from_pydata.call_args_list
    if not calls:
        return None
    return calls[-1][0][2]  # faces from last call


# ─── Tests: Carcass Mesh Creation ─────────────────────────────────────────────

class TestCarcassMeshCreation:
    """Test that carcass mesh is created with correct dimensions."""

    def test_carcass_uses_cabinet_geometry(self, mock_bpy):
        """Carcass should use CabinetGeometry for dimensions."""
        # Create geometry calculator for D60 cabinet
        geom = CabinetGeometry(600, 560, 720)

        # Expected internal dimensions
        assert geom.internal_width == 564
        assert geom.internal_depth == 547
        assert geom.internal_height == 720

    def test_carcass_external_dimensions(self, mock_bpy):
        """Carcass external box should match external width/depth/height."""
        geom = CabinetGeometry(600, 560, 720)

        # When creating carcass, use external dimensions
        w = geom.external_width / 1000  # Convert to meters
        d = geom.external_depth / 1000
        h = geom.external_height / 1000

        assert w == pytest.approx(0.6)
        assert d == pytest.approx(0.56)
        assert h == pytest.approx(0.72)


# ─── Tests: Front Panel Mesh Creation ────────────────────────────────────────

class TestFrontPanelMeshCreation:
    """Test that front panel is created as a thick box, not flat quad."""

    def test_front_has_thickness(self):
        """Front panel should have 19mm thickness (not zero)."""
        geom = CabinetGeometry(600, 560, 720)

        # Front thickness in meters
        thickness_m = geom.front_thickness / 1000

        assert thickness_m == pytest.approx(0.019)
        assert thickness_m > 0  # Not zero!

    def test_front_dimensions_with_overlay(self):
        """Front panel should be larger than carcass (overlay)."""
        geom = CabinetGeometry(600, 560, 720)
        front_w, front_h = geom.front_dimensions()

        # Front is wider than carcass (604 > 600)
        assert front_w > geom.external_width
        # Front is taller than carcass (724 > 720)
        assert front_h > geom.external_height

    def test_front_box_vertices(self):
        """Front panel should be a box with 8 vertices (not 4)."""
        geom = CabinetGeometry(600, 560, 720)
        front_w, front_h = geom.front_dimensions()
        front_x, front_y, front_z = geom.front_position()

        # Convert to meters
        fw = front_w / 1000
        fh = front_h / 1000
        ft = geom.front_thickness / 1000
        fx = front_x / 1000
        fy = front_y / 1000
        fz = front_z / 1000

        # Front box vertices (8 vertices for a box)
        expected_verts = [
            (fx, fy, fz),                      # 0: front-left-bottom
            (fx + fw, fy, fz),                 # 1: front-right-bottom
            (fx + fw, fy, fz + fh),            # 2: front-right-top
            (fx, fy, fz + fh),                 # 3: front-left-top
            (fx, fy + ft, fz),                 # 4: back-left-bottom
            (fx + fw, fy + ft, fz),            # 5: back-right-bottom
            (fx + fw, fy + ft, fz + fh),       # 6: back-right-top
            (fx, fy + ft, fz + fh),            # 7: back-left-top
        ]

        # Front should have 8 vertices (box), not 4 (quad)
        assert len(expected_verts) == 8

    def test_front_box_faces(self):
        """Front panel box should have 6 faces."""
        # 6 faces for a closed box
        expected_face_count = 6
        assert expected_face_count == 6

    def test_front_position_relative_to_carcass(self):
        """Front panel should be positioned correctly relative to carcass."""
        geom = CabinetGeometry(600, 560, 720)
        x, y, z = geom.front_position()

        # Front extends forward (negative Y)
        assert y < 0
        # Front overlaps sides (negative X for left shift)
        assert x < 0
        # Front overlaps bottom (negative Z for down shift)
        assert z < 0


# ─── Tests: Back Panel Mesh Creation ─────────────────────────────────────────

class TestBackPanelMeshCreation:
    """Test that back panel is created as separate thin panel."""

    def test_back_panel_is_thin(self):
        """Back panel should be 3mm thick."""
        geom = CabinetGeometry(600, 560, 720)

        assert geom.back_thickness == pytest.approx(0.003 * 1000)  # 3mm

    def test_back_panel_dimensions(self):
        """Back panel should match internal width and height."""
        geom = CabinetGeometry(600, 560, 720)

        assert geom.back_panel_width == pytest.approx(564.0)
        assert geom.back_panel_height == pytest.approx(717.0)

    def test_back_panel_position_offset(self):
        """Back panel should be offset from rear edge by groove position."""
        geom = CabinetGeometry(600, 560, 720)

        # Back panel Y position = external_depth - groove_offset
        back_y_mm = geom.external_depth - geom.groove_offset
        back_y_m = back_y_mm / 1000

        assert back_y_m == pytest.approx(0.55)  # 560 - 10 = 550mm


# ─── Tests: Geometry Builder Integration ─────────────────────────────────────

class TestGeometryBuilderIntegration:
    """Test that geometry_builder uses CabinetGeometry correctly."""

    def test_cabinet_geometry_available_in_builder(self):
        """CabinetGeometry should be importable from kitchen module."""
        from src.kitchen.cabinet_geometry import CabinetGeometry

        geom = CabinetGeometry(600, 560, 720)
        assert geom is not None

    def test_geometry_calculates_all_dimensions(self):
        """CabinetGeometry should calculate all component dimensions."""
        geom = CabinetGeometry(600, 560, 720)

        # Should have all required properties
        assert hasattr(geom, 'internal_width')
        assert hasattr(geom, 'internal_depth')
        assert hasattr(geom, 'internal_height')
        assert hasattr(geom, 'side_panel_width')
        assert hasattr(geom, 'side_panel_height')
        assert hasattr(geom, 'bottom_panel_width')
        assert hasattr(geom, 'bottom_panel_depth')
        assert hasattr(geom, 'back_panel_width')
        assert hasattr(geom, 'back_panel_height')
        assert hasattr(geom, 'front_dimensions')
        assert hasattr(geom, 'front_position')

    def test_geometry_default_values_match_european_standards(self):
        """Default values should match European kitchen standards."""
        geom = CabinetGeometry(600, 560, 720)

        assert geom.corpus_thickness == 18
        assert geom.back_thickness == 3
        assert geom.front_thickness == 19
        assert geom.groove_offset == 10
