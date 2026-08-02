# tests/test_material_mirror.py
"""Material mirror (ADR-011 phase 3, spec: docs/specs/material-mirror.md).

The mirror consumes the catalog service's flat decor-variant rows
(v_decors_full shape) and converges the local Material table onto them:
identity fields come from the catalog, price_per_unit stays local
(catalog does not price; the ERP does).
"""
import pytest
from sqlmodel import select

from kitchen_erp.core.models import Material
from kitchen_erp.core.catalog_client import CatalogUnavailable
from kitchen_erp.core.material_mirror import refresh_material_mirror


def row(**overrides) -> dict:
    """A flat /catalog/decors row (one per variant), minimal fields."""
    base = {
        "decor_id": "K101",
        "decor_name": "Front White",
        "producer": "kronospan",
        "discontinued": False,
        "variant_id": "K101-PB-18",
        "material_type": "board",
        "structure": "SM",
        "structure_type": "smooth",
        "roles": '["front", "carcass"]',
        "thickness_mm": 18.0,
        "width_mm": 2800,
        "length_mm": 2070,
    }
    base.update(overrides)
    return base


class FakeCatalog:
    """In-memory stand-in for HttpCatalogClient."""

    def __init__(self, rows):
        self.rows = rows

    def iter_rows(self):
        yield from self.rows


class DeadCatalog:
    def iter_rows(self):
        raise CatalogUnavailable("connection refused")


def boards(session):
    return session.exec(
        select(Material).where(Material.catalog_variant_id.is_not(None))  # type: ignore[union-attr]
    ).all()


def test_refresh_populates_mirror_from_catalog(session):
    stats = refresh_material_mirror(
        session,
        FakeCatalog([
            row(),
            row(decor_id="D1811", decor_name="Walnut", variant_id="D1811-PB-18",
                structure_type="wood_grain"),
        ]),
    )
    assert stats.added == 2
    mirrored = {m.catalog_variant_id: m for m in boards(session)}
    white = mirrored["K101-PB-18"]
    assert white.name == "K101 Front White 18mm"
    assert white.brand == "Kronospan"
    assert white.category == "Board"
    assert white.unit == "m2"
    assert white.price_per_unit == 0.0          # pricing is ERP-local, admin sets it
    assert white.sheet_size_m2 == pytest.approx(2.8 * 2.07)
    assert white.has_woodgrain is False
    assert mirrored["D1811-PB-18"].has_woodgrain is True


# --- orderable identity (kuchnie-h45 step 1) ------------------------------
#
# The catalog row already owns these facts: v_decors_full exposes
# `structure` (= structures.code, the producer's structure code "ST2"/"PW"/
# "SM") and `thickness_mm` (= variants.thickness_mm, a float). The mirror
# used to drop both on the floor.

def test_mirror_populates_structure_and_thickness(session):
    refresh_material_mirror(session, FakeCatalog([row()]))

    m = boards(session)[0]
    assert m.structure == "SM"          # catalog row's structures.code
    assert m.thickness_mm == 18.0       # catalog row's variants.thickness_mm


def test_mirror_does_not_confuse_structure_code_with_structure_type(session):
    """`structure_type` is the family ("wood_grain") and already feeds
    has_woodgrain; `structure` is the orderable code. Different columns."""
    refresh_material_mirror(
        session,
        FakeCatalog([row(structure="PW", structure_type="wood_grain")]),
    )

    m = boards(session)[0]
    assert m.structure == "PW"
    assert m.has_woodgrain is True


def test_mirror_tolerates_a_structureless_variant(session):
    """v_decors_full LEFT JOINs structures — the column can be NULL, and a
    catalog row may omit thickness too."""
    refresh_material_mirror(
        session,
        FakeCatalog([row(structure=None, thickness_mm=None)]),
    )

    m = boards(session)[0]
    assert m.structure is None
    assert m.thickness_mm is None


def test_mirror_converges_stale_identity_on_an_existing_row(session):
    """A row mirrored before this change has NULL identity; the next refresh
    must fill it in and count as an update."""
    session.add(Material(
        name="K101 Front White 18mm", brand="Kronospan", category="Board",
        price_per_unit=42.0, unit="m2", sheet_size_m2=2.8 * 2.07,
        has_woodgrain=False, catalog_variant_id="K101-PB-18",
    ))
    session.commit()

    stats = refresh_material_mirror(session, FakeCatalog([row()]))

    assert (stats.added, stats.updated) == (0, 1)
    m = boards(session)[0]
    assert (m.structure, m.thickness_mm) == ("SM", 18.0)
    assert m.price_per_unit == 42.0     # still ERP-local


def test_mirror_reprices_nothing_when_only_thickness_differs(session):
    """Two variants of one decor differing only in thickness are two rows —
    the mirror must not collapse them onto each other."""
    stats = refresh_material_mirror(session, FakeCatalog([
        row(variant_id="K101-PB-18", thickness_mm=18.0),
        row(variant_id="K101-PB-36", thickness_mm=36.0),
    ]))

    assert stats.added == 2
    assert sorted(m.thickness_mm for m in boards(session)) == [18.0, 36.0]


def test_mirrored_fields_list_names_the_identity_columns(session):
    """The module's own declaration of what the mirror owns must not lie."""
    from kitchen_erp.core import material_mirror

    assert {"structure", "thickness_mm"} <= set(material_mirror._MIRRORED_FIELDS)
    assert "price_per_unit" not in material_mirror._MIRRORED_FIELDS


def test_refresh_preserves_local_price_and_updates_identity(session):
    session.add(Material(
        name="stale name", brand="Kronospan", category="Board",
        price_per_unit=42.0, unit="m2", catalog_variant_id="K101-PB-18",
    ))
    session.commit()

    stats = refresh_material_mirror(session, FakeCatalog([row()]))

    assert stats.added == 0 and stats.updated == 1
    m = boards(session)[0]
    assert m.name == "K101 Front White 18mm"    # identity converged
    assert m.price_per_unit == 42.0             # local price survived


def test_refresh_is_idempotent(session):
    catalog = FakeCatalog([row()])
    refresh_material_mirror(session, catalog)
    stats = refresh_material_mirror(session, catalog)
    assert (stats.added, stats.updated, stats.unchanged) == (0, 0, 1)
    assert len(boards(session)) == 1


def test_local_born_materials_are_never_touched(session):
    local = Material(name="HDF White 3mm", brand="Generic", category="Back",
                     price_per_unit=4.5, unit="m2")
    session.add(local)
    session.commit()

    refresh_material_mirror(session, FakeCatalog([row()]))

    survivor = session.exec(
        select(Material).where(Material.name == "HDF White 3mm")
    ).one()
    assert survivor.catalog_variant_id is None
    assert survivor.price_per_unit == 4.5


def test_non_board_and_discontinued_rows_are_skipped(session):
    stats = refresh_material_mirror(
        session,
        FakeCatalog([
            row(variant_id="W1-WT", roles='["worktop"]'),
            row(variant_id="K101-D", discontinued=True),
        ]),
    )
    assert stats.added == 0
    assert boards(session) == []


def test_catalog_unavailable_propagates_as_typed_error(session):
    with pytest.raises(CatalogUnavailable):
        refresh_material_mirror(session, DeadCatalog())
