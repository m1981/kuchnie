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
