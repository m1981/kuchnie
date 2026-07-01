"""Phase 1 tests: Materials and thicknesses (TC-1.1, TC-1.2).

Covers:
- TC-1.1.x: Different material types
- TC-1.2.x: Panel thickness validation
- TC-1.3.x: Surface structure (PM/TM)
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from kitchen_cam.models import Panel, PanelRole


# ---------------------------------------------------------------------------
# TC-1.1: Material types
# ---------------------------------------------------------------------------


class TestMaterialTypes:
    """TC-1.1: Verify different board materials can be used."""

    @pytest.mark.parametrize(
        "material, thickness, role",
        [
            ("U702_PMST9", 19.0, PanelRole.FRONT_DOOR),       # TC-1.1.1: EGGER
            ("D3821_SW", 18.0, PanelRole.LEFT_SIDE),          # TC-1.1.2: Swiss Krono
            ("MDF_LAKIER", 22.0, PanelRole.FRONT_DOOR),       # TC-1.1.3: MDF
            ("HDF_3mm_bialy", 3.0, PanelRole.BACK),           # TC-1.1.4: HDF
        ],
        ids=[
            "TC-1.1.1_EGGER_U702_19mm",
            "TC-1.1.2_Swiss_Krono_D3821_18mm",
            "TC-1.1.3_MDF_22mm",
            "TC-1.1.4_HDF_3mm",
        ],
    )
    def test_material_creation(self, material: str, thickness: float, role: PanelRole):
        """Panel can be created with various standard materials."""
        panel = Panel(
            id="test-001",
            role=role,
            width=500.0,
            height=700.0,
            thickness=thickness,
            material=material,
        )
        assert panel.material == material
        assert panel.thickness == thickness

    def test_unknown_material_accepted(self):
        """TC-1.1.5: Unknown material is accepted (string field, no validation)."""
        panel = Panel(
            id="test-unknown",
            role=PanelRole.LEFT_SIDE,
            width=500.0,
            height=700.0,
            thickness=18.0,
            material="XXX_999_UNKNOWN",
        )
        assert panel.material == "XXX_999_UNKNOWN"


# ---------------------------------------------------------------------------
# TC-1.2: Panel thicknesses
# ---------------------------------------------------------------------------


class TestPanelThickness:
    """TC-1.2: Verify panel thickness validation."""

    @pytest.mark.parametrize(
        "thickness",
        [18.0, 19.0, 16.0, 22.0, 3.0, 5.0],
        ids=[
            "TC-1.2.1_standard_18mm",
            "TC-1.2.2_EGGER_19mm",
            "TC-1.2.3_thin_16mm",
            "TC-1.2.4_thick_front_22mm",
            "TC-1.2.5_HDF_3mm",
            "TC-1.2.6_HDF_5mm",
        ],
    )
    def test_valid_thickness(self, thickness: float):
        """Panel accepts valid thickness values."""
        panel = Panel(
            id=f"test-{thickness}",
            role=PanelRole.LEFT_SIDE,
            width=500.0,
            height=700.0,
            thickness=thickness,
            material="TEST",
        )
        assert panel.thickness == thickness

    def test_zero_thickness_rejected(self):
        """TC-1.2.7: Thickness 0 is rejected by Pydantic gt=0 constraint."""
        with pytest.raises(ValidationError, match="thickness"):
            Panel(
                id="test-zero",
                role=PanelRole.LEFT_SIDE,
                width=500.0,
                height=700.0,
                thickness=0.0,
                material="TEST",
            )

    def test_negative_thickness_rejected(self):
        """TC-1.2.8: Negative thickness is rejected."""
        with pytest.raises(ValidationError, match="thickness"):
            Panel(
                id="test-neg",
                role=PanelRole.LEFT_SIDE,
                width=500.0,
                height=700.0,
                thickness=-1.0,
                material="TEST",
            )


# ---------------------------------------------------------------------------
# TC-1.3: Surface structure
# ---------------------------------------------------------------------------


class TestSurfaceStructure:
    """TC-1.3: Surface structure variants (PM vs TM PerfectSense)."""

    def test_PM_surface_material(self):
        """TC-1.3.1: PM PerfectSense Matt material string."""
        panel = Panel(
            id="test-pm",
            role=PanelRole.FRONT_DOOR,
            width=500.0,
            height=700.0,
            thickness=19.0,
            material="U702_PMST9",  # PM = PerfectSense Matt ST9
        )
        assert "PM" in panel.material

    def test_TM_surface_material(self):
        """TC-1.3.2: TM PerfectSense Matt material string."""
        panel = Panel(
            id="test-tm",
            role=PanelRole.FRONT_DOOR,
            width=500.0,
            height=700.0,
            thickness=19.0,
            material="U702_TMST9",  # TM = alternative surface
        )
        assert "TM" in panel.material
