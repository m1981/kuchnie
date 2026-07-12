# tests/test_calculations.py
"""Deterministic pricing math for the canonical BOM path (ADR-011 phase 2).

Panel quantities come from kuchnie_core construction methods (gorna_drzwiowa);
expected values are HAND-COMPUTED from the documented construction (18mm
board, 8mm groove, 3mm gaps) and the default hardware rules — never
re-derived with the code under test.
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

    # Panels per gorna_drzwiowa construction (18mm board, 8mm groove):
    # corpus = sides 2x(300x500) + top/bottom 2x(964x300)
    #        = 0.30 + 0.5784 = 0.8784 m2 @ $10 = $8.784
    assert parts["Corpus: Corpus"].quantity_net == pytest.approx(0.8784)
    assert parts["Corpus: Corpus"].cost == pytest.approx(8.784)

    # back = 978x478 (in groove, 2mm luz: 1000-36+16-2 x 500-36+16-2)
    #      = 0.467484 m2 @ $5 = $2.33742
    assert parts["Back panel: Back"].cost == pytest.approx(2.33742)

    # door = 994x494 (3mm gaps) = 0.491036 m2 @ $20 = $9.82072
    assert parts["Front: Front"].cost == pytest.approx(9.82072)

    # Edging from real banded edges: corpus 2x500 + 2x964 = 2.928 lm;
    # door all 4 edges 2x994 + 2x494 = 2.976 lm; total 5.904 lm @ $0.80 = $4.7232
    assert parts["Edge banding: Generic ABS"].quantity_net == pytest.approx(5.904)
    assert parts["Edge banding: Generic ABS"].cost == pytest.approx(4.7232)

    # CNC: cutting 1.83692 m2 @ $15 = $27.5538; edgebanding 5.904 lm @ $4.50 = $26.568
    assert parts["CNC Service: Cutting & Nesting"].cost == pytest.approx(27.5538)
    assert parts["CNC Service: Edgebanding PUR"].cost == pytest.approx(26.568)

    # Hardware (default rules): is_wall -> 2 brackets @ $3 = $6.00
    # has_doors x1 -> 2 hinges @ $15 = $30.00, 1 bumper @ $0.20, 1 handle @ $25
    assert parts["Wall mounting brackets"].cost == pytest.approx(6.0)
    assert parts["Door hinges"].cost == pytest.approx(30.0)
    assert parts["Door bumpers"].cost == pytest.approx(0.2)
    assert parts["Handle (Uchwyt)"].cost == pytest.approx(25.0)

    # No plinth on a WALL cabinet.
    assert not any("Plinth" in n for n in parts)

    # Grand total, by hand:
    # 8.784 + 2.33742 + 9.82072 + 4.7232 + 27.5538 + 26.568 + 6 + 30 + 0.2 + 25
    assert tree.cost == pytest.approx(140.98714)


def test_gated_front_carries_no_ghost_costs():
    """A doorless, drawerless BASE cabinet gets NO front material — and no
    front edging or front CNC either (the old recipe path charged edging and
    cutting for a front it never added)."""
    corpus_mat = Material(id=1, name="Corpus", price_per_unit=10.0, unit="m2")
    front_mat = Material(id=2, name="Front", price_per_unit=20.0, unit="m2")
    back_mat = Material(id=3, name="Back", price_per_unit=5.0, unit="m2")
    edge_mat = Material(id=4, name="Edge", price_per_unit=1.0, unit="lm")
    defaults = ProjectDefaults(
        corpus_mat=corpus_mat, front_mat=front_mat, back_mat=back_mat,
        edge_band_mat=edge_mat,
        hinge_sys=HardwareSet(id=1, name="H", price_per_set=2.0),
        drawer_sys=HardwareSet(id=2, name="D", price_per_set=30.0),
    )
    cabinet = Cabinet(
        name="Open base", module_kind="BASE_CABINET", type="BASE",
        width_mm=600.0, height_mm=720.0, depth_mm=510.0,
        door_count=0, drawer_count=0,
    )
    tree = BOMGenerator(cabinet, defaults).generate()
    parts = {p.name: p for p in tree.get_all_parts()}

    assert not any(n.startswith("Front:") for n in parts)
    # Edging is corpus-only: sides 2x620 + bottom 564 = 1.804 lm
    assert parts["Edge banding: Generic ABS"].quantity_net == pytest.approx(1.804)
    # CNC cutting covers corpus + back only: 0.92004 + 0.345644 = 1.265684 m2
    assert parts["CNC Service: Cutting & Nesting"].quantity_net == pytest.approx(1.265684)
