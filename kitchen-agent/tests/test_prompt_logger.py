"""
TDD suite for prompt logging.

Covers the pure append-to-file function that maintains a running
Markdown log of every user prompt.
"""
import os

from src.prompt_logger import log_prompt


def test_log_prompt_creates_file_if_missing(tmp_path):
    """Logging a prompt creates the log file when it does not exist."""

    # 1. Arrange
    log_path = str(tmp_path / "prompt_log.md")

    # 2. Act
    log_prompt("First prompt", log_path=log_path)

    # 3. Assert
    assert os.path.exists(log_path)
    with open(log_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "First prompt" in content


def test_log_prompt_creates_nested_dirs(tmp_path):
    """Logging creates intermediate directories as needed."""

    # 1. Arrange
    log_path = str(tmp_path / "nested" / "dir" / "prompt_log.md")

    # 2. Act
    log_prompt("Hello", log_path=log_path)

    # 3. Assert
    assert os.path.exists(log_path)


def test_log_prompt_appends_without_overwriting(tmp_path):
    """A second prompt is appended, preserving the first."""

    # 1. Arrange
    log_path = str(tmp_path / "prompt_log.md")

    # 2. Act
    log_prompt("PROMPT_ONE", log_path=log_path)
    log_prompt("PROMPT_TWO", log_path=log_path)

    # 3. Assert
    with open(log_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "PROMPT_ONE" in content
    assert "PROMPT_TWO" in content
    assert content.index("PROMPT_ONE") < content.index("PROMPT_TWO")


def test_log_prompt_includes_timestamp_header(tmp_path):
    """Each entry includes a Markdown timestamp header."""

    # 1. Arrange
    log_path = str(tmp_path / "prompt_log.md")

    # 2. Act
    log_prompt("Timed prompt", log_path=log_path)

    # 3. Assert
    with open(log_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert content.lstrip().startswith("## ")


def test_log_prompt_ignores_empty_prompt(tmp_path):
    """Empty or whitespace-only prompts are not logged."""

    # 1. Arrange
    log_path = str(tmp_path / "prompt_log.md")

    # 2. Act
    log_prompt("   ", log_path=log_path)

    # 3. Assert
    assert not os.path.exists(log_path)
