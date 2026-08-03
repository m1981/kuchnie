#!/usr/bin/env bash
# Dashboard freshness: STATUS.md must reflect current ledger/bd/gate data
# (volatile Generated-line excluded). Regenerate + commit when stale:
#     .venv/bin/python scripts/dashboard.py
# BLIND-SPOT: it compares STATUS.md against a regeneration, so it catches a stale dashboard but never a WRONG one: if dashboard.py itself renders a bad number, the check confirms the bad number reproduces..
cd "$(git rev-parse --show-toplevel)"
.venv/bin/python scripts/dashboard.py --check
