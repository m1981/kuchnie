"""Tests for manifest schema compliance.

Verifies the manifest structure matches the v2.0 schema.
These tests use mock data — no Blender dependency.
"""

import pytest
import json
from pathlib import Path


# Load schema for validation
SCHEMA_PATH = Path(__file__).parent.parent / "schemas" / "manifest_v2.schema.json"


def _load_schema():
    """Load the manifest JSON schema."""
    if SCHEMA_PATH.exists():
        return json.loads(SCHEMA_PATH.read_text())
    return None


def _make_minimal_manifest():
    """Create a minimal valid manifest for testing."""
    return {
        "format": "kitchen-geometry-manifest",
        "version": "2.0",
        "units": "meters",
        "generated_at": "2025-01-01T00:00:00+00:00",
        "source_config": "configs/test.json",
        "coordinate_system": {
            "type": "Z-up",
            "handedness": "right",
            "x": "width (left to right)",
            "y": "depth (into room)",
            "z": "height (up)",
        },
        "settings": {
            "baseBodyHeight": 720,
            "baseDepth": 560,
            "plinthHeight": 120,
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


class TestManifestSchema:
    """Test manifest schema compliance."""

    def test_has_required_top_level_fields(self):
        manifest = _make_minimal_manifest()
        required = [
            "format", "version", "units", "coordinate_system",
            "settings", "layout", "objects", "validation_summary",
        ]
        for field in required:
            assert field in manifest, f"Missing required field: {field}"

    def test_format_is_correct(self):
        manifest = _make_minimal_manifest()
        assert manifest["format"] == "kitchen-geometry-manifest"

    def test_version_is_2(self):
        manifest = _make_minimal_manifest()
        assert manifest["version"] == "2.0"

    def test_units_are_meters(self):
        manifest = _make_minimal_manifest()
        assert manifest["units"] == "meters"

    def test_coordinate_system_is_z_up(self):
        manifest = _make_minimal_manifest()
        cs = manifest["coordinate_system"]
        assert cs["type"] == "Z-up"
        assert cs["handedness"] == "right"

    def test_coordinate_system_has_all_axes(self):
        manifest = _make_minimal_manifest()
        cs = manifest["coordinate_system"]
        assert "x" in cs
        assert "y" in cs
        assert "z" in cs

    def test_layout_has_required_fields(self):
        manifest = _make_minimal_manifest()
        layout = manifest["layout"]
        assert "type" in layout
        assert "run_count" in layout
        assert "total_cabinets" in layout
        assert "runs" in layout

    def test_run_has_required_fields(self):
        manifest = _make_minimal_manifest()
        run = manifest["layout"]["runs"][0]
        required = [
            "label", "index", "direction", "total_width_mm",
            "cabinet_count", "cabinets",
        ]
        for field in required:
            assert field in run, f"Run missing required field: {field}"

    def test_object_has_required_fields(self):
        manifest = _make_minimal_manifest()
        obj = manifest["objects"][0]
        required = [
            "name", "type", "classification", "transform",
            "local_bounds", "local_dimensions_mm",
            "world_bounds", "world_dimensions_mm",
            "vertex_count", "face_count", "validation",
        ]
        for field in required:
            assert field in obj, f"Object missing required field: {field}"

    def test_object_transform_has_required_fields(self):
        manifest = _make_minimal_manifest()
        transform = manifest["objects"][0]["transform"]
        assert "location_m" in transform
        assert "rotation_euler_rad" in transform
        assert "scale" in transform
        assert len(transform["location_m"]) == 3
        assert len(transform["rotation_euler_rad"]) == 3
        assert len(transform["scale"]) == 3

    def test_object_validation_has_required_fields(self):
        manifest = _make_minimal_manifest()
        validation = manifest["objects"][0]["validation"]
        required = [
            "width_ok", "depth_ok", "height_ok",
            "vertex_count_ok", "face_count_ok", "issues",
        ]
        for field in required:
            assert field in validation, f"Validation missing required field: {field}"

    def test_validation_summary_has_required_fields(self):
        manifest = _make_minimal_manifest()
        summary = manifest["validation_summary"]
        required = [
            "total_objects", "total_vertices", "total_faces",
            "passed", "failed", "warnings", "issues",
        ]
        for field in required:
            assert field in summary, f"Summary missing required field: {field}"

    def test_bounds_have_min_max(self):
        manifest = _make_minimal_manifest()
        obj = manifest["objects"][0]
        for bounds_key in ["local_bounds", "world_bounds"]:
            bounds = obj[bounds_key]
            assert "min_m" in bounds, f"{bounds_key} missing min_m"
            assert "max_m" in bounds, f"{bounds_key} missing max_m"
            assert len(bounds["min_m"]) == 3
            assert len(bounds["max_m"]) == 3

    def test_dimensions_are_3_element_arrays(self):
        manifest = _make_minimal_manifest()
        obj = manifest["objects"][0]
        assert len(obj["local_dimensions_mm"]) == 3
        assert len(obj["world_dimensions_mm"]) == 3

    def test_layout_type_is_valid(self):
        manifest = _make_minimal_manifest()
        assert manifest["layout"]["type"] in ["I-shape", "L-shape", "U-shape"]

    def test_direction_is_valid(self):
        manifest = _make_minimal_manifest()
        for run in manifest["layout"]["runs"]:
            assert run["direction"] in ["east", "north", "west", "south"]

    def test_classification_is_valid(self):
        manifest = _make_minimal_manifest()
        valid_classifications = [
            "carcass", "door_front", "drawer_front", "back_panel",
            "countertop", "filler", "plinth", "other",
        ]
        for obj in manifest["objects"]:
            assert obj["classification"] in valid_classifications

    def test_schema_file_exists(self):
        assert SCHEMA_PATH.exists(), f"Schema file not found: {SCHEMA_PATH}"

    def test_schema_is_valid_json(self):
        schema = _load_schema()
        assert schema is not None
        assert "properties" in schema

    def test_schema_defines_required_fields(self):
        schema = _load_schema()
        if schema:
            assert "required" in schema
            assert "format" in schema["required"]
            assert "version" in schema["required"]
            assert "units" in schema["required"]
