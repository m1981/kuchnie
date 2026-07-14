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
    golden = [GoldenPanel("Front F1", 596, 140, 18, 1, "K5307_18", "pion")]
    result = decompose(d60())
    result.panels = [p for p in result.panels if p.name == "Front F1"]
    diff = diff_panels(golden, result)  # generated is 140x596 — swapped
    assert diff.matched == 0


def test_full_d60_diff_against_expected_golden():
    """The whole scenario: golden mirroring GOLDEN.md of e2e-d60-legrabox
    with pipeline-convention fronts (596 — G12 2mm shop reveal, wk-f3ce63bf)
    and material names — clean diff."""
    golden = [
        GoldenPanel("Bok lewy", 720, 560, 18, 1, "PLYTA_BIALA_18", "brak"),
        GoldenPanel("Bok prawy", 720, 560, 18, 1, "PLYTA_BIALA_18", "brak"),
        GoldenPanel("Dno", 564, 560, 18, 1, "PLYTA_BIALA_18", "brak"),
        GoldenPanel("Trawers przedni", 564, 100, 18, 1, "PLYTA_BIALA_18", "brak"),
        GoldenPanel("Trawers tylny", 564, 100, 18, 1, "PLYTA_BIALA_18", "brak"),
        GoldenPanel("Plecy", 698, 578, 3, 1, "HDF_BIALA_3", "brak"),
        GoldenPanel("Front M", 140, 596, 18, 1, "K5307_18", "pion"),
        GoldenPanel("Front C", 287, 596, 18, 2, "K5307_18", "pion"),
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
    """A 2mm-off golden (authored under the pre-G12 594 convention) lands
    as DELTA against today's 596 fronts — not MISSING."""
    golden = [GoldenPanel("Front M", 140, 594, 18, 1, "K5307_18", "pion")]
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


def test_gap_log_fail_modes():
    from harness.gaps import HarnessFailure
    g = GapLog(strict=False)
    g.fail("tolerated in exploration")
    assert g.fail_count == 1 and g.gap_count == 0
    with pytest.raises(HarnessFailure, match="escalated"):
        GapLog(strict=True).fail("escalated in strict mode")


def test_gap_log_strict_from_env(monkeypatch):
    monkeypatch.setenv("KUCHNIE_STRICT", "1")
    assert GapLog().strict
    monkeypatch.delenv("KUCHNIE_STRICT")
    assert not GapLog().strict


# ── labels: single source ────────────────────────────────────────

def test_grain_label_single_source():
    from kuchnie_core.model import GrainAxis
    from harness.labels import grain_label
    assert grain_label(GrainAxis.HEIGHT) == "pion"
    assert grain_label(GrainAxis.WIDTH) == "poziom"
    assert grain_label(None) == "brak"
    # unknown values surface verbatim instead of masquerading as 'brak'
    assert grain_label("diagonal") == "diagonal"


# ── config: env-overridable paths ────────────────────────────────

def test_config_env_overrides(monkeypatch):
    from harness import config
    monkeypatch.setenv("KUCHNIE_HB5_PATH", "/opt/hb5")
    monkeypatch.setenv("BLENDER_BIN", "/opt/blender")
    assert str(config.hb5_path()) == "/opt/hb5"
    assert str(config.hb5_parent()) == "/opt"
    assert str(config.blender_bin()) == "/opt/blender"
    assert config.repo_root().name == "kuchnie"


# ── distance-sorted near-miss matching ───────────────────────────

def test_near_miss_prefers_closest_pair():
    """Two goldens 760 and 764 vs generated 762 and 764: greedy first-fit
    would give 760->762 and 764->764 or mispair; distance-first must pair
    764 exactly (pass 1) and 760->762 as the only delta."""
    from kuchnie_core.model import Panel
    from kuchnie_core.model import DecompositionResult
    result = DecompositionResult(cabinet_id="t", cabinet_type="x")
    for i, w in enumerate((762, 764)):
        result.panels.append(Panel(
            id=f"p{i}", name=f"Polka {w}", material="M", thickness_mm=18,
            width_mm=w, height_mm=300))
    golden = [
        GoldenPanel("Polka A", 300, 760, 18, 1, "M", "brak"),
        GoldenPanel("Polka B", 300, 764, 18, 1, "M", "brak"),
    ]
    diff = diff_panels(golden, result)
    assert diff.matched == 1 and diff.deltas == 1
    delta_line = next(l for l in diff.lines if "DELTA" in l)
    assert "Polka A" in delta_line and "762" in delta_line


# ── machining-ops oracle (the G8 catcher) ────────────────────────

def _golden_ops_d60_correct():
    """Runner rows as DESIGNED (C bottom, C middle, M top): Y = 55/342/629."""
    from harness.ops import GoldenOp
    ops = []
    for side in ("Bok lewy", "Bok prawy"):
        for y in (55, 342, 629):
            for x in (46, 78, 110, 398):
                ops.append(GoldenOp(side, "drill", x=x, y=y, srednica=5,
                                    glebokosc=12, drill_type="runner_screw"))
        for x, y in ((50, 9), (280, 9), (510, 9), (50, 711), (510, 711)):
            ops.append(GoldenOp(side, "drill", x=x, y=y, srednica=7,
                                glebokosc=18, drill_type="confirmat"))
        ops.append(GoldenOp(side, "groove", x=12, glebokosc=8,
                            szerokosc=4, dlugosc=720))
    for elem, length in (("Dno", 564), ("Trawers tylny", 564)):
        ops.append(GoldenOp(elem, "groove", x=12, glebokosc=8,
                            szerokosc=4, dlugosc=length))
    return ops


def test_ops_diff_catches_g8_drawer_order():
    """The M-first input (G8) drills runner rows at Y=195/482 instead of
    342/629 — the ops oracle must flag exactly those 16 wrong drills,
    while confirmats and grooves match."""
    from harness.ops import diff_ops
    diff = diff_ops(_golden_ops_d60_correct(), decompose(d60()))
    assert not diff.clean
    assert diff.missing == 16 and diff.extra == 16  # 2 rows x 4 holes x 2 sides
    assert diff.matched == 10 + 4 + 8               # confirmats + grooves + Y=55 row
    assert any("MISSING" in l and ",342)" in l for l in diff.lines)
    assert any("EXTRA" in l and ",195)" in l for l in diff.lines)


def test_ops_diff_clean_when_golden_matches_behavior():
    """Golden authored bottom-up (M rows at 55, C at 195/482) diffs clean —
    proving the 16/16 above is G8, not harness noise."""
    from harness.ops import GoldenOp, diff_ops
    ops = []
    for side in ("Bok lewy", "Bok prawy"):
        for y in (55, 195, 482):
            for x in (46, 78, 110, 398):
                ops.append(GoldenOp(side, "drill", x=x, y=y, srednica=5,
                                    glebokosc=12, drill_type="runner_screw"))
        for x, y in ((50, 9), (280, 9), (510, 9), (50, 711), (510, 711)):
            ops.append(GoldenOp(side, "drill", x=x, y=y, srednica=7,
                                glebokosc=18, drill_type="confirmat"))
        ops.append(GoldenOp(side, "groove", x=12, glebokosc=8,
                            szerokosc=4, dlugosc=720))
    for elem, length in (("Dno", 564), ("Trawers tylny", 564)):
        ops.append(GoldenOp(elem, "groove", x=12, glebokosc=8,
                            szerokosc=4, dlugosc=length))
    diff = diff_ops(ops, decompose(d60()))
    assert diff.clean, diff.text()


def test_ops_csv_roundtrip(tmp_path):
    from harness.ops import read_golden_ops
    p = tmp_path / "ops.csv"
    p.write_text("Element;Typ;X;Y;Srednica;Glebokosc;Szerokosc;Dlugosc;DrillType\n"
                 "Bok lewy;drill;46;55;5;12;;;runner_screw\n"
                 "Bok lewy;groove;12;;;8;4;720;\n", encoding="utf-8")
    ops = read_golden_ops(p)
    assert len(ops) == 2
    assert ops[0].drill_type == "runner_screw" and ops[0].y == 55
    assert ops[1].typ == "groove" and ops[1].y is None


# ── hardware oracle (the G13 meter) ──────────────────────────────

def test_hardware_diff_measures_g13():
    """Golden lists the full hardware; the pipeline emits runners only —
    the diff must report the missing types, and match the runners."""
    from harness.hardware import GoldenHardware, diff_hardware
    golden = [
        GoldenHardware("runner", "LEGRABOX kpl. NL500 40kg", 3),
        GoldenHardware("confirmat", "Konfirmat 7x50", 10),
        GoldenHardware("leg", "Nozka regulowana 100", 4),
        GoldenHardware("plinth_clip", "Klips cokolowy", 2),
    ]
    diff = diff_hardware(golden, decompose(d60()))
    assert diff.matched >= 1          # runners
    assert diff.missing == 3          # confirmat, leg, plinth_clip (G13)
    assert any("confirmat" in l and "MISSING" in l for l in diff.lines)


# ── scaffold (pinned, generates into tmp and runs the leg) ───────

def test_scaffold_creates_runnable_exercise(tmp_path):
    import subprocess
    from harness.scaffold import create_exercise
    target = create_exercise("smoke", tmp_path)
    expected = {"GOLDEN.md", "GAP-REPORT.md", "blender_leg.py",
                "run_production_leg.py"}
    assert expected <= {f.name for f in target.iterdir()}
    assert (target / "golden" / "panels.csv").exists()
    assert (target / "golden" / "ops.csv").exists()
    assert (target / "golden" / "hardware.csv").exists()
    # the generated production leg must run out of the box...
    proc = subprocess.run([sys.executable, str(target / "run_production_leg.py")],
                          capture_output=True, text=True, timeout=60)
    # ...but it lives outside the repo (tmp), so REPO derivation fails —
    # that is expected; run it with cwd + PYTHONPATH help instead:
    if proc.returncode != 0:
        env = {"PYTHONPATH": f"{REPO / 'kuchnie-core' / 'src'}:{REPO / 'exercises'}"}
        import os
        proc = subprocess.run(
            [sys.executable, str(target / "run_production_leg.py")],
            capture_output=True, text=True, timeout=60,
            env={**os.environ, **env})
    assert proc.returncode == 0, proc.stderr
    assert (target / "generated" / "golden-diff.txt").exists()
    assert "summary:" in (target / "generated" / "golden-diff.txt").read_text()


def test_scaffold_guards(tmp_path):
    from harness.scaffold import create_exercise
    create_exercise("dup", tmp_path)
    with pytest.raises(FileExistsError):
        create_exercise("dup", tmp_path)
    with pytest.raises(ValueError, match="kebab-case"):
        create_exercise("Bad Name", tmp_path)
