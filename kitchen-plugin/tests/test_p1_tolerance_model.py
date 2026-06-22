"""P1-1: Tolerance Model Contract Tests.

PROBLEM: Magic numbers like 0.001 are scattered throughout geometry_builder.py:
    - obj.location = (0, -0.001, 0)  # "slightly in front of cabinet face"
    - door_w = w - blind_depth - 0.001  # "small offset for clearance"

These are unnamed, undiscoverable, and unconfigurable. In CAD systems,
tolerances MUST be explicit and documented.

SOLUTION: Extract all magic numbers into named settings:
    - frontOffset: how far door/drawer fronts protrude from cabinet face
    - clearanceOffset: small gap for geometric clearance (blind corners, etc.)

These tests enforce that tolerances are:
1. Named and documented in settings
2. Used consistently throughout geometry_builder
3. Configurable by the user
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from src.config_parser import DEFAULTS, _apply_defaults


# ─── Tolerance Constants (the contract) ───────────────────────────────────────

DEFAULT_FRONT_OFFSET = 0.001      # meters (1mm) - how far fronts protrude
DEFAULT_CLEARANCE_OFFSET = 0.001  # meters (1mm) - geometric clearance


# ─── Settings Defaults Tests ──────────────────────────────────────────────────

class TestToleranceDefaults:
    """Verify that tolerance defaults are correctly defined."""

    def test_default_front_offset_exists(self):
        """frontOffset must be in DEFAULTS."""
        assert "frontOffset" in DEFAULTS

    def test_default_front_offset_value(self):
        """frontOffset default is 1mm (0.001m)."""
        assert DEFAULTS["frontOffset"] == DEFAULT_FRONT_OFFSET

    def test_default_clearance_offset_exists(self):
        """clearanceOffset must be in DEFAULTS."""
        assert "clearanceOffset" in DEFAULTS

    def test_default_clearance_offset_value(self):
        """clearanceOffset default is 1mm (0.001m)."""
        assert DEFAULTS["clearanceOffset"] == DEFAULT_CLEARANCE_OFFSET

    def test_apply_defaults_sets_tolerances(self):
        """_apply_defaults must set both tolerance settings."""
        config = {"runs": []}
        _apply_defaults(config)
        assert config["settings"]["frontOffset"] == DEFAULT_FRONT_OFFSET
        assert config["settings"]["clearanceOffset"] == DEFAULT_CLEARANCE_OFFSET


# ─── Tolerance Validation Tests ───────────────────────────────────────────────

class TestToleranceValidation:
    """Verify that tolerance values are validated."""

    def test_front_offset_must_be_positive(self):
        """frontOffset must be > 0."""
        from src.validators import validate_config
        config = {
            "settings": {"frontOffset": -0.001},
            "runs": [{"base": [{"type": "base-door", "width": 600}]}],
        }
        _apply_defaults(config)
        warnings = validate_config(config)
        assert any("frontOffset" in w for w in warnings)

    def test_clearance_offset_must_be_positive(self):
        """clearanceOffset must be > 0."""
        from src.validators import validate_config
        config = {
            "settings": {"clearanceOffset": -0.001},
            "runs": [{"base": [{"type": "base-door", "width": 600}]}],
        }
        _apply_defaults(config)
        warnings = validate_config(config)
        assert any("clearanceOffset" in w for w in warnings)

    def test_front_offset_excessive_warns(self):
        """frontOffset > 10mm should warn."""
        from src.validators import validate_config
        config = {
            "settings": {"frontOffset": 0.05},  # 50mm - way too much
            "runs": [{"base": [{"type": "base-door", "width": 600}]}],
        }
        _apply_defaults(config)
        warnings = validate_config(config)
        assert any("frontOffset" in w for w in warnings)


# ─── Geometry Builder Tolerance Usage Tests ───────────────────────────────────
# These tests verify that geometry_builder uses the settings, not hardcoded values.

try:
    import bpy
    HAS_BPY = True
except ImportError:
    HAS_BPY = False

requires_bpy = pytest.mark.skipif(not HAS_BPY, reason="bpy not available")


@requires_bpy
class TestFrontOffsetUsage:
    """Verify that door/drawer fronts use frontOffset from settings."""

    @pytest.fixture(autouse=True)
    def clean_scene(self):
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete(use_global=False)
        yield

    def test_door_front_uses_front_offset_setting(self):
        """Door front location.y must equal -frontOffset from settings."""
        from src.geometry_builder import _create_box, _add_door_front

        parent = _create_box("test", 0.6, 0.56, 0.72)
        cab = {"type": "base-door", "door": "right"}

        # Test with custom frontOffset
        settings = {"frontGap": 2, "frontOffset": 0.002}
        _add_door_front(parent, 0.6, 0.72, 0.018, cab, "base")

        # Find door child
        door = [c for c in parent.children if "_door" in c.name][0]
        # Door should be at y = -frontOffset
        assert door.location.y == pytest.approx(-0.002, abs=1e-6)

    def test_drawer_front_uses_front_offset_setting(self):
        """Drawer front location.y must equal -frontOffset from settings."""
        from src.geometry_builder import _create_box, _add_drawer_front

        parent = _create_box("test", 0.6, 0.56, 0.72)

        # Test with custom frontOffset
        settings = {"frontGap": 2, "frontOffset": 0.003}
        _add_drawer_front(parent, 0.6, 0.2, 0.018, 0, 0)

        # Find drawer child
        drawer = [c for c in parent.children if "_drawer" in c.name][0]
        # Drawer should be at y = -frontOffset
        assert drawer.location.y == pytest.approx(-0.003, abs=1e-6)


@requires_bpy
class TestClearanceOffsetUsage:
    """Verify that clearance-sensitive geometry uses clearanceOffset."""

    @pytest.fixture(autouse=True)
    def clean_scene(self):
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete(use_global=False)
        yield

    def test_blind_corner_uses_clearance_offset(self):
        """Blind corner door width = w - blindDepth - clearanceOffset."""
        from src.geometry_builder import _create_box, _add_front

        parent = _create_box("test", 0.9, 0.56, 0.72)
        cab = {
            "type": "corner-blind",
            "width": 900,
            "blindDepth": 400,
            "blindSide": "left",
            "door": "right",
        }
        settings = {"frontGap": 2, "frontOffset": 0.001, "clearanceOffset": 0.002}

        _add_front(parent, cab, settings, "base", 0.9, 0.56, 0.72)

        # Find door child
        doors = [c for c in parent.children if "_door" in c.name]
        assert len(doors) == 1
        door = doors[0]

        # Door width should be: 0.9 - 0.4 - 0.002 = 0.498
        door_verts = [v.co.x for v in door.data.vertices]
        door_width = max(door_verts) - min(door_verts)
        expected_width = 0.9 - 0.4 - 0.002
        assert door_width == pytest.approx(expected_width, abs=1e-5)
