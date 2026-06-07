"""
src/repositories/connection.py
===============================
SQLite connection manager and schema initialization.

Owns:
  - Database file creation
  - Schema DDL (CREATE TABLE, ALTER TABLE for migrations)
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from src.config import settings


class SQLiteConnection:
    def __init__(self, db_path: Path | str | None = None) -> None:
        self.db_path = str(db_path) if db_path is not None else str(settings.db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self.get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id               TEXT PRIMARY KEY,
                    title            TEXT,
                    api_history_json TEXT,
                    ui_history_json  TEXT,
                    updated_at       TIMESTAMP,
                    parent_id        TEXT,
                    fork_turn_index  INTEGER,
                    root_id          TEXT,
                    archived_at      TIMESTAMP,
                    system_prompt    TEXT
                )
                """
            )
            for col, typedef in (
                ("parent_id",       "TEXT"),
                ("fork_turn_index", "INTEGER"),
                ("root_id",         "TEXT"),
                ("archived_at",     "TIMESTAMP"),
                ("system_prompt",   "TEXT"),
            ):
                try:
                    conn.execute(f"ALTER TABLE sessions ADD COLUMN {col} {typedef}")
                except Exception:
                    pass
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
