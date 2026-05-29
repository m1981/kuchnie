"""
src/chat_service.py
===================
Business-logic layer for the chat endpoint.

Extracts the orchestration so that:
  1. The route handler is thin (HTTP concerns only).
  2. The service is independently testable (using the Repository Pattern).
"""

import json
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
        """
        # 1. Load existing history from DB.
        api_json, ui_json, _existing_system_prompt = self._session_repo.load_session(session_id)
        history = hydrate_history(api_json)
        ui_messages: list[dict] = json.loads(ui_json) if ui_json != "[]" else []

        # 2. Record user message in UI state and prompt log.
        ui_messages.append({"role": "user", "content": user_message})
        log_prompt(user_message)

        # 3. Run the agentic loop.
        logger.info("running_agent", session_id=session_id[:8])
        final_text, tool_logs = process_chat_turn(
            user_message=user_message,
            history=history,
            system_instruction=system_prompt,
            images=images,
            context_files=context_files or None,
        )

        # 4. Record assistant response in UI state.
        ui_messages.append(
            {"role": "assistant", "content": final_text, "tools": tool_logs}
        )

        # 5. Persist updated state — system_prompt is stored so the LLM debug
        #    export can reconstruct the GenerateContentConfig envelope (F04).
        #    If no system_prompt was passed this turn, fall back to the one
        #    already stored (preserves the prompt across turns within a session).
        resolved_prompt = system_prompt if system_prompt is not None else _existing_system_prompt

        self._session_repo.save_session(
            session_id=session_id,
            title=_make_title(ui_messages),
            api_history_json=dehydrate_history(history),
            ui_history_json=json.dumps(ui_messages),
            system_prompt=resolved_prompt,
        )

        return final_text, tool_logs
