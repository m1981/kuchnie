"""
src/tools/repo_map.py
=====================
Lightweight "repo map" tool: scans the knowledge-base directory for Markdown
files and extracts their headings so the LLM can decide which file to read
without loading the full content of every file.
"""

from pathlib import Path


def get_repo_map(base_dir: str = "data") -> dict:
    """
    Scans *base_dir* recursively for ``.md`` files and extracts their Markdown
    headings (lines starting with ``#``).

    Returns:
        {"content": str}  — formatted map ready for the model.
        {"error":   str}  — when *base_dir* does not exist.
    """
    base_path = Path(base_dir)
    if not base_path.exists():
        return {"error": f"Directory not found: {base_dir}"}

    output: list[str] = []

    for filepath in sorted(base_path.rglob("*.md")):
        # Full POSIX path so the LLM can pass it directly to read_file.
        output.append(f"\n=== {filepath.as_posix()} ===")
        try:
            for line_num, line in enumerate(
                filepath.read_text(encoding="utf-8").splitlines(), start=1
            ):
                if line.startswith("#"):
                    output.append(f"{line_num}: {line.strip()}")
        except OSError:
            output.append("  (unreadable)")

    if not output:
        return {"content": "No markdown files found."}

    return {"content": "\n".join(output)}
