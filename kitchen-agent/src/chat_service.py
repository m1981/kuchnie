"""
src/chat_service.py
===================
Business-logic layer for the chat endpoint.

Extracts the seven-step orchestration that previously lived inside the FastAPI
route handler so that:

  1. The route handler is thin (HTTP concerns only).
  2. The service is independently testable without an HTTP client.
  3. The service can be called from tests or future CLI tools directly.

All methods are synchronous — the FastAPI handler runs them inside
``asyncio.run_in_executor`` so the event loop is never blocked.
"""

import json
import logging

from agent import process_chat_turn
from db import DatabaseManager
from prompt_logger import log_prompt
from serializers import dehydrate_history, hydrate_history

logger = logging.getLogger(__name__)


def _make_title(ui_messages: list[dict]) -> str:
    """Derives a session title from the first user message (max 30 chars)."""
    first_content = next(
        (m["content"] for m in ui_messages if m.get("role") == "user"), "New Chat"
    )
    return first_content[:30] + "..." if len(first_content) > 30 else first_content


class ChatService:
    """Orchestrates a single chat turn end-to-end."""

    def __init__(self, db: DatabaseManager) -> None:
        self._db = db

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

        Args:
            session_id:    UUID string identifying the session.
            user_message:  Raw text from the user.
            system_prompt: Optional system-instruction override.
            images:        List of ``{mime_type, data}`` base64 image dicts.
            context_files: Paths injected as context before the user message.

        Returns:
            ``(final_text, tool_logs)`` — same shape as ``process_chat_turn``.
        """
        # 1. Load existing history from DB.
        api_json, ui_json = self._db.load_session(session_id)
        history = hydrate_history(api_json)
        ui_messages: list[dict] = json.loads(ui_json) if ui_json != "[]" else []

        # 2. Record user message in UI state and prompt log.
        ui_messages.append({"role": "user", "content": user_message})
        log_prompt(user_message)

        # 3. Run the agentic loop.
        logger.info("ChatService: running agent for session %s", session_id[:8])
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

        # 5. Persist updated state.
        self._db.save_session(
            session_id=session_id,
            title=_make_title(ui_messages),
            api_history_json=dehydrate_history(history),
            ui_history_json=json.dumps(ui_messages),
        )

        return final_text, tool_logs
