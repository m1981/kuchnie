# tests/evals/test_agent_eval.py
import pytest
from pathlib import Path
from agent import process_chat_turn

@pytest.mark.integration
def test_eval_agent_can_update_material(tmp_path, monkeypatch):
    """
    EVAL: Tests if the REAL Gemini model is smart enough to read a file,
    find the text, and edit it successfully.
    """
    # 1. Arrange: Set up a real file
    test_file = tmp_path / "materials.md"
    test_file.write_text("We use 18mm MDF for cabinets.", encoding="utf-8")

    # Monkeypatch the agent's working directory or pass the tmp_path
    # so the agent operates on our safe test file.

    history = []
    prompt = f"Please update {test_file}. Change the material from MDF to Birch Plywood."

    # 2. Act: Call the REAL agent (This costs API credits!)
    final_text, tools_used = process_chat_turn(prompt, history)

    # 3. Assert the OUTCOME
    # We don't care what the agent said in final_text.
    # We only care if it successfully manipulated the file system.
    updated_content = test_file.read_text(encoding="utf-8")

    assert "Birch Plywood" in updated_content
    assert "MDF" not in updated_content
    assert "edit_file" in tools_used