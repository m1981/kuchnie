"""
tests/test_providers_base.py
============================
Tests for the LLMProvider Protocol and provider registry.

Verifies:
  - Protocol structural compliance (duck-typing) — any object that implements
    ``process_chat_turn`` satisfies the protocol.
  - ``get_provider()`` factory returns the correct concrete class based on
    ``settings.llm_provider``.
  - ``get_provider()`` raises ``ValueError`` for unknown provider names.
"""
from unittest.mock import patch, MagicMock

import pytest

from src.providers.base import LLMProvider, get_provider
from src.providers.gemini import GeminiProvider
from src.providers.anthropic_provider import AnthropicProvider


# ---------------------------------------------------------------------------
# Protocol structural compliance
# ---------------------------------------------------------------------------

class _MinimalProvider:
    """Minimal duck-type implementation to verify protocol shape."""

    def process_chat_turn(
        self,
        user_message: str,
        history: list,
        system_instruction=None,
        images=None,
        context_files=None,
    ):
        return "ok", []


def test_minimal_provider_satisfies_protocol() -> None:
    """Any object with the right signature satisfies LLMProvider (structural subtyping)."""
    provider = _MinimalProvider()
    assert isinstance(provider, LLMProvider)


def test_gemini_provider_satisfies_protocol() -> None:
    with patch("src.providers.gemini.genai.Client"):
        provider = GeminiProvider()
    assert isinstance(provider, LLMProvider)


def test_anthropic_provider_satisfies_protocol() -> None:
    with patch("src.providers.anthropic_provider.anthropic.Anthropic"):
        provider = AnthropicProvider()
    assert isinstance(provider, LLMProvider)


# ---------------------------------------------------------------------------
# get_provider() factory
# ---------------------------------------------------------------------------

def test_get_provider_returns_gemini_by_default() -> None:
    # settings is imported locally inside get_provider() — patch at the config
    # module level so the local import inside get_provider picks it up.
    with patch("src.config.settings") as mock_settings, \
         patch("src.providers.gemini.genai.Client"):
        mock_settings.llm_provider = "gemini"
        provider = get_provider()
    assert isinstance(provider, GeminiProvider)


def test_get_provider_returns_anthropic_when_configured() -> None:
    with patch("src.config.settings") as mock_settings, \
         patch("src.providers.anthropic_provider.anthropic.Anthropic"):
        mock_settings.llm_provider = "anthropic"
        mock_settings.anthropic_api_key = None
        provider = get_provider()
    assert isinstance(provider, AnthropicProvider)


def test_get_provider_raises_for_unknown_provider() -> None:
    with patch("src.config.settings") as mock_settings:
        mock_settings.llm_provider = "openai"
        with pytest.raises(ValueError, match="Unknown LLM provider: openai"):
            get_provider()
