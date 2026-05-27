# tests/test_file_ops.py
import pytest
from src.tools.file_ops import edit_file


def test_edit_file_success(tmp_path):
    # Arrange
    test_file = tmp_path / "hinges.md"
    test_file.write_text("We use standard hinges.", encoding="utf-8")

    # Act
    result = edit_file(
        filepath=str(test_file),
        search_text="standard hinges",
        replace_text="Blum soft-close hinges"
    )

    # Assert
    assert "error" not in result
    assert "Successfully updated" in result["success"]
    assert test_file.read_text(encoding="utf-8") == "We use Blum soft-close hinges."


def test_edit_file_search_text_not_found(tmp_path):
    # Arrange
    test_file = tmp_path / "hinges.md"
    test_file.write_text("We use standard hinges.", encoding="utf-8")

    # Act
    result = edit_file(
        filepath=str(test_file),
        search_text="cheap hinges",  # This text doesn't exist in the file
        replace_text="Blum hinges"
    )

    # Assert
    assert "error" in result
    assert "Search text not found" in result["error"]
    # Ensure file was NOT modified
    assert test_file.read_text(encoding="utf-8") == "We use standard hinges."