#!/usr/bin/env python3
"""One-command exercise run: build -> inspect -> produce, with a manifest.

Usage:
    .venv/bin/python exercises/harness/runner.py <scenario> [options]

Options:
    --skip-blender    reuse the committed .blend/extracted JSON (fast lane
                      for decomposer-only changes)
    --skip-inspect    skip the dev_tools inspection step
    --strict          KUCHNIE_STRICT=1 for the legs + nonzero exit on any
                      failed step (regression/CI mode); default is
                      exploration mode: run everything, record failures

Convention rules 6-7 (one command from clean, pinned toolchain): every run
writes generated/run-manifest.json recording repo SHA + dirty flag, Blender
binary + version, hb5 path + SHA, python version, and per-step exit codes
with durations — so when a rerun disagrees with a committed artifact, the
toolchain delta is on record.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from harness import config  # noqa: E402


def _run(cmd: list[str], env: dict | None = None) -> tuple[int, float]:
    start = time.monotonic()
    proc = subprocess.run(cmd, env=env)
    return proc.returncode, round(time.monotonic() - start, 1)


def _git(args: list[str], cwd: Path) -> str:
    try:
        return subprocess.run(["git", *args], cwd=cwd, capture_output=True,
                              text=True, timeout=10).stdout.strip()
    except Exception:  # noqa: BLE001
        return ""


def _blender_version(blender: Path) -> str:
    try:
        out = subprocess.run([str(blender), "--version"], capture_output=True,
                             text=True, timeout=30).stdout
        return out.splitlines()[0] if out else ""
    except Exception:  # noqa: BLE001
        return ""


def toolchain_manifest(scenario: str) -> dict:
    repo = config.repo_root()
    hb5 = config.hb5_path()
    return {
        "scenario": scenario,
        "started_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "repo_sha": _git(["rev-parse", "HEAD"], repo),
        "repo_dirty": bool(_git(["status", "--porcelain"], repo)),
        "blender_bin": str(config.blender_bin()),
        "blender_version": _blender_version(config.blender_bin()),
        "hb5_path": str(hb5),
        "hb5_sha": _git(["rev-parse", "HEAD"], hb5),
        "python": sys.version.split()[0],
        "strict": config.strict_mode(),
        "steps": [],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("scenario")
    ap.add_argument("--skip-blender", action="store_true")
    ap.add_argument("--skip-inspect", action="store_true")
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()

    repo = config.repo_root()
    scen = repo / "exercises" / args.scenario
    gen = scen / "generated"
    if not scen.is_dir():
        print(f"runner: no such exercise: {scen}")
        return 2
    gen.mkdir(exist_ok=True)

    env = dict(os.environ)
    if args.strict:
        env["KUCHNIE_STRICT"] = "1"

    manifest = toolchain_manifest(args.scenario)

    def step(name: str, cmd: list[str], skipped: bool = False) -> int:
        if skipped:
            manifest["steps"].append({"name": name, "skipped": True})
            print(f"[runner] {name}: skipped")
            return 0
        print(f"[runner] {name}: {' '.join(cmd)}")
        code, secs = _run(cmd, env)
        manifest["steps"].append({"name": name, "exit": code, "seconds": secs})
        return code

    failures = 0

    failures += bool(step(
        "blender-leg",
        [str(config.blender_bin()), "--background", "--enable-autoexec",
         "--python", str(scen / "blender_leg.py")],
        skipped=args.skip_blender,
    ))

    blends = sorted(gen.glob("*.blend"))
    if args.skip_inspect or not blends:
        step("inspect", [], skipped=True)
        if not blends and not args.skip_inspect:
            print("[runner] inspect: no .blend in generated/")
            failures += 1
    else:
        failures += bool(step(
            "inspect",
            [sys.executable,
             str(config.hb5_path() / "dev_tools" / "inspection" / "inspect_cabinet.py"),
             "--open", str(blends[0]), "--all",
             "--out", str(gen / "inspection")],
        ))

    failures += bool(step(
        "production-leg",
        [sys.executable, str(scen / "run_production_leg.py")],
    ))

    manifest["finished_utc"] = datetime.now(
        timezone.utc).isoformat(timespec="seconds")
    manifest["failed_steps"] = failures
    (gen / "run-manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"[runner] manifest: {gen / 'run-manifest.json'}")
    print(f"[runner] {'FAIL' if failures else 'OK'} ({failures} failed step(s))")
    return 1 if (failures and args.strict) else 0


if __name__ == "__main__":
    raise SystemExit(main())
