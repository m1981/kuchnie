"""P1-3: Drawer Height Validation Tests.

PROBLEM: The config allows specifying drawer heights as an array:
    "drawers": [120, 160, 200, 240]

But there's no validation that:
1. Sum of drawer heights + frontGaps <= carcass height
2. Individual drawer heights are reasonable (>30mm, <carcass height)
3. Drawer count is within range (1-6)

SOLUTION: Add validation that checks drawer heights against carcass dimensions.

These tests enforce that drawer configurations are physically possible.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from src.config_parser import _apply_defaults, _validate, DEFAULTS


# ─── Drawer Count Validation ──────────────────────────────────────────────────

class TestDrawerCountValidation:
    """Verify that drawer counts are validated."""

    def test_valid_drawer_count_1(self):
        """1 drawer is valid."""
        config = {
            "settings": {},
            "runs": [{"base": [{"type": "base-drawers", "width": 600, "drawers": 1}]}],
        }
        _apply_defaults(config)
        _validate(config)  # Should not raise

    def test_valid_drawer_count_6(self):
        """6 drawers is valid."""
        config = {
            "settings": {},
            "runs": [{"base": [{"type": "base-drawers", "width": 600, "drawers": 6}]}],
        }
        _apply_defaults(config)
        _validate(config)  # Should not raise

    def test_drawer_count_zero_rejected(self):
        """0 drawers should be rejected."""
        config = {
            "settings": {},
            "runs": [{"base": [{"type": "base-drawers", "width": 600, "drawers": 0}]}],
        }
        _apply_defaults(config)
        with pytest.raises(ValueError, match="drawers"):
            _validate(config)

    def test_drawer_count_seven_rejected(self):
        """7 drawers should be rejected."""
        config = {
            "settings": {},
            "runs": [{"base": [{"type": "base-drawers", "width": 600, "drawers": 7}]}],
        }
        _apply_defaults(config)
        with pytest.raises(ValueError, match="drawers"):
            _validate(config)


# ─── Drawer Height Array Validation ───────────────────────────────────────────

class TestDrawerHeightArrayValidation:
    """Verify that drawer height arrays are validated."""

    def test_valid_height_array(self):
        """Reasonable height array should pass."""
        config = {
            "settings": {},
            "runs": [{"base": [
                {"type": "base-drawers", "width": 600, "drawers": [150, 200, 300]}
            ]}],
        }
        _apply_defaults(config)
        _validate(config)  # Should not raise

    def test_height_array_exceeds_carcass_rejected(self):
        """Sum of heights exceeding carcass height should be rejected."""
        config = {
            "settings": {"baseBodyHeight": 720, "frontGap": 2},
            "runs": [{"base": [
                {"type": "base-drawers", "width": 600, "drawers": [300, 300, 300]}
            ]}],
        }
        _apply_defaults(config)
        # 300 + 300 + 300 + 2*2 (gaps) = 904 > 720
        with pytest.raises(ValueError, match="exceed"):
            _validate(config)

    def test_height_array_too_long_rejected(self):
        """Array with more than 6 elements should be rejected."""
        config = {
            "settings": {},
            "runs": [{"base": [
                {"type": "base-drawers", "width": 600, "drawers": [100, 100, 100, 100, 100, 100, 100]}
            ]}],
        }
        _apply_defaults(config)
        with pytest.raises(ValueError, match="drawers"):
            _validate(config)

    def test_height_array_empty_rejected(self):
        """Empty array should be rejected."""
        config = {
            "settings": {},
            "runs": [{"base": [
                {"type": "base-drawers", "width": 600, "drawers": []}
            ]}],
        }
        _apply_defaults(config)
        with pytest.raises(ValueError, match="drawers"):
            _validate(config)

    def test_individual_drawer_too_small_rejected(self):
        """Drawer height < 30mm should be rejected."""
        config = {
            "settings": {},
            "runs": [{"base": [
                {"type": "base-drawers", "width": 600, "drawers": [20, 200, 300]}
            ]}],
        }
        _apply_defaults(config)
        with pytest.raises(ValueError, match="too small"):
            _validate(config)

    def test_individual_drawer_exceeds_carcass_rejected(self):
        """Single drawer height > carcass height should be rejected."""
        config = {
            "settings": {"baseBodyHeight": 720},
            "runs": [{"base": [
                {"type": "base-drawers", "width": 600, "drawers": [800]}
            ]}],
        }
        _apply_defaults(config)
        with pytest.raises(ValueError, match="exceed"):
            _validate(config)


# ─── Wall Drawer Validation ───────────────────────────────────────────────────

class TestWallDrawerValidation:
    """Verify that wall drawer heights are validated against wall cabinet height."""

    def test_wall_drawers_valid(self):
        """Reasonable wall drawer heights should pass."""
        config = {
            "settings": {"wallHeight": 600},
            "runs": [{"upper": [
                {"type": "wall-drawers", "width": 600, "drawers": [200, 200]}
            ]}],
        }
        _apply_defaults(config)
        _validate(config)  # Should not raise

    def test_wall_drawers_exceed_height_rejected(self):
        """Wall drawer heights exceeding wall cabinet height should be rejected."""
        config = {
            "settings": {"wallHeight": 600, "frontGap": 2},
            "runs": [{"upper": [
                {"type": "wall-drawers", "width": 600, "drawers": [300, 300, 300]}
            ]}],
        }
        _apply_defaults(config)
        # 300 + 300 + 300 + 2*2 = 904 > 600
        with pytest.raises(ValueError, match="exceed"):
            _validate(config)


# ─── Drawer-Door Combination Validation ───────────────────────────────────────

class TestDrawerDoorValidation:
    """Verify that drawer-door combinations are validated."""

    def test_drawer_door_valid(self):
        """Reasonable drawer-door combo should pass."""
        config = {
            "settings": {"baseBodyHeight": 720},
            "runs": [{"base": [
                {"type": "base-drawer-door", "width": 600, "drawerHeight": 150}
            ]}],
        }
        _apply_defaults(config)
        _validate(config)  # Should not raise

    def test_drawer_height_exceeds_carcass_rejected(self):
        """Drawer height > carcass height should be rejected."""
        config = {
            "settings": {"baseBodyHeight": 720},
            "runs": [{"base": [
                {"type": "base-drawer-door", "width": 600, "drawerHeight": 800}
            ]}],
        }
        _apply_defaults(config)
        with pytest.raises(ValueError, match="exceed"):
            _validate(config)

    def test_drawer_height_too_small_rejected(self):
        """Drawer height < 30mm should be rejected."""
        config = {
            "settings": {"baseBodyHeight": 720},
            "runs": [{"base": [
                {"type": "base-drawer-door", "width": 600, "drawerHeight": 20}
            ]}],
        }
        _apply_defaults(config)
        with pytest.raises(ValueError, match="too small"):
            _validate(config)
