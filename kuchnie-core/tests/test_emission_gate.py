"""UC-2 ext 5a — emission gated on the buildability verdict (wk-cb6a17c8)
and structured row findings underneath it (wk-acc8e094).

A FAILED verdict must block rozrys/edging/BOM emission: the doorway
raises BuildabilityError and writes nothing. The design-legality rules
emit Finding objects (gate id, severity, ref) that buildability buckets
directly — validate_rows is only a display layer over them.
"""

import inspect
from pathlib import Path

import pytest

from kuchnie_core import buildability as buildability_module
from kuchnie_core.buildability import (
    ADVISORY,
    BLOCKING,
    BuildabilityError,
    evaluate_buildability,
    require_buildable,
)
from kuchnie_core.export.cutlist_csv import export_cutlist_csv
from kuchnie_core.export.edging_csv import export_edging_csv
from kuchnie_core.kitchen import kitchen_bom, row_findings, validate_rows
from kuchnie_core.loader import load_kitchen

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def _buildable_kitchen():
    return load_kitchen(FIXTURES / "kitchen_01.yaml")


def _unbuildable_kitchen():
    """Fixture kitchen with the wall shrunk under its cabinets — FIT fires."""
    kitchen = _buildable_kitchen()
    kitchen.rows[0].wall_width_mm = 100
    return kitchen


# ── wk-cb6a17c8: FAILED verdict blocks emission ─────────────────

def test_failed_verdict_blocks_cutlist(tmp_path):
    out = tmp_path / "rozrys.csv"
    with pytest.raises(BuildabilityError):
        export_cutlist_csv(_unbuildable_kitchen(), out)
    assert not out.exists()  # nothing written, not a partial file


def test_failed_verdict_blocks_edging(tmp_path):
    out = tmp_path / "edging.csv"
    with pytest.raises(BuildabilityError):
        export_edging_csv(_unbuildable_kitchen(), out)
    assert not out.exists()


def test_failed_verdict_blocks_bom():
    with pytest.raises(BuildabilityError):
        kitchen_bom(_unbuildable_kitchen())


def test_buildable_kitchen_still_emits(tmp_path):
    out = export_cutlist_csv(_buildable_kitchen(), tmp_path / "rozrys.csv")
    assert out.exists() and out.stat().st_size > 0


def test_error_carries_verdict_and_names_gates():
    try:
        require_buildable(_unbuildable_kitchen())
    except BuildabilityError as err:
        assert err.verdict.buildable is False
        assert "[FIT]" in str(err)
        assert "blocking" in str(err)
    else:
        pytest.fail("require_buildable did not raise")


def test_precomputed_verdict_is_trusted_not_reevaluated(monkeypatch, tmp_path):
    """Emitters accept a precomputed verdict and must not re-run gates."""
    kitchen = _buildable_kitchen()
    verdict = evaluate_buildability(kitchen)

    def _boom(*a, **kw):  # pragma: no cover - guard
        raise AssertionError("gates re-evaluated despite precomputed verdict")

    monkeypatch.setattr(buildability_module, "evaluate_buildability", _boom)
    out = export_cutlist_csv(kitchen, tmp_path / "rozrys.csv", verdict=verdict)
    assert out.exists()


# ── wk-acc8e094: structured findings, strings as display ────────

def test_row_findings_are_structured():
    findings = row_findings(_unbuildable_kitchen())
    fit = [f for f in findings if f.gate_id == "FIT"]
    assert fit and all(f.severity == BLOCKING for f in fit)
    assert all(f.ref for f in fit)  # offending row named, not parsed


def test_wstd_is_advisory_with_cabinet_ref():
    kitchen = _buildable_kitchen()
    kitchen.rows[0].cabinets[0].width_mm = 517  # non-standard width
    wstd = [f for f in row_findings(kitchen) if f.gate_id == "WSTD"]
    assert wstd and wstd[0].severity == ADVISORY
    assert wstd[0].ref == kitchen.rows[0].cabinets[0].id


def test_validate_rows_is_the_display_layer():
    kitchen = _unbuildable_kitchen()
    assert validate_rows(kitchen) == [f.message for f in row_findings(kitchen)]


def test_buildability_buckets_without_string_parsing():
    """The classifier consumes gate ids; the string-marker parsing
    (regexes, 'advisory:'/'G1 —' matching) is gone (premise tr-88fb2941)."""
    src = inspect.getsource(buildability_module._row_gate_buckets)
    assert "row_findings" in src
    for marker in ("advisory:", "G1 —", "re.", "startswith"):
        assert marker not in src, f"string parsing crept back: {marker}"
