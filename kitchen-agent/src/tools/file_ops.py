# src/tools/file_ops.py
import os
import re
from pathlib import Path


def read_file(filepath: str) -> dict:
    """Reads a file and returns its content or an error message."""
    try:
        if not os.path.exists(filepath):
            return {"error": f"File not found: {filepath}"}

        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        return {"content": content}
    except Exception as e:
        return {"error": str(e)}

def edit_file(filepath: str, search_text: str, replace_text: str) -> dict:
    """
    Safely edits a file using exact search and replace.
    Prevents the LLM from accidentally deleting the whole file.
    """
    try:
        if not os.path.exists(filepath):
            return {"error": f"File not found: {filepath}"}

        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        if search_text not in content:
            return {
                "error": "Search text not found in file. Please read the file again to ensure you have the exact text."
            }

        # Perform the replacement
        new_content = content.replace(search_text, replace_text)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)

        return {"success": f"Successfully updated {filepath}."}

    except Exception as e:
        return {"error": str(e)}


def create_file(filepath: str, content: str) -> dict:
    """
    Creates a new file with the given content.
    Fails if the file already exists to prevent accidental overwrites.
    """
    try:
        if os.path.exists(filepath):
            return {"error": f"File already exists at {filepath}. Use edit_file instead."}

        # Ensure the directory exists (e.g., if LLM creates 'data/03_Finishes/paint.md')
        directory = os.path.dirname(filepath)
        if directory:
            os.makedirs(directory, exist_ok=True)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        return {"success": f"Successfully created {filepath}."}

    except Exception as e:
        return {"error": str(e)}


def append_to_file(filepath: str, content: str) -> dict:
    """
    Appends content to an existing file.
    Creates the file if it does not exist.
    Used by the UI's 'Highlight -> Add to Docs' feature.
    """
    try:
        directory = os.path.dirname(filepath)
        if directory:
            os.makedirs(directory, exist_ok=True)

        with open(filepath, "a", encoding="utf-8") as f:
            # Ensure a newline separator before appended content
            f.write("\n" + content)

        return {"success": f"Successfully appended to {filepath}."}

    except Exception as e:
        return {"error": str(e)}


def search_knowledge_base(query: str, base_dir: str = "data") -> dict:
    """
    Searches all markdown files for lines matching a regex pattern.
    Supports multi-keyword OR search (e.g., 'hinge|blum|runner').
    Simulates grep -E across the entire knowledge base.

    Returns up to 200 matching lines with file path and line number context.
    """
    try:
        base_path = Path(base_dir)
        if not base_path.exists():
            return {"error": f"Directory not found: {base_dir}"}

        try:
            pattern = re.compile(query, re.IGNORECASE)
        except re.error as e:
            return {"error": f"Invalid regex pattern: {e}"}

        matches: list[str] = []
        MAX_MATCHES = 200

        for filepath in sorted(base_path.rglob("*.md")):
            try:
                lines = filepath.read_text(encoding="utf-8").splitlines()
            except Exception:
                continue

            for line_num, line in enumerate(lines, 1):
                if pattern.search(line):
                    matches.append(f"{filepath.as_posix()}:{line_num}: {line}")
                    if len(matches) >= MAX_MATCHES:
                        matches.append(f"... (truncated at {MAX_MATCHES} results)")
                        return {"content": "\n".join(matches)}

        if not matches:
            return {"content": f"No matches found for pattern: '{query}'"}

        return {"content": "\n".join(matches)}

    except Exception as e:
        return {"error": str(e)}