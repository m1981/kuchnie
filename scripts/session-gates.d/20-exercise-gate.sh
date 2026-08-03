#!/usr/bin/env bash
# Flagship-exercise regression gate (see scripts/exercise-gate.sh).
# BLIND-SPOT: byte-identity against a committed baseline proves the pipeline is unchanged, not that it is CORRECT.
#   A wrong cut list that has always been wrong passes forever; the gate protects the golden, not the geometry.
cd "$(git rev-parse --show-toplevel)"
bash scripts/exercise-gate.sh
