"""Every gate declares what it does NOT catch, and the declaration is pinned.

Doctrine reference: agentic-verification-doctrine-2026-08-03.md L2 —
"a declared-unsoundness block in every gate, pinned by a test. Each gate
states what it does not catch; a test constructs that case and asserts the
gate passes it. If someone later fixes the blind spot, the test fails and
forces the declaration to be updated." (Livshits et al., 2015, on soundiness:
the value is in stating the unsoundness, not pretending to have none.)

Two separate obligations, and they are deliberately not the same strength:

  * DECLARATION is mandatory and enforced here for every gate. A gate with no
    stated blind spot is claiming completeness it does not have.
  * PROBE is optional but, where present, must actually run and must exit 0.
    A probe exits 0 while the blind spot is REAL, so it fails exactly when
    someone closes the blind spot without updating the prose — which is the
    self-maintaining property the doctrine is after.

The probed/unprobed split is printed rather than hidden: it is the honest
measure of how much of this layer is real, and per ADR-047 it is the metric a
later decision to require probes everywhere would rest on.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
GATE_DIR = ROOT / "scripts" / "session-gates.d"
# Gates that live outside session-gates.d because their question is shaped by
# a boundary other than the session: pre-push-checks.sh IS the push boundary,
# and impact-check.sh asks "what depends on the commits ahead of upstream?",
# which has no meaning at session close. They are named here so the
# declaration obligation reaches them exactly as it reaches the directory.
EXTRA_GATES = [ROOT / "scripts" / "pre-push-checks.sh",
               ROOT / "scripts" / "impact-check.sh"]

DECL = "# BLIND-SPOT:"
PROBE = "# BLIND-SPOT-PROBE:"


def gates() -> list[Path]:
    found = sorted(GATE_DIR.glob("*.sh")) + EXTRA_GATES
    # A sensor that cannot see its own corpus must scream, never pass empty
    # (the F1 rule). An empty glob here would make every assertion below
    # vacuously true.
    assert len(found) >= 5, f"only {len(found)} gate(s) found — the sweep is dark"
    return found


@pytest.mark.parametrize("gate", gates(), ids=lambda p: p.name)
def test_gate_declares_its_blind_spot(gate: Path) -> None:
    text = gate.read_text(encoding="utf-8")
    assert DECL in text, (
        f"{gate.name} states no blind spot. Every gate is a fitness function "
        "with an unsound edge; declaring it is the price of being trusted "
        "(doctrine L2). Add a '# BLIND-SPOT: <what this cannot catch>' line."
    )


def _probe_of(gate: Path) -> Path | None:
    for line in gate.read_text(encoding="utf-8").splitlines():
        if line.startswith(PROBE):
            return ROOT / line.split(":", 1)[1].strip()
    return None


PROBED = [(g, p) for g in gates() if (p := _probe_of(g)) is not None]


@pytest.mark.parametrize("gate,probe", PROBED, ids=lambda x: getattr(x, "name", str(x)))
def test_declared_blind_spot_still_holds(gate: Path, probe: Path) -> None:
    assert probe.exists(), (
        f"{gate.name} names a probe that does not exist: {probe}. A dangling "
        "reference is worse than none — it reads as pinned when it is not."
    )
    run = subprocess.run(["bash", str(probe)], capture_output=True, text=True,
                         cwd=ROOT, timeout=180)
    assert run.returncode == 0, (
        f"{probe.name} failed — the blind spot {gate.name} declares is no "
        f"longer real, so the declaration is now a lie. Rewrite the "
        f"BLIND-SPOT line (and this is good news: a gate got stronger).\n"
        f"{run.stdout}\n{run.stderr}"
    )


def test_probe_coverage_is_visible() -> None:
    """Not a threshold — a report. Silent partial coverage is the failure."""
    total, probed = len(gates()), len(PROBED)
    print(f"\nblind-spot coverage: {probed}/{total} gates carry an executable "
          f"probe; {total - probed} are declared-only.")
    assert probed >= 1, (
        "no gate carries an executable probe — the layer is prose only, "
        "which is the state doctrine L2 exists to leave."
    )
