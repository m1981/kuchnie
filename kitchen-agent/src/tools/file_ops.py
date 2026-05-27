# src/tools/file_ops.py
import os


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