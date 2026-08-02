# tests/test_admin_state.py
"""kuchnie-33x: direct tests for AdminState's material CRUD.

admin_state.py is the largest class in the repo (36 methods per the
arch-smells gate) and, until this file, no test named it — yet it is where
Material identity is edited by hand (kuchnie-h45). The Reflex *views*
(admin_ui.py) are deliberately NOT tested here; the state class is plain
Python and is where the behaviour lives.

AdminState reaches for a session through the module-level `get_session`
generator, so these tests swap that binding for one backed by a shared
in-memory SQLite engine (StaticPool keeps every Session on the same
database). Reflex permits direct instantiation under pytest.
"""
import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

import kitchen_erp.ui.admin_state as admin_state
from kitchen_erp.core.models import Material
from kitchen_erp.ui.admin_state import AdminState


@pytest.fixture(name="db")
def db_fixture():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture(name="admin")
def admin_fixture(db, monkeypatch):
    def fake_get_session():
        with Session(db) as session:
            yield session

    monkeypatch.setattr(admin_state, "get_session", fake_get_session)
    return AdminState()


def seed(db, **overrides) -> int:
    fields = dict(
        name="U999 Black", brand="Egger", category="Board",
        price_per_unit=61.0, unit="m2", sheet_size_m2=5.796,
        has_woodgrain=False, structure="ST2", thickness_mm=18.0,
    )
    fields.update(overrides)
    with Session(db) as session:
        material = Material(**fields)
        session.add(material)
        session.commit()
        return material.id


def stored(db, material_id: int) -> Material:
    with Session(db) as session:
        return session.get(Material, material_id)


# --- create ---------------------------------------------------------------

def test_save_material_creates_a_row_with_full_identity(admin, db):
    admin.open_new_material_form()
    admin.set_edit_material_brand("Egger")
    admin.set_edit_material_name("U999 Black")
    admin.set_edit_material_structure("ST2")
    admin.set_edit_material_thickness("18")
    admin.set_edit_material_price("61.00")
    admin.set_edit_material_sheet_size("5.796")

    admin.save_material()

    with Session(db) as session:
        m = session.exec(select(Material)).one()
    assert (m.brand, m.name) == ("Egger", "U999 Black")
    assert m.structure == "ST2"
    assert m.thickness_mm == 18.0
    assert m.price_per_unit == 61.0
    assert admin.show_material_form is False


def test_created_material_appears_in_the_loaded_list(admin, db):
    admin.open_new_material_form()
    admin.set_edit_material_name("U999 Black")
    admin.set_edit_material_structure("ST2")
    admin.set_edit_material_thickness("18")

    admin.save_material()

    assert [(m.name, m.structure, m.thickness_mm) for m in admin.materials] == [
        ("U999 Black", "ST2", 18.0)
    ]


def test_blank_identity_is_stored_as_null_not_empty(admin, db):
    """A service or edge-tape row has no board structure/thickness. Storing
    "" and 0.0 would make 'unknown' indistinguishable from 'zero'."""
    admin.open_new_material_form()
    admin.set_edit_material_name("Cutting service")
    admin.set_edit_material_structure("   ")
    admin.set_edit_material_thickness("")

    admin.save_material()

    with Session(db) as session:
        m = session.exec(select(Material)).one()
    assert m.structure is None
    assert m.thickness_mm is None


def test_open_new_material_form_clears_identity_left_by_a_previous_edit(admin, db):
    material_id = seed(db)
    admin.open_edit_material_form(material_id)

    admin.open_new_material_form()

    assert admin.is_editing is False
    assert admin.edit_material_structure == ""
    assert admin.edit_material_thickness_mm == 0.0
    assert admin.edit_material_name == ""


# --- read -----------------------------------------------------------------

def test_load_materials_exposes_identity_to_the_view(admin, db):
    seed(db)

    admin.load_materials()

    row = admin.materials[0]
    assert row.structure == "ST2"
    assert row.thickness_mm == 18.0


def test_load_materials_renders_missing_identity_without_crashing(admin, db):
    """NULL structure/thickness is the normal state of a legacy row that has
    not been through the mirror yet."""
    seed(db, name="Legacy board", structure=None, thickness_mm=None)

    admin.load_materials()

    row = admin.materials[0]
    assert row.structure == ""
    assert row.thickness_mm == 0.0


def test_load_materials_honours_the_category_filter(admin, db):
    seed(db, name="Board row", category="Board")
    seed(db, name="Edge row", category="Edge", structure=None, thickness_mm=0.8)

    admin.set_material_filter("Edge")

    assert [m.name for m in admin.materials] == ["Edge row"]
    assert admin.materials[0].thickness_mm == 0.8


def test_open_edit_material_form_loads_every_field(admin, db):
    material_id = seed(db, has_woodgrain=True)

    admin.open_edit_material_form(material_id)

    assert admin.is_editing is True
    assert admin.selected_material_id == material_id
    assert admin.edit_material_name == "U999 Black"
    assert admin.edit_material_brand == "Egger"
    assert admin.edit_material_structure == "ST2"
    assert admin.edit_material_thickness_mm == 18.0
    assert admin.edit_material_price == 61.0
    assert admin.edit_material_has_woodgrain is True
    assert admin.show_material_form is True


def test_open_edit_material_form_ignores_a_missing_id(admin, db):
    admin.open_edit_material_form(4242)
    assert admin.show_material_form is False


# --- update ---------------------------------------------------------------

def test_save_material_updates_identity_in_place(admin, db):
    material_id = seed(db)
    admin.open_edit_material_form(material_id)
    admin.set_edit_material_structure("PW")
    admin.set_edit_material_thickness("36")

    admin.save_material()

    m = stored(db, material_id)
    assert (m.structure, m.thickness_mm) == ("PW", 36.0)
    with Session(db) as session:
        assert len(session.exec(select(Material)).all()) == 1  # updated, not cloned


def test_editing_a_mirrored_row_keeps_its_catalog_key(admin, db):
    """catalog_variant_id is the mirror key (ADR-011 phase 3). A hand edit in
    Admin must not orphan the row from the catalog."""
    material_id = seed(db, catalog_variant_id="K101-PB-18")
    admin.open_edit_material_form(material_id)
    admin.set_edit_material_price("70")

    admin.save_material()

    assert stored(db, material_id).catalog_variant_id == "K101-PB-18"


def test_thickness_setter_rejects_garbage_without_raising(admin, db):
    admin.set_edit_material_thickness("18")
    admin.set_edit_material_thickness("eighteen")
    assert admin.edit_material_thickness_mm == 0.0


def test_thickness_setter_accepts_a_decimal(admin, db):
    admin.set_edit_material_thickness("0.8")
    assert admin.edit_material_thickness_mm == 0.8


def test_structure_setter_stores_the_raw_code(admin, db):
    admin.set_edit_material_structure("ST2")
    assert admin.edit_material_structure == "ST2"


# --- delete ---------------------------------------------------------------

def test_delete_material_removes_the_row_and_refreshes_the_list(admin, db):
    material_id = seed(db)
    admin.load_materials()
    assert len(admin.materials) == 1

    admin.delete_material(material_id)

    assert stored(db, material_id) is None
    assert admin.materials == []


def test_delete_material_ignores_a_missing_id(admin, db):
    seed(db)
    admin.delete_material(4242)
    assert len(admin.materials) == 1


# --- form lifecycle -------------------------------------------------------

def test_cancel_form_closes_the_material_form(admin, db):
    admin.open_new_material_form()
    admin.cancel_form()
    assert admin.show_material_form is False
