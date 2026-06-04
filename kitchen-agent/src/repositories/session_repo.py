"""
src/repositories/session_repo.py
=================================
SQLite-backed implementation of SessionRepository.

Handles:
  - Session CRUD (save, load, list, delete)
  - Archive/unarchive
  - Fork (branch a conversation at a given turn)
  - Export data extraction
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime

from src.repositories.connection import SQLiteConnection


class SQLiteSessionRepository:
    def __init__(self, db: SQLiteConnection):
        self.db = db

    def save_session(
        self,
        session_id: str,
        title: str,
        api_history_json: str,
        ui_history_json: str,
        parent_id: str | None = None,
        fork_turn_index: int | None = None,
        root_id: str | None = None,
        system_prompt: str | None = None,
    ) -> None:
        with self.db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO sessions
                    (id, title, api_history_json, ui_history_json, updated_at,
                     parent_id, fork_turn_index, root_id, system_prompt)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    title            = excluded.title,
                    api_history_json = excluded.api_history_json,
                    ui_history_json  = excluded.ui_history_json,
                    updated_at       = excluded.updated_at,
                    system_prompt    = excluded.system_prompt
                """,
                (
                    session_id, title, api_history_json, ui_history_json,
                    datetime.now(), parent_id, fork_turn_index, root_id,
                    system_prompt,
                ),
            )
            conn.commit()

    def load_session(self, session_id: str) -> tuple[str, str, str | None]:
        """
        Returns ``(api_history_json, ui_history_json, system_prompt)``.

        ``system_prompt`` is ``None`` when it was never set or when the row
        pre-dates the F04 schema migration.
        """
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                "SELECT api_history_json, ui_history_json, system_prompt "
                "FROM sessions WHERE id = ?",
                (session_id,),
            )
            row = cursor.fetchone()
        if row:
            return row["api_history_json"], row["ui_history_json"], row["system_prompt"]
        return "[]", "[]", None

    def list_sessions(self, include_archived: bool = False) -> list[dict]:
        where = "" if include_archived else "WHERE archived_at IS NULL"
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                f"SELECT id, title, updated_at, parent_id, fork_turn_index, root_id, archived_at "
                f"FROM sessions {where} ORDER BY updated_at DESC"
            )
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
            cursor = conn.execute(
                "UPDATE sessions SET archived_at = ? WHERE id = ? AND archived_at IS NULL",
                (datetime.now(), session_id),
            )
            conn.commit()
        return cursor.rowcount > 0

    def unarchive_session(self, session_id: str) -> bool:
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                "UPDATE sessions SET archived_at = NULL WHERE id = ? AND archived_at IS NOT NULL",
                (session_id,),
            )
            conn.commit()
        return cursor.rowcount > 0

    def delete_session(self, session_id: str) -> None:
        with self.db.get_connection() as conn:
            row = conn.execute(
                "SELECT id FROM sessions WHERE id = ?", (session_id,)
            ).fetchone()
            if row is None:
                raise ValueError(f"Session not found: {session_id}")

            child_count = conn.execute(
                "SELECT COUNT(*) FROM sessions WHERE parent_id = ?", (session_id,)
            ).fetchone()[0]
            if child_count > 0:
                raise ValueError(
                    f"Cannot delete session '{session_id}': it has {child_count} "
                    f"child session(s). Delete all descendants first."
                )

            conn.execute("DELETE FROM notes WHERE session_id = ?", (session_id,))
            conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            conn.commit()

    def fork_session(self, source_session_id: str, turn_index: int) -> str:
        if turn_index < 0:
            raise ValueError(f"turn_index must be >= 0, got {turn_index}")

        with self.db.get_connection() as conn:
            row = conn.execute(
                "SELECT title, api_history_json, ui_history_json, system_prompt "
                "FROM sessions WHERE id = ?",
                (source_session_id,),
            ).fetchone()

        if row is None:
            raise ValueError(f"Source session not found: {source_session_id}")

        source_title: str = row["title"] or ""
        source_api: list = json.loads(row["api_history_json"]) if row["api_history_json"] else []
        source_ui: list = json.loads(row["ui_history_json"]) if row["ui_history_json"] else []
        source_system_prompt: str | None = row["system_prompt"]

        end = turn_index + 1
        new_api = source_api[:end]
        new_ui = source_ui[:end]
        new_id = str(uuid.uuid4())

        with self.db.get_connection() as conn:
            parent_row = conn.execute(
                "SELECT root_id FROM sessions WHERE id = ?", (source_session_id,)
            ).fetchone()
        parent_root = (
            parent_row["root_id"]
            if parent_row and parent_row["root_id"]
            else source_session_id
        )

        self.save_session(
            session_id=new_id,
            title=f"{source_title} (fork @ turn {turn_index})",
            api_history_json=json.dumps(new_api),
            ui_history_json=json.dumps(new_ui),
            parent_id=source_session_id,
            fork_turn_index=turn_index,
            root_id=parent_root,
            system_prompt=source_system_prompt,
        )
        return new_id

    def get_export_data(self, session_id: str) -> dict:
        """
        Return raw session data needed for export.
        Formatting is ExportService's responsibility, not ours.
        """
        with self.db.get_connection() as conn:
            row = conn.execute(
                """
                SELECT id, title, api_history_json, ui_history_json,
                       system_prompt, updated_at
                FROM sessions
                WHERE id = ?
                """,
                (session_id,),
            ).fetchone()

        if row is None:
            raise ValueError(f"Session not found: {session_id!r}")

        return {
            "session_id":      row["id"],
            "title":           row["title"],
            "api_history":     row["api_history_json"],
            "ui_history":      row["ui_history_json"],
            "system_prompt":   row["system_prompt"],
            "updated_at":      row["updated_at"],
        }
