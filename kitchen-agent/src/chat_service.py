"""
src/chat_service.py
===================
Business-logic layer for the chat endpoint.

Extracts the orchestration so that:
  1. The route handler is thin (HTTP concerns only).
  2. The service is independently testable (using the Repository Pattern).

Refactor — Decision 1: turn_id identity
-----------------------------------------
Each logical UI turn (one user message + one assistant response) is now
assigned a stable UUID at write time.  The UUID is stamped on:

  * The ``ui_history`` dict:  ``{"role": ..., "content": ..., "turn_id": ...}``
  * Every ``api_history`` item produced during that turn, via the
    ``turn_ids`` argument to ``dehydrate_history``.

This means that for any item in ``api_history_json`` we can do:

    api_items_for_turn = [i for i in api_items if i["turn_id"] == t]

...instead of walking the list and counting tool-call footprints.

The ``turn_id`` is generated once per turn here, in ``handle_turn``, and
propagated outward.  ``agent.process_chat_turn`` is not aware of turn_ids —
it still mutates the bare ``history`` list.  We reconstruct the turn_id→
index mapping after the agent returns by comparing the history length before
and after the call.

Context files UI persistence
-----------------------------
When ``context_files`` are provided to ``handle_turn`` their **basenames**
are stored on the user ``ui_messages`` entry under the key
``"context_files"``.  This allows the frontend to display which files were
attached to a message without needing to know the server's filesystem layout.

Example stored entry::

    {
        "role": "user",
        "content": "What materials?",
        "turn_id": "<uuid>",
        "context_files": ["kuchnia-kroki.md", "materials.md"]
    }

The key is omitted entirely when no context_files are attached so legacy
sessions remain clean.

Activity log (prompt_logger)
-----------------------------
After each turn we call ``log_turn(user_message, tool_logs, session_id, ...)``
so the Markdown activity log contains:
  * What the user asked
  * Which files the agent read / edited / created (with inline diffs)
  * The session context (short ID + title) for easy "Friday recall"
"""

import json
import uuid
from pathlib import Path
from typing import TYPE_CHECKING

import structlog

from prompt_logger import log_turn
from serializers import dehydrate_history, hydrate_history
from repositories import SessionRepository

if TYPE_CHECKING:
    from src.agent.turn_orchestrator import TurnOrchestrator

logger = structlog.get_logger(__name__)


def _make_title(ui_messages: list[dict]) -> str:
    """Derives a session title from the first user message (max 30 chars)."""
    first_content = next(
        (m["content"] for m in ui_messages if m.get("role") == "user"), "New Chat"
    )
    return first_content[:30] + "..." if len(first_content) > 30 else first_content


def _context_file_basenames(context_files: list[str] | None) -> list[str] | None:
    """
    Extract the basename of each context file path for UI display.

    The frontend sends relative names (e.g. ``"kuchnia-kroki.md"``), the
    backend resolves them to absolute paths (e.g.
    ``"/abs/path/data/kuchnia-kroki.md"``).  Either way we store only the
    basename so the UI can render the filename without knowing the server's
    filesystem layout.

    Returns ``None`` (not an empty list) when no files are provided so the
    key is omitted from the stored ui_message dict entirely.
    """
    if not context_files:
        return None
    basenames = [Path(fp).name for fp in context_files]
    return basenames if basenames else None


def _build_turn_ids_for_history(
    existing_turn_ids: list[str | None],
    history_before_len: int,
    history_after: list,
    user_turn_id: str,
    assistant_turn_id: str,
) -> list[str | None]:
    """
    Build the full parallel turn_ids list to pass to dehydrate_history.

    After ``process_chat_turn`` runs, ``history`` contains:
      [... existing items ..., user_content, (tool_calls...), assistant_text]

    The user_content item gets ``user_turn_id``.
    All tool_call and tool_response items produced by the agent, plus the
    final assistant text item, all belong to ``assistant_turn_id``.

    Args:
        existing_turn_ids:  turn_ids for items that were already in history
                            before this turn (may contain None for legacy rows).
        history_before_len: len(history) before process_chat_turn was called.
        history_after:      the mutated history list after the call.
        user_turn_id:       UUID for the user message.
        assistant_turn_id:  UUID for the assistant response (incl. tool turns).

    Returns:
        A list of the same length as ``history_after``.
    """
    result: list[str | None] = list(existing_turn_ids)

    # history_after[history_before_len] is the user Content appended by agent.
    # Everything after that is tool calls + assistant response — all under the
    # assistant turn id.
    for i in range(history_before_len, len(history_after)):
        if i == history_before_len:
            # First new item = user message
            result.append(user_turn_id)
        else:
            # Tool call/response pairs + final model text = assistant turn
            result.append(assistant_turn_id)

    return result


def _content_to_dict(item: object) -> dict:
    """
    Convert a Gemini ``types.Content`` object to a plain dict.

    Plain dicts are returned unchanged.  This is needed so the
    TurnOrchestrator (which expects ``list[dict]`` messages) can work with
    histories loaded from the DB that may contain ``types.Content`` objects.
    """
    try:
        from google.genai import types
    except ImportError:
        return item if isinstance(item, dict) else {}

    if not isinstance(item, types.Content):
        return item if isinstance(item, dict) else {}

    role = item.role
    if not item.parts:
        return {"role": role, "content": ""}

    part = item.parts[0]
    if part.text is not None:
        return {"role": role, "content": part.text}
    elif part.function_call is not None:
        return {
            "role": role,
            "content": [{
                "type": "tool_use",
                "id": part.function_call.id,
                "name": part.function_call.name,
                "input": dict(part.function_call.args) if part.function_call.args else {},
            }]
        }
    elif part.function_response is not None:
        return {
            "role": role,
            "content": [{
                "type": "tool_result",
                "tool_use_id": part.function_response.id,
                "content": part.function_response.response,
            }]
        }
    else:
        return {"role": role, "content": ""}


class ChatService:
    """Orchestrates a single chat turn end-to-end."""

    def __init__(
        self,
        session_repo: SessionRepository,
        turn_orchestrator: "TurnOrchestrator",
    ) -> None:
        self._session_repo = session_repo
        self._orchestrator = turn_orchestrator

    def handle_turn(
        self,
        session_id: str,
        user_message: str,
        system_prompt: str | None = None,
        images: list[dict] | None = None,
        context_files: list[str] | None = None,
        provider_name: str | None = None,
        model_override: str | None = None,
        use_tools: bool = True,
    ) -> tuple[str, list[dict]]:
        """
        Loads history, runs the agent, persists state, and returns the result.

        When a ``TurnOrchestrator`` is injected, the new path is used:
        the orchestrator manages the agentic loop via ``LLMProvider``.
        Otherwise, falls back to ``process_chat_turn()`` (legacy path).

        The ``system_prompt`` is now persisted alongside the history so that
        the LLM debug export (F04) can faithfully reconstruct the
        ``GenerateContentConfig`` envelope for each session.

        Turn IDs (Decision 1)
        ----------------------
        Two UUIDs are generated per call:
          - ``user_turn_id``      — stamps the user Content and the ui_messages
                                    user entry.
          - ``assistant_turn_id`` — stamps all api_history items produced by
                                    the agent (tool calls, tool responses, and
                                    the final text) plus the ui_messages
                                    assistant entry.

        Context files UI persistence
        ----------------------------
        When ``context_files`` are provided, the **basenames** of those paths
        are stored on the user ui_message under the key ``"context_files"``.
        This allows the frontend bubble to show which files were attached
        without exposing server filesystem paths.  The key is omitted entirely
        when no context_files are sent.

        Activity log
        ------------
        After the agent returns, ``log_turn`` is called with the full
        tool_logs list so the Markdown diary records which files were touched
        and what changed (inline diff for edit_file / create_file).
        """
        # ── 1. Load existing history from DB ─────────────────────────────────
        api_json, ui_json, _existing_system_prompt = self._session_repo.load_session(session_id)
        history = hydrate_history(api_json)
        ui_messages: list[dict] = json.loads(ui_json) if ui_json != "[]" else []

        # Load the existing api items to extract their turn_ids.
        existing_api_items: list[dict] = json.loads(api_json) if api_json not in ("", "[]") else []
        existing_turn_ids: list[str | None] = [
            item.get("turn_id") for item in existing_api_items
        ]

        # ── 2. Generate stable IDs for this turn ─────────────────────────────
        user_turn_id: str = str(uuid.uuid4())
        assistant_turn_id: str = str(uuid.uuid4())

        history_before_len = len(history)

        # ── 3. Record user message in UI state ────────────────────────────────
        # Include context_files basenames so the frontend bubble can show
        # which files were attached to this specific message.
        user_ui_entry: dict = {
            "role": "user",
            "content": user_message,
            "turn_id": user_turn_id,
        }
        file_basenames = _context_file_basenames(context_files)
        if file_basenames is not None:
            user_ui_entry["context_files"] = file_basenames

        ui_messages.append(user_ui_entry)

        # ── 4. Run the agentic loop ───────────────────────────────────────────
        logger.info("running_agent", session_id=session_id[:8], use_tools=use_tools)

        if not provider_name:
            # Orchestrator path: default provider via TurnOrchestrator
            final_text, tool_logs = self._run_with_orchestrator(
                history=history,
                user_message=user_message,
                system_prompt=system_prompt,
                images=images,
                context_files=context_files,
                use_tools=use_tools,
            )
        else:
            # Direct provider path: per-request provider/model override
            from src.providers.base import get_provider
            provider = get_provider(
                provider_name=provider_name,
                model_override=model_override,
            )
            raise NotImplementedError(
                "process_chat_turn removed. Use TurnOrchestrator.run() instead."
            )

        # ── 5. Record assistant response in UI state ──────────────────────────
        ui_messages.append({
            "role": "assistant",
            "content": final_text,
            "tools": tool_logs,
            "turn_id": assistant_turn_id,
        })

        # ── 6. Build the full parallel turn_ids list for dehydration ─────────
        turn_ids = _build_turn_ids_for_history(
            existing_turn_ids=existing_turn_ids,
            history_before_len=history_before_len,
            history_after=history,
            user_turn_id=user_turn_id,
            assistant_turn_id=assistant_turn_id,
        )

        # ── 7. Persist updated state ──────────────────────────────────────────
        # system_prompt is stored so the LLM debug export can reconstruct the
        # GenerateContentConfig envelope (F04).  If no system_prompt was passed
        # this turn, fall back to the one already stored.
        resolved_prompt = system_prompt if system_prompt is not None else _existing_system_prompt

        self._session_repo.save_session(
            session_id=session_id,
            title=_make_title(ui_messages),
            api_history_json=dehydrate_history(history, turn_ids=turn_ids),
            ui_history_json=json.dumps(ui_messages),
            system_prompt=resolved_prompt,
        )

        # ── 8. Write human-readable activity log ─────────────────────────────
        # Derive session title from the UI messages already computed above.
        session_title = _make_title(ui_messages)
        log_turn(
            user_message=user_message,
            tool_logs=tool_logs,
            session_id=session_id,
            session_title=session_title,
        )

        return final_text, tool_logs

    def _run_with_orchestrator(
        self,
        history: list,
        user_message: str,
        system_prompt: str | None,
        images: list[dict] | None,
        context_files: list[str] | None,
        use_tools: bool = True,
    ) -> tuple[str, list[dict]]:
        """
        Run a chat turn using the injected TurnOrchestrator.

        Converts history to dict format for the orchestrator, runs the turn,
        and appends the new history items (user message, tool calls, tool
        results, assistant response) to the history list.
        """
        from src.agent.turn_orchestrator import TurnInput

        # Convert history to dict format for the orchestrator
        session_messages = [_content_to_dict(item) for item in history]
        session = {"messages": session_messages}

        # Build TurnInput
        turn_input = TurnInput(
            user_message=user_message,
            system_prompt=system_prompt,
            images=images or [],
            context_files=context_files or [],
            use_tools=use_tools,
        )

        # Run orchestrator
        turn_output = self._orchestrator.run(session, turn_input)

        # Build tool_logs from tool_details
        tool_logs: list[dict] = []
        for detail in turn_output.tool_details:
            tool_logs.append({
                "name": detail.name,
                "args": detail.arguments,
                "result": {"content": detail.result_content} if not detail.is_error else {"error": detail.result_content},
            })

        # Append new history items for persistence
        # User message
        history.append({"role": "user", "content": user_message})

        # Tool call/response pairs
        for detail in turn_output.tool_details:
            # Tool call (assistant message with tool_use)
            history.append({
                "role": "assistant",
                "content": [{
                    "type": "tool_use",
                    "id": detail.id,
                    "name": detail.name,
                    "input": detail.arguments,
                }]
            })
            # Tool result (user message with tool_result)
            history.append({
                "role": "user",
                "content": [{
                    "type": "tool_result",
                    "tool_use_id": detail.id,
                    "content": detail.result_content,
                }]
            })

        # Assistant response
        history.append({
            "role": "assistant",
            "content": [{"type": "text", "text": turn_output.assistant_message}],
        })

        return turn_output.assistant_message, tool_logs
