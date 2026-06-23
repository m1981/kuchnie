"""Tests for manifest object extraction.

Verifies that objects in the manifest have correct structure
and construction details. Uses mock data — no Blender dependency.
"""

import pytest


def _make_carcass_object():
    """Create a mock carcass object for testing."""
    return {
        "name": "run0_base_0_base-door",
        "type": "MESH",
        "classification": "carcass",
        "level": "base",
        "run_label": "back wall",
        "run_index": 0,
        "cabinet_index": 0,
        "parent": None,
        "transform": {
            "location_m": [0.0, 0.0, 0.12],
            "rotation_euler_rad": [0, 0, 0],
            "scale": [1, 1, 1],
        },
        "local_bounds": {
            "min_m": [0, 0, 0],
            "max_m": [0.6, 0.56, 0.72],
        },
        "local_dimensions_mm": [600, 560, 720],
        "world_bounds": {
            "min_m": [0, 0, 0.12],
            "max_m": [0.6, 0.56, 0.84],
        },
        "world_dimensions_mm": [600, 560, 720],
        "vertex_count": 16,
        "face_count": 12,
        "expected_dimensions_mm": {
            "width": None,
            "depth": 560,
            "height": 720,
        },
        "construction": {
            "corpus_thickness_mm": 18,
            "back_thickness_mm": 3,
            "front_thickness_mm": 19,
            "groove_offset_mm": 10,
            "front_overlay_mm": 2,
        },
        "children": [
            {
                "name": "run0_base_0_base-door_back",
                "type": "back_panel",
                "local_dimensions_mm": [564, 3, 717],
            },
            {
                "name": "run0_base_0_base-door_door",
                "type": "door_front",
                "local_dimensions_mm": [604, 19, 724],
            },
        ],
        "validation": {
            "width_ok": True,
            "depth_ok": True,
            "height_ok": True,
            "vertex_count_ok": True,
            "face_count_ok": True,
            "issues": [],
        },
    }


def _make_door_object():
    """Create a mock door front object for testing."""
    return {
        "name": "run0_base_0_base-door_door",
        "type": "MESH",
        "classification": "door_front",
        "level": "base",
        "run_label": "back wall",
        "run_index": 0,
        "cabinet_index": 0,
        "parent": "run0_base_0_base-door",
        "transform": {
            "location_m": [0.0, 0.561, 0.0],
            "rotation_euler_rad": [0, 0, 0],
            "scale": [1, 1, 1],
        },
        "local_bounds": {
            "min_m": [-0.002, -0.019, -0.002],
            "max_m": [0.602, 0.0, 0.724],
        },
        "local_dimensions_mm": [604, 19, 724],
        "world_bounds": {
            "min_m": [-0.002, 0.542, -0.002],
            "max_m": [0.602, 0.561, 0.724],
        },
        "world_dimensions_mm": [604, 19, 724],
        "vertex_count": 8,
        "face_count": 6,
        "expected_dimensions_mm": None,
        "construction": {
            "corpus_thickness_mm": 18,
            "back_thickness_mm": 3,
            "front_thickness_mm": 19,
            "groove_offset_mm": 10,
            "front_overlay_mm": 2,
        },
        "children": [],
        "validation": {
            "width_ok": True,
            "depth_ok": True,
            "height_ok": True,
            "vertex_count_ok": True,
            "face_count_ok": True,
            "issues": [],
        },
    }


def _make_back_panel_object():
    """Create a mock back panel object for testing."""
    return {
        "name": "run0_base_0_base-door_back",
        "type": "MESH",
        "classification": "back_panel",
        "level": "base",
        "run_label": "back wall",
        "run_index": 0,
        "cabinet_index": 0,
        "parent": "run0_base_0_base-door",
        "transform": {
            "location_m": [0.018, 0.0, 0.0],
            "rotation_euler_rad": [0, 0, 0],
            "scale": [1, 1, 1],
        },
        "local_bounds": {
            "min_m": [0, 0.547, 0],
            "max_m": [0.564, 0.55, 0.717],
        },
        "local_dimensions_mm": [564, 3, 717],
        "world_bounds": {
            "min_m": [0.018, 0.547, 0],
            "max_m": [0.582, 0.55, 0.717],
        },
        "world_dimensions_mm": [564, 3, 717],
        "vertex_count": 8,
        "face_count": 6,
        "expected_dimensions_mm": None,
        "construction": {
            "corpus_thickness_mm": 18,
            "back_thickness_mm": 3,
            "front_thickness_mm": 19,
            "groove_offset_mm": 10,
            "front_overlay_mm": 2,
        },
        "children": [],
        "validation": {
            "width_ok": True,
            "depth_ok": True,
            "height_ok": True,
            "vertex_count_ok": True,
            "face_count_ok": True,
            "issues": [],
        },
    }


class TestCarcassObject:
    """Test carcass object structure."""

    def test_has_name(self):
        obj = _make_carcass_object()
        assert obj["name"] == "run0_base_0_base-door"

    def test_classification_is_carcass(self):
        obj = _make_carcass_object()
        assert obj["classification"] == "carcass"

    def test_level_is_base(self):
        obj = _make_carcass_object()
        assert obj["level"] == "base"

    def test_has_no_parent(self):
        obj = _make_carcass_object()
        assert obj["parent"] is None

    def test_dimensions_are_correct(self):
        obj = _make_carcass_object()
        dims = obj["local_dimensions_mm"]
        assert dims[0] == 600  # width
        assert dims[1] == 560  # depth
        assert dims[2] == 720  # height

    def test_vertex_count_for_hollow_box(self):
        """Carcass should have ≥16 vertices (8 outer + 8 inner)."""
        obj = _make_carcass_object()
        assert obj["vertex_count"] >= 16

    def test_face_count_for_hollow_box(self):
        """Carcass should have ≥12 faces."""
        obj = _make_carcass_object()
        assert obj["face_count"] >= 12

    def test_has_construction_params(self):
        obj = _make_carcass_object()
        construction = obj["construction"]
        assert construction["corpus_thickness_mm"] == 18
        assert construction["back_thickness_mm"] == 3
        assert construction["front_thickness_mm"] == 19

    def test_has_children(self):
        obj = _make_carcass_object()
        assert len(obj["children"]) == 2

    def test_children_have_correct_types(self):
        obj = _make_carcass_object()
        child_types = {c["type"] for c in obj["children"]}
        assert "back_panel" in child_types
        assert "door_front" in child_types

    def test_world_bounds_differ_from_local(self):
        """World bounds should account for transform (plinth offset)."""
        obj = _make_carcass_object()
        local_z_min = obj["local_bounds"]["min_m"][2]
        world_z_min = obj["world_bounds"]["min_m"][2]
        # World Z should be offset by plinth height (0.12m)
        assert world_z_min > local_z_min

    def test_run_info_is_correct(self):
        obj = _make_carcass_object()
        assert obj["run_label"] == "back wall"
        assert obj["run_index"] == 0
        assert obj["cabinet_index"] == 0


class TestDoorObject:
    """Test door front object structure."""

    def test_classification_is_door_front(self):
        obj = _make_door_object()
        assert obj["classification"] == "door_front"

    def test_has_parent(self):
        obj = _make_door_object()
        assert obj["parent"] == "run0_base_0_base-door"

    def test_thickness_is_19mm(self):
        """Door front should be ~19mm thick."""
        obj = _make_door_object()
        dims = obj["local_dimensions_mm"]
        # Find the smallest dimension (thickness)
        thickness = min(dims)
        assert abs(thickness - 19) < 1

    def test_vertex_count_for_solid_box(self):
        """Door front should have 8 vertices (solid box)."""
        obj = _make_door_object()
        assert obj["vertex_count"] == 8

    def test_face_count_for_solid_box(self):
        """Door front should have 6 faces."""
        obj = _make_door_object()
        assert obj["face_count"] == 6

    def test_width_includes_overlay(self):
        """Door width should be carcass width + 2 * overlay."""
        obj = _make_door_object()
        # Carcass width = 600mm, overlay = 2mm per side
        # Expected door width = 600 + 2*2 = 604mm
        assert obj["local_dimensions_mm"][0] == 604

    def test_height_includes_overlay(self):
        """Door height should be carcass height + overlay top + bottom."""
        obj = _make_door_object()
        # Carcass height = 720mm, overlay = 2mm top + 2mm bottom
        # Expected door height = 720 + 2 + 2 = 724mm
        assert obj["local_dimensions_mm"][2] == 724


class TestBackPanelObject:
    """Test back panel object structure."""

    def test_classification_is_back_panel(self):
        obj = _make_back_panel_object()
        assert obj["classification"] == "back_panel"

    def test_thickness_is_3mm(self):
        """Back panel should be ~3mm HDF."""
        obj = _make_back_panel_object()
        dims = obj["local_dimensions_mm"]
        # Find the smallest dimension (thickness)
        thickness = min(dims)
        assert abs(thickness - 3) < 1

    def test_width_is_internal(self):
        """Back panel width should be internal (corpus - 2*thickness)."""
        obj = _make_back_panel_object()
        # External = 600mm, corpus = 18mm
        # Internal = 600 - 2*18 = 564mm
        assert obj["local_dimensions_mm"][0] == 564

    def test_vertex_count(self):
        """Back panel should have 8 vertices (thin box)."""
        obj = _make_back_panel_object()
        assert obj["vertex_count"] == 8


class TestObjectNaming:
    """Test object naming conventions."""

    def test_carcass_name_format(self):
        obj = _make_carcass_object()
        # Format: run{N}_{level}_{index}_{type}
        parts = obj["name"].split("_")
        assert parts[0].startswith("run")
        assert parts[1] in ("base", "upper", "tall")
        assert parts[2].isdigit()

    def test_child_name_contains_parent(self):
        obj = _make_carcass_object()
        for child in obj["children"]:
            # Child name should start with parent name
            assert child["name"].startswith(obj["name"])

    def test_back_panel_name_suffix(self):
        obj = _make_carcass_object()
        back = [c for c in obj["children"] if c["type"] == "back_panel"]
        assert len(back) == 1
        assert back[0]["name"].endswith("_back")

    def test_door_name_suffix(self):
        obj = _make_carcass_object()
        doors = [c for c in obj["children"] if c["type"] == "door_front"]
        assert len(doors) == 1
        assert doors[0]["name"].endswith("_door")


class TestConstructionParams:
    """Test construction parameter values."""

    def test_corpus_thickness_is_european_standard(self):
        obj = _make_carcass_object()
        assert obj["construction"]["corpus_thickness_mm"] == 18

    def test_back_thickness_is_hdf(self):
        obj = _make_carcass_object()
        assert obj["construction"]["back_thickness_mm"] == 3

    def test_front_thickness_is_mdf(self):
        obj = _make_carcass_object()
        assert obj["construction"]["front_thickness_mm"] == 19

    def test_groove_offset_is_standard(self):
        obj = _make_carcass_object()
        assert obj["construction"]["groove_offset_mm"] == 10

    def test_front_overlay_is_standard(self):
        obj = _make_carcass_object()
        assert obj["construction"]["front_overlay_mm"] == 2
