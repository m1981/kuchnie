# tests/test_quote_range.py
"""Pins wk-224f3712 (rough-quote canvas widelka) + wk-59b943b1 (per-type
labor pricing), owner-merged scopes, decision 2026-08-02. Spec:
docs/specs/use-cases.md § UC-1 steps 1-4 / ext 1a/2a/3a,
kitchen-erp/docs/specs/screens.md's Canvas row + pre-written acceptance.
"""
from datetime import date, timedelta

from kitchen_erp.core.bom_generator import BOMGenerator
from kitchen_erp.core.models import Cabinet, HardwareSet, Material, Project, ProjectDefaults
from kitchen_erp.core.quote_range import (
    VAT_RATE,
    WIDELKA_DO_MARGIN,
    WIDELKA_OD_MARGIN,
    EstimateLinePrice,
    KOMFORT_DRAWER_SYSTEM_DELTA_PER_DRAWER,
    KOMFORT_HINGE_DELTA_PER_DOOR,
    LaborRate,
    QuoteRange,
    compute_quote_range,
    labor_category_for,
    labor_total_for_cabinets,
    latest_quote_range,
    price_module,
    round_to_100,
    save_quote_range,
    seed_defaults,
    widelka_display,
)

AS_OF = date(2026, 8, 2)


def seed_project(session):
    """A project with materials priced round-number, matching the
    house pattern in test_quote_freshness.py's seed_project."""
    corpus = Material(name="Egger W980", price_per_unit=10.0, unit="m2")
    front = Material(name="Front MDF", price_per_unit=20.0, unit="m2")
    back = Material(name="HDF", price_per_unit=5.0, unit="m2")
    edge = Material(name="ABS", price_per_unit=1.0, unit="lm")
    defaults = ProjectDefaults(
        corpus_mat=corpus, front_mat=front, back_mat=back, edge_band_mat=edge,
        hinge_sys=HardwareSet(name="Hinge", price_per_set=2.0),
        drawer_sys=HardwareSet(name="Drawer", price_per_set=30.0),
    )
    project = Project(customer_name="Kowalski", defaults=defaults)
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


def cab(session, project, **kwargs):
    defaults = dict(
        type="BASE", width_mm=600.0, height_mm=720.0, depth_mm=510.0,
        door_count=0, drawer_count=0, order_index=0, project=project,
    )
    defaults.update(kwargs)
    new_cab = Cabinet(**defaults)
    # project is already persistent by the time tests call this helper
    # (seed_project commits+refreshes it); the back-populated relationship
    # alone does not reliably cascade a brand-new child into the session
    # once the parent's collection has been loaded/refreshed, so add the
    # cabinet explicitly.
    session.add(new_cab)
    return new_cab


# --- round_to_100 / VAT constants: pinned arithmetic (item e) ------------

class TestRoundTo100:
    def test_rounds_down_below_half(self):
        assert round_to_100(12345) == 12300

    def test_rounds_up_at_and_above_half(self):
        assert round_to_100(12350) == 12400
        assert round_to_100(12351) == 12400

    def test_exact_hundred_stays_put(self):
        assert round_to_100(12300) == 12300

    def test_zero_and_small_values(self):
        assert round_to_100(0) == 0
        assert round_to_100(49) == 0
        assert round_to_100(50) == 100


class TestConstants:
    def test_vat_and_margins_pinned(self):
        # Owner-confirmed 2026-08-02: od = standard*0.95*1.23, do = komfort*1.15*1.23
        assert VAT_RATE == 1.23
        assert WIDELKA_OD_MARGIN == 0.95
        assert WIDELKA_DO_MARGIN == 1.15


# --- Labor mapping (module type -> cennik category) -----------------------

class TestLaborCategoryFor:
    def test_drawer_base_is_drawer(self):
        assert labor_category_for("DRAWER_BASE", door_count=0, drawer_count=3) == "drawer"

    def test_corner_kinds_are_corner(self):
        assert labor_category_for("CARGO", door_count=0, drawer_count=0) == "corner"
        assert labor_category_for("CAROUSEL", door_count=0, drawer_count=0) == "corner"

    def test_base_wall_sink_with_doors_is_door(self):
        assert labor_category_for("BASE_CABINET", door_count=1, drawer_count=0) == "door"
        assert labor_category_for("WALL_CABINET", door_count=2, drawer_count=0) == "door"
        assert labor_category_for("SINK_BASE", door_count=1, drawer_count=0) == "door"

    def test_base_wall_sink_without_doors_has_no_labor_line(self):
        assert labor_category_for("BASE_CABINET", door_count=0, drawer_count=0) is None

    def test_filler_and_side_panel_are_plain(self):
        assert labor_category_for("FILLER", door_count=1, drawer_count=0) == "plain"
        assert labor_category_for("SIDE_PANEL", door_count=0, drawer_count=0) == "plain"

    def test_fixed_equipment_has_no_labor_line(self):
        for kind in ("DISHWASHER", "OVEN", "COOKTOP", "HOOD", "COUNTERTOP", "SINK", "FAUCET"):
            assert labor_category_for(kind, door_count=0, drawer_count=0) is None


# --- Pre-written acceptance test (screens.md ~line 95): one priced, one --
# --- unpriced module -------------------------------------------------------

def test_unpriced_module_is_flagged_and_widelka_marked_incomplete(session):
    """screens.md's pre-written acceptance: "the Canvas screen flags a
    module line with no price-book entry as unpriced rather than omitting
    it, and renders the od-do widelek with a SZACUNEK badge showing
    per-line price age, covered by a test exercising both a priced and an
    unpriced module" (wk-224f3712)."""
    project = seed_project(session)
    cab(session, project, name="Dishwasher", module_kind="DISHWASHER", equipment_price=1399)
    cab(session, project, name="Hood", module_kind="HOOD", equipment_price=788)
    session.add(project)
    session.commit()
    session.refresh(project)

    # Only DISHWASHER gets a price-book entry -- HOOD stays unpriced.
    session.add(EstimateLinePrice(
        module_kind="DISHWASHER", standard_price=1399.0, komfort_price=1399.0,
        valid_from=AS_OF - timedelta(days=10),
    ))
    session.add(LaborRate(category="door", price=250.0, valid_from=AS_OF))
    session.commit()

    result = compute_quote_range(session, project, as_of=AS_OF)

    lines_by_kind = {l.module_kind: l for l in result.lines}
    assert lines_by_kind["DISHWASHER"].priced is True
    assert lines_by_kind["HOOD"].priced is False
    # Never silently omitted or zero-counted quietly: the line exists.
    assert lines_by_kind["HOOD"].standard_price == 0.0
    assert lines_by_kind["HOOD"].komfort_price == 0.0

    assert result.incomplete is True  # UC-1 ext 2a

    # SZACUNEK badge with per-line age (tr-4afef6fb machinery, reused).
    assert result.freshness.grade == "estimate"
    dishwasher_line = next(
        l for l in result.freshness.lines if l.material_name == "Dishwasher (DISHWASHER)"
    )
    assert dishwasher_line.status == "fresh"
    assert dishwasher_line.age_days == 10


def test_all_priced_and_fresh_module_lines_do_not_force_incomplete(session):
    project = seed_project(session)
    cab(session, project, name="Dishwasher", module_kind="DISHWASHER")
    session.add(project)
    session.commit()
    session.refresh(project)
    session.add(EstimateLinePrice(
        module_kind="DISHWASHER", standard_price=1399.0, komfort_price=1399.0,
        valid_from=AS_OF,
    ))
    session.commit()

    result = compute_quote_range(session, project, as_of=AS_OF)
    assert result.incomplete is False


# --- Hand-computed golden (item b) -----------------------------------------

def test_golden_widelka_arithmetic(session):
    """1 drawer base (3 drawers) + 2 door bases (1 and 2 doors) + 1
    dishwasher, known seed prices. Arithmetic below is plain Python, not
    the function under test.

    Material baselines for the three buildable cabinets come from
    BOMGenerator -- the SAME already-tested pipeline as every other cost
    trace in this app (see test_bom_generator.py) -- so they are MEASURED
    here as known inputs, not re-derived by hand; what this test hand-
    verifies is quote_range's OWN new arithmetic built on top of them:
    the komfort tier-delta, the labor cennik sum, and the widelka
    rounding/VAT formula.
    """
    project = seed_project(session)
    drawer_cab = cab(session, project, name="Drawer base", module_kind="DRAWER_BASE", drawer_count=3)
    door_cab_1 = cab(session, project, name="Door base 1", module_kind="BASE_CABINET", door_count=1)
    door_cab_2 = cab(session, project, name="Door base 2", module_kind="BASE_CABINET", door_count=2)
    dishwasher = cab(session, project, name="Dishwasher", module_kind="DISHWASHER", equipment_price=1399)
    session.add(project)
    session.commit()
    session.refresh(project)

    session.add(EstimateLinePrice(
        module_kind="DISHWASHER", standard_price=1399.0, komfort_price=1399.0,
        valid_from=AS_OF,
    ))
    for category, price in (("drawer", 400.0), ("door", 250.0)):
        session.add(LaborRate(category=category, price=price, valid_from=AS_OF))
    session.commit()

    # Measured baselines (BOMGenerator, not hand-derived -- see docstring).
    baseline_drawer = BOMGenerator(drawer_cab, project.defaults).generate().cost
    baseline_door_1 = BOMGenerator(door_cab_1, project.defaults).generate().cost
    baseline_door_2 = BOMGenerator(door_cab_2, project.defaults).generate().cost

    # --- Hand-computed expectations -----------------------------------
    # Komfort tier-delta: legrabox-vs-tandembox per drawer, soft-close
    # hinge per door (KOMFORT_* constants, quote_range.py).
    komfort_drawer = baseline_drawer + 3 * KOMFORT_DRAWER_SYSTEM_DELTA_PER_DRAWER  # +3*180 = +540
    komfort_door_1 = baseline_door_1 + 1 * KOMFORT_HINGE_DELTA_PER_DOOR            # +1*25  = +25
    komfort_door_2 = baseline_door_2 + 2 * KOMFORT_HINGE_DELTA_PER_DOOR            # +2*25  = +50

    # Labor cennik: drawer(400) + door(250) + door(250) + dishwasher(none) = 900
    expected_labor_total = 400.0 + 250.0 + 250.0
    assert expected_labor_total == 900.0

    expected_standard_total = (
        baseline_drawer + baseline_door_1 + baseline_door_2  # material baselines
        + 1399.0                                              # dishwasher, standard tier
        + expected_labor_total
    )
    expected_komfort_total = (
        komfort_drawer + komfort_door_1 + komfort_door_2
        + 1399.0                                              # dishwasher, komfort tier (same seed)
        + expected_labor_total
    )

    expected_od = round_to_100(expected_standard_total * 0.95 * 1.23)
    expected_do = round_to_100(expected_komfort_total * 1.15 * 1.23)

    result = compute_quote_range(session, project, as_of=AS_OF)

    assert result.incomplete is False
    assert result.module_count == 4
    assert result.labor_total == expected_labor_total
    assert round(result.standard_total_net, 6) == round(expected_standard_total, 6)
    assert round(result.komfort_total_net, 6) == round(expected_komfort_total, 6)
    assert result.od_brutto == expected_od
    assert result.do_brutto == expected_do
    assert result.od_brutto <= result.do_brutto  # a widelka is a range, not a point


# --- (c) labor sum replaces markup ------------------------------------------

def test_labor_total_for_cabinets_sums_cennik_not_markup(session):
    project = seed_project(session)
    cab(session, project, name="Drawer base", module_kind="DRAWER_BASE", drawer_count=2)
    cab(session, project, name="Door base", module_kind="BASE_CABINET", door_count=1)
    cab(session, project, name="Filler", module_kind="FILLER", door_count=1)
    cab(session, project, name="Dishwasher", module_kind="DISHWASHER")  # no labor line
    session.add(project)
    session.commit()
    session.refresh(project)
    seed_defaults(session, as_of=AS_OF)

    total = labor_total_for_cabinets(session, project.cabinets)
    # drawer(400) + door(250) + plain(150) + dishwasher(0) = 800, regardless
    # of Project.labor_markup (which stays unused by this math).
    assert total == 400.0 + 250.0 + 150.0


def test_cost_trace_robocizna_row_wired_to_cennik_not_markup():
    """Source-text pin (house pattern: test_quote_freshness.py's
    test_ui_state_wires_the_doorway): open_project_cost_trace's
    "Robocizna" row must sum the cennik nakładów, not
    project.labor_markup (owner decision 2026-08-02 REPLACES the old
    x1.50 multiplier)."""
    from pathlib import Path
    state_src = (Path(__file__).resolve().parents[1] / "kitchen_erp" / "ui" / "state.py").read_text(encoding="utf-8")
    trace_fn = state_src.split("def open_project_cost_trace")[1].split("\n    def ")[0]
    assert "labor_total_for_cabinets" in trace_fn
    # The multiplier itself must be gone; a code comment noting the
    # replacement (documenting the "why") is fine and expected.
    assert "raw_total * project.labor_markup" not in trace_fn
    assert "raw_total * (project.labor_markup" not in trace_fn


def test_canvas_total_wired_to_labor_total_not_markup():
    from pathlib import Path
    state_src = (Path(__file__).resolve().parents[1] / "kitchen_erp" / "ui" / "state.py").read_text(encoding="utf-8")
    load_fn = state_src.split("def load_mock_data")[1]
    assert "labor_total_for_cabinets" in load_fn
    assert "total_price * existing.labor_markup" not in load_fn


# --- (d) QuoteRange persists and is retrievable -----------------------------

def test_quote_range_persists_and_is_retrievable(session):
    project = seed_project(session)
    cab(session, project, name="Dishwasher", module_kind="DISHWASHER")
    session.add(project)
    session.commit()
    session.refresh(project)
    seed_defaults(session, as_of=AS_OF)

    result = compute_quote_range(session, project, as_of=AS_OF)
    saved = save_quote_range(session, project, result)

    assert saved.id is not None
    fetched = latest_quote_range(session, project.id)
    assert fetched is not None
    assert fetched.id == saved.id
    assert fetched.od_brutto == result.od_brutto
    assert fetched.do_brutto == result.do_brutto
    assert fetched.standard_total_net == result.standard_total_net
    assert fetched.komfort_total_net == result.komfort_total_net
    assert fetched.module_count == result.module_count
    assert fetched.incomplete == result.incomplete


def test_latest_quote_range_picks_the_newest(session):
    project = seed_project(session)
    session.add(project)
    session.commit()
    session.refresh(project)

    from kitchen_erp.core.quote_range import QuoteRangeResult
    first = save_quote_range(session, project, QuoteRangeResult(
        standard_total_net=1000.0, komfort_total_net=1200.0,
        module_count=1, incomplete=False, od_brutto=1000.0, do_brutto=1400.0,
    ))
    second = save_quote_range(session, project, QuoteRangeResult(
        standard_total_net=2000.0, komfort_total_net=2200.0,
        module_count=2, incomplete=False, od_brutto=2000.0, do_brutto=2400.0,
    ))
    assert first.id != second.id

    latest = latest_quote_range(session, project.id)
    assert latest.id == second.id
    assert latest.od_brutto == 2000.0


def test_quote_range_missing_returns_none(session):
    project = seed_project(session)
    session.add(project)
    session.commit()
    session.refresh(project)
    assert latest_quote_range(session, project.id) is None


# --- widelka_display -------------------------------------------------------

def test_widelka_display_format():
    assert widelka_display(12300, 15600) == "od 12 300 do 15 600 zł brutto"
