"""GAP logging — every hand re-entry or workaround is a first-class result.

The per-run GAP count is the pipeline-integration metric (convention §10).

Three severities, deliberately distinct:
  log(msg)   — progress, kept in the leg log, not a gap
  gap(msg)   — a FINDING (hand re-entry, workaround): always recorded,
               never raises — findings are the point of an exercise
  fail(msg)  — a FAILURE (something broke that the run tolerated):
               recorded in exploration mode, raised in strict mode so a
               regression/CI run stops loudly instead of producing
               artifacts from a half-built scene
Strict mode: GapLog(strict=True), or KUCHNIE_STRICT=1 (see config.py).
"""
from __future__ import annotations

import os
from pathlib import Path


class HarnessFailure(RuntimeError):
    """A tolerable-in-exploration failure escalated by strict mode."""


class GapLog:
    """Collects GAP/FAIL lines; print immediately, persist at the end."""

    def __init__(self, prefix: str = "GAP", strict: bool | None = None) -> None:
        self.prefix = prefix
        self.items: list[str] = []
        if strict is None:
            strict = os.environ.get("KUCHNIE_STRICT") == "1"
        self.strict = strict

    def log(self, msg: str) -> None:
        """Non-gap progress line (printed, kept for the leg log)."""
        print(f"[{self.prefix.lower()}] {msg}")
        self.items.append(f"[info] {msg}")

    def gap(self, msg: str) -> None:
        print(f"{self.prefix}: {msg}")
        self.items.append(msg)

    def fail(self, msg: str) -> None:
        """A failure the run can survive — unless strict mode says otherwise."""
        if self.strict:
            raise HarnessFailure(msg)
        print(f"{self.prefix}-FAIL: {msg}")
        self.items.append(f"[fail] {msg}")

    def write(self, path: str | Path) -> None:
        Path(path).write_text("\n".join(self.items) + "\n", encoding="utf-8")

    @property
    def gap_count(self) -> int:
        return sum(1 for i in self.items
                   if not i.startswith("[info]") and not i.startswith("[fail]"))

    @property
    def fail_count(self) -> int:
        return sum(1 for i in self.items if i.startswith("[fail]"))
