"""GAP logging — every hand re-entry or workaround is a first-class result.

The per-run GAP count is the pipeline-integration metric (convention §10).
"""
from __future__ import annotations

from pathlib import Path


class GapLog:
    """Collects GAP lines; print immediately, persist at the end."""

    def __init__(self, prefix: str = "GAP") -> None:
        self.prefix = prefix
        self.items: list[str] = []

    def gap(self, msg: str) -> None:
        print(f"{self.prefix}: {msg}")
        self.items.append(msg)

    def log(self, msg: str) -> None:
        """Non-gap progress line (printed, kept for the leg log)."""
        print(f"[{self.prefix.lower()}] {msg}")
        self.items.append(f"[info] {msg}")

    def write(self, path: str | Path) -> None:
        Path(path).write_text("\n".join(self.items) + "\n", encoding="utf-8")

    @property
    def gap_count(self) -> int:
        return sum(1 for i in self.items if not i.startswith("[info]"))
