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
    all tables, views, indexes, and seeds lookup tables.
    """
    schema_sql = _SCHEMA_PATH.read_text(encoding="utf-8")
    db.executescript(schema_sql)
