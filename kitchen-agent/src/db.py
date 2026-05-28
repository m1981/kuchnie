# src/db.py
import sqlite3
import os
import json
import uuid
from datetime import datetime

class DatabaseManager:
    def __init__(self, db_path: str = "data/chats.db"):
        self.db_path = db_path
        # Ensure the data directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _get_connection(self):
        # Return rows as dictionaries instead of tuples for easier access
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Creates the sessions table if it doesn't exist."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    title TEXT,
                    api_history_json TEXT,
                    ui_history_json TEXT,
                    updated_at TIMESTAMP
                )
            """)
            conn.commit()

    def save_session(self, session_id: str, title: str, api_history_json: str, ui_history_json: str):
        """Inserts a new session or updates an existing one."""
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO sessions (id, title, api_history_json, ui_history_json, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    api_history_json=excluded.api_history_json,
                    ui_history_json=excluded.ui_history_json,
                    updated_at=excluded.updated_at
            """, (session_id, title, api_history_json, ui_history_json, datetime.now()))
            conn.commit()

    def load_session(self, session_id: str) -> tuple[str, str]:
        """Returns (api_history_json, ui_history_json) for a given session ID."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT api_history_json, ui_history_json FROM sessions WHERE id = ?", (session_id,))
            row = cursor.fetchone()
            if row:
                return row["api_history_json"], row["ui_history_json"]
            return "[]", "[]"

    def list_sessions(self) -> list[dict]:
        """Returns a list of all sessions, ordered by most recently updated."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT id, title, updated_at FROM sessions ORDER BY updated_at DESC")
            return [dict(row) for row in cursor.fetchall()]

    def fork_session(self, source_session_id: str, turn_index: int) -> str:
        """
        Creates a new session by slicing the source session's histories up to
        and including `turn_index`. Returns the new session ID.

        Raises:
            ValueError: if source_session_id does not exist or turn_index < 0.
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

            source_title = row["title"] or ""
            source_api = json.loads(row["api_history_json"]) if row["api_history_json"] else []
            source_ui = json.loads(row["ui_history_json"]) if row["ui_history_json"] else []

        # Inclusive slice; Python list slicing naturally clamps beyond length.
        slice_end = turn_index + 1
        new_api = source_api[:slice_end]
        new_ui = source_ui[:slice_end]

        new_id = str(uuid.uuid4())
        new_title = f"{source_title} (fork @ turn {turn_index})"

        self.save_session(
            session_id=new_id,
            title=new_title,
            api_history_json=json.dumps(new_api),
            ui_history_json=json.dumps(new_ui),
        )
        return new_id
