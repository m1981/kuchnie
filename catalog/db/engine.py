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

import re
import sqlite3
from pathlib import Path

_SCHEMA_PATH = Path(__file__).parent / "schema.sql"

_VERSION_RE = re.compile(r"^--\s*Version:\s*(\d+\.\d+\.\d+)\s*$")
_VERSION_HEADER_LINES = 10


def _read_schema_version(path: Path = _SCHEMA_PATH) -> str:
    """Parse the schema version from schema.sql's header comment.

    schema.sql is the authoritative statement of the catalog's shape, and its
    `-- Version: X.Y.Z` header is where that shape is versioned. Reading it
    here rather than restating it as a Python constant means a migration that
    edits the DDL cannot forget to move the number consumers handshake on
    (bead kuchnie-019).
    """
    with path.open(encoding="utf-8") as handle:
        for _ in range(_VERSION_HEADER_LINES):
            line = handle.readline()
            if not line:
                break
            match = _VERSION_RE.match(line.rstrip("\n"))
            if match:
                return match.group(1)
    raise RuntimeError(
        f"{path} has no '-- Version: X.Y.Z' header — the catalog schema version "
        "is unknown, so no consumer can assert compatibility against it."
    )


#: The catalog schema version this code base ships. Published over the wire by
#: GET /catalog/admin/stats and asserted by every consumer (catalog.client).
SCHEMA_VERSION = _read_schema_version()


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
