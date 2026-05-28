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
import re
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

from src.config import settings
from src.exporter import export_session_to_markdown


LEGACY_FORK_TITLE_RE = re.compile(r"^(?P<parent_title>.+) \(fork @ turn (?P<turn>\d+)\)$")


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
        """Creates all tables and missing columns if they do not already exist."""
        with self._get_connection() as conn:
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
            # ── Forward-compatible migration for existing DBs ─────────────
            # ADD COLUMN is idempotent when the column already exists only on
            # SQLite ≥ 3.37 (IF NOT EXISTS clause on ADD COLUMN).  For older
            # SQLite we catch the OperationalError raised on duplicate column.
            for col, typedef in (
                ("parent_id",       "TEXT"),
                ("fork_turn_index", "INTEGER"),
                ("root_id",         "TEXT"),
                ("archived_at",     "TIMESTAMP"),
            ):
                try:
                    conn.execute(
                        f"ALTER TABLE sessions ADD COLUMN {col} {typedef}"
                    )
                except Exception:  # noqa: BLE001 — column already exists
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
        """
        Populates lineage for old fork rows created before parent_id existed.

        Early builds only encoded branches in titles, e.g.
        ``Kitchen plan (fork @ turn 2)``.  The tree UI needs real lineage, so
        when the parent title still exists we repair those rows in place.
        """
        rows = [
            dict(row)
            for row in conn.execute(
                """
                SELECT id, title, updated_at, parent_id, root_id
                FROM sessions
                ORDER BY updated_at ASC, id ASC
                """
            )
        ]

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
                candidate
                for candidate in by_title.get(match.group("parent_title"), [])
                if candidate["id"] != row["id"]
            ]
            if not candidates:
                continue

            parent = self._choose_legacy_fork_parent(row, candidates)
            turn_index = int(match.group("turn"))
            root_id = parent["root_id"] or parent["id"]
            updates.append((parent["id"], turn_index, root_id, row["id"]))

            # Keep in-memory rows current so nested legacy forks inherit root_id.
            row["parent_id"] = parent["id"]
            row["root_id"] = root_id

        if updates:
            conn.executemany(
                """
                UPDATE sessions
                SET parent_id = ?, fork_turn_index = ?, root_id = ?
                WHERE id = ? AND parent_id IS NULL
                """,
                updates,
            )

    @staticmethod
    def _choose_legacy_fork_parent(row: dict, candidates: list[dict]) -> dict:
        """Choose the closest existing parent title match for a legacy fork."""
        row_updated_at = row["updated_at"]
        older_candidates = [
            candidate
            for candidate in candidates
            if row_updated_at and candidate["updated_at"] and candidate["updated_at"] <= row_updated_at
        ]
        pool = older_candidates or candidates
        return max(
            pool,
            key=lambda candidate: (
                candidate["updated_at"] is not None,
                candidate["updated_at"] or "",
                candidate["id"],
            ),
        )

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def save_session(
        self,
        session_id: str,
        title: str,
        api_history_json: str,
        ui_history_json: str,
        parent_id: str | None = None,
        fork_turn_index: int | None = None,
        root_id: str | None = None,
    ) -> None:
        """Inserts a new session or updates an existing one (upsert).

        Lineage columns (parent_id, fork_turn_index, root_id) are written on
        INSERT and intentionally NOT overwritten on UPDATE — ancestry is
        immutable once set.
        """
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO sessions
                    (id, title, api_history_json, ui_history_json, updated_at,
                     parent_id, fork_turn_index, root_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    title            = excluded.title,
                    api_history_json = excluded.api_history_json,
                    ui_history_json  = excluded.ui_history_json,
                    updated_at       = excluded.updated_at
                """,
                (
                    session_id, title, api_history_json, ui_history_json,
                    datetime.now(), parent_id, fork_turn_index, root_id,
                ),
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

    def list_sessions(self, include_archived: bool = False) -> list[dict]:
        """
        Returns all sessions (flat) ordered by most-recently updated.

        Args:
            include_archived: When ``False`` (default) archived sessions are
                              excluded.  Pass ``True`` to include them — used
                              by the tree endpoint so the tree structure stays
                              coherent even when some nodes are archived.
        """
        where = "" if include_archived else "WHERE archived_at IS NULL"
        with self._get_connection() as conn:
            cursor = conn.execute(
                f"""
                SELECT id, title, updated_at, parent_id, fork_turn_index,
                       root_id, archived_at
                FROM   sessions
                {where}
                ORDER  BY updated_at DESC
                """
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_session_tree(self, include_archived: bool = True) -> list[dict]:
        """
        Returns all sessions assembled into a forest of trees.

        Each node has the same fields as ``list_sessions`` rows plus a
        ``children`` key containing a list of child nodes (same shape,
        recursively).  Root sessions (``parent_id IS NULL``) are the
        top-level elements; they are ordered by ``updated_at DESC``.
        Children within each node are ordered by ``updated_at DESC``.

        Args:
            include_archived: Defaults to ``True`` so the tree structure
                              remains coherent — archived nodes are visible
                              (greyed-out in the UI) rather than silently
                              creating gaps in the ancestry chain.

        Assembly is done in Python with a single SQL query + one O(n) pass —
        no recursive CTE required.
        """
        rows = self.list_sessions(include_archived=include_archived)

        # Build a lookup and pre-attach an empty children list to every node.
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

    # ── Archive / Delete ──────────────────────────────────────────────────────

    def archive_session(self, session_id: str) -> bool:
        """
        Soft-archives a session by stamping ``archived_at``.

        Archived sessions are hidden from normal listings but remain in the DB
        with all data and lineage intact.  No child-presence check is needed
        because data is not destroyed.

        Returns:
            ``True`` when the session existed and was archived.
            ``False`` when *session_id* was not found.
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                "UPDATE sessions SET archived_at = ? WHERE id = ? AND archived_at IS NULL",
                (datetime.now(), session_id),
            )
            conn.commit()
        return cursor.rowcount > 0

    def unarchive_session(self, session_id: str) -> bool:
        """
        Reverses an archive operation by clearing ``archived_at``.

        Returns:
            ``True`` when the session existed and was unarchived.
            ``False`` when *session_id* was not found or was not archived.
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                "UPDATE sessions SET archived_at = NULL WHERE id = ? AND archived_at IS NOT NULL",
                (session_id,),
            )
            conn.commit()
        return cursor.rowcount > 0

    def delete_session(self, session_id: str) -> None:
        """
        Permanently deletes a session and all its notes.

        Protection rule: a session cannot be deleted while it has living
        (non-deleted) direct children.  The caller must delete all descendants
        leaf-first before this succeeds.

        Args:
            session_id: The session to permanently remove.

        Raises:
            ValueError: When *session_id* does not exist.
            ValueError: When the session has one or more living children
                        (``HasChildrenError`` semantics — caught by the HTTP
                        layer and returned as 409 Conflict).
        """
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT id FROM sessions WHERE id = ?", (session_id,)
            ).fetchone()

            if row is None:
                raise ValueError(f"Session not found: {session_id}")

            child_count = conn.execute(
                "SELECT COUNT(*) FROM sessions WHERE parent_id = ?",
                (session_id,),
            ).fetchone()[0]

            if child_count > 0:
                raise ValueError(
                    f"Cannot delete session '{session_id}': it has {child_count} "
                    f"child session(s). Delete all descendants first."
                )

            # Cascade-delete notes before removing the session.
            conn.execute("DELETE FROM notes WHERE session_id = ?", (session_id,))
            conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            conn.commit()

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

        # root_id: forks inherit the root of their parent; a root points to itself.
        with self._get_connection() as conn:
            parent_row = conn.execute(
                "SELECT root_id FROM sessions WHERE id = ?",
                (source_session_id,),
            ).fetchone()
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
