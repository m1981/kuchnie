"""
src/agent/
==========
Agent layer — LLM turn lifecycle, tool execution, and context assembly.

  - ``process_chat_turn`` — thin dispatcher (backward-compatible public API)
  - ``tool_executor``     — safe, isolated tool execution
  - ``context_assembler`` — builds the context window (Phase 3)
  - ``turn_orchestrator`` — manages one turn end-to-end (Phase 4)

Public API
----------
``process_chat_turn`` — signature is **identical** to the original function so
all callers (``chat_service.py``, tests) require zero changes.

Provider implementations
------------------------
- Gemini  → ``src/providers/gemini.py``   (original logic, class-ified)
- Anthropic → ``src/providers/anthropic_provider.py``   (new)

Adding a new provider
---------------------
1. Implement ``LLMProvider`` in a new file under ``src/providers/``.
2. Register it in ``src/providers/base.py :: get_provider()``.
3. Add the key to ``settings.llm_provider`` docs in ``config.py``.
This package does NOT need to change.
"""
# ╔════════════════════════════════════════════════════════════════════╗
# ║  MIGRATION_SHIM                                                  ║
# ║  Safe to delete when:                                            ║
# ║    - test_agent_dispatcher.py updated to use TurnOrchestrator   ║
# ║    - test_context_files.py updated to use TurnOrchestrator      ║
# ║    - test_tools_toggle.py updated to use TurnOrchestrator       ║
# ║    - ChatService always uses injected TurnOrchestrator          ║
# ╚════════════════════════════════════════════════════════════════════╝
from __future__ import annotations

from src.providers.base import get_provider


def process_chat_turn(
    user_message: str,
    history: list,
    system_instruction: str | None = None,
    images: list[dict] | None = None,
    context_files: list[str] | None = None,
    provider_name: str | None = None,
    model_override: str | None = None,
    use_tools: bool = True,
) -> tuple[str, list[dict]]:
    """
    Handles a single conversational turn using the configured LLM provider.

    Delegates entirely to the active ``LLMProvider`` implementation.
    Mutates *history* in place — see the provider's own docstring for the
    exact format of history items.

    Args:
        user_message:       Plain text from the user.
        history:            Conversation history (mutated in place by the provider).
        system_instruction: Optional system-prompt override.
        images:             List of ``{"mime_type": str, "data": str}`` dicts.
        context_files:      File paths whose contents are prepended as context.
        provider_name:      Override which LLM provider to use for this turn.
                            ``None`` → read from ``settings.llm_provider``.
        model_override:     Override the model within the chosen provider.
                            ``None`` → provider uses its own default model.
        use_tools:          When ``False``, skip the agentic tool-calling loop
                            and make a single direct LLM call instead.
                            Default ``True`` preserves existing behaviour.

    Returns:
        ``(final_text, tool_logs)`` — see ``LLMProvider.process_chat_turn``.
    """
    provider = get_provider(
        provider_name=provider_name,
        model_override=model_override,
    )
    return provider.process_chat_turn(
        user_message=user_message,
        history=history,
        system_instruction=system_instruction,
        images=images,
        context_files=context_files,
        use_tools=use_tools,
    )
