"""Edging CSV export tests.

Proves: kitchen panels → per-edge CSV worklist for the banding operator.
Verifies Polish CNC semicolon format (UTF-8-SIG BOM, ``;`` delimiter,
Polish headers) — matches the format used by ``cutlist_csv``.
"""

from __future__ import annotations

from pathlib import Path

from kuchnie_core.export.edging_csv import (
    HEADER,
    collect_edging_rows,
    export_edging_csv,
    rows_to_csv,
)
from kuchnie_core.kitchen import all_panels
from kuchnie_core.loader import load_kitchen
from kuchnie_core.model import EdgeBand, Kitchen, Panel, Row

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def _kitchen() -> Kitchen:
    return load_kitchen(FIXTURES / "kitchen_01.yaml")


# ── Row collection ──────────────────────────────────────────────

def test_only_banded_edges_appear() -> None:
    """Panels without banding contribute zero rows; banded ones contribute
    one row per side present in ``banded_edges``."""
    panels = [
        Panel(
            id="A", name="A", material="m", thickness_mm=18,
            width_mm=500, height_mm=700,
            banded_edges={},  # no banding
        ),
        Panel(
            id="B", name="B", material="m", thickness_mm=18,
            width_mm=500, height_mm=700,
            banded_edges={
                "front": EdgeBand(material="ABS_U119", thickness_mm=0.8, length_mm=500),
                "left":  EdgeBand(material="ABS_U119", thickness_mm=0.8, length_mm=700),
            },
        ),
    ]
    rows = collect_edging_rows(panels)
    assert [r.panel_id for r in rows] == ["B", "B"]
    assert {r.side for r in rows} == {"front", "left"}


def test_edge_length_follows_side_convention() -> None:
    """front/back edges → width_mm; left/right edges → height_mm."""
    panel = Panel(
        id="P", name="P", material="m", thickness_mm=18,
        width_mm=500, height_mm=700,
        banded_edges={
            "front": EdgeBand(material="ABS", thickness_mm=0.8, length_mm=0),
            "back":  EdgeBand(material="ABS", thickness_mm=0.8, length_mm=0),
            "left":  EdgeBand(material="ABS", thickness_mm=0.8, length_mm=0),
            "right": EdgeBand(material="ABS", thickness_mm=0.8, length_mm=0),
        },
    )
    rows = {r.side: r.length_mm for r in collect_edging_rows([panel])}
    assert rows["front"] == 500
    assert rows["back"]  == 500
    assert rows["left"]  == 700
    assert rows["right"] == 700


def test_kitchen_fixture_produces_rows() -> None:
    """Real fixture: rows exist and each one references a real panel."""
    kitchen = _kitchen()
    panels = all_panels(kitchen)
    rows = collect_edging_rows(panels)
    assert len(rows) > 0
    panel_ids = {p.id for p in panels}
    assert all(r.panel_id in panel_ids for r in rows)


# ── CSV format ──────────────────────────────────────────────────

def test_csv_uses_semicolon_delimiter() -> None:
    """Polish CNC convention — every non-empty line has the same
    number of semicolons as the header."""
    kitchen = _kitchen()
    text = rows_to_csv(collect_edging_rows(all_panels(kitchen)))
    lines = [line for line in text.splitlines() if line]
    assert lines, "expected at least one row"
    expected = lines[0].count(";")
    for line in lines[1:]:
        assert line.count(";") == expected


def test_csv_header_is_polish() -> None:
    text = rows_to_csv([])
    first_line = text.splitlines()[0]
    assert first_line == ";".join(HEADER)
    # sanity — headers include Polish diacritics
    assert "Krawędź" in first_line
    assert "Długość_mm" in first_line
    assert "Materiał" in first_line


def test_export_writes_utf8_sig_bom(tmp_path: Path) -> None:
    """File is written with a UTF-8 BOM so Excel/LibreOffice open it
    directly with correct diacritics."""
    out = export_edging_csv(_kitchen(), tmp_path / "edging.csv")
    raw = out.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf"), "expected UTF-8 BOM"


def test_export_round_trip(tmp_path: Path) -> None:
    """Written file can be re-parsed and matches ``rows_to_csv`` output."""
    kitchen = _kitchen()
    out = export_edging_csv(kitchen, tmp_path / "edging.csv")
    text = out.read_text(encoding="utf-8-sig")
    expected = rows_to_csv(collect_edging_rows(all_panels(kitchen)))
    assert text == expected


# ── Package-level re-export contract ────────────────────────────
# ``kuchnie_core`` re-exports its public entrypoints; ``edging_csv`` should
# follow the same convention as its sister ``cutlist_csv``.

def test_edging_csv_reexported_from_kuchnie_core() -> None:
    import kuchnie_core

    assert hasattr(kuchnie_core, "export_edging_csv")
    assert hasattr(kuchnie_core, "collect_edging_rows")
    assert "export_edging_csv" in kuchnie_core.__all__
    assert "collect_edging_rows" in kuchnie_core.__all__

    # Same callable reached via both import paths.
    from kuchnie_core.export.edging_csv import export_edging_csv as direct
    assert kuchnie_core.export_edging_csv is direct


# ── Cutlist CSV format sanity ───────────────────────────────────
# Also asserted here (small guard test) so a regression in cutlist_csv's
# Polish format shows up next to its sister test.

def test_cutlist_csv_polish_format(tmp_path: Path) -> None:
    """cutlist_csv preserves Polish semicolon format from ADR-010."""
    from kuchnie_core.export.cutlist_csv import export_cutlist_csv

    out = export_cutlist_csv(_kitchen(), tmp_path / "cut.csv")
    raw = out.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf"), "expected UTF-8 BOM"
    text = raw.decode("utf-8-sig")
    header = text.splitlines()[0]
    assert ";" in header, "expected semicolon-delimited CSV"
    # Polish headers are the contract; check a couple of diacritic tokens.
    assert "Materiał" in header
    assert "Grubość" in header
    assert "Ilość" in header
