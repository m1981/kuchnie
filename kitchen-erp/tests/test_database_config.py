# tests/test_database_config.py
"""kuchnie-26s: the ERP database must not be chosen by the process CWD, and
schema evolution must not run from a Reflex event handler.

Three properties are pinned here:
  (a) the resolved DB path is absolute and independent of os.getcwd()
  (b) KITCHEN_ERP_DB overrides it
  (c) the startup migration step is declarative and idempotent
"""
import importlib
import os
from pathlib import Path

import pytest
from sqlmodel import Session, create_engine, text

import kitchen_erp.core.database as database

KITCHEN_ERP_ROOT = Path(__file__).resolve().parents[1]


def _reload_database(monkeypatch, cwd=None, env=None):
    """Re-import core.database under a given CWD / environment."""
    if cwd is not None:
        monkeypatch.chdir(cwd)
    if env is None:
        monkeypatch.delenv("KITCHEN_ERP_DB", raising=False)
    else:
        monkeypatch.setenv("KITCHEN_ERP_DB", env)
    return importlib.reload(database)


# --- (a) path is absolute and CWD-independent -------------------------------

def test_db_path_is_absolute():
    assert database.DB_PATH.is_absolute()


def test_db_path_does_not_depend_on_cwd(tmp_path, monkeypatch):
    here = _reload_database(monkeypatch, cwd=KITCHEN_ERP_ROOT).DB_PATH
    elsewhere = _reload_database(monkeypatch, cwd=tmp_path).DB_PATH
    assert here == elsewhere
    assert tmp_path not in elsewhere.parents


def test_db_path_resolves_under_the_package_root(tmp_path, monkeypatch):
    """The real 28KB database lives at kitchen-erp/database.db — the package
    root, not wherever the process happens to have been started."""
    resolved = _reload_database(monkeypatch, cwd=tmp_path).DB_PATH
    assert resolved == KITCHEN_ERP_ROOT / "database.db"


def test_engine_url_carries_the_absolute_path(tmp_path, monkeypatch):
    module = _reload_database(monkeypatch, cwd=tmp_path)
    assert str(module.DB_PATH) in module.sqlite_url
    assert module.sqlite_url != "sqlite:///database.db"


# --- (b) explicit override --------------------------------------------------

def test_kitchen_erp_db_env_var_overrides_the_default(tmp_path, monkeypatch):
    override = tmp_path / "elsewhere" / "erp.db"
    module = _reload_database(monkeypatch, cwd=KITCHEN_ERP_ROOT, env=str(override))
    assert module.DB_PATH == override
    assert str(override) in module.sqlite_url


# --- (c) startup migrations: declarative and idempotent ---------------------

@pytest.fixture(name="legacy_engine")
def legacy_engine_fixture(tmp_path):
    """A database that predates every additive column — the exact shape the
    _ensure_*_schema methods existed to repair."""
    eng = create_engine(f"sqlite:///{tmp_path / 'legacy.db'}", connect_args={"check_same_thread": False})
    with Session(eng) as session:
        session.exec(text("CREATE TABLE cabinet (id INTEGER PRIMARY KEY, name VARCHAR)"))
        session.exec(text("CREATE TABLE material (id INTEGER PRIMARY KEY, name VARCHAR)"))
        session.exec(text("CREATE TABLE project (id INTEGER PRIMARY KEY, name VARCHAR)"))
        session.exec(text("CREATE TABLE projectdefaults (id INTEGER PRIMARY KEY)"))
        session.commit()
    return eng


def _columns(eng, table):
    with Session(eng) as session:
        return [row[1] for row in session.exec(text(f"PRAGMA table_info({table})")).all()]


def test_migration_table_is_a_flat_declarative_list():
    """Adding a column must be a one-line addition. Each entry is
    (table, column, ddl) so a new row needs no new code path."""
    assert isinstance(database.SCHEMA_MIGRATIONS, list)
    for entry in database.SCHEMA_MIGRATIONS:
        table, column, ddl = entry
        assert ddl.upper().startswith(f"ALTER TABLE {table} ADD COLUMN".upper())
        assert column in ddl


def test_migrations_cover_every_column_the_ui_layer_used_to_add():
    """Behaviour parity with the removed _ensure_*_schema methods."""
    declared = {(t, c) for t, c, _ in database.SCHEMA_MIGRATIONS}
    expected = {
        ("cabinet", "module_kind"), ("cabinet", "x_mm"), ("cabinet", "y_mm"),
        ("cabinet", "equipment_price"),
        ("material", "catalog_variant_id"),
        ("project", "stage"), ("project", "customer_email"),
        ("project", "customer_phone"), ("project", "customer_address"),
        ("project", "created_at"), ("project", "quoted_at"),
        ("project", "ordered_at"), ("project", "production_at"),
        ("project", "installed_at"),
        ("projectdefaults", "elbow_height_mm"),
        ("projectdefaults", "worktop_height_mm"),
        ("projectdefaults", "wall_line_mm"), ("projectdefaults", "tall_line_mm"),
    }
    assert expected <= declared


def test_run_startup_migrations_adds_missing_columns(legacy_engine):
    database.run_startup_migrations(legacy_engine)
    assert "module_kind" in _columns(legacy_engine, "cabinet")
    assert "catalog_variant_id" in _columns(legacy_engine, "material")
    assert "stage" in _columns(legacy_engine, "project")
    assert "elbow_height_mm" in _columns(legacy_engine, "projectdefaults")


def test_run_startup_migrations_is_idempotent(legacy_engine):
    database.run_startup_migrations(legacy_engine)
    after_first = {t: _columns(legacy_engine, t) for t in ("cabinet", "material", "project", "projectdefaults")}
    database.run_startup_migrations(legacy_engine)  # must not raise
    after_second = {t: _columns(legacy_engine, t) for t in ("cabinet", "material", "project", "projectdefaults")}
    assert after_first == after_second
    for cols in after_second.values():
        assert len(cols) == len(set(cols)), "a column was added twice"


def test_run_startup_migrations_skips_absent_tables(tmp_path):
    """A brand-new file has no tables yet; migrations must no-op, not blow up
    with 'no such table'."""
    eng = create_engine(f"sqlite:///{tmp_path / 'empty.db'}", connect_args={"check_same_thread": False})
    database.run_startup_migrations(eng)  # must not raise


def test_create_db_and_tables_runs_the_migrations(tmp_path):
    eng = create_engine(f"sqlite:///{tmp_path / 'fresh.db'}", connect_args={"check_same_thread": False})
    database.create_db_and_tables(eng)
    database.create_db_and_tables(eng)  # idempotent on a second boot
    assert "module_kind" in _columns(eng, "cabinet")


# --- the UI layer no longer owns schema evolution ---------------------------

def test_state_module_has_no_runtime_schema_migrations():
    state_src = (KITCHEN_ERP_ROOT / "kitchen_erp" / "ui" / "state.py").read_text(encoding="utf-8")
    assert "_ensure_" not in state_src
    assert "ALTER TABLE" not in state_src


def test_state_module_delegates_boot_to_core_database():
    state_src = (KITCHEN_ERP_ROOT / "kitchen_erp" / "ui" / "state.py").read_text(encoding="utf-8")
    load_fn = state_src.split("def load_mock_data")[1]
    assert "create_db_and_tables()" in load_fn


@pytest.fixture(autouse=True)
def _restore_database_module():
    """monkeypatch undoes env/cwd, but the reloaded module object keeps the
    values it was reloaded with — put it back for the next test."""
    yield
    os.environ.pop("KITCHEN_ERP_DB", None)
    importlib.reload(database)


def test_app_module_runs_migrations_at_import_not_from_a_route(tmp_path):
    """Reaching /admin directly must not hit a pre-migration schema.

    kuchnie-26s moved the DDL out of the Reflex state class but left its only
    trigger on the "/" route's on_load, so a bookmark straight to /admin ran
    AdminState.load_materials against an unmigrated database. kuchnie-h45
    widened that hole by adding two columns. The migration therefore has to
    fire at module import, before any page is registered.
    """
    src = (
        Path(__file__).resolve().parents[1] / "kitchen_erp" / "kitchen_erp.py"
    ).read_text()

    call = "create_db_and_tables()"
    assert call in src, "app module never runs the startup migration"

    # Module level means column 0 — inside a def/on_load it would be indented.
    assert any(
        line == call for line in src.splitlines()
    ), "create_db_and_tables() must run at import, not inside a function or a route hook"

    # And it must precede the first add_page, or a route could load first.
    assert src.index(call) < src.index("app.add_page"), (
        "migrations must run before any page is registered"
    )
