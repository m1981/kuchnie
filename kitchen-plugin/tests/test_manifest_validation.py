"""Tests for manifest validation logic.

Verifies dimension checks, overlap detection, clearance checks,
and other validation rules. Uses mock data — no Blender dependency.
"""

import pytest
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from manifest_validator import (
    validate_manifest,
    check_dimensions,
    check_overlaps,
    check_vertex_face_counts,
    check_standard_widths,
    check_run_continuity,
    check_construction,
    ValidationResult,
    Issue,
)


def _make_manifest_with_issues():
    """Create a manifest with known issues for testing."""
    return {
        "format": "kitchen-geometry-manifest",
        "version": "2.0",
        "units": "meters",
        "coordinate_system": {"type": "Z-up", "handedness": "right"},
        "settings": {
            "baseBodyHeight": 720,
            "baseDepth": 560,
            "corpusThickness": 18,
            "backThickness": 3,
            "frontThickness": 19,
        },
        "layout": {
            "type": "I-shape",
            "run_count": 1,
            "total_cabinets": 1,
            "runs": [
                {
                    "label": "back wall",
                    "index": 0,
                    "direction": "east",
                    "turn": None,
                    "start_position_mm": [0, 0],
                    "end_position_mm": [600, 0],
                    "total_width_mm": 600,
                    "cabinet_count": 1,
                    "cabinets": ["run0_base_0_base-door"],
                }
            ],
        },
        "objects": [
            {
                "name": "run0_base_0_base-door",
                "type": "MESH",
                "classification": "carcass",
                "level": "base",
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
        ],
        "validation_summary": {
            "total_objects": 1,
            "total_vertices": 16,
            "total_faces": 12,
            "passed": 1,
            "failed": 0,
            "warnings": 0,
            "issues": [],
        },
    }


class TestDimensionChecks:
    """Test dimension validation."""

    def test_dimensions_within_tolerance_pass(self):
        obj = {
            "name": "test_cabinet",
            "local_dimensions_mm": [600, 560, 720],
            "expected_dimensions_mm": {"width": 600, "depth": 560, "height": 720},
        }
        issues = check_dimensions(obj, tolerance_mm=2.0)
        assert len(issues) == 0

    def test_dimensions_outside_tolerance_fail(self):
        obj = {
            "name": "test_cabinet",
            "local_dimensions_mm": [600, 540, 720],  # depth is 20mm off
            "expected_dimensions_mm": {"width": 600, "depth": 560, "height": 720},
        }
        issues = check_dimensions(obj, tolerance_mm=2.0)
        assert len(issues) == 1
        assert issues[0].severity == "error"
        assert issues[0].check == "depth"

    def test_dimensions_at_tolerance_boundary_pass(self):
        obj = {
            "name": "test_cabinet",
            "local_dimensions_mm": [602, 558, 722],  # all within 2mm
            "expected_dimensions_mm": {"width": 600, "depth": 560, "height": 720},
        }
        issues = check_dimensions(obj, tolerance_mm=2.0)
        assert len(issues) == 0

    def test_dimensions_with_none_expected_skip(self):
        """Dimensions with None expected should be skipped."""
        obj = {
            "name": "test_cabinet",
            "local_dimensions_mm": [600, 560, 720],
            "expected_dimensions_mm": {"width": None, "depth": 560, "height": None},
        }
        issues = check_dimensions(obj, tolerance_mm=2.0)
        # Only depth is checked
        assert len(issues) == 0

    def test_no_expected_dimensions_skip(self):
        """Objects without expected dimensions should be skipped."""
        obj = {
            "name": "test_cabinet",
            "local_dimensions_mm": [600, 560, 720],
            "expected_dimensions_mm": None,
        }
        issues = check_dimensions(obj, tolerance_mm=2.0)
        assert len(issues) == 0

    def test_width_mismatch_detected(self):
        obj = {
            "name": "test_cabinet",
            "local_dimensions_mm": [610, 560, 720],  # width 10mm off
            "expected_dimensions_mm": {"width": 600, "depth": 560, "height": 720},
        }
        issues = check_dimensions(obj, tolerance_mm=2.0)
        assert any(i.check == "width" for i in issues)


class TestOverlapChecks:
    """Test overlap detection."""

    def test_no_overlap_pass(self):
        objects = [
            {
                "name": "cabinet_1",
                "classification": "carcass",
                "world_bounds": {
                    "min_m": [0, 0, 0],
                    "max_m": [0.6, 0.56, 0.72],
                },
            },
            {
                "name": "cabinet_2",
                "classification": "carcass",
                "world_bounds": {
                    "min_m": [0.6, 0, 0],  # Starts where cabinet_1 ends
                    "max_m": [1.2, 0.56, 0.72],
                },
            },
        ]
        issues = check_overlaps(objects, tolerance_mm=0.0)
        assert len(issues) == 0

    def test_overlap_detected(self):
        objects = [
            {
                "name": "cabinet_1",
                "classification": "carcass",
                "world_bounds": {
                    "min_m": [0, 0, 0],
                    "max_m": [0.65, 0.56, 0.72],  # Extends 650mm
                },
            },
            {
                "name": "cabinet_2",
                "classification": "carcass",
                "world_bounds": {
                    "min_m": [0.6, 0, 0],  # Starts at 600mm
                    "max_m": [1.2, 0.56, 0.72],
                },
            },
        ]
        issues = check_overlaps(objects, tolerance_mm=0.0)
        assert len(issues) == 1
        assert "overlap" in issues[0].message.lower()

    def test_fronts_skipped_in_overlap_check(self):
        """Fronts should not be checked for overlaps."""
        objects = [
            {
                "name": "cabinet_1_door",
                "classification": "door_front",
                "world_bounds": {
                    "min_m": [0, 0, 0],
                    "max_m": [1.0, 1.0, 1.0],
                },
            },
            {
                "name": "cabinet_2_door",
                "classification": "door_front",
                "world_bounds": {
                    "min_m": [0, 0, 0],
                    "max_m": [1.0, 1.0, 1.0],
                },
            },
        ]
        issues = check_overlaps(objects, tolerance_mm=0.0)
        assert len(issues) == 0

    def test_different_heights_no_overlap(self):
        """Objects at different heights don't overlap."""
        objects = [
            {
                "name": "base_cabinet",
                "classification": "carcass",
                "world_bounds": {
                    "min_m": [0, 0, 0],
                    "max_m": [0.6, 0.56, 0.84],
                },
            },
            {
                "name": "wall_cabinet",
                "classification": "carcass",
                "world_bounds": {
                    "min_m": [0, 0, 1.4],  # Wall-mounted at 1400mm
                    "max_m": [0.6, 0.3, 2.0],
                },
            },
        ]
        issues = check_overlaps(objects, tolerance_mm=0.0)
        assert len(issues) == 0


class TestVertexFaceChecks:
    """Test vertex and face count validation."""

    def test_carcass_with_enough_vertices_pass(self):
        obj = {"name": "test", "classification": "carcass", "vertex_count": 16, "face_count": 12}
        issues = check_vertex_face_counts(obj)
        assert not any(i.severity == "warning" for i in issues)

    def test_carcass_with_too_few_vertices_warn(self):
        obj = {"name": "test", "classification": "carcass", "vertex_count": 4, "face_count": 6}
        issues = check_vertex_face_counts(obj)
        assert any(i.severity == "warning" and i.check == "vertex_count" for i in issues)

    def test_board_with_8_vertices_pass(self):
        obj = {"name": "test_left", "classification": "board", "vertex_count": 8, "face_count": 6}
        issues = check_vertex_face_counts(obj)
        assert not any(i.severity == "warning" for i in issues)

    def test_door_with_8_vertices_pass(self):
        obj = {"name": "test", "classification": "door_front", "vertex_count": 8, "face_count": 6}
        issues = check_vertex_face_counts(obj)
        assert not any(i.severity == "warning" for i in issues)

    def test_door_with_4_vertices_warn(self):
        obj = {"name": "test", "classification": "door_front", "vertex_count": 4, "face_count": 6}
        issues = check_vertex_face_counts(obj)
        assert any(i.severity == "warning" and i.check == "vertex_count" for i in issues)

    def test_zero_vertices_skipped_for_empty_parent(self):
        obj = {"name": "test", "classification": "carcass", "vertex_count": 0, "face_count": 0}
        issues = check_vertex_face_counts(obj)
        # Empty parent (0 vertices) — skip checks, no error
        assert len(issues) == 0

    def test_vertices_but_no_faces_error(self):
        obj = {"name": "test", "classification": "carcass", "vertex_count": 16, "face_count": 0}
        issues = check_vertex_face_counts(obj)
        assert any(i.severity == "error" and i.check == "face_count" for i in issues)


class TestStandardWidthChecks:
    """Test standard width validation."""

    def test_standard_width_600_pass(self):
        obj = {"name": "test", "classification": "carcass", "local_dimensions_mm": [600, 560, 720]}
        settings = {}
        issues = check_standard_widths(obj, settings)
        assert len(issues) == 0

    def test_standard_width_400_pass(self):
        obj = {"name": "test", "classification": "carcass", "local_dimensions_mm": [400, 560, 720]}
        settings = {}
        issues = check_standard_widths(obj, settings)
        assert len(issues) == 0

    def test_non_standard_width_warn(self):
        obj = {"name": "test", "classification": "carcass", "local_dimensions_mm": [550, 560, 720]}
        settings = {}
        issues = check_standard_widths(obj, settings)
        assert len(issues) == 1
        assert issues[0].severity == "warning"

    def test_non_carcass_skipped(self):
        obj = {"name": "test", "classification": "door_front", "local_dimensions_mm": [604, 19, 724]}
        settings = {}
        issues = check_standard_widths(obj, settings)
        assert len(issues) == 0


class TestRunContinuityChecks:
    """Test run direction continuity."""

    def test_i_shape_no_turns_pass(self):
        layout = {
            "runs": [
                {"label": "wall1", "index": 0, "direction": "east", "turn": None,
                 "start_position_mm": [0, 0], "end_position_mm": [3000, 0]},
            ]
        }
        issues = check_run_continuity(layout)
        assert len(issues) == 0

    def test_l_shape_correct_turn_pass(self):
        layout = {
            "runs": [
                {"label": "wall1", "index": 0, "direction": "east", "turn": None,
                 "start_position_mm": [0, 0], "end_position_mm": [3000, 0]},
                {"label": "wall2", "index": 1, "direction": "south", "turn": "right",
                 "start_position_mm": [3000, 0], "end_position_mm": [3000, -2000]},
            ]
        }
        issues = check_run_continuity(layout)
        assert len(issues) == 0

    def test_position_mismatch_fail(self):
        layout = {
            "runs": [
                {"label": "wall1", "index": 0, "direction": "east", "turn": None,
                 "start_position_mm": [0, 0], "end_position_mm": [3000, 0]},
                {"label": "wall2", "index": 1, "direction": "south", "turn": "right",
                 "start_position_mm": [3050, 0], "end_position_mm": [3050, -2000]},  # 50mm gap
            ]
        }
        issues = check_run_continuity(layout)
        assert len(issues) == 1
        assert "continuity" in issues[0].check

    def test_wrong_direction_fail(self):
        layout = {
            "runs": [
                {"label": "wall1", "index": 0, "direction": "east", "turn": None,
                 "start_position_mm": [0, 0], "end_position_mm": [3000, 0]},
                {"label": "wall2", "index": 1, "direction": "north", "turn": "right",
                 "start_position_mm": [3000, 0], "end_position_mm": [3000, 2000]},
                # "right" from east should give "south", not "north"
            ]
        }
        issues = check_run_continuity(layout)
        assert any(i.check == "direction" for i in issues)


class TestConstructionChecks:
    """Test construction parameter validation."""

    def test_thick_back_panel_warn(self):
        obj = {
            "name": "test_back",
            "classification": "back_panel",
            "local_dimensions_mm": [564, 20, 717],  # 20mm is too thick
        }
        settings = {"backThickness": 3}
        issues = check_construction(obj, settings)
        assert any(i.severity == "warning" and i.check == "back_thickness" for i in issues)

    def test_thin_front_warn(self):
        obj = {
            "name": "test_door",
            "classification": "door_front",
            "local_dimensions_mm": [604, 5, 724],  # 5mm is too thin
        }
        settings = {"frontThickness": 19}
        issues = check_construction(obj, settings)
        assert any(i.severity == "warning" and i.check == "front_thickness" for i in issues)


class TestFullValidation:
    """Test full manifest validation."""

    def test_valid_manifest_passes(self):
        manifest = _make_manifest_with_issues()
        result = validate_manifest(manifest)
        assert result.is_valid

    def test_validation_result_counts(self):
        manifest = _make_manifest_with_issues()
        result = validate_manifest(manifest)
        assert result.total_objects == 1
        assert result.passed == 1
        assert result.failed == 0

    def test_validation_result_to_dict(self):
        manifest = _make_manifest_with_issues()
        result = validate_manifest(manifest)
        d = result.to_dict()
        assert "total_objects" in d
        assert "passed" in d
        assert "failed" in d
        assert "is_valid" in d
        assert "issues" in d
