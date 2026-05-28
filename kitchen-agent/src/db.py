# src/db.py
import sqlite3
import os
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