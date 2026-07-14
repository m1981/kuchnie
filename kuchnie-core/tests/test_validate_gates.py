"""Playbook Phase-8 gate rules in validate_rows (wk-bae72832).

The today-feasible slice of the buildability verdict (wk-89a668a2):
G1 worktop line, G6 plinth line, standard-width advisory. Adopts
KitchenStandards (formerly dark: zero consumers) as the width authority.
Playbook: docs/l-kitchen-design-playbook.md §6.
"""
from kuchnie_core.kitchen import validate_rows
from kuchnie_core.model import CabinetInstance, Kitchen, Row
from kuchnie_core.standards import KitchenStandards


def cab(id="C1", type="dolna_drzwiowa", width=600, height=720, plinth=100):
    return CabinetInstance(
        id=id, type=type, description="t",
        width_mm=width, height_mm=height, depth_mm=560,
        body_material="P18", back_material="HDF3", front_material="F18",
        plinth_height_mm=plinth,
    )


def kitchen_with(cabinets, wall=3000):
    return Kitchen(rows=[Row(id="r1", label="A", wall_width_mm=wall,
                             wall_height_mm=2600, cabinets=cabinets)])


# ── component: KitchenStandards width authority ──────────────────

def test_standard_widths_membership():
    std = KitchenStandards()
    for w in (300, 400, 450, 500, 600, 800, 900):
        assert std.is_standard_width(w)
    assert not std.is_standard_width(611)
    assert not std.is_standard_width(597)


def test_standard_width_tolerance():
    std = KitchenStandards()
    assert std.is_standard_width(600 + std.dimension_tolerance / 2)


# ── integration: G1 worktop line ─────────────────────────────────

def test_g1_broken_worktop_line_fails():
    errors = validate_rows(kitchen_with([
        cab("K1", height=720), cab("K2", height=730)]))
    assert any("G1" in e and "720" in e and "730" in e for e in errors)


def test_g1_wall_cabinets_exempt():
    """A wall cabinet (plinth 0) at another height does not break G1."""
    errors = validate_rows(kitchen_with([
        cab("K1", height=720), cab("G1", type="gorna_drzwiowa",
                                    height=900, plinth=0)]))
    assert not any("G1 —" in e for e in errors)


# ── integration: G6 plinth line ──────────────────────────────────

def test_g6_broken_plinth_line_fails():
    errors = validate_rows(kitchen_with([
        cab("K1", plinth=100), cab("K2", plinth=120)]))
    assert any("G6" in e for e in errors)


# ── integration: width advisory ──────────────────────────────────

def test_nonstandard_width_is_advisory_not_error():
    errors = validate_rows(kitchen_with([cab("K1", width=611)]))
    hits = [e for e in errors if "611" in e]
    assert len(hits) == 1 and hits[0].startswith("advisory:")


def test_corner_cabinet_exempt_from_width_rule():
    errors = validate_rows(kitchen_with([
        cab("N1", type="dolna_narozna_slepa", width=1050)]))
    assert not any("1050" in e for e in errors)


# ── clean design passes everything ───────────────────────────────

def test_clean_row_passes():
    errors = validate_rows(kitchen_with([
        cab("K1", width=600), cab("K2", width=800),
        cab("G1", type="gorna_drzwiowa", height=720, plinth=0)]))
    assert errors == []
