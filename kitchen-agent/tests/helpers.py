"""
tests/helpers.py
================
Shared test doubles used across unit, contract, and integration tests.

Keep this module minimal — only fakes that are genuinely shared between
multiple test files belong here.  Single-use fakes stay in their test file.
"""
from __future__ import annotations

from src.agent.context_assembler import ContextSlot
from src.agent.turn_orchestrator import ToolCall, ToolCallDetail, TurnInput, TurnOutput


class FakeOrchestrator:
    """
    Minimal fake TurnOrchestrator for ChatService and integration tests.
    Records calls. Returns controllable output.
    """

    def __init__(
        self,
        text: str = "response text",
        tool_details: list[ToolCallDetail] | None = None,
    ) -> None:
        self._text = text
        self._tool_details = tool_details or []
        self.run_call_count = 0
        self.last_turn_input: TurnInput | None = None
        self.last_session: dict | None = None

    def run(self, session: dict, turn_input: TurnInput) -> TurnOutput:
        self.run_call_count += 1
        self.last_turn_input = turn_input
        self.last_session = session

        # Build tool_logs and tool_calls_made from tool_details
        tool_logs = []
        tool_calls_made = []
        for d in self._tool_details:
            tool_calls_made.append(
                ToolCall(id=d.id, name=d.name, arguments=d.arguments)
            )
            tool_logs.append({
                "name": d.name,
                "args": d.arguments,
                "result": {"content": d.result_content} if not d.is_error else {"error": d.result_content},
            })

        # Build updated_api_history
        updated_api_history = list(session.get("messages", []))
        updated_api_history.append({"role": "user", "content": turn_input.user_message})
        for d in self._tool_details:
            updated_api_history.append({
                "role": "assistant",
                "content": [{"type": "tool_use", "id": d.id, "name": d.name, "input": d.arguments}],
            })
            updated_api_history.append({
                "role": "user",
                "content": [{"type": "tool_result", "tool_use_id": d.id, "content": d.result_content}],
            })
        updated_api_history.append({
            "role": "assistant",
            "content": [{"type": "text", "text": self._text}],
        })

        return TurnOutput(
            assistant_message=self._text,
            updated_api_history=updated_api_history,
            user_turn_id="test-user-turn-id",
            assistant_turn_id="test-assistant-turn-id",
            tool_calls_made=tool_calls_made,
            tool_logs=tool_logs,
            tokens_used={"input": 10, "output": 5, "total": 15},
            context_slots={ContextSlot.SYSTEM_PROMPT: 20},
        )
