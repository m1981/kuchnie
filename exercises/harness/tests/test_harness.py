"""Harness self-tests: golden parsing/diff, writers, gap log.

Run:  .venv/bin/python -m pytest exercises/harness/tests -q
No bpy needed — hb5.py is exercised only inside Blender legs.
"""
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "kuchnie-core" / "src"))
sys.path.insert(0, str(REPO / "exercises"))

from kuchnie_core.decomposer import decompose  # noqa: E402
from kuchnie_core.model import CabinetInstance  # noqa: E402
from harness.gaps import GapLog  # noqa: E402
from harness.golden import (  # noqa: E402
    GoldenPanel,
    diff_panels,
    read_golden_panels,
)
from harness.writers import write_bom, write_cnc, write_rozrys  # noqa: E402


def d60() -> CabinetInstance:
    """The e2e-d60 scenario, decomposed live (not from committed CSVs)."""
    return CabinetInstance(
        id="D60S3", type="dolna_legrabox", description="harness test",
        width_mm=600, height_mm=820, depth_mm=560,
        body_material="PLYTA_BIALA_18", back_material="HDF_BIALA_3",
        front_material="K5307_18", thickness_back_mm=3, plinth_height_mm=100,
        drawers=[{"id": f"S{i+1}", "height_code": c, "nl": 500,
                  "capacity_kg": 40, "wysokosc": h}
                 for i, (c, h) in enumerate([("M", 140), ("C", 287), ("C", 287)])],
        fronts=[{"id": f"F{i+1}", "typ": "szufladowy", "powiazany": f"S{i+1}"}
                for i in range(3)],
        edge_banding_type="abs",
    )


# ── golden parsing ───────────────────────────────────────────────

def test_read_golden_panels(tmp_path):
    p = tmp_path / "panels.csv"
    p.write_text("Element;Dlugosc;Szerokosc;Grubosc;Ilosc;Material;Uslojenie\n"
                 "Bok lewy;720;560;18;1;PLYTA_BIALA_18;brak\n"
                 "Front M;140;596;18;1;K5307_18;pion\n", encoding="utf-8")
    panels = read_golden_panels(p)
    assert len(panels) == 2
    assert panels[0].uslojenie == "brak"
    assert panels[1].uslojenie == "pion"


def test_golden_rejects_bad_grain():
    with pytest.raises(ValueError, match="Uslojenie"):
        GoldenPanel("X", 100, 100, 18, 1, "M", "diagonal")


# ── grain-aware diff ─────────────────────────────────────────────

def test_brak_panels_match_rotated():
    """A 'brak' golden matches a generated panel with swapped dims (the
    dno/trawers Dlugosc-orientation case from e2e-d60, P3)."""
    golden = [GoldenPanel("Dno", 564, 560, 18, 1, "PLYTA_BIALA_18", "brak")]
    result = decompose(d60())
    result.panels = [p for p in result.panels if p.name == "Dno"]
    diff = diff_panels(golden, result)
    assert diff.matched == 1 and diff.clean


def test_pion_panels_do_not_rotate():
    """Grain-constrained panels must match orientation exactly."""
    golden = [GoldenPanel("Front F1", 594, 140, 18, 1, "K5307_18", "pion")]
    result = decompose(d60())
    result.panels = [p for p in result.panels if p.name == "Front F1"]
    diff = diff_panels(golden, result)  # generated is 140x594 — swapped
    assert diff.matched == 0


def test_full_d60_diff_against_expected_golden():
    """The whole scenario: golden mirroring GOLDEN.md of e2e-d60-legrabox
    with pipeline-convention fronts (594) and material names — clean diff."""
    golden = [
        GoldenPanel("Bok lewy", 720, 560, 18, 1, "PLYTA_BIALA_18", "brak"),
        GoldenPanel("Bok prawy", 720, 560, 18, 1, "PLYTA_BIALA_18", "brak"),
        GoldenPanel("Dno", 564, 560, 18, 1, "PLYTA_BIALA_18", "brak"),
        GoldenPanel("Trawers przedni", 564, 100, 18, 1, "PLYTA_BIALA_18", "brak"),
        GoldenPanel("Trawers tylny", 564, 100, 18, 1, "PLYTA_BIALA_18", "brak"),
        GoldenPanel("Plecy", 698, 578, 3, 1, "HDF_BIALA_3", "brak"),
        GoldenPanel("Front M", 140, 594, 18, 1, "K5307_18", "pion"),
        GoldenPanel("Front C", 287, 594, 18, 2, "K5307_18", "pion"),
        GoldenPanel("Szuflada dno", 490, 503, 16, 3, "plyta_16mm", "brak"),
        GoldenPanel("Szuflada tyl M", 63, 500, 16, 1, "plyta_16mm", "brak"),
        GoldenPanel("Szuflada tyl C", 148, 500, 16, 2, "plyta_16mm", "brak"),
        GoldenPanel("Cokol", 97, 596, 18, 1, "PLYTA_BIALA_18", "brak"),
    ]
    diff = diff_panels(golden, decompose(d60()))
    assert diff.clean, diff.text()
    assert diff.matched == 16  # quantities expanded


def test_diff_reports_missing_and_extra():
    golden = [GoldenPanel("Widmo", 999, 999, 18, 1, "X", "brak")]
    result = decompose(d60())
    result.panels = [p for p in result.panels if p.name == "Cokół"]
    diff = diff_panels(golden, result)
    assert diff.missing == 1 and diff.extra == 1 and not diff.clean


def test_diff_near_miss_is_delta():
    """596 vs generated 594 fronts (G12) land as DELTA, not MISSING."""
    golden = [GoldenPanel("Front M", 140, 596, 18, 1, "K5307_18", "pion")]
    result = decompose(d60())
    result.panels = [p for p in result.panels if p.name == "Front F1"]
    diff = diff_panels(golden, result)
    assert diff.deltas == 1 and diff.missing == 0


# ── writers ──────────────────────────────────────────────────────

def test_writers_produce_contract_shapes(tmp_path):
    result = decompose(d60())
    rozrys = write_rozrys(result.panels, tmp_path / "rozrys.csv")
    bom = write_bom(result, tmp_path / "bom.csv")
    cnc = write_cnc(result, tmp_path / "cnc.txt", title="D60S3")

    lines = rozrys.read_text(encoding="utf-8-sig").strip().split("\n")
    assert lines[0].startswith("Lp;Element;Dlugosc")
    assert len(lines) == 1 + len(result.panels)
    assert sum(1 for l in lines if ";pion;" in l) == 3  # K5307 fronts

    bom_text = bom.read_text(encoding="utf-8-sig")
    assert "Plyta;HDF_BIALA_3;0.403;m2;netto" in bom_text  # 698x578 back

    cnc_text = cnc.read_text()
    assert cnc_text.count("[confirmat]") == 10
    assert cnc_text.count("GROOVE") == 4


# ── gap log ──────────────────────────────────────────────────────

def test_gap_log_counts_and_persists(tmp_path):
    g = GapLog()
    g.log("progress line")
    g.gap("hand re-entry one")
    g.gap("hand re-entry two")
    assert g.gap_count == 2
    g.write(tmp_path / "log.txt")
    assert "hand re-entry two" in (tmp_path / "log.txt").read_text()
