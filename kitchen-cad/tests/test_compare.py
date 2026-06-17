"""Tests for comparison tools — validate kitchen-cad output against reference files.

Supports:
  - CSV comparison (exact + fuzzy numeric)
  - DXF comparison (semantic geometry with tolerance)
"""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass, field
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# CSV comparison
# ---------------------------------------------------------------------------

@dataclass
class CsvDiff:
    """Result of comparing two CSV files."""
    missing_in_generated: list[str] = field(default_factory=list)
    missing_in_reference: list[str] = field(default_factory=list)
    value_mismatches: list[str] = field(default_factory=list)
    row_count_match: bool = True

    @property
    def ok(self) -> bool:
        return (
            not self.missing_in_generated
            and not self.missing_in_reference
            and not self.value_mismatches
        )

    def report(self) -> str:
        lines = []
        if self.missing_in_reference:
            lines.append(f"Rows in generated but NOT in reference ({len(self.missing_in_reference)}):")
            for r in self.missing_in_reference:
                lines.append(f"  + {r}")
        if self.missing_in_generated:
            lines.append(f"Rows in reference but NOT in generated ({len(self.missing_in_generated)}):")
            for r in self.missing_in_generated:
                lines.append(f"  - {r}")
        if self.value_mismatches:
            lines.append(f"Value mismatches ({len(self.value_mismatches)}):")
            for r in self.value_mismatches:
                lines.append(f"  ≠ {r}")
        return "\n".join(lines) if lines else "CSV files match."


def load_csv(path: Path, key_column: str = "id") -> dict[str, dict[str, str]]:
    """Load CSV into dict keyed by key_column."""
    result = {}
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter=";"):
            result[row[key_column]] = row
    return result


def _numeric_close(a: str, b: str, rel_tol: float = 0.001) -> bool:
    """Check if two string values are numerically close."""
    try:
        return math.isclose(float(a), float(b), rel_tol=rel_tol)
    except (ValueError, TypeError):
        return a.strip() == b.strip()


def compare_csv(
    reference: Path,
    generated: Path,
    key_column: str = "id",
    numeric_tol: float = 0.001,
) -> CsvDiff:
    """Compare two CSV files semantically.

    Rows are matched by key_column. Numeric values are compared with tolerance.
    """
    ref = load_csv(reference, key_column)
    gen = load_csv(generated, key_column)
    diff = CsvDiff()

    # Rows in reference but not generated
    for key in ref:
        if key not in gen:
            diff.missing_in_generated.append(key)

    # Rows in generated but not reference
    for key in gen:
        if key not in ref:
            diff.missing_in_reference.append(key)

    # Compare matching rows
    for key in ref:
        if key not in gen:
            continue
        for col in ref[key]:
            ref_val = ref[key][col]
            gen_val = gen[key].get(col, "")
            if not _numeric_close(ref_val, gen_val, rel_tol=numeric_tol):
                diff.value_mismatches.append(
                    f"[{key}] {col}: ref={ref_val!r} gen={gen_val!r}"
                )

    diff.row_count_match = len(ref) == len(gen)
    return diff


# ---------------------------------------------------------------------------
# DXF comparison (semantic, requires ezdxf)
# ---------------------------------------------------------------------------

try:
    import ezdxf

    @dataclass
    class DxfCircle:
        """Extracted circle from DXF."""
        cx: float
        cy: float
        diameter: float
        layer: str

    @dataclass
    class DxfDiff:
        """Result of comparing two DXF files."""
        missing_in_generated: list[str] = field(default_factory=list)
        missing_in_reference: list[str] = field(default_factory=list)
        position_mismatches: list[str] = field(default_factory=list)
        layer_mismatches: list[str] = field(default_factory=list)

        @property
        def ok(self) -> bool:
            return (
                not self.missing_in_generated
                and not self.missing_in_reference
                and not self.position_mismatches
            )

        def report(self) -> str:
            lines = []
            for section, items in [
                ("Missing in generated", self.missing_in_reference),
                ("Extra in generated", self.missing_in_generated),
                ("Position mismatches", self.position_mismatches),
                ("Layer mismatches", self.layer_mismatches),
            ]:
                if items:
                    lines.append(f"{section} ({len(items)}):")
                    for item in items:
                        lines.append(f"  {item}")
            return "\n".join(lines) if lines else "DXF files match."

    def extract_circles(path: Path) -> list[DxfCircle]:
        """Extract all CIRCLE entities from a DXF file."""
        doc = ezdxf.readfile(str(path))
        msp = doc.modelspace()
        circles = []
        for entity in msp.query("CIRCLE"):
            dxf = entity.dxf
            circles.append(DxfCircle(
                cx=round(dxf.center.x, 4),
                cy=round(dxf.center.y, 4),
                diameter=round(dxf.radius * 2, 4),
                layer=dxf.layer,
            ))
        return circles

    def _circle_key(c: DxfCircle, pos_tol: float = 0.1) -> tuple:
        """Generate a grouping key for a circle (rounded to tolerance)."""
        return (
            round(c.cx / pos_tol) * pos_tol,
            round(c.cy / pos_tol) * pos_tol,
            round(c.diameter / 0.01) * 0.01,
        )

    def compare_dxf(
        reference: Path,
        generated: Path,
        pos_tol: float = 0.2,
        diam_tol: float = 0.1,
    ) -> DxfDiff:
        """Compare drill circles between two DXF files.

        Matches circles by proximity (position + diameter).
        """
        ref_circles = extract_circles(reference)
        gen_circles = extract_circles(generated)
        diff = DxfDiff()

        gen_matched = [False] * len(gen_circles)

        for ref_c in ref_circles:
            best_idx = -1
            best_dist = float("inf")
            for j, gen_c in enumerate(gen_circles):
                if gen_matched[j]:
                    continue
                dist = math.hypot(ref_c.cx - gen_c.cx, ref_c.cy - gen_c.cy)
                diam_diff = abs(ref_c.diameter - gen_c.diameter)
                if dist < pos_tol and diam_diff < diam_tol and dist < best_dist:
                    best_dist = dist
                    best_idx = j

            if best_idx >= 0:
                gen_matched[best_idx] = True
                gen_c = gen_circles[best_idx]
                if ref_c.layer != gen_c.layer:
                    diff.layer_mismatches.append(
                        f"({ref_c.cx}, {ref_c.cy}) ∅{ref_c.diameter}: "
                        f"ref layer={ref_c.layer!r} gen layer={gen_c.layer!r}"
                    )
            else:
                diff.missing_in_generated.append(
                    f"({ref_c.cx}, {ref_c.cy}) ∅{ref_c.diameter} layer={ref_c.layer!r}"
                )

        for j, gen_c in enumerate(gen_circles):
            if not gen_matched[j]:
                diff.missing_in_reference.append(
                    f"({gen_c.cx}, {gen_c.cy}) ∅{gen_c.diameter} layer={gen_c.layer!r}"
                )

        return diff

except ImportError:
    ezdxf = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Self-tests (using our own generated output)
# ---------------------------------------------------------------------------

class TestCsvSelfCompare:
    """Compare our own generated CSV against itself — should always pass."""

    def test_csv_self_compare(self, tmp_path):
        """Generate CSV, then compare against itself."""
        from kitchen_cad.models import CorpusSpec, HingeSpec
        from kitchen_cad.panel_calculator import calculate_panels
        from kitchen_cad.csv_generator import generate_cutting_csv

        spec = CorpusSpec(
            id="T1", name="Test", corpus_type="base_door",
            width=800, height=720, depth=510,
            doors=[2], hinges=HingeSpec(count=2),
        )
        panels = calculate_panels(spec)
        ref_path = tmp_path / "ref.csv"
        gen_path = tmp_path / "gen.csv"
        generate_cutting_csv(panels, ref_path)
        generate_cutting_csv(panels, gen_path)

        diff = compare_csv(ref_path, gen_path)
        assert diff.ok, diff.report()

    def test_csv_detects_missing_row(self, tmp_path):
        """Should detect when a row is missing from generated."""
        ref_content = "id;width;height\nA;100;200\nB;300;400\n"
        gen_content = "id;width;height\nA;100;200\n"
        ref = tmp_path / "ref.csv"
        gen = tmp_path / "gen.csv"
        ref.write_text(ref_content)
        gen.write_text(gen_content)

        diff = compare_csv(ref, gen)
        assert not diff.ok
        assert any("B" in m for m in diff.missing_in_generated)

    def test_csv_detects_value_mismatch(self, tmp_path):
        ref_content = "id;width;height\nA;100;200\n"
        gen_content = "id;width;height\nA;100;250\n"
        ref = tmp_path / "ref.csv"
        gen = tmp_path / "gen.csv"
        ref.write_text(ref_content)
        gen.write_text(gen_content)

        diff = compare_csv(ref, gen)
        assert not diff.ok
        assert len(diff.value_mismatches) == 1


@pytest.mark.skipif(ezdxf is None, reason="ezdxf not installed")
class TestDxfSelfCompare:
    """DXF self-comparison — our output against itself."""

    def _generate_test_dxf(self, path: Path):
        """Create a minimal DXF with drill circles."""
        doc = ezdxf.new("R2000")
        msp = doc.modelspace()
        doc.layers.add("WIERCENIE", color=3)
        # Two drill holes
        msp.add_circle(
            center=(37, 100), radius=2.5,
            dxfattribs={"layer": "WIERCENIE"},
        )
        msp.add_circle(
            center=(37, 132), radius=2.5,
            dxfattribs={"layer": "WIERCENIE"},
        )
        doc.saveas(str(path))

    def test_dxf_self_compare(self, tmp_path):
        ref = tmp_path / "ref.dxf"
        gen = tmp_path / "gen.dxf"
        self._generate_test_dxf(ref)
        self._generate_test_dxf(gen)

        diff = compare_dxf(ref, gen)
        assert diff.ok, diff.report()

    def test_dxf_detects_missing_circle(self, tmp_path):
        """Extra circle in generated → detected as missing_in_reference."""
        ref = tmp_path / "ref.dxf"
        gen = tmp_path / "gen.dxf"

        # Reference: 1 circle
        doc = ezdxf.new("R2000")
        msp = doc.modelspace()
        doc.layers.add("WIERCENIE", color=3)
        msp.add_circle(center=(37, 100), radius=2.5, dxfattribs={"layer": "WIERCENIE"})
        doc.saveas(str(ref))

        # Generated: 2 circles
        msp.add_circle(center=(37, 132), radius=2.5, dxfattribs={"layer": "WIERCENIE"})
        doc.saveas(str(gen))

        diff = compare_dxf(ref, gen)
        assert not diff.ok
        assert len(diff.missing_in_reference) == 1
