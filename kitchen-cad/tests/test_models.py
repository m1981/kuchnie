"""Tests for domain models (Pydantic validation)."""

from __future__ import annotations

import pytest

from kitchen_cad.models import (
    BaseDrawerConfig,
    CorpusSpec,
    DrillPoint,
    DrillType,
    DrillFace,
    EdgeBand,
    EdgeSide,
    Panel,
    PanelRole,
)


# ---------------------------------------------------------------------------
# Panel
# ---------------------------------------------------------------------------

class TestPanel:
    def test_create_minimal_panel(self):
        p = Panel(
            id="K01-BOK-L",
            role=PanelRole.LEFT_SIDE,
            width=510,
            height=720,
            thickness=18,
            material="U119_VL",
        )
        assert p.id == "K01-BOK-L"
        assert p.quantity == 1
        assert p.edges == []
        assert p.drill_points == []

    def test_panel_with_edges_and_drills(self):
        p = Panel(
            id="K01-BOK-L",
            role=PanelRole.LEFT_SIDE,
            width=510,
            height=720,
            thickness=18,
            material="U119_VL",
            edges=[EdgeBand(side=EdgeSide.TOP, material="ABS_0.8")],
            drill_points=[
                DrillPoint(
                    x=37, y=37, diameter=5, depth=13,
                    face=DrillFace.INSIDE,
                    drill_type=DrillType.SYSTEM_32,
                )
            ],
        )
        assert len(p.edges) == 1
        assert len(p.drill_points) == 1

    def test_panel_zero_width_rejected(self):
        with pytest.raises(Exception):
            Panel(
                id="X", role=PanelRole.SHELF,
                width=0, height=100, thickness=18, material="X",
            )


# ---------------------------------------------------------------------------
# DrillPoint
# ---------------------------------------------------------------------------

class TestDrillPoint:
    def test_create_system32_point(self):
        dp = DrillPoint(
            x=37, y=100, diameter=5, depth=13,
            face=DrillFace.INSIDE,
            drill_type=DrillType.SYSTEM_32,
        )
        assert dp.diameter == 5
        assert dp.drill_type == DrillType.SYSTEM_32

    def test_negative_coordinate_rejected(self):
        with pytest.raises(Exception):
            DrillPoint(
                x=-1, y=0, diameter=5, depth=13,
                face=DrillFace.INSIDE,
                drill_type=DrillType.SYSTEM_32,
            )


# ---------------------------------------------------------------------------
# CorpusSpec
# ---------------------------------------------------------------------------

class TestCorpusSpec:
    def test_create_base_door_spec(self, base_door_spec: CorpusSpec):
        assert base_door_spec.width == 800
        assert base_door_spec.height == 720
        assert base_door_spec.depth == 510
        assert base_door_spec.panel_thickness == 18

    def test_create_base_drawer_spec(self, base_drawer_spec: CorpusSpec):
        assert isinstance(base_drawer_spec.config, BaseDrawerConfig)
        assert len(base_drawer_spec.config.drawers) == 2
        assert base_drawer_spec.config.drawers[0].internal_height == 150

    def test_create_wall_spec(self, wall_door_spec: CorpusSpec):
        assert wall_door_spec.depth == 300

    def test_zero_width_rejected(self):
        with pytest.raises(Exception):
            CorpusSpec(
                id="X", name="X", corpus_type="base_door",
                width=0, height=720, depth=510,
            )

    def test_default_front_gap(self):
        spec = CorpusSpec(
            id="X", name="X", corpus_type="base_door",
            width=600, height=720, depth=510,
        )
        assert spec.front_gap == 3.0
