# tests/test_purchasing_order_docs.py
"""wk-593a317b -- board / edging / hardware order-doc generators.

Golden-first: the three CSVs under
exercises/walking-skeleton-d60/reference/{board,edging,hardware}-order.csv
are hand-computed and owner-confirmed (2026-08-01, see
purchasing-ASSUMPTIONS.md in the same directory) -- they are NOT edited by
these tests. The D60 cabinet is built the same way
exercises/walking-skeleton-d60/run_production_leg.py's build_instance()
does on its hand-entered fallback path (no Blender extraction available):
600x820x560, 100mm plinth, drawers M/C/C at NL500/40kg with front heights
140/287/287, no handles.

Row comparison is column-by-column, EXCLUDING Uwagi (free text) -- per the
task brief, Uwagi is deliberately not checked. Some golden Uwagi cells
contain an unescaped ';' (e.g. hardware-order.csv row 3), which would
otherwise misalign a naive csv-diff; ``_read_golden_data_cols`` truncates
every golden row to the generator's data-column count before comparing, so
that spillover never leaks into the comparison.

Golden-correction history: edging-order.csv's corpus (0.8mm) row
originally stated Netto_mb=2.57 -- a hand-arithmetic slip omitting the
cokol's 596mm edge while its own note listed cokol. Verified against the
decomposition's emitted geometry (720x2 + 564x2 + 596 = 3.16mb) and
corrected in the golden on 2026-08-01; the corpus-row test keeps an
independent recomputation so golden, generator and geometry stay pinned
three ways.
"""
import csv
from pathlib import Path

import pytest
from kuchnie_core.decomposer import decompose
from kuchnie_core.model import Accessory, CabinetInstance, DecompositionResult, Panel

from kitchen_erp.core.purchasing import (
    BOARD_ORDER_HEADER,
    EDGING_ORDER_HEADER,
    HARDWARE_ORDER_HEADER,
    board_order_rows,
    board_order_rows_to_csv,
    edging_order_rows,
    edging_order_rows_to_csv,
    hardware_order_rows,
    hardware_order_rows_to_csv,
)

REFERENCE = (
    Path(__file__).resolve().parent.parent.parent
    / "exercises" / "walking-skeleton-d60" / "reference"
)


# ── D60 cabinet (mirrors walking-skeleton-d60/run_production_leg.py's
#    build_instance() hand-entered fallback exactly) ────────────────────

def build_d60_cabinet() -> CabinetInstance:
    drawer_heights = [140, 287, 287]
    codes = ["M", "C", "C"]
    drawers = [
        {"id": f"S{i+1}", "height_code": c, "nl": 500, "capacity_kg": 40,
         "wysokosc": h}
        for i, (c, h) in enumerate(zip(codes, drawer_heights))
    ]
    fronts = [
        {"id": f"F{i+1}", "typ": "szufladowy", "powiazany": f"S{i+1}"}
        for i in range(3)
    ]
    return CabinetInstance(
        id="D60S3",
        type="dolna_legrabox",
        description="walking skeleton D60 (hand-entered)",
        width_mm=600,
        height_mm=820,
        depth_mm=560,
        body_material="PLYTA_BIALA_18",
        back_material="HDF_BIALA_3",
        front_material="K5307_18",
        thickness_back_mm=3,
        plinth_height_mm=100,
        drawers=drawers,
        fronts=fronts,
        edge_banding_type="abs",
    )


@pytest.fixture(scope="module")
def d60_result() -> DecompositionResult:
    return decompose(build_d60_cabinet())


# ── Golden CSV reading ───────────────────────────────────────────────

def _read_golden_data_cols(path: Path, n_data_cols: int) -> list[list[str]]:
    """Read a golden CSV, truncating every row to its first
    ``n_data_cols`` fields (drops Uwagi and any accidental spillover from
    an unescaped ';' inside a Uwagi cell)."""
    with path.open(encoding="utf-8-sig") as f:
        rows = list(csv.reader(f, delimiter=";"))
    return [r[:n_data_cols] for r in rows]


def _generated_data_cols(csv_text: str, n_data_cols: int) -> list[list[str]]:
    rows = list(csv.reader(csv_text.splitlines(), delimiter=";"))
    return [r[:n_data_cols] for r in rows]


# ── Board order ──────────────────────────────────────────────────────

def test_board_order_header_matches_golden():
    golden = _read_golden_data_cols(REFERENCE / "board-order.csv", len(BOARD_ORDER_HEADER))
    assert BOARD_ORDER_HEADER == golden[0]


def test_board_order_rows_match_golden_exactly(d60_result):
    n = len(BOARD_ORDER_HEADER) - 1  # exclude Uwagi
    golden = _read_golden_data_cols(REFERENCE / "board-order.csv", n)
    generated = _generated_data_cols(
        board_order_rows_to_csv(board_order_rows(d60_result)), n
    )
    assert len(generated) == len(golden), (
        f"row count differs: golden={len(golden)-1} generated={len(generated)-1}"
    )
    for i, (g, m) in enumerate(zip(golden, generated)):
        assert g == m, f"board-order.csv row {i} differs:\n golden={g}\n  generated={m}"


# ── Edging order ─────────────────────────────────────────────────────

def test_edging_order_header_matches_golden():
    golden = _read_golden_data_cols(REFERENCE / "edging-order.csv", len(EDGING_ORDER_HEADER))
    assert EDGING_ORDER_HEADER == golden[0]


def test_edging_order_front_row_matches_golden_exactly(d60_result):
    """The K5307 (2.0mm/front) row matches the golden on every column."""
    n = len(EDGING_ORDER_HEADER) - 1
    golden = _read_golden_data_cols(REFERENCE / "edging-order.csv", n)
    generated = _generated_data_cols(
        edging_order_rows_to_csv(edging_order_rows(d60_result)), n
    )
    front_golden = next(r for r in golden if "K5307" in r[2])
    front_generated = next(r for r in generated if "K5307" in r[2])
    assert front_golden == front_generated


def test_edging_order_corpus_row_matches_golden_exactly(d60_result):
    """The corpus (0.8mm/bialy korpusowy) row matches the golden on every
    column. The golden originally stated 2.57mb -- a hand-arithmetic slip
    that omitted the cokol's 596mm edge while its own note listed cokol --
    and was corrected to 3.16mb on 2026-08-01 after verification against
    the decomposition's emitted geometry (720x2 + 564x2 + 596). The
    independent recomputation below keeps guarding that the golden, the
    generator, and the emitted panels agree three ways."""
    n = len(EDGING_ORDER_HEADER) - 1
    golden = _read_golden_data_cols(REFERENCE / "edging-order.csv", n)
    generated = _generated_data_cols(
        edging_order_rows_to_csv(edging_order_rows(d60_result)), n
    )
    corpus_golden = next(r for r in golden if r[2] == "bialy korpusowy")
    corpus_generated = next(r for r in generated if r[2] == "bialy korpusowy")

    # Independent recomputation straight from the decomposition's panels
    # (not via the generator under test).
    expected_mb = sum(
        band.length_mm
        for p in d60_result.panels
        for band in p.banded_edges.values()
        if band.material == "abs_PLYTA_BIALA_18"
    ) / 1000
    assert corpus_generated[5] == f"{expected_mb:.2f}"  # Netto_mb column
    assert corpus_golden == corpus_generated


# ── Hardware order ───────────────────────────────────────────────────

def test_hardware_order_header_matches_golden():
    golden = _read_golden_data_cols(REFERENCE / "hardware-order.csv", len(HARDWARE_ORDER_HEADER))
    assert HARDWARE_ORDER_HEADER == golden[0]


def test_hardware_order_rows_match_golden_exactly(d60_result):
    n = len(HARDWARE_ORDER_HEADER) - 1  # exclude Uwagi
    golden = _read_golden_data_cols(REFERENCE / "hardware-order.csv", n)
    generated = _generated_data_cols(
        hardware_order_rows_to_csv(hardware_order_rows(d60_result)), n
    )
    assert len(generated) == len(golden), (
        f"row count differs: golden={len(golden)-1} generated={len(generated)-1}"
    )
    for i, (g, m) in enumerate(zip(golden, generated)):
        assert g == m, f"hardware-order.csv row {i} differs:\n golden={g}\n  generated={m}"


def test_hardware_order_konfirmat_quantity_matches_g13_derivation(d60_result):
    """The Konfirmat row's Ilosc_netto must equal the confirmat op count
    G13 derives in catalog.py -- 10 for the D60 (single source of truth,
    not a coincidence of two hard-coded numbers)."""
    confirmat_ops = sum(
        1 for p in d60_result.panels for op in p.machining_ops
        if op.drill_type == "confirmat"
    )
    assert confirmat_ops == 10
    rows = hardware_order_rows(d60_result)
    konfirmat = next(r for r in rows if r.pozycja == "Konfirmat 7x50")
    assert konfirmat.ilosc_netto == confirmat_ops
    assert konfirmat.ilosc_zamowiona == 0  # stock draw, never a PO line


# ── Catalog completeness (fail loud on unmapped materials/accessories) ──

def _bare_result(**kw) -> DecompositionResult:
    return DecompositionResult(cabinet_id="t", cabinet_type="t", **kw)


def test_board_order_rows_raises_on_unmapped_material():
    panel = Panel(id="p1", name="X", material="UNKNOWN_BOARD",
                  thickness_mm=18, width_mm=100, height_mm=100)
    with pytest.raises(ValueError, match="UNKNOWN_BOARD"):
        board_order_rows(_bare_result(panels=[panel]))


def test_hardware_order_rows_raises_on_unmapped_accessory():
    acc = Accessory(id="a1", name="Nieznane okucie", type="misc", quantity=1)
    with pytest.raises(ValueError, match="Nieznane okucie"):
        hardware_order_rows(_bare_result(accessories=[acc]))


# ── LEGRABOX colour parameter ────────────────────────────────────────

def test_hardware_order_colour_is_per_project_parameter(d60_result):
    """Colour is a per-project parameter (owner decision 2026-08-02):
    default is jedwabiscie bialy (JBM); an override changes the Pozycja
    of every colour-bearing Blum line (boki + sprzegla) and nothing
    else — base codes are geometry-only and must not move."""
    default_rows = hardware_order_rows(d60_result)
    dark_rows = hardware_order_rows(d60_result, legrabox_colour="czarny (CS-M)")

    assert len(default_rows) == len(dark_rows)
    changed = [
        (d, k) for d, k in zip(default_rows, dark_rows) if d.pozycja != k.pozycja
    ]
    # D60: boki M, boki C, sprzeglo M, sprzeglo C = 4 colour-bearing lines
    assert len(changed) == 4
    for d, k in changed:
        assert "jedwabiscie bialy (JBM)" in d.pozycja
        assert "czarny (CS-M)" in k.pozycja
        assert d.kod_producenta == k.kod_producenta
        assert d.ilosc_zamowiona == k.ilosc_zamowiona
