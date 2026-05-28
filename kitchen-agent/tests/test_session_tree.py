"""
tests/test_session_tree.py
==========================
TDD suite for the session lineage / tree feature.

Structure
---------
Section 1 — DatabaseManager unit tests
  - save_session now persists lineage columns
  - list_sessions now returns lineage columns
  - fork_session populates parent_id / fork_turn_index / root_id correctly
  - get_session_tree assembles the correct nested structure

Section 2 — FastAPI endpoint tests
  GET /api/sessions       → flat list now includes lineage fields
  GET /api/sessions/tree  → nested tree structure

All tests use isolated tmp DBs / TestClients — no network calls.
"""
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import src.main as main_module
from src import config as config_module
from src.db import DatabaseManager
from src.main import app, get_db


# ===========================================================================
# Helpers
# ===========================================================================

def _make_db(tmp_path: Path) -> DatabaseManager:
    return DatabaseManager(db_path=str(tmp_path / "test.db"))


def _seed(db: DatabaseManager, session_id: str, title: str = "Root") -> str:
    db.save_session(
        session_id=session_id,
        title=title,
        api_history_json="[]",
        ui_history_json="[]",
    )
    return session_id


# ===========================================================================
# Section 1 — DatabaseManager
# ===========================================================================

class TestLineageColumns:
    def test_root_session_has_null_lineage(self, tmp_path: Path) -> None:
        """A brand-new session (not a fork) has NULL parent_id and fork_turn_index."""
        db = _make_db(tmp_path)
        _seed(db, "root-1")

        rows = db.list_sessions()
        assert len(rows) == 1
        row = rows[0]
        assert row["parent_id"] is None
        assert row["fork_turn_index"] is None

    def test_root_session_root_id_is_none_before_fork(self, tmp_path: Path) -> None:
        """A plain session has root_id = NULL (no fork ancestry)."""
        db = _make_db(tmp_path)
        _seed(db, "root-1")

        rows = db.list_sessions()
        assert rows[0]["root_id"] is None

    def test_list_sessions_exposes_lineage_fields(self, tmp_path: Path) -> None:
        """list_sessions rows must include parent_id, fork_turn_index, root_id."""
        db = _make_db(tmp_path)
        _seed(db, "s1")
        row = db.list_sessions()[0]
        for field in ("parent_id", "fork_turn_index", "root_id"):
            assert field in row, f"Missing field: {field}"

    def test_upsert_does_not_overwrite_lineage(self, tmp_path: Path) -> None:
        """Saving a session twice must not clear lineage set on first insert."""
        db = _make_db(tmp_path)
        _seed(db, "parent-1")
        child_id = db.fork_session("parent-1", turn_index=0)

        # Re-save the child (simulates ChatService updating history).
        db.save_session(
            session_id=child_id,
            title="Updated title",
            api_history_json="[]",
            ui_history_json="[]",
        )

        rows = {r["id"]: r for r in db.list_sessions()}
        assert rows[child_id]["parent_id"] == "parent-1"
        assert rows[child_id]["fork_turn_index"] == 0


class TestForkLineage:
    def test_fork_sets_parent_id(self, tmp_path: Path) -> None:
        db = _make_db(tmp_path)
        _seed(db, "parent-1")
        child_id = db.fork_session("parent-1", turn_index=2)

        rows = {r["id"]: r for r in db.list_sessions()}
        assert rows[child_id]["parent_id"] == "parent-1"

    def test_fork_sets_fork_turn_index(self, tmp_path: Path) -> None:
        db = _make_db(tmp_path)
        _seed(db, "parent-1")
        child_id = db.fork_session("parent-1", turn_index=3)

        rows = {r["id"]: r for r in db.list_sessions()}
        assert rows[child_id]["fork_turn_index"] == 3

    def test_first_fork_root_id_equals_parent(self, tmp_path: Path) -> None:
        """When a root session is forked, root_id of the child == parent id."""
        db = _make_db(tmp_path)
        _seed(db, "root-1")
        child_id = db.fork_session("root-1", turn_index=0)

        rows = {r["id"]: r for r in db.list_sessions()}
        assert rows[child_id]["root_id"] == "root-1"

    def test_grandchild_inherits_root_id(self, tmp_path: Path) -> None:
        """root_id must propagate through multiple fork levels."""
        db = _make_db(tmp_path)
        _seed(db, "root-1")
        child_id = db.fork_session("root-1", turn_index=0)
        grandchild_id = db.fork_session(child_id, turn_index=0)

        rows = {r["id"]: r for r in db.list_sessions()}
        assert rows[grandchild_id]["root_id"] == "root-1"

    def test_sibling_forks_share_root_id(self, tmp_path: Path) -> None:
        """Two forks from the same root both point to that root."""
        db = _make_db(tmp_path)
        _seed(db, "root-1")
        child_a = db.fork_session("root-1", turn_index=0)
        child_b = db.fork_session("root-1", turn_index=1)

        rows = {r["id"]: r for r in db.list_sessions()}
        assert rows[child_a]["root_id"] == "root-1"
        assert rows[child_b]["root_id"] == "root-1"

    def test_independent_trees_have_different_roots(self, tmp_path: Path) -> None:
        db = _make_db(tmp_path)
        _seed(db, "tree-A")
        _seed(db, "tree-B")
        child_a = db.fork_session("tree-A", turn_index=0)
        child_b = db.fork_session("tree-B", turn_index=0)

        rows = {r["id"]: r for r in db.list_sessions()}
        assert rows[child_a]["root_id"] == "tree-A"
        assert rows[child_b]["root_id"] == "tree-B"
        assert rows[child_a]["root_id"] != rows[child_b]["root_id"]

    def test_parent_lineage_unchanged_after_fork(self, tmp_path: Path) -> None:
        """Forking a session must not modify the parent's lineage columns."""
        db = _make_db(tmp_path)
        _seed(db, "parent-1")
        db.fork_session("parent-1", turn_index=0)

        rows = {r["id"]: r for r in db.list_sessions()}
        assert rows["parent-1"]["parent_id"] is None
        assert rows["parent-1"]["fork_turn_index"] is None


class TestGetSessionTree:
    def test_empty_db_returns_empty_list(self, tmp_path: Path) -> None:
        db = _make_db(tmp_path)
        assert db.get_session_tree() == []

    def test_single_root_no_children(self, tmp_path: Path) -> None:
        db = _make_db(tmp_path)
        _seed(db, "root-1", "My Chat")
        tree = db.get_session_tree()

        assert len(tree) == 1
        assert tree[0]["id"] == "root-1"
        assert tree[0]["children"] == []

    def test_fork_appears_as_child_not_root(self, tmp_path: Path) -> None:
        db = _make_db(tmp_path)
        _seed(db, "root-1")
        child_id = db.fork_session("root-1", turn_index=1)

        tree = db.get_session_tree()

        # Only the root is at top level.
        assert len(tree) == 1
        assert tree[0]["id"] == "root-1"

        # The fork is a child.
        children = tree[0]["children"]
        assert len(children) == 1
        assert children[0]["id"] == child_id

    def test_multiple_forks_all_appear_as_children(self, tmp_path: Path) -> None:
        db = _make_db(tmp_path)
        _seed(db, "root-1")
        child_a = db.fork_session("root-1", turn_index=0)
        child_b = db.fork_session("root-1", turn_index=1)

        tree = db.get_session_tree()
        assert len(tree) == 1

        child_ids = {c["id"] for c in tree[0]["children"]}
        assert child_a in child_ids
        assert child_b in child_ids

    def test_grandchild_nested_correctly(self, tmp_path: Path) -> None:
        db = _make_db(tmp_path)
        _seed(db, "root-1")
        child_id = db.fork_session("root-1", turn_index=0)
        grandchild_id = db.fork_session(child_id, turn_index=0)

        tree = db.get_session_tree()
        assert len(tree) == 1  # only root at top level

        child_node = tree[0]["children"][0]
        assert child_node["id"] == child_id
        assert len(child_node["children"]) == 1
        assert child_node["children"][0]["id"] == grandchild_id

    def test_independent_trees_produce_multiple_roots(self, tmp_path: Path) -> None:
        db = _make_db(tmp_path)
        _seed(db, "tree-A")
        _seed(db, "tree-B")
        db.fork_session("tree-A", turn_index=0)

        tree = db.get_session_tree()
        root_ids = {node["id"] for node in tree}

        assert "tree-A" in root_ids
        assert "tree-B" in root_ids
        # tree-B has no children, tree-A has one
        tree_b_node = next(n for n in tree if n["id"] == "tree-B")
        assert tree_b_node["children"] == []

    def test_node_contains_lineage_fields(self, tmp_path: Path) -> None:
        """Each tree node must carry parent_id, fork_turn_index, root_id."""
        db = _make_db(tmp_path)
        _seed(db, "root-1")
        child_id = db.fork_session("root-1", turn_index=2)

        tree = db.get_session_tree()
        child_node = tree[0]["children"][0]

        assert child_node["parent_id"] == "root-1"
        assert child_node["fork_turn_index"] == 2
        assert child_node["root_id"] == "root-1"
        assert child_node["id"] == child_id

    def test_node_contains_children_key(self, tmp_path: Path) -> None:
        db = _make_db(tmp_path)
        _seed(db, "root-1")
        tree = db.get_session_tree()
        assert "children" in tree[0]


# ===========================================================================
# Section 2 — FastAPI endpoints
# ===========================================================================

@pytest.fixture
def db(tmp_path: Path) -> DatabaseManager:
    return _make_db(tmp_path)


@pytest.fixture
def client(db: DatabaseManager, tmp_path: Path, monkeypatch) -> TestClient:
    monkeypatch.setattr(config_module.settings, "data_dir", tmp_path)
    monkeypatch.setattr(main_module.settings, "data_dir", tmp_path)
    app.dependency_overrides[get_db] = lambda: db
    yield TestClient(app)
    app.dependency_overrides.pop(get_db, None)


class TestGetSessionsFlat:
    def test_returns_lineage_fields(
        self, client: TestClient, db: DatabaseManager
    ) -> None:
        _seed(db, "s1")
        resp = client.get("/api/sessions")
        assert resp.status_code == 200
        item = resp.json()[0]
        assert "parent_id" in item
        assert "fork_turn_index" in item
        assert "root_id" in item

    def test_root_session_has_null_lineage(
        self, client: TestClient, db: DatabaseManager
    ) -> None:
        _seed(db, "s1")
        resp = client.get("/api/sessions")
        item = resp.json()[0]
        assert item["parent_id"] is None
        assert item["fork_turn_index"] is None
        assert item["root_id"] is None

    def test_forked_session_has_lineage_populated(
        self, client: TestClient, db: DatabaseManager
    ) -> None:
        _seed(db, "root-1")
        child_id = db.fork_session("root-1", turn_index=3)

        resp = client.get("/api/sessions")
        rows = {r["id"]: r for r in resp.json()}
        assert rows[child_id]["parent_id"] == "root-1"
        assert rows[child_id]["fork_turn_index"] == 3
        assert rows[child_id]["root_id"] == "root-1"


class TestGetSessionTree:
    def test_empty_returns_empty_list(self, client: TestClient) -> None:
        resp = client.get("/api/sessions/tree")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_single_root_in_tree(
        self, client: TestClient, db: DatabaseManager
    ) -> None:
        _seed(db, "root-1", "My chat")
        resp = client.get("/api/sessions/tree")
        assert resp.status_code == 200
        tree = resp.json()
        assert len(tree) == 1
        assert tree[0]["id"] == "root-1"
        assert tree[0]["children"] == []

    def test_fork_is_child_not_root(
        self, client: TestClient, db: DatabaseManager
    ) -> None:
        _seed(db, "root-1")
        child_id = db.fork_session("root-1", turn_index=1)

        resp = client.get("/api/sessions/tree")
        tree = resp.json()
        assert len(tree) == 1
        assert tree[0]["id"] == "root-1"
        assert len(tree[0]["children"]) == 1
        assert tree[0]["children"][0]["id"] == child_id

    def test_grandchild_nested(
        self, client: TestClient, db: DatabaseManager
    ) -> None:
        _seed(db, "root-1")
        child_id = db.fork_session("root-1", turn_index=0)
        grandchild_id = db.fork_session(child_id, turn_index=0)

        resp = client.get("/api/sessions/tree")
        tree = resp.json()

        child_node = tree[0]["children"][0]
        assert child_node["id"] == child_id
        assert child_node["children"][0]["id"] == grandchild_id

    def test_node_schema_has_all_fields(
        self, client: TestClient, db: DatabaseManager
    ) -> None:
        _seed(db, "root-1")
        child_id = db.fork_session("root-1", turn_index=2)

        tree = client.get("/api/sessions/tree").json()
        child_node = tree[0]["children"][0]

        for field in ("id", "title", "updated_at", "parent_id",
                      "fork_turn_index", "root_id", "children"):
            assert field in child_node, f"Missing field: {field}"

        assert child_node["parent_id"] == "root-1"
        assert child_node["fork_turn_index"] == 2

    def test_multiple_independent_trees(
        self, client: TestClient, db: DatabaseManager
    ) -> None:
        _seed(db, "tree-A")
        _seed(db, "tree-B")

        resp = client.get("/api/sessions/tree")
        root_ids = {n["id"] for n in resp.json()}
        assert "tree-A" in root_ids
        assert "tree-B" in root_ids

    def test_tree_endpoint_distinct_from_session_id_route(
        self, client: TestClient, db: DatabaseManager
    ) -> None:
        """'tree' must not be swallowed as a {session_id} path param."""
        resp = client.get("/api/sessions/tree")
        # Must NOT 404 (which would happen if matched as a session id lookup
        # and the session was not found — that route returns 200 with empty,
        # but the tree route has its own 200 response_model).
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
