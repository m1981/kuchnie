"""Semantic-golden tests for the generic Panel → DXF writer (F6).

Byte-identical golden files are brittle across ezdxf versions, so the
CAD-correct check is semantic: write the DXF, read it back with ezdxf,
and assert the entity model — one circle per drill op at the exact
coordinates, routed onto a layer named after its ``drill_type``, plus a
closed outline polyline matching the panel bounds.

This closes the loop the cold review flagged: before this writer,
``machining_ops`` had no output consumer at all — kuchnie_core computed
drillings nobody could send to a machine.
"""

from pathlib import Path

import ezdxf
import pytest

from kuchnie_core.decomposer import decompose
from kuchnie_core.loader import load_cabinet
from kuchnie_core.model import MachiningOp, Panel, PanelRole

from kitchen_cam.dxf.panel_dxf import panel_to_dxf
from kitchen_cam.machining import apply_all_drilling

FIXTURES = Path(__file__).resolve().parents[2] / "kuchnie-core" / "fixtures"


def _read_back(path):
    msp = ezdxf.readfile(str(path)).modelspace()
    circles = msp.query("CIRCLE")
    outlines = msp.query("LWPOLYLINE")
    return circles, outlines


class TestHandBuiltPanel:

    @pytest.fixture()
    def panel(self):
        return Panel(
            id="P1", name="Bok testowy", material="U119", thickness_mm=18,
            width_mm=500, height_mm=700,
            banded_edges={},
            machining_ops=[
                MachiningOp(type="drill", x_mm=37, y_mm=37, diameter_mm=5,
                            depth_mm=13, drill_type="system32"),
                MachiningOp(type="drill", x_mm=100, y_mm=650, diameter_mm=35,
                            depth_mm=13, drill_type="hinge_cup"),
                MachiningOp(type="drill", x_mm=200, y_mm=300, diameter_mm=8),
            ],
        )

    def test_one_circle_per_drill_op(self, panel, tmp_path):
        circles, _ = _read_back(panel_to_dxf(panel, tmp_path / "p.dxf"))
        assert len(circles) == 3

    def test_circle_geometry_matches_ops(self, panel, tmp_path):
        circles, _ = _read_back(panel_to_dxf(panel, tmp_path / "p.dxf"))
        got = {
            (c.dxf.center.x, c.dxf.center.y, c.dxf.radius) for c in circles
        }
        assert got == {(37, 37, 2.5), (100, 650, 17.5), (200, 300, 4)}

    def test_ops_routed_to_layers_by_drill_type(self, panel, tmp_path):
        circles, _ = _read_back(panel_to_dxf(panel, tmp_path / "p.dxf"))
        layers = {
            (c.dxf.center.x, c.dxf.center.y): c.dxf.layer for c in circles
        }
        assert layers[(37, 37)] == "SYSTEM32"
        assert layers[(100, 650)] == "HINGE_CUP"
        assert layers[(200, 300)] == "DRILL"  # unclassified fallback

    def test_outline_is_closed_panel_boundary(self, panel, tmp_path):
        _, outlines = _read_back(panel_to_dxf(panel, tmp_path / "p.dxf"))
        assert len(outlines) == 1
        outline = outlines[0]
        assert outline.closed
        pts = {(p[0], p[1]) for p in outline.get_points()}
        assert pts == {(0, 0), (500, 0), (500, 700), (0, 700)}


class TestYamlPathToDxf:
    """Whole pipeline: YAML → decompose → drilling → DXF, per panel."""

    def test_g01_side_panel_dxf_carries_all_drillings(self, tmp_path):
        cab = load_cabinet(FIXTURES / "G01.yaml")
        panels = apply_all_drilling(decompose(cab).panels, cab)
        side = next(p for p in panels if p.role == PanelRole.LEFT_SIDE)
        assert side.machining_ops  # sanity: there is something to draw

        circles, _ = _read_back(panel_to_dxf(side, tmp_path / "side.dxf"))
        assert len(circles) == len(
            [op for op in side.machining_ops if op.type == "drill"]
        )

    def test_every_g01_panel_exports(self, tmp_path):
        """No panel role may crash the writer — fronts, back, bottom, all."""
        cab = load_cabinet(FIXTURES / "G01.yaml")
        panels = apply_all_drilling(decompose(cab).panels, cab)
        for i, panel in enumerate(panels):
            out = panel_to_dxf(panel, tmp_path / f"{i}.dxf")
            assert out.exists()
