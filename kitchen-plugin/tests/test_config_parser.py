"""Unit tests for config_parser — runs without Blender."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from src.config_parser import load_config, _apply_defaults, _validate, mm_to_m


def test_mm_to_m():
    assert mm_to_m(1000) == 1.0
    assert mm_to_m(600) == 0.6
    assert mm_to_m(2) == 0.002
    assert mm_to_m(0) == 0.0


def test_apply_defaults():
    config = {"runs": []}
    _apply_defaults(config)
    assert config["settings"]["baseBodyHeight"] == 720
    assert config["settings"]["cabinetGap"] == 0
    assert config["settings"]["frontGap"] == 2
    assert config["settings"]["wallDepth"] == 300


def test_validate_missing_runs():
    with pytest.raises(ValueError, match="must have 'runs'"):
        _validate({})


def test_validate_empty_run():
    with pytest.raises(ValueError, match="at least one of"):
        _validate({"runs": [{"label": "empty"}], "settings": {}})


def test_validate_missing_type():
    with pytest.raises(ValueError, match="missing 'type'"):
        _validate({
            "runs": [{"base": [{"width": 600}]}],
            "settings": {}
        })


def test_validate_unknown_type():
    with pytest.raises(ValueError, match="unknown type"):
        _validate({
            "runs": [{"base": [{"type": "unknown", "width": 600}]}],
            "settings": {}
        })


def test_validate_missing_width():
    with pytest.raises(ValueError, match="missing 'width'"):
        _validate({
            "runs": [{"base": [{"type": "base-door"}]}],
            "settings": {}
        })


def test_validate_zero_width():
    with pytest.raises(ValueError, match="width must be > 0"):
        _validate({
            "runs": [{"base": [{"type": "base-door", "width": 0}]}],
            "settings": {}
        })


def test_validate_blind_depth_exceeds_width():
    with pytest.raises(ValueError, match="blindDepth.*must be < width"):
        _validate({
            "runs": [{"base": [
                {"type": "corner-blind", "width": 600, "blindDepth": 700}
            ]}],
            "settings": {}
        })


def test_load_config_i_shape():
    config = load_config(str(Path(__file__).resolve().parent.parent / "configs" / "i_shape.json"))
    assert config["name"] == "I-Shape Test Kitchen 3.0m"
    assert len(config["runs"]) == 1
    assert len(config["runs"][0]["base"]) == 6
    assert len(config["runs"][0]["upper"]) == 5


def test_load_config_types():
    config = load_config(str(Path(__file__).resolve().parent.parent / "configs" / "i_shape.json"))
    base_types = [c["type"] for c in config["runs"][0]["base"]]
    assert "filler" in base_types
    assert "base-drawer-door" in base_types
    assert "base-sink" in base_types
    assert "base-drawers" in base_types
    assert "base-door" in base_types


# ─── Construction Parameter Tests ────────────────────────────────────────────

def test_construction_defaults():
    """Default construction parameters should be set."""
    config = {"runs": []}
    _apply_defaults(config)
    assert config["settings"]["corpusThickness"] == 18
    assert config["settings"]["frontThickness"] == 19
    assert config["settings"]["backThickness"] == 3
    assert config["settings"]["grooveOffset"] == 10
    assert config["settings"]["frontOverlay"] == 2


def test_construction_custom_values():
    """Custom construction parameters should override defaults."""
    config = {
        "runs": [],
        "settings": {
            "corpusThickness": 16,
            "frontThickness": 18,
            "backThickness": 5,
            "grooveOffset": 8,
            "frontOverlay": 3,
        }
    }
    _apply_defaults(config)
    assert config["settings"]["corpusThickness"] == 16
    assert config["settings"]["frontThickness"] == 18
    assert config["settings"]["backThickness"] == 5
    assert config["settings"]["grooveOffset"] == 8
    assert config["settings"]["frontOverlay"] == 3


def test_construction_partial_override():
    """Partial override should keep defaults for unspecified."""
    config = {
        "runs": [],
        "settings": {
            "corpusThickness": 16,
        }
    }
    _apply_defaults(config)
    assert config["settings"]["corpusThickness"] == 16
    assert config["settings"]["frontThickness"] == 19  # default
    assert config["settings"]["backThickness"] == 3    # default


def test_construction_validation_positive():
    """Construction parameters must be positive."""
    from src.config_parser import _validate_settings
    with pytest.raises(ValueError, match="corpusThickness.*must be > 0"):
        _validate_settings({"corpusThickness": 0})
    with pytest.raises(ValueError, match="frontThickness.*must be > 0"):
        _validate_settings({"frontThickness": -1})
    with pytest.raises(ValueError, match="backThickness.*must be > 0"):
        _validate_settings({"backThickness": 0})


def test_construction_validation_reasonable():
    """Construction parameters should have reasonable limits."""
    from src.config_parser import _validate_settings
    # Corpus thickness 10-30mm is reasonable
    with pytest.raises(ValueError, match="corpusThickness"):
        _validate_settings({"corpusThickness": 5})   # too thin
    with pytest.raises(ValueError, match="corpusThickness"):
        _validate_settings({"corpusThickness": 50})  # too thick
    # Front thickness 10-30mm is reasonable
    with pytest.raises(ValueError, match="frontThickness"):
        _validate_settings({"frontThickness": 5})
    # Back thickness 2-10mm is reasonable
    with pytest.raises(ValueError, match="backThickness"):
        _validate_settings({"backThickness": 1})
    with pytest.raises(ValueError, match="backThickness"):
        _validate_settings({"backThickness": 20})


def test_construction_in_config_file():
    """Loading config with construction params should work."""
    import json
    import tempfile
    config = {
        "version": "1.1",
        "settings": {
            "corpusThickness": 16,
            "frontThickness": 18,
        },
        "runs": [{"base": [{"type": "base-door", "width": 600}]}]
    }
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config, f)
        f.flush()
        loaded = load_config(f.name)
    assert loaded["settings"]["corpusThickness"] == 16
    assert loaded["settings"]["frontThickness"] == 18
    assert loaded["settings"]["backThickness"] == 3  # default
