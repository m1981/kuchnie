"""Panel grain axis (G10, tr-9054097f → wk-5dc557d6).

Fronts get vertical grain (GrainAxis.HEIGHT → "pion" in rozrys Usłojenie);
carcass, back, and drawer-box panels stay unconstrained (None → "brak").
The cut-list aggregator must NOT merge otherwise-identical panels that
differ in grain — a merged row would let the optimizer rotate a decor front.
"""

from kuchnie_core.decomposer import decompose
from kuchnie_core.loader import load_cabinet
from kuchnie_core.model import GrainAxis, Panel, PanelRole
from kuchnie_core.export.cutlist_csv import aggregate_panels, pieces_to_csv


# ── Decomposers set grain ────────────────────────────────────────

def test_fronts_have_vertical_grain(k01_path):
    result = decompose(load_cabinet(k01_path))
    fronts = [p for p in result.panels
              if p.role in (PanelRole.FRONT_DOOR, PanelRole.FRONT_DRAWER)]
    assert fronts, "K01 should produce drawer fronts"
    assert all(p.grain == GrainAxis.HEIGHT for p in fronts)


def test_carcass_and_back_have_no_grain(k01_path):
    result = decompose(load_cabinet(k01_path))
    rest = [p for p in result.panels
            if p.role not in (PanelRole.FRONT_DOOR, PanelRole.FRONT_DRAWER)]
    assert rest
    assert all(p.grain is None for p in rest)


def test_door_fronts_have_vertical_grain(g01_path):
    result = decompose(load_cabinet(g01_path))
    doors = [p for p in result.panels if p.role == PanelRole.FRONT_DOOR]
    assert doors, "G01 should produce door fronts"
    assert all(p.grain == GrainAxis.HEIGHT for p in doors)


# ── Aggregation respects grain ───────────────────────────────────

def _panel(pid: str, grain: str | None) -> Panel:
    return Panel(
        id=pid, name="Front", material="K5307_18", thickness_mm=18,
        width_mm=596, height_mm=287, grain=grain,
    )


def test_aggregation_does_not_merge_across_grain():
    pieces = aggregate_panels([
        _panel("a_front", GrainAxis.HEIGHT),
        _panel("b_front", None),
    ])
    assert len(pieces) == 2


def test_aggregation_merges_same_grain():
    pieces = aggregate_panels([
        _panel("a_front", GrainAxis.HEIGHT),
        _panel("b_front", GrainAxis.HEIGHT),
    ])
    assert len(pieces) == 1
    assert pieces[0].quantity == 2
    assert pieces[0].grain == GrainAxis.HEIGHT


# ── CSV emits Usłojenie ──────────────────────────────────────────

def test_csv_uslojenie_column():
    pieces = aggregate_panels([
        _panel("a_front", GrainAxis.HEIGHT),
        _panel("b_front", GrainAxis.WIDTH),
        _panel("c_front", None),
    ])
    csv_text = pieces_to_csv(pieces)
    header, *rows = csv_text.strip().split("\n")
    assert "Usłojenie" in header
    col = header.split(";").index("Usłojenie")
    values = {r.split(";")[col] for r in rows}
    assert values == {"pion", "poziom", "brak"}
