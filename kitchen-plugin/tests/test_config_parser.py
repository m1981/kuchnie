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
