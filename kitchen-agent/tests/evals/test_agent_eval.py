# tests/evals/test_agent_eval.py
"""
Live integration evaluation — requires a real GEMINI_API_KEY and hits the
actual Gemini API.  Run with:

    uv run pytest tests/evals/ -m integration -v

These tests are excluded from the normal CI test run.
"""
import pytest
from pathlib import Path
from agent import process_chat_turn


@pytest.mark.integration
def test_eval_agent_can_update_material(tmp_path: Path) -> None:
    """
    EVAL: Verifies that the real Gemini model is capable of reading a file,
    locating the target text, and editing it successfully.

    Note: This test costs API credits.
    """
    # 1. Arrange: create a real temporary file for the agent to modify.
    test_file = tmp_path / "materials.md"
    test_file.write_text("We use 18mm MDF for cabinets.", encoding="utf-8")

    history: list = []
    prompt = (
        f"Please update the file at {test_file}. "
        "Change the material from MDF to Birch Plywood."
    )

    # 2. Act: call the real agent (costs API credits).
    final_text, tools_used = process_chat_turn(prompt, history)

    # 3. Assert the file-system outcome.
    updated_content = test_file.read_text(encoding="utf-8")

    assert "Birch Plywood" in updated_content, (
        f"Expected 'Birch Plywood' in file content, got:\n{updated_content}"
    )
    assert "MDF" not in updated_content, (
        f"'MDF' should have been removed, but file content is:\n{updated_content}"
    )

    # tools_used is list[dict] — check by name, not by membership in string list.
    tool_names = [t["name"] for t in tools_used]
    assert "edit_file" in tool_names, (
        f"Expected 'edit_file' to be used, but tools used were: {tool_names}"
    )
