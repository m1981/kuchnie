"""
tests/test_serializers.py
=========================
Unit tests for dehydrate_history / hydrate_history round-trip.

Covers:
 - Normal full cycle (text, function_call with signature, function_response)
 - Content with no parts is silently skipped   (line 36-37)
 - function_call with no thought_signature     (line 79)
 - Unknown item type is silently skipped       (line 141)
"""
import json

import pytest
from google.genai import types

from src.serializers import dehydrate_history, hydrate_history


# ---------------------------------------------------------------------------
# Full round-trip (existing)
# ---------------------------------------------------------------------------

def test_serialization_cycle() -> None:
    """
    Converts a complex Gemini history to JSON and back without losing data.
    Now returns common format dicts instead of types.Content objects.
    """
    original_history = [
        types.Content(role="user", parts=[types.Part(text="Read the file.")]),
        types.Content(
            role="model",
            parts=[
                types.Part(
                    function_call=types.FunctionCall(
                        name="read_file", args={"filepath": "test.md"}, id="call_1"
                    ),
                    thought_signature=b"fake_encrypted_bytes_123",
                )
            ],
        ),
        types.Content(
            role="user",
            parts=[
                types.Part(
                    function_response=types.FunctionResponse(
                        name="read_file", response={"content": "wood"}, id="call_1"
                    )
                )
            ],
        ),
    ]

    json_string = dehydrate_history(original_history)
    restored = hydrate_history(json_string)

    assert len(restored) == 3

    # Text part — common format
    assert restored[0]["role"] == "user"
    assert restored[0]["content"] == "Read the file."

    # Function call — common format with tool_calls
    assert restored[1]["role"] == "assistant"
    assert restored[1]["tool_calls"][0]["name"] == "read_file"
    assert restored[1]["tool_calls"][0]["id"] == "call_1"

    # Function response — common format
    assert restored[2]["role"] == "tool"
    assert restored[2]["tool_call_id"] == "call_1"
    # Response content is JSON-encoded string
    response = json.loads(restored[2]["content"])
    assert response == {"content": "wood"}


# ---------------------------------------------------------------------------
# Content with no parts is silently skipped (lines 36-37)
# ---------------------------------------------------------------------------

def test_dehydrate_skips_empty_parts() -> None:
    """A Content object with an empty parts list must be silently skipped."""
    history = [
        types.Content(role="user", parts=[types.Part(text="hello")]),
        types.Content(role="model", parts=[]),   # ← empty — must be skipped
    ]
    result = json.loads(dehydrate_history(history))
    assert len(result) == 1
    assert result[0]["content"] == "hello"


# ---------------------------------------------------------------------------
# function_call with no thought_signature (line 79)
# ---------------------------------------------------------------------------

def test_dehydrate_function_call_without_signature() -> None:
    """function_call with no thought_signature serialises correctly."""
    history = [
        types.Content(
            role="model",
            parts=[
                types.Part(
                    function_call=types.FunctionCall(
                        name="get_repo_map", args={}, id="call_2"
                    )
                    # no thought_signature
                )
            ],
        )
    ]
    data = json.loads(dehydrate_history(history))
    assert len(data) == 1
    item = data[0]
    # Common format
    assert item["role"] == "assistant"
    assert item["tool_calls"][0]["name"] == "get_repo_map"
    assert item["tool_calls"][0]["id"] == "call_2"


def test_hydrate_function_call_without_signature() -> None:
    """Hydrating a function_call in common format works correctly."""
    raw = json.dumps([
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {"id": "call_2", "name": "get_repo_map", "arguments": {}}
            ],
        }
    ])
    restored = hydrate_history(raw)
    assert len(restored) == 1
    # Common format doesn't preserve thought_signature
    assert restored[0]["role"] == "assistant"
    assert restored[0]["tool_calls"][0]["name"] == "get_repo_map"


# ---------------------------------------------------------------------------
# Unknown item type is silently skipped (line 141)
# ---------------------------------------------------------------------------

def test_hydrate_skips_unknown_item_type() -> None:
    """An item with an unrecognised 'type' key but no 'data' is passed through."""
    # First item is legacy Gemini format (will be converted)
    # Second item has 'type' but no 'data' — not legacy Gemini, passed through
    raw = json.dumps([
        {"role": "user", "type": "text", "data": "good"},
        {"role": "user", "type": "alien_format", "payload": "???"},
    ])
    restored = hydrate_history(raw)
    # Both items are returned — first converted, second passed through
    assert len(restored) == 2
    assert restored[0]["content"] == "good"
    assert restored[1]["type"] == "alien_format"


# ---------------------------------------------------------------------------
# Edge cases for hydrate_history input
# ---------------------------------------------------------------------------

def test_hydrate_empty_string_returns_empty_list() -> None:
    assert hydrate_history("") == []


def test_hydrate_empty_json_array_returns_empty_list() -> None:
    assert hydrate_history("[]") == []


# ---------------------------------------------------------------------------
# Dehydrate: unrecognised Part type is skipped with a warning (line 79)
# ---------------------------------------------------------------------------

def test_dehydrate_skips_unrecognised_part_type() -> None:
    """
    A Part that is neither text, function_call, nor function_response must be
    silently skipped (the else-branch warning on line 79).

    We use Part.from_bytes() to create a binary-blob Part which has none of
    the three recognised attributes set.
    """
    binary_part = types.Part.from_bytes(data=b"\x89PNG", mime_type="image/png")
    history = [
        types.Content(role="user", parts=[types.Part(text="before")]),
        types.Content(role="user", parts=[binary_part]),   # unrecognised
        types.Content(role="user", parts=[types.Part(text="after")]),
    ]
    result = json.loads(dehydrate_history(history))
    # Only the two text parts should be serialised; the binary part is dropped.
    assert len(result) == 2
    assert result[0]["content"] == "before"
    assert result[1]["content"] == "after"
