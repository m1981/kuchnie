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

    # door = 996x494 (G12 2mm side reveal) = 0.492024 m2 @ $20 = $9.84048
    assert parts["Front: Front"].cost == pytest.approx(9.84048)

    # Edging from real banded edges: corpus 2x500 + 2x964 = 2.928 lm;
    # door all 4 edges 2x996 + 2x494 = 2.980 lm; total 5.908 lm priced at
    # the project's edge_band_mat ($1.00/lm), not a hardcode (wk-aa3e159c)
    assert parts["Edge banding: Edge"].quantity_net == pytest.approx(5.908)
    assert parts["Edge banding: Edge"].cost == pytest.approx(5.908)

    # CNC: cutting 1.837908 m2 @ $15 = $27.56862; edgebanding 5.908 lm @ $4.50 = $26.586
    assert parts["CNC Service: Cutting & Nesting"].cost == pytest.approx(27.56862)
    assert parts["CNC Service: Edgebanding PUR"].cost == pytest.approx(26.586)

    # Hardware (default rules): is_wall -> 2 brackets @ $3 = $6.00
    # has_doors x1 -> 2 hinges @ $15 = $30.00, 1 bumper @ $0.20, 1 handle @ $25
    assert parts["Wall mounting brackets"].cost == pytest.approx(6.0)
    assert parts["Door hinges"].cost == pytest.approx(30.0)
    assert parts["Door bumpers"].cost == pytest.approx(0.2)
    assert parts["Handle (Uchwyt)"].cost == pytest.approx(25.0)

    # No plinth on a WALL cabinet.
    assert not any("Plinth" in n for n in parts)

    # Grand total, by hand:
    # 8.784 + 2.33742 + 9.84048 + 5.908 + 27.56862 + 26.586 + 6 + 30 + 0.2 + 25
    assert tree.cost == pytest.approx(142.22452)


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
    assert parts["Edge banding: Edge"].quantity_net == pytest.approx(1.804)
    # CNC cutting covers corpus + back only: 0.92004 + 0.345644 = 1.265684 m2
    assert parts["CNC Service: Cutting & Nesting"].quantity_net == pytest.approx(1.265684)


def test_corpus_override_prices_corpus_and_drawer_box_lines():
    """wk-aa3e159c: Cabinet.override_corpus_mat reaches cost (it was gathered
    for price freshness but dead in the BOM). Only the corpus line is
    exercised here — the stand-in drawer-box line shares the same override
    variable but stays latent in this path (see comment below)."""
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
        name="Wet zone", module_kind="DRAWER_BASE", type="BASE",
        width_mm=600.0, height_mm=820.0, depth_mm=560.0,
        door_count=0, drawer_count=2,
    )
    cabinet.override_corpus_mat = Material(
        id=9, name="MDF Wilgocioodporna", price_per_unit=15.0, unit="m2")

    tree = BOMGenerator(cabinet, defaults).generate()
    parts = {p.name: p for p in tree.get_all_parts()}

    # (No drawer-box line here: dolna_szufladowa decomposes no box parts in
    # the BOMGenerator path — boxes attach only in variant derivation.)
    assert "Corpus: MDF Wilgocioodporna" in parts
    assert parts["Corpus: MDF Wilgocioodporna"].unit_price == 15.0
    assert not any(n == "Corpus: Corpus" for n in parts)
