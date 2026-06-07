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
  tool_results)``.  This is a *new* protocol (``LLMProvider``) distinct
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
``LLMProvider`` interface.

Public API
----------
``TurnInput``  — dataclass describing one user turn
``TurnOutput`` — dataclass describing the assistant's response
``TurnOrchestrator.run(session, turn_input)`` — execute one turn
``TurnOrchestrator.stream(session, turn_input)`` — stream one turn (future)
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Protocol

import structlog
from src.agent.context_assembler import AssembledContext, ContextAssembler
from src.agent.tool_executor import ToolCall, ToolExecutor, ToolResult
from src.logger import log_timing
from src.providers.base import LLMProvider
from src.providers.normalizer import NormalizedResponse, ResponseNormalizer


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class TurnInput:
    """Describes one user turn — what the orchestrator needs to proceed."""

    user_message: str
    mode: str = "default"
    system_prompt: str | None = None  # override system prompt (bypass PromptManager)
    note_ids: list[str] = field(default_factory=list)
    file_ids: list[str] = field(default_factory=list)
    images: list[dict] = field(default_factory=list)
    context_files: list[str] = field(default_factory=list)
    use_tools: bool = True
    # Provider routing — when set, overrides the server default for this turn.
    provider: str | None = None
    model: str | None = None


@dataclass
class ToolCallDetail:
    """Full detail of a tool call for history persistence."""

    id: str
    name: str
    arguments: dict
    result_content: str
    is_error: bool = False


@dataclass
class TurnOutput:
    """
    Everything produced by one complete turn execution.
    ChatService reads this — nothing else should need to.
    """
    assistant_message: str
    updated_api_history: list          # full history after turn, ready to persist
    user_turn_id: str                  # stable ID for the user message
    assistant_turn_id: str             # stable ID for the assistant message
    tool_calls_made: list[ToolCall]    # all tool calls in execution order
    tool_logs: list[dict]              # serializable tool log for UI + PromptLogger
    tokens_used: dict                  # {input, output, total} from provider
    provider_name: str = ""            # actual provider used (e.g. "gemini", "anthropic")
    model_name: str = ""               # actual model used (e.g. "gemini-2.5-flash")
    context_slots: dict = field(default_factory=dict)  # observability



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
    2. Call LLM (via LLMProvider)
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
        provider: LLMProvider,
        response_normalizer: ResponseNormalizer,
        provider_name: str = "gemini",
        max_tool_iterations: int = 10,
        tool_registry: Any | None = None,
    ) -> None:
        self._ctx = context_assembler
        self._tools = tool_executor
        self._provider = provider
        self._normalizer = response_normalizer
        self._provider_name = provider_name
        self._max_tool_iterations = max_tool_iterations
        self._tool_registry = tool_registry
        self._log = structlog.get_logger(__name__)

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
        # ── 1. Resolve provider for this turn ───────────────────────────
        if turn_input.provider:
            from src.providers.base import get_provider
            provider = get_provider(
                provider_name=turn_input.provider,
                model_override=turn_input.model,
            )
            provider_name = turn_input.provider
        else:
            provider = self._provider
            provider_name = self._provider_name

        actual_model = getattr(provider, "_model", "unknown")
        self._log.info(
            "orchestrator_provider_resolved",
            provider=provider_name,
            model=actual_model,
            override_used=bool(turn_input.provider),
        )

        # ── 2. Assemble context ─────────────────────────────────────────
        with log_timing(self._log, "orchestrator_context_assembled"):
            context = self._ctx.assemble(
                session=session,
                mode=turn_input.mode,
                user_message=turn_input.user_message,
                note_ids=turn_input.note_ids or None,
                file_ids=turn_input.file_ids or None,
            )

        # Override system prompt if provided in TurnInput
        if turn_input.system_prompt is not None:
            context.system_prompt = turn_input.system_prompt

        # Propagate images and context_files from TurnInput to context
        # so providers can access them via the LLMProvider interface.
        context.images = turn_input.images or []
        context.context_files = turn_input.context_files or []

        # Inject tool schemas from registry
        if self._tool_registry is not None and turn_input.use_tools:
            context.tool_schemas = self._tool_registry.schemas_for_provider(
                provider=provider_name,
            )

        self._log.info(
            "orchestrator_llm_call_start",
            provider=provider_name,
            model=actual_model,
            has_system_prompt=bool(context.system_prompt),
            has_images=bool(context.images),
            has_context_files=bool(context.context_files),
            tool_schemas_count=len(context.tool_schemas) if context.tool_schemas else 0,
            use_tools=turn_input.use_tools,
        )

        # ── 3. Call LLM ────────────────────────────────────────────────
        with log_timing(self._log, "orchestrator_llm_call_complete") as timing:
            raw_response = provider.complete(context)
            normalized = self._normalizer.normalize(raw_response, provider_name)
        timing["has_tool_calls"] = normalized.has_tool_calls

        # ── 4. Agentic tool loop ───────────────────────────────────────
        tool_calls_made: list[str] = []
        tool_details: list[ToolCallDetail] = []
        iterations = 0

        while normalized.has_tool_calls and turn_input.use_tools:
            iterations += 1
            if iterations > self._max_tool_iterations:
                raise MaxToolIterationsError(self._max_tool_iterations)

            self._log.info(
                "orchestrator_tool_iteration",
                iteration=iterations,
                tool_calls=[tc.name for tc in normalized.tool_calls],
            )

            # Execute tools
            with log_timing(self._log, "orchestrator_tools_executed") as timing:
                tool_results = self._tools.execute_all(normalized.tool_calls)
            timing["tools_count"] = len(tool_results)

            tool_calls_made.extend(
                tc.name for tc in normalized.tool_calls
            )

            # Record tool details for history persistence
            for tc, tr in zip(normalized.tool_calls, tool_results):
                tool_details.append(ToolCallDetail(
                    id=tc.id,
                    name=tc.name,
                    arguments=tc.arguments,
                    result_content=tr.content,
                    is_error=tr.is_error,
                ))

            # Feed results back to LLM
            self._log.info("orchestrator_feeding_tool_results_to_llm")
            raw_response = provider.complete_with_tools(
                context, normalized.tool_calls, tool_results,
            )
            normalized = self._normalizer.normalize(raw_response, provider_name)

        # 4. Build output
        # Build tool_logs (serializable) and tool_calls_made (ToolCall list)
        tool_calls_made_objects: list[ToolCall] = []
        tool_logs: list[dict] = []
        for detail in tool_details:
            tool_calls_made_objects.append(
                ToolCall(id=detail.id, name=detail.name, arguments=detail.arguments)
            )
            tool_logs.append({
                "name": detail.name,
                "args": detail.arguments,
                "result": ({"content": detail.result_content}
                           if not detail.is_error
                           else {"error": detail.result_content}),
            })

        # Build updated_api_history from session messages + new turns
        # Using provider-agnostic common format
        updated_api_history: list = list(session.get("messages", []))
        
        # User message
        updated_api_history.append({"role": "user", "content": turn_input.user_message})
        
        # Tool call/response pairs
        for detail in tool_details:
            # Assistant tool call message
            updated_api_history.append({
                "role": "assistant",
                "content": "",
                "tool_calls": [{
                    "id": detail.id,
                    "name": detail.name,
                    "arguments": detail.arguments,
                }],
            })
            # Tool response message
            updated_api_history.append({
                "role": "tool",
                "tool_call_id": detail.id,
                "content": detail.result_content,
            })
        
        # Assistant response
        updated_api_history.append({
            "role": "assistant",
            "content": normalized.text,
        })

        # Generate stable turn IDs
        user_turn_id = str(uuid.uuid4())
        assistant_turn_id = str(uuid.uuid4())

        # Capture actual model used — provider._model holds the resolved value.
        actual_model = getattr(provider, "_model", "") or ""

        return TurnOutput(
            assistant_message=normalized.text,
            updated_api_history=updated_api_history,
            user_turn_id=user_turn_id,
            assistant_turn_id=assistant_turn_id,
            tool_calls_made=tool_calls_made_objects,
            tool_logs=tool_logs,
            tokens_used=normalized.usage,
            provider_name=provider_name,
            model_name=actual_model,
            context_slots=context.slots_used,
        )
