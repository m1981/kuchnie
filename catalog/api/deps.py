"""FastAPI dependency providers."""

from __future__ import annotations

import sqlite3
from typing import Generator

# Module-level reference, set by main.py lifespan startup.
_db_connection: sqlite3.Connection | None = None


def set_db(conn: sqlite3.Connection) -> None:
    """Register the application-wide DB connection."""
    global _db_connection
    _db_connection = conn


def get_db() -> Generator[sqlite3.Connection, None, None]:
    """Yield the shared DB connection. Override in tests."""
    if _db_connection is None:
        raise RuntimeError("Database not initialized. Call set_db() first.")
    yield _db_connection
