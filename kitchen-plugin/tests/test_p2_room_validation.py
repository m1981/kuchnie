"""P2-1: Room Dimension Validation Tests.

PROBLEM: There's no way to specify room dimensions, so the plugin can never
detect when:
- Cabinets exceed wall length
- Corner cabinets overlap with adjacent run
- U-shape left and right walls collide

SOLUTION: Add optional `room` config with wall lengths. Validate that each
run fits its wall, and corner transitions don't overlap.

These tests enforce that impossible layouts are detected BEFORE geometry
generation.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from src.config_parser import _apply_defaults, _validate, load_config
from src.validators import validate_config, compute_total_width


# ─── Room Config Structure Tests ──────────────────────────────────────────────

class TestRoomConfigStructure:
    """Verify that room config is optional and well-structured."""

    def test_room_config_is_optional(self):
        """Config without 'room' key should still load."""
        config = {
            "settings": {},
            "runs": [{"base": [{"type": "base-door", "width": 600}]}],
        }
        _apply_defaults(config)
        _validate(config)  # Should not raise

    def test_room_with_wall_lengths(self):
        """Room config with wall lengths should be accepted."""
        config = {
            "settings": {},
            "room": {
                "walls": [
                    {"length": 3200},
                    {"length": 2400},
                ]
            },
            "runs": [
                {"label": "wall1", "base": [{"type": "base-door", "width": 600}]},
                {"label": "wall2", "turn": "left", "base": [{"type": "base-door", "width": 600}]},
            ],
        }
        _apply_defaults(config)
        _validate(config)  # Should not raise


# ─── Wall Length Validation Tests ─────────────────────────────────────────────

class TestWallLengthValidation:
    """Verify that runs are validated against wall lengths."""

    def test_run_fits_wall(self):
        """Run width exactly equal to wall length should pass."""
        config = {
            "settings": {"cabinetGap": 0},
            "room": {"walls": [{"length": 1200}]},
            "runs": [
                {"label": "wall1", "base": [
                    {"type": "base-door", "width": 600},
                    {"type": "base-door", "width": 600},
                ]},
            ],
        }
        _apply_defaults(config)
        warnings = validate_config(config)
        # No warnings about exceeding wall length
        assert not any("exceeds wall" in w for w in warnings)

    def test_run_exceeds_wall_warns(self):
        """Run width exceeding wall length should warn."""
        config = {
            "settings": {"cabinetGap": 0},
            "room": {"walls": [{"length": 1000}]},
            "runs": [
                {"label": "wall1", "base": [
                    {"type": "base-door", "width": 600},
                    {"type": "base-door", "width": 600},
                ]},
            ],
        }
        _apply_defaults(config)
        warnings = validate_config(config)
        assert any("exceeds wall" in w for w in warnings)

    def test_run_exceeds_wall_by_small_amount_warns(self):
        """Run exceeding wall by even 1mm should warn."""
        config = {
            "settings": {"cabinetGap": 0},
            "room": {"walls": [{"length": 1199}]},
            "runs": [
                {"label": "wall1", "base": [
                    {"type": "base-door", "width": 600},
                    {"type": "base-door", "width": 600},
                ]},
            ],
        }
        _apply_defaults(config)
        warnings = validate_config(config)
        assert any("exceeds wall" in w for w in warnings)


# ─── Multi-Wall Layout Validation Tests ───────────────────────────────────────

class TestMultiWallValidation:
    """Verify that multi-wall layouts are validated."""

    def test_l_shape_fits_room(self):
        """L-shape that fits within room should pass."""
        config = {
            "settings": {"cabinetGap": 0},
            "room": {"walls": [{"length": 3200}, {"length": 2400}]},
            "runs": [
                {
                    "label": "back wall",
                    "base": [
                        {"type": "base-door", "width": 600},
                        {"type": "base-door", "width": 600},
                        {"type": "corner-blind", "width": 900, "blindDepth": 400},
                    ],
                },
                {
                    "label": "left wall",
                    "turn": "left",
                    "base": [
                        {"type": "base-door", "width": 600},
                        {"type": "base-door", "width": 600},
                    ],
                },
            ],
        }
        _apply_defaults(config)
        warnings = validate_config(config)
        # Should not warn about wall length
        assert not any("exceeds wall" in w for w in warnings)

    def test_u_shape_fits_room(self):
        """U-shape that fits within room should pass."""
        config = {
            "settings": {"cabinetGap": 0},
            "room": {"walls": [
                {"length": 2400},
                {"length": 3200},
                {"length": 2400},
            ]},
            "runs": [
                {
                    "label": "left wall",
                    "base": [
                        {"type": "base-door", "width": 600},
                        {"type": "corner-blind", "width": 900, "blindDepth": 400},
                    ],
                },
                {
                    "label": "back wall",
                    "turn": "right",
                    "base": [
                        {"type": "base-door", "width": 600},
                        {"type": "base-door", "width": 600},
                    ],
                },
                {
                    "label": "right wall",
                    "turn": "right",
                    "base": [
                        {"type": "corner-blind", "width": 900, "blindDepth": 400},
                        {"type": "base-door", "width": 600},
                    ],
                },
            ],
        }
        _apply_defaults(config)
        warnings = validate_config(config)
        assert not any("exceeds wall" in w for w in warnings)


# ─── Corner Overlap Detection Tests ───────────────────────────────────────────

class TestCornerOverlapDetection:
    """Verify that corner overlaps are detected."""

    def test_corner_blind_depth_consumes_wall_space(self):
        """Corner blind depth should reduce available space on adjacent wall."""
        config = {
            "settings": {"cabinetGap": 0},
            "room": {"walls": [{"length": 2000}, {"length": 1000}]},
            "runs": [
                {
                    "label": "back wall",
                    "base": [
                        {"type": "base-door", "width": 600},
                        {"type": "corner-blind", "width": 900, "blindDepth": 400},
                    ],
                },
                {
                    "label": "left wall",
                    "turn": "left",
                    "base": [
                        # This wall is 1000mm, but corner consumes 400mm
                        # So only 600mm is available
                        {"type": "base-door", "width": 600},
                        {"type": "base-door", "width": 600},  # This should cause warning
                    ],
                },
            ],
        }
        _apply_defaults(config)
        warnings = validate_config(config)
        # Should warn that left wall run exceeds available space
        assert any("exceeds" in w and "wall" in w.lower() for w in warnings)


# ─── No Room Config Tests ─────────────────────────────────────────────────────

class TestNoRoomConfig:
    """Verify behavior when room config is absent."""

    def test_no_room_no_wall_warnings(self):
        """Without room config, no wall-length warnings should appear."""
        config = {
            "settings": {},
            "runs": [
                {
                    "label": "back wall",
                    "base": [
                        {"type": "base-door", "width": 600},
                        {"type": "base-door", "width": 600},
                        {"type": "base-door", "width": 600},
                    ],
                },
            ],
        }
        _apply_defaults(config)
        warnings = validate_config(config)
        # No wall-length warnings possible without room config
        assert not any("exceeds wall" in w for w in warnings)

    def test_room_with_fewer_walls_than_runs_uses_last_wall(self):
        """If room has fewer walls than runs, last wall length is reused."""
        config = {
            "settings": {"cabinetGap": 0},
            "room": {"walls": [{"length": 2000}]},  # Only 1 wall defined
            "runs": [
                {
                    "label": "wall1",
                    "base": [{"type": "base-door", "width": 600}],
                },
                {
                    "label": "wall2",
                    "turn": "left",
                    "base": [{"type": "base-door", "width": 600}],
                },
            ],
        }
        _apply_defaults(config)
        warnings = validate_config(config)
        # Should not crash, just reuse last wall length
        assert not any("exceeds wall" in w for w in warnings)
