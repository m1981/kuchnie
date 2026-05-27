# tests/test_agent.py
import pytest
from unittest.mock import patch, MagicMock
from google.genai import types
from src.agent import process_chat_turn


@patch("src.agent.client.models.generate_content")
def test_agent_preserves_thought_signature_and_id(mock_generate_content):
    """
    Validates that the agent correctly preserves the thought_signature from the
    model's function call and passes the correct function call ID in the response.
    """
    # --- Arrange ---
    # 1. Mock the first response: Model decides to call 'read_file' and includes a signature
    mock_tool_call_part = types.Part(
        function_call=types.FunctionCall(
            name="read_file",
            args={"filepath": "dummy.md"},
            id="call_123"
        ),
        thought_signature="encrypted_thought_abc123"
    )

    mock_response_1 = MagicMock()
    mock_response_1.candidates = [
        MagicMock(content=types.Content(role="model", parts=[mock_tool_call_part]))
    ]

    # 2. Mock the second response: Model provides the final text answer
    mock_text_part = types.Part(text="The file contains wood.")
    mock_response_2 = MagicMock()
    mock_response_2.candidates = [
        MagicMock(content=types.Content(role="model", parts=[mock_text_part]))
    ]
    mock_response_2.text = "The file contains wood."

    # Set the mock to return response 1 on the first call, and response 2 on the second call
    mock_generate_content.side_effect = [mock_response_1, mock_response_2]

    # Mock the actual file reading tool so we don't hit the disk during tests
    with patch("src.agent.FUNCTION_MAP", {"read_file": lambda filepath: {"content": "wood"}}):
        history = []

        # --- Act ---
        final_text, tool_used = process_chat_turn("What is in dummy.md?", history)

    # --- Assert ---
    assert tool_used == "read_file"
    assert final_text == "The file contains wood."

    # Verify the mock was called exactly twice
    assert mock_generate_content.call_count == 2

    # Inspect the final state of the history list
    final_history = mock_generate_content.call_args[1]["contents"]

    # The history should have 4 items by the end of the function:
    # [User Msg, Model Tool Call, User Tool Response, Model Final Answer]
    assert len(final_history) == 4

    # 1. Validate the Model's Tool Call part preserved the signature (Index 1)
    model_turn = final_history[1]
    assert model_turn.role == "model"

    # FIX: Compare it directly to the mock object's signature,
    # letting the SDK handle the string-to-bytes conversion internally.
    assert model_turn.parts[0].thought_signature == mock_tool_call_part.thought_signature, \
        "FAIL: The thought_signature was stripped or altered!"

    # 2. Validate the User's Tool Response part includes the correct ID (Index 2)
    tool_response_turn = final_history[2]
    assert tool_response_turn.role == "user"
    assert tool_response_turn.parts[0].function_response.id == "call_123", \
        "FAIL: The function_response ID does not match the function_call ID!"