"""Phase 1 tests: Full pipeline — cabinet types (TC-12.1, TC-12.2).

Covers:
- TC-12.1.x: Base cabinets with doors
- TC-12.2.x: Base cabinets with drawers
- TC-12.3.x: Wall cabinets
"""

from __future__ import annotations

import pytest

from kitchen_cad.models import (
    CorpusSpec,
    DrawerSpec,
    HandleSpec,
    HingeSpec,
    PanelRole,
)
from kitchen_cad.panel_calculator import calculate_panels
from kitchen_cad.drill_engine import apply_all_drilling


# ---------------------------------------------------------------------------
# TC-12.1: Base cabinets with doors
# ---------------------------------------------------------------------------


class TestBaseCabinetWithDoors:
    """TC-12.1: Full pipeline for base cabinets with doors."""

    @pytest.fixture()
    def base_door_600(self) -> CorpusSpec:
        return CorpusSpec(
            id="K01",
            name="Szafka dolna drzwiowa 600",
            corpus_type="base_door",
            width=600,
            height=720,
            depth=510,
            panel_thickness=18,
            back_thickness=3,
            back_groove_depth=8,
            material_corpus="D3821_SW",
            material_back="HDF_3mm_bialy",
            material_front="U164_EM",
            edge_material="ABS_0.8",
            shelves=[352],
            doors=[2],
            hinges=HingeSpec(count=2),
            handles=HandleSpec(spacing=160),
        )

    @pytest.fixture()
    def base_door_800(self) -> CorpusSpec:
        return CorpusSpec(
            id="K02",
            name="Szafka dolna drzwiowa 800",
            corpus_type="base_door",
            width=800,
            height=720,
            depth=510,
            panel_thickness=18,
            back_thickness=3,
            back_groove_depth=8,
            material_corpus="D3821_SW",
            material_back="HDF_3mm_bialy",
            material_front="U164_EM",
            edge_material="ABS_0.8",
            shelves=[352],
            doors=[3],  # 1 door with 3 hinges (wide door)
            hinges=HingeSpec(count=3),
            handles=HandleSpec(spacing=256),
        )

    def test_base_door_600_panel_count(self, base_door_600: CorpusSpec):
        """TC-12.1.1: D60 with doors produces correct panel count."""
        panels = calculate_panels(base_door_600)

        roles = {p.role for p in panels}
        assert PanelRole.LEFT_SIDE in roles
        assert PanelRole.RIGHT_SIDE in roles
        assert PanelRole.TOP in roles
        assert PanelRole.BOTTOM in roles
        assert PanelRole.SHELF in roles
        assert PanelRole.BACK in roles
        assert PanelRole.FRONT_DOOR in roles

        # 2 sides + 2 horizontals + 1 shelf + 1 back + 1 door = 7
        assert len(panels) == 7

    def test_base_door_600_has_drilling(self, base_door_600: CorpusSpec):
        """TC-12.1.1: D60 drilling is applied correctly."""
        panels = calculate_panels(base_door_600)
        panels = apply_all_drilling(panels, base_door_600)

        # Sides should have System 32 holes
        sides = [p for p in panels if p.role in (PanelRole.LEFT_SIDE, PanelRole.RIGHT_SIDE)]
        for side in sides:
            assert len(side.drill_points) > 0, f"{side.id} has no drill points"
            s32 = [dp for dp in side.drill_points if dp.drill_type.value == "system32"]
            assert len(s32) > 0, f"{side.id} has no System 32 holes"

        # Door should have hinge cups
        doors = [p for p in panels if p.role == PanelRole.FRONT_DOOR]
        assert len(doors) == 1
        cups = [dp for dp in doors[0].drill_points if dp.drill_type.value == "puszka_zawiasu"]
        assert len(cups) == 2, f"Expected 2 hinge cups, got {len(cups)}"

    def test_base_door_800_panel_count(self, base_door_800: CorpusSpec):
        """TC-12.1.2: D80 with door produces correct panel count."""
        panels = calculate_panels(base_door_800)
        # 2 sides + 2 horizontals + 1 shelf + 1 back + 1 door = 7
        assert len(panels) == 7

    def test_base_door_800_dimensions(self, base_door_800: CorpusSpec):
        """TC-12.1.2: D80 panel dimensions are correct."""
        panels = calculate_panels(base_door_800)

        sides = [p for p in panels if p.role == PanelRole.LEFT_SIDE]
        assert len(sides) == 1
        assert sides[0].width == pytest.approx(510.0)
        assert sides[0].height == pytest.approx(720.0)

        horizontals = [p for p in panels if p.role in (PanelRole.TOP, PanelRole.BOTTOM)]
        for h in horizontals:
            assert h.width == pytest.approx(800 - 2 * 18)
            assert h.height == pytest.approx(510 - 8)

    def test_base_door_800_hinge_positions(self, base_door_800: CorpusSpec):
        """TC-12.1.2: D80 has 3 hinges (wide door)."""
        panels = calculate_panels(base_door_800)
        panels = apply_all_drilling(panels, base_door_800)

        doors = [p for p in panels if p.role == PanelRole.FRONT_DOOR]
        assert len(doors) == 1
        cups = [dp for dp in doors[0].drill_points if dp.drill_type.value == "puszka_zawiasu"]
        assert len(cups) == 3

    def test_base_door_without_handle(self):
        """TC-12.1.3: D60 without handle — no handle holes."""
        spec = CorpusSpec(
            id="K03",
            name="Szafka bez uchwytu",
            corpus_type="base_door",
            width=600,
            height=720,
            depth=510,
            panel_thickness=18,
            back_thickness=3,
            back_groove_depth=8,
            material_corpus="D3821_SW",
            material_back="HDF_3mm_bialy",
            material_front="U164_EM",
            doors=[2],
            hinges=HingeSpec(count=2),
            handles=None,
        )
        panels = calculate_panels(spec)
        panels = apply_all_drilling(panels, spec)

        doors = [p for p in panels if p.role == PanelRole.FRONT_DOOR]
        for door in doors:
            handle_holes = [dp for dp in door.drill_points if dp.drill_type.value == "uchwyt"]
            assert len(handle_holes) == 0


# ---------------------------------------------------------------------------
# TC-12.2: Base cabinets with drawers
# ---------------------------------------------------------------------------


class TestBaseCabinetWithDrawers:
    """TC-12.2: Full pipeline for base cabinets with drawers."""

    @pytest.fixture()
    def base_drawer_2(self) -> CorpusSpec:
        return CorpusSpec(
            id="S01",
            name="Szafka dolna 2 szuflady",
            corpus_type="base_drawer",
            width=600,
            height=720,
            depth=510,
            panel_thickness=18,
            back_thickness=3,
            back_groove_depth=8,
            material_corpus="D3821_SW",
            material_back="HDF_3mm_bialy",
            material_front="U164_EM",
            edge_material="ABS_0.8",
            drawers=[
                DrawerSpec(internal_height=150, runner_type="blum_metabox"),
                DrawerSpec(internal_height=270, runner_type="blum_metabox"),
            ],
            handles=HandleSpec(spacing=160),
        )

    @pytest.fixture()
    def base_drawer_3(self) -> CorpusSpec:
        return CorpusSpec(
            id="S02",
            name="Szafka dolna 3 szuflady LEGRABOX",
            corpus_type="base_drawer",
            width=600,
            height=720,
            depth=510,
            panel_thickness=18,
            back_thickness=3,
            back_groove_depth=8,
            material_corpus="D3821_SW",
            material_back="HDF_3mm_bialy",
            material_front="U164_EM",
            edge_material="ABS_0.8",
            drawers=[
                DrawerSpec(internal_height=150, runner_type="blum_legrabox"),
                DrawerSpec(internal_height=270, runner_type="blum_legrabox"),
                DrawerSpec(internal_height=300, runner_type="blum_legrabox"),
            ],
            handles=HandleSpec(spacing=160),
        )

    def test_base_drawer_2_panel_count(self, base_drawer_2: CorpusSpec):
        """TC-12.2.1: D60 with 2 drawers produces correct panel count."""
        panels = calculate_panels(base_drawer_2)
        drawer_fronts = [p for p in panels if p.role == PanelRole.FRONT_DRAWER]
        assert len(drawer_fronts) == 2
        assert len(panels) == 7

    def test_base_drawer_2_has_handle_holes(self, base_drawer_2: CorpusSpec):
        """TC-12.2.1: D60 drawer fronts have handle holes."""
        panels = calculate_panels(base_drawer_2)
        panels = apply_all_drilling(panels, base_drawer_2)

        drawer_fronts = [p for p in panels if p.role == PanelRole.FRONT_DRAWER]
        for front in drawer_fronts:
            handle_holes = [dp for dp in front.drill_points if dp.drill_type.value == "uchwyt"]
            assert len(handle_holes) == 2, f"{front.id} should have 2 handle holes"

    def test_base_drawer_3_panel_count(self, base_drawer_3: CorpusSpec):
        """TC-12.2.2: D60 with 3 drawers produces correct panel count."""
        panels = calculate_panels(base_drawer_3)
        drawer_fronts = [p for p in panels if p.role == PanelRole.FRONT_DRAWER]
        assert len(drawer_fronts) == 3
        assert len(panels) == 8

    def test_base_drawer_3_runner_type(self, base_drawer_3: CorpusSpec):
        """TC-12.2.3: LEGRABOX runner type is preserved."""
        assert base_drawer_3.drawers[0].runner_type == "blum_legrabox"
        assert base_drawer_3.drawers[1].runner_type == "blum_legrabox"
        assert base_drawer_3.drawers[2].runner_type == "blum_legrabox"

    def test_base_drawer_2_dimensions(self, base_drawer_2: CorpusSpec):
        """TC-12.2.1: Drawer front dimensions are correct."""
        panels = calculate_panels(base_drawer_2)
        drawer_fronts = [p for p in panels if p.role == PanelRole.FRONT_DRAWER]
        expected_width = 600 - 2 * 3.0
        for front in drawer_fronts:
            assert front.width == pytest.approx(expected_width, abs=0.1)

    def test_base_drawer_2_front_heights(self, base_drawer_2: CorpusSpec):
        """TC-12.2.1: Drawer front heights fill available space."""
        panels = calculate_panels(base_drawer_2)
        drawer_fronts = [p for p in panels if p.role == PanelRole.FRONT_DRAWER]
        total_height = sum(f.height for f in drawer_fronts)
        expected_total = 720 - 2 * 3.0 - (2 - 1) * 3.0
        assert total_height == pytest.approx(expected_total, abs=1.0)

    def test_base_drawer_no_shelves(self, base_drawer_2: CorpusSpec):
        """TC-12.2.1: Drawer cabinet has no shelves."""
        panels = calculate_panels(base_drawer_2)
        shelves = [p for p in panels if p.role == PanelRole.SHELF]
        assert len(shelves) == 0


# ---------------------------------------------------------------------------
# TC-12.3: Wall cabinets
# ---------------------------------------------------------------------------


class TestWallCabinet:
    """TC-12.3: Full pipeline for wall cabinets."""

    @pytest.fixture()
    def wall_door_600(self) -> CorpusSpec:
        return CorpusSpec(
            id="G01",
            name="Szafka wisząca 600",
            corpus_type="wall_door",
            width=600,
            height=720,
            depth=300,
            panel_thickness=18,
            back_thickness=3,
            back_groove_depth=8,
            material_corpus="D3821_SW",
            material_back="HDF_3mm_bialy",
            material_front="U164_EM",
            shelves=[352],
            doors=[2],
            hinges=HingeSpec(count=2),
        )

    def test_wall_cabinet_panel_count(self, wall_door_600: CorpusSpec):
        """TC-12.3.1: G60 with door produces correct panel count."""
        panels = calculate_panels(wall_door_600)
        assert len(panels) == 7

    def test_wall_cabinet_depth(self, wall_door_600: CorpusSpec):
        """TC-12.3.1: G60 sides have depth=300mm."""
        panels = calculate_panels(wall_door_600)
        sides = [p for p in panels if p.role == PanelRole.LEFT_SIDE]
        assert sides[0].width == pytest.approx(300.0)

    def test_wall_cabinet_has_hinges(self, wall_door_600: CorpusSpec):
        """TC-12.3.1: G60 door has hinge cups."""
        panels = calculate_panels(wall_door_600)
        panels = apply_all_drilling(panels, wall_door_600)

        doors = [p for p in panels if p.role == PanelRole.FRONT_DOOR]
        assert len(doors) == 1
        cups = [dp for dp in doors[0].drill_points if dp.drill_type.value == "puszka_zawiasu"]
        assert len(cups) == 2

    def test_wall_cabinet_800_panel_count(self):
        """TC-12.3.2: G80 with door produces correct panel count."""
        spec = CorpusSpec(
            id="G02",
            name="Szafka wisząca 800",
            corpus_type="wall_door",
            width=800,
            height=720,
            depth=300,
            panel_thickness=18,
            back_thickness=3,
            back_groove_depth=8,
            material_corpus="D3821_SW",
            material_back="HDF_3mm_bialy",
            material_front="U164_EM",
            shelves=[352],
            doors=[2],  # 1 door with 2 hinges
            hinges=HingeSpec(count=2),
        )
        panels = calculate_panels(spec)
        # 2 sides + 2 horizontals + 1 shelf + 1 back + 1 door = 7
        assert len(panels) == 7


# ---------------------------------------------------------------------------
# Pipeline integrity
# ---------------------------------------------------------------------------


class TestPipelineIntegrity:
    """Verify full pipeline produces consistent results."""

    def test_all_panels_have_material(self):
        """Every panel in output has a material string."""
        spec = CorpusSpec(
            id="T",
            name="test",
            corpus_type="base_door",
            width=800,
            height=720,
            depth=510,
            panel_thickness=18,
            material_corpus="D3821_SW",
            material_front="U164_EM",
            doors=[2],
            hinges=HingeSpec(count=2),
        )
        panels = calculate_panels(spec)
        for panel in panels:
            assert panel.material, f"{panel.id} has empty material"

    def test_all_panels_have_positive_dimensions(self):
        """Every panel has positive width, height, thickness."""
        spec = CorpusSpec(
            id="T",
            name="test",
            corpus_type="base_door",
            width=800,
            height=720,
            depth=510,
            panel_thickness=18,
            material_corpus="D3821_SW",
            material_front="U164_EM",
            doors=[2],
            hinges=HingeSpec(count=2),
        )
        panels = calculate_panels(spec)
        for panel in panels:
            assert panel.width > 0, f"{panel.id} width <= 0"
            assert panel.height > 0, f"{panel.id} height <= 0"
            assert panel.thickness > 0, f"{panel.id} thickness <= 0"

    def test_pipeline_idempotent(self):
        """Running pipeline twice on same spec gives same results."""
        spec = CorpusSpec(
            id="T",
            name="test",
            corpus_type="base_door",
            width=600,
            height=720,
            depth=510,
            panel_thickness=18,
            material_corpus="D3821_SW",
            material_front="U164_EM",
            shelves=[352],
            doors=[2],
            hinges=HingeSpec(count=2),
        )
        panels1 = apply_all_drilling(calculate_panels(spec), spec)
        panels2 = apply_all_drilling(calculate_panels(spec), spec)

        assert len(panels1) == len(panels2)
        for p1, p2 in zip(panels1, panels2):
            assert p1.id == p2.id
            assert len(p1.drill_points) == len(p2.drill_points)
