"""
Prompt logging.

Pure function that appends every user prompt to a running Markdown log
file, creating the file and any parent directories as needed.
"""
import os
from datetime import datetime


def log_prompt(prompt: str, log_path: str = "data/prompt_log.md") -> None:
    """
    Appends a timestamped Markdown entry for the given prompt.

    Empty or whitespace-only prompts are ignored.

    Args:
        prompt: The user prompt to log.
        log_path: Destination Markdown file (created if missing).
    """
    if not prompt or not prompt.strip():
        return

    parent = os.path.dirname(log_path)
    if parent:
        os.makedirs(parent, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"## {timestamp}\n\n{prompt.strip()}\n\n"

    with open(log_path, "a", encoding="utf-8") as f:
        f.write(entry)
