"""
src/db.py
=========
SQLite persistence layer for chat sessions.

Design notes
------------
* ``_get_connection()`` opens a *new* connection on every call so each request
  thread gets its own connection — safe for FastAPI's thread-pool executor.
* ``check_same_thread=False`` is intentionally set; the single-connection-per-
  call pattern above makes it safe (no connection is shared across threads).
* All public methods are intentionally synchronous.  The FastAPI chat handler
  runs them inside an executor so they never block the event loop.
"""

import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

from src.config import settings
from src.exporter import export_session_to_markdown


class DatabaseManager:
    def __init__(self, db_path: Path | str | None = None) -> None:
        self.db_path = str(db_path) if db_path is not None else str(settings.db_path)
        # Ensure parent directory exists before creating the DB file.
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    # ── Connection ────────────────────────────────────────────────────────────

    def _get_connection(self) -> sqlite3.Connection:
        """Opens a new SQLite connection (rows returned as dicts)."""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    # ── Schema ────────────────────────────────────────────────────────────────

    def _init_db(self) -> None:
        """Creates all tables if they do not already exist."""
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id               TEXT PRIMARY KEY,
                    title            TEXT,
                    api_history_json TEXT,
                    ui_history_json  TEXT,
                    updated_at       TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS notes (
                    id            TEXT PRIMARY KEY,
                    session_id    TEXT NOT NULL,
                    selected_text TEXT NOT NULL,
                    note          TEXT NOT NULL DEFAULT '',
                    source_role   TEXT NOT NULL,
                    created_at    TIMESTAMP NOT NULL
                )
                """
            )
            conn.commit()

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def save_session(
        self,
        session_id: str,
        title: str,
        api_history_json: str,
        ui_history_json: str,
    ) -> None:
        """Inserts a new session or updates an existing one (upsert)."""
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO sessions (id, title, api_history_json, ui_history_json, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    title            = excluded.title,
                    api_history_json = excluded.api_history_json,
                    ui_history_json  = excluded.ui_history_json,
                    updated_at       = excluded.updated_at
                """,
                (session_id, title, api_history_json, ui_history_json, datetime.now()),
            )
            conn.commit()

    def load_session(self, session_id: str) -> tuple[str, str]:
        """
        Returns ``(api_history_json, ui_history_json)`` for *session_id*.

        Returns ``("[]", "[]")`` when the session does not exist so callers
        never have to handle ``None``.
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT api_history_json, ui_history_json FROM sessions WHERE id = ?",
                (session_id,),
            )
            row = cursor.fetchone()
        if row:
            return row["api_history_json"], row["ui_history_json"]
        return "[]", "[]"

    def list_sessions(self) -> list[dict]:
        """Returns all sessions ordered by most-recently updated."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT id, title, updated_at FROM sessions ORDER BY updated_at DESC"
            )
            return [dict(row) for row in cursor.fetchall()]

    # ── Fork ──────────────────────────────────────────────────────────────────

    def fork_session(self, source_session_id: str, turn_index: int) -> str:
        """
        Creates a new session by slicing both history lists up to and including
        *turn_index* (inclusive, 0-based).  Returns the new session ID.

        Args:
            source_session_id: ID of the session to branch from.
            turn_index:        Zero-based index of the last turn to include.

        Raises:
            ValueError: When *source_session_id* is not found or *turn_index* < 0.
        """
        if turn_index < 0:
            raise ValueError(f"turn_index must be >= 0, got {turn_index}")

        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT title, api_history_json, ui_history_json FROM sessions WHERE id = ?",
                (source_session_id,),
            )
            row = cursor.fetchone()

        if row is None:
            raise ValueError(f"Source session not found: {source_session_id}")

        source_title: str = row["title"] or ""
        source_api: list = json.loads(row["api_history_json"]) if row["api_history_json"] else []
        source_ui: list = json.loads(row["ui_history_json"]) if row["ui_history_json"] else []

        # Inclusive slice; Python naturally clamps beyond list length.
        end = turn_index + 1
        new_api = source_api[:end]
        new_ui = source_ui[:end]

        new_id = str(uuid.uuid4())
        self.save_session(
            session_id=new_id,
            title=f"{source_title} (fork @ turn {turn_index})",
            api_history_json=json.dumps(new_api),
            ui_history_json=json.dumps(new_ui),
        )
        return new_id

    # ── Notes ─────────────────────────────────────────────────────────────────

    def add_note(
        self,
        session_id: str,
        selected_text: str,
        source_role: str,
        note: str = "",
    ) -> dict:
        """
        Persists a new note tied to *session_id*.

        Args:
            session_id:    The owning session.  Must already exist.
            selected_text: The raw text the user highlighted.
            source_role:   Which message the selection came from
                           (``"user"`` or ``"assistant"``).
            note:          Optional free-text annotation added by the user.

        Returns:
            The newly created note as a plain dict.

        Raises:
            ValueError: When *session_id* does not exist.
            ValueError: When *selected_text* is empty.
        """
        if not selected_text.strip():
            raise ValueError("selected_text must not be empty.")

        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT id FROM sessions WHERE id = ?", (session_id,)
            ).fetchone()

        if row is None:
            raise ValueError(f"Session not found: {session_id}")

        note_id = str(uuid.uuid4())
        created_at = datetime.now()

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO notes (id, session_id, selected_text, note, source_role, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (note_id, session_id, selected_text, note, source_role, created_at),
            )
            conn.commit()

        return {
            "id": note_id,
            "session_id": session_id,
            "selected_text": selected_text,
            "note": note,
            "source_role": source_role,
            "created_at": created_at.isoformat(),
        }

    def list_notes(self, session_id: str) -> list[dict]:
        """
        Returns all notes for *session_id* ordered oldest-first.

        Returns an empty list (not an error) when the session has no notes
        or does not exist — the caller decides whether a missing session
        warrants a 404.
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT id, session_id, selected_text, note, source_role, created_at
                FROM   notes
                WHERE  session_id = ?
                ORDER  BY created_at ASC
                """,
                (session_id,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def delete_note(self, note_id: str, session_id: str) -> bool:
        """
        Deletes a single note.

        Both *note_id* and *session_id* must match — prevents one session
        from deleting another session's notes.

        Returns:
            ``True`` when a row was deleted, ``False`` when not found.
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM notes WHERE id = ? AND session_id = ?",
                (note_id, session_id),
            )
            conn.commit()
        return cursor.rowcount > 0

    # ── Export ────────────────────────────────────────────────────────────────

    def export_session(self, session_id: str) -> str:
        """
        Renders a session as a Markdown document.

        Raises:
            ValueError: When *session_id* is not found.
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT title, ui_history_json FROM sessions WHERE id = ?",
                (session_id,),
            )
            row = cursor.fetchone()

        if row is None:
            raise ValueError(f"Session not found: {session_id}")

        title: str = row["title"] or ""
        ui_messages: list[dict] = (
            json.loads(row["ui_history_json"]) if row["ui_history_json"] else []
        )
        return export_session_to_markdown(ui_messages, title)
