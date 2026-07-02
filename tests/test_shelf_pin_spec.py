"""ADR-012 §5 — ``ShelfPinSpec`` on ``CabinetInstance``.

Additive extension: adds a typed shelf-pin drilling spec to every cabinet
with a sane default. No pre-ADR-012 behaviour changes; existing fixtures
and tests keep working.

Locked in:

  * ``ShelfPinSpec`` field defaults from ADR-012 §5.
  * ``CabinetInstance.shelf_pins`` uses ``field(default_factory=ShelfPinSpec)``
    so every cabinet gets a spec without opt-in.
  * Loader accepts optional Polish ``kolki_polkowe`` block and English
    ``shelf_pins`` block; both round-trip.
  * BOM accessory name uses ``spec.diameter_mm`` \u2014 byte-identical to the
    pre-ADR-012 hard-coded ``"Kołek półkowy 5 mm"`` for the default case.
  * Non-default diameter reflects in the BOM label.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from kuchnie_core import CabinetInstance, ShelfPinSpec
from kuchnie_core.decomposer import decompose
from kuchnie_core.loader import (
    _shelf_pins_from_polish,
    _shelf_pins_from_schema,
    load_cabinet,
)


FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


# ── Dataclass defaults (ADR-012 §5) ─────────────────────────────

class TestShelfPinSpecDefaults:
    def test_default_diameter(self):
        assert ShelfPinSpec().diameter_mm == 5.0

    def test_default_depth(self):
        assert ShelfPinSpec().depth_mm == 8.0

    def test_default_front_offset(self):
        assert ShelfPinSpec().front_offset_mm == 50.0

    def test_default_back_offset(self):
        assert ShelfPinSpec().back_offset_mm == 80.0

    def test_default_max_per_row(self):
        assert ShelfPinSpec().max_per_row == 3

    def test_explicit_construction(self):
        s = ShelfPinSpec(
            diameter_mm=3.0, depth_mm=6.0,
            front_offset_mm=40.0, back_offset_mm=70.0, max_per_row=4,
        )
        assert (s.diameter_mm, s.depth_mm) == (3.0, 6.0)
        assert (s.front_offset_mm, s.back_offset_mm) == (40.0, 70.0)
        assert s.max_per_row == 4


# ── CabinetInstance carries a default spec ──────────────────────

class TestCabinetInstanceShelfPinsField:
    """Every cabinet gets a ShelfPinSpec via default_factory — no opt-in."""

    def _make(self, **kw):
        defaults = dict(
            id="TEST", type="test", description="test",
            width_mm=800, height_mm=720, depth_mm=510,
            body_material="mat", back_material="mat", front_material="mat",
        )
        defaults.update(kw)
        return CabinetInstance(**defaults)

    def test_default_shelf_pins_is_adr012_spec(self):
        cab = self._make()
        assert isinstance(cab.shelf_pins, ShelfPinSpec)
        assert cab.shelf_pins.diameter_mm == 5.0
        assert cab.shelf_pins.depth_mm == 8.0

    def test_each_cabinet_gets_its_own_spec(self):
        """default_factory means no shared mutable state — regression guard."""
        a = self._make(id="A")
        b = self._make(id="B")
        assert a.shelf_pins is not b.shelf_pins

    def test_accepts_custom_spec(self):
        cab = self._make(shelf_pins=ShelfPinSpec(diameter_mm=3.0, depth_mm=6.0))
        assert cab.shelf_pins.diameter_mm == 3.0


# ── Loader: Polish YAML → ShelfPinSpec ──────────────────────────

class TestShelfPinsFromPolishYaml:

    def test_empty_dict_returns_default_spec(self):
        s = _shelf_pins_from_polish({})
        assert s == ShelfPinSpec()

    def test_none_returns_default_spec(self):
        s = _shelf_pins_from_polish(None)
        assert s == ShelfPinSpec()

    def test_polish_keys_translated(self):
        s = _shelf_pins_from_polish({
            "srednica": 3, "glebokosc": 6,
            "odsuniecie_przod": 40, "odsuniecie_tyl": 70,
            "maks_na_rzad": 4,
        })
        assert s.diameter_mm == 3.0
        assert s.depth_mm == 6.0
        assert s.front_offset_mm == 40.0
        assert s.back_offset_mm == 70.0
        assert s.max_per_row == 4

    def test_partial_override_keeps_defaults(self):
        s = _shelf_pins_from_polish({"srednica": 3})
        assert s.diameter_mm == 3.0
        assert s.depth_mm == 8.0            # unchanged default
        assert s.max_per_row == 3           # unchanged default


class TestShelfPinsFromSchema:

    def test_empty_returns_default(self):
        assert _shelf_pins_from_schema({}) == ShelfPinSpec()
        assert _shelf_pins_from_schema(None) == ShelfPinSpec()

    def test_english_keys_lifted(self):
        s = _shelf_pins_from_schema({
            "diameter_mm": 3.0, "depth_mm": 6.0,
            "front_offset_mm": 40.0, "back_offset_mm": 70.0,
            "max_per_row": 4,
        })
        assert (s.diameter_mm, s.depth_mm) == (3.0, 6.0)
        assert s.max_per_row == 4


# ── Real fixture round-trip (fixtures have no explicit shelf pins) ──

class TestFixtureRoundTrip:
    """Every fixture in the repo omits ``kolki_polkowe`` \u2014 so all cabinets
    should load with the ADR-012 default spec."""

    def test_k01_uses_default_spec(self):
        cab = load_cabinet(FIXTURES / "K01.yaml")
        assert cab.shelf_pins == ShelfPinSpec()

    def test_g01_uses_default_spec(self):
        cab = load_cabinet(FIXTURES / "G01.yaml")
        assert cab.shelf_pins == ShelfPinSpec()

    def test_legrabox_uses_default_spec(self):
        cab = load_cabinet(FIXTURES / "K02_legrabox.yaml")
        assert cab.shelf_pins == ShelfPinSpec()


# ── BOM stability: default diameter → identical accessory name ──

class TestBOMAccessoryNameStability:
    """The pre-ADR-012 accessory name was hard-coded ``"Kołek półkowy 5 mm"``.
    Now it's built from ``spec.diameter_mm`` — must be byte-identical for the
    default 5mm case, and must reflect the diameter for non-default cases.
    """

    def test_g01_default_accessory_name(self):
        cab = load_cabinet(FIXTURES / "G01.yaml")
        result = decompose(cab)
        pins = [a for a in result.accessories if a.type == "shelf_pin"]
        assert len(pins) == 1
        # Byte-identical to pre-ADR-012 output.
        assert pins[0].name == "Kołek półkowy 5 mm"

    def test_non_default_diameter_reflects_in_name(self):
        # Construct a cabinet by hand with a 3mm pin spec.
        cab = CabinetInstance(
            id="CUSTOM", type="dolna_drzwiowa", description="test",
            width_mm=800, height_mm=720, depth_mm=510,
            body_material="mat", back_material="mat", front_material="mat",
            shelves=[{"id": "P1"}, {"id": "P2"}],
            shelf_pins=ShelfPinSpec(diameter_mm=3.0),
        )
        result = decompose(cab)
        pins = [a for a in result.accessories if a.type == "shelf_pin"]
        assert len(pins) == 1
        assert pins[0].name == "Kołek półkowy 3 mm"
        # Quantity math is unchanged: 4 pins per shelf × 2 shelves = 8.
        assert pins[0].quantity == 8


# ── Loader integration: explicit YAML override honoured ─────────

class TestLoaderShelfPinsOverride:
    """Loading a cabinet with an explicit ``kolki_polkowe`` block overrides the default."""

    # Use a fixture written on-the-fly rather than a permanent one — the
    # feature is that the YAML *can* carry the block, not that any current
    # fixture does. Locked-in behaviour: default when absent, override when
    # present.

    def test_polish_block_overrides_default(self, tmp_path):
        yaml_text = """
korpus:
    id: 'X1'
    typ: 'dolna_drzwiowa'
    opis: 'test'
    wymiary:
        szerokosc: 800
        wysokosc: 720
        glebokosc: 510
    material:
        korpus: 'mat'
        plecy: 'mat'
        fronty: 'mat'
    grubosci:
        boki: 18
        polki: 18
        dna: 18
        plecy: 3
        fronty: 18
    plecy:
        typ: 'wpuszczane_w_nut'
        nut: 8
    oklejanie:
        typ: 'ABS'
        grubosc: 0.8
    wnetrze:
        polki:
            - id: 'P1'
    kolki_polkowe:
        srednica: 3
        glebokosc: 6
        maks_na_rzad: 4
"""
        p = tmp_path / "x1.yaml"
        p.write_text(yaml_text)
        cab = load_cabinet(p)
        assert cab.shelf_pins.diameter_mm == 3.0
        assert cab.shelf_pins.depth_mm == 6.0
        assert cab.shelf_pins.max_per_row == 4
        # Fields not overridden keep ADR-012 defaults.
        assert cab.shelf_pins.front_offset_mm == 50.0
