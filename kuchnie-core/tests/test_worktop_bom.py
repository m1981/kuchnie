"""Worktop per-lm BOM position (wk-4c37f4ee).

Laminate model: WorktopSegment length × PLN-per-lm rate for the segment's
material, plus per-piece charges for named cutouts. Expected values are
HAND-COMPUTED — never re-derived by running the code under test. Stone
worktops stay external: an unpriced material folds at 0, same convention
as boards in calculate_bom.
"""

from pathlib import Path

import pytest

from kuchnie_core.bom import worktop_bom_items
from kuchnie_core.kitchen import kitchen_bom
from kuchnie_core.loader import load_kitchen
from kuchnie_core.model import Kitchen, WorktopSegment
from kuchnie_core.serialize import kitchen_from_dict, kitchen_to_dict

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"

WORKTOP_PRICES = {"egger.F2060_ST87": 120.00}   # PLN per lm
CUTOUT_PRICES = {"zlew": 80.00, "plyta": 60.00}  # PLN per piece


def test_worktop_line_hand_computed():
    seg = WorktopSegment(row_id="row_1", length_mm=2400,
                         material="egger.F2060_ST87")
    items = worktop_bom_items([seg], WORKTOP_PRICES)
    assert len(items) == 1
    line = items[0]
    assert line.category == "worktop"
    assert line.unit == "mb"
    assert line.material == "egger.F2060_ST87"
    # 2400mm = 2.4 lm @ 120.00/lm = 288.00
    assert line.measure == pytest.approx(2.4)
    assert line.total == pytest.approx(288.00)


def test_cutout_lines_priced_per_piece():
    seg = WorktopSegment(row_id="row_1", length_mm=2400,
                         material="egger.F2060_ST87",
                         cutouts=["zlew", "plyta"])
    items = worktop_bom_items([seg], WORKTOP_PRICES, CUTOUT_PRICES)
    cutouts = [i for i in items if i.category == "worktop_cutout"]
    assert [c.material for c in cutouts] == ["zlew", "plyta"]
    assert [c.total for c in cutouts] == [pytest.approx(80.00), pytest.approx(60.00)]
    assert all(c.unit == "szt" and c.quantity == 1 for c in cutouts)
    # segment total: 288.00 worktop + 140.00 cutouts = 428.00
    assert sum(i.total for i in items) == pytest.approx(428.00)


def test_unpriced_material_folds_at_zero_stone_stays_external():
    seg = WorktopSegment(row_id="row_1", length_mm=3000, material="granit.Star")
    items = worktop_bom_items([seg], WORKTOP_PRICES)
    assert items[0].total == 0.0
    assert items[0].measure == pytest.approx(3.0)  # quantity still visible


def test_kitchen_bom_includes_worktop_position():
    """The flagship fixture's 2400mm segment lands in kitchen_bom output
    and its cost joins the total."""
    kitchen = load_kitchen(FIXTURES / "kitchen_01.yaml")
    without = kitchen_bom(kitchen)
    with_worktop = kitchen_bom(kitchen, worktop_prices=WORKTOP_PRICES)

    worktop_lines = [i for i in with_worktop.items if i.category == "worktop"]
    assert len(worktop_lines) == 1
    assert worktop_lines[0].total == pytest.approx(288.00)
    assert with_worktop.total_cost == pytest.approx(without.total_cost + 288.00)


def test_serialize_roundtrip_preserves_cutouts():
    kitchen = Kitchen(worktops=[WorktopSegment(
        row_id="row_1", length_mm=2400, material="egger.F2060_ST87",
        cutouts=["zlew"])])
    restored = kitchen_from_dict(kitchen_to_dict(kitchen))
    assert restored.worktops[0].cutouts == ["zlew"]
