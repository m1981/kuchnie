"""Wall Builder Tests.

Converts config (runs with directions) to wall-based representation.

The wall_builder module bridges the gap between:
- Config format (runs with turn directions)
- Wall model (walls with start/end points)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest


# ─── Config to Wall Conversion Tests ──────────────────────────────────────────

class TestConfigToWalls:
    """Test conversion from config runs to Wall objects."""

    def test_single_run_creates_one_wall(self):
        """Single I-shape run creates one wall."""
        from src.wall_builder import config_to_walls

        config = {
            "settings": {"cabinetGap": 0},
            "runs": [
                {
                    "label": "back wall",
                    "base": [
                        {"type": "base-door", "width": 600},
                        {"type": "base-door", "width": 600},
                    ],
                }
            ],
        }

        room = config_to_walls(config)
        assert len(room.walls) == 1
        assert room.walls[0].id == "back wall"

    def test_single_run_wall_length(self):
        """Wall length = sum of cabinet widths + gaps."""
        from src.wall_builder import config_to_walls

        config = {
            "settings": {"cabinetGap": 0},
            "runs": [
                {
                    "label": "back wall",
                    "base": [
                        {"type": "base-door", "width": 600},
                        {"type": "base-door", "width": 800},
                    ],
                }
            ],
        }

        room = config_to_walls(config)
        assert room.walls[0].length == 1400  # 600 + 800

    def test_single_run_wall_direction_east(self):
        """First run goes east (+X) by default."""
        from src.wall_builder import config_to_walls

        config = {
            "settings": {},
            "runs": [
                {
                    "label": "back wall",
                    "base": [{"type": "base-door", "width": 600}],
                }
            ],
        }

        room = config_to_walls(config)
        wall = room.walls[0]
        d = wall.direction
        assert abs(d.x - 1.0) < 1e-6  # east
        assert abs(d.y) < 1e-6

    def test_two_runs_creates_two_walls(self):
        """L-shape creates two walls."""
        from src.wall_builder import config_to_walls

        config = {
            "settings": {"cabinetGap": 0},
            "runs": [
                {
                    "label": "back wall",
                    "base": [{"type": "base-door", "width": 600}],
                },
                {
                    "label": "left wall",
                    "turn": "left",
                    "base": [{"type": "base-door", "width": 500}],
                },
            ],
        }

        room = config_to_walls(config)
        assert len(room.walls) == 2
        assert room.walls[0].id == "back wall"
        assert room.walls[1].id == "left wall"

    def test_l_shape_second_wall_direction(self):
        """L-shape: second wall turns left from first."""
        from src.wall_builder import config_to_walls

        config = {
            "settings": {"cabinetGap": 0},
            "runs": [
                {
                    "label": "back wall",
                    "base": [{"type": "base-door", "width": 600}],
                },
                {
                    "label": "left wall",
                    "turn": "left",
                    "base": [{"type": "base-door", "width": 500}],
                },
            ],
        }

        room = config_to_walls(config)
        wall = room.walls[1]
        d = wall.direction
        # Left turn from east = north
        assert abs(d.x) < 1e-6
        assert abs(d.y - 1.0) < 1e-6  # north

    def test_l_shape_second_wall_starts_at_corner(self):
        """L-shape: second wall starts where first wall ends."""
        from src.wall_builder import config_to_walls

        config = {
            "settings": {"cabinetGap": 0},
            "runs": [
                {
                    "label": "back wall",
                    "base": [{"type": "base-door", "width": 600}],
                },
                {
                    "label": "left wall",
                    "turn": "left",
                    "base": [{"type": "base-door", "width": 500}],
                },
            ],
        }

        room = config_to_walls(config)
        back_end = room.walls[0].end
        left_start = room.walls[1].start

        assert abs(back_end.x - left_start.x) < 1e-6
        assert abs(back_end.y - left_start.y) < 1e-6

    def test_u_shape_three_walls(self):
        """U-shape creates three walls."""
        from src.wall_builder import config_to_walls

        config = {
            "settings": {"cabinetGap": 0},
            "runs": [
                {"label": "left", "base": [{"type": "base-door", "width": 600}]},
                {"label": "back", "turn": "right", "base": [{"type": "base-door", "width": 800}]},
                {"label": "right", "turn": "right", "base": [{"type": "base-door", "width": 600}]},
            ],
        }

        room = config_to_walls(config)
        assert len(room.walls) == 3


# ─── Config to Cabinets Conversion Tests ─────────────────────────────────────

class TestConfigToCabinets:
    """Test conversion from config cabinets to WallCabinet objects."""

    def test_single_cabinet_conversion(self):
        """One base-door becomes one WallCabinet."""
        from src.wall_builder import config_to_cabinets

        config = {
            "settings": {"cabinetGap": 0},
            "runs": [
                {
                    "label": "back wall",
                    "base": [
                        {"type": "base-door", "width": 600, "depth": 560, "height": 720},
                    ],
                }
            ],
        }

        cabinets = config_to_cabinets(config)
        assert len(cabinets) == 1
        assert cabinets[0].wall_id == "back wall"
        assert cabinets[0].offset == 0
        assert cabinets[0].width == 600

    def test_two_cabinets_offset(self):
        """Second cabinet offset = first width + gap."""
        from src.wall_builder import config_to_cabinets

        config = {
            "settings": {"cabinetGap": 0},
            "runs": [
                {
                    "label": "back wall",
                    "base": [
                        {"type": "base-door", "width": 600},
                        {"type": "base-door", "width": 400},
                    ],
                }
            ],
        }

        cabinets = config_to_cabinets(config)
        assert len(cabinets) == 2
        assert cabinets[0].offset == 0
        assert cabinets[1].offset == 600

    def test_cabinet_depth_from_settings(self):
        """Cabinet depth comes from settings based on cabinet type."""
        from src.wall_builder import config_to_cabinets

        config = {
            "settings": {"baseDepth": 560, "wallDepth": 300, "cabinetGap": 0},
            "runs": [
                {
                    "label": "back",
                    "base": [{"type": "base-door", "width": 600}],
                    "upper": [{"type": "wall-door", "width": 600}],
                }
            ],
        }

        cabinets = config_to_cabinets(config)
        # First cabinet is base (560mm), second is upper (300mm)
        assert cabinets[0].depth == 560
        assert cabinets[1].depth == 300

    def test_upper_cabinets_same_wall(self):
        """Upper cabinets are on the same wall as base."""
        from src.wall_builder import config_to_cabinets

        config = {
            "settings": {"baseDepth": 560, "wallDepth": 300, "cabinetGap": 0},
            "runs": [
                {
                    "label": "back",
                    "base": [{"type": "base-door", "width": 600}],
                    "upper": [{"type": "wall-door", "width": 600}],
                }
            ],
        }

        cabinets = config_to_cabinets(config)
        wall_ids = set(c.wall_id for c in cabinets)
        assert len(wall_ids) == 1  # All on same wall


# ─── Corner Cabinet Detection Tests ──────────────────────────────────────────

class TestCornerCabinetDetection:
    """Test detection of corner cabinets in config."""

    def test_corner_cabinet_detected(self):
        """Corner-blind at end of run creates CornerCabinet."""
        from src.wall_builder import config_to_corners

        config = {
            "settings": {},
            "runs": [
                {
                    "label": "back wall",
                    "base": [
                        {"type": "base-door", "width": 600},
                        {"type": "corner-blind", "width": 900, "blindDepth": 400, "blindSide": "right"},
                    ],
                },
                {
                    "label": "left wall",
                    "turn": "left",
                    "base": [{"type": "base-door", "width": 600}],
                },
            ],
        }

        corners = config_to_corners(config)
        assert len(corners) == 1
        assert corners[0].primary_wall_id == "back wall"
        assert corners[0].secondary_wall_id == "left wall"
        assert corners[0].blind_depth == 400

    def test_u_shape_two_corners(self):
        """U-shape has two corner cabinets."""
        from src.wall_builder import config_to_corners

        config = {
            "settings": {},
            "runs": [
                {
                    "label": "left",
                    "base": [
                        {"type": "corner-blind", "width": 900, "blindDepth": 400, "blindSide": "right"},
                    ],
                },
                {
                    "label": "back",
                    "turn": "right",
                    "base": [{"type": "base-door", "width": 600}],
                },
                {
                    "label": "right",
                    "turn": "right",
                    "base": [
                        {"type": "corner-blind", "width": 900, "blindDepth": 400, "blindSide": "left"},
                    ],
                },
            ],
        }

        corners = config_to_corners(config)
        assert len(corners) == 2


# ─── Integration: Full Pipeline Tests ─────────────────────────────────────────

class TestFullPipeline:
    """Test the complete config → walls → positions pipeline."""

    def test_i_shape_all_cabinets_positioned(self):
        """I-shape: all cabinets get world positions."""
        from src.wall_builder import build_layout

        config = {
            "settings": {"baseDepth": 560, "wallDepth": 300, "cabinetGap": 0},
            "runs": [
                {
                    "label": "back",
                    "base": [
                        {"type": "base-door", "width": 600},
                        {"type": "base-door", "width": 600},
                    ],
                }
            ],
        }

        layout = build_layout(config)
        assert len(layout.cabinets) == 2
        for cab in layout.cabinets:
            assert cab.world_x is not None
            assert cab.world_y is not None

    def test_l_shape_cabinets_on_different_walls(self):
        """L-shape: cabinets distributed across two walls."""
        from src.wall_builder import build_layout

        config = {
            "settings": {"baseDepth": 560, "cabinetGap": 0},
            "runs": [
                {
                    "label": "back",
                    "base": [
                        {"type": "base-door", "width": 600},
                        {"type": "corner-blind", "width": 900, "blindDepth": 400, "blindSide": "right"},
                    ],
                },
                {
                    "label": "left",
                    "turn": "left",
                    "base": [{"type": "base-door", "width": 600}],
                },
            ],
        }

        layout = build_layout(config)
        back_cabs = [c for c in layout.cabinets if c.wall_id == "back"]
        left_cabs = [c for c in layout.cabinets if c.wall_id == "left"]

        assert len(back_cabs) == 2
        assert len(left_cabs) == 1
