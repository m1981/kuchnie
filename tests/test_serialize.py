"""Intermediate format — JSON round-trip tests.

Proves: Kitchen → JSON → Kitchen preserves all data.
This is the contract between kitchen-plugin, render-service, and kitchen-cli.
"""

import json
import tempfile
from pathlib import Path

from kuchnie_core.loader import load_kitchen
from kuchnie_core.serialize import (
    kitchen_to_dict,
    kitchen_to_json,
    kitchen_to_json_str,
    kitchen_from_dict,
    kitchen_from_json,
    kitchen_from_json_str,
)

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def _original() -> object:
    return load_kitchen(FIXTURES / "kitchen_01.yaml")


# ── dict round-trip ─────────────────────────────────────────────

def test_dict_roundtrip_preserves_project():
    kitchen = _original()
    d = kitchen_to_dict(kitchen)
    restored = kitchen_from_dict(d)
    assert restored.version == kitchen.version
    assert restored.project_name == kitchen.project_name
    assert restored.created == kitchen.created


def test_dict_roundtrip_preserves_rows():
    kitchen = _original()
    d = kitchen_to_dict(kitchen)
    restored = kitchen_from_dict(d)
    assert len(restored.rows) == len(kitchen.rows)
    assert restored.rows[0].id == kitchen.rows[0].id
    assert restored.rows[0].wall_width_mm == kitchen.rows[0].wall_width_mm


def test_dict_roundtrip_preserves_cabinets():
    kitchen = _original()
    d = kitchen_to_dict(kitchen)
    restored = kitchen_from_dict(d)
    cabs = restored.rows[0].cabinets
    assert len(cabs) == 2
    assert cabs[0].id == "K01"
    assert cabs[0].width_mm == 800
    assert cabs[0].body_material == "swiss_krono.U119_VL"


def test_dict_roundtrip_preserves_worktops():
    kitchen = _original()
    d = kitchen_to_dict(kitchen)
    restored = kitchen_from_dict(d)
    assert len(restored.worktops) == 1
    assert restored.worktops[0].material == "egger.F2060_ST87"


# ── JSON string round-trip ──────────────────────────────────────

def test_json_str_roundtrip():
    kitchen = _original()
    text = kitchen_to_json_str(kitchen)
    restored = kitchen_from_json_str(text)
    assert restored.project_name == kitchen.project_name
    assert len(restored.rows[0].cabinets) == 2


def test_json_str_is_valid_json():
    text = kitchen_to_json_str(_original())
    data = json.loads(text)
    assert "version" in data
    assert "rows" in data


# ── JSON file round-trip ────────────────────────────────────────

def test_json_file_roundtrip():
    kitchen = _original()
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = Path(f.name)
    try:
        kitchen_to_json(kitchen, path)
        restored = kitchen_from_json(path)
        assert restored.project_name == kitchen.project_name
        assert len(restored.rows) == 1
        assert restored.rows[0].cabinets[1].type == "gorna_drzwiowa"
    finally:
        path.unlink()


# ── JSON is self-contained ──────────────────────────────────────

def test_json_contains_cabinet_details():
    """The intermediate format must contain full cabinet definitions,
    not just references — it's self-contained."""
    text = kitchen_to_json_str(_original())
    data = json.loads(text)
    cab = data["rows"][0]["cabinets"][0]
    assert "width_mm" in cab
    assert "body_material" in cab
    assert "drawers" in cab
    assert "fronts" in cab
