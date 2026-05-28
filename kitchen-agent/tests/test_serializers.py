# tests/test_serializers.py
import pytest
import json
from google.genai import types
from src.serializers import dehydrate_history, hydrate_history


def test_serialization_cycle():
    """
    Tests that we can convert a complex Gemini history to JSON and back
    without losing data, especially the byte-encoded thought_signature.
    """
    # --- Arrange ---
    # Create a mock history with Text, Function Call, and Function Response
    original_history = [
        types.Content(role="user", parts=[types.Part(text="Read the file.")]),
        types.Content(role="model", parts=[
            types.Part(
                function_call=types.FunctionCall(name="read_file", args={"filepath": "test.md"}, id="call_1"),
                thought_signature=b"fake_encrypted_bytes_123"  # Raw bytes!
            )
        ]),
        types.Content(role="user", parts=[
            types.Part(
                function_response=types.FunctionResponse(name="read_file", response={"content": "wood"}, id="call_1")
            )
        ])
    ]

    # --- Act ---
    # 1. Dehydrate to JSON string
    json_string = dehydrate_history(original_history)

    # 2. Hydrate back to Gemini objects
    restored_history = hydrate_history(json_string)

    # --- Assert ---
    assert len(restored_history) == 3

    # Check Text
    assert restored_history[0].role == "user"
    assert restored_history[0].parts[0].text == "Read the file."

    # Check Function Call & Bytes
    assert restored_history[1].role == "model"
    fc_part = restored_history[1].parts[0]
    assert fc_part.function_call.name == "read_file"
    assert fc_part.function_call.id == "call_1"
    assert fc_part.thought_signature == b"fake_encrypted_bytes_123"  # Bytes survived!

    # Check Function Response
    assert restored_history[2].role == "user"
    fr_part = restored_history[2].parts[0]
    assert fr_part.function_response.name == "read_file"
    assert fr_part.function_response.response == {"content": "wood"}