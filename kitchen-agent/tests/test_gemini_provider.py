"""
tests/test_gemini_provider.py
==============================
Unit tests for GeminiProvider — the refactored Gemini agentic loop.

These tests mirror the existing test_agent.py tests to ensure full
parity after the refactor.  All Gemini API calls are mocked.

Covers:
  - Normal single-tool turn: thought_signature + ID preserved
  - Empty candidate parts → empty string returned
  - context_files are injected before the user message
  - Images are base64-decoded and appended as Parts
  - Bad base64 image is skipped with a warning
  - Unknown tool name → error result, no raise
  - Tool function raises → error result, no raise
  - Multi-tool turn: each tool call dispatched sequentially
"""
import base64
from unittest.mock import MagicMock, patch

import pytest
from google.genai import types

from src.providers.gemini import GeminiProvider


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def _make_text_response(text: str) -> MagicMock:
    part = types.Part(text=text)
    mock = MagicMock()
    mock.candidates = [MagicMock(content=types.Content(role="model", parts=[part]))]
    mock.text = text
    return mock


def _make_tool_call_response(name: str, args: dict, call_id: str, signature: str = "") -> MagicMock:
    part = types.Part(
        function_call=types.FunctionCall(name=name, args=args, id=call_id),
        thought_signature=signature,
    )
    mock = MagicMock()
    mock.candidates = [MagicMock(content=types.Content(role="model", parts=[part]))]
    return mock


@pytest.fixture
def provider() -> GeminiProvider:
    """Return a GeminiProvider with a mocked Gemini client."""
    with patch("src.providers.gemini.genai.Client") as mock_client_cls:
        p = GeminiProvider()
        p._client = mock_client_cls.return_value
        return p


# ---------------------------------------------------------------------------
# Normal single-tool turn: thought_signature + ID preserved
# ---------------------------------------------------------------------------

def test_preserves_thought_signature_and_id(provider: GeminiProvider) -> None:
    mock_tool_part = types.Part(
        function_call=types.FunctionCall(
            name="read_file", args={"filepath": "dummy.md"}, id="call_123"
        ),
        thought_signature="encrypted_thought_abc123",
    )
    resp1 = MagicMock()
    resp1.candidates = [MagicMock(content=types.Content(role="model", parts=[mock_tool_part]))]

    resp2 = _make_text_response("The file contains wood.")

    provider._client.models.generate_content.side_effect = [resp1, resp2]

    with patch("src.providers.gemini.FUNCTION_MAP", {"read_file": lambda filepath: {"content": "wood"}}):
        history: list = []
        final_text, tool_logs = provider.process_chat_turn("What is in dummy.md?", history)

    assert final_text == "The file contains wood."
    assert len(tool_logs) == 1
    assert tool_logs[0]["name"] == "read_file"
    assert tool_logs[0]["args"] == {"filepath": "dummy.md"}
    assert tool_logs[0]["result"] == {"content": "wood"}
    assert provider._client.models.generate_content.call_count == 2

    # The model turn in history must carry the original thought_signature.
    model_turn = history[1]
    assert model_turn.role == "model"
    assert model_turn.parts[0].thought_signature == mock_tool_part.thought_signature

    # The tool response must use the correct call ID.
    tool_response_turn = history[2]
    assert tool_response_turn.role == "user"
    assert tool_response_turn.parts[0].function_response.id == "call_123"


# ---------------------------------------------------------------------------
# Empty candidate parts → safe empty-string return
# ---------------------------------------------------------------------------

def test_returns_empty_on_no_parts(provider: GeminiProvider) -> None:
    mock_resp = MagicMock()
    mock_resp.candidates = [MagicMock(content=types.Content(role="model", parts=[]))]
    provider._client.models.generate_content.return_value = mock_resp

    history: list = []
    final_text, tool_logs = provider.process_chat_turn("Say something unsafe", history)

    assert final_text == ""
    assert tool_logs == []


# ---------------------------------------------------------------------------
# context_files injection
# ---------------------------------------------------------------------------

def test_injects_context_files(provider: GeminiProvider) -> None:
    provider._client.models.generate_content.return_value = _make_text_response("noted")

    with patch("src.providers.gemini.read_file", return_value={"content": "# Materials\n18mm Birch."}):
        history: list = []
        provider.process_chat_turn("Use the context", history, context_files=["data/materials.md"])

    user_content = history[0]
    assert len(user_content.parts) == 2
    assert "[Context files injected by user]" in user_content.parts[0].text
    assert "18mm Birch" in user_content.parts[0].text
    assert user_content.parts[1].text == "Use the context"


def test_skips_unreadable_context_file(provider: GeminiProvider) -> None:
    provider._client.models.generate_content.return_value = _make_text_response("ok")

    with patch("src.providers.gemini.read_file", return_value={"error": "File not found"}):
        history: list = []
        provider.process_chat_turn("hello", history, context_files=["missing.md"])

    user_content = history[0]
    assert len(user_content.parts) == 1
    assert user_content.parts[0].text == "hello"


# ---------------------------------------------------------------------------
# Image handling
# ---------------------------------------------------------------------------

def test_decodes_valid_image(provider: GeminiProvider) -> None:
    raw = b"\x89PNG\r\n"
    b64 = base64.b64encode(raw).decode()
    provider._client.models.generate_content.return_value = _make_text_response("saw it")

    history: list = []
    provider.process_chat_turn(
        "Here is an image", history,
        images=[{"mime_type": "image/png", "data": b64}],
    )

    user_content = history[0]
    assert len(user_content.parts) == 2  # text + image


def test_skips_bad_base64_image(provider: GeminiProvider) -> None:
    provider._client.models.generate_content.return_value = _make_text_response("ok")

    history: list = []
    final_text, _ = provider.process_chat_turn(
        "bad image", history,
        images=[{"mime_type": "image/png", "data": "!!!not_base64!!!"}],
    )

    user_content = history[0]
    assert len(user_content.parts) == 1
    assert final_text == "ok"


# ---------------------------------------------------------------------------
# Unknown tool name
# ---------------------------------------------------------------------------

def test_handles_unknown_tool(provider: GeminiProvider) -> None:
    provider._client.models.generate_content.side_effect = [
        _make_tool_call_response("nonexistent_tool", {}, "call_x"),
        _make_text_response("I used a bad tool"),
    ]

    with patch("src.providers.gemini.FUNCTION_MAP", {}):
        history: list = []
        final_text, tool_logs = provider.process_chat_turn("do something", history)

    assert len(tool_logs) == 1
    assert "Unknown tool" in tool_logs[0]["result"]["error"]
    assert final_text == "I used a bad tool"


# ---------------------------------------------------------------------------
# Tool function raises exception
# ---------------------------------------------------------------------------

def test_handles_tool_exception(provider: GeminiProvider) -> None:
    def boom(**kwargs):
        raise RuntimeError("disk on fire")

    provider._client.models.generate_content.side_effect = [
        _make_tool_call_response("read_file", {"filepath": "x.md"}, "call_y"),
        _make_text_response("recovered"),
    ]

    with patch("src.providers.gemini.FUNCTION_MAP", {"read_file": boom}):
        history: list = []
        final_text, tool_logs = provider.process_chat_turn("read x.md", history)

    assert "disk on fire" in tool_logs[0]["result"]["error"]
    assert final_text == "recovered"


# ---------------------------------------------------------------------------
# tools_enabled=False — direct LLM call, no agentic loop
# ---------------------------------------------------------------------------

def test_no_tools_skips_agentic_loop(provider: GeminiProvider) -> None:
    """When use_tools=False the provider makes exactly one API call and returns."""
    provider._client.models.generate_content.return_value = _make_text_response("direct answer")

    history: list = []
    final_text, tool_logs = provider.process_chat_turn(
        "what is the standard overhang?", history, use_tools=False
    )

    assert final_text == "direct answer"
    assert tool_logs == []
    assert provider._client.models.generate_content.call_count == 1


def test_no_tools_sends_no_tools_to_api(provider: GeminiProvider) -> None:
    """When use_tools=False the GenerateContentConfig must contain no tools."""
    provider._client.models.generate_content.return_value = _make_text_response("ok")

    history: list = []
    provider.process_chat_turn("hello", history, use_tools=False)

    call_kwargs = provider._client.models.generate_content.call_args[1]
    config = call_kwargs.get("config")
    # tools must be absent or an empty list
    tools = getattr(config, "tools", None)
    assert not tools


def test_no_tools_history_has_user_and_model_turn(provider: GeminiProvider) -> None:
    """Even without tools the history must have the user turn + model reply."""
    provider._client.models.generate_content.return_value = _make_text_response("reply")

    history: list = []
    provider.process_chat_turn("ping", history, use_tools=False)

    # Exactly two items: user turn + model final turn
    assert len(history) == 2
    assert history[0].role == "user"
    assert history[1].role == "model"


def test_tools_enabled_true_still_uses_agentic_loop(provider: GeminiProvider) -> None:
    """Explicit use_tools=True must behave identically to the default (agentic loop)."""
    resp_tool = _make_tool_call_response("read_file", {"filepath": "x.md"}, "c99")
    resp_text = _make_text_response("done")
    provider._client.models.generate_content.side_effect = [resp_tool, resp_text]

    with patch("src.providers.gemini.FUNCTION_MAP",
               {"read_file": lambda filepath: {"content": "stuff"}}):
        history: list = []
        final_text, tool_logs = provider.process_chat_turn(
            "read x.md", history, use_tools=True
        )

    assert final_text == "done"
    assert len(tool_logs) == 1
    assert provider._client.models.generate_content.call_count == 2


# ---------------------------------------------------------------------------
# Multi-tool turn: two sequential tool calls in one conversation
# ---------------------------------------------------------------------------

def test_multi_tool_turn(provider: GeminiProvider) -> None:
    """Two tool calls followed by a final text response."""
    resp_tool1 = _make_tool_call_response("read_file", {"filepath": "a.md"}, "c1")
    resp_tool2 = _make_tool_call_response("read_file", {"filepath": "b.md"}, "c2")
    resp_final = _make_text_response("Done reading both.")

    provider._client.models.generate_content.side_effect = [resp_tool1, resp_tool2, resp_final]

    with patch("src.providers.gemini.FUNCTION_MAP", {
        "read_file": lambda filepath: {"content": f"contents of {filepath}"}
    }):
        history: list = []
        final_text, tool_logs = provider.process_chat_turn("read a.md and b.md", history)

    assert final_text == "Done reading both."
    assert len(tool_logs) == 2
    assert tool_logs[0]["args"]["filepath"] == "a.md"
    assert tool_logs[1]["args"]["filepath"] == "b.md"
