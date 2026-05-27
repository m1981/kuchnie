# tests/test_repo_map.py
import pytest
from pathlib import Path
from src.tools.repo_map import get_repo_map


def test_get_repo_map_returns_full_posix_paths(tmp_path):
    """
    Tests that the repo map extracts headers AND returns full POSIX paths.
    This prevents regressions where relative paths break the read_file tool.
    """
    # --- Arrange ---
    dir_1 = tmp_path / "01_Materials"
    dir_1.mkdir()
    file_1 = dir_1 / "wood.md"
    file_1.write_text("# Wood Types\nSome text.", encoding="utf-8")

    # --- Act ---
    result = get_repo_map(base_dir=str(tmp_path))

    # --- Assert ---
    assert "error" not in result
    content = result["content"]

    # CRITICAL REGRESSION CHECK:
    # Ensure the full path (including the base tmp_path) is in the output,
    # and that it uses forward slashes (.as_posix())
    expected_full_path = file_1.as_posix()

    assert expected_full_path in content, \
        f"Regression caught! Expected full path '{expected_full_path}' not found in repo map."

    # Check that headers are still extracted
    assert "# Wood Types" in content