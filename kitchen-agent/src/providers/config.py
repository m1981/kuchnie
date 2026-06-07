"""
src/providers/config.py
========================
Provider-specific configuration dataclasses.

Decouples provider implementations from the global ``Settings`` singleton.
The DI layer (``dependencies.py``) builds these from ``Settings``; providers
receive them via constructor injection.

Benefits
--------
* Providers are testable without monkeypatching global settings.
* Adding a new provider doesn't grow the ``Settings`` class.
* Config is explicit at the type level — each provider knows exactly
  what it needs.

Usage::

    # In dependencies.py
    config = GeminiConfig(model=settings.gemini_model, temperature=0.2)
    provider = GeminiProvider(config=config)

    # In tests
    config = GeminiConfig(model="test-model", temperature=0.0)
    provider = GeminiProvider(config=config)
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GeminiConfig:
    """Configuration for the Google Gemini provider."""

    model: str = "gemini-2.5-flash"
    temperature: float = 0.2


@dataclass(frozen=True)
class AnthropicConfig:
    """Configuration for the Anthropic Claude provider."""

    api_key: str | None = None
    model: str = "claude-sonnet-4-5"
    temperature: float = 0.2
    max_tokens: int = 8096


@dataclass(frozen=True)
class MimoConfig:
    """Configuration for the Xiaomi Mimo provider (OpenAI-compatible)."""

    api_key: str | None = None
    base_url: str = "https://api.xiaomimimo.com/v1"
    model: str = "mimo-v2.5-pro"
    temperature: float = 0.2
    max_tokens: int = 8096
