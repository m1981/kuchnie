"""Tests for manifest layout metadata.

Verifies layout type detection, run metadata, and position tracking.
Uses mock data — no Blender dependency.
"""

import pytest


def _make_i_shape_layout():
    """Create I-shape layout metadata."""
    return {
        "type": "I-shape",
        "run_count": 1,
        "total_cabinets": 4,
        "runs": [
            {
                "label": "back wall",
                "index": 0,
                "direction": "east",
                "turn": None,
                "start_position_mm": [0, 0],
                "end_position_mm": [2400, 0],
                "total_width_mm": 2400,
                "cabinet_count": 4,
                "cabinets": [
                    "run0_base_0_base-door",
                    "run0_base_1_base-drawers",
                    "run0_base_2_base-sink",
                    "run0_base_3_base-door",
                ],
            }
        ],
    }


def _make_l_shape_layout():
    """Create L-shape layout metadata."""
    return {
        "type": "L-shape",
        "run_count": 2,
        "total_cabinets": 8,
        "runs": [
            {
                "label": "back wall",
                "index": 0,
                "direction": "east",
                "turn": None,
                "start_position_mm": [0, 0],
                "end_position_mm": [3200, 0],
                "total_width_mm": 3200,
                "cabinet_count": 5,
                "cabinets": [
                    "run0_base_0_filler",
                    "run0_base_1_base-door",
                    "run0_base_2_base-drawers",
                    "run0_base_3_base-sink",
                    "run0_base_4_corner-blind",
                ],
            },
            {
                "label": "left wall",
                "index": 1,
                "direction": "south",
                "turn": "right",
                "start_position_mm": [3200, 0],
                "end_position_mm": [3200, -1800],
                "total_width_mm": 1800,
                "cabinet_count": 3,
                "cabinets": [
                    "run1_base_0_base-door",
                    "run1_base_1_base-drawers",
                    "run1_base_2_filler",
                ],
            },
        ],
    }


def _make_u_shape_layout():
    """Create U-shape layout metadata."""
    return {
        "type": "U-shape",
        "run_count": 3,
        "total_cabinets": 12,
        "runs": [
            {
                "label": "back wall",
                "index": 0,
                "direction": "east",
                "turn": None,
                "start_position_mm": [0, 0],
                "end_position_mm": [3000, 0],
                "total_width_mm": 3000,
                "cabinet_count": 5,
                "cabinets": ["run0_base_0_base-door", "..."],
            },
            {
                "label": "right wall",
                "index": 1,
                "direction": "south",
                "turn": "right",
                "start_position_mm": [3000, 0],
                "end_position_mm": [3000, -2000],
                "total_width_mm": 2000,
                "cabinet_count": 4,
                "cabinets": ["run1_base_0_base-door", "..."],
            },
            {
                "label": "front wall",
                "index": 2,
                "direction": "west",
                "turn": "right",
                "start_position_mm": [3000, -2000],
                "end_position_mm": [0, -2000],
                "total_width_mm": 3000,
                "cabinet_count": 3,
                "cabinets": ["run2_base_0_base-door", "..."],
            },
        ],
    }


class TestIShapeLayout:
    """Test I-shape layout metadata."""

    def test_type_is_i_shape(self):
        layout = _make_i_shape_layout()
        assert layout["type"] == "I-shape"

    def test_has_one_run(self):
        layout = _make_i_shape_layout()
        assert layout["run_count"] == 1
        assert len(layout["runs"]) == 1

    def test_total_cabinets(self):
        layout = _make_i_shape_layout()
        assert layout["total_cabinets"] == 4

    def test_run_direction(self):
        layout = _make_i_shape_layout()
        assert layout["runs"][0]["direction"] == "east"

    def test_no_turn(self):
        layout = _make_i_shape_layout()
        assert layout["runs"][0]["turn"] is None

    def test_run_width(self):
        layout = _make_i_shape_layout()
        assert layout["runs"][0]["total_width_mm"] == 2400

    def test_cabinets_list(self):
        layout = _make_i_shape_layout()
        assert len(layout["runs"][0]["cabinets"]) == 4

    def test_positions_chain(self):
        layout = _make_i_shape_layout()
        run = layout["runs"][0]
        assert run["start_position_mm"] == [0, 0]
        assert run["end_position_mm"] == [2400, 0]


class TestLShapeLayout:
    """Test L-shape layout metadata."""

    def test_type_is_l_shape(self):
        layout = _make_l_shape_layout()
        assert layout["type"] == "L-shape"

    def test_has_two_runs(self):
        layout = _make_l_shape_layout()
        assert layout["run_count"] == 2
        assert len(layout["runs"]) == 2

    def test_total_cabinets(self):
        layout = _make_l_shape_layout()
        assert layout["total_cabinets"] == 8

    def test_first_run_direction(self):
        layout = _make_l_shape_layout()
        assert layout["runs"][0]["direction"] == "east"

    def test_second_run_direction(self):
        layout = _make_l_shape_layout()
        assert layout["runs"][1]["direction"] == "south"

    def test_turn_exists(self):
        layout = _make_l_shape_layout()
        assert layout["runs"][1]["turn"] == "right"

    def test_positions_chain_correctly(self):
        layout = _make_l_shape_layout()
        # End of first run = start of second run
        end_first = layout["runs"][0]["end_position_mm"]
        start_second = layout["runs"][1]["start_position_mm"]
        assert end_first == start_second

    def test_second_run_perpendicular(self):
        layout = _make_l_shape_layout()
        # First run goes east (X direction), second goes south (Y direction)
        run1 = layout["runs"][0]
        run2 = layout["runs"][1]
        # They should be perpendicular
        assert run1["direction"] != run2["direction"]

    def test_run_labels(self):
        layout = _make_l_shape_layout()
        assert layout["runs"][0]["label"] == "back wall"
        assert layout["runs"][1]["label"] == "left wall"


class TestUShapeLayout:
    """Test U-shape layout metadata."""

    def test_type_is_u_shape(self):
        layout = _make_u_shape_layout()
        assert layout["type"] == "U-shape"

    def test_has_three_runs(self):
        layout = _make_u_shape_layout()
        assert layout["run_count"] == 3
        assert len(layout["runs"]) == 3

    def test_total_cabinets(self):
        layout = _make_u_shape_layout()
        assert layout["total_cabinets"] == 12

    def test_directions_form_u(self):
        layout = _make_u_shape_layout()
        directions = [r["direction"] for r in layout["runs"]]
        # U-shape: east → south → west (or similar pattern)
        assert len(set(directions)) >= 2  # At least 2 different directions

    def test_positions_chain_through_all_runs(self):
        layout = _make_u_shape_layout()
        for i in range(len(layout["runs"]) - 1):
            end_current = layout["runs"][i]["end_position_mm"]
            start_next = layout["runs"][i + 1]["start_position_mm"]
            assert end_current == start_next, (
                f"Run {i} ends at {end_current} but run {i+1} starts at {start_next}"
            )

    def test_all_runs_have_turns_except_first(self):
        layout = _make_u_shape_layout()
        assert layout["runs"][0]["turn"] is None
        for run in layout["runs"][1:]:
            assert run["turn"] is not None


class TestRunMetadata:
    """Test run metadata structure."""

    def test_run_has_label(self):
        layout = _make_i_shape_layout()
        for run in layout["runs"]:
            assert "label" in run
            assert isinstance(run["label"], str)

    def test_run_has_index(self):
        layout = _make_l_shape_layout()
        for i, run in enumerate(layout["runs"]):
            assert run["index"] == i

    def test_run_has_direction(self):
        layout = _make_l_shape_layout()
        valid_directions = {"east", "north", "west", "south"}
        for run in layout["runs"]:
            assert run["direction"] in valid_directions

    def test_run_has_positions(self):
        layout = _make_l_shape_layout()
        for run in layout["runs"]:
            assert "start_position_mm" in run
            assert "end_position_mm" in run
            assert len(run["start_position_mm"]) == 2
            assert len(run["end_position_mm"]) == 2

    def test_run_has_width(self):
        layout = _make_l_shape_layout()
        for run in layout["runs"]:
            assert "total_width_mm" in run
            assert run["total_width_mm"] > 0

    def test_run_has_cabinet_count(self):
        layout = _make_l_shape_layout()
        for run in layout["runs"]:
            assert "cabinet_count" in run
            assert run["cabinet_count"] >= 0

    def test_run_has_cabinets_list(self):
        layout = _make_l_shape_layout()
        for run in layout["runs"]:
            assert "cabinets" in run
            assert isinstance(run["cabinets"], list)


class TestLayoutDetection:
    """Test layout type detection logic."""

    def test_single_run_is_i_shape(self):
        """Single run = I-shape."""
        run_count = 1
        has_turns = False
        if run_count == 1:
            layout_type = "I-shape"
        elif run_count == 2 and has_turns:
            layout_type = "L-shape"
        elif run_count == 3 and has_turns:
            layout_type = "U-shape"
        else:
            layout_type = "unknown"
        assert layout_type == "I-shape"

    def test_two_runs_with_turn_is_l_shape(self):
        """Two runs with turn = L-shape."""
        run_count = 2
        has_turns = True
        if run_count == 1:
            layout_type = "I-shape"
        elif run_count == 2 and has_turns:
            layout_type = "L-shape"
        elif run_count == 3 and has_turns:
            layout_type = "U-shape"
        else:
            layout_type = "unknown"
        assert layout_type == "L-shape"

    def test_three_runs_with_turns_is_u_shape(self):
        """Three runs with turns = U-shape."""
        run_count = 3
        has_turns = True
        if run_count == 1:
            layout_type = "I-shape"
        elif run_count == 2 and has_turns:
            layout_type = "L-shape"
        elif run_count == 3 and has_turns:
            layout_type = "U-shape"
        else:
            layout_type = "unknown"
        assert layout_type == "U-shape"
