"""Unit tests for validators — runs without Blender."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from src.config_parser import load_config
from src.validators import validate_config, compute_total_width


def test_validate_i_shape_no_warnings():
    config = load_config(str(Path(__file__).resolve().parent.parent / "configs" / "i_shape.json"))
    warnings = validate_config(config)
    # i_shape has no corners, should have no warnings
    assert warnings == []


def test_validate_corner_not_last():
    config = {
        "version": "1.0",
        "settings": {},
        "runs": [
            {
                "base": [
                    {"type": "base-door", "width": 600},
                    {"type": "corner-blind", "width": 900},
                    {"type": "base-door", "width": 600},
                ]
            }
        ]
    }
    warnings = validate_config(config)
    assert any("corner cabinet should be first or last" in w for w in warnings)


def test_validate_missing_turn_after_corner():
    config = {
        "version": "1.0",
        "settings": {},
        "runs": [
            {
                "base": [
                    {"type": "corner-blind", "width": 900},
                ]
            },
            {
                "base": [
                    {"type": "base-door", "width": 600},
                ]
            }
        ]
    }
    warnings = validate_config(config)
    assert any("missing 'turn' direction" in w for w in warnings)


def test_validate_turn_present_after_corner():
    config = {
        "version": "1.0",
        "settings": {},
        "runs": [
            {
                "base": [
                    {"type": "corner-blind", "width": 900},
                ]
            },
            {
                "turn": "left",
                "base": [
                    {"type": "base-door", "width": 600},
                ]
            }
        ]
    }
    warnings = validate_config(config)
    assert not any("missing 'turn' direction" in w for w in warnings)


def test_compute_total_width():
    config = {
        "version": "1.0",
        "settings": {"cabinetGap": 0, "frontGap": 2},
        "runs": [
            {
                "base": [
                    {"type": "base-door", "width": 600},
                    {"type": "base-door", "width": 600},
                ]
            }
        ]
    }
    widths = compute_total_width(config)
    # With cabinetGap=0: 600 + 0 + 600 = 1200mm
    assert widths["run[0].base"] == 1200


def test_compute_total_width_i_shape():
    config = load_config(str(Path(__file__).resolve().parent.parent / "configs" / "i_shape.json"))
    widths = compute_total_width(config)
    # 50 + 600 + 800 + 600 + 600 + 50 = 2700 + 5 * 0 (cabinetGap) = 2700
    assert widths["run[0].base"] == 2700
