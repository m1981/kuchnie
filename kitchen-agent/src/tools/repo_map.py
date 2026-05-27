# src/tools/repo_map.py
import os
from pathlib import Path


def get_repo_map(base_dir: str = "data") -> dict:
    """
    Scans the directory for .md files and extracts their headers.
    Acts as a lightweight 'Repo Map' for the LLM.
    """
    try:
        base_path = Path(base_dir)
        if not base_path.exists():
            return {"error": f"Directory not found: {base_dir}"}

        output = []

        # Find all .md files recursively
        for filepath in base_path.rglob("*.md"):

            # FIX: Use the full path (e.g., data/test.md) so the LLM knows exactly where it is.
            # .as_posix() ensures we use forward slashes (/) even if you are on Windows.
            output.append(f"\n=== {filepath.as_posix()} ===")

            with open(filepath, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    if line.startswith("#"):
                        output.append(f"{line_num}: {line.strip()}")

        if not output:
            return {"content": "No markdown files found."}

        return {"content": "\n".join(output)}

    except Exception as e:
        return {"error": str(e)}