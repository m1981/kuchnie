"""Blum ClipTop hinge catalog — 110°, 95°, 155°.

Tests prove:
  1. Hinge model has correct properties (angle, overlay, cup diameter)
  2. HingeCalculator returns correct count based on door height
  3. HingeFactory returns correct hinge by id
  4. Default hinge is ClipTop 110°
"""

import pytest
from kuchnie_core.blum_hinges import (
    BlumHinge,
    BlumClipTop110,
    BlumClipTop95,
    BlumClipTop155,
    HingeFactory,
    calculate_hinge_count,
)


# ── BlumClipTop 110° ────────────────────────────────────────────

class TestBlumClipTop110:
    """Standard concealed hinge — 110° opening angle."""

    def test_id(self):
        h = BlumClipTop110()
        assert h.id == "blum_cliptop_110"

    def test_name(self):
        h = BlumClipTop110()
        assert "110" in h.name

    def test_opening_angle(self):
        h = BlumClipTop110()
        assert h.opening_angle_deg == 110

    def test_cup_diameter(self):
        h = BlumClipTop110()
        assert h.cup_diameter_mm == 35

    def test_cup_drill_depth(self):
        h = BlumClipTop110()
        assert h.cup_drill_depth_mm == 13

    def test_mounting_type(self):
        h = BlumClipTop110()
        assert h.mounting_type == "clip"

    def test_overlay_types(self):
        h = BlumClipTop110()
        assert "full" in h.overlay_types
        assert "half" in h.overlay_types
        assert "inset" in h.overlay_types

    def test_closing_type(self):
        h = BlumClipTop110()
        assert h.closing_type == "blumotion"

    def test_is_default(self):
        h = BlumClipTop110()
        assert h.is_default is True


# ── BlumClipTop 95° ─────────────────────────────────────────────

class TestBlumClipTop95:
    """Hinge for inset doors — 95° opening angle."""

    def test_opening_angle(self):
        h = BlumClipTop95()
        assert h.opening_angle_deg == 95

    def test_id(self):
        h = BlumClipTop95()
        assert h.id == "blum_cliptop_95"

    def test_overlay_types(self):
        h = BlumClipTop95()
        assert "inset" in h.overlay_types

    def test_is_not_default(self):
        h = BlumClipTop95()
        assert h.is_default is False


# ── BlumClipTop 155° ────────────────────────────────────────────

class TestBlumClipTop155:
    """Wide-angle hinge — 155° opening angle."""

    def test_opening_angle(self):
        h = BlumClipTop155()
        assert h.opening_angle_deg == 155

    def test_id(self):
        h = BlumClipTop155()
        assert h.id == "blum_cliptop_155"

    def test_overlay_types(self):
        h = BlumClipTop155()
        assert "full" in h.overlay_types


# ── HingeFactory ─────────────────────────────────────────────────

class TestHingeFactory:
    """Factory returns correct hinge by id."""

    def test_get_110(self):
        h = HingeFactory.get("blum_cliptop_110")
        assert isinstance(h, BlumClipTop110)

    def test_get_95(self):
        h = HingeFactory.get("blum_cliptop_95")
        assert isinstance(h, BlumClipTop95)

    def test_get_155(self):
        h = HingeFactory.get("blum_cliptop_155")
        assert isinstance(h, BlumClipTop155)

    def test_get_default(self):
        h = HingeFactory.get_default()
        assert isinstance(h, BlumClipTop110)

    def test_get_unknown_raises(self):
        with pytest.raises(KeyError, match="unknown_hinge"):
            HingeFactory.get("unknown_hinge")

    def test_list_ids(self):
        ids = HingeFactory.list_ids()
        assert "blum_cliptop_110" in ids
        assert "blum_cliptop_95" in ids
        assert "blum_cliptop_155" in ids


# ── Hinge count calculation ─────────────────────────────────────

class TestHingeCountCalculation:
    """Hinge count depends on door height and weight.

    Blum standard:
      - Up to 1200mm: 2 hinges
      - 1200-1800mm: 3 hinges
      - 1800-2400mm: 4 hinges
    """

    def test_short_door_gets_2(self):
        assert calculate_hinge_count(600) == 2

    def test_medium_door_gets_2(self):
        assert calculate_hinge_count(1000) == 2

    def test_1200mm_gets_2(self):
        assert calculate_hinge_count(1200) == 2

    def test_1201mm_gets_3(self):
        assert calculate_hinge_count(1201) == 3

    def test_tall_door_gets_3(self):
        assert calculate_hinge_count(1500) == 3

    def test_1800mm_gets_3(self):
        assert calculate_hinge_count(1800) == 3

    def test_1801mm_gets_4(self):
        assert calculate_hinge_count(1801) == 4

    def test_very_tall_gets_4(self):
        assert calculate_hinge_count(2200) == 4

    def test_minimum_is_2(self):
        assert calculate_hinge_count(100) == 2


# ── BlumHinge as Accessory ───────────────────────────────────────

class TestHingeToAccessory:
    """Hinge can produce an Accessory for BOM."""

    def test_to_accessory(self):
        h = BlumClipTop110()
        acc = h.to_accessory("CAB1", "D1", quantity=2)
        assert acc.id == "CAB1_hinge_D1"
        assert acc.type == "hinge"
        assert acc.quantity == 2
        assert "110" in acc.name
