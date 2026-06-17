"""Tests for csv_generator — cutting list + edge banding list output."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from kitchen_cad.models import EdgeSide, PanelRole
from kitchen_cad.panel_calculator import calculate_panels
from kitchen_cad.drill_engine import apply_all_drilling
from kitchen_cad.csv_generator import (
    generate_cutting_csv,
    generate_edging_csv,
)


# ---------------------------------------------------------------------------
# Cutting CSV
# ---------------------------------------------------------------------------

class TestCuttingCsv:
    def _rows(self, spec, tmp_path: Path) -> list[dict]:
        panels = calculate_panels(spec)
        out = tmp_path / "ciecie.csv"
        generate_cutting_csv(panels, out)
        with out.open(encoding="utf-8") as f:
            return list(csv.DictReader(f, delimiter=";"))

    def test_file_created(self, base_door_spec, tmp_path):
        panels = calculate_panels(base_door_spec)
        out = tmp_path / "ciecie.csv"
        generate_cutting_csv(panels, out)
        assert out.exists()

    def test_row_count_matches_panel_count(self, base_door_spec, tmp_path):
        rows = self._rows(base_door_spec, tmp_path)
        assert len(rows) == 7  # 2 sides + top + bottom + shelf + back + front

    def test_columns_present(self, base_door_spec, tmp_path):
        rows = self._rows(base_door_spec, tmp_path)
        row = rows[0]
        assert "id" in row
        assert "role" in row
        assert "width" in row
        assert "height" in row
        assert "thickness" in row
        assert "material" in row
        assert "quantity" in row
        assert "edges" in row

    def test_side_panel_values(self, base_door_spec, tmp_path):
        rows = self._rows(base_door_spec, tmp_path)
        left = next(r for r in rows if r["id"] == "K01-BOK-L")
        assert left["width"] == "510"
        assert left["height"] == "720"
        assert left["thickness"] == "18"
        assert left["material"] == "U119_VL"
        assert left["quantity"] == "1"

    def test_edges_column_lists_sides(self, base_door_spec, tmp_path):
        rows = self._rows(base_door_spec, tmp_path)
        left = next(r for r in rows if r["id"] == "K01-BOK-L")
        edge_str = left["edges"]
        assert "gora" in edge_str
        assert "lewo" in edge_str

    def test_back_panel_has_no_edges(self, base_door_spec, tmp_path):
        rows = self._rows(base_door_spec, tmp_path)
        back = next(r for r in rows if r["role"] == "plecy")
        assert back["edges"] == ""

    def test_separator_is_semicolon(self, base_door_spec, tmp_path):
        panels = calculate_panels(base_door_spec)
        out = tmp_path / "ciecie.csv"
        generate_cutting_csv(panels, out)
        content = out.read_text(encoding="utf-8")
        assert ";" in content


# ---------------------------------------------------------------------------
# Edging CSV
# ---------------------------------------------------------------------------

class TestEdgingCsv:
    def _rows(self, spec, tmp_path: Path) -> list[dict]:
        panels = calculate_panels(spec)
        out = tmp_path / "oklejanie.csv"
        generate_edging_csv(panels, out)
        with out.open(encoding="utf-8") as f:
            return list(csv.DictReader(f, delimiter=";"))

    def test_file_created(self, base_door_spec, tmp_path):
        panels = calculate_panels(base_door_spec)
        out = tmp_path / "oklejanie.csv"
        generate_edging_csv(panels, out)
        assert out.exists()

    def test_columns_present(self, base_door_spec, tmp_path):
        rows = self._rows(base_door_spec, tmp_path)
        assert len(rows) > 0
        row = rows[0]
        assert "panel_id" in row
        assert "edge" in row
        assert "length_mm" in row
        assert "material" in row

    def test_side_panel_top_edge_length(self, base_door_spec, tmp_path):
        """Top edge of side panel = panel width = 510 mm."""
        rows = self._rows(base_door_spec, tmp_path)
        top_edge = next(
            r for r in rows
            if r["panel_id"] == "K01-BOK-L" and r["edge"] == "gora"
        )
        assert top_edge["length_mm"] == "510"

    def test_side_panel_front_edge_length(self, base_door_spec, tmp_path):
        """Front edge of side panel = panel height = 720 mm."""
        rows = self._rows(base_door_spec, tmp_path)
        front_edge = next(
            r for r in rows
            if r["panel_id"] == "K01-BOK-L" and r["edge"] == "lewo"
        )
        assert front_edge["length_mm"] == "720"

    def test_front_door_has_four_edges(self, base_door_spec, tmp_path):
        rows = self._rows(base_door_spec, tmp_path)
        front_edges = [r for r in rows if r["panel_id"] == "K01-F1"]
        assert len(front_edges) == 4

    def test_back_panel_has_no_edging_rows(self, base_door_spec, tmp_path):
        rows = self._rows(base_door_spec, tmp_path)
        back_rows = [r for r in rows if r["panel_id"] == "K01-PLECY"]
        assert len(back_rows) == 0

    def test_edging_material_from_spec(self, base_door_spec, tmp_path):
        rows = self._rows(base_door_spec, tmp_path)
        for row in rows:
            assert row["material"] == "ABS_0.8"
