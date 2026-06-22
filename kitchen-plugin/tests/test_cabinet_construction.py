"""Cabinet Construction Tests.

Tests for realistic European cabinet construction geometry.
Based on 18mm corpus board, 18-19mm front panels, 3mm HDF back.

Reference: docs/analiza_konfiguratora_formatek.md
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from src.core.types import Dimensions
from src.kitchen.cabinet_geometry import (
    CabinetGeometry,
    DEFAULT_CORPUS_THICKNESS,
    DEFAULT_FRONT_THICKNESS,
    DEFAULT_BACK_THICKNESS,
    DEFAULT_GROOVE_OFFSET,
    DEFAULT_OVERLAY_SIDE,
    DEFAULT_OVERLAY_TOP,
    DEFAULT_OVERLAY_BOTTOM,
)


# ─── Tests ───────────────────────────────────────────────────────────────────

class TestCabinetGeometryBase:
    """Test basic cabinet geometry calculations."""

    def test_standard_base_cabinet_d60(self):
        """Standard D60 base cabinet (600mm wide)."""
        geom = CabinetGeometry(
            external_width=600,
            external_depth=560,
            external_height=720,
        )

        # External dimensions unchanged
        assert geom.external_width == 600
        assert geom.external_depth == 560
        assert geom.external_height == 720

    def test_internal_width_d60(self):
        """D60 internal width = 600 - 2*18 = 564mm."""
        geom = CabinetGeometry(600, 560, 720)
        assert geom.internal_width == pytest.approx(564.0)

    def test_internal_depth_d60(self):
        """D60 internal depth = 560 - 10 - 3 = 547mm (groove offset + back)."""
        geom = CabinetGeometry(600, 560, 720)
        assert geom.internal_depth == pytest.approx(547.0)

    def test_internal_height_d60(self):
        """D60 internal height = 720mm (frameless, no top/bottom deduction)."""
        geom = CabinetGeometry(600, 560, 720)
        assert geom.internal_height == pytest.approx(720.0)


class TestCabinetGeometrySidePanels:
    """Test side panel dimensions."""

    def test_side_panel_d60(self):
        """D60 side panel: 720mm high × 560mm deep."""
        geom = CabinetGeometry(600, 560, 720)
        assert geom.side_panel_height == pytest.approx(720.0)
        assert geom.side_panel_width == pytest.approx(560.0)


class TestCabinetGeometryBottomPanel:
    """Test bottom/top panel dimensions."""

    def test_bottom_panel_d60(self):
        """D60 bottom panel: 564mm wide × 547mm deep."""
        geom = CabinetGeometry(600, 560, 720)
        assert geom.bottom_panel_width == pytest.approx(564.0)
        assert geom.bottom_panel_depth == pytest.approx(547.0)


class TestCabinetGeometryBackPanel:
    """Test back panel dimensions."""

    def test_back_panel_d60(self):
        """D60 back panel: 564mm wide × 717mm high (with tolerance)."""
        geom = CabinetGeometry(600, 560, 720)
        assert geom.back_panel_width == pytest.approx(564.0)
        assert geom.back_panel_height == pytest.approx(717.0)

    def test_back_panel_thickness(self):
        """Back panel is 3mm HDF."""
        geom = CabinetGeometry(600, 560, 720)
        assert geom.back_thickness == pytest.approx(3.0)


class TestCabinetGeometryFrontPanel:
    """Test front panel (door/drawer front) dimensions."""

    def test_front_dimensions_overlay_d60(self):
        """D60 overlay door: 604mm wide × 724mm high (with 2mm overlay)."""
        geom = CabinetGeometry(600, 560, 720)
        width, height = geom.front_dimensions()

        # Width: 600 + 2*2 = 604mm
        assert width == pytest.approx(604.0)
        # Height: 720 + 2 + 2 = 724mm
        assert height == pytest.approx(724.0)

    def test_front_position_overlay_d60(self):
        """D60 overlay door position: offset -2mm in X, -19mm in Y, -2mm in Z."""
        geom = CabinetGeometry(600, 560, 720)
        x, y, z = geom.front_position()

        assert x == pytest.approx(-2.0)  # Shift left by overlay
        assert y == pytest.approx(-19.0)  # Front thickness forward
        assert z == pytest.approx(-2.0)  # Shift down by overlay

    def test_front_thickness(self):
        """Front panel is 19mm thick."""
        geom = CabinetGeometry(600, 560, 720)
        assert geom.front_thickness == pytest.approx(19.0)

    def test_front_custom_overlay(self):
        """Custom overlay values change front dimensions."""
        geom = CabinetGeometry(600, 560, 720)
        width, height = geom.front_dimensions(
            overlay_side=16,  # Larger overlay
            overlay_top=10,
            overlay_bottom=10,
        )

        # Width: 600 + 2*16 = 632mm
        assert width == pytest.approx(632.0)
        # Height: 720 + 10 + 10 = 740mm
        assert height == pytest.approx(740.0)


class TestCabinetGeometryWallCabinet:
    """Test wall cabinet geometry."""

    def test_wall_cabinet_w60(self):
        """W60 wall cabinet (600×300×720)."""
        geom = CabinetGeometry(600, 300, 720)

        assert geom.internal_width == pytest.approx(564.0)
        assert geom.internal_depth == pytest.approx(287.0)  # 300 - 10 - 3


class TestCabinetGeometryTallCabinet:
    """Test tall cabinet geometry."""

    def test_tall_cabinet_t60(self):
        """T60 tall cabinet (600×560×2000)."""
        geom = CabinetGeometry(600, 560, 2000)

        assert geom.internal_width == pytest.approx(564.0)
        assert geom.internal_height == pytest.approx(2000.0)


class TestCabinetGeometryNarrowCabinet:
    """Test narrow cabinet geometry."""

    def test_narrow_cabinet_300(self):
        """300mm wide cabinet."""
        geom = CabinetGeometry(300, 560, 720)

        assert geom.internal_width == pytest.approx(264.0)
        assert geom.internal_depth == pytest.approx(547.0)


class TestCabinetGeometryWideCabinet:
    """Test wide cabinet geometry."""

    def test_wide_cabinet_1200(self):
        """1200mm wide cabinet (double door)."""
        geom = CabinetGeometry(1200, 560, 720)

        assert geom.internal_width == pytest.approx(1164.0)
        assert geom.internal_depth == pytest.approx(547.0)


class TestCabinetGeometryCustomThickness:
    """Test custom board thickness."""

    def test_custom_corpus_thickness(self):
        """Custom corpus thickness (e.g., 16mm)."""
        geom = CabinetGeometry(600, 560, 720, corpus_thickness=16)

        assert geom.internal_width == pytest.approx(568.0)  # 600 - 2*16

    def test_custom_back_thickness(self):
        """Custom back thickness (e.g., 5mm MDF)."""
        geom = CabinetGeometry(600, 560, 720, back_thickness=5)

        assert geom.internal_depth == pytest.approx(545.0)  # 560 - 10 - 5

    def test_custom_front_thickness(self):
        """Custom front thickness (e.g., 18mm)."""
        geom = CabinetGeometry(600, 560, 720, front_thickness=18)

        width, height = geom.front_dimensions()
        x, y, z = geom.front_position()

        assert geom.front_thickness == pytest.approx(18.0)
        assert y == pytest.approx(-18.0)


class TestCabinetGeometryConsistency:
    """Test dimension consistency."""

    def test_internal_plus_walls_equals_external(self):
        """Internal width + 2 walls = external width."""
        geom = CabinetGeometry(600, 560, 720)

        reconstructed = geom.internal_width + 2 * geom.corpus_thickness
        assert reconstructed == pytest.approx(geom.external_width)

    def test_internal_depth_consistency(self):
        """Internal depth + back offset + back = external depth."""
        geom = CabinetGeometry(600, 560, 720)

        reconstructed = geom.internal_depth + geom.groove_offset + geom.back_thickness
        assert reconstructed == pytest.approx(geom.external_depth)


class TestCabinetGeometryDoubleDoor:
    """Test double door cabinet front calculations."""

    def test_double_door_width_split(self):
        """Double door: each door is (width - gap) / 2."""
        geom = CabinetGeometry(800, 560, 720)
        front_gap = 2  # mm between doors

        total_width, height = geom.front_dimensions()
        # Each door width
        door_width = (total_width - front_gap) / 2

        # Each door should be ~401mm
        assert door_width == pytest.approx(401.0)
        assert height == pytest.approx(724.0)
