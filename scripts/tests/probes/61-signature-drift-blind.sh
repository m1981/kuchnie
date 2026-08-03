#!/usr/bin/env bash
# Blind-spot probe for 61-signature-drift.sh.
#
# CONTRACT: exit 0 while the declared blind spot is still REAL (the gate
# passes the case it says it cannot catch); exit 1 once the blind spot has
# been closed, which forces the declaration in the gate to be rewritten.
# This is the self-maintaining property from Livshits et al. (2015):
# declared unsoundness, pinned by a test.
#
# Declared: the gate watches module-level defs/classes/methods, so a changed
# function BODY with an unchanged signature is invisible.
# Probed by: a token that exists only inside a function body must be absent
# from the signature summary. If the summary ever starts carrying bodies,
# this fails and the declaration is no longer true.
set -u
cd "$(git rev-parse --show-toplevel)"
SRC=kitchen-erp/kitchen_erp/core/database.py
TOKEN='metadata.create_all'

grep -q "$TOKEN" "$SRC" || {
  echo "probe-61: anchor gone -- '$TOKEN' no longer in $SRC; re-anchor the probe"; exit 1; }

if python3 scripts/signature-summary.py | grep -q "$TOKEN"; then
  echo "probe-61: the signature summary now carries function bodies -- the declared blind spot is CLOSED; update the BLIND-SPOT line in 61-signature-drift.sh"
  exit 1
fi
echo "probe-61: blind spot intact -- bodies remain invisible to the signature surface"
exit 0
