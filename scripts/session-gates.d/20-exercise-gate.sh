#!/usr/bin/env bash
# Flagship-exercise regression gate (see scripts/exercise-gate.sh).
cd "$(git rev-parse --show-toplevel)"
bash scripts/exercise-gate.sh
