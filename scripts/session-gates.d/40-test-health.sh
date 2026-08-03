#!/usr/bin/env bash
# Test-citation health (R4): every tr-/wk- id cited by a test must exist in
# the ledger; retracted/diverged citations and pin-less recent closes WARN.
# Detail run: bash scripts/test-health.sh (spec: docs/specs/conformance-join.md)
# BLIND-SPOT: it verifies that ids cited by tests exist and are believed.
#   It cannot see a test that cites the RIGHT id while asserting something the claim does not say -- citation health is not semantic agreement.
cd "$(git rev-parse --show-toplevel)"
bash scripts/test-health.sh
