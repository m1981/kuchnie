"""Unit tests for L-shape layout — runs without Blender."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from src.config_parser import load_config
from src.validators import validate_config, compute_total_width


def test_load_config_l_shape():
    config = load_config(str(Path(__file__).resolve().parent.parent / "configs" / "l_shape.json"))
    assert config["name"] == "L-Shape Kitchen 3.2m + 1.8m"
    assert len(config["runs"]) == 2


def test_l_shape_run_structure():
    config = load_config(str(Path(__file__).resolve().parent.parent / "configs" / "l_shape.json"))
    run0 = config["runs"][0]
    run1 = config["runs"][1]

    assert run0["label"] == "back wall"
    assert run1["label"] == "left wall"
    assert run1["turn"] == "left"


def test_l_shape_cabinet_counts():
    config = load_config(str(Path(__file__).resolve().parent.parent / "configs" / "l_shape.json"))
    assert len(config["runs"][0]["base"]) == 6
    assert len(config["runs"][0]["upper"]) == 6
    assert len(config["runs"][1]["base"]) == 4
    assert len(config["runs"][1]["upper"]) == 4


def test_l_shape_has_corner():
    config = load_config(str(Path(__file__).resolve().parent.parent / "configs" / "l_shape.json"))
    base_types = [c["type"] for c in config["runs"][0]["base"]]
    assert "corner-blind" in base_types


def test_l_shape_corner_is_last():
    config = load_config(str(Path(__file__).resolve().parent.parent / "configs" / "l_shape.json"))
    last_base = config["runs"][0]["base"][-1]
    assert last_base["type"] == "corner-blind"
    assert last_base["blindDepth"] == 400


def test_l_shape_turn_present():
    config = load_config(str(Path(__file__).resolve().parent.parent / "configs" / "l_shape.json"))
    assert config["runs"][1]["turn"] == "left"


def test_l_shape_no_warnings():
    config = load_config(str(Path(__file__).resolve().parent.parent / "configs" / "l_shape.json"))
    warnings = validate_config(config)
    assert warnings == []


def test_l_shape_run_widths():
    config = load_config(str(Path(__file__).resolve().parent.parent / "configs" / "l_shape.json"))
    widths = compute_total_width(config)

    # Run 0 base: 50+600+600+800+600+900 + 5*0 (cabinetGap) = 3550mm
    assert widths["run[0].base"] == 3550

    # Run 1 base: 600+400+800+50 + 3*0 (cabinetGap) = 1850mm
    assert widths["run[1].base"] == 1850


def test_l_shape_has_tall_cabinet():
    config = load_config(str(Path(__file__).resolve().parent.parent / "configs" / "l_shape.json"))
    base_types = [c["type"] for c in config["runs"][0]["base"]]
    assert "tall-oven" in base_types


def test_l_shape_custom_drawer_heights():
    config = load_config(str(Path(__file__).resolve().parent.parent / "configs" / "l_shape.json"))
    drawers_cab = config["runs"][1]["base"][1]
    assert drawers_cab["type"] == "base-drawers"
    assert drawers_cab["drawers"] == [120, 160, 200]


def test_l_shape_gola_handle():
    config = load_config(str(Path(__file__).resolve().parent.parent / "configs" / "l_shape.json"))
    drawers_cab = config["runs"][1]["base"][1]
    assert drawers_cab["handle"]["type"] == "gola"
