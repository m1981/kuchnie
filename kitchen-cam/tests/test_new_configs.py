"""Tests for the 5 new cabinet config types."""

from __future__ import annotations

import pytest

from kitchen_cam.models import (
    BaseDoorConfig,
    CargoConfig,
    CargoType,
    CarouselType,
    CornerBlindConfig,
    CornerInternalConfig,
    CornerSide,
    CorpusSpec,
    DrawerSpec,
    HandleSpec,
    HingeSpec,
    OvenConfig,
    PanelRole,
    SinkConfig,
)
from kitchen_cam.panel_calculator import calculate_panels
from kitchen_cam.machining import apply_all_drilling


class TestCornerInternal:
    """Corner internal cabinet with carousel."""

    @pytest.fixture()
    def spec(self) -> CorpusSpec:
        return CorpusSpec(
            id="N01",
            name="Szafka narożna wewnętrzna 900",
            width=900,
            height=720,
            depth=510,
            hinges=HingeSpec(count=2),
            config=CornerInternalConfig(
                carousel=CarouselType.OPTIMA_800,
                shelves=[352],
                doors=[2],
            ),
        )

    def test_has_sides(self, spec):
        panels = calculate_panels(spec)
        roles = {p.role for p in panels}
        assert PanelRole.LEFT_SIDE in roles
        assert PanelRole.RIGHT_SIDE in roles

    def test_has_diagonal_back(self, spec):
        """Diagonal back is wider than standard."""
        panels = calculate_panels(spec)
        backs = [p for p in panels if p.role == PanelRole.BACK]
        assert len(backs) == 1
        # Diagonal = sqrt(900² + 510²) - 2*18 ≈ 1007 - 36 ≈ 971
        assert backs[0].width > 900, "Diagonal back should be wider than cabinet"

    def test_has_shelf_and_door(self, spec):
        panels = calculate_panels(spec)
        shelves = [p for p in panels if p.role == PanelRole.SHELF]
        doors = [p for p in panels if p.role == PanelRole.FRONT_DOOR]
        assert len(shelves) == 1
        assert len(doors) == 1


class TestSinkCabinet:
    """Sink base cabinet."""

    @pytest.fixture()
    def spec_with_drawer(self) -> CorpusSpec:
        return CorpusSpec(
            id="Z01",
            name="Szafka zlewowa z sortowaniem",
            width=800,
            height=720,
            depth=510,
            hinges=HingeSpec(count=2),
            handles=HandleSpec(spacing=256),
            config=SinkConfig(
                has_sorting_drawer=True,
                sorting_drawer=DrawerSpec(internal_height=150),
                doors=[2],
            ),
        )

    @pytest.fixture()
    def spec_without_drawer(self) -> CorpusSpec:
        return CorpusSpec(
            id="Z02",
            name="Szafka pod zlewozmywak",
            width=800,
            height=720,
            depth=510,
            hinges=HingeSpec(count=2),
            config=SinkConfig(
                has_sorting_drawer=False,
                doors=[2],
            ),
        )

    def test_with_sorting_drawer(self, spec_with_drawer):
        panels = calculate_panels(spec_with_drawer)
        drawer_fronts = [p for p in panels if p.role == PanelRole.FRONT_DRAWER]
        door_fronts = [p for p in panels if p.role == PanelRole.FRONT_DOOR]
        assert len(drawer_fronts) == 1
        assert len(door_fronts) == 1

    def test_without_drawer(self, spec_without_drawer):
        panels = calculate_panels(spec_without_drawer)
        drawer_fronts = [p for p in panels if p.role == PanelRole.FRONT_DRAWER]
        door_fronts = [p for p in panels if p.role == PanelRole.FRONT_DOOR]
        assert len(drawer_fronts) == 0
        assert len(door_fronts) == 1

    def test_no_shelves(self, spec_without_drawer):
        """Sink cabinet typically has no shelves."""
        panels = calculate_panels(spec_without_drawer)
        shelves = [p for p in panels if p.role == PanelRole.SHELF]
        assert len(shelves) == 0


class TestCargoCabinet:
    """Base cabinet with cargo basket."""

    @pytest.fixture()
    def spec(self) -> CorpusSpec:
        return CorpusSpec(
            id="C01",
            name="Szafka z koszem cargo 400",
            width=400,
            height=720,
            depth=510,
            hinges=HingeSpec(count=2),
            config=CargoConfig(
                cargo_type=CargoType.MINI_40,
                cargo_color="ocynk",
                doors=[2],
            ),
        )

    def test_has_door(self, spec):
        panels = calculate_panels(spec)
        doors = [p for p in panels if p.role == PanelRole.FRONT_DOOR]
        assert len(doors) == 1

    def test_no_shelves(self, spec):
        """Cargo basket replaces shelves."""
        panels = calculate_panels(spec)
        shelves = [p for p in panels if p.role == PanelRole.SHELF]
        assert len(shelves) == 0

    def test_no_drawers(self, spec):
        """Cargo basket replaces drawers."""
        panels = calculate_panels(spec)
        drawer_fronts = [p for p in panels if p.role == PanelRole.FRONT_DRAWER]
        assert len(drawer_fronts) == 0


class TestOvenCabinet:
    """Oven housing cabinet."""

    @pytest.fixture()
    def spec(self) -> CorpusSpec:
        return CorpusSpec(
            id="P01",
            name="Szafka do zabudowy piekarnika",
            width=600,
            height=2000,
            depth=560,
            config=OvenConfig(
                cavity_height=600,
                has_ventilation=True,
                reinforced_shelf=True,
            ),
        )

    def test_has_reinforced_shelf(self, spec):
        """Oven cabinet has a reinforced shelf at cavity height."""
        panels = calculate_panels(spec)
        shelves = [p for p in panels if p.role == PanelRole.SHELF]
        assert len(shelves) == 1

    def test_no_doors(self, spec):
        """Oven door is the front — no cabinet doors."""
        panels = calculate_panels(spec)
        doors = [p for p in panels if p.role == PanelRole.FRONT_DOOR]
        assert len(doors) == 0

    def test_has_sides_and_horizontals(self, spec):
        panels = calculate_panels(spec)
        roles = {p.role for p in panels}
        assert PanelRole.LEFT_SIDE in roles
        assert PanelRole.RIGHT_SIDE in roles
        assert PanelRole.TOP in roles
        assert PanelRole.BOTTOM in roles
        assert PanelRole.BACK in roles


class TestBackwardCompatibility:
    """Legacy flat fields still work."""

    def test_legacy_base_door(self):
        spec = CorpusSpec(
            id="K01",
            name="Legacy door",
            width=800,
            height=720,
            depth=510,
            corpus_type="base_door",
            shelves=[352],
            doors=[2],
        )
        assert spec.corpus_type_resolved == "base_door"
        panels = calculate_panels(spec)
        assert len(panels) == 7

    def test_legacy_base_drawer(self):
        spec = CorpusSpec(
            id="K02",
            name="Legacy drawer",
            width=600,
            height=720,
            depth=510,
            corpus_type="base_drawer",
            drawers=[DrawerSpec(internal_height=150)],
        )
        assert spec.corpus_type_resolved == "base_drawer"
        panels = calculate_panels(spec)
        drawer_fronts = [p for p in panels if p.role == PanelRole.FRONT_DRAWER]
        assert len(drawer_fronts) == 1

    def test_legacy_oven(self):
        spec = CorpusSpec(
            id="P01",
            name="Legacy oven",
            width=600,
            height=2000,
            depth=560,
            corpus_type="oven",
        )
        assert spec.corpus_type_resolved == "oven"
        panels = calculate_panels(spec)
        shelves = [p for p in panels if p.role == PanelRole.SHELF]
        assert len(shelves) == 1
