# kitchen_erp/core/database.py
import os
from pathlib import Path

from sqlmodel import create_engine, SQLModel, Session, text

from . import models  # noqa: F401 — side-effect import: registers SQLModel tables before create_all
from .models import DEFAULT_STAGE

# SQLite for local development and testing. The path is resolved from the
# package root or an explicit KITCHEN_ERP_DB override — NEVER the process
# CWD (kuchnie-26s: a relative "database.db" meant the ERP opened whichever
# file the working directory happened to hold, silently creating an empty
# schema when started from the wrong place).
DB_PATH = Path(os.environ.get("KITCHEN_ERP_DB") or Path(__file__).resolve().parents[2] / "database.db")

sqlite_url = f"sqlite:///{DB_PATH}"

connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, echo=False, connect_args=connect_args)

# Additive startup migrations (kuchnie-26s). These used to be four
# _ensure_*_schema methods on the Reflex state class, running at request
# time; schema evolution from a UI event handler is the wrong seam. They
# exist because local database.db files predate newer model columns.
#
# Each entry is (table, column, DDL) — adding a column is ONE LINE here, no
# new code path. Rules: additive only (ADD COLUMN), nullable or defaulted,
# safe to re-run (run_startup_migrations consults the live PRAGMA first).
SCHEMA_MIGRATIONS: list[tuple[str, str, str]] = [
    ("cabinet", "module_kind", "ALTER TABLE cabinet ADD COLUMN module_kind VARCHAR DEFAULT 'BASE_CABINET'"),
    ("cabinet", "x_mm", "ALTER TABLE cabinet ADD COLUMN x_mm FLOAT DEFAULT 0"),
    ("cabinet", "y_mm", "ALTER TABLE cabinet ADD COLUMN y_mm FLOAT DEFAULT 0"),
    ("cabinet", "equipment_price", "ALTER TABLE cabinet ADD COLUMN equipment_price FLOAT DEFAULT 0"),
    ("material", "catalog_variant_id", "ALTER TABLE material ADD COLUMN catalog_variant_id VARCHAR"),
    # Project/Order spine (wk-02a62298): stage, customer contact, lifecycle dates.
    ("project", "stage", f"ALTER TABLE project ADD COLUMN stage VARCHAR DEFAULT '{DEFAULT_STAGE}'"),
    ("project", "customer_email", "ALTER TABLE project ADD COLUMN customer_email VARCHAR"),
    ("project", "customer_phone", "ALTER TABLE project ADD COLUMN customer_phone VARCHAR"),
    ("project", "customer_address", "ALTER TABLE project ADD COLUMN customer_address VARCHAR"),
    ("project", "created_at", "ALTER TABLE project ADD COLUMN created_at DATETIME"),
    ("project", "quoted_at", "ALTER TABLE project ADD COLUMN quoted_at DATETIME"),
    ("project", "ordered_at", "ALTER TABLE project ADD COLUMN ordered_at DATETIME"),
    ("project", "production_at", "ALTER TABLE project ADD COLUMN production_at DATETIME"),
    ("project", "installed_at", "ALTER TABLE project ADD COLUMN installed_at DATETIME"),
    # Height parameter set (wk-5b929a7c, docs/specs/height-parameter-set.md).
    ("projectdefaults", "elbow_height_mm", "ALTER TABLE projectdefaults ADD COLUMN elbow_height_mm FLOAT"),
    ("projectdefaults", "worktop_height_mm", "ALTER TABLE projectdefaults ADD COLUMN worktop_height_mm FLOAT"),
    ("projectdefaults", "wall_line_mm", "ALTER TABLE projectdefaults ADD COLUMN wall_line_mm FLOAT"),
    ("projectdefaults", "tall_line_mm", "ALTER TABLE projectdefaults ADD COLUMN tall_line_mm FLOAT"),
]


def run_startup_migrations(target_engine=None) -> list[str]:
    """Apply SCHEMA_MIGRATIONS to `target_engine` (default: the module engine).

    Idempotent: a column already present is skipped, and a table that does
    not exist yet is skipped entirely (a fresh file gets those columns from
    create_all instead). Returns the "table.column" entries actually added.
    """
    target_engine = engine if target_engine is None else target_engine
    applied: list[str] = []
    with Session(target_engine) as session:
        for table, column, ddl in SCHEMA_MIGRATIONS:
            columns = {row[1] for row in session.exec(text(f"PRAGMA table_info({table})")).all()}
            if not columns:
                continue  # table not created yet — nothing to migrate
            if column not in columns:
                session.exec(text(ddl))
                applied.append(f"{table}.{column}")
        session.commit()
    return applied


def create_db_and_tables(target_engine=None):
    """Startup step: create anything missing, then bring existing tables up
    to date. The only place the ERP schema is allowed to evolve."""
    target_engine = engine if target_engine is None else target_engine
    SQLModel.metadata.create_all(target_engine)
    run_startup_migrations(target_engine)


def get_session():
    with Session(engine) as session:
        yield session
