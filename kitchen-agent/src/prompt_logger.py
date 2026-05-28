"""
src/prompt_logger.py
====================
Pure function that appends every user prompt to a running Markdown log file.

No DB or HTTP concerns — just file I/O.  The default log path comes from
``settings.prompt_log_path`` so it is configurable without touching code.
"""

from datetime import datetime
from pathlib import Path

from src.config import settings


def log_prompt(prompt: str, log_path: Path | str | None = None) -> None:
    """
    Appends a timestamped Markdown entry for *prompt* to the log file.

    Empty or whitespace-only prompts are silently ignored.

    Args:
        prompt:   The user prompt to record.
        log_path: Override for the log file path (defaults to
                  ``settings.prompt_log_path``).  Useful in tests.
    """
    if not prompt or not prompt.strip():
        return

    target = Path(log_path) if log_path is not None else settings.prompt_log_path
    target.parent.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"## {timestamp}\n\n{prompt.strip()}\n\n"

    with target.open("a", encoding="utf-8") as f:
        f.write(entry)
