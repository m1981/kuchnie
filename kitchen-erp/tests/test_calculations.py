# tests/test_calculations.py
"""Deterministic pricing math for the canonical BOM path (ADR-011).

Expected values are HAND-COMPUTED from the WALL_CABINET recipe formulas and
the default hardware rules — never re-derived with the code under test.
"""
import pytest
from kitchen_erp.core.models import Material, HardwareSet, ProjectDefaults, Cabinet
from kitchen_erp.core.bom_generator import BOMGenerator
from kitchen_erp.core.rules_engine import RulesEngine, get_default_hardware_rules


@pytest.fixture(autouse=True)
def pinned_rules():
    """Pin the rules engine to shipped defaults; unit math must not depend
    on whatever HardwareRule rows the app database happens to hold."""
    RulesEngine._cached_rules = get_default_hardware_rules()
    yield
    RulesEngine.clear_cache()


def test_wall_cabinet_bom_pricing():
    corpus_mat = Material(id=1, name="Corpus", price_per_unit=10.0, unit="m2")
    front_mat = Material(id=2, name="Front", price_per_unit=20.0, unit="m2")
    back_mat = Material(id=3, name="Back", price_per_unit=5.0, unit="m2")
    edge_mat = Material(id=4, name="Edge", price_per_unit=1.0, unit="lm")
    hinge_sys = HardwareSet(id=1, name="Hinge", price_per_set=2.0)
    drawer_sys = HardwareSet(id=2, name="Drawer", price_per_set=30.0)

    defaults = ProjectDefaults(
        corpus_mat=corpus_mat,
        front_mat=front_mat,
        back_mat=back_mat,
        edge_band_mat=edge_mat,
        hinge_sys=hinge_sys,
        drawer_sys=drawer_sys,
    )

    # Wall cabinet 1000W x 500H x 300D, 1 door (within recipe limits).
    cabinet = Cabinet(
        name="Test Wall",
        module_kind="WALL_CABINET",
        type="WALL",
        width_mm=1000.0,
        height_mm=500.0,
        depth_mm=300.0,
        door_count=1,
        drawer_count=0,
    )

    tree = BOMGenerator(cabinet, defaults).generate()
    parts = {p.name: p for p in tree.get_all_parts()}

    # Recipe: corpus_m2 = (2*H*D + 2*W*D + W*D)/1e6
    #        = (2*500*300 + 2*1000*300 + 1000*300)/1e6 = 1.2 m2 @ $10 = $12.00
    assert parts["Corpus: Corpus"].quantity_net == pytest.approx(1.2)
    assert parts["Corpus: Corpus"].cost == pytest.approx(12.0)

    # back_m2 = H*W/1e6 = 0.5 m2 @ $5 = $2.50
    assert parts["Back panel: Back"].cost == pytest.approx(2.5)

    # front_m2 = H*W/1e6 = 0.5 m2 @ $20 = $10.00 (1 door -> front present)
    assert parts["Front: Front"].cost == pytest.approx(10.0)

    # Edging: front 2*(W+H)/1000 = 3.0 lm; corpus (2*H + 3*W)/1000 = 4.0 lm
    # total 7.0 lm @ $0.80 = $5.60
    assert parts["Edge banding: Generic ABS"].quantity_net == pytest.approx(7.0)
    assert parts["Edge banding: Generic ABS"].cost == pytest.approx(5.6)

    # CNC: cutting 2.2 m2 @ $15 = $33.00; edgebanding 7.0 lm @ $4.50 = $31.50
    assert parts["CNC Service: Cutting & Nesting"].cost == pytest.approx(33.0)
    assert parts["CNC Service: Edgebanding PUR"].cost == pytest.approx(31.5)

    # Hardware (default rules): is_wall -> 2 brackets @ $3 = $6.00
    # has_doors x1 -> 2 hinges @ $15 = $30.00, 1 bumper @ $0.20, 1 handle @ $25
    assert parts["Wall mounting brackets"].cost == pytest.approx(6.0)
    assert parts["Door hinges"].cost == pytest.approx(30.0)
    assert parts["Door bumpers"].cost == pytest.approx(0.2)
    assert parts["Handle (Uchwyt)"].cost == pytest.approx(25.0)

    # No plinth on a WALL cabinet.
    assert not any("Plinth" in n for n in parts)

    # Grand total, by hand: 12 + 2.5 + 10 + 5.6 + 33 + 31.5 + 6 + 30 + 0.2 + 25
    assert tree.cost == pytest.approx(155.80)
