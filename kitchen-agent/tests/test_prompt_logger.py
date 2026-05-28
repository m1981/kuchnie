"""
tests/test_prompt_logger.py
============================
TDD suite for prompt logging.

Covers the pure append-to-file function that maintains a running
Markdown log of every user prompt.
"""
from pathlib import Path

import pytest

from src.prompt_logger import log_prompt


def test_log_prompt_creates_file_if_missing(tmp_path: Path) -> None:
    """Logging a prompt creates the log file when it does not exist."""
    log_path = tmp_path / "prompt_log.md"

    log_prompt("First prompt", log_path=log_path)

    assert log_path.exists()
    assert "First prompt" in log_path.read_text(encoding="utf-8")


def test_log_prompt_creates_nested_dirs(tmp_path: Path) -> None:
    """Logging creates intermediate directories as needed."""
    log_path = tmp_path / "nested" / "dir" / "prompt_log.md"

    log_prompt("Hello", log_path=log_path)

    assert log_path.exists()


def test_log_prompt_appends_without_overwriting(tmp_path: Path) -> None:
    """A second prompt is appended, preserving the first."""
    log_path = tmp_path / "prompt_log.md"

    log_prompt("PROMPT_ONE", log_path=log_path)
    log_prompt("PROMPT_TWO", log_path=log_path)

    content = log_path.read_text(encoding="utf-8")
    assert "PROMPT_ONE" in content
    assert "PROMPT_TWO" in content
    assert content.index("PROMPT_ONE") < content.index("PROMPT_TWO")


def test_log_prompt_includes_timestamp_header(tmp_path: Path) -> None:
    """Each entry includes a Markdown timestamp heading."""
    log_path = tmp_path / "prompt_log.md"

    log_prompt("Timed prompt", log_path=log_path)

    content = log_path.read_text(encoding="utf-8")
    assert content.lstrip().startswith("## ")


def test_log_prompt_ignores_empty_prompt(tmp_path: Path) -> None:
    """Empty or whitespace-only prompts are not logged."""
    log_path = tmp_path / "prompt_log.md"

    log_prompt("   ", log_path=log_path)

    assert not log_path.exists()
