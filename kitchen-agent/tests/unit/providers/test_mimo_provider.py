"""
tests/test_mimo_provider.py
============================
Tests for the Xiaomi Mimo provider.

Verifies:
  - MimoProvider satisfies LLMProvider Protocol
  - get_provider() returns MimoProvider when configured
  - Normalizer handles OpenAI-compatible responses
  - Provider catalogue includes mimo
"""
from unittest.mock import patch, MagicMock, PropertyMock
from dataclasses import dataclass

import pytest

from src.providers.base import LLMProvider, get_provider
from src.providers.mimo_provider import MimoProvider
from src.providers.normalizer import ResponseNormalizer, NormalizedResponse


# ---------------------------------------------------------------------------
# Mock OpenAI response objects
# ---------------------------------------------------------------------------

def _make_mock_message(content="Hello", tool_calls=None):
    """Create a mock OpenAI ChatCompletionMessage."""
    msg = MagicMock()
    msg.content = content
    msg.tool_calls = tool_calls
    return msg


def _make_mock_choice(message=None):
    """Create a mock OpenAI Choice."""
    choice = MagicMock()
    choice.message = message or _make_mock_message()
    return choice


def _make_mock_completion(choices=None, input_tokens=10, output_tokens=5):
    """Create a mock OpenAI ChatCompletion."""
    completion = MagicMock()
    completion.choices = choices or [_make_mock_choice()]
    completion.usage = MagicMock(
        prompt_tokens=input_tokens,
        completion_tokens=output_tokens,
    )
    return completion


def _make_mock_tool_call(name="read_file", args='{"filepath": "test.md"}', call_id="call-1"):
    """Create a mock OpenAI ToolCall."""
    tc = MagicMock()
    tc.id = call_id
    tc.function = MagicMock()
    tc.function.name = name
    tc.function.arguments = args
    return tc


# ---------------------------------------------------------------------------
# Protocol compliance
# ---------------------------------------------------------------------------

def test_mimo_provider_satisfies_protocol() -> None:
    """MimoProvider must satisfy the LLMProvider Protocol."""
    with patch("src.providers.mimo_provider.OpenAI"):
        provider = MimoProvider()
    assert isinstance(provider, LLMProvider)


# ---------------------------------------------------------------------------
# get_provider() factory
# ---------------------------------------------------------------------------

def test_get_provider_returns_mimo_when_configured() -> None:
    with patch("src.config.settings") as mock_settings, \
         patch("src.providers.mimo_provider.OpenAI"):
        mock_settings.llm_provider = "mimo"
        mock_settings.mimo_api_key = None
        mock_settings.mimo_base_url = "https://api.xiaomimimo.com/v1"
        mock_settings.mimo_model = "mimo-v2.5-pro"
        provider = get_provider()
    assert isinstance(provider, MimoProvider)


def test_get_provider_mimo_with_model_override() -> None:
    with patch("src.config.settings") as mock_settings, \
         patch("src.providers.mimo_provider.OpenAI"):
        mock_settings.llm_provider = "mimo"
        mock_settings.mimo_api_key = None
        mock_settings.mimo_base_url = "https://api.xiaomimimo.com/v1"
        mock_settings.mimo_model = "mimo-v2.5-pro"
        provider = get_provider(model_override="mimo-v2.5")
    assert isinstance(provider, MimoProvider)
    assert provider._model == "mimo-v2.5"


# ---------------------------------------------------------------------------
# Normalizer — OpenAI-compatible responses
# ---------------------------------------------------------------------------

class TestNormalizerMimo:
    def test_text_response(self):
        normalizer = ResponseNormalizer()
        mock_response = _make_mock_completion(
            choices=[_make_mock_choice(_make_mock_message("Hello from MiMo"))]
        )

        result = normalizer.normalize(mock_response, "mimo")

        assert result.text == "Hello from MiMo"
        assert result.has_tool_calls is False
        assert result.tool_calls == []

    def test_tool_call_response(self):
        normalizer = ResponseNormalizer()
        mock_tc = _make_mock_tool_call("read_file", '{"filepath": "test.md"}', "call-1")
        mock_response = _make_mock_completion(
            choices=[_make_mock_choice(_make_mock_message(None, tool_calls=[mock_tc]))]
        )

        result = normalizer.normalize(mock_response, "mimo")

        assert result.text == ""
        assert result.has_tool_calls is True
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].name == "read_file"
        assert result.tool_calls[0].arguments == {"filepath": "test.md"}
        assert result.tool_calls[0].id == "call-1"

    def test_usage_populated(self):
        normalizer = ResponseNormalizer()
        mock_response = _make_mock_completion(input_tokens=100, output_tokens=50)

        result = normalizer.normalize(mock_response, "mimo")

        assert result.usage["input"] == 100
        assert result.usage["output"] == 50
        assert result.usage["total"] == 150

    def test_mixed_text_and_tool_calls(self):
        normalizer = ResponseNormalizer()
        mock_tc = _make_mock_tool_call("search_knowledge_base", '{"query": "blum"}', "call-2")
        mock_response = _make_mock_completion(
            choices=[_make_mock_choice(_make_mock_message("Let me search...", tool_calls=[mock_tc]))]
        )

        result = normalizer.normalize(mock_response, "mimo")

        assert result.text == "Let me search..."
        assert result.has_tool_calls is True
        assert len(result.tool_calls) == 1

    def test_chunk_text(self):
        normalizer = ResponseNormalizer()
        chunk = MagicMock()
        chunk.choices = [MagicMock()]
        chunk.choices[0].delta.content = "Hello"

        result = normalizer.normalize_chunk(chunk, "mimo")
        assert result == "Hello"

    def test_chunk_empty(self):
        normalizer = ResponseNormalizer()
        chunk = MagicMock()
        chunk.choices = [MagicMock()]
        chunk.choices[0].delta.content = None

        result = normalizer.normalize_chunk(chunk, "mimo")
        assert result == ""


# ---------------------------------------------------------------------------
# Provider catalogue
# ---------------------------------------------------------------------------

def test_provider_catalogue_includes_mimo() -> None:
    from src.api.providers import _PROVIDER_CATALOGUE

    provider_ids = [p.id for p in _PROVIDER_CATALOGUE]
    assert "mimo" in provider_ids


def test_mimo_provider_has_two_models() -> None:
    from src.api.providers import _PROVIDER_CATALOGUE

    mimo = next(p for p in _PROVIDER_CATALOGUE if p.id == "mimo")
    model_ids = [m.id for m in mimo.models]
    assert "mimo-v2.5-pro" in model_ids
    assert "mimo-v2.5" in model_ids


def test_mimo_default_model_is_pro() -> None:
    from src.api.providers import _PROVIDER_CATALOGUE

    mimo = next(p for p in _PROVIDER_CATALOGUE if p.id == "mimo")
    assert mimo.default_model == "mimo-v2.5-pro"


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def test_config_has_mimo_settings() -> None:
    from src.config import Settings

    s = Settings()
    assert hasattr(s, "mimo_api_key")
    assert hasattr(s, "mimo_base_url")
    assert hasattr(s, "mimo_model")
    assert hasattr(s, "mimo_temperature")
    assert hasattr(s, "mimo_max_tokens")


def test_config_mimo_defaults() -> None:
    from src.config import Settings

    s = Settings()
    assert s.mimo_base_url == "https://api.xiaomimimo.com/v1"
    assert s.mimo_model == "mimo-v2.5-pro"
    assert s.mimo_temperature == 0.2
    assert s.mimo_max_tokens == 8096


# ---------------------------------------------------------------------------
# Active provider endpoint
# ---------------------------------------------------------------------------

def test_active_provider_mimo() -> None:
    from src.api.providers import get_active_provider
    from src.config import settings

    with patch.object(settings, "llm_provider", "mimo"), \
         patch.object(settings, "mimo_model", "mimo-v2.5-pro"):
        result = get_active_provider()
    assert result.provider == "mimo"
    assert result.model == "mimo-v2.5-pro"
