"""Pinned tests for scripts/test-health.sh (wk-0d7a80d2, R4 satellite).

Spec: docs/specs/conformance-join.md — FAIL only on a citation that does
not exist in the ledger; existing citations pass regardless of warnings.
Run: .venv/bin/python -m pytest scripts/tests -q
"""
from __future__ import annotations

import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def run_test_health(roots: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", "scripts/test-health.sh"],
        cwd=REPO,
        env={"PATH": "/usr/bin:/bin:/usr/local/bin", "TEST_HEALTH_ROOTS": roots},
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_fabricated_citation_fails(tmp_path: Path) -> None:
    """A test citing an id absent from the ledger must make the gate exit 1
    (wk-0d7a80d2 acceptance: fabricated citation is a broken trace link).

    The fake id is assembled at runtime so this file itself never carries
    a fabricated citation — the default sweep covers scripts/tests too.
    """
    fake_id = "tr-" + "dead" + "beef"
    (tmp_path / "test_fake.py").write_text(
        f"# pins {fake_id} which no ledger record carries\n"
    )
    proc = run_test_health(str(tmp_path))
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert fake_id in proc.stdout
    assert "missing from the ledger" in proc.stdout


def test_existing_citation_passes(tmp_path: Path) -> None:
    """Citing a real ledger id (wk-0d7a80d2, this satellite's own work item)
    exits 0 — warnings (inverse check, diverged pins) never fail the gate."""
    (tmp_path / "test_real.py").write_text("# pins wk-0d7a80d2\n")
    proc = run_test_health(str(tmp_path))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "0 failure(s)" in proc.stdout.splitlines()[-1]


def test_repo_suites_have_no_fabricated_citations() -> None:
    """The default sweep at HEAD reports 0 failures (wk-0d7a80d2 acceptance:
    runs clean at HEAD)."""
    proc = subprocess.run(
        ["bash", "scripts/test-health.sh"],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
