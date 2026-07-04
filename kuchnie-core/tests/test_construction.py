"""ConstructionMethod — first-class construction rules (Polyboard pattern).

Tests prove:
  1. ConstructionMethod is a data object with all panel thicknesses + joinery rules
  2. Registry holds named methods, retrievable by id
  3. Methods are reusable across cabinet types
  4. Changing a method cascades to all panels that reference it
"""

import pytest
from kuchnie_core.construction import ConstructionMethod, ConstructionMethodRegistry


# ── ConstructionMethod dataclass ─────────────────────────────────

class TestConstructionMethodDefaults:
    """Default method matches standard European 18mm chipboard construction."""

    def test_has_id(self):
        m = ConstructionMethod(id="test", name="Test")
        assert m.id == "test"

    def test_has_name(self):
        m = ConstructionMethod(id="test", name="Test Method")
        assert m.name == "Test Method"

    def test_default_side_thickness(self):
        m = ConstructionMethod(id="test", name="Test")
        assert m.side_thickness_mm == 18

    def test_default_top_thickness(self):
        m = ConstructionMethod(id="test", name="Test")
        assert m.top_thickness_mm == 18

    def test_default_bottom_thickness(self):
        m = ConstructionMethod(id="test", name="Test")
        assert m.bottom_thickness_mm == 18

    def test_default_shelf_thickness(self):
        m = ConstructionMethod(id="test", name="Test")
        assert m.shelf_thickness_mm == 18

    def test_default_back_thickness(self):
        m = ConstructionMethod(id="test", name="Test")
        assert m.back_thickness_mm == 3

    def test_default_front_thickness(self):
        m = ConstructionMethod(id="test", name="Test")
        assert m.front_thickness_mm == 18

    def test_default_joinery_type(self):
        m = ConstructionMethod(id="test", name="Test")
        assert m.joinery_type == "dowel_confirmat"

    def test_default_back_attachment(self):
        m = ConstructionMethod(id="test", name="Test")
        assert m.back_attachment == "groove"

    def test_default_back_groove_depth(self):
        m = ConstructionMethod(id="test", name="Test")
        assert m.back_groove_depth_mm == 8

    def test_default_edge_band_thickness(self):
        m = ConstructionMethod(id="test", name="Test")
        assert m.edge_band_thickness_mm == 0.8

    def test_default_system32_offset(self):
        m = ConstructionMethod(id="test", name="Test")
        assert m.system32_offset_mm == 37

    def test_default_system32_spacing(self):
        m = ConstructionMethod(id="test", name="Test")
        assert m.system32_spacing_mm == 32

    def test_default_default_hinge(self):
        m = ConstructionMethod(id="test", name="Test")
        assert m.default_hinge == "blum_cliptop_110"

    def test_default_default_runner_brand(self):
        m = ConstructionMethod(id="test", name="Test")
        assert m.default_runner_brand == "blum"


class TestConstructionMethodCustom:
    """Custom values override defaults."""

    def test_custom_thicknesses(self):
        m = ConstructionMethod(
            id="thin", name="Thin 16mm",
            side_thickness_mm=16,
            top_thickness_mm=16,
            bottom_thickness_mm=16,
            shelf_thickness_mm=16,
            back_thickness_mm=2.5,
            front_thickness_mm=16,
        )
        assert m.side_thickness_mm == 16
        assert m.back_thickness_mm == 2.5

    def test_custom_joinery(self):
        m = ConstructionMethod(
            id="camlock", name="Cam Lock",
            joinery_type="camlock",
            back_attachment="rabbet",
            back_groove_depth_mm=0,
        )
        assert m.joinery_type == "camlock"
        assert m.back_attachment == "rabbet"

    def test_custom_system32(self):
        m = ConstructionMethod(
            id="custom", name="Custom",
            system32_offset_mm=32,
            system32_spacing_mm=64,
        )
        assert m.system32_offset_mm == 32
        assert m.system32_spacing_mm == 64


class TestConstructionMethodDerived:
    """Derived values computed from base parameters."""

    def test_carcass_bottom_width_formula(self):
        """bottom_width = cabinet_width - 2 * side_thickness"""
        m = ConstructionMethod(id="test", name="Test", side_thickness_mm=18)
        assert m.carcass_bottom_width(800) == 764  # 800 - 2*18

    def test_carcass_bottom_width_16mm(self):
        m = ConstructionMethod(id="test", name="Test", side_thickness_mm=16)
        assert m.carcass_bottom_width(800) == 768  # 800 - 2*16

    def test_back_panel_width_formula(self):
        """back_width = cabinet_width - 2*side + 2*groove_depth"""
        m = ConstructionMethod(
            id="test", name="Test",
            side_thickness_mm=18, back_groove_depth_mm=8
        )
        assert m.back_panel_width(800) == 780  # 800 - 36 + 16

    def test_back_panel_height_formula(self):
        """back_height = side_height + groove_depth (extends into bottom groove)"""
        m = ConstructionMethod(id="test", name="Test", back_groove_depth_mm=8)
        assert m.back_panel_height(620) == 628  # 620 + 8

    def test_shelf_width_formula(self):
        """shelf_width = bottom_width - 2mm clearance"""
        m = ConstructionMethod(id="test", name="Test", side_thickness_mm=18)
        assert m.shelf_width(800) == 762  # (800 - 36) - 2

    def test_door_width_single(self):
        """single_door = cabinet_width - 2*gap"""
        m = ConstructionMethod(id="test", name="Test")
        assert m.door_width(800, door_count=1) == 794  # 800 - 6

    def test_door_width_double(self):
        """double_door = (cabinet_width - 3*gap) / 2.
        gap_total = 3 * (door_count + 1) = 3 * 3 = 9
        door_w = (800 - 9) / 2 = 395.5
        """
        m = ConstructionMethod(id="test", name="Test")
        assert m.door_width(800, door_count=2) == 395.5

    def test_door_height_formula(self):
        """door_height = cabinet_height - 6 (3mm top + 3mm bottom gap)"""
        m = ConstructionMethod(id="test", name="Test")
        assert m.door_height(720) == 714  # 720 - 6


# ── Registry ─────────────────────────────────────────────────────

class TestConstructionMethodRegistry:
    """Registry holds named construction methods."""

    def test_create_empty_registry(self):
        reg = ConstructionMethodRegistry()
        assert len(reg) == 0

    def test_register_method(self):
        reg = ConstructionMethodRegistry()
        m = ConstructionMethod(id="test", name="Test")
        reg.register(m)
        assert len(reg) == 1

    def test_get_by_id(self):
        reg = ConstructionMethodRegistry()
        m = ConstructionMethod(id="test", name="Test")
        reg.register(m)
        assert reg.get("test") is m

    def test_get_missing_raises(self):
        reg = ConstructionMethodRegistry()
        with pytest.raises(KeyError, match="nonexistent"):
            reg.get("nonexistent")

    def test_register_duplicate_raises(self):
        reg = ConstructionMethodRegistry()
        m1 = ConstructionMethod(id="dup", name="First")
        m2 = ConstructionMethod(id="dup", name="Second")
        reg.register(m1)
        with pytest.raises(ValueError, match="already registered"):
            reg.register(m2)

    def test_list_ids(self):
        reg = ConstructionMethodRegistry()
        reg.register(ConstructionMethod(id="a", name="A"))
        reg.register(ConstructionMethod(id="b", name="B"))
        assert sorted(reg.list_ids()) == ["a", "b"]


# ── Default Methods ──────────────────────────────────────────────

class TestDefaultMethods:
    """Pre-built methods for common European construction."""

    def test_default_registry_has_methods(self):
        reg = ConstructionMethodRegistry.default()
        assert len(reg) >= 2

    def test_dowel_confirmat_18mm(self):
        reg = ConstructionMethodRegistry.default()
        m = reg.get("dowel_confirmat_18mm")
        assert m.side_thickness_mm == 18
        assert m.joinery_type == "dowel_confirmat"
        assert m.back_attachment == "groove"

    def test_camlock_18mm(self):
        reg = ConstructionMethodRegistry.default()
        m = reg.get("camlock_18mm")
        assert m.side_thickness_mm == 18
        assert m.joinery_type == "camlock"
        assert m.back_attachment == "groove"

    def test_dowel_16mm(self):
        """16mm chipboard — lighter construction, some budget kitchens."""
        reg = ConstructionMethodRegistry.default()
        m = reg.get("dowel_16mm")
        assert m.side_thickness_mm == 16
        assert m.back_thickness_mm == 2.5


# ── Immutability ─────────────────────────────────────────────────

class TestConstructionMethodImmutability:
    """ConstructionMethod should be frozen after creation."""

    def test_cannot_modify_side_thickness(self):
        m = ConstructionMethod(id="test", name="Test")
        with pytest.raises(AttributeError):
            m.side_thickness_mm = 25

    def test_cannot_modify_id(self):
        m = ConstructionMethod(id="test", name="Test")
        with pytest.raises(AttributeError):
            m.id = "changed"


class TestConstructionMethodValidation:
    """Validation catches impossible cabinet dimensions."""

    def test_valid_width_passes(self):
        m = ConstructionMethod(id="test", name="Test")
        assert m.validate_cabinet_width(800) == []

    def test_too_small_width_fails(self):
        m = ConstructionMethod(id="test", name="Test")
        errors = m.validate_cabinet_width(30)
        assert len(errors) > 0
        assert "too small" in errors[0].lower()

    def test_zero_width_fails(self):
        m = ConstructionMethod(id="test", name="Test")
        errors = m.validate_cabinet_width(0)
        assert len(errors) > 0

    def test_negative_bottom_width_fails(self):
        m = ConstructionMethod(id="test", name="Test", side_thickness_mm=18)
        errors = m.validate_cabinet_width(35)  # 35 - 36 = -1
        assert any("negative" in e.lower() for e in errors)
