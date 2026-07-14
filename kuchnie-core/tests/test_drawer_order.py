"""Drawer-stack order contract (G8, UC-2 step 3 / extension 3a, wk-844f5a9f).

The model consumes drawers BOTTOM-UP. An unequal multi-drawer stack with no
explicit order declaration is ambiguous — the e2e exercise proved it drills
runner rows for the top drawer at the floor (tr-0958807f). Loaders must
reject the ambiguity and normalize declared top-down input.
"""
import pytest

from kuchnie_core.decomposer import decompose
from kuchnie_core.loader import _normalize_drawer_order, load_cabinet


def _stack(heights):
    return [{"id": f"S{i+1}", "typ": "legrabox", "height_code": c,
             "nl": 500, "capacity_kg": 40, "wysokosc": h}
            for i, (c, h) in enumerate(heights)]


# ── the normalizer ───────────────────────────────────────────────

def test_ambiguous_unequal_stack_rejected():
    with pytest.raises(ValueError, match="ambiguous"):
        _normalize_drawer_order(_stack([("M", 140), ("C", 287), ("C", 287)]),
                                None, "D60S3")


def test_equal_stack_needs_no_declaration():
    drawers = _stack([("C", 177), ("C", 177)])
    assert _normalize_drawer_order(drawers, None, "K02") == drawers


def test_top_down_is_reversed_to_model_order():
    drawers = _stack([("M", 140), ("C", 287), ("C", 287)])  # designer: top first
    out = _normalize_drawer_order(drawers, "od_gory", "D60S3")
    assert [d["id"] for d in out] == ["S3", "S2", "S1"]
    assert out[-1]["height_code"] == "M"  # M ends up on TOP (last = highest)
    out_en = _normalize_drawer_order(drawers, "top_down", "D60S3")
    assert out_en == out


def test_bottom_up_passes_through():
    drawers = _stack([("C", 287), ("C", 287), ("M", 140)])
    assert _normalize_drawer_order(drawers, "od_dolu", "X") == drawers
    assert _normalize_drawer_order(drawers, "bottom_up", "X") == drawers


def test_unknown_order_value_rejected():
    with pytest.raises(ValueError, match="unknown drawer order"):
        _normalize_drawer_order(_stack([("M", 140), ("C", 287)]), "gora", "X")


def test_single_drawer_never_ambiguous():
    d = _stack([("M", 140)])
    assert _normalize_drawer_order(d, None, "X") == d


# ── end to end: declared top-down input yields correct drillings ─

def test_top_down_input_puts_m_runner_row_on_top(tmp_path, k02_path):
    """The exact G8 scenario: designer enters M,C,C top-down. With the
    declaration, runner rows land at Y=55/342/629 (C,C bottom-up, M top) —
    the golden design — instead of the scrapped 55/195/482."""
    import yaml
    data = yaml.safe_load(open(k02_path).read())
    k = data["korpus"]
    k["wnetrze"]["kolejnosc_szuflad"] = "od_gory"
    k["wnetrze"]["szuflady"] = [
        {"id": "S1", "typ": "legrabox", "height_code": "M", "nl": 500,
         "capacity_kg": 40, "wysokosc": 140},
        {"id": "S2", "typ": "legrabox", "height_code": "C", "nl": 500,
         "capacity_kg": 40, "wysokosc": 287},
        {"id": "S3", "typ": "legrabox", "height_code": "C", "nl": 500,
         "capacity_kg": 40, "wysokosc": 287},
    ]
    p = tmp_path / "d60.yaml"
    p.write_text(yaml.dump(data, allow_unicode=True))
    cab = load_cabinet(p)
    result = decompose(cab)
    left = next(pn for pn in result.panels if pn.role and pn.role.value == "left_side")
    rows = sorted({op.y_mm for op in left.machining_ops
                   if op.drill_type == "runner_screw"})
    assert rows == [55.0, 342.0, 629.0]


def test_ambiguous_yaml_fails_at_load(tmp_path, k02_path):
    import yaml
    data = yaml.safe_load(open(k02_path).read())
    k = data["korpus"]
    k["wnetrze"].pop("kolejnosc_szuflad", None)
    k["wnetrze"]["szuflady"] = _stack([("M", 140), ("C", 287), ("C", 287)])
    p = tmp_path / "bad.yaml"
    p.write_text(yaml.dump(data, allow_unicode=True))
    with pytest.raises(ValueError, match="ambiguous"):
        load_cabinet(p)
