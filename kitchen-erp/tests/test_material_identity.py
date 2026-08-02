# tests/test_material_identity.py
"""kuchnie-h45 step 1: a Material row must carry enough identity to ORDER a
board.

Owner-confirmed identity shape (recorded in kuchnie-ubc notes, 2026-08-01):
no cross-supplier canonical SKU exists, so stable identity is
(manufacturer, decor code + structure e.g. "U999 ST2" / "K003 PW",
thickness_mm, width_mm) plus a free-text supplier SKU.

The ERP `Material` table carried the manufacturer (brand), the decor code
(inside name) and the sheet format (sheet_size_m2) — but had NO thickness
column at all, and no structure code. Thickness survived only because the
decomposer stamps Panel.thickness_mm downstream; nothing upstream of that
could tell an 18mm board from a 36mm one.

Pinned here: the columns exist on the model, round-trip through SQLite as
nullable values, and legacy database.db files gain them via the declarative
startup migration (kuchnie-26s' SCHEMA_MIGRATIONS) rather than a second
migration mechanism.
"""
from sqlmodel import Session, create_engine, select, text

import kitchen_erp.core.database as database
from kitchen_erp.core.models import Material


# --- the columns exist on the model and round-trip ------------------------

def test_material_carries_thickness_and_structure(session: Session):
    session.add(Material(
        name="U999 Black", brand="Egger", category="Board",
        price_per_unit=61.0, unit="m2",
        structure="ST2", thickness_mm=18.0,
    ))
    session.commit()

    m = session.exec(select(Material).where(Material.name == "U999 Black")).one()
    assert m.structure == "ST2"
    assert m.thickness_mm == 18.0


def test_identity_fields_are_optional_for_local_born_rows(session: Session):
    """Edge tape, services and utility rows have no board thickness or
    structure — the columns must be nullable, not defaulted to a lie."""
    session.add(Material(name="ABS Edge 1mm", price_per_unit=1.0, unit="lm"))
    session.commit()

    m = session.exec(select(Material).where(Material.name == "ABS Edge 1mm")).one()
    assert m.structure is None
    assert m.thickness_mm is None


def test_thickness_round_trips_as_a_float(session: Session):
    """0.8mm edge tape and 38mm worktops both exist — an int column would
    silently truncate."""
    session.add(Material(name="Worktop 38", price_per_unit=1.0, unit="m2",
                         thickness_mm=38.5))
    session.commit()
    assert session.exec(
        select(Material).where(Material.name == "Worktop 38")
    ).one().thickness_mm == 38.5


def test_two_thicknesses_of_one_decor_are_distinct_rows(session: Session):
    """The point of the change: 'U999 ST2' at 18mm and at 36mm are different
    orderable things, and the table can now say so."""
    session.add_all([
        Material(name="U999 Black", brand="Egger", category="Board",
                 price_per_unit=61.0, unit="m2", structure="ST2", thickness_mm=18.0),
        Material(name="U999 Black", brand="Egger", category="Board",
                 price_per_unit=118.0, unit="m2", structure="ST2", thickness_mm=36.0),
    ])
    session.commit()

    rows = session.exec(select(Material).where(Material.name == "U999 Black")).all()
    assert sorted(r.thickness_mm for r in rows) == [18.0, 36.0]
    assert {r.structure for r in rows} == {"ST2"}


# --- legacy databases gain the columns via SCHEMA_MIGRATIONS --------------

def _legacy_engine(tmp_path):
    """A material table as it existed before this change: no structure, no
    thickness_mm, no catalog_variant_id."""
    eng = create_engine(f"sqlite:///{tmp_path / 'legacy.db'}",
                        connect_args={"check_same_thread": False})
    with Session(eng) as session:
        session.exec(text(
            "CREATE TABLE material ("
            " id INTEGER PRIMARY KEY, name VARCHAR, brand VARCHAR,"
            " category VARCHAR, price_per_unit FLOAT, unit VARCHAR,"
            " sheet_size_m2 FLOAT, has_woodgrain BOOLEAN)"
        ))
        session.exec(text(
            "INSERT INTO material (id, name, price_per_unit, unit)"
            " VALUES (1, 'legacy board', 55.0, 'm2')"
        ))
        session.commit()
    return eng


def _columns(eng, table):
    with Session(eng) as session:
        return [row[1] for row in session.exec(text(f"PRAGMA table_info({table})")).all()]


def test_identity_columns_are_declared_in_schema_migrations():
    """One line each in the flat list — no second migration mechanism."""
    declared = {(t, c) for t, c, _ in database.SCHEMA_MIGRATIONS}
    assert ("material", "structure") in declared
    assert ("material", "thickness_mm") in declared


def test_legacy_material_table_gains_the_identity_columns(tmp_path):
    eng = _legacy_engine(tmp_path)
    assert "thickness_mm" not in _columns(eng, "material")

    applied = database.run_startup_migrations(eng)

    assert "material.structure" in applied
    assert "material.thickness_mm" in applied
    assert {"structure", "thickness_mm"} <= set(_columns(eng, "material"))


def test_identity_migration_is_idempotent(tmp_path):
    eng = _legacy_engine(tmp_path)
    database.run_startup_migrations(eng)
    first = _columns(eng, "material")

    second_run = database.run_startup_migrations(eng)

    assert "material.structure" not in second_run
    assert "material.thickness_mm" not in second_run
    assert _columns(eng, "material") == first
    assert len(first) == len(set(first)), "a column was added twice"


def test_migration_preserves_existing_rows(tmp_path):
    """Additive only: the pre-existing board survives, with NULL identity."""
    eng = _legacy_engine(tmp_path)
    database.run_startup_migrations(eng)

    with Session(eng) as session:
        row = session.exec(text(
            "SELECT name, price_per_unit, structure, thickness_mm FROM material"
        )).one()
    assert row == ("legacy board", 55.0, None, None)


def test_fresh_database_gets_the_columns_from_create_all(tmp_path):
    eng = create_engine(f"sqlite:///{tmp_path / 'fresh.db'}",
                        connect_args={"check_same_thread": False})
    database.create_db_and_tables(eng)
    assert {"structure", "thickness_mm"} <= set(_columns(eng, "material"))
