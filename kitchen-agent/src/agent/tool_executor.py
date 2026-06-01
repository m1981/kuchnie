"""
src/agent/tool_executor.py
===========================
ToolExecutor — isolated, safe tool execution.

Single responsibility: resolve a tool handler from a registry, execute it,
and return a normalized result.  Errors are caught and wrapped so the LLM
sees them (as a tool error result) instead of the application crashing.

Design decisions
----------------
* **Sync-first**: Current tool handlers are synchronous functions.  The
  executor runs them directly (no ``asyncio.to_thread``) for simplicity
  and determinism.  When async handlers are added, the executor can be
  extended with ``asyncio.iscoroutinefunction`` detection.
* **No provider knowledge**: The executor does not know about LLM providers,
  sessions, or history.  It only knows about tool names and registries.
* **Error wrapping**: Any exception from a tool handler is caught and
  returned as a ``ToolResult(is_error=True)``.  The caller (provider
  agentic loop) decides what to do with the error.

Phase 2 scope
-------------
Initially used by the provider agentic loops (GeminiProvider and
AnthropicProvider) for tool dispatch.  The providers previously called
``FUNCTION_MAP[tool_name](**args)`` inline; they now delegate to
ToolExecutor for the same behavior.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ToolCall:
    """Normalized tool call — provider-agnostic."""

    id: str
    name: str
    arguments: dict


@dataclass
class ToolResult:
    """Normalized tool result — provider-agnostic."""

    tool_call_id: str
    name: str
    content: str
    is_error: bool = False


# ---------------------------------------------------------------------------
# Registry protocol — what ToolExecutor needs from a registry
# ---------------------------------------------------------------------------

class ToolRegistryProtocol(Protocol):
    """
    Minimal interface the ToolExecutor requires from a registry.

    This decouples ToolExecutor from the concrete ToolRegistry class
    and allows test fakes to be passed in easily.
    """

    def get_handler(self, name: str) -> Any: ...


# ---------------------------------------------------------------------------
# Executor
# ---------------------------------------------------------------------------

class ToolExecutor:
    """
    Execute tool calls safely.

    - Resolves handler from registry
    - Catches and wraps errors (LLM should see error, not crash)
    - Does NOT know about providers or sessions
    """

    def __init__(self, registry: ToolRegistryProtocol) -> None:
        self._registry = registry

    def execute_all(
        self,
        tool_calls: list[ToolCall],
    ) -> list[ToolResult]:
        """
        Execute all tool calls and return their results.

        Current implementation runs synchronously (matching the
        synchronous tool handlers in the codebase).  Each call
        is executed sequentially for determinism.

        Args:
            tool_calls: List of ToolCall objects to execute.

        Returns:
            List of ToolResult objects — one per tool call.
            Errors are wrapped, never raised.
        """
        return [self._execute_one(tc) for tc in tool_calls]

    def _execute_one(self, tool_call: ToolCall) -> ToolResult:
        try:
            handler = self._registry.get_handler(tool_call.name)
            result = handler(**tool_call.arguments)

            return ToolResult(
                tool_call_id=tool_call.id,
                name=tool_call.name,
                content=str(result),
                is_error=False,
            )

        except Exception as e:
            # Never crash the turn — return structured error to LLM
            return ToolResult(
                tool_call_id=tool_call.id,
                name=tool_call.name,
                content=f"Tool error: {type(e).__name__}: {e}",
                is_error=True,
            )
