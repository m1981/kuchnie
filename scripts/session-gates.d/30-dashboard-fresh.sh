#!/usr/bin/env bash
# Dashboard freshness: STATUS.md must reflect current ledger/bd/gate data
# (volatile Generated-line excluded). Regenerate + commit when stale:
#     .venv/bin/python scripts/dashboard.py
cd "$(git rev-parse --show-toplevel)"
.venv/bin/python scripts/dashboard.py --check
