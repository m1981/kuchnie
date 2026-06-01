"""
tests/test_anthropic_provider.py
=================================
Unit tests for AnthropicProvider — the Anthropic Claude agentic loop.

All Anthropic API calls are mocked — no network or API key required.

The Anthropic messages API differs from Gemini in several important ways:

  1. History is a list of plain dicts (``{"role": ..., "content": [...]}``),
     NOT SDK objects.  The provider manages this internally.
  2. Tool calls are returned as ``ToolUseBlock`` objects inside ``content``.
  3. Tool results are fed back as ``{"role": "user", "content": [{"type":
     "tool_result", "tool_use_id": ..., "content": ...}]}``.
  4. There is no ``thought_signature`` concept — we do not test for it.
  5. ``stop_reason == "tool_use"`` signals another iteration; ``"end_turn"``
     (or ``"stop_sequence"``) signals the final answer.

History format (internal Anthropic representation)
---------------------------------------------------
The provider stores history as a list of ``MessageParam``-shaped dicts so
they can be passed verbatim to ``client.messages.create``.  After the turn
completes the history list (passed in by chat_service) will contain:

  [user_turn, assistant_tool_call_turn, user_tool_result_turn, ..., assistant_final_turn]

Covers:
  - Simple text response (no tool calls)
  - Single tool call → result → final text
  - Unknown tool name → error result injected, loop continues
  - Tool function raises → error result injected, loop continues
  - context_files injected as first user text block
  - Images encoded as Anthropic image blocks
  - Bad base64 image skipped gracefully
  - System instruction forwarded to the API call
  - Multi-tool turn (two sequential tool calls)
  - Empty / blank final text handled without raise
"""
import base64
import json
from unittest.mock import MagicMock, patch, call

import pytest
import anthropic

from src.providers.anthropic_provider import AnthropicProvider


# ---------------------------------------------------------------------------
# Helpers to build mock Anthropic API responses
# ---------------------------------------------------------------------------

def _text_block(text: str) -> MagicMock:
    block = MagicMock(spec=anthropic.types.TextBlock)
    block.type = "text"
    block.text = text
    return block


def _tool_use_block(name: str, tool_input: dict, tool_id: str) -> MagicMock:
    block = MagicMock(spec=anthropic.types.ToolUseBlock)
    block.type = "tool_use"
    block.name = name
    block.input = tool_input
    block.id = tool_id
    return block


def _make_response(content_blocks: list, stop_reason: str = "end_turn") -> MagicMock:
    msg = MagicMock()
    msg.content = content_blocks
    msg.stop_reason = stop_reason
    # .text convenience — Anthropic SDK flattens TextBlocks
    text_parts = [b.text for b in content_blocks if getattr(b, "type", None) == "text"]
    msg.text = " ".join(text_parts) if text_parts else ""
    return msg


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def provider() -> AnthropicProvider:
    """Return an AnthropicProvider with a mocked Anthropic client."""
    with patch("src.providers.anthropic_provider.anthropic.Anthropic") as mock_cls:
        p = AnthropicProvider()
        p._client = mock_cls.return_value
        return p


# ---------------------------------------------------------------------------
# Simple text response — no tool calls
# ---------------------------------------------------------------------------

def test_simple_text_response(provider: AnthropicProvider) -> None:
    """When the model returns text directly, no tools are called."""
    resp = _make_response([_text_block("Hello from Claude!")], stop_reason="end_turn")
    provider._client.messages.create.return_value = resp

    history: list = []
    final_text, tool_logs = provider.process_chat_turn("Hello", history)

    assert final_text == "Hello from Claude!"
    assert tool_logs == []
    assert provider._client.messages.create.call_count == 1


def test_simple_text_appended_to_history(provider: AnthropicProvider) -> None:
    """After a text-only turn, history must have user + assistant entries."""
    resp = _make_response([_text_block("Hi!")], stop_reason="end_turn")
    provider._client.messages.create.return_value = resp

    history: list = []
    provider.process_chat_turn("Hi", history)

    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[1]["role"] == "assistant"


# ---------------------------------------------------------------------------
# Single tool call → result → final text
# ---------------------------------------------------------------------------

def test_single_tool_call_dispatched(provider: AnthropicProvider) -> None:
    """A tool_use block triggers dispatch, result is fed back, loop continues."""
    tool_resp = _make_response(
        [_tool_use_block("read_file", {"filepath": "data/test.md"}, "tid_1")],
        stop_reason="tool_use",
    )
    final_resp = _make_response([_text_block("File read successfully.")], stop_reason="end_turn")
    provider._client.messages.create.side_effect = [tool_resp, final_resp]

    fake_fn = MagicMock(return_value={"content": "# Test\nsome content"})

    with patch("src.providers.anthropic_provider.FUNCTION_MAP", {"read_file": fake_fn}):
        history: list = []
        final_text, tool_logs = provider.process_chat_turn("Read test.md", history)

    assert final_text == "File read successfully."
    assert len(tool_logs) == 1
    assert tool_logs[0]["name"] == "read_file"
    assert tool_logs[0]["args"] == {"filepath": "data/test.md"}
    assert tool_logs[0]["result"] == {"content": "# Test\nsome content"}
    fake_fn.assert_called_once_with(filepath="data/test.md")


def test_single_tool_call_history_structure(provider: AnthropicProvider) -> None:
    """History after a single tool call must be: user, assistant(tool_use), user(tool_result), assistant(text)."""
    tool_resp = _make_response(
        [_tool_use_block("read_file", {"filepath": "x.md"}, "tid_2")],
        stop_reason="tool_use",
    )
    final_resp = _make_response([_text_block("Done.")], stop_reason="end_turn")
    provider._client.messages.create.side_effect = [tool_resp, final_resp]

    with patch("src.providers.anthropic_provider.FUNCTION_MAP", {
        "read_file": lambda filepath: {"content": "x"}
    }):
        history: list = []
        provider.process_chat_turn("go", history)

    # Roles in order: user, assistant, user (tool result), assistant
    roles = [h["role"] for h in history]
    assert roles == ["user", "assistant", "user", "assistant"]

    # The second user turn must carry a tool_result block.
    tool_result_turn = history[2]
    assert tool_result_turn["role"] == "user"
    content = tool_result_turn["content"]
    assert isinstance(content, list)
    assert content[0]["type"] == "tool_result"
    assert content[0]["tool_use_id"] == "tid_2"


# ---------------------------------------------------------------------------
# Unknown tool name → error result, loop continues
# ---------------------------------------------------------------------------

def test_unknown_tool_returns_error_result(provider: AnthropicProvider) -> None:
    """An unknown tool must produce an error result — not raise."""
    tool_resp = _make_response(
        [_tool_use_block("nonexistent_tool", {}, "tid_3")],
        stop_reason="tool_use",
    )
    final_resp = _make_response([_text_block("Recovered.")], stop_reason="end_turn")
    provider._client.messages.create.side_effect = [tool_resp, final_resp]

    with patch("src.providers.anthropic_provider.FUNCTION_MAP", {}):
        history: list = []
        final_text, tool_logs = provider.process_chat_turn("go", history)

    assert final_text == "Recovered."
    assert len(tool_logs) == 1
    assert "Unknown tool" in tool_logs[0]["result"]["error"]


# ---------------------------------------------------------------------------
# Tool function raises → error result, loop continues
# ---------------------------------------------------------------------------

def test_tool_exception_returns_error_result(provider: AnthropicProvider) -> None:
    """A crashing tool must produce an error result — not propagate."""
    def bomb(**kwargs):
        raise RuntimeError("disk on fire")

    tool_resp = _make_response(
        [_tool_use_block("read_file", {"filepath": "boom.md"}, "tid_4")],
        stop_reason="tool_use",
    )
    final_resp = _make_response([_text_block("Recovered from crash.")], stop_reason="end_turn")
    provider._client.messages.create.side_effect = [tool_resp, final_resp]

    with patch("src.providers.anthropic_provider.FUNCTION_MAP", {"read_file": bomb}):
        history: list = []
        final_text, tool_logs = provider.process_chat_turn("read it", history)

    assert final_text == "Recovered from crash."
    assert "disk on fire" in tool_logs[0]["result"]["error"]


# ---------------------------------------------------------------------------
# context_files injected as text block
# ---------------------------------------------------------------------------

def test_context_files_injected_before_message(provider: AnthropicProvider) -> None:
    """Context file contents must appear as a text block before the user message."""
    resp = _make_response([_text_block("noted")], stop_reason="end_turn")
    provider._client.messages.create.return_value = resp

    with patch("src.providers.anthropic_provider.read_file", return_value={"content": "18mm Birch."}):
        history: list = []
        provider.process_chat_turn("Use context", history, context_files=["data/materials.md"])

    # Inspect the messages sent to the API.
    call_kwargs = provider._client.messages.create.call_args[1]
    sent_messages = call_kwargs["messages"]

    user_msg = sent_messages[0]
    assert user_msg["role"] == "user"
    # Content must be a list with at least 2 items (context block + message block).
    assert isinstance(user_msg["content"], list)
    assert len(user_msg["content"]) >= 2
    context_block = user_msg["content"][0]
    assert context_block["type"] == "text"
    assert "[Context files injected by user]" in context_block["text"]
    assert "18mm Birch" in context_block["text"]


def test_unreadable_context_file_skipped(provider: AnthropicProvider) -> None:
    """An unreadable context file must not inject any block."""
    resp = _make_response([_text_block("ok")], stop_reason="end_turn")
    provider._client.messages.create.return_value = resp

    with patch("src.providers.anthropic_provider.read_file", return_value={"error": "not found"}):
        history: list = []
        provider.process_chat_turn("hello", history, context_files=["missing.md"])

    call_kwargs = provider._client.messages.create.call_args[1]
    sent_messages = call_kwargs["messages"]
    user_msg = sent_messages[0]
    # Without context, content may be a plain string or single-block list.
    if isinstance(user_msg["content"], list):
        texts = [b["text"] for b in user_msg["content"] if b.get("type") == "text"]
        assert not any("[Context files injected by user]" in t for t in texts)
    else:
        assert "[Context files injected by user]" not in user_msg["content"]


# ---------------------------------------------------------------------------
# Images encoded as Anthropic image blocks
# ---------------------------------------------------------------------------

def test_valid_image_sent_as_base64_block(provider: AnthropicProvider) -> None:
    """A valid base64 image must be added as an Anthropic image content block."""
    raw = b"\x89PNG\r\n"
    b64 = base64.b64encode(raw).decode()
    resp = _make_response([_text_block("saw it")], stop_reason="end_turn")
    provider._client.messages.create.return_value = resp

    history: list = []
    provider.process_chat_turn(
        "Here is an image", history,
        images=[{"mime_type": "image/png", "data": b64}],
    )

    call_kwargs = provider._client.messages.create.call_args[1]
    sent_messages = call_kwargs["messages"]
    user_msg = sent_messages[0]
    assert isinstance(user_msg["content"], list)
    # Find an image block
    image_blocks = [b for b in user_msg["content"] if b.get("type") == "image"]
    assert len(image_blocks) == 1
    assert image_blocks[0]["source"]["type"] == "base64"
    assert image_blocks[0]["source"]["media_type"] == "image/png"
    assert image_blocks[0]["source"]["data"] == b64


def test_bad_base64_image_skipped(provider: AnthropicProvider) -> None:
    """An invalid base64 string must be skipped without raising."""
    resp = _make_response([_text_block("ok")], stop_reason="end_turn")
    provider._client.messages.create.return_value = resp

    history: list = []
    final_text, _ = provider.process_chat_turn(
        "bad image", history,
        images=[{"mime_type": "image/png", "data": "!!!not_base64!!!"}],
    )

    assert final_text == "ok"
    call_kwargs = provider._client.messages.create.call_args[1]
    sent_messages = call_kwargs["messages"]
    user_msg = sent_messages[0]
    content = user_msg["content"] if isinstance(user_msg["content"], list) else []
    image_blocks = [b for b in content if b.get("type") == "image"]
    assert len(image_blocks) == 0


# ---------------------------------------------------------------------------
# system_instruction forwarded
# ---------------------------------------------------------------------------

def test_system_instruction_forwarded(provider: AnthropicProvider) -> None:
    """The system_instruction must be passed as the ``system`` parameter."""
    resp = _make_response([_text_block("Hi!")], stop_reason="end_turn")
    provider._client.messages.create.return_value = resp

    history: list = []
    provider.process_chat_turn("Hello", history, system_instruction="You are a kitchen expert.")

    call_kwargs = provider._client.messages.create.call_args[1]
    assert call_kwargs.get("system") == "You are a kitchen expert."


def test_no_system_instruction_not_sent(provider: AnthropicProvider) -> None:
    """When system_instruction is None, the ``system`` key must be absent or None."""
    resp = _make_response([_text_block("Hi!")], stop_reason="end_turn")
    provider._client.messages.create.return_value = resp

    history: list = []
    provider.process_chat_turn("Hello", history, system_instruction=None)

    call_kwargs = provider._client.messages.create.call_args[1]
    # Either absent or explicitly None — both are acceptable.
    assert call_kwargs.get("system") is None


# ---------------------------------------------------------------------------
# tools_enabled=False — direct LLM call, no agentic loop
# ---------------------------------------------------------------------------

def test_no_tools_skips_agentic_loop(provider: AnthropicProvider) -> None:
    """When use_tools=False the provider makes exactly one API call and returns."""
    resp = _make_response([_text_block("direct answer")], stop_reason="end_turn")
    provider._client.messages.create.return_value = resp

    history: list = []
    final_text, tool_logs = provider.process_chat_turn(
        "what is the standard overhang?", history, use_tools=False
    )

    assert final_text == "direct answer"
    assert tool_logs == []
    assert provider._client.messages.create.call_count == 1


def test_no_tools_sends_no_tools_to_api(provider: AnthropicProvider) -> None:
    """When use_tools=False the messages.create call must have an empty tools list."""
    resp = _make_response([_text_block("ok")], stop_reason="end_turn")
    provider._client.messages.create.return_value = resp

    history: list = []
    provider.process_chat_turn("hello", history, use_tools=False)

    call_kwargs = provider._client.messages.create.call_args[1]
    assert call_kwargs.get("tools") == []


def test_no_tools_history_has_user_and_assistant_turn(provider: AnthropicProvider) -> None:
    """Even without tools, history must contain the user turn and the assistant reply."""
    resp = _make_response([_text_block("reply")], stop_reason="end_turn")
    provider._client.messages.create.return_value = resp

    history: list = []
    provider.process_chat_turn("ping", history, use_tools=False)

    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[1]["role"] == "assistant"


def test_tools_enabled_true_still_uses_agentic_loop(provider: AnthropicProvider) -> None:
    """Explicit use_tools=True must behave identically to the default (agentic loop)."""
    tool_resp = _make_response(
        [_tool_use_block("read_file", {"filepath": "a.md"}, "cX")],
        stop_reason="tool_use",
    )
    final_resp = _make_response([_text_block("done")], stop_reason="end_turn")
    provider._client.messages.create.side_effect = [tool_resp, final_resp]

    with patch("src.providers.anthropic_provider.FUNCTION_MAP",
               {"read_file": lambda filepath: {"content": "stuff"}}):
        history: list = []
        final_text, tool_logs = provider.process_chat_turn(
            "read a.md", history, use_tools=True
        )

    assert final_text == "done"
    assert len(tool_logs) == 1
    assert provider._client.messages.create.call_count == 2


# ---------------------------------------------------------------------------
# Multi-tool turn
# ---------------------------------------------------------------------------

def test_multi_tool_turn(provider: AnthropicProvider) -> None:
    """Two sequential tool calls before the final text response."""
    resp1 = _make_response(
        [_tool_use_block("read_file", {"filepath": "a.md"}, "c1")],
        stop_reason="tool_use",
    )
    resp2 = _make_response(
        [_tool_use_block("read_file", {"filepath": "b.md"}, "c2")],
        stop_reason="tool_use",
    )
    resp3 = _make_response([_text_block("Done reading both.")], stop_reason="end_turn")
    provider._client.messages.create.side_effect = [resp1, resp2, resp3]

    with patch("src.providers.anthropic_provider.FUNCTION_MAP", {
        "read_file": lambda filepath: {"content": f"contents of {filepath}"}
    }):
        history: list = []
        final_text, tool_logs = provider.process_chat_turn("read a.md and b.md", history)

    assert final_text == "Done reading both."
    assert len(tool_logs) == 2
    assert tool_logs[0]["args"]["filepath"] == "a.md"
    assert tool_logs[1]["args"]["filepath"] == "b.md"
    assert provider._client.messages.create.call_count == 3


# ---------------------------------------------------------------------------
# Tool schemas match FUNCTION_MAP keys
# ---------------------------------------------------------------------------

def test_tool_schemas_built_from_registry(provider: AnthropicProvider) -> None:
    """The provider must build Anthropic tool schemas for every tool in FUNCTION_MAP."""
    resp = _make_response([_text_block("ok")], stop_reason="end_turn")
    provider._client.messages.create.return_value = resp

    fake_map = {
        "read_file": lambda filepath: {},
        "edit_file": lambda filepath, search_text, replace_text: {},
    }
    fake_declarations = []  # we rely on provider's own schema building logic

    with patch("src.providers.anthropic_provider.FUNCTION_MAP", fake_map), \
         patch("src.providers.anthropic_provider.DECLARATIONS", fake_declarations):
        history: list = []
        provider.process_chat_turn("go", history)

    call_kwargs = provider._client.messages.create.call_args[1]
    tool_names_sent = {t["name"] for t in call_kwargs.get("tools", [])}
    assert tool_names_sent == set(fake_map.keys())


# ---------------------------------------------------------------------------
# Empty final text — no raise
# ---------------------------------------------------------------------------

def test_empty_final_text_handled(provider: AnthropicProvider) -> None:
    """An assistant response with empty text must return '' without raising."""
    resp = _make_response([_text_block("")], stop_reason="end_turn")
    provider._client.messages.create.return_value = resp

    history: list = []
    final_text, tool_logs = provider.process_chat_turn("hello", history)

    assert final_text == ""
    assert tool_logs == []
