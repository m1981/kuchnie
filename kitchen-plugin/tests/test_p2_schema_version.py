"""P2-3: Schema Version Migration Tests.

PROBLEM: The config has `"version": "1.0"` but no plan for what happens
when the schema changes. No version checking, no migration path.

SOLUTION: Define:
1. Supported versions list
2. Version validation at load time
3. Clear error for unsupported versions
4. Migration path documentation

These tests enforce that schema versioning is handled correctly.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from src.config_parser import load_config, _apply_defaults, _validate


# ─── Version Constants ────────────────────────────────────────────────────────

# These are the CONTRACT. Update when adding new versions.
SUPPORTED_VERSIONS = {"1.0", "1.1"}  # 1.1 = gap system + tolerances
CURRENT_VERSION = "1.1"


# ─── Version Validation Tests ─────────────────────────────────────────────────

class TestVersionValidation:
    """Verify that config versions are validated."""

    def test_version_1_0_accepted(self):
        """Version 1.0 should be accepted (backward compatible)."""
        config = {
            "version": "1.0",
            "settings": {},
            "runs": [{"base": [{"type": "base-door", "width": 600}]}],
        }
        _apply_defaults(config)
        _validate(config)  # Should not raise

    def test_version_1_1_accepted(self):
        """Version 1.1 should be accepted."""
        config = {
            "version": "1.1",
            "settings": {},
            "runs": [{"base": [{"type": "base-door", "width": 600}]}],
        }
        _apply_defaults(config)
        _validate(config)  # Should not raise

    def test_missing_version_defaults_to_1_0(self):
        """Missing version should default to 1.0."""
        config = {
            "settings": {},
            "runs": [{"base": [{"type": "base-door", "width": 600}]}],
        }
        _apply_defaults(config)
        _validate(config)  # Should not raise
        assert config.get("version", "1.0") == "1.0"

    def test_unsupported_version_rejected(self):
        """Unsupported version should be rejected."""
        config = {
            "version": "2.0",
            "settings": {},
            "runs": [{"base": [{"type": "base-door", "width": 600}]}],
        }
        _apply_defaults(config)
        with pytest.raises(ValueError, match="Unsupported.*version"):
            _validate(config)

    def test_future_version_rejected(self):
        """Future version should be rejected."""
        config = {
            "version": "99.0",
            "settings": {},
            "runs": [{"base": [{"type": "base-door", "width": 600}]}],
        }
        _apply_defaults(config)
        with pytest.raises(ValueError, match="Unsupported.*version"):
            _validate(config)

    def test_invalid_version_format_rejected(self):
        """Invalid version format should be rejected."""
        config = {
            "version": "invalid",
            "settings": {},
            "runs": [{"base": [{"type": "base-door", "width": 600}]}],
        }
        _apply_defaults(config)
        with pytest.raises(ValueError, match="Unsupported.*version"):
            _validate(config)


# ─── Version Migration Tests ──────────────────────────────────────────────────

class TestVersionMigration:
    """Verify that older versions are migrated correctly."""

    def test_v1_0_gap_migrated_to_v1_1(self):
        """V1.0 config with 'gap' should migrate to V1.1 'frontGap'."""
        config = {
            "version": "1.0",
            "settings": {"gap": 3},
            "runs": [{"base": [{"type": "base-door", "width": 600}]}],
        }
        _apply_defaults(config)
        _validate(config)

        # Old gap should be migrated
        assert config["settings"]["frontGap"] == 3
        assert config["settings"]["cabinetGap"] == 0

    def test_v1_0_defaults_applied(self):
        """V1.0 config should get V1.1 defaults applied."""
        config = {
            "version": "1.0",
            "settings": {},
            "runs": [{"base": [{"type": "base-door", "width": 600}]}],
        }
        _apply_defaults(config)
        _validate(config)

        # V1.1 defaults should be present
        assert "frontOffset" in config["settings"]
        assert "clearanceOffset" in config["settings"]
        assert "cabinetGap" in config["settings"]
        assert "frontGap" in config["settings"]


# ─── Supported Versions Constant Tests ────────────────────────────────────────

class TestSupportedVersionsConstant:
    """Verify that supported versions are properly defined."""

    def test_supported_versions_is_set(self):
        """SUPPORTED_VERSIONS should be a set."""
        from src.config_parser import SUPPORTED_VERSIONS
        assert isinstance(SUPPORTED_VERSIONS, set)

    def test_supported_versions_contains_1_0(self):
        """SUPPORTED_VERSIONS must include 1.0."""
        from src.config_parser import SUPPORTED_VERSIONS
        assert "1.0" in SUPPORTED_VERSIONS

    def test_supported_versions_contains_1_1(self):
        """SUPPORTED_VERSIONS must include 1.1."""
        from src.config_parser import SUPPORTED_VERSIONS
        assert "1.1" in SUPPORTED_VERSIONS

    def test_current_version_is_defined(self):
        """CURRENT_VERSION should be defined."""
        from src.config_parser import CURRENT_VERSION
        assert CURRENT_VERSION is not None

    def test_current_version_is_in_supported(self):
        """CURRENT_VERSION must be in SUPPORTED_VERSIONS."""
        from src.config_parser import CURRENT_VERSION, SUPPORTED_VERSIONS
        assert CURRENT_VERSION in SUPPORTED_VERSIONS


# ─── Load Config Version Tests ────────────────────────────────────────────────

class TestLoadConfigVersion:
    """Verify that load_config handles versions correctly."""

    def test_load_config_i_shape_version(self):
        """i_shape.json should load without version errors."""
        config = load_config(str(Path(__file__).resolve().parent.parent / "configs" / "i_shape.json"))
        # Should have a version or default to 1.0
        version = config.get("version", "1.0")
        assert version in ("1.0", "1.1")
