"""
src/repositories.py
===================
Data access layer using the Repository Pattern.
"""

import json
import re
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Protocol

from src.config import settings
from src.exporter import export_session_to_markdown

LEGACY_FORK_TITLE_RE = re.compile(r"^(?P<parent_title>.+) \(fork @ turn (?P<turn>\d+)\)$")

# ---------------------------------------------------------------------------
# 1. Interfaces (Protocols)
# ---------------------------------------------------------------------------

class SessionRepository(Protocol):
    def save_session(self, session_id: str, title: str, api_history_json: str, ui_history_json: str, parent_id: str | None = None, fork_turn_index: int | None = None, root_id: str | None = None) -> None: ...
    def load_session(self, session_id: str) -> tuple[str, str]: ...
    def list_sessions(self, include_archived: bool = False) -> list[dict]: ...
    def get_session_tree(self, include_archived: bool = True) -> list[dict]: ...
    def archive_session(self, session_id: str) -> bool: ...
    def unarchive_session(self, session_id: str) -> bool: ...
    def delete_session(self, session_id: str) -> None: ...
    def fork_session(self, source_session_id: str, turn_index: int) -> str: ...
    def export_session(self, session_id: str) -> str: ...


class NoteRepository(Protocol):
    def add_note(self, session_id: str, selected_text: str, source_role: str, note: str = "") -> dict: ...
    def list_notes(self, session_id: str) -> list[dict]: ...
    def delete_note(self, note_id: str, session_id: str) -> bool: ...


# ---------------------------------------------------------------------------
# 2. Connection Manager
# ---------------------------------------------------------------------------

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
                    archived_at      TIMESTAMP
                )
                """
            )
            for col, typedef in (
                ("parent_id",       "TEXT"),
                ("fork_turn_index", "INTEGER"),
                ("root_id",         "TEXT"),
                ("archived_at",     "TIMESTAMP"),
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
        rows = [dict(row) for row in conn.execute("SELECT id, title, updated_at, parent_id, root_id FROM sessions ORDER BY updated_at ASC, id ASC")]
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
            candidates = [c for c in by_title.get(match.group("parent_title"), []) if c["id"] != row["id"]]
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
                "UPDATE sessions SET parent_id = ?, fork_turn_index = ?, root_id = ? WHERE id = ? AND parent_id IS NULL",
                updates,
            )

    @staticmethod
    def _choose_legacy_fork_parent(row: dict, candidates: list[dict]) -> dict:
        row_updated_at = row["updated_at"]
        older_candidates = [c for c in candidates if row_updated_at and c["updated_at"] and c["updated_at"] <= row_updated_at]
        pool = older_candidates or candidates
        return max(pool, key=lambda c: (c["updated_at"] is not None, c["updated_at"] or "", c["id"]))


# ---------------------------------------------------------------------------
# 3. Concrete Implementations
# ---------------------------------------------------------------------------

class SQLiteSessionRepository:
    def __init__(self, db: SQLiteConnection):
        self.db = db

    def save_session(self, session_id: str, title: str, api_history_json: str, ui_history_json: str, parent_id: str | None = None, fork_turn_index: int | None = None, root_id: str | None = None) -> None:
        with self.db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO sessions
                    (id, title, api_history_json, ui_history_json, updated_at, parent_id, fork_turn_index, root_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    title            = excluded.title,
                    api_history_json = excluded.api_history_json,
                    ui_history_json  = excluded.ui_history_json,
                    updated_at       = excluded.updated_at
                """,
                (session_id, title, api_history_json, ui_history_json, datetime.now(), parent_id, fork_turn_index, root_id),
            )
            conn.commit()

    def load_session(self, session_id: str) -> tuple[str, str]:
        with self.db.get_connection() as conn:
            cursor = conn.execute("SELECT api_history_json, ui_history_json FROM sessions WHERE id = ?", (session_id,))
            row = cursor.fetchone()
        if row:
            return row["api_history_json"], row["ui_history_json"]
        return "[]", "[]"

    def list_sessions(self, include_archived: bool = False) -> list[dict]:
        where = "" if include_archived else "WHERE archived_at IS NULL"
        with self.db.get_connection() as conn:
            cursor = conn.execute(f"SELECT id, title, updated_at, parent_id, fork_turn_index, root_id, archived_at FROM sessions {where} ORDER BY updated_at DESC")
            return [dict(row) for row in cursor.fetchall()]

    def get_session_tree(self, include_archived: bool = True) -> list[dict]:
        rows = self.list_sessions(include_archived=include_archived)
        nodes: dict[str, dict] = {}
        for row in rows:
            node = dict(row)
            node["children"] = []
            nodes[node["id"]] = node

        roots: list[dict] = []
        for node in nodes.values():
            parent_id = node.get("parent_id")
            if parent_id and parent_id in nodes:
                nodes[parent_id]["children"].append(node)
            else:
                roots.append(node)
        return roots

    def archive_session(self, session_id: str) -> bool:
        with self.db.get_connection() as conn:
            cursor = conn.execute("UPDATE sessions SET archived_at = ? WHERE id = ? AND archived_at IS NULL", (datetime.now(), session_id))
            conn.commit()
        return cursor.rowcount > 0

    def unarchive_session(self, session_id: str) -> bool:
        with self.db.get_connection() as conn:
            cursor = conn.execute("UPDATE sessions SET archived_at = NULL WHERE id = ? AND archived_at IS NOT NULL", (session_id,))
            conn.commit()
        return cursor.rowcount > 0

    def delete_session(self, session_id: str) -> None:
        with self.db.get_connection() as conn:
            row = conn.execute("SELECT id FROM sessions WHERE id = ?", (session_id,)).fetchone()
            if row is None:
                raise ValueError(f"Session not found: {session_id}")

            child_count = conn.execute("SELECT COUNT(*) FROM sessions WHERE parent_id = ?", (session_id,)).fetchone()[0]
            if child_count > 0:
                raise ValueError(f"Cannot delete session '{session_id}': it has {child_count} child session(s). Delete all descendants first.")

            conn.execute("DELETE FROM notes WHERE session_id = ?", (session_id,))
            conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            conn.commit()

    def fork_session(self, source_session_id: str, turn_index: int) -> str:
        if turn_index < 0:
            raise ValueError(f"turn_index must be >= 0, got {turn_index}")

        with self.db.get_connection() as conn:
            row = conn.execute("SELECT title, api_history_json, ui_history_json FROM sessions WHERE id = ?", (source_session_id,)).fetchone()

        if row is None:
            raise ValueError(f"Source session not found: {source_session_id}")

        source_title: str = row["title"] or ""
        source_api: list = json.loads(row["api_history_json"]) if row["api_history_json"] else []
        source_ui: list = json.loads(row["ui_history_json"]) if row["ui_history_json"] else []

        end = turn_index + 1
        new_api = source_api[:end]
        new_ui = source_ui[:end]
        new_id = str(uuid.uuid4())

        with self.db.get_connection() as conn:
            parent_row = conn.execute("SELECT root_id FROM sessions WHERE id = ?", (source_session_id,)).fetchone()
        parent_root = parent_row["root_id"] if parent_row and parent_row["root_id"] else source_session_id

        self.save_session(
            session_id=new_id,
            title=f"{source_title} (fork @ turn {turn_index})",
            api_history_json=json.dumps(new_api),
            ui_history_json=json.dumps(new_ui),
            parent_id=source_session_id,
            fork_turn_index=turn_index,
            root_id=parent_root,
        )
        return new_id

    def export_session(self, session_id: str) -> str:
        with self.db.get_connection() as conn:
            row = conn.execute("SELECT title, ui_history_json FROM sessions WHERE id = ?", (session_id,)).fetchone()

        if row is None:
            raise ValueError(f"Session not found: {session_id}")

        title: str = row["title"] or ""
        ui_messages: list[dict] = json.loads(row["ui_history_json"]) if row["ui_history_json"] else []
        return export_session_to_markdown(ui_messages, title)


class SQLiteNoteRepository:
    def __init__(self, db: SQLiteConnection):
        self.db = db

    def add_note(self, session_id: str, selected_text: str, source_role: str, note: str = "") -> dict:
        if not selected_text.strip():
            raise ValueError("selected_text must not be empty.")

        with self.db.get_connection() as conn:
            row = conn.execute("SELECT id FROM sessions WHERE id = ?", (session_id,)).fetchone()

        if row is None:
            raise ValueError(f"Session not found: {session_id}")

        note_id = str(uuid.uuid4())
        created_at = datetime.now()

        with self.db.get_connection() as conn:
            conn.execute(
                "INSERT INTO notes (id, session_id, selected_text, note, source_role, created_at) VALUES (?, ?, ?, ?, ?, ?)",
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
        with self.db.get_connection() as conn:
            cursor = conn.execute("SELECT id, session_id, selected_text, note, source_role, created_at FROM notes WHERE session_id = ? ORDER BY created_at ASC", (session_id,))
            return [dict(row) for row in cursor.fetchall()]

    def delete_note(self, note_id: str, session_id: str) -> bool:
        with self.db.get_connection() as conn:
            cursor = conn.execute("DELETE FROM notes WHERE id = ? AND session_id = ?", (note_id, session_id))
            conn.commit()
        return cursor.rowcount > 0