"""
tests/test_gemini_history_coercion.py
======================================
TDD tests for GeminiProvider's Anthropic-history coercion.

Root cause
----------
When a session was created with the Anthropic provider its history items are
stored as plain ``__provider: "anthropic"`` JSON objects.  On the next turn,
``hydrate_history()`` correctly returns those items as plain ``dict`` objects.
If the user switches to the Gemini provider (or the server default changes),
``GeminiProvider.process_chat_turn()`` receives a history list containing
plain dicts.  It then passes that list unchanged to
``client.models.generate_content(contents=history, ...)``.

The Gemini SDK validates ``contents`` with Pydantic and expects only
``types.Content`` instances.  Plain dicts are rejected with a
``ValidationError``::

    contents.list[union[Content,...]].6.Content.content
        Extra inputs are not permitted [type=extra_forbidden]
    ...

This causes HTTP 500 on the ``POST /api/chat`` endpoint.

Fix contract
------------
``GeminiProvider`` must coerce any plain-dict items in the history list to
``types.Content`` objects **before** passing the list to the Gemini SDK.
The coercion must:

  1. Map Anthropic ``"assistant"`` role → Gemini ``"model"`` role.
  2. Handle plain-string content (``{"role": "user", "content": "hello"}``).
  3. Handle list-of-blocks content:
       - ``{"type": "text", "text": "..."}``  → ``Part(text=...)``
       - ``{"type": "tool_use", ...}``         → ``Part(function_call=...)``
       - ``{"type": "tool_result", ...}``      → ``Part(function_response=...)``
  4. Support multiple blocks of the same type in one message (parallel tools).
  5. Recover the function name for ``tool_result`` blocks by scanning
     backwards through previously processed items for a matching tool_use id.
  6. Leave ``types.Content`` objects already in the list untouched
     (pure-Gemini sessions must not be affected).
  7. Not mutate the original history list — coercion is internal to the
     provider; the caller's list keeps its plain dicts so serialisation
     stays correct.

Test coverage
-------------
- Plain-string user turn coerced to ``types.Content``
- List-of-text-blocks assistant turn coerced correctly
- Single ``tool_use`` block → ``Part(function_call=...)``
- Multiple ``tool_use`` blocks in one message (parallel tools)
- ``tool_result`` block → ``Part(function_response=...)`` with correct name
- Multiple ``tool_result`` blocks (parallel) with correct names
- Mixed text + tool_use in one assistant message
- ``types.Content`` items are not re-wrapped (regression guard)
- Full end-to-end: Anthropic history → GeminiProvider → no Pydantic error
- process_chat_turn with anthropic dict history calls generate_content without error
- Role mapping: assistant → model, user → user
- Unknown block type → ``Part(text=str(block))`` fallback (no crash)
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from google.genai import types

from src.providers.gemini import GeminiProvider, _coerce_history_for_gemini


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_text_response(text: str) -> MagicMock:
    """Return a mock Gemini generate_content response with a text answer."""
    part = types.Part(text=text)
    mock = MagicMock()
    mock.candidates = [MagicMock(content=types.Content(role="model", parts=[part]))]
    mock.text = text
    return mock


def _anthropic_user_str(text: str) -> dict:
    return {"role": "user", "content": text}


def _anthropic_assistant_text(text: str) -> dict:
    return {"role": "assistant", "content": [{"type": "text", "text": text}]}


def _anthropic_assistant_tool_use(name: str, tool_input: dict, tool_id: str) -> dict:
    return {
        "role": "assistant",
        "content": [{"type": "tool_use", "id": tool_id, "name": name, "input": tool_input}],
    }


def _anthropic_assistant_multi_tool(tools: list[tuple[str, dict, str]]) -> dict:
    """tools = [(name, input, id), ...]"""
    return {
        "role": "assistant",
        "content": [
            {"type": "tool_use", "id": tid, "name": name, "input": inp}
            for name, inp, tid in tools
        ],
    }


def _anthropic_user_tool_result(tool_id: str, result_json: str) -> dict:
    return {
        "role": "user",
        "content": [{"type": "tool_result", "tool_use_id": tool_id, "content": result_json}],
    }


def _anthropic_user_multi_tool_result(results: list[tuple[str, str]]) -> dict:
    """results = [(tool_use_id, result_json), ...]"""
    return {
        "role": "user",
        "content": [
            {"type": "tool_result", "tool_use_id": tid, "content": res}
            for tid, res in results
        ],
    }


@pytest.fixture
def provider() -> GeminiProvider:
    with patch("src.providers.gemini.genai.Client"):
        return GeminiProvider()


# ===========================================================================
# Unit tests for _coerce_history_for_gemini()
# ===========================================================================

class TestCoercionFunction:
    """Direct tests of the internal _coerce_history_for_gemini helper."""

    # -----------------------------------------------------------------------
    # Plain-string user content
    # -----------------------------------------------------------------------

    def test_plain_string_user_content_becomes_content_object(self) -> None:
        history = [_anthropic_user_str("Hello, what are your capabilities?")]
        result = _coerce_history_for_gemini(history)

        assert len(result) == 1
        item = result[0]
        assert isinstance(item, types.Content)
        assert item.role == "user"
        assert len(item.parts) == 1
        assert item.parts[0].text == "Hello, what are your capabilities?"

    # -----------------------------------------------------------------------
    # Role mapping: assistant → model
    # -----------------------------------------------------------------------

    def test_assistant_role_mapped_to_model(self) -> None:
        history = [_anthropic_assistant_text("I can help with kitchen design.")]
        result = _coerce_history_for_gemini(history)

        assert result[0].role == "model"

    def test_user_role_preserved(self) -> None:
        history = [_anthropic_user_str("Hello")]
        result = _coerce_history_for_gemini(history)

        assert result[0].role == "user"

    # -----------------------------------------------------------------------
    # Text block in list-content
    # -----------------------------------------------------------------------

    def test_list_text_block_becomes_text_part(self) -> None:
        history = [_anthropic_assistant_text("Use 18mm birch.")]
        result = _coerce_history_for_gemini(history)

        assert isinstance(result[0], types.Content)
        assert result[0].parts[0].text == "Use 18mm birch."

    # -----------------------------------------------------------------------
    # Single tool_use → function_call Part
    # -----------------------------------------------------------------------

    def test_single_tool_use_becomes_function_call_part(self) -> None:
        history = [
            _anthropic_assistant_tool_use(
                "read_file", {"filepath": "materials.md"}, "c1"
            )
        ]
        result = _coerce_history_for_gemini(history)

        item = result[0]
        assert isinstance(item, types.Content)
        assert item.role == "model"
        fc = item.parts[0].function_call
        assert fc is not None
        assert fc.name == "read_file"
        assert fc.args == {"filepath": "materials.md"}
        assert fc.id == "c1"

    # -----------------------------------------------------------------------
    # Multiple parallel tool_use blocks in one message
    # -----------------------------------------------------------------------

    def test_multiple_tool_use_blocks_become_multiple_parts(self) -> None:
        history = [
            _anthropic_assistant_multi_tool([
                ("read_file", {"filepath": "a.md"}, "c1"),
                ("read_file", {"filepath": "b.md"}, "c2"),
                ("get_repo_map", {}, "c3"),
            ])
        ]
        result = _coerce_history_for_gemini(history)

        item = result[0]
        assert len(item.parts) == 3
        assert item.parts[0].function_call.name == "read_file"
        assert item.parts[0].function_call.id == "c1"
        assert item.parts[1].function_call.name == "read_file"
        assert item.parts[1].function_call.id == "c2"
        assert item.parts[2].function_call.name == "get_repo_map"
        assert item.parts[2].function_call.id == "c3"

    # -----------------------------------------------------------------------
    # tool_result → function_response with correct name recovered
    # -----------------------------------------------------------------------

    def test_tool_result_recovers_function_name_from_preceding_tool_use(self) -> None:
        history = [
            _anthropic_assistant_tool_use("read_file", {"filepath": "test.md"}, "c1"),
            _anthropic_user_tool_result("c1", '{"content": "hello"}'),
        ]
        result = _coerce_history_for_gemini(history)

        fr = result[1].parts[0].function_response
        assert fr is not None
        assert fr.name == "read_file"       # recovered from the preceding tool_use
        assert fr.id == "c1"
        assert fr.response == {"content": "hello"}

    def test_tool_result_without_matching_tool_use_uses_unknown_name(self) -> None:
        """When no matching tool_use is found, name falls back to 'unknown'."""
        history = [
            _anthropic_user_tool_result("orphan_id", '{"x": 1}'),
        ]
        result = _coerce_history_for_gemini(history)

        fr = result[0].parts[0].function_response
        assert fr is not None
        assert fr.name == "unknown"

    # -----------------------------------------------------------------------
    # Multiple parallel tool_result blocks (parallel tool calls)
    # -----------------------------------------------------------------------

    def test_multiple_tool_results_each_get_correct_name(self) -> None:
        history = [
            _anthropic_assistant_multi_tool([
                ("read_file",          {"filepath": "a.md"}, "c1"),
                ("search_knowledge_base", {"query": "hinges"}, "c2"),
            ]),
            _anthropic_user_multi_tool_result([
                ("c1", '{"content": "board specs"}'),
                ("c2", '{"results": []}'),
            ]),
        ]
        result = _coerce_history_for_gemini(history)

        parts = result[1].parts
        assert len(parts) == 2

        assert parts[0].function_response.name == "read_file"
        assert parts[0].function_response.id == "c1"
        assert parts[0].function_response.response == {"content": "board specs"}

        assert parts[1].function_response.name == "search_knowledge_base"
        assert parts[1].function_response.id == "c2"

    # -----------------------------------------------------------------------
    # Mixed text + tool_use in one assistant message
    # -----------------------------------------------------------------------

    def test_mixed_text_and_tool_use_in_one_message(self) -> None:
        history = [
            {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "Let me read that file."},
                    {"type": "tool_use", "id": "c1", "name": "read_file",
                     "input": {"filepath": "x.md"}},
                ],
            }
        ]
        result = _coerce_history_for_gemini(history)

        item = result[0]
        assert len(item.parts) == 2
        assert item.parts[0].text == "Let me read that file."
        assert item.parts[1].function_call.name == "read_file"

    # -----------------------------------------------------------------------
    # types.Content items are NOT re-wrapped (Gemini-format sessions)
    # -----------------------------------------------------------------------

    def test_existing_content_objects_pass_through_unchanged(self) -> None:
        original = types.Content(
            role="user",
            parts=[types.Part(text="Pure Gemini message")]
        )
        result = _coerce_history_for_gemini([original])

        assert len(result) == 1
        assert result[0] is original          # exact same object, not a copy

    def test_mixed_content_objects_and_dicts(self) -> None:
        """A history with both Gemini Content and Anthropic dicts is coerced."""
        original_content = types.Content(
            role="user", parts=[types.Part(text="First Gemini turn")]
        )
        history = [
            original_content,
            _anthropic_assistant_text("Then Anthropic answered."),
        ]
        result = _coerce_history_for_gemini(history)

        assert result[0] is original_content  # unchanged
        assert isinstance(result[1], types.Content)
        assert result[1].role == "model"

    # -----------------------------------------------------------------------
    # Unknown block type → fallback to text Part (no crash)
    # -----------------------------------------------------------------------

    def test_unknown_block_type_becomes_text_part_fallback(self) -> None:
        history = [
            {
                "role": "user",
                "content": [{"type": "alien_format", "payload": "???"}],
            }
        ]
        # Must not raise
        result = _coerce_history_for_gemini(history)
        assert isinstance(result[0], types.Content)
        assert result[0].parts[0].text is not None  # some fallback text

    # -----------------------------------------------------------------------
    # Original history list is NOT mutated
    # -----------------------------------------------------------------------

    def test_does_not_mutate_original_history_list(self) -> None:
        original = [_anthropic_user_str("hello")]
        original_id = id(original[0])
        result = _coerce_history_for_gemini(original)

        # original list still has a plain dict
        assert isinstance(original[0], dict)
        assert id(original[0]) == original_id
        # result has a Content object
        assert isinstance(result[0], types.Content)

    # -----------------------------------------------------------------------
    # Empty history
    # -----------------------------------------------------------------------

    def test_empty_history_returns_empty_list(self) -> None:
        assert _coerce_history_for_gemini([]) == []

    # -----------------------------------------------------------------------
    # tool_result content: JSON string parsed to dict
    # -----------------------------------------------------------------------

    def test_tool_result_json_string_parsed_to_dict(self) -> None:
        history = [
            _anthropic_assistant_tool_use("read_file", {}, "c1"),
            _anthropic_user_tool_result("c1", '{"content": "# heading\\ntext"}'),
        ]
        result = _coerce_history_for_gemini(history)
        fr = result[1].parts[0].function_response
        assert fr.response == {"content": "# heading\ntext"}

    def test_tool_result_invalid_json_wrapped_in_dict(self) -> None:
        """Malformed JSON in tool_result content must not crash."""
        history = [
            _anthropic_assistant_tool_use("some_tool", {}, "c1"),
            _anthropic_user_tool_result("c1", "not-valid-json!!!"),
        ]
        result = _coerce_history_for_gemini(history)
        fr = result[1].parts[0].function_response
        assert isinstance(fr.response, dict)  # wrapped, not crashed


# ===========================================================================
# Integration tests: GeminiProvider.process_chat_turn with Anthropic history
# ===========================================================================

class TestGeminiProviderWithAnthropicHistory:
    """
    End-to-end tests ensuring that GeminiProvider does not raise a Pydantic
    ValidationError when called with a history list containing Anthropic dicts.
    """

    def test_process_chat_turn_does_not_raise_with_anthropic_dict_history(
        self, provider: GeminiProvider
    ) -> None:
        """Core regression test — this is the exact scenario from the bug report."""
        # Simulate an 8-turn Anthropic session (indices 0-7 are all plain dicts)
        anthropic_history = [
            _anthropic_user_str("Jesteś technologiem produkcji."),
            _anthropic_assistant_tool_use("read_file", {"filepath": "data.md"}, "c1"),
            _anthropic_user_tool_result("c1", '{"content": "oak 18mm"}'),
            _anthropic_assistant_multi_tool([
                ("read_file",  {"filepath": "a.md"}, "c2"),
                ("read_file",  {"filepath": "b.md"}, "c3"),
                ("get_repo_map", {}, "c4"),
            ]),
            _anthropic_user_multi_tool_result([
                ("c2", '{"content": "spec-a"}'),
                ("c3", '{"content": "spec-b"}'),
                ("c4", '{"files": []}'),
            ]),
            _anthropic_assistant_multi_tool([
                ("read_file",  {"filepath": "x.md"}, "c5"),
                ("read_file",  {"filepath": "y.md"}, "c6"),
            ]),
            _anthropic_user_multi_tool_result([          # ← index 6 (the failing one)
                ("c5", '{"content": "x data"}'),
                ("c6", '{"content": "y data"}'),
            ]),
            _anthropic_assistant_text("Oto wyniki mojej pracy."),  # ← index 7
        ]

        provider._client.models.generate_content.return_value = _make_text_response(
            "Rozumiem, kontynuujemy."
        )

        # Must not raise Pydantic ValidationError
        final_text, tool_logs = provider.process_chat_turn(
            user_message="Czy możesz podsumować?",
            history=list(anthropic_history),   # copy so original is unchanged
        )

        assert final_text == "Rozumiem, kontynuujemy."
        assert tool_logs == []

    def test_generate_content_receives_only_content_objects(
        self, provider: GeminiProvider
    ) -> None:
        """generate_content must be called with only types.Content in contents."""
        anthropic_history = [
            _anthropic_user_str("Hello"),
            _anthropic_assistant_text("Hi!"),
        ]

        provider._client.models.generate_content.return_value = _make_text_response("ok")

        provider.process_chat_turn("Next question", history=list(anthropic_history))

        call_args = provider._client.models.generate_content.call_args
        contents = call_args.kwargs.get("contents") or call_args.args[1]

        for item in contents:
            assert isinstance(item, types.Content), (
                f"Expected types.Content but got {type(item).__name__}: {item}"
            )

    def test_pure_gemini_history_still_works(self, provider: GeminiProvider) -> None:
        """Pure Gemini sessions (Content objects) must continue to work."""
        gemini_history = [
            types.Content(role="user",  parts=[types.Part(text="What is Blum?")]),
            types.Content(role="model", parts=[types.Part(text="Blum is a hinge maker.")]),
        ]

        provider._client.models.generate_content.return_value = _make_text_response(
            "Yes, they make hinges."
        )

        final_text, _ = provider.process_chat_turn(
            "Tell me more", history=list(gemini_history)
        )
        assert final_text == "Yes, they make hinges."

    def test_empty_history_does_not_raise(self, provider: GeminiProvider) -> None:
        provider._client.models.generate_content.return_value = _make_text_response("Hello!")

        final_text, _ = provider.process_chat_turn("First message", history=[])
        assert final_text == "Hello!"

    def test_anthropic_history_original_list_unchanged_after_turn(
        self, provider: GeminiProvider
    ) -> None:
        """
        The caller's history list should accumulate new items correctly even
        when existing items are Anthropic dicts.
        """
        anthropic_history: list = [
            _anthropic_user_str("Setup"),
            _anthropic_assistant_text("Ready."),
        ]
        original_item_0 = anthropic_history[0]

        provider._client.models.generate_content.return_value = _make_text_response(
            "Continuing."
        )

        provider.process_chat_turn("Continue please", history=anthropic_history)

        # The new user turn was appended as a types.Content (GeminiProvider always
        # appends Content objects for new turns)
        assert isinstance(anthropic_history[-1], types.Content)
        # The old items are still plain dicts (not converted in-place)
        assert anthropic_history[0] is original_item_0
        assert isinstance(anthropic_history[0], dict)

    def test_full_tool_call_loop_with_anthropic_history(
        self, provider: GeminiProvider
    ) -> None:
        """
        Tool call loop works correctly when the pre-existing history is all
        Anthropic dicts and the new turn triggers a tool call.
        """
        anthropic_history: list = [
            _anthropic_user_str("Read the materials file."),
            _anthropic_assistant_text("I read it already."),
        ]

        # First API call returns a tool call
        tool_part = types.Part(
            function_call=types.FunctionCall(
                name="read_file", args={"filepath": "materials.md"}, id="new_c1"
            )
        )
        resp_tool = MagicMock()
        resp_tool.candidates = [
            MagicMock(content=types.Content(role="model", parts=[tool_part]))
        ]

        resp_final = _make_text_response("The file contains oak 18mm.")

        provider._client.models.generate_content.side_effect = [resp_tool, resp_final]

        with patch("src.providers.gemini.FUNCTION_MAP", {
            "read_file": lambda filepath: {"content": "oak 18mm"},
        }):
            final_text, tool_logs = provider.process_chat_turn(
                "What is in materials.md?",
                history=anthropic_history,
            )

        assert final_text == "The file contains oak 18mm."
        assert len(tool_logs) == 1
        assert tool_logs[0]["name"] == "read_file"
