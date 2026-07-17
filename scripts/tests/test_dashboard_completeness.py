"""Pinned tests for the dashboard Completeness (R7) view (wk-9d77de94).

Covers the pure parser/classifier pair in scripts/dashboard.py:
acceptance_items() and classify_acceptance() — proto-R1/R7 per
docs/specs/conformance-join.md (lexical match, no NLP).
Run: .venv/bin/python -m pytest scripts/tests -q
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

_spec = importlib.util.spec_from_file_location(
    "dashboard", REPO / "scripts" / "dashboard.py")
dashboard = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dashboard)

SAMPLE = '''# Spec: sample

## Acceptance

Pre-written `done --claim` texts:

- "UC-4 ordering emits a board order CSV with producer SKUs resolved
  from the catalog" (step 3)
- "the widget frobnicates reliably" (later)
'''


def test_acceptance_items_parses_bullets_and_ucs() -> None:
    items = dashboard.acceptance_items(SAMPLE)
    assert len(items) == 2
    assert items[0]["ucs"] == ["UC-4"]
    assert items[0]["text"].startswith("UC-4 ordering emits a board order")
    assert "resolved from the catalog" in items[0]["text"]  # joined lines
    assert items[1]["ucs"] == []


def test_classify_three_states() -> None:
    items = dashboard.acceptance_items(SAMPLE)
    claims = [
        {"id": "c-live", "status": "live",
         "text": "UC-4 ordering emits a board order CSV with producer "
                 "SKUs resolved from the catalog service"},
        {"id": "c-other", "status": "stale",
         "text": "completely unrelated fact about drawer runners"},
    ]
    out = dashboard.classify_acceptance(items, claims)
    assert out[0]["state"] == "LIVE" and out[0]["claim"] == "c-live"
    assert out[1]["state"] == "PRE-WRITTEN" and out[1]["claim"] == ""
    # same match, claim no longer live -> FILED (the gauge can go DOWN)
    claims[0]["status"] = "stale"
    out2 = dashboard.classify_acceptance(items, claims)
    assert out2[0]["state"] == "FILED"


def test_classifier_is_deterministic_on_ties() -> None:
    items = [{"text": "alpha beta gamma delta", "ucs": []}]
    twin = {"text": "alpha beta gamma delta"}
    claims = [{"id": "c-bbb", "status": "live", **twin},
              {"id": "c-aaa", "status": "live", **twin}]
    out = dashboard.classify_acceptance(items, claims)
    # live-first then lexicographic id: c-aaa wins regardless of order
    assert out[0]["claim"] == "c-aaa"
    out_rev = dashboard.classify_acceptance(items, list(reversed(claims)))
    assert out_rev[0]["claim"] == "c-aaa"


def test_real_use_cases_spec_parses() -> None:
    text = (REPO / "docs/specs/use-cases.md").read_text(encoding="utf-8")
    items = dashboard.acceptance_items(text)
    assert len(items) >= 3  # the three migration-step items exist today
    assert any("roadmap-map.csv" in it["text"] for it in items)


def test_live_successor_beats_dead_original(  # pins wk-eb7164f1
) -> None:
    """A retracted/diverged original with near-perfect overlap must lose
    to a live successor that still clears the threshold."""
    items = [{"text": "alpha beta gamma delta epsilon zeta", "ucs": []}]
    claims = [
        # dead original: verbatim overlap (6/6)
        {"id": "c-dead", "status": "retracted",
         "text": "alpha beta gamma delta epsilon zeta"},
        # live successor: 4/6 coverage, above the 0.5 threshold
        {"id": "c-live", "status": "live",
         "text": "alpha beta gamma delta reworded differently"},
    ]
    out = dashboard.classify_acceptance(items, claims)
    assert out[0]["state"] == "LIVE" and out[0]["claim"] == "c-live"
    # and with NO live candidate above threshold, the dead one still shows
    out2 = dashboard.classify_acceptance(items, [claims[0]])
    assert out2[0]["state"] == "FILED" and out2[0]["claim"] == "c-dead"


def _fake_tr(hexpart: str) -> str:
    """Synthetic ledger-id fixtures, assembled at runtime so the R4
    citation sweep (scripts/test-health.sh) never reads them as
    fabricated citations — they are deliberately not in the ledger."""
    return "tr-" + hexpart


def test_reworded_successor_found_via_lineage() -> None:  # pins wk-dcf4ab04
    """A successor reworded below the lexical threshold must still turn
    the item LIVE when explicit lineage links it to the dead best match."""
    dead, new = _fake_tr("0000dead"), _fake_tr("00000new")
    items = [{"text": "alpha beta gamma delta epsilon zeta", "ucs": []}]
    claims = [
        {"id": dead, "status": "retracted",
         "text": "alpha beta gamma delta epsilon zeta"},
        # reworded successor: 0/6 lexical overlap, cites the dead id
        {"id": new, "status": "live",
         "text": f"entirely different wording (supersedes {dead})"},
    ]
    successors = dashboard.successor_map(claims, [])
    assert successors == {dead: new}
    out = dashboard.classify_acceptance(items, claims, successors=successors)
    assert out[0]["state"] == "LIVE"
    assert out[0]["claim"] == new
    assert out[0]["status"] == f"live ← {dead}"
    # without the lineage map the old (under-reporting) behavior remains
    out_bare = dashboard.classify_acceptance(items, claims)
    assert out_bare[0]["state"] == "FILED"


def test_successor_map_follows_verdict_basis_and_chains() -> None:
    """Lineage source (b): the diverge/retract verdict basis names the
    successor; chains dead->dead->live resolve transitively; cycles and
    dead ends drop out."""
    a1, a2, a3 = (_fake_tr(h) for h in ("aaaa0001", "aaaa0002", "aaaa0003"))
    b1, b2 = _fake_tr("bbbb0001"), _fake_tr("bbbb0002")
    claims = [
        {"id": a1, "status": "retracted", "text": "first filing"},
        {"id": a2, "status": "retracted", "text": "second filing"},
        {"id": a3, "status": "live", "text": "third, no citations"},
        {"id": b1, "status": "retracted", "text": "cycle a"},
        {"id": b2, "status": "retracted", "text": f"cycle b names {b1}"},
    ]
    verdicts = [
        {"claim": a1, "verdict": "diverge",
         "basis": f"resolved by progress; successor {a2} carries it"},
        {"claim": a2, "verdict": "retracted",
         "basis": f"superseded; successor {a3}"},
        {"claim": b1, "verdict": "diverge", "basis": f"see {b2}"},
    ]
    successors = dashboard.successor_map(claims, verdicts)
    # the chain resolves both dead aaaa claims to the live third filing
    assert successors[a1] == a3
    assert successors[a2] == a3
    # the bbbb cycle never reaches a live claim -> absent, not looping
    assert b1 not in successors
