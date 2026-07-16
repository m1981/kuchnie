# tests/test_price_import.py
"""Pins the wk-39ed9155 acceptance: supplier price rows enter through the
landing schema with verbatim source archived, validation refuses
schema-incomplete / out-of-tolerance rows, and a stale price renders any
quote standing on it estimate-grade with age visible.
Spec: docs/specs/purchasing-variants.md § "Price ingestion"."""
from datetime import date, timedelta
from pathlib import Path

import pytest
from sqlmodel import select

from kitchen_erp.core.models import Material, SupplierPrice
from kitchen_erp.core.price_import import (
    LANDING_FIELDS,
    PRICE_TTL_DAYS,
    LandingSchemaError,
    assess_quote_freshness,
    import_price_file,
    read_source_rows,
    validate_landing_rows,
)

HEADER = ";".join(LANDING_FIELDS)


def landing_csv(tmp_path: Path, *lines: str, name: str = "prices.csv") -> Path:
    path = tmp_path / name
    path.write_text("\n".join([HEADER, *lines]) + "\n", encoding="utf-8")
    return path


@pytest.fixture
def mirrored_material(session) -> Material:
    material = Material(
        name="U112 PM 18mm", price_per_unit=0.0, unit="m2",
        catalog_variant_id="EGGER-U112-18",
    )
    session.add(material)
    session.commit()
    session.refresh(material)
    return material


def test_canonical_import_lands_rows_and_updates_material(session, tmp_path, mirrored_material):
    source = landing_csv(
        tmp_path,
        "Egger;EGGER-U112-18;U112 PM 18mm;m2;54.20;PLN;2026-07-01;",
        "Egger;EGGER-W980-18;W980 SM 18mm;m2;48.00;PLN;2026-07-01;",
    )
    report = import_price_file(session, source, tmp_path / "archive")

    assert [r.reason for r in report.refused] == []
    assert len(report.accepted) == 2
    # verbatim capture: archive copy exists, byte-identical, stamped as source_ref
    archived = Path(report.archived_path)
    assert archived.read_bytes() == source.read_bytes()
    assert all(r.source_ref == str(archived) for r in report.accepted)
    # landed history rows
    assert len(session.exec(select(SupplierPrice)).all()) == 2
    # mirrored material repriced by catalog_variant_id; unmatched code reported
    session.refresh(mirrored_material)
    assert mirrored_material.price_per_unit == 54.20
    assert report.materials_updated == 1
    assert report.unmatched_item_codes == ["EGGER-W980-18"]


def test_schema_incomplete_row_refused_never_coerced(session, tmp_path):
    source = landing_csv(
        tmp_path,
        "Egger;EGGER-U112-18;U112;m2;;PLN;2026-07-01;",       # missing price_net
        "Egger;;U112;m2;54.20;PLN;2026-07-01;",                # missing item_code
        "Egger;EGGER-W980-18;W980;m2;48.00;PLN;2026-07-01;",   # valid
    )
    report = import_price_file(session, source, tmp_path / "archive")
    assert len(report.accepted) == 1
    assert len(report.refused) == 2
    assert "schema-incomplete" in report.refused[0].reason
    assert len(session.exec(select(SupplierPrice)).all()) == 1


@pytest.mark.parametrize(
    ("row", "fragment"),
    [
        ("Egger;X;d;furlongs;10.0;PLN;2026-07-01;", "unit"),
        ("Egger;X;d;m2;abc;PLN;2026-07-01;", "not a number"),
        ("Egger;X;d;m2;-5;PLN;2026-07-01;", "must be > 0"),
        ("Egger;X;d;m2;10.0;ZLOTE;2026-07-01;", "3-letter"),
        ("Egger;X;d;m2;10.0;PLN;yesterday;", "ISO date"),
    ],
)
def test_insane_values_refused(session, tmp_path, row, fragment):
    report = import_price_file(session, landing_csv(tmp_path, row), tmp_path / "archive")
    assert report.accepted == []
    assert len(report.refused) == 1 and fragment in report.refused[0].reason


def test_price_jump_beyond_tolerance_refused(session, tmp_path, mirrored_material):
    session.add(SupplierPrice(
        supplier="Egger", item_code="EGGER-U112-18", unit="m2", price_net=50.0,
        currency="PLN", valid_from=date(2026, 6, 1), source_ref="seed",
    ))
    session.commit()
    source = landing_csv(
        tmp_path,
        "Egger;EGGER-U112-18;U112;m2;160.00;PLN;2026-07-01;",  # 3.2x — refuse
    )
    report = import_price_file(session, source, tmp_path / "archive")
    assert report.accepted == []
    assert "human eyeballs" in report.refused[0].reason
    session.refresh(mirrored_material)
    assert mirrored_material.price_per_unit == 0.0  # untouched

    within = landing_csv(tmp_path, "Egger;EGGER-U112-18;U112;m2;60.00;PLN;2026-07-02;",
                         name="within.csv")
    report = import_price_file(session, within, tmp_path / "archive")
    assert len(report.accepted) == 1
    session.refresh(mirrored_material)
    assert mirrored_material.price_per_unit == 60.0


def test_wrong_header_is_schema_error(session, tmp_path):
    path = tmp_path / "bad.csv"
    path.write_text("kod;cena\nX;10\n", encoding="utf-8")
    with pytest.raises(LandingSchemaError):
        read_source_rows(path)


def test_xls_source_refused_with_pointer(tmp_path):
    path = tmp_path / "prices.xls"
    path.write_bytes(b"\xd0\xcf\x11\xe0")
    with pytest.raises(LandingSchemaError, match="unsupported source format"):
        read_source_rows(path)


def test_column_map_adapter_lands_supplier_csv(session, tmp_path, mirrored_material):
    path = tmp_path / "dealer.csv"
    path.write_text(
        "Kod,Nazwa,Jm,Cena netto,Waluta,Data\n"
        "EGGER-U112-18,U112 PM,m2,\"54,20\",PLN,2026-07-01\n",
        encoding="utf-8",
    )
    report = import_price_file(
        session, path, tmp_path / "archive",
        column_map={
            "item_code": "Kod", "description": "Nazwa", "unit": "Jm",
            "price_net": "Cena netto", "currency": "Waluta", "valid_from": "Data",
        },
        constants={"supplier": "Egger"},
    )
    assert [r.reason for r in report.refused] == []
    assert report.accepted[0].price_net == 54.20  # comma decimal normalized
    session.refresh(mirrored_material)
    assert mirrored_material.price_per_unit == 54.20


def test_column_map_missing_required_field_is_schema_error(tmp_path):
    path = tmp_path / "dealer.csv"
    path.write_text("Kod,Cena\nX,10\n", encoding="utf-8")
    with pytest.raises(LandingSchemaError, match="required landing fields"):
        read_source_rows(path, column_map={"item_code": "Kod", "price_net": "Cena"},
                         constants={"supplier": "X"})


def test_stale_price_renders_estimate_grade_with_age_visible(session, mirrored_material):
    as_of = date(2026, 7, 17)
    session.add(SupplierPrice(
        supplier="Egger", item_code="EGGER-U112-18", unit="m2", price_net=54.2,
        currency="PLN", valid_from=as_of - timedelta(days=200), source_ref="a",
    ))
    session.commit()
    quote = assess_quote_freshness(session, [mirrored_material], as_of=as_of)
    assert quote.grade == "estimate"
    line = quote.lines[0]
    assert line.status == "stale" and line.age_days == 200  # age visible


def test_fresh_prices_render_current_grade(session, mirrored_material):
    as_of = date(2026, 7, 17)
    session.add(SupplierPrice(
        supplier="Egger", item_code="EGGER-U112-18", unit="m2", price_net=54.2,
        currency="PLN", valid_from=as_of - timedelta(days=PRICE_TTL_DAYS), source_ref="a",
    ))
    session.commit()
    quote = assess_quote_freshness(session, [mirrored_material], as_of=as_of)
    assert quote.grade == "current"
    assert quote.lines[0].status == "fresh"


def test_hand_priced_material_has_no_provenance_and_estimates(session):
    local = Material(name="Blenda", price_per_unit=30.0, unit="m2")  # local-born
    session.add(local)
    session.commit()
    quote = assess_quote_freshness(session, [local], as_of=date(2026, 7, 17))
    assert quote.grade == "estimate"
    assert quote.lines[0].status == "no_provenance" and quote.lines[0].age_days is None


def test_validate_rows_alone_stamps_source_ref(session):
    rows = [dict(zip(LANDING_FIELDS,
                     ["Egger", "X", "d", "m2", "10.0", "PLN", "2026-07-01", ""]))]
    accepted, refused = validate_landing_rows(rows, session, source_ref="archive/f.csv")
    assert refused == []
    assert accepted[0].source_ref == "archive/f.csv"
