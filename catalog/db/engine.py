"""Database engine — SQLite connection management.

Usage:
    from catalog.db.engine import get_connection, init_schema

    # Production
    db = get_connection("catalog/db/catalog.db")
    init_schema(db)

    # Testing (in-memory)
    db = get_connection(":memory:")
    init_schema(db)
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

_SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def get_connection(db_path: str = ":memory:") -> sqlite3.Connection:
    """Create a SQLite connection with FK enforcement and WAL mode."""
    db = sqlite3.connect(db_path, check_same_thread=False)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA foreign_keys=ON")
    db.row_factory = sqlite3.Row
    return db


def init_schema(db: sqlite3.Connection) -> None:
    """Execute the consolidated schema SQL (DDL + seed data).

    Idempotent: safe to call multiple times (uses CREATE TABLE IF NOT EXISTS
    and INSERT OR IGNORE where needed). For a fresh database, this creates
    all tables, views, indexes, and seeds lookup tables. A database on an
    older schema version is migrated first (see scripts/migrate_1_5_0.py).
    """
    _migrate_if_needed(db)
    schema_sql = _SCHEMA_PATH.read_text(encoding="utf-8")
    db.executescript(schema_sql)


def _migrate_if_needed(db: sqlite3.Connection) -> None:
    """Apply pending in-place migrations to a pre-1.5.0 database."""
    has_decors = db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='decors'"
    ).fetchone()
    if not has_decors:
        return  # fresh DB — schema.sql creates everything at current version
    columns = {row[1] for row in db.execute("PRAGMA table_info(decors)")}
    if "one_global" in columns:
        # import here: migrate_1_5_0 imports this module at top level
        from catalog.scripts.migrate_1_5_0 import migrate

        migrate(db)
