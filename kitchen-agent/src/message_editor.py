"""
src/message_editor.py
=====================
Business-logic layer for chat message editing and deletion.

Responsibilities
----------------
* Edit the *content* of any message in a session (user or assistant) while
  keeping both ``api_history_json`` and ``ui_history_json`` in sync.
* Delete a single message (with optional paired-turn removal).
* Truncate the tail of a conversation by N complete turn-pairs.
* Update the session-scoped system-prompt override stored in the DB.

Design decisions
----------------
* ``api_history_json`` stores the Gemini SDK wire format as serialised by
  ``src/serializers.py`` — a flat list of dicts with a ``type`` key
  (``"text"``, ``"function_call"``, ``"function_response"``).

* ``ui_history_json`` stores the display-layer list:
  ``[{"role": "user"|"assistant", "content": str, "tools": [...]}]``.

* The two lists are **not** guaranteed to be the same length because tool
  calls insert extra turns in ``api_history`` (one ``function_call`` turn +
  one ``function_response`` turn per tool invocation, before the final model
  text turn).

* The mapping strategy is:
    - For ``ui_history``:  index directly by ``ui_index``.
    - For ``api_history``: locate the *N-th occurrence* of the role-matching
      entry that carries ``type="text"`` and matches the content.  This is
      unambiguous for user turns (always ``type="text"``).  For assistant turns
      we target the model ``type="text"`` text turn.

* All public methods raise ``EditError`` on validation failure so callers can
  map errors to appropriate HTTP status codes.
"""

from __future__ import annotations

import json
from typing import Any

import structlog

from src.repositories import SessionRepository

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Domain exception
# ---------------------------------------------------------------------------

class EditError(Exception):
    """Raised when a message-editing operation cannot be completed."""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _load_histories(
    repo: SessionRepository,
    session_id: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str | None]:
    """
    Load and parse both histories + system prompt from the repository.

    Returns:
        (api_items, ui_messages, system_prompt)

    Raises:
        EditError: when the session does not exist.
    """
    api_json, ui_json, system_prompt = repo.load_session(session_id)
    # load_session returns "[]" for missing sessions, not a real error.
    # Detect by checking if the session actually exists by listing — simpler
    # approach: if both return default "[]" AND we can't find it in list.
    # But repositories don't expose a direct exists() — use the returned data.
    # Convention: load_session returns ("[]", "[]", None) for unknown IDs.
    # We treat a session as non-existent when both json strings are default.
    if api_json == "[]" and ui_json == "[]":
        # Double-check via list (avoids false positives for empty sessions).
        # list_sessions includes archived, so use include_archived=True.
        sessions = repo.list_sessions(include_archived=True)
        if not any(s["id"] == session_id for s in sessions):
            raise EditError(f"Session not found: {session_id}")

    api_items: list[dict[str, Any]] = json.loads(api_json) if api_json else []
    ui_messages: list[dict[str, Any]] = json.loads(ui_json) if ui_json else []
    return api_items, ui_messages, system_prompt


def _save_histories(
    repo: SessionRepository,
    session_id: str,
    api_items: list[dict[str, Any]],
    ui_messages: list[dict[str, Any]],
    system_prompt: str | None,
) -> None:
    """Persist both histories back to the repository."""
    # We need the title — derive it from ui_messages or keep existing.
    title = next(
        (m["content"][:30] + ("..." if len(m["content"]) > 30 else "")
         for m in ui_messages if m.get("role") == "user"),
        "Chat",
    )
    repo.save_session(
        session_id=session_id,
        title=title,
        api_history_json=json.dumps(api_items),
        ui_history_json=json.dumps(ui_messages),
        system_prompt=system_prompt,
    )


def _api_role_for_ui_role(ui_role: str) -> str:
    """Maps ui role ('user'|'assistant') → api role ('user'|'model')."""
    return "model" if ui_role == "assistant" else "user"


def _find_api_index_for_ui_index(
    api_items: list[dict[str, Any]],
    ui_messages: list[dict[str, Any]],
    ui_index: int,
) -> int | None:
    """
    Locate the position in ``api_items`` that corresponds to ``ui_messages[ui_index]``.

    Strategy:
    - Walk ``ui_messages`` from 0 to ``ui_index``.
    - For each UI message, count how many api items we need to consume:
        * A user turn = 1 api text item.
        * An assistant turn = M function_call/response pairs + 1 text item.
    - The api index is the running pointer into api_items.

    Returns None when mapping cannot be determined (empty api, mismatch).
    """
    if not api_items:
        return None

    api_ptr = 0

    for i, ui_msg in enumerate(ui_messages):
        if api_ptr >= len(api_items):
            return None

        if i == ui_index:
            # We want the TEXT item at api_ptr for this UI slot.
            # For user turns: should already be text.
            # For assistant turns: skip any leading function_call/response pairs.
            while api_ptr < len(api_items):
                item = api_items[api_ptr]
                expected_role = _api_role_for_ui_role(ui_msg["role"])
                if item["role"] == expected_role and item.get("type") == "text":
                    return api_ptr
                api_ptr += 1
            return None

        # Advance past this UI message's api footprint.
        ui_role = ui_msg["role"]
        if ui_role == "user":
            # One text item.
            api_ptr += 1
        else:
            # assistant: skip function_call + function_response pairs, then text.
            tools = ui_msg.get("tools") or []
            api_ptr += len(tools) * 2  # each tool: 1 function_call + 1 function_response
            api_ptr += 1  # final text turn

    return None


def _api_footprint_start_and_length(
    api_items: list[dict[str, Any]],
    ui_messages: list[dict[str, Any]],
    ui_index: int,
) -> tuple[int, int]:
    """
    Returns (start_in_api, count_of_api_items) that belong to ui_messages[ui_index].

    For a user message: (ptr, 1).
    For an assistant message with K tools: (ptr, 2*K + 1).
    """
    if not api_items:
        return 0, 0

    api_ptr = 0
    for i, ui_msg in enumerate(ui_messages):
        if api_ptr >= len(api_items):
            return api_ptr, 0

        ui_role = ui_msg["role"]
        tools = ui_msg.get("tools") or []

        if ui_role == "user":
            count = 1
        else:
            count = len(tools) * 2 + 1

        if i == ui_index:
            return api_ptr, count

        api_ptr += count

    return api_ptr, 0


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class MessageEditService:
    """
    Manages editing and deletion of chat messages within a session.

    All methods are synchronous and safe to call from ``run_in_executor``.
    """

    def __init__(self, session_repo: SessionRepository) -> None:
        self._repo = session_repo

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def edit_message(
        self,
        session_id: str,
        ui_index: int,
        new_content: str,
    ) -> None:
        """
        Replace the *content* of ``ui_messages[ui_index]`` and sync api_history.

        Args:
            session_id:  Target session UUID.
            ui_index:    Zero-based position in ``ui_history_json``.
            new_content: Replacement text (must be non-empty after strip).

        Raises:
            EditError: on validation failure or session not found.
        """
        if ui_index < 0:
            raise EditError(f"Invalid index {ui_index}: must be >= 0.")
        if not new_content.strip():
            raise EditError("new_content must not be empty or blank.")

        api_items, ui_messages, system_prompt = _load_histories(self._repo, session_id)

        if ui_index >= len(ui_messages):
            raise EditError(
                f"index {ui_index} is out of range (session has {len(ui_messages)} messages)."
            )

        # Update UI layer.
        ui_messages[ui_index]["content"] = new_content

        # Sync API layer — find the matching text item.
        api_idx = _find_api_index_for_ui_index(api_items, ui_messages, ui_index)
        if api_idx is not None and api_idx < len(api_items):
            api_items[api_idx]["data"] = new_content

        _save_histories(self._repo, session_id, api_items, ui_messages, system_prompt)
        logger.info(
            "message_edited",
            session_id=session_id[:8],
            ui_index=ui_index,
            preview=new_content[:40],
        )

    def delete_message(
        self,
        session_id: str,
        ui_index: int,
        delete_pair: bool = False,
    ) -> None:
        """
        Remove ``ui_messages[ui_index]`` and optionally its paired next message.

        When ``delete_pair=True`` and ``ui_index`` points to a user message,
        the following assistant message is also removed (if it exists).

        Both ``ui_history`` and ``api_history`` are kept in sync.

        Raises:
            EditError: on validation failure or session not found.
        """
        if ui_index < 0:
            raise EditError(f"Invalid index {ui_index}: must be >= 0.")

        api_items, ui_messages, system_prompt = _load_histories(self._repo, session_id)

        if ui_index >= len(ui_messages):
            raise EditError(
                f"index {ui_index} is out of range (session has {len(ui_messages)} messages)."
            )

        # Determine indices to delete (in reverse order so earlier deletions
        # don't shift the positions of later ones).
        ui_indices_to_delete = [ui_index]
        if delete_pair and ui_index + 1 < len(ui_messages):
            ui_indices_to_delete.append(ui_index + 1)

        # Collect api footprints for all ui items to remove (before any mutation).
        api_ranges: list[tuple[int, int]] = []
        for idx in ui_indices_to_delete:
            start, length = _api_footprint_start_and_length(api_items, ui_messages, idx)
            if length > 0:
                api_ranges.append((start, length))

        # Remove from ui_messages (high-to-low to preserve indices).
        for idx in sorted(ui_indices_to_delete, reverse=True):
            ui_messages.pop(idx)

        # Remove from api_items (high-to-low).
        for start, length in sorted(api_ranges, key=lambda r: r[0], reverse=True):
            del api_items[start : start + length]

        _save_histories(self._repo, session_id, api_items, ui_messages, system_prompt)
        logger.info(
            "message_deleted",
            session_id=session_id[:8],
            ui_index=ui_index,
            delete_pair=delete_pair,
        )

    def truncate_turns(
        self,
        session_id: str,
        n: int,
    ) -> None:
        """
        Remove the last ``n`` complete turn-pairs (user + assistant) from the tail.

        A "turn pair" is one user message + one assistant message.  If the
        session ends with a lone user message (no assistant reply yet), it is
        counted as a half-pair and removed as part of the first ``n=1``.

        Raises:
            EditError: when ``n < 1``, session not found, or ``n`` exceeds
                       the available number of pairs.
        """
        if n < 1:
            raise EditError("n must be >= 1.")

        api_items, ui_messages, system_prompt = _load_histories(self._repo, session_id)

        # Count complete pairs from the tail.
        total = len(ui_messages)
        # Each pair is 2 items; n pairs = 2*n items from the tail.
        items_to_remove = n * 2
        if items_to_remove > total:
            raise EditError(
                f"n={n} exceeds the number of available turn pairs "
                f"(session has {total} messages = {total // 2} complete pairs)."
            )

        # Determine which ui_indices are being removed.
        first_ui_to_remove = total - items_to_remove

        # Find the corresponding api start position.
        api_start, _ = _api_footprint_start_and_length(
            api_items, ui_messages, first_ui_to_remove
        )

        # Truncate both lists.
        del ui_messages[first_ui_to_remove:]
        del api_items[api_start:]

        _save_histories(self._repo, session_id, api_items, ui_messages, system_prompt)
        logger.info(
            "turns_truncated",
            session_id=session_id[:8],
            n=n,
            remaining_messages=len(ui_messages),
        )

    def update_system_prompt(
        self,
        session_id: str,
        system_prompt: str,
    ) -> None:
        """
        Overwrite the session-scoped system prompt stored in the DB.

        This affects the *next* call to ``ChatService.handle_turn`` for this
        session — the new value is passed directly to the LLM instead of the
        PromptManager-resolved prompt.

        An empty string is valid (clears any override) so that the next turn
        falls back to the PromptManager default.

        Raises:
            EditError: when the session does not exist.
        """
        api_items, ui_messages, _old_prompt = _load_histories(self._repo, session_id)
        _save_histories(self._repo, session_id, api_items, ui_messages, system_prompt)
        logger.info(
            "system_prompt_updated",
            session_id=session_id[:8],
            chars=len(system_prompt),
        )
