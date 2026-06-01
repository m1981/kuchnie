"""
src/agent/turn_orchestrator.py
================================
TurnOrchestrator — manages one complete chat turn lifecycle.

Before this module, the turn lifecycle (context assembly → LLM call → tool
loop → response normalization) was embedded inside ``process_chat_turn`` in
``src/agent/__init__.py``.  This made it impossible to test the orchestration
logic in isolation or swap providers without touching the agent code.

The TurnOrchestrator composes three already-extracted components:
  - **ContextAssembler** (Phase 3) — builds the context window
  - **ToolExecutor** (Phase 2) — runs tools safely
  - **ResponseNormalizer** (Phase 1) — unifies provider response shapes

Design decisions
----------------
* **Provider protocol**: The orchestrator requires a provider that exposes
  ``complete(context)`` and ``complete_with_tools(context, tool_calls,
  tool_results)``.  This is a *new* protocol (``LLMCompleter``) distinct
  from the existing ``LLMProvider`` protocol in ``providers/base.py``.
  Existing providers can be adapted to this protocol later; the orchestrator
  does not depend on the old ``process_chat_turn`` interface.
* **Max tool iterations**: A hard cap prevents infinite tool loops when the
  LLM keeps requesting tool calls.  The default is 10; override via
  constructor.
* **Sync tool execution**: Current tool handlers are synchronous.  The
  orchestrator calls ``ToolExecutor.execute_all`` directly (no async).
  When async handlers arrive, the executor can be extended independently.
* **No persistence**: The orchestrator does NOT save sessions, log prompts,
  or count global tokens.  Those are ChatService responsibilities.

Phase 4 scope
-------------
TurnOrchestrator is introduced as a standalone component.  It is NOT yet
wired into ChatService or the existing ``process_chat_turn`` function.
That wiring will happen in a later phase once providers expose the
``LLMCompleter`` interface.

Public API
----------
``TurnInput``  — dataclass describing one user turn
``TurnOutput`` — dataclass describing the assistant's response
``TurnOrchestrator.run(session, turn_input)`` — execute one turn
``TurnOrchestrator.stream(session, turn_input)`` — stream one turn (future)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from src.agent.context_assembler import AssembledContext, ContextAssembler
from src.agent.tool_executor import ToolCall, ToolExecutor, ToolResult
from src.providers.normalizer import NormalizedResponse, ResponseNormalizer


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class TurnInput:
    """Describes one user turn — what the orchestrator needs to proceed."""

    user_message: str
    mode: str = "default"
    note_ids: list[str] = field(default_factory=list)
    file_ids: list[str] = field(default_factory=list)


@dataclass
class TurnOutput:
    """The orchestrator's result — what ChatService receives."""

    assistant_message: str
    tool_calls_made: list[str]
    tokens_used: dict  # {input, output, total}
    context_slots: dict  # observability: which slots consumed tokens


# ---------------------------------------------------------------------------
# Provider protocol — what the orchestrator needs from an LLM provider
# ---------------------------------------------------------------------------

class LLMCompleter(Protocol):
    """
    Minimal interface the TurnOrchestrator requires from an LLM provider.

    This is distinct from the existing ``LLMProvider`` protocol in
    ``providers/base.py`` which exposes ``process_chat_turn`` (the full
    agentic loop).  ``LLMCompleter`` exposes only the raw API call —
    the orchestrator owns the tool loop.
    """

    def complete(self, context: AssembledContext) -> Any:
        """Send a context to the LLM and return the raw SDK response."""
        ...

    def complete_with_tools(
        self,
        context: AssembledContext,
        tool_calls: list[ToolCall],
        tool_results: list[ToolResult],
    ) -> Any:
        """Send context + tool results to the LLM and return the raw SDK response."""
        ...


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class MaxToolIterationsError(Exception):
    """Raised when the tool loop exceeds the maximum allowed iterations."""

    def __init__(self, max_iterations: int) -> None:
        self.max_iterations = max_iterations
        super().__init__(
            f"Tool loop exceeded {max_iterations} iterations. "
            "The LLM may be stuck in a tool-calling cycle."
        )


# ---------------------------------------------------------------------------
# TurnOrchestrator
# ---------------------------------------------------------------------------

class TurnOrchestrator:
    """
    Manages one complete chat turn lifecycle.

    Lifecycle:
    1. Assemble context (via ContextAssembler)
    2. Call LLM (via LLMCompleter)
    3. Normalize response (via ResponseNormalizer)
    4. If tool calls: execute tools, feed results back, repeat
    5. Return TurnOutput

    Does NOT: persist sessions, log prompts, count global tokens.
    Those are ChatService responsibilities.
    """

    def __init__(
        self,
        context_assembler: ContextAssembler,
        tool_executor: ToolExecutor,
        provider: LLMCompleter,
        response_normalizer: ResponseNormalizer,
        provider_name: str = "gemini",
        max_tool_iterations: int = 10,
    ) -> None:
        self._ctx = context_assembler
        self._tools = tool_executor
        self._provider = provider
        self._normalizer = response_normalizer
        self._provider_name = provider_name
        self._max_tool_iterations = max_tool_iterations

    def run(
        self,
        session: dict,
        turn_input: TurnInput,
    ) -> TurnOutput:
        """
        Execute one complete chat turn.

        Args:
            session:     Session-like dict with a ``messages`` key.
            turn_input:  Describes the user's turn.

        Returns:
            TurnOutput with assistant message, tool calls made,
            token usage, and context slot observability.

        Raises:
            MaxToolIterationsError: if the tool loop exceeds the cap.
        """
        # 1. Assemble context
        context = self._ctx.assemble(
            session=session,
            mode=turn_input.mode,
            user_message=turn_input.user_message,
            note_ids=turn_input.note_ids or None,
            file_ids=turn_input.file_ids or None,
        )

        # 2. Call LLM
        raw_response = self._provider.complete(context)
        normalized = self._normalizer.normalize(raw_response, self._provider_name)

        # 3. Agentic tool loop
        tool_calls_made: list[str] = []
        iterations = 0

        while normalized.has_tool_calls:
            iterations += 1
            if iterations > self._max_tool_iterations:
                raise MaxToolIterationsError(self._max_tool_iterations)

            # Execute tools
            tool_results = self._tools.execute_all(normalized.tool_calls)
            tool_calls_made.extend(
                tc.name for tc in normalized.tool_calls
            )

            # Feed results back to LLM
            raw_response = self._provider.complete_with_tools(
                context, normalized.tool_calls, tool_results,
            )
            normalized = self._normalizer.normalize(raw_response, self._provider_name)

        # 4. Build output
        return TurnOutput(
            assistant_message=normalized.text,
            tool_calls_made=tool_calls_made,
            tokens_used=normalized.usage,
            context_slots=context.slots_used,
        )
