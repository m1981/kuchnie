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
"""

import json
import uuid
import structlog

from agent import process_chat_turn
from prompt_logger import log_prompt
from serializers import dehydrate_history, hydrate_history
from repositories import SessionRepository

logger = structlog.get_logger(__name__)


def _make_title(ui_messages: list[dict]) -> str:
    """Derives a session title from the first user message (max 30 chars)."""
    first_content = next(
        (m["content"] for m in ui_messages if m.get("role") == "user"), "New Chat"
    )
    return first_content[:30] + "..." if len(first_content) > 30 else first_content


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


class ChatService:
    """Orchestrates a single chat turn end-to-end."""

    # Notice we inject the Protocol (Interface), not the SQLite class!
    def __init__(self, session_repo: SessionRepository) -> None:
        self._session_repo = session_repo

    def handle_turn(
        self,
        session_id: str,
        user_message: str,
        system_prompt: str | None = None,
        images: list[dict] | None = None,
        context_files: list[str] | None = None,
    ) -> tuple[str, list[dict]]:
        """
        Loads history, runs the agent, persists state, and returns the result.

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

        # ── 3. Record user message in UI state and prompt log ─────────────────
        ui_messages.append({
            "role": "user",
            "content": user_message,
            "turn_id": user_turn_id,
        })
        log_prompt(user_message)

        # ── 4. Run the agentic loop ───────────────────────────────────────────
        logger.info("running_agent", session_id=session_id[:8])
        final_text, tool_logs = process_chat_turn(
            user_message=user_message,
            history=history,
            system_instruction=system_prompt,
            images=images,
            context_files=context_files or None,
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

        return final_text, tool_logs
