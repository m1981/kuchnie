"""Test fixtures — shared by schema tests, import tests, and API tests.

Merges fixtures from:
  - Schema/import tests (phases 1–4b): db, db_with_kronospan, lookup
  - API tests (second agent): client (FastAPI TestClient)
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Add catalog/ to sys.path so `from scripts.importer import ...` works
CATALOG_DIR = Path(__file__).resolve().parent.parent
if str(CATALOG_DIR) not in sys.path:
    sys.path.insert(0, str(CATALOG_DIR))

from catalog.api.deps import get_db
from catalog.api.main import app
from catalog.db.engine import get_connection, init_schema
from catalog.scripts.importer import CatalogImporter, load_yaml

# ── Paths ────────────────────────────────────────────────────────

ARCHITECTURE_DIR = CATALOG_DIR / "docs" / "architecture"
DATA_DIR = CATALOG_DIR / "data"

SCHEMA_FILES = [
    "01-schema.sql",
    "02-phase1-worktop-specs.sql",
    "03-phase2-decor-structures-and-pairings.sql",
    "04-phase4a-variant-availability.sql",
    "05-phase4b-property-flags.sql",
    "06-phase5-producer-generalization.sql",
]


def _load_sql(name: str) -> str:
    """Read a SQL file from the architecture directory."""
    path = ARCHITECTURE_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"SQL migration not found: {path}")
    return path.read_text(encoding="utf-8")


# ── Schema/import test fixtures ──────────────────────────────────


@pytest.fixture
def db() -> sqlite3.Connection:
    """Fresh in-memory SQLite DB with all incremental migrations applied.

    Each test gets a fresh DB — no test pollution.
    """
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    for sql_file in SCHEMA_FILES:
        conn.executescript(_load_sql(sql_file))

    conn.commit()
    yield conn
    conn.close()


@pytest.fixture
def db_with_kronospan(db: sqlite3.Connection) -> sqlite3.Connection:
    """DB seeded with a minimal Kronospan dataset for downstream tests.

    Inserts:
      - producer 'kronospan'
      - collection 'global'
      - materials (chipboard + postformed)
      - structures (SM, BS, PE, RS)
      - decors (K8685, 868S, K190)
    """
    cur = db.cursor()

    # Producer
    cur.execute(
        "INSERT INTO producers (slug, name, country) "
        "VALUES ('kronospan', 'Kronospan', 'Polska')"
    )
    producer_id = cur.lastrowid

    # Collection
    cur.execute(
        "INSERT INTO collections (slug, producer_id, name, has_countertops) "
        "VALUES ('global', ?, 'Global Collection 2026', 1)",
        (producer_id,),
    )
    collection_id = cur.lastrowid

    # Materials
    chipboard_type_id = cur.execute(
        "SELECT id FROM material_types WHERE slug = 'chipboard'"
    ).fetchone()[0]
    postformed_type_id = cur.execute(
        "SELECT id FROM material_types WHERE slug = 'worktop_postformed'"
    ).fetchone()[0]

    cur.execute(
        "INSERT INTO materials (slug, material_type_id, collection_id, name) "
        "VALUES ('kronospan-chipboard-global', ?, ?, 'Global Chipboard')",
        (chipboard_type_id, collection_id),
    )
    cur.execute(
        "INSERT INTO materials (slug, material_type_id, collection_id, name) "
        "VALUES ('kronospan-postformed-global', ?, ?, 'Global Postformed Worktop')",
        (postformed_type_id, collection_id),
    )

    # Structures (producer-scoped)
    for code, name, type_, finish in [
        ("SM", "Super Mat", "smooth", "matt"),
        ("BS", "Black Structure", "structured", "matt"),
        ("PE", "Pearl Effect", "structured", "gloss"),
        ("RS", "Rustykalna", "wood_grain", "structured"),
    ]:
        cur.execute(
            "INSERT INTO structures "
            "(code, name, type, finish, producer_id) "
            "VALUES (?, ?, ?, ?, ?)",
            (code, name, type_, finish, producer_id),
        )

    # Decors
    for bid, name, group in [
        ("K8685", "Biel Alpejska", "WHITE FRONT"),
        ("868S", "Biel Alpejska", "XIV MAT 1"),
        ("K190", "Czarny", "COLOR BASIC"),
    ]:
        cur.execute(
            "INSERT INTO decors (business_id, producer_id, name, group_name) "
            "VALUES (?, ?, ?, ?)",
            (bid, producer_id, name, group),
        )

    db.commit()
    return db


@pytest.fixture
def db_seeded(db: sqlite3.Connection) -> sqlite3.Connection:
    """DB with schema + kronospan_sample.yaml data loaded.

    Used by TestImporter tests that verify import counts.
    """
    data = load_yaml(DATA_DIR / "kronospan_sample.yaml")
    importer = CatalogImporter(db)
    importer.import_all(data)
    return db


def lookup_id(db: sqlite3.Connection, table: str, column: str, value: str) -> int:
    """Generic FK resolution helper: SELECT id FROM <table> WHERE <column>=?."""
    row = db.execute(
        f"SELECT id FROM {table} WHERE {column} = ?", (value,)
    ).fetchone()
    if row is None:
        raise LookupError(f"{table}.{column}='{value}' not found")
    return row[0]


@pytest.fixture
def lookup(db: sqlite3.Connection):
    """Convenience fixture: lookup('material_types', 'slug', 'chipboard') → 1."""

    def _lookup(table: str, column: str, value: str) -> int:
        return lookup_id(db, table, column, value)

    return _lookup


# ── API test fixtures (second agent) ─────────────────────────────


@pytest.fixture(scope="module")
def _api_db() -> sqlite3.Connection:
    """Module-scoped DB for API tests. Loads schema + sample data once."""
    conn = get_connection(":memory:")
    init_schema(conn)
    data = load_yaml(DATA_DIR / "kronospan_sample.yaml")
    importer = CatalogImporter(conn)
    importer.import_all(data)
    yield conn
    conn.close()


@pytest.fixture(scope="module")
def client(_api_db: sqlite3.Connection) -> TestClient:
    """FastAPI TestClient wired to the in-memory DB."""

    def _override_get_db():
        yield _api_db

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
