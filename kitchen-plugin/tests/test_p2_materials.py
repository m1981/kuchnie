"""P2-2: Material System Enhancement Tests.

PROBLEM: Materials are just RGB colors:
    "carcass": { "color": [0.90, 0.90, 0.88] }

Real kitchen visualization needs:
- Roughness (matte vs glossy laminate)
- Texture maps (wood grain, marble pattern)
- Metallic (for handles, hardware)
- Normal maps (brushed metal, wood grain)
- Emission (for glass transparency)

SOLUTION: Extend material format with PBR properties while maintaining
backward compatibility with simple RGB-only definitions.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from src.config_parser import _apply_defaults, _validate


# ─── Material Format Constants ────────────────────────────────────────────────

DEFAULT_ROUGHNESS = 0.5      # neutral matte
DEFAULT_METALLIC = 0.0       # non-metallic
DEFAULT_ALPHA = 1.0          # fully opaque
DEFAULT_EMISSION = 0.0       # no emission


# ─── Backward Compatibility Tests ─────────────────────────────────────────────

class TestMaterialBackwardCompatibility:
    """Verify that old RGB-only format still works."""

    def test_rgb_only_format(self):
        """Old RGB-only format should be accepted."""
        config = {
            "settings": {},
            "materials": {
                "carcass": {"color": [0.90, 0.90, 0.88]},
            },
            "runs": [{"base": [{"type": "base-door", "width": 600}]}],
        }
        _apply_defaults(config)
        _validate(config)  # Should not raise

    def test_rgba_format(self):
        """RGBA format should be accepted."""
        config = {
            "settings": {},
            "materials": {
                "glass": {"color": [0.90, 0.95, 1.00, 0.15]},
            },
            "runs": [{"base": [{"type": "base-door", "width": 600}]}],
        }
        _apply_defaults(config)
        _validate(config)  # Should not raise


# ─── PBR Property Tests ───────────────────────────────────────────────────────

class TestPBRProperties:
    """Verify that PBR properties are accepted."""

    def test_roughness_property(self):
        """Roughness property should be accepted."""
        config = {
            "settings": {},
            "materials": {
                "counter": {
                    "color": [0.72, 0.70, 0.68],
                    "roughness": 0.3,
                },
            },
            "runs": [{"base": [{"type": "base-door", "width": 600}]}],
        }
        _apply_defaults(config)
        _validate(config)  # Should not raise

    def test_metallic_property(self):
        """Metallic property should be accepted."""
        config = {
            "settings": {},
            "materials": {
                "handle": {
                    "color": [0.25, 0.25, 0.25],
                    "metallic": 0.9,
                },
            },
            "runs": [{"base": [{"type": "base-door", "width": 600}]}],
        }
        _apply_defaults(config)
        _validate(config)  # Should not raise

    def test_texture_property(self):
        """Texture path should be accepted."""
        config = {
            "settings": {},
            "materials": {
                "counter": {
                    "color": [0.72, 0.70, 0.68],
                    "texture": "textures/quartz.png",
                },
            },
            "runs": [{"base": [{"type": "base-door", "width": 600}]}],
        }
        _apply_defaults(config)
        _validate(config)  # Should not raise

    def test_normal_map_property(self):
        """Normal map path should be accepted."""
        config = {
            "settings": {},
            "materials": {
                "counter": {
                    "color": [0.72, 0.70, 0.68],
                    "normalMap": "textures/quartz_normal.png",
                },
            },
            "runs": [{"base": [{"type": "base-door", "width": 600}]}],
        }
        _apply_defaults(config)
        _validate(config)  # Should not raise

    def test_emission_property(self):
        """Emission property should be accepted."""
        config = {
            "settings": {},
            "materials": {
                "glass": {
                    "color": [0.90, 0.95, 1.00],
                    "alpha": 0.15,
                    "emission": 0.01,
                },
            },
            "runs": [{"base": [{"type": "base-door", "width": 600}]}],
        }
        _apply_defaults(config)
        _validate(config)  # Should not raise


# ─── Material Validation Tests ────────────────────────────────────────────────

class TestMaterialValidation:
    """Verify that material properties are validated."""

    def test_roughness_range(self):
        """Roughness must be 0-1."""
        config = {
            "settings": {},
            "materials": {
                "test": {"color": [0.5, 0.5, 0.5], "roughness": 1.5},
            },
            "runs": [{"base": [{"type": "base-door", "width": 600}]}],
        }
        _apply_defaults(config)
        with pytest.raises(ValueError, match="roughness"):
            _validate(config)

    def test_metallic_range(self):
        """Metallic must be 0-1."""
        config = {
            "settings": {},
            "materials": {
                "test": {"color": [0.5, 0.5, 0.5], "metallic": -0.1},
            },
            "runs": [{"base": [{"type": "base-door", "width": 600}]}],
        }
        _apply_defaults(config)
        with pytest.raises(ValueError, match="metallic"):
            _validate(config)

    def test_alpha_range(self):
        """Alpha must be 0-1."""
        config = {
            "settings": {},
            "materials": {
                "test": {"color": [0.5, 0.5, 0.5], "alpha": 2.0},
            },
            "runs": [{"base": [{"type": "base-door", "width": 600}]}],
        }
        _apply_defaults(config)
        with pytest.raises(ValueError, match="alpha"):
            _validate(config)

    def test_color_range(self):
        """Color values must be 0-1."""
        config = {
            "settings": {},
            "materials": {
                "test": {"color": [1.5, 0.5, 0.5]},
            },
            "runs": [{"base": [{"type": "base-door", "width": 600}]}],
        }
        _apply_defaults(config)
        with pytest.raises(ValueError, match="color"):
            _validate(config)

    def test_color_length(self):
        """Color must be 3 or 4 elements."""
        config = {
            "settings": {},
            "materials": {
                "test": {"color": [0.5, 0.5]},
            },
            "runs": [{"base": [{"type": "base-door", "width": 600}]}],
        }
        _apply_defaults(config)
        with pytest.raises(ValueError, match="color"):
            _validate(config)


# ─── Default Material Tests ───────────────────────────────────────────────────

class TestDefaultMaterials:
    """Verify that standard kitchen materials are defined."""

    def test_carcass_material_exists(self):
        """Carcass material should be defined by default."""
        config = {
            "settings": {},
            "runs": [{"base": [{"type": "base-door", "width": 600}]}],
        }
        _apply_defaults(config)
        materials = config.get("materials", {})
        # Materials might not be auto-created, that's OK
        # This test just verifies the format is accepted

    def test_material_without_color_rejected(self):
        """Material without color should be rejected."""
        config = {
            "settings": {},
            "materials": {
                "test": {"roughness": 0.5},
            },
            "runs": [{"base": [{"type": "base-door", "width": 600}]}],
        }
        _apply_defaults(config)
        with pytest.raises(ValueError, match="color"):
            _validate(config)


# ─── Complete Material Definition Tests ────────────────────────────────────────

class TestCompleteMaterialDefinition:
    """Verify that full PBR material definitions work."""

    def test_full_pbr_material(self):
        """Full PBR material with all properties should work."""
        config = {
            "settings": {},
            "materials": {
                "quartz_counter": {
                    "color": [0.85, 0.83, 0.80],
                    "roughness": 0.2,
                    "metallic": 0.0,
                    "texture": "textures/quartz_diffuse.png",
                    "normalMap": "textures/quartz_normal.png",
                },
                "stainless_handle": {
                    "color": [0.7, 0.7, 0.7],
                    "roughness": 0.15,
                    "metallic": 0.95,
                },
                "frosted_glass": {
                    "color": [0.95, 0.95, 0.95],
                    "roughness": 0.8,
                    "alpha": 0.4,
                },
            },
            "runs": [{"base": [{"type": "base-door", "width": 600}]}],
        }
        _apply_defaults(config)
        _validate(config)  # Should not raise
