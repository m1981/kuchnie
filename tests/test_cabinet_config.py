"""ADR-012 §6 — discriminated ``CabinetInstance.config`` union.

Locks in:

  * The seven variant dataclasses exist and construct with safe defaults.
  * ``CabinetConfig`` is a ``Union`` of exactly those seven variants.
  * ``CabinetInstance.config`` is ``None`` by default (legacy loose fields
    still work for callers that have not migrated).
  * ``kuchnie_core.loader._synthesise_config`` maps every currently
    registered Polish cabinet type to the correct variant.
  * Fixture round-trip: ``load_cabinet`` synthesises the expected config
    from ``K01`` (drawer), ``G01`` (door), ``K02_legrabox`` (drawer).
  * Explicit ``config=`` passed to the constructor is preserved by the
    loader (no synthesis clobber).
  * Unknown cabinet types leave ``config = None`` \u2014 no false variant.
  * Every variant + ``DrawerSlot`` + ``CabinetConfig`` is re-exported from
    the ``kuchnie_core`` package root.
"""

from __future__ import annotations

from pathlib import Path
from typing import get_args

import pytest

from kuchnie_core import (
    BaseDoorConfig,
    BaseDrawerConfig,
    CabinetConfig,
    CabinetInstance,
    CargoConfig,
    CornerBlindConfig,
    CornerInternalConfig,
    DrawerSlot,
    OvenConfig,
    SinkConfig,
)
from kuchnie_core.loader import (
    _apply_synthesised_config,
    _door_hinge_counts,
    _drawer_slot_from_dict,
    _shelf_positions,
    _synthesise_config,
    load_cabinet,
)


FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def _make_cab(**kw) -> CabinetInstance:
    defaults = dict(
        id="TEST",
        type="dolna_drzwiowa",
        description="test",
        width_mm=800,
        height_mm=720,
        depth_mm=510,
        body_material="mat",
        back_material="mat",
        front_material="mat",
    )
    defaults.update(kw)
    return CabinetInstance(**defaults)


# ── 1. Variant dataclasses: defaults & shape ────────────────────

class TestVariantDefaults:

    def test_base_door_defaults(self):
        c = BaseDoorConfig()
        assert c.shelves == []
        assert c.doors == []

    def test_base_drawer_defaults(self):
        c = BaseDrawerConfig()
        assert c.drawers == []

    def test_corner_blind_defaults(self):
        c = CornerBlindConfig()
        assert c.corner_side == "left"
        assert c.second_width_mm == 0.0
        assert c.shelves == []
        assert c.doors == []

    def test_corner_internal_defaults(self):
        c = CornerInternalConfig()
        assert c.carousel == "optima_800"
        assert c.shelves == []
        assert c.doors == []

    def test_sink_defaults(self):
        c = SinkConfig()
        assert c.has_sorting_drawer is False
        assert c.sorting_drawer is None
        assert c.doors == []

    def test_cargo_defaults(self):
        c = CargoConfig()
        assert c.cargo_type == "mini_40"
        assert c.cargo_colour == "ocynk"
        assert c.doors == []

    def test_oven_defaults(self):
        c = OvenConfig()
        assert c.cavity_height_mm == 0.0
        assert c.has_ventilation is True
        assert c.reinforced_shelf is True

    def test_drawer_slot_defaults(self):
        d = DrawerSlot()
        assert d.id == ""
        assert d.system == "tandembox_antaro"
        assert d.height_mm == 0.0
        assert d.height_code == "M"
        assert d.nl_mm == 500.0
        assert d.capacity_kg == 40.0

    def test_default_factory_isolation(self):
        """No shared mutable state between instances (regression guard)."""
        a = BaseDoorConfig()
        b = BaseDoorConfig()
        a.shelves.append(100.0)
        assert b.shelves == []


# ── 2. CabinetConfig union membership ───────────────────────────

class TestCabinetConfigUnion:

    def test_union_covers_seven_variants(self):
        members = set(get_args(CabinetConfig))
        assert members == {
            BaseDoorConfig,
            BaseDrawerConfig,
            CornerBlindConfig,
            CornerInternalConfig,
            SinkConfig,
            CargoConfig,
            OvenConfig,
        }


# ── 3. CabinetInstance.config field ─────────────────────────────

class TestCabinetInstanceConfigField:

    def test_default_is_none(self):
        cab = _make_cab()
        assert cab.config is None

    def test_accepts_any_variant(self):
        for variant in (
            BaseDoorConfig(),
            BaseDrawerConfig(),
            CornerBlindConfig(),
            CornerInternalConfig(),
            SinkConfig(),
            CargoConfig(),
            OvenConfig(),
        ):
            cab = _make_cab(config=variant)
            assert cab.config is variant

    def test_legacy_fields_still_present(self):
        """ADR-012 §6: legacy loose fields remain until callers migrate."""
        cab = _make_cab(
            drawers=[{"id": "S1"}],
            shelves=[{"id": "P1"}],
            fronts=[{"id": "F1"}],
        )
        assert cab.drawers == [{"id": "S1"}]
        assert cab.shelves == [{"id": "P1"}]
        assert cab.fronts == [{"id": "F1"}]


# ── 4. Loader helpers ───────────────────────────────────────────

class TestShelfPositions:

    def test_polish_key_extracted(self):
        cab = _make_cab(shelves=[{"id": "P1", "pozycja_od_dolu": 352}])
        assert _shelf_positions(cab) == [352.0]

    def test_english_key_extracted(self):
        cab = _make_cab(shelves=[{"id": "P1", "position_mm": 352}])
        assert _shelf_positions(cab) == [352.0]

    def test_shelf_without_position_skipped(self):
        cab = _make_cab(shelves=[{"id": "P1"}])
        assert _shelf_positions(cab) == []


class TestDoorHingeCounts:

    def test_counts_extracted_in_order(self):
        cab = _make_cab(fronts=[
            {"id": "F1", "typ": "drzwiowy_lewy",  "ilosc_zawiasow": 2},
            {"id": "F2", "typ": "drzwiowy_prawy", "ilosc_zawiasow": 3},
        ])
        assert _door_hinge_counts(cab) == [2, 3]

    def test_drawer_fronts_ignored(self):
        cab = _make_cab(fronts=[
            {"id": "F1", "typ": "szufladowy"},
            {"id": "F2", "typ": "drzwiowy",  "ilosc_zawiasow": 2},
        ])
        assert _door_hinge_counts(cab) == [2]

    def test_default_hinge_count_when_missing(self):
        cab = _make_cab(fronts=[{"id": "F1", "typ": "drzwiowy"}])
        assert _door_hinge_counts(cab) == [2]


class TestDrawerSlotFromDict:

    def test_polish_keys(self):
        d = _drawer_slot_from_dict({"id": "S1", "typ": "legrabox",
                                    "wysokosc": 177, "nl": 500})
        assert d == DrawerSlot(id="S1", system="legrabox",
                               height_mm=177.0, nl_mm=500.0)

    def test_english_keys(self):
        d = _drawer_slot_from_dict({"id": "S1", "system": "legrabox",
                                    "height_mm": 177, "nl_mm": 500})
        assert d == DrawerSlot(id="S1", system="legrabox",
                               height_mm=177.0, nl_mm=500.0)

    def test_missing_id_yields_empty_string(self):
        d = _drawer_slot_from_dict({})
        assert d.id == ""
        assert d.system == "tandembox_antaro"


# ── 5. _synthesise_config type dispatch ─────────────────────────

class TestSynthesiseConfig:

    def test_dolna_drzwiowa_gives_door_config(self):
        cab = _make_cab(type="dolna_drzwiowa")
        assert isinstance(_synthesise_config(cab), BaseDoorConfig)

    def test_gorna_drzwiowa_gives_door_config(self):
        cab = _make_cab(type="gorna_drzwiowa")
        assert isinstance(_synthesise_config(cab), BaseDoorConfig)

    def test_dolna_szufladowa_gives_drawer_config(self):
        cab = _make_cab(type="dolna_szufladowa")
        assert isinstance(_synthesise_config(cab), BaseDrawerConfig)

    def test_dolna_legrabox_gives_drawer_config(self):
        cab = _make_cab(type="dolna_legrabox")
        assert isinstance(_synthesise_config(cab), BaseDrawerConfig)

    def test_corner_blind_dispatch(self):
        cab = _make_cab(type="dolna_narozna_slepa")
        cfg = _synthesise_config(cab)
        assert isinstance(cfg, CornerBlindConfig)
        assert cfg.second_width_mm == cab.depth_mm

    def test_corner_internal_dispatch(self):
        cab = _make_cab(type="dolna_narozna_karuzela")
        assert isinstance(_synthesise_config(cab), CornerInternalConfig)

    def test_sink_dispatch(self):
        cab = _make_cab(type="dolna_zlewozmywakowa")
        assert isinstance(_synthesise_config(cab), SinkConfig)

    def test_cargo_dispatch(self):
        cab = _make_cab(type="dolna_cargo")
        assert isinstance(_synthesise_config(cab), CargoConfig)

    def test_oven_dispatch(self):
        cab = _make_cab(type="slupek_piekarnikowy", height_mm=2100)
        cfg = _synthesise_config(cab)
        assert isinstance(cfg, OvenConfig)
        assert cfg.cavity_height_mm == pytest.approx(2100 * 0.6)

    def test_unknown_type_returns_none(self):
        cab = _make_cab(type="totally_made_up_type")
        assert _synthesise_config(cab) is None


# ── 6. _apply_synthesised_config: guard around existing config ──

class TestApplySynthesisedConfig:

    def test_populates_when_none(self):
        cab = _make_cab(type="gorna_drzwiowa")
        assert cab.config is None
        _apply_synthesised_config(cab)
        assert isinstance(cab.config, BaseDoorConfig)

    def test_preserves_explicit_config(self):
        explicit = OvenConfig(cavity_height_mm=999.0)
        cab = _make_cab(type="gorna_drzwiowa", config=explicit)
        _apply_synthesised_config(cab)
        assert cab.config is explicit  # untouched


# ── 7. Fixture round-trip ───────────────────────────────────────

class TestFixtureRoundTrip:

    def test_k01_synthesises_drawer_config(self):
        cab = load_cabinet(FIXTURES / "K01.yaml")
        assert isinstance(cab.config, BaseDrawerConfig)
        assert [d.id for d in cab.config.drawers] == ["S1", "S2"]
        assert [d.height_mm for d in cab.config.drawers] == [150.0, 300.0]
        assert cab.config.drawers[0].system == "blum_metabox"

    def test_g01_synthesises_door_config(self):
        cab = load_cabinet(FIXTURES / "G01.yaml")
        assert isinstance(cab.config, BaseDoorConfig)
        assert cab.config.shelves == [352.0, 544.0]
        assert cab.config.doors == [2, 2]

    def test_legrabox_synthesises_drawer_config(self):
        cab = load_cabinet(FIXTURES / "K02_legrabox.yaml")
        assert isinstance(cab.config, BaseDrawerConfig)
        assert len(cab.config.drawers) == 2
        assert cab.config.drawers[0].system == "legrabox"
