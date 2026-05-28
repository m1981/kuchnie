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
    Converts a complex Gemini history to JSON and back without losing data,
    including byte-encoded thought_signature.
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

    # Text part
    assert restored[0].role == "user"
    assert restored[0].parts[0].text == "Read the file."

    # Function call + bytes
    assert restored[1].role == "model"
    fc_part = restored[1].parts[0]
    assert fc_part.function_call.name == "read_file"
    assert fc_part.function_call.id == "call_1"
    assert fc_part.thought_signature == b"fake_encrypted_bytes_123"

    # Function response
    assert restored[2].role == "user"
    fr_part = restored[2].parts[0]
    assert fr_part.function_response.name == "read_file"
    assert fr_part.function_response.response == {"content": "wood"}


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
    assert result[0]["data"] == "hello"


# ---------------------------------------------------------------------------
# function_call with no thought_signature (line 79)
# ---------------------------------------------------------------------------

def test_dehydrate_function_call_without_signature() -> None:
    """function_call with no thought_signature serialises signature as None."""
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
    assert item["type"] == "function_call"
    assert item["signature"] is None


def test_hydrate_function_call_without_signature() -> None:
    """Hydrating a function_call with signature=None yields thought_signature=None."""
    raw = json.dumps([
        {
            "role": "model",
            "type": "function_call",
            "name": "get_repo_map",
            "args": {},
            "id": "call_2",
            "signature": None,
        }
    ])
    restored = hydrate_history(raw)
    assert len(restored) == 1
    assert restored[0].parts[0].thought_signature is None


# ---------------------------------------------------------------------------
# Unknown item type is silently skipped (line 141)
# ---------------------------------------------------------------------------

def test_hydrate_skips_unknown_item_type() -> None:
    """An item with an unrecognised 'type' key must be silently skipped."""
    raw = json.dumps([
        {"role": "user", "type": "text", "data": "good"},
        {"role": "user", "type": "alien_format", "payload": "???"},
    ])
    restored = hydrate_history(raw)
    assert len(restored) == 1
    assert restored[0].parts[0].text == "good"


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
    assert result[0]["data"] == "before"
    assert result[1]["data"] == "after"
