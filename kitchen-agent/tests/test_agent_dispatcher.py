"""
tests/test_agent_dispatcher.py
================================
Tests for the refactored agent.py dispatcher.

After the provider refactor, ``agent.process_chat_turn`` is a thin delegator:
it calls ``get_provider()`` to retrieve the configured provider instance and
delegates the turn to it.

Covers:
  - process_chat_turn delegates to the active provider
  - The correct provider (Gemini/Anthropic) is called based on settings
  - The function signature and return contract are preserved (backward compat)
"""
from unittest.mock import MagicMock, patch

import pytest

from src.agent import process_chat_turn


# ---------------------------------------------------------------------------
# Delegation to provider
# ---------------------------------------------------------------------------

def test_process_chat_turn_delegates_to_provider() -> None:
    """process_chat_turn must call the active provider's process_chat_turn."""
    mock_provider = MagicMock()
    mock_provider.process_chat_turn.return_value = ("Hello from provider", [])

    with patch("src.agent.get_provider", return_value=mock_provider):
        history: list = []
        text, tools = process_chat_turn("Hi", history)

    assert text == "Hello from provider"
    assert tools == []
    mock_provider.process_chat_turn.assert_called_once_with(
        user_message="Hi",
        history=history,
        system_instruction=None,
        images=None,
        context_files=None,
        use_tools=True,
    )


def test_process_chat_turn_passes_all_args() -> None:
    """All optional arguments must be forwarded verbatim to the provider."""
    mock_provider = MagicMock()
    mock_provider.process_chat_turn.return_value = ("answer", [{"name": "read_file"}])

    images = [{"mime_type": "image/png", "data": "abc123"}]
    context_files = ["data/materials.md"]
    history: list = [{"role": "user", "content": "prev"}]

    with patch("src.agent.get_provider", return_value=mock_provider):
        text, tools = process_chat_turn(
            "New question",
            history,
            system_instruction="Be a kitchen expert",
            images=images,
            context_files=context_files,
        )

    mock_provider.process_chat_turn.assert_called_once_with(
        user_message="New question",
        history=history,
        system_instruction="Be a kitchen expert",
        images=images,
        context_files=context_files,
        use_tools=True,
    )
    assert text == "answer"
    assert len(tools) == 1


def test_process_chat_turn_returns_tuple() -> None:
    """Return value must always be a (str, list) tuple."""
    mock_provider = MagicMock()
    mock_provider.process_chat_turn.return_value = ("text", [])

    with patch("src.agent.get_provider", return_value=mock_provider):
        result = process_chat_turn("test", [])

    assert isinstance(result, tuple)
    assert len(result) == 2
    assert isinstance(result[0], str)
    assert isinstance(result[1], list)


# ---------------------------------------------------------------------------
# Provider selection is not hard-coded
# ---------------------------------------------------------------------------

def test_process_chat_turn_calls_get_provider_on_each_call() -> None:
    """get_provider must be called each time so runtime config changes take effect."""
    mock_provider = MagicMock()
    mock_provider.process_chat_turn.return_value = ("ok", [])

    with patch("src.agent.get_provider", return_value=mock_provider) as mock_get_provider:
        process_chat_turn("q1", [])
        process_chat_turn("q2", [])

    assert mock_get_provider.call_count == 2
