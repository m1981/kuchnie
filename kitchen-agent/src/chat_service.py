"""
src/chat_service.py
===================
Business-logic layer for the chat endpoint.

Extracts the orchestration so that:
  1. The route handler is thin (HTTP concerns only).
  2. The service is independently testable (using the Repository Pattern).

Design
------
ChatService is a thin orchestrator with exactly five responsibilities:
  1. Load session state from repository
  2. Delegate turn execution to TurnOrchestrator
  3. Persist updated session state
  4. Log the turn
  5. Return structured response

Explicitly NOT responsible for:
  - Provider or model selection (DI layer)
  - Context assembly (ContextAssembler)
  - Tool execution (ToolExecutor)
  - Token counting logic (TokenBudget inside ContextAssembler)
  - History serialization format details (Serializers)

Context files UI persistence
-----------------------------
When ``context_files`` are provided, their **basenames** are stored on
the user ui_message under the key ``"context_files"``.  This allows the
frontend bubble to show which files were attached without exposing
server filesystem paths.  The key is omitted entirely when no files are sent.

Activity log (prompt_logger)
-----------------------------
After each turn we call ``log_turn(user_message, tool_logs, session_id, ...)``
so the Markdown activity log contains:
  * What the user asked
  * Which files the agent read / edited / created (with inline diffs)
  * The session context (short ID + title) for easy "Friday recall"
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Iterator

import structlog

from src.logger import bind_request_context, log_timing
from src.prompt_logger import log_turn
from src.repositories import SessionRepository
from src.serializers import dehydrate_history, hydrate_history

if TYPE_CHECKING:
    from src.agent.turn_orchestrator import TurnOrchestrator

log = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Request / Response dataclasses
# ---------------------------------------------------------------------------

@dataclass
class ChatTurnRequest:
    """
    Everything ChatService needs for one turn.
    """

    session_id: str
    user_message: str
    system_prompt: str | None = None
    images: list[dict] = field(default_factory=list)
    context_files: list[str] = field(default_factory=list)
    mode: str = "default"
    note_ids: list[str] = field(default_factory=list)
    file_ids: list[str] = field(default_factory=list)
    use_tools: bool = True
    # Provider routing — when set, overrides the server default for this turn.
    provider: str | None = None
    model: str | None = None


@dataclass
class ChatTurnResponse:
    """
    Everything callers need after a turn completes.
    """

    session_id: str
    assistant_message: str
    ui_history: list[dict]
    user_turn_id: str = ""
    assistant_turn_id: str = ""
    tool_calls_made: list[str] = field(default_factory=list)
    tool_logs: list[dict] = field(default_factory=list)
    tokens_used: dict = field(default_factory=dict)
    provider_name: str = ""
    model_name: str = ""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_title(ui_messages: list[dict]) -> str:
    """Derives a session title from the first user message (max 30 chars)."""
    first_content = next(
        (m["content"] for m in ui_messages if m.get("role") == "user"), "New Chat"
    )
    return first_content[:30] + "..." if len(first_content) > 30 else first_content


def _context_file_basenames(context_files: list[str] | None) -> list[str] | None:
    """
    Extract the basename of each context file path for UI display.

    Returns ``None`` (not an empty list) when no files are provided so the
    key is omitted from the stored ui_message dict entirely.
    """
    if not context_files:
        return None
    basenames = [Path(fp).name for fp in context_files]
    return basenames if basenames else None


# ---------------------------------------------------------------------------
# ChatService
# ---------------------------------------------------------------------------

class ChatService:
    """
    Thin orchestrator for one chat turn.

    Responsibilities (exactly these, no more):
      1. Load session state from repository
      2. Delegate turn execution to TurnOrchestrator
      3. Persist updated session state
      4. Log the turn
      5. Return structured response

    Explicitly NOT responsible for:
      - Provider or model selection (DI layer)
      - Context assembly (ContextAssembler)
      - Tool execution (ToolExecutor)
      - Token counting logic (TokenBudget inside ContextAssembler)
      - History serialization format details (Serializers)
    """

    def __init__(
        self,
        session_repo: SessionRepository,
        turn_orchestrator: TurnOrchestrator,
    ) -> None:
        self._sessions = session_repo
        self._orchestrator = turn_orchestrator
        self._log = structlog.get_logger(__name__)

    def handle_turn(self, request: ChatTurnRequest) -> ChatTurnResponse:
        """
        Execute one complete chat turn.
        Single code path — always through TurnOrchestrator.
        """
        self._log.info(
            "turn_started",
            user_message_preview=request.user_message[:60],
            mode=request.mode,
            use_tools=request.use_tools,
            req_provider=request.provider,
            req_model=request.model,
        )

        # ── 1. Load ───────────────────────────────────────────────────
        with log_timing(self._log, "turn_load_session"):
            api_history_json, ui_history_json, saved_system_prompt = (
                self._sessions.load_session(request.session_id)
            )

        api_history = hydrate_history(api_history_json)
        ui_history: list[dict] = json.loads(ui_history_json) if ui_history_json else []

        # System prompt: explicit request value wins, then saved, then None
        system_prompt = request.system_prompt or saved_system_prompt

        self._log.info(
            "turn_session_loaded",
            history_turns=len(api_history),
            has_system_prompt=bool(system_prompt),
        )

        # ── 2. Build session dict for orchestrator ────────────────────
        session = {
            "session_id": request.session_id,
            "messages": api_history,
            "system_prompt": system_prompt,
        }

        # ── 3. Build TurnInput ────────────────────────────────────────
        from src.agent.turn_orchestrator import TurnInput

        turn_input = TurnInput(
            user_message=request.user_message,
            mode=request.mode,
            images=request.images,
            context_files=request.context_files,
            note_ids=request.note_ids,
            file_ids=request.file_ids,
            use_tools=request.use_tools,
            system_prompt=system_prompt,
            provider=request.provider,
            model=request.model,
        )

        # ── 4. Execute turn ───────────────────────────────────────────
        bind_request_context(
            provider=request.provider or "(default)",
            model=request.model or "(default)",
        )

        with log_timing(self._log, "turn_orchestrator_complete") as timing:
            turn_output = self._orchestrator.run(
                session=session,
                turn_input=turn_input,
            )
        timing["provider"] = turn_output.provider_name
        timing["model"] = turn_output.model_name
        timing["response_length"] = len(turn_output.assistant_message)
        timing["tool_calls"] = len(turn_output.tool_calls_made)

        # ── 5. Build updated UI history ───────────────────────────────
        new_ui_history = self._build_ui_history(
            existing=ui_history,
            turn_output=turn_output,
            request=request,
        )

        title = _make_title(new_ui_history)

        # ── 6. Persist ─────────────────────────────────────────────────
        # dehydrate_history ensures every item has a turn_id (stamped by
        # the orchestrator or generated as a UUID fallback).
        self._sessions.save_session(
            session_id=request.session_id,
            title=title,
            api_history_json=dehydrate_history(turn_output.updated_api_history),
            ui_history_json=json.dumps(new_ui_history),
            system_prompt=system_prompt,
        )

        # ── 8. Log ────────────────────────────────────────────────────
        log_turn(
            user_message=request.user_message,
            tool_logs=turn_output.tool_logs,
            session_id=request.session_id,
            session_title=title,
        )

        log.debug(
            "turn_result",
            tool_calls_made=[t.name for t in turn_output.tool_calls_made],
            tool_logs_count=len(turn_output.tool_logs),
            response_length=len(turn_output.assistant_message),
            provider=turn_output.provider_name,
            model=turn_output.model_name,
        )

        return ChatTurnResponse(
            session_id=request.session_id,
            assistant_message=turn_output.assistant_message,
            ui_history=new_ui_history,
            user_turn_id=turn_output.user_turn_id,
            assistant_turn_id=turn_output.assistant_turn_id,
            tool_calls_made=[t.name for t in turn_output.tool_calls_made],
            tool_logs=turn_output.tool_logs,
            tokens_used=turn_output.tokens_used,
            provider_name=turn_output.provider_name,
            model_name=turn_output.model_name,
        )

    def stream_turn(self, request: ChatTurnRequest) -> Iterator[dict]:
        """
        Stream one complete chat turn.
        Yields event dicts for SSE serialization.
        """
        self._log.info(
            "stream_turn_started",
            user_message_preview=request.user_message[:60],
            mode=request.mode,
            use_tools=request.use_tools,
        )

        # ── 1. Load session ───────────────────────────────────────────
        api_history_json, ui_history_json, saved_system_prompt = (
            self._sessions.load_session(request.session_id)
        )
        api_history = hydrate_history(api_history_json)
        ui_history: list[dict] = json.loads(ui_history_json) if ui_history_json else []
        system_prompt = request.system_prompt or saved_system_prompt

        session = {
            "session_id": request.session_id,
            "messages": api_history,
            "system_prompt": system_prompt,
        }

        from src.agent.turn_orchestrator import TurnInput

        turn_input = TurnInput(
            user_message=request.user_message,
            mode=request.mode,
            images=request.images,
            context_files=request.context_files,
            note_ids=request.note_ids,
            file_ids=request.file_ids,
            use_tools=request.use_tools,
            system_prompt=system_prompt,
            provider=request.provider,
            model=request.model,
        )

        bind_request_context(
            provider=request.provider or "(default)",
            model=request.model or "(default)",
        )

        # ── 2. Stream from orchestrator ───────────────────────────────
        full_text = ""
        tool_calls_made: list[str] = []
        tool_logs: list[dict] = []
        provider_name = ""
        model_name = ""
        user_turn_id = ""
        assistant_turn_id = ""
        done_tool_details: list = []  # ToolCallDetail from done event

        for event in self._orchestrator.stream(session, turn_input):
            event_type = event.get("type")

            if event_type == "text_delta":
                full_text += event.get("content", "")
                yield {"type": "text", "content": event.get("content", "")}

            elif event_type == "tool_call":
                tool_calls_made.append(event.get("name", ""))
                yield {
                    "type": "tool_call",
                    "name": event.get("name"),
                    "args": event.get("args"),
                    "id": event.get("id"),
                }

            elif event_type == "tool_result":
                tool_logs.append({
                    "name": event.get("name"),
                    "args": event.get("args", {}),
                    "result": event.get("result", {}),
                })
                yield {
                    "type": "tool_result",
                    "name": event.get("name"),
                    "result": event.get("result"),
                    "id": event.get("id"),
                }

            elif event_type == "done":
                provider_name = event.get("provider", "")
                model_name = event.get("model", "")
                user_turn_id = event.get("user_turn_id", "")
                assistant_turn_id = event.get("assistant_turn_id", "")
                # Capture tool_details for history building (Fix #5)
                done_tool_details = event.get("tool_details", [])

        # ── 3. Persist ────────────────────────────────────────────────
        # Build updated API history with tool call/response pairs.
        # Before Fix #5: tool calls were lost in streaming history.
        # After Fix #5: tool_details from done event used to build proper history.
        updated_api_history = list(api_history)
        updated_api_history.append({"role": "user", "content": request.user_message})

        # Add tool call/response pairs from tool_details
        for detail in done_tool_details:
            updated_api_history.append({
                "role": "assistant",
                "content": "",
                "tool_calls": [{
                    "id": detail.id,
                    "name": detail.name,
                    "arguments": detail.arguments,
                }],
            })
            updated_api_history.append({
                "role": "tool",
                "tool_call_id": detail.id,
                "content": detail.result_content,
            })

        # Final assistant message
        updated_api_history.append({"role": "assistant", "content": full_text})

        new_ui_history = list(ui_history)
        new_ui_history.append({"role": "user", "content": request.user_message})
        new_ui_history.append({
            "role": "assistant",
            "content": full_text,
            "tools": tool_logs if tool_logs else None,
            "turn_id": assistant_turn_id,
            "provider": provider_name,
            "model": model_name,
        })

        title = _make_title(new_ui_history)

        self._sessions.save_session(
            session_id=request.session_id,
            title=title,
            api_history_json=dehydrate_history(updated_api_history),
            ui_history_json=json.dumps(new_ui_history),
            system_prompt=system_prompt,
        )

        # ── 4. Final done event ───────────────────────────────────────
        yield {
            "type": "done",
            "provider": provider_name,
            "model": model_name,
            "user_turn_id": user_turn_id,
            "assistant_turn_id": assistant_turn_id,
            "tool_calls_made": tool_calls_made,
            "tool_logs": tool_logs,
            "tokens_used": {},  # TODO: extract from stream
        }

        self._log.info(
            "stream_turn_completed",
            response_length=len(full_text),
            tool_calls=len(tool_calls_made),
            provider=provider_name,
            model=model_name,
        )

    def _build_ui_history(
        self,
        existing: list[dict],
        turn_output: "TurnOutput",
        request: ChatTurnRequest,
    ) -> list[dict]:
        """
        Append the new user + assistant turn to UI history.
        Preserves existing entries unchanged.
        """
        updated = list(existing)

        # User entry
        user_entry: dict = {
            "role": "user",
            "content": request.user_message,
            "turn_id": turn_output.user_turn_id,
        }
        file_basenames = _context_file_basenames(request.context_files)
        if file_basenames is not None:
            user_entry["context_files"] = file_basenames
        updated.append(user_entry)

        # Assistant entry
        assistant_entry: dict = {
            "role": "assistant",
            "content": turn_output.assistant_message,
            "turn_id": turn_output.assistant_turn_id,
            "tools": turn_output.tool_logs or [],
        }
        # Store actual provider/model used for this turn.
        if turn_output.provider_name:
            assistant_entry["provider"] = turn_output.provider_name
        if turn_output.model_name:
            assistant_entry["model"] = turn_output.model_name
        updated.append(assistant_entry)

        return updated
