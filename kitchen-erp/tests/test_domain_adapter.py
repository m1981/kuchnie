# tests/test_domain_adapter.py
"""ADR-011 phase 2: Cabinet -> kuchnie_core.CabinetInstance adapter.

Expected panel dimensions are HAND-COMPUTED from the documented construction
method (ConstructionMethod defaults: 18mm sides/bottom/front, 3mm back,
8mm groove, 3mm door gap, 100mm plinth) — never re-derived by running the
code under test.
"""
import pytest
from kitchen_erp.core.models import Material, HardwareSet, ProjectDefaults, Cabinet
from kitchen_erp.core.domain_adapter import (
    ERP_KIND_TO_DOMAIN,
    to_kuchnie_core,
    quantities_from_decomposition,
)
from kuchnie_core.decomposer import decompose


@pytest.fixture
def defaults():
    return ProjectDefaults(
        corpus_mat=Material(id=1, name="Egger W980", price_per_unit=10.0, unit="m2"),
        front_mat=Material(id=2, name="Front MDF", price_per_unit=20.0, unit="m2"),
        back_mat=Material(id=3, name="HDF", price_per_unit=5.0, unit="m2"),
        edge_band_mat=Material(id=4, name="ABS", price_per_unit=1.0, unit="lm"),
        hinge_sys=HardwareSet(id=1, name="Hinge", price_per_set=2.0),
        drawer_sys=HardwareSet(id=2, name="Drawer", price_per_set=30.0),
    )


def make_cabinet(**kw):
    base = dict(
        name="Test", type="BASE", module_kind="BASE_CABINET",
        width_mm=600.0, height_mm=720.0, depth_mm=510.0,
        door_count=1, drawer_count=0,
    )
    base.update(kw)
    return Cabinet(**base)


class TestMapping:
    def test_supported_kinds_route_to_domain_types(self, defaults):
        assert ERP_KIND_TO_DOMAIN == {
            "BASE_CABINET": "dolna_drzwiowa",
            "WALL_CABINET": "gorna_drzwiowa",
            "DRAWER_BASE": "dolna_szufladowa",
        }

    def test_unsupported_kind_returns_none(self, defaults):
        for kind in ["DISHWASHER", "SIDE_PANEL", "SINK_BASE", "OVEN_BASE", "HOOD"]:
            cab = make_cabinet(module_kind=kind)
            assert to_kuchnie_core(cab, defaults) is None

    def test_field_mapping(self, defaults):
        cab = make_cabinet(module_kind="WALL_CABINET", type="WALL",
                           width_mm=1000.0, height_mm=500.0, depth_mm=300.0)
        inst = to_kuchnie_core(cab, defaults)
        assert inst.type == "gorna_drzwiowa"
        assert (inst.width_mm, inst.height_mm, inst.depth_mm) == (1000, 500, 300)
        assert inst.body_material == "Egger W980"
        assert inst.back_material == "HDF"
        assert inst.front_material == "Front MDF"
        assert inst.fronts == [{"id": "D1", "typ": "drzwiowy_lewy"}]

    def test_front_override_wins(self, defaults):
        override = Material(id=9, name="Lacquered", price_per_unit=50.0, unit="m2")
        cab = make_cabinet()
        cab.override_front_mat = override
        inst = to_kuchnie_core(cab, defaults)
        assert inst.front_material == "Lacquered"

    def test_corpus_override_wins(self, defaults):
        """wk-aa3e159c: override_corpus_mat reaches the domain instance, so
        rozrys/edging/purchasing name the actual board, mirroring the front."""
        override = Material(id=9, name="MDF Wilgocioodporna", price_per_unit=55.0, unit="m2")
        cab = make_cabinet()
        cab.override_corpus_mat = override
        inst = to_kuchnie_core(cab, defaults)
        assert inst.body_material == "MDF Wilgocioodporna"

    def test_drawer_base_synthesizes_linked_drawer_fronts(self, defaults):
        cab = make_cabinet(module_kind="DRAWER_BASE", drawer_count=3, door_count=0)
        inst = to_kuchnie_core(cab, defaults)
        assert inst.type == "dolna_szufladowa"
        assert len(inst.drawers) == 3 and len(inst.fronts) == 3
        assert all(f["typ"] == "szufladowy" for f in inst.fronts)
        # Fronts fill side height (720-100=620) minus 4 x 3mm gaps: 608/3 each
        assert inst.drawers[0]["wysokosc"] == pytest.approx(608 / 3)
        # Every front is linked to its drawer (decompose reads the height via powiazany)
        assert {f["powiazany"] for f in inst.fronts} == {d["id"] for d in inst.drawers}

    def test_zero_doors_synthesizes_no_fronts(self, defaults):
        inst = to_kuchnie_core(make_cabinet(door_count=0), defaults)
        assert inst.fronts == []


class TestQuantities:
    def test_wall_cabinet_quantities_hand_computed(self, defaults):
        """Wall 1000W x 500H x 300D, 1 door, gorna_drzwiowa construction:
        sides 2x(300x500), top+bottom 2x(964x300), back 978x478,
        door 996x494 (G12 2mm reveal). Corpus edging: 2x500 + 2x964 =
        2928mm. Front edging: 2x996 + 2x494 = 2980mm."""
        cab = make_cabinet(module_kind="WALL_CABINET", type="WALL",
                           width_mm=1000.0, height_mm=500.0, depth_mm=300.0)
        q = quantities_from_decomposition(decompose(to_kuchnie_core(cab, defaults)))
        assert q.corpus_m2 == pytest.approx(0.30 + 0.5784)
        assert q.back_m2 == pytest.approx(0.467484)
        assert q.front_m2 == pytest.approx(0.492024)
        assert q.corpus_edge_lm == pytest.approx(2.928)
        assert q.front_edge_lm == pytest.approx(2.980)

    def test_base_cabinet_quantities_hand_computed(self, defaults):
        """Base 600W x 720H x 510D, 1 door, dolna_drzwiowa construction:
        side height 720-100(plinth)=620; sides 2x(510x620), bottom 564x510
        (no top panel), back 578x598, door 596x614 (G12 2mm reveal).
        Corpus edging: 2x620 + 564 = 1804mm. Front: 2x596 + 2x614 = 2420mm."""
        q = quantities_from_decomposition(decompose(to_kuchnie_core(make_cabinet(), defaults)))
        assert q.corpus_m2 == pytest.approx(0.6324 + 0.28764)
        assert q.back_m2 == pytest.approx(0.345644)
        assert q.front_m2 == pytest.approx(0.365944)
        assert q.corpus_edge_lm == pytest.approx(1.804)
        assert q.front_edge_lm == pytest.approx(2.420)

    def test_back_panel_never_banded(self, defaults):
        result = decompose(to_kuchnie_core(make_cabinet(), defaults))
        back = next(p for p in result.panels if p.name == "Plecy")
        assert back.banded_edges == {}

    def test_drawer_box_panels_bucket_separately(self):
        """Drawer-box board (DRAWER_BACK/DRAWER_BASE) must not be folded
        into corpus_m2 (wk-c9e848a3): 462x160 back + 465x490 base =
        0.07392 + 0.227850 m2 in drawer_box_m2, corpus untouched."""
        from kuchnie_core.model import DecompositionResult, Panel, PanelRole
        result = DecompositionResult(cabinet_id="t", cabinet_type="dolna_legrabox")
        result.panels.append(Panel(
            id="t_drawer_S1_back", name="Szuflada S1 — tył",
            material="plyta_16mm", thickness_mm=16,
            width_mm=462, height_mm=160, banded_edges={},
            quantity=1, role=PanelRole.DRAWER_BACK,
        ))
        result.panels.append(Panel(
            id="t_drawer_S1_base", name="Szuflada S1 — dno",
            material="plyta_16mm", thickness_mm=16,
            width_mm=465, height_mm=490, banded_edges={},
            quantity=1, role=PanelRole.DRAWER_BASE,
        ))
        q = quantities_from_decomposition(result)
        assert q.drawer_box_m2 == pytest.approx(0.07392 + 0.22785)
        assert q.corpus_m2 == 0.0
        assert q.corpus_edge_lm == 0.0

    def test_corner_blind_front_parts_price_as_front(self):
        """FRONT_BLIND and FILLER (ADR-014) are front material — they bucket
        into front_m2/front_edge_lm, never corpus: blind 560x614 + filler
        50x614 = 0.34384 + 0.0307 m2."""
        from kuchnie_core.model import DecompositionResult, EdgeBand, Panel, PanelRole
        result = DecompositionResult(cabinet_id="t", cabinet_type="dolna_narozna_slepa")
        result.panels.append(Panel(
            id="t_front_slepy", name="Front ślepy",
            material="K5307_18", thickness_mm=18,
            width_mm=560, height_mm=614,
            banded_edges={"right": EdgeBand(material="abs", thickness_mm=2, length_mm=614)},
            quantity=1, role=PanelRole.FRONT_BLIND,
        ))
        result.panels.append(Panel(
            id="t_listwa", name="Listwa narożna",
            material="K5307_18", thickness_mm=18,
            width_mm=50, height_mm=614,
            banded_edges={"left": EdgeBand(material="abs", thickness_mm=2, length_mm=614)},
            quantity=1, role=PanelRole.FILLER,
        ))
        q = quantities_from_decomposition(result)
        assert q.front_m2 == pytest.approx(0.34384 + 0.0307)
        assert q.front_edge_lm == pytest.approx(1.228)
        assert q.corpus_m2 == 0.0
        assert q.corpus_edge_lm == 0.0
