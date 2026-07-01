"""Phase 1 tests: Hinge configuration (TC-5.1, TC-5.2).

Covers:
- TC-5.1.x: Hinge types (Blum, Hettich, Salice, GTV)
- TC-5.2.x: Hinge count based on door height
- TC-5.3.x: First hinge position
- TC-5.4.x: Hinge distribution
"""

from __future__ import annotations

import pytest

from kitchen_cam.models import HingeSpec
from kitchen_cam.machining import _hinge_positions


# ---------------------------------------------------------------------------
# TC-5.1: Hinge types
# ---------------------------------------------------------------------------


class TestHingeTypes:
    """TC-5.1: Verify hinge specifications for different manufacturers."""

    def test_blum_clip_35_wkret(self):
        """TC-5.1.1: Blum CLIP 35mm with screw mounting."""
        hinge = HingeSpec(
            type="blum_clip_35",
            cup_diameter=35.0,
            cup_depth=13.0,
            screw_spacing=45.0,
            screw_diameter=3.0,
            screw_depth=2.0,
        )
        assert hinge.cup_diameter == 35.0
        assert hinge.screw_spacing == 45.0
        assert hinge.screw_diameter == 3.0

    def test_blum_clip_35_kolek(self):
        """TC-5.1.2: Blum CLIP 35mm with dowel mounting (∅8mm)."""
        hinge = HingeSpec(
            type="blum_clip_35_dowel",
            cup_diameter=35.0,
            cup_depth=13.5,
            screw_spacing=45.0,
            screw_diameter=8.0,  # dowel
            screw_depth=13.5,
        )
        assert hinge.screw_diameter == 8.0
        assert hinge.cup_depth == 13.5

    def test_hettich(self):
        """TC-5.1.3: Hettich hinge — screw spacing 52mm."""
        hinge = HingeSpec(
            type="hettich_35",
            cup_diameter=35.0,
            screw_spacing=52.0,  # Hettich uses 52mm
        )
        assert hinge.screw_spacing == 52.0

    def test_salice(self):
        """TC-5.1.4: Salice hinge."""
        hinge = HingeSpec(
            type="salice_35",
            cup_diameter=35.0,
            screw_spacing=48.0,  # Salice typical
        )
        assert hinge.screw_spacing == 48.0

    def test_gtv(self):
        """TC-5.1.5: GTV hinge (budget)."""
        hinge = HingeSpec(
            type="gtv_35",
            cup_diameter=35.0,
            screw_spacing=45.0,
        )
        assert hinge.cup_diameter == 35.0

    def test_default_hinge_is_blum(self):
        """Default HingeSpec matches Blum CLIP top parameters."""
        hinge = HingeSpec()
        assert hinge.type == "blum_clip_35"
        assert hinge.cup_diameter == 35.0
        assert hinge.cup_depth == 13.0
        assert hinge.screw_spacing == 45.0
        assert hinge.edge_to_cup_centre == 5.0


# ---------------------------------------------------------------------------
# TC-5.2: Hinge count based on door height
# ---------------------------------------------------------------------------


class TestHingeCountByHeight:
    """TC-5.2: Verify automatic hinge count determination."""

    def test_door_400mm_gets_2_hinges(self):
        """TC-5.2.1: Door ≤ 500mm → 2 hinges."""
        positions = _hinge_positions(front_height=400.0, count=2, first_pos=100.0)
        assert len(positions) == 2

    def test_door_500mm_gets_2_hinges(self):
        """TC-5.2.2: Door 500mm (boundary) → 2 hinges."""
        positions = _hinge_positions(front_height=500.0, count=2, first_pos=100.0)
        assert len(positions) == 2

    def test_door_501mm_gets_3_hinges(self):
        """TC-5.2.3: Door 501mm → 3 hinges."""
        positions = _hinge_positions(front_height=501.0, count=3, first_pos=100.0)
        assert len(positions) == 3

    def test_door_900mm_gets_3_hinges(self):
        """TC-5.2.4: Door 900mm (boundary) → 3 hinges."""
        positions = _hinge_positions(front_height=900.0, count=3, first_pos=100.0)
        assert len(positions) == 3

    def test_door_901mm_gets_4_hinges(self):
        """TC-5.2.5: Door 901mm → 4 hinges."""
        positions = _hinge_positions(front_height=901.0, count=4, first_pos=100.0)
        assert len(positions) == 4

    def test_door_1500mm_gets_4_hinges(self):
        """TC-5.2.6: Very tall door 1500mm → 4 hinges."""
        positions = _hinge_positions(front_height=1500.0, count=4, first_pos=100.0)
        assert len(positions) == 4


# ---------------------------------------------------------------------------
# TC-5.3: First hinge position
# ---------------------------------------------------------------------------


class TestFirstHingePosition:
    """TC-5.3: Verify first hinge position parameter."""

    def test_default_first_position_100mm(self):
        """TC-5.3.1: Default first hinge at 100mm from bottom."""
        positions = _hinge_positions(front_height=713.0, count=2, first_pos=100.0)
        assert positions[0] == pytest.approx(100.0)

    def test_custom_first_position_80mm(self):
        """TC-5.3.2: Custom first hinge at 80mm."""
        positions = _hinge_positions(front_height=713.0, count=2, first_pos=80.0)
        assert positions[0] == pytest.approx(80.0)

    def test_custom_first_position_120mm(self):
        """TC-5.3.3: Custom first hinge at 120mm."""
        positions = _hinge_positions(front_height=713.0, count=2, first_pos=120.0)
        assert positions[0] == pytest.approx(120.0)


# ---------------------------------------------------------------------------
# TC-5.4: Hinge distribution
# ---------------------------------------------------------------------------


class TestHingeDistribution:
    """TC-5.4: Verify hinges are distributed symmetrically."""

    def test_2_hinges_symmetric(self):
        """TC-5.4.1: 2 hinges on 713mm — symmetric from top/bottom."""
        positions = _hinge_positions(front_height=713.0, count=2, first_pos=100.0)
        assert positions[0] == pytest.approx(100.0)
        assert positions[1] == pytest.approx(713.0 - 100.0)

    def test_3_hinges_evenly_spaced(self):
        """TC-5.4.2: 3 hinges on 713mm — evenly spaced."""
        positions = _hinge_positions(front_height=713.0, count=3, first_pos=100.0)
        assert len(positions) == 3
        # First at 100, last at 613, middle at ~356.5
        assert positions[0] == pytest.approx(100.0)
        assert positions[2] == pytest.approx(613.0)
        # Middle should be average of first and last
        expected_middle = (100.0 + 613.0) / 2
        assert positions[1] == pytest.approx(expected_middle, abs=1.0)

    def test_4_hinges_evenly_spaced(self):
        """TC-5.4.3: 4 hinges on 1000mm — evenly spaced."""
        positions = _hinge_positions(front_height=1000.0, count=4, first_pos=100.0)
        assert len(positions) == 4
        assert positions[0] == pytest.approx(100.0)
        assert positions[3] == pytest.approx(900.0)
        # Middle two should be evenly spaced
        step = (900.0 - 100.0) / 3
        assert positions[1] == pytest.approx(100.0 + step, abs=1.0)
        assert positions[2] == pytest.approx(100.0 + 2 * step, abs=1.0)

    def test_single_hinge_centered(self):
        """Single hinge should be at center of door."""
        positions = _hinge_positions(front_height=400.0, count=1, first_pos=100.0)
        assert len(positions) == 1
        assert positions[0] == pytest.approx(200.0)
