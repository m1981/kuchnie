"""Cut list CSV export tests.

Proves: kitchen panels → aggregated CSV with correct counts and edge banding.
"""

import csv
import io
import tempfile
from pathlib import Path

from kuchnie_core.loader import load_kitchen
from kuchnie_core.kitchen import all_panels
from kuchnie_core.export.cutlist_csv import (
    aggregate_panels,
    pieces_to_csv,
    export_cutlist_csv,
)

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def _kitchen():
    return load_kitchen(FIXTURES / "kitchen_01.yaml")


# ── Aggregation ─────────────────────────────────────────────────

def test_aggregate_reduces_count():
    """15 raw panels → fewer unique cut pieces (some share dimensions)."""
    kitchen = _kitchen()
    panels = all_panels(kitchen)
    pieces = aggregate_panels(panels)
    assert len(pieces) < len(panels)
    assert len(pieces) > 0


def test_aggregate_sums_quantities():
    """K01 and G01 have identical side-panel dimensions (same depth, same height)
    only if depth and height match — they don't (510 vs 300, 620 vs 720),
    so sides should NOT merge.  But two sides WITHIN one cabinet should."""
    kitchen = _kitchen()
    panels = all_panels(kitchen)
    pieces = aggregate_panels(panels)

    # K01 left + right sides are identical → aggregated to qty=2
    k01_side = next(
        (p for p in pieces if "bok" in p.name.lower() and p.source == "K01"),
        None,
    )
    assert k01_side is not None
    assert k01_side.quantity == 2   # left + right merged


def test_aggregate_preserves_edge_info():
    kitchen = _kitchen()
    panels = all_panels(kitchen)
    pieces = aggregate_panels(panels)

    # Back panels: no banding
    backs = [p for p in pieces if "plecy" in p.name.lower()]
    for b in backs:
        assert b.edge_front is False
        assert b.edge_back is False

    # Drawer fronts: all 4 edges
    drawer_fronts = [p for p in pieces if "front" in p.name.lower()
                     and p.thickness_mm == 18 and p.height_mm < 400]
    for df in drawer_fronts:
        assert df.edge_front is True
        assert df.edge_back is True
        assert df.edge_left is True
        assert df.edge_right is True


# ── CSV output ──────────────────────────────────────────────────

def test_csv_is_parseable():
    kitchen = _kitchen()
    panels = all_panels(kitchen)
    pieces = aggregate_panels(panels)
    text = pieces_to_csv(pieces)
    reader = csv.reader(io.StringIO(text), delimiter=";")
    rows = list(reader)
    assert rows[0][0] == "Nr"       # header
    assert len(rows) == len(pieces) + 1  # header + data rows


def test_csv_has_all_pieces():
    kitchen = _kitchen()
    panels = all_panels(kitchen)
    pieces = aggregate_panels(panels)
    text = pieces_to_csv(pieces)
    reader = csv.DictReader(io.StringIO(text), delimiter=";")
    csv_pieces = list(reader)
    assert len(csv_pieces) == len(pieces)


def test_export_creates_file():
    kitchen = _kitchen()
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
        path = Path(f.name)
    try:
        result = export_cutlist_csv(kitchen, path)
        assert result == path
        assert path.stat().st_size > 0
        content = path.read_text(encoding="utf-8-sig")
        assert "Nr;" in content
    finally:
        path.unlink()


def test_csv_total_quantity_matches_raw_panels():
    """Sum of qty in CSV must equal total number of raw panels."""
    kitchen = _kitchen()
    panels = all_panels(kitchen)
    pieces = aggregate_panels(panels)
    total_qty = sum(p.quantity for p in pieces)
    # Each raw panel has qty=1, so total pieces = len(panels)
    assert total_qty == len(panels)   # 15
