"""
src/tools/file_ops.py
=====================
File-system tool implementations executed by the agent.

All functions return a plain dict so they can be sent directly back to the
Gemini function-calling API.  Two keys are used:
  {"content": str}  — success with a string payload
  {"success": str}  — success with a status message
  {"error":   str}  — failure; the agent will see the reason
"""

import re
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read_path(filepath: str) -> tuple[Path, dict | None]:
    """
    Returns (resolved_path, None) on success, or (path, error_dict) when the
    file does not exist.  Callers return the error_dict immediately.
    """
    p = Path(filepath)
    if not p.exists():
        return p, {"error": f"File not found: {filepath}"}
    return p, None


# ---------------------------------------------------------------------------
# Public tool functions
# ---------------------------------------------------------------------------

def read_file(filepath: str) -> dict:
    """Reads a file and returns its content or an error message."""
    p, err = _read_path(filepath)
    if err:
        return err
    try:
        return {"content": p.read_text(encoding="utf-8")}
    except OSError as exc:
        return {"error": str(exc)}


def edit_file(filepath: str, search_text: str, replace_text: str) -> dict:
    """
    Safely edits a file using exact search-and-replace.

    Returns an error when *search_text* is not found so the agent can
    re-read the file before trying again — preventing accidental data loss.
    """
    p, err = _read_path(filepath)
    if err:
        return err
    try:
        content = p.read_text(encoding="utf-8")
    except OSError as exc:
        return {"error": str(exc)}

    if search_text not in content:
        return {
            "error": (
                "Search text not found in file. "
                "Please read the file again to ensure you have the exact text."
            )
        }

    p.write_text(content.replace(search_text, replace_text), encoding="utf-8")
    return {"success": f"Successfully updated {filepath}."}


def create_file(filepath: str, content: str) -> dict:
    """
    Creates a new file with the given content.

    Refuses to overwrite an existing file — the agent must use edit_file
    for updates.
    """
    p = Path(filepath)
    if p.exists():
        return {"error": f"File already exists at {filepath}. Use edit_file instead."}
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return {"success": f"Successfully created {filepath}."}
    except OSError as exc:
        return {"error": str(exc)}


def append_to_file(filepath: str, content: str) -> dict:
    """
    Appends *content* to an existing file (or creates it when absent).

    Used by the UI's "Highlight → Add to Docs" feature and exposed as a
    REST endpoint; NOT exposed to the LLM as a tool.
    """
    p = Path(filepath)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as f:
            # Ensure a blank line separates existing content from the snippet.
            f.write("\n" + content)
        return {"success": f"Successfully appended to {filepath}."}
    except OSError as exc:
        return {"error": str(exc)}


def search_knowledge_base(query: str, base_dir: str = "data") -> dict:
    """
    Searches all Markdown files under *base_dir* for lines matching a
    case-insensitive regex pattern.

    Supports OR logic via the pipe character, e.g. ``'hinge|blum|runner'``.
    Returns up to 200 matching lines with their file path and line number.
    """
    MAX_MATCHES = 200

    base_path = Path(base_dir)
    if not base_path.exists():
        return {"error": f"Directory not found: {base_dir}"}

    try:
        pattern = re.compile(query, re.IGNORECASE)
    except re.error as exc:
        return {"error": f"Invalid regex pattern: {exc}"}

    matches: list[str] = []

    for filepath in sorted(base_path.rglob("*.md")):
        try:
            lines = filepath.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue

        for line_num, line in enumerate(lines, start=1):
            if pattern.search(line):
                matches.append(f"{filepath.as_posix()}:{line_num}: {line}")
                if len(matches) >= MAX_MATCHES:
                    matches.append(f"... (truncated at {MAX_MATCHES} results)")
                    return {"content": "\n".join(matches)}

    if not matches:
        return {"content": f"No matches found for pattern: '{query}'"}

    return {"content": "\n".join(matches)}
