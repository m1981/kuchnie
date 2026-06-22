"""Unit tests for U-shape layout — runs without Blender."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from src.config_parser import load_config
from src.validators import validate_config, compute_total_width


def test_load_config_u_shape():
    config = load_config(str(Path(__file__).resolve().parent.parent / "configs" / "u_shape.json"))
    assert config["name"] == "U-Shape Kitchen 3.0m + 2.0m + 3.0m"
    assert len(config["runs"]) == 3


def test_u_shape_run_labels():
    config = load_config(str(Path(__file__).resolve().parent.parent / "configs" / "u_shape.json"))
    labels = [r["label"] for r in config["runs"]]
    assert labels == ["left wall", "back wall", "right wall"]


def test_u_shape_turns():
    config = load_config(str(Path(__file__).resolve().parent.parent / "configs" / "u_shape.json"))
    assert config["runs"][0].get("turn") is None  # first run has no turn
    assert config["runs"][1]["turn"] == "right"
    assert config["runs"][2]["turn"] == "right"


def test_u_shape_cabinet_counts():
    config = load_config(str(Path(__file__).resolve().parent.parent / "configs" / "u_shape.json"))
    assert len(config["runs"][0]["base"]) == 4   # left wall
    assert len(config["runs"][0]["upper"]) == 4
    assert len(config["runs"][1]["base"]) == 3   # back wall
    assert len(config["runs"][1]["upper"]) == 3
    assert len(config["runs"][2]["base"]) == 5   # right wall
    assert len(config["runs"][2]["upper"]) == 3


def test_u_shape_has_two_corners():
    config = load_config(str(Path(__file__).resolve().parent.parent / "configs" / "u_shape.json"))
    corner_count = 0
    for run in config["runs"]:
        for cab in run.get("base", []):
            if cab["type"].startswith("corner-"):
                corner_count += 1
    assert corner_count == 2


def test_u_shape_corners_are_last():
    config = load_config(str(Path(__file__).resolve().parent.parent / "configs" / "u_shape.json"))
    # Run 0: corner-blind should be last
    assert config["runs"][0]["base"][-1]["type"] == "corner-blind"
    # Run 2: corner-blind should be first (it's at the junction)
    assert config["runs"][2]["base"][0]["type"] == "corner-blind"


def test_u_shape_no_warnings():
    config = load_config(str(Path(__file__).resolve().parent.parent / "configs" / "u_shape.json"))
    warnings = validate_config(config)
    assert warnings == []


def test_u_shape_run_widths():
    config = load_config(str(Path(__file__).resolve().parent.parent / "configs" / "u_shape.json"))
    widths = compute_total_width(config)

    # Run 0: 50+600+600+900 + 3 gaps = 2156mm
    assert widths["run[0].base"] == 2156

    # Run 1: 800+600+900 + 2 gaps = 2304mm
    assert widths["run[1].base"] == 2304

    # Run 2: 900+600+600+600+50 + 4 gaps = 2758mm
    assert widths["run[2].base"] == 2758


def test_u_shape_has_tall_and_special():
    config = load_config(str(Path(__file__).resolve().parent.parent / "configs" / "u_shape.json"))
    all_types = []
    for run in config["runs"]:
        for cab in run.get("base", []):
            all_types.append(cab["type"])

    assert "tall-oven" in all_types
    assert "tall-fridge" in all_types
    assert "base-sink" in all_types


def test_u_shape_custom_drawer_heights():
    config = load_config(str(Path(__file__).resolve().parent.parent / "configs" / "u_shape.json"))
    drawers_cab = config["runs"][1]["base"][1]
    assert drawers_cab["type"] == "base-drawers"
    assert drawers_cab["drawers"] == [150, 200, 250]


def test_u_shape_gola_handles():
    config = load_config(str(Path(__file__).resolve().parent.parent / "configs" / "u_shape.json"))
    gola_count = 0
    for run in config["runs"]:
        for cab in run.get("base", []):
            if cab.get("handle", {}).get("type") == "gola":
                gola_count += 1
    assert gola_count == 3  # 3 cabinets with gola handles
