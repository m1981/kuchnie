"""Phase 1 tests: Edge banding (TC-3.1).

Covers:
- TC-3.1.x: Edge selection (all, individual, none)
- TC-3.2.x: Edge thickness
- TC-3.3.x: Edge color matching
"""

from __future__ import annotations

import pytest

from kitchen_cad.models import EdgeBand, EdgeSide, Panel, PanelRole


# ---------------------------------------------------------------------------
# TC-3.1: Edge selection combinations
# ---------------------------------------------------------------------------


class TestEdgeSelection:
    """TC-3.1: Verify edge banding can be applied to any combination of sides."""

    def test_all_four_edges(self):
        """TC-3.1.1: All 4 edges banded."""
        edges = [EdgeBand(side=s) for s in EdgeSide]
        panel = Panel(
            id="test-all-edges",
            role=PanelRole.FRONT_DOOR,
            width=596.0,
            height=713.0,
            thickness=18.0,
            material="TEST",
            edges=edges,
        )
        assert len(panel.edges) == 4
        edge_sides = {e.side for e in panel.edges}
        assert edge_sides == {EdgeSide.TOP, EdgeSide.BOTTOM, EdgeSide.LEFT, EdgeSide.RIGHT}

    @pytest.mark.parametrize(
        "side, expected",
        [
            (EdgeSide.TOP, "TC-3.1.2_top_only"),
            (EdgeSide.RIGHT, "TC-3.1.3_right_only"),
            (EdgeSide.BOTTOM, "TC-3.1.4_bottom_only"),
            (EdgeSide.LEFT, "TC-3.1.5_left_only"),
        ],
    )
    def test_single_edge(self, side: EdgeSide, expected: str):
        """TC-3.1.2-5: Single edge banding."""
        panel = Panel(
            id=expected,
            role=PanelRole.LEFT_SIDE,
            width=510.0,
            height=720.0,
            thickness=18.0,
            material="TEST",
            edges=[EdgeBand(side=side)],
        )
        assert len(panel.edges) == 1
        assert panel.edges[0].side == side

    def test_two_edges_front_and_right(self):
        """TC-3.1.6: Two edges (top + right) — typical for side panel."""
        panel = Panel(
            id="test-two-edges",
            role=PanelRole.LEFT_SIDE,
            width=510.0,
            height=720.0,
            thickness=18.0,
            material="TEST",
            edges=[
                EdgeBand(side=EdgeSide.TOP),
                EdgeBand(side=EdgeSide.RIGHT),
            ],
        )
        assert len(panel.edges) == 2

    def test_no_edges(self):
        """TC-3.1.7: No edge banding — typical for back panel."""
        panel = Panel(
            id="test-no-edges",
            role=PanelRole.BACK,
            width=764.0,
            height=720.0,
            thickness=3.0,
            material="HDF",
            edges=[],
        )
        assert len(panel.edges) == 0


# ---------------------------------------------------------------------------
# TC-3.2: Edge material/thickness
# ---------------------------------------------------------------------------


class TestEdgeMaterial:
    """TC-3.2: Verify edge material specification."""

    @pytest.mark.parametrize(
        "material, label",
        [
            ("ABS_1.0_bezspoinowy", "TC-3.2.1_ABS_1mm_glueless"),
            ("ABS_1.0_standard", "TC-3.2.2_ABS_1mm_standard"),
            ("ABS_2.0", "TC-3.2.3_ABS_2mm_front"),
            ("PVC_0.4", "TC-3.2.4_PVC_0.4mm"),
            ("Fornir_0.6", "TC-3.2.5_Fornir_0.6mm"),
        ],
    )
    def test_edge_material_variants(self, material: str, label: str):
        """TC-3.2.1-5: Different edge materials accepted."""
        edge = EdgeBand(side=EdgeSide.TOP, material=material)
        assert edge.material == material

    def test_default_edge_material(self):
        """Default edge material is ABS_0.8."""
        edge = EdgeBand(side=EdgeSide.TOP)
        assert edge.material == "ABS_0.8"


# ---------------------------------------------------------------------------
# TC-3.3: Edge color matching
# ---------------------------------------------------------------------------


class TestEdgeColor:
    """TC-3.3: Verify edge color can match plate color."""

    def test_matching_color(self):
        """TC-3.3.1: Edge color matches plate (U702)."""
        edge = EdgeBand(side=EdgeSide.TOP, material="ABS_U702_1.0")
        assert "U702" in edge.material

    def test_different_color(self):
        """TC-3.3.2: Different edge color (U164)."""
        edge = EdgeBand(side=EdgeSide.TOP, material="ABS_U164_1.0")
        assert "U164" in edge.material


# ---------------------------------------------------------------------------
# TC-3.4: Edge banding in panel_calculator output
# ---------------------------------------------------------------------------


class TestEdgeBandingInCalculator:
    """Verify panel_calculator applies correct edges to panel types."""

    @pytest.fixture()
    def spec(self):
        from kitchen_cad.models import CorpusSpec
        return CorpusSpec(
            id="T",
            name="test",
            corpus_type="base_door",
            width=800,
            height=720,
            depth=510,
            panel_thickness=18,
            edge_material="ABS_TEST",
        )

    def test_side_panels_have_top_and_left_edges(self, spec):
        """Side panels should have top (visible) and front (left=front) edges."""
        from kitchen_cad.panel_calculator import _side_panels

        sides = _side_panels(spec)
        for panel in sides:
            edge_sides = {e.side for e in panel.edges}
            assert EdgeSide.TOP in edge_sides, f"{panel.id} missing TOP edge"
            assert EdgeSide.LEFT in edge_sides, f"{panel.id} missing LEFT (front) edge"

    def test_back_panel_has_no_edges(self, spec):
        """Back panel (HDF) should have no edge banding."""
        from kitchen_cad.panel_calculator import _back_panel

        back = _back_panel(spec)
        assert len(back.edges) == 0

    def test_door_fronts_have_all_edges(self, spec):
        """Door fronts should have all 4 edges banded."""
        from kitchen_cad.panel_calculator import _door_fronts

        spec.doors = [2]
        fronts = _door_fronts(spec, spec.config.doors)
        for front in fronts:
            edge_sides = {e.side for e in front.edges}
            assert len(edge_sides) == 4, f"{front.id} should have 4 edges"
