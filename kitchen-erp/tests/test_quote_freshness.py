# tests/test_quote_freshness.py
"""Pins wk-68b32f3b: the quote path's freshness verdict — every material a
project's quote stands on (defaults + cabinet overrides) is graded, a stale
or provenance-free price renders the quote estimate-grade, and the display
strings carry the age. Spec: docs/specs/purchasing-variants.md § Price
ingestion ("prices decay")."""
from datetime import date, timedelta

from kitchen_erp.core.models import (
    Cabinet,
    HardwareSet,
    Material,
    Project,
    ProjectDefaults,
    SupplierPrice,
)
from kitchen_erp.core.price_import import (
    PRICE_TTL_DAYS,
    freshness_display,
    quote_freshness_for_project,
)

AS_OF = date(2026, 7, 17)


def seed_project(session, *, front_variant="EGGER-F-18", corpus_variant="EGGER-C-18"):
    corpus = Material(name="Egger W980", price_per_unit=10.0, unit="m2",
                      catalog_variant_id=corpus_variant)
    front = Material(name="Front MDF", price_per_unit=20.0, unit="m2",
                     catalog_variant_id=front_variant)
    back = Material(name="HDF", price_per_unit=5.0, unit="m2")
    edge = Material(name="ABS", price_per_unit=1.0, unit="lm")
    defaults = ProjectDefaults(
        corpus_mat=corpus, front_mat=front, back_mat=back, edge_band_mat=edge,
        hinge_sys=HardwareSet(name="Hinge", price_per_set=2.0),
        drawer_sys=HardwareSet(name="Drawer", price_per_set=30.0),
    )
    project = Project(customer_name="Kowalski", defaults=defaults)
    Cabinet(name="D60", type="BASE", module_kind="BASE_CABINET",
            width_mm=600.0, height_mm=720.0, depth_mm=510.0,
            door_count=1, drawer_count=0, order_index=0, project=project)
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


def price_row(item_code, age_days, price=50.0):
    return SupplierPrice(
        supplier="Egger", item_code=item_code, unit="m2", price_net=price,
        currency="PLN", valid_from=AS_OF - timedelta(days=age_days),
        source_ref="archive/seed.csv",
    )


def test_all_fresh_supplier_backed_defaults_grade_current(session):
    project = seed_project(session)
    session.add(price_row("EGGER-F-18", 10))
    session.add(price_row("EGGER-C-18", 30))
    # HDF + ABS are hand-priced utility rows -> no provenance; reprice them
    # as supplier-backed for this test by giving them variant ids
    project.defaults.back_mat.catalog_variant_id = "HDF-3"
    project.defaults.edge_band_mat.catalog_variant_id = "ABS-1"
    session.add(price_row("HDF-3", 1))
    session.add(price_row("ABS-1", PRICE_TTL_DAYS))
    session.commit()

    freshness = quote_freshness_for_project(session, project, as_of=AS_OF)
    assert freshness.grade == "current"
    assert len(freshness.lines) == 4  # all defaults graded


def test_one_stale_default_renders_estimate_grade_with_age(session):
    project = seed_project(session)
    session.add(price_row("EGGER-F-18", 200))  # stale front
    session.add(price_row("EGGER-C-18", 10))
    session.commit()

    freshness = quote_freshness_for_project(session, project, as_of=AS_OF)
    assert freshness.grade == "estimate"
    stale = [l for l in freshness.lines if l.status == "stale"]
    assert len(stale) == 1 and stale[0].age_days == 200

    badge, lines = freshness_display(freshness)
    assert badge == "SZACUNEK — ceny do weryfikacji"
    assert any("200 dni" in line for line in lines)  # age visible


def test_hand_priced_material_alone_forces_estimate_grade(session):
    project = seed_project(session)
    session.add(price_row("EGGER-F-18", 10))
    session.add(price_row("EGGER-C-18", 10))
    session.commit()
    # back/edge stay provenance-free (hand-priced)
    freshness = quote_freshness_for_project(session, project, as_of=AS_OF)
    assert freshness.grade == "estimate"
    badge, lines = freshness_display(freshness)
    assert any("brak pochodzenia" in line for line in lines)


def test_cabinet_override_material_is_graded_too(session):
    project = seed_project(session)
    for code in ("EGGER-F-18", "EGGER-C-18"):
        session.add(price_row(code, 10))
    project.defaults.back_mat.catalog_variant_id = "HDF-3"
    project.defaults.edge_band_mat.catalog_variant_id = "ABS-1"
    session.add(price_row("HDF-3", 1))
    session.add(price_row("ABS-1", 1))
    override = Material(name="Dab Sonoma", price_per_unit=30.0, unit="m2",
                        catalog_variant_id="EGGER-DS-18")
    session.add(override)
    session.commit()
    project.cabinets[0].override_front_mat_id = override.id
    session.add(project.cabinets[0])
    session.add(price_row("EGGER-DS-18", 400))  # stale override
    session.commit()
    session.refresh(project)

    freshness = quote_freshness_for_project(session, project, as_of=AS_OF)
    assert freshness.grade == "estimate"  # override drags the quote down
    assert any(l.material_name == "Dab Sonoma" and l.status == "stale"
               for l in freshness.lines)


def test_fresh_display_lines_still_show_age(session):
    project = seed_project(session)
    session.add(price_row("EGGER-F-18", 10))
    session.commit()
    freshness = quote_freshness_for_project(session, project, as_of=AS_OF)
    _, lines = freshness_display(freshness)
    assert any("(10 dni)" in line for line in lines)


def test_ui_state_wires_the_doorway():
    """The refutation that diverged the first filing: assess_quote_freshness
    had no production caller. Pin the wiring: state.py calls the project
    grader next to total_price and kitchen_erp.py renders the badge."""
    from pathlib import Path
    pkg = Path(__file__).resolve().parents[1] / "kitchen_erp"
    state_src = (pkg / "ui" / "state.py").read_text(encoding="utf-8")
    app_src = (pkg / "kitchen_erp.py").read_text(encoding="utf-8")
    assert state_src.count("quote_freshness_for_project(session, existing)") == 1
    assert state_src.count("freshness_display(freshness)") == 1
    assert app_src.count("quote_grade_badge") >= 1
    assert app_src.count("quote_freshness_lines") >= 1
