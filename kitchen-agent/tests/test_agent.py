"""
tests/test_agent.py
===================
Unit tests for the Gemini agentic loop (src/agent.py).

All Gemini API calls are mocked — no network or API key required.

Covers:
 - Normal single-tool turn: thought_signature + ID preserved  (main path)
 - Empty candidate parts → empty string returned               (lines 163-165)
 - context_files are injected before the user message          (lines 109-118)
 - Images are base64-decoded and appended as Parts             (lines 125-130)
 - Bad base64 image is skipped with a warning                  (lines 131-132)
 - Unknown tool name → error result                            (lines 181-183)
 - Tool function raises → error result                         (lines 178-180)
"""
from unittest.mock import MagicMock, patch

import pytest
from google.genai import types

from src.agent import process_chat_turn


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_tool_response(text: str) -> MagicMock:
    """Build a mock Gemini response that returns *text* as the final answer."""
    part = types.Part(text=text)
    mock = MagicMock()
    mock.candidates = [MagicMock(content=types.Content(role="model", parts=[part]))]
    mock.text = text
    return mock


def _make_function_call_response(name: str, args: dict, call_id: str, signature: str = "") -> MagicMock:
    """Build a mock Gemini response that requests a tool call."""
    part = types.Part(
        function_call=types.FunctionCall(name=name, args=args, id=call_id),
        thought_signature=signature,
    )
    mock = MagicMock()
    mock.candidates = [MagicMock(content=types.Content(role="model", parts=[part]))]
    return mock


# ---------------------------------------------------------------------------
# Main path: thought_signature + function-call ID preserved
# ---------------------------------------------------------------------------

@patch("src.agent._client.models.generate_content")
def test_agent_preserves_thought_signature_and_id(mock_generate: MagicMock) -> None:
    mock_tool_part = types.Part(
        function_call=types.FunctionCall(
            name="read_file", args={"filepath": "dummy.md"}, id="call_123"
        ),
        thought_signature="encrypted_thought_abc123",
    )
    resp1 = MagicMock()
    resp1.candidates = [MagicMock(content=types.Content(role="model", parts=[mock_tool_part]))]

    resp2 = MagicMock()
    resp2.candidates = [
        MagicMock(content=types.Content(role="model", parts=[types.Part(text="The file contains wood.")]))
    ]
    resp2.text = "The file contains wood."

    mock_generate.side_effect = [resp1, resp2]

    with patch("src.agent.FUNCTION_MAP", {"read_file": lambda filepath: {"content": "wood"}}):
        history: list = []
        final_text, tool_logs = process_chat_turn("What is in dummy.md?", history)

    assert final_text == "The file contains wood."
    assert len(tool_logs) == 1
    assert tool_logs[0]["name"] == "read_file"
    assert tool_logs[0]["args"] == {"filepath": "dummy.md"}
    assert tool_logs[0]["result"] == {"content": "wood"}
    assert mock_generate.call_count == 2

    final_history = mock_generate.call_args[1]["contents"]
    assert len(final_history) == 4

    model_turn = final_history[1]
    assert model_turn.role == "model"
    assert model_turn.parts[0].thought_signature == mock_tool_part.thought_signature

    tool_response_turn = final_history[2]
    assert tool_response_turn.role == "user"
    assert tool_response_turn.parts[0].function_response.id == "call_123"


# ---------------------------------------------------------------------------
# Empty candidate parts → safe empty-string return (lines 163-165)
# ---------------------------------------------------------------------------

@patch("src.agent._client.models.generate_content")
def test_agent_returns_empty_string_on_no_parts(mock_generate: MagicMock) -> None:
    mock_resp = MagicMock()
    mock_resp.candidates = [MagicMock(content=types.Content(role="model", parts=[]))]
    mock_generate.return_value = mock_resp

    history: list = []
    final_text, tool_logs = process_chat_turn("Say something unsafe", history)

    assert final_text == ""
    assert tool_logs == []


# ---------------------------------------------------------------------------
# context_files injection (lines 109-118)
# ---------------------------------------------------------------------------

@patch("src.agent._client.models.generate_content")
@patch("src.agent.read_file")
def test_agent_injects_context_files(mock_read_file: MagicMock, mock_generate: MagicMock) -> None:
    """When context_files are provided, their content must be prepended as a Part."""
    mock_read_file.return_value = {"content": "# Materials\n18mm Birch."}
    mock_generate.return_value = _make_tool_response("noted")

    history: list = []
    process_chat_turn(
        "Use the context",
        history,
        context_files=["data/materials.md"],
    )

    mock_read_file.assert_called_once_with("data/materials.md")
    # The user Content must have two Parts: the context block + the message.
    user_content = history[0]
    assert len(user_content.parts) == 2
    assert "[Context files injected by user]" in user_content.parts[0].text
    assert "18mm Birch" in user_content.parts[0].text
    assert user_content.parts[1].text == "Use the context"


@patch("src.agent._client.models.generate_content")
@patch("src.agent.read_file")
def test_agent_skips_unreadable_context_file(mock_read_file: MagicMock, mock_generate: MagicMock) -> None:
    """An unreadable context file must be silently skipped (line 115)."""
    mock_read_file.return_value = {"error": "File not found: missing.md"}
    mock_generate.return_value = _make_tool_response("ok")

    history: list = []
    process_chat_turn("hello", history, context_files=["missing.md"])

    # Only the plain user message Part — no context block injected.
    user_content = history[0]
    assert len(user_content.parts) == 1
    assert user_content.parts[0].text == "hello"


# ---------------------------------------------------------------------------
# Image handling (lines 125-132)
# ---------------------------------------------------------------------------

@patch("src.agent._client.models.generate_content")
def test_agent_decodes_valid_image(mock_generate: MagicMock) -> None:
    """A valid base64 image must be decoded and appended as a binary Part."""
    import base64
    raw = b"\x89PNG\r\n"
    b64 = base64.b64encode(raw).decode()

    mock_generate.return_value = _make_tool_response("saw it")

    history: list = []
    process_chat_turn(
        "Here is an image",
        history,
        images=[{"mime_type": "image/png", "data": b64}],
    )

    user_content = history[0]
    # Parts: [message_text, image_bytes]
    assert len(user_content.parts) == 2


@patch("src.agent._client.models.generate_content")
def test_agent_skips_bad_base64_image(mock_generate: MagicMock) -> None:
    """An invalid base64 string must be skipped without raising (lines 131-132)."""
    mock_generate.return_value = _make_tool_response("ok")

    history: list = []
    final_text, _ = process_chat_turn(
        "bad image",
        history,
        images=[{"mime_type": "image/png", "data": "!!!not_base64!!!"}],
    )

    # Should not raise; only the text part present.
    user_content = history[0]
    assert len(user_content.parts) == 1
    assert final_text == "ok"


# ---------------------------------------------------------------------------
# Unknown tool name (lines 181-183)
# ---------------------------------------------------------------------------

@patch("src.agent._client.models.generate_content")
def test_agent_handles_unknown_tool(mock_generate: MagicMock) -> None:
    """Calling an unknown tool must return an error result, not raise (lines 181-183)."""
    mock_generate.side_effect = [
        _make_function_call_response("nonexistent_tool", {}, "call_x"),
        _make_tool_response("I used a bad tool"),
    ]

    with patch("src.agent.FUNCTION_MAP", {}):  # empty → every tool is unknown
        history: list = []
        final_text, tool_logs = process_chat_turn("do something", history)

    assert len(tool_logs) == 1
    assert "Unknown tool" in tool_logs[0]["result"]["error"]
    assert final_text == "I used a bad tool"


# ---------------------------------------------------------------------------
# Tool function raises exception (lines 178-180)
# ---------------------------------------------------------------------------

@patch("src.agent._client.models.generate_content")
def test_agent_handles_tool_exception(mock_generate: MagicMock) -> None:
    """A crashing tool function must return an error dict, not raise (lines 178-180)."""

    def boom(**kwargs):  # noqa: ANN202
        raise RuntimeError("disk on fire")

    mock_generate.side_effect = [
        _make_function_call_response("read_file", {"filepath": "x.md"}, "call_y"),
        _make_tool_response("recovered"),
    ]

    with patch("src.agent.FUNCTION_MAP", {"read_file": boom}):
        history: list = []
        final_text, tool_logs = process_chat_turn("read x.md", history)

    assert len(tool_logs) == 1
    assert "disk on fire" in tool_logs[0]["result"]["error"]
    assert final_text == "recovered"
