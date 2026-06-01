"""
src/providers/base.py
=====================
LLMProvider Protocol + provider registry factory.

Design
------
``LLMProvider`` is a ``runtime_checkable`` Protocol — any class that
implements ``process_chat_turn`` with the correct signature satisfies it
without inheritance.  This lets us test structural compliance easily and
avoids coupling providers to a base class.

``get_provider()`` is the single entry point for the rest of the application.
It reads ``settings.llm_provider`` and returns the matching instance.  We
deliberately read settings at *call time* (not cached at module load) so that
runtime reconfiguration (e.g. in tests with ``monkeypatch`` or
``patch("src.config.settings")``) takes effect immediately.

Providers available:
  ``"gemini"``     → GeminiProvider   (default)
  ``"anthropic"``  → AnthropicProvider

Adding a new provider
---------------------
1. Create ``src/providers/my_provider.py`` implementing ``process_chat_turn``.
2. Add a new branch in ``get_provider()`` below.
3. Document the provider name in ``config.py``.
That is all — no other file needs to change.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class LLMProvider(Protocol):
    """
    Structural interface every LLM provider must satisfy.

    The method contract is identical to the original ``agent.process_chat_turn``
    function signature so ``chat_service.py`` requires zero changes.

    Args:
        user_message:       Plain text from the user.
        history:            Mutable conversation history list (mutated in place).
                            The concrete format depends on the provider:
                              - Gemini: list of ``types.Content`` objects
                              - Anthropic: list of ``MessageParam``-shaped dicts
        system_instruction: Optional system-prompt text.
        images:             Optional list of ``{"mime_type": str, "data": str}``
                            base64-encoded image dicts.
        context_files:      Optional list of file paths to inject as context.

    Returns:
        ``(final_text, tool_logs)`` tuple where ``tool_logs`` is a list of
        dicts with keys ``name``, ``args``, ``result``.
    """

    def process_chat_turn(
        self,
        user_message: str,
        history: list,
        system_instruction: str | None = None,
        images: list[dict] | None = None,
        context_files: list[str] | None = None,
        use_tools: bool = True,
    ) -> tuple[str, list[dict]]:
        ...


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def get_provider(
    provider_name: str | None = None,
    model_override: str | None = None,
) -> LLMProvider:
    """
    Return an LLM provider instance.

    Args:
        provider_name:  Which provider to use.  When ``None`` (the default) the
                        value is read from ``settings.llm_provider`` so the
                        server default applies.
        model_override: Model id to use instead of the provider's configured
                        default.  When ``None`` the provider reads its own
                        ``settings.*_model`` field.

    Implementation note: we import ``src.config`` (the module) and access
    ``src.config.settings`` through it so ``patch("src.config.settings")``
    correctly intercepts the attribute lookup even after the module is cached.

    Raises:
        ValueError: when the resolved provider name is not supported.
    """
    import src.config as _config  # noqa: PLC0415

    name = provider_name or _config.settings.llm_provider

    if name == "gemini":
        from src.providers.gemini import GeminiProvider  # noqa: PLC0415
        return GeminiProvider(model_override=model_override)

    if name == "anthropic":
        from src.providers.anthropic_provider import AnthropicProvider  # noqa: PLC0415
        return AnthropicProvider(model_override=model_override)

    raise ValueError(f"Unknown LLM provider: {name}. Supported: 'gemini', 'anthropic'.")
