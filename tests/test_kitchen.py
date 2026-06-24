"""Kitchen model + aggregation tests.

Proves: kitchen loads, panels aggregate across cabinets, BOM totals,
row validation catches overflow.
"""

from pathlib import Path

from kuchnie_core.loader import load_kitchen
from kuchnie_core.kitchen import (
    all_panels,
    all_accessories,
    kitchen_bom,
    validate_rows,
    decompose_kitchen,
)
from kuchnie_core.model import Kitchen, Row, CabinetInstance

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def test_load_kitchen():
    kitchen = load_kitchen(FIXTURES / "kitchen_01.yaml")
    assert kitchen.version == "1.0"
    assert kitchen.project_name == "Kuchnia Nowowiejska"
    assert len(kitchen.rows) == 1


def test_row_cabinets_loaded():
    kitchen = load_kitchen(FIXTURES / "kitchen_01.yaml")
    row = kitchen.rows[0]
    assert row.id == "row_1"
    assert len(row.cabinets) == 2
    assert row.cabinets[0].id == "K01"
    assert row.cabinets[1].id == "G01"


def test_worktop_loaded():
    kitchen = load_kitchen(FIXTURES / "kitchen_01.yaml")
    assert len(kitchen.worktops) == 1
    wt = kitchen.worktops[0]
    assert wt.row_id == "row_1"
    assert wt.length_mm == 2400
    assert wt.material == "egger.F2060_ST87"


def test_all_panels_count():
    """K01 produces 6 panels, G01 produces 9 → 15 total."""
    kitchen = load_kitchen(FIXTURES / "kitchen_01.yaml")
    panels = all_panels(kitchen)
    assert len(panels) == 15


def test_all_accessories_count():
    """K01: 3 accessories, G01: 4 accessories → 7 total."""
    kitchen = load_kitchen(FIXTURES / "kitchen_01.yaml")
    accs = all_accessories(kitchen)
    assert len(accs) == 7


def test_kitchen_bom():
    kitchen = load_kitchen(FIXTURES / "kitchen_01.yaml")
    bom = kitchen_bom(kitchen)
    assert bom.cabinet_id == "Kuchnia Nowowiejska"
    assert len(bom.items) > 0
    assert bom.total_cost == round(sum(i.total for i in bom.items), 2)


def test_decompose_kitchen_returns_per_cabinet():
    kitchen = load_kitchen(FIXTURES / "kitchen_01.yaml")
    results = decompose_kitchen(kitchen)
    assert "K01" in results
    assert "G01" in results
    assert len(results["K01"].panels) == 6
    assert len(results["G01"].panels) == 9


# ── Row validation ──────────────────────────────────────────────

def test_row_fits():
    """K01 (800) + G01 (800) = 1600, wall = 2400 → fits with 800 spare."""
    kitchen = load_kitchen(FIXTURES / "kitchen_01.yaml")
    errors = validate_rows(kitchen)
    assert errors == []


def test_row_overflow():
    """Cram two cabinets into a wall that's too narrow."""
    cab = kitchen = load_kitchen(FIXTURES / "kitchen_01.yaml").rows[0].cabinets[0]
    narrow = Kitchen(
        rows=[
            Row(
                id="tight",
                label="Ciasna ściana",
                wall_width_mm=1000,  # too narrow for 800 + 800
                wall_height_mm=2400,
                cabinets=[cab, cab],
            )
        ]
    )
    errors = validate_rows(narrow)
    assert len(errors) >= 1
    assert any("1000mm" in e for e in errors)


def test_row_used_width():
    kitchen = load_kitchen(FIXTURES / "kitchen_01.yaml")
    row = kitchen.rows[0]
    assert row.used_width_mm() == 1600   # K01(800) + G01(800)
    assert row.remaining_mm() == 800     # 2400 - 1600
