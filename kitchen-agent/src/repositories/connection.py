"""
src/repositories/connection.py
===============================
SQLite connection manager and schema initialization.

Owns:
  - Database file creation
  - Schema DDL (CREATE TABLE, ALTER TABLE for migrations)
  - Legacy fork lineage backfill
"""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path

from src.config import settings

LEGACY_FORK_TITLE_RE = re.compile(r"^(?P<parent_title>.+) \(fork @ turn (?P<turn>\d+)\)$")


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
            self._backfill_legacy_fork_lineage(conn)
            conn.commit()

    def _backfill_legacy_fork_lineage(self, conn: sqlite3.Connection) -> None:
        rows = [dict(row) for row in conn.execute(
            "SELECT id, title, updated_at, parent_id, root_id "
            "FROM sessions ORDER BY updated_at ASC, id ASC"
        )]
        by_title: dict[str, list[dict]] = {}
        for row in rows:
            by_title.setdefault(row["title"] or "", []).append(row)

        updates: list[tuple[str, int, str, str]] = []
        for row in rows:
            if row["parent_id"] is not None:
                continue
            match = LEGACY_FORK_TITLE_RE.match(row["title"] or "")
            if match is None:
                continue
            candidates = [
                c for c in by_title.get(match.group("parent_title"), [])
                if c["id"] != row["id"]
            ]
            if not candidates:
                continue

            parent = self._choose_legacy_fork_parent(row, candidates)
            turn_index = int(match.group("turn"))
            root_id = parent["root_id"] or parent["id"]
            updates.append((parent["id"], turn_index, root_id, row["id"]))
            row["parent_id"] = parent["id"]
            row["root_id"] = root_id

        if updates:
            conn.executemany(
                "UPDATE sessions SET parent_id = ?, fork_turn_index = ?, root_id = ? "
                "WHERE id = ? AND parent_id IS NULL",
                updates,
            )

    @staticmethod
    def _choose_legacy_fork_parent(row: dict, candidates: list[dict]) -> dict:
        row_updated_at = row["updated_at"]
        older_candidates = [
            c for c in candidates
            if row_updated_at and c["updated_at"] and c["updated_at"] <= row_updated_at
        ]
        pool = older_candidates or candidates
        return max(
            pool,
            key=lambda c: (c["updated_at"] is not None, c["updated_at"] or "", c["id"]),
        )
