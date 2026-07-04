"""CabinetInstance validation tests.

Proves:
  1. Valid cabinet passes validation
  2. Zero/negative dimensions fail
  3. Too-thick sides fail (internal width <= 0)
"""

import pytest
from kuchnie_core.model import CabinetInstance


def _make_cab(**overrides) -> CabinetInstance:
    """Helper to create a valid cabinet with optional overrides."""
    defaults = dict(
        id="TEST", type="test", description="test",
        width_mm=800, height_mm=720, depth_mm=510,
        body_material="test", back_material="test", front_material="test",
    )
    defaults.update(overrides)
    return CabinetInstance(**defaults)


# ── Valid cabinet ────────────────────────────────────────────────

class TestCabinetInstanceValid:
    def test_valid_cabinet_creates(self):
        cab = _make_cab()
        assert cab.id == "TEST"

    def test_valid_cabinet_no_errors(self):
        cab = _make_cab()
        assert cab.validate() == []


# ── Invalid dimensions ───────────────────────────────────────────

class TestCabinetInstanceInvalid:
    def test_zero_width_raises(self):
        with pytest.raises(ValueError, match="width_mm must be > 0"):
            _make_cab(width_mm=0)

    def test_negative_width_raises(self):
        with pytest.raises(ValueError, match="width_mm must be > 0"):
            _make_cab(width_mm=-100)

    def test_zero_height_raises(self):
        with pytest.raises(ValueError, match="height_mm must be > 0"):
            _make_cab(height_mm=0)

    def test_zero_depth_raises(self):
        with pytest.raises(ValueError, match="depth_mm must be > 0"):
            _make_cab(depth_mm=0)

    def test_zero_side_thickness_raises(self):
        with pytest.raises(ValueError, match="thickness_side_mm must be > 0"):
            _make_cab(thickness_side_mm=0)

    def test_sides_too_thick_raises(self):
        """Width 30mm with 18mm sides = internal -6mm."""
        with pytest.raises(ValueError, match="Internal width"):
            _make_cab(width_mm=30, thickness_side_mm=18)

    def test_sides_exactly_half_raises(self):
        """Width 36mm with 18mm sides = internal 0mm (not positive)."""
        with pytest.raises(ValueError, match="Internal width"):
            _make_cab(width_mm=36, thickness_side_mm=18)


# ── Edge cases ───────────────────────────────────────────────────

class TestCabinetInstanceEdgeCases:
    def test_minimum_valid_width(self):
        """Width 37mm with 18mm sides = internal 1mm (barely valid)."""
        cab = _make_cab(width_mm=37, thickness_side_mm=18)
        assert cab.validate() == []

    def test_very_small_cabinet(self):
        """100×100×100 with 16mm sides = internal 68mm."""
        cab = _make_cab(width_mm=100, height_mm=100, depth_mm=100,
                        thickness_side_mm=16)
        assert cab.validate() == []
