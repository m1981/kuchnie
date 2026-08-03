#!/usr/bin/env bash
# Blind-spot probe for scripts/impact-check.sh. Contract: 0 = blind spot real.
#
# Declared: the blast radius is DECLARED coupling, not computed coupling. A
# changed path that no active claim watches reports ZERO dependents, and that
# is indistinguishable from "nothing depends on it". Silence means UNWATCHED,
# not SAFE.
#
# Probed by: take a tracked file the backward trace calls dark (watched by no
# active claim) and assert `truth impact` reports nothing for it. If ledger
# coverage ever reaches every tracked file, the dark set empties and this
# probe fails -- which is good news, and forces the declaration to be rewritten.
#
# POSITIVE CONTROL, because a checker that reports nothing for EVERY path
# would otherwise satisfy the assertion above trivially (QB-013: run a control
# you know matches). A tracked file the same trace says IS watched must
# produce at least one row from the same verb, in the same run.
set -u
cd "$(git rev-parse --show-toplevel)" || exit 1
python3 - <<'PY'
import json
import subprocess
import sys


def run(args):
    return subprocess.run(args, capture_output=True, text=True, timeout=180)


inv = run(["scripts/truth", "impact", "--inverse", "--json"])
if inv.returncode not in (0, 4):          # 0 = no dark files, 4 = dark files exist
    print("probe-impact-check: SENSOR FAILED -- 'truth impact --inverse' exited "
          f"{inv.returncode}; nothing was probed\n{inv.stderr.strip()[-400:]}")
    sys.exit(1)
rep = json.loads(inv.stdout or "{}")
dark = set(rep.get("dark", []))
considered = rep.get("considered", 0)
if considered == 0:
    print("probe-impact-check: SENSOR FAILED -- the backward trace considered 0 "
          "tracked files; the probe examined nothing")
    sys.exit(1)

ls = run(["git", "ls-files"])
tracked = [p for p in ls.stdout.splitlines() if p and not p.startswith('"')]
if not tracked:
    print("probe-impact-check: SENSOR FAILED -- git ls-files returned no plain "
          "paths; the probe examined nothing")
    sys.exit(1)

dark_plain = [p for p in tracked if p in dark]
watched_plain = [p for p in tracked if p not in dark]

# --- positive control: the verb must still be able to SPEAK ---------------
if not watched_plain:
    print("probe-impact-check: no tracked file is watched by any active claim -- "
          "the ledger has no coverage at all, so this probe cannot tell a real "
          "blind spot from a dead sensor")
    sys.exit(1)
control = watched_plain[0]
out = run(["scripts/truth", "impact", "--json", "--", control])
if out.returncode not in (0, 3):
    print(f"probe-impact-check: SENSOR FAILED -- 'truth impact' exited "
          f"{out.returncode} on {control}\n{out.stderr.strip()[-400:]}")
    sys.exit(1)
rows = json.loads(out.stdout or "[]")
if not rows:
    print(f"probe-impact-check: POSITIVE CONTROL FAILED -- {control} is watched "
          "by an active claim per the backward trace, yet the forward verb "
          "reports nothing. The two matchers disagree; the silence below would "
          "have proved nothing.")
    sys.exit(1)

# --- the blind spot itself ------------------------------------------------
if not dark_plain:
    print(f"probe-impact-check: every one of the {considered} tracked file(s) is "
          "now watched by an active claim -- the declared blind spot (silence "
          "means UNWATCHED, not SAFE) is CLOSED. Rewrite the BLIND-SPOT block "
          "in scripts/impact-check.sh.")
    sys.exit(1)
victim = dark_plain[0]
out = run(["scripts/truth", "impact", "--json", "--", victim])
if out.returncode not in (0, 3):
    print(f"probe-impact-check: SENSOR FAILED -- 'truth impact' exited "
          f"{out.returncode} on {victim}\n{out.stderr.strip()[-400:]}")
    sys.exit(1)
rows = json.loads(out.stdout or "[]")
if rows:
    print(f"probe-impact-check: {victim} is called dark by the backward trace "
          f"yet the forward verb returns {len(rows)} row(s). The two disagree "
          "-- one of the two matchers changed; fix that before trusting either.")
    sys.exit(1)

print(f"probe-impact-check: blind spot intact -- {len(dark_plain)} of "
      f"{len(tracked)} plain tracked path(s) are watched by no active claim, and "
      f"pushing {victim} would report a blast radius of ZERO. Control: "
      f"{control} still reports a non-empty radius, so the verb is alive.")
PY
