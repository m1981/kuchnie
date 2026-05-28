"""
tests/test_archive_delete.py
============================
TDD suite for session archive and permanent-delete features.

Structure
---------
Section 1 — DatabaseManager unit tests
  archive_session:   happy path, already-archived idempotency,
                     not-found, archived_at is a timestamp
  unarchive_session: happy path, not-found, not-archived
  list_sessions:     default hides archived, include_archived=True shows all
  get_session_tree:  include_archived=True default, False excludes archived
  delete_session:    happy path, not-found (404), has-children guard (409),
                     notes cascade, archived child still blocks delete

Section 2 — FastAPI endpoint tests
  PATCH  /api/sessions/{id}/archive       → 200 / 404
  DELETE /api/sessions/{id}/archive       → 200 / 404
  DELETE /api/sessions/{id}               → 204 / 404 / 409
  GET    /api/sessions?include_archived   → filter behaviour
  GET    /api/sessions/tree?include_archived → filter behaviour
"""
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


def _seed(db: DatabaseManager, session_id: str, title: str = "Chat") -> str:
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

class TestArchiveSession:
    def test_returns_true_when_archived(self, tmp_path: Path) -> None:
        db = _make_db(tmp_path)
        _seed(db, "s1")
        assert db.archive_session("s1") is True

    def test_archived_at_is_set(self, tmp_path: Path) -> None:
        db = _make_db(tmp_path)
        _seed(db, "s1")
        db.archive_session("s1")

        rows = db.list_sessions(include_archived=True)
        row = next(r for r in rows if r["id"] == "s1")
        assert row["archived_at"] is not None

    def test_returns_false_for_nonexistent_session(self, tmp_path: Path) -> None:
        db = _make_db(tmp_path)
        assert db.archive_session("ghost") is False

    def test_returns_false_when_already_archived(self, tmp_path: Path) -> None:
        """Archiving an already-archived session is a no-op that returns False."""
        db = _make_db(tmp_path)
        _seed(db, "s1")
        db.archive_session("s1")
        assert db.archive_session("s1") is False

    def test_archived_session_disappears_from_default_list(self, tmp_path: Path) -> None:
        db = _make_db(tmp_path)
        _seed(db, "s1")
        _seed(db, "s2")
        db.archive_session("s1")

        ids = [r["id"] for r in db.list_sessions()]
        assert "s1" not in ids
        assert "s2" in ids

    def test_archive_does_not_delete_data(self, tmp_path: Path) -> None:
        """Archiving must not touch any data columns."""
        db = _make_db(tmp_path)
        _seed(db, "s1", title="Important Chat")
        db.archive_session("s1")

        rows = db.list_sessions(include_archived=True)
        row = next(r for r in rows if r["id"] == "s1")
        assert row["title"] == "Important Chat"

    def test_archive_does_not_affect_sibling(self, tmp_path: Path) -> None:
        db = _make_db(tmp_path)
        _seed(db, "s1")
        _seed(db, "s2")
        db.archive_session("s1")

        rows = db.list_sessions(include_archived=True)
        s2 = next(r for r in rows if r["id"] == "s2")
        assert s2["archived_at"] is None


class TestUnarchiveSession:
    def test_returns_true_when_unarchived(self, tmp_path: Path) -> None:
        db = _make_db(tmp_path)
        _seed(db, "s1")
        db.archive_session("s1")
        assert db.unarchive_session("s1") is True

    def test_archived_at_cleared_after_unarchive(self, tmp_path: Path) -> None:
        db = _make_db(tmp_path)
        _seed(db, "s1")
        db.archive_session("s1")
        db.unarchive_session("s1")

        rows = db.list_sessions(include_archived=True)
        row = next(r for r in rows if r["id"] == "s1")
        assert row["archived_at"] is None

    def test_unarchived_session_reappears_in_default_list(self, tmp_path: Path) -> None:
        db = _make_db(tmp_path)
        _seed(db, "s1")
        db.archive_session("s1")
        db.unarchive_session("s1")

        ids = [r["id"] for r in db.list_sessions()]
        assert "s1" in ids

    def test_returns_false_for_nonexistent_session(self, tmp_path: Path) -> None:
        db = _make_db(tmp_path)
        assert db.unarchive_session("ghost") is False

    def test_returns_false_when_not_archived(self, tmp_path: Path) -> None:
        """Unarchiving a live session is a no-op that returns False."""
        db = _make_db(tmp_path)
        _seed(db, "s1")
        assert db.unarchive_session("s1") is False


class TestListSessionsFilter:
    def test_default_hides_archived(self, tmp_path: Path) -> None:
        db = _make_db(tmp_path)
        _seed(db, "live")
        _seed(db, "archived")
        db.archive_session("archived")

        ids = [r["id"] for r in db.list_sessions()]
        assert "live" in ids
        assert "archived" not in ids

    def test_include_archived_true_shows_all(self, tmp_path: Path) -> None:
        db = _make_db(tmp_path)
        _seed(db, "live")
        _seed(db, "archived")
        db.archive_session("archived")

        ids = [r["id"] for r in db.list_sessions(include_archived=True)]
        assert "live" in ids
        assert "archived" in ids

    def test_archived_at_field_present_in_rows(self, tmp_path: Path) -> None:
        db = _make_db(tmp_path)
        _seed(db, "s1")
        row = db.list_sessions()[0]
        assert "archived_at" in row
        assert row["archived_at"] is None


class TestGetSessionTreeFilter:
    def test_tree_includes_archived_by_default(self, tmp_path: Path) -> None:
        """Default include_archived=True preserves tree coherence."""
        db = _make_db(tmp_path)
        _seed(db, "root-1")
        child_id = db.fork_session("root-1", turn_index=0)
        db.archive_session(child_id)

        tree = db.get_session_tree()
        root = tree[0]
        child_ids = [c["id"] for c in root["children"]]
        assert child_id in child_ids

    def test_tree_excludes_archived_when_requested(self, tmp_path: Path) -> None:
        db = _make_db(tmp_path)
        _seed(db, "root-1")
        child_id = db.fork_session("root-1", turn_index=0)
        db.archive_session(child_id)

        tree = db.get_session_tree(include_archived=False)
        root = tree[0]
        child_ids = [c["id"] for c in root["children"]]
        assert child_id not in child_ids

    def test_archived_node_carries_archived_at(self, tmp_path: Path) -> None:
        db = _make_db(tmp_path)
        _seed(db, "root-1")
        child_id = db.fork_session("root-1", turn_index=0)
        db.archive_session(child_id)

        tree = db.get_session_tree(include_archived=True)
        child_node = tree[0]["children"][0]
        assert child_node["archived_at"] is not None


class TestDeleteSession:
    def test_deletes_leaf_session(self, tmp_path: Path) -> None:
        db = _make_db(tmp_path)
        _seed(db, "s1")
        db.delete_session("s1")
        assert db.list_sessions(include_archived=True) == []

    def test_raises_for_nonexistent_session(self, tmp_path: Path) -> None:
        db = _make_db(tmp_path)
        with pytest.raises(ValueError, match="not found"):
            db.delete_session("ghost")

    def test_raises_when_session_has_children(self, tmp_path: Path) -> None:
        """Deleting a parent with living children must raise ValueError."""
        db = _make_db(tmp_path)
        _seed(db, "parent")
        db.fork_session("parent", turn_index=0)

        with pytest.raises(ValueError, match="child session"):
            db.delete_session("parent")

    def test_parent_deletable_after_child_deleted(self, tmp_path: Path) -> None:
        """Once all children are removed, the parent can be deleted."""
        db = _make_db(tmp_path)
        _seed(db, "parent")
        child_id = db.fork_session("parent", turn_index=0)

        db.delete_session(child_id)   # leaf first
        db.delete_session("parent")   # now allowed

        assert db.list_sessions(include_archived=True) == []

    def test_grandchild_blocks_intermediate_delete(self, tmp_path: Path) -> None:
        """Leaf-first order required: child can't be deleted while it has its own child."""
        db = _make_db(tmp_path)
        _seed(db, "root")
        child_id = db.fork_session("root", turn_index=0)
        db.fork_session(child_id, turn_index=0)

        with pytest.raises(ValueError, match="child session"):
            db.delete_session(child_id)

    def test_notes_cascade_deleted(self, tmp_path: Path) -> None:
        """Deleting a session must also delete its notes."""
        db = _make_db(tmp_path)
        _seed(db, "s1")
        db.add_note("s1", "important note", "assistant")
        assert len(db.list_notes("s1")) == 1

        db.delete_session("s1")

        assert db.list_notes("s1") == []

    def test_archived_child_still_blocks_parent_delete(self, tmp_path: Path) -> None:
        """An archived child is still a child — parent deletion must be blocked."""
        db = _make_db(tmp_path)
        _seed(db, "parent")
        child_id = db.fork_session("parent", turn_index=0)
        db.archive_session(child_id)

        with pytest.raises(ValueError, match="child session"):
            db.delete_session("parent")

    def test_sibling_unaffected_by_leaf_delete(self, tmp_path: Path) -> None:
        db = _make_db(tmp_path)
        _seed(db, "root")
        child_a = db.fork_session("root", turn_index=0)
        child_b = db.fork_session("root", turn_index=1)

        db.delete_session(child_a)

        ids = [r["id"] for r in db.list_sessions(include_archived=True)]
        assert child_b in ids
        assert "root" in ids
        assert child_a not in ids


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


@pytest.fixture
def session_id(db: DatabaseManager) -> str:
    return _seed(db, "sess-1")


class TestArchiveEndpoint:
    def test_returns_200_on_success(
        self, client: TestClient, session_id: str
    ) -> None:
        resp = client.patch(f"/api/sessions/{session_id}/archive")
        assert resp.status_code == 200
        body = resp.json()
        assert body["archived"] is True
        assert body["session_id"] == session_id

    def test_session_hidden_from_default_list_after_archive(
        self, client: TestClient, session_id: str
    ) -> None:
        client.patch(f"/api/sessions/{session_id}/archive")
        resp = client.get("/api/sessions")
        ids = [s["id"] for s in resp.json()]
        assert session_id not in ids

    def test_returns_404_for_unknown_session(self, client: TestClient) -> None:
        resp = client.patch("/api/sessions/ghost/archive")
        assert resp.status_code == 404

    def test_returns_404_when_already_archived(
        self, client: TestClient, session_id: str
    ) -> None:
        client.patch(f"/api/sessions/{session_id}/archive")
        resp = client.patch(f"/api/sessions/{session_id}/archive")
        assert resp.status_code == 404

    def test_archived_at_appears_in_include_archived_list(
        self, client: TestClient, session_id: str
    ) -> None:
        client.patch(f"/api/sessions/{session_id}/archive")
        resp = client.get("/api/sessions?include_archived=true")
        rows = {r["id"]: r for r in resp.json()}
        assert rows[session_id]["archived_at"] is not None


class TestUnarchiveEndpoint:
    def test_returns_200_on_success(
        self, client: TestClient, session_id: str
    ) -> None:
        client.patch(f"/api/sessions/{session_id}/archive")
        resp = client.delete(f"/api/sessions/{session_id}/archive")
        assert resp.status_code == 200
        body = resp.json()
        assert body["archived"] is False
        assert body["session_id"] == session_id

    def test_session_reappears_in_default_list_after_unarchive(
        self, client: TestClient, session_id: str
    ) -> None:
        client.patch(f"/api/sessions/{session_id}/archive")
        client.delete(f"/api/sessions/{session_id}/archive")
        resp = client.get("/api/sessions")
        ids = [s["id"] for s in resp.json()]
        assert session_id in ids

    def test_returns_404_for_unknown_session(self, client: TestClient) -> None:
        resp = client.delete("/api/sessions/ghost/archive")
        assert resp.status_code == 404

    def test_returns_404_when_not_archived(
        self, client: TestClient, session_id: str
    ) -> None:
        resp = client.delete(f"/api/sessions/{session_id}/archive")
        assert resp.status_code == 404


class TestDeleteSessionEndpoint:
    def test_returns_204_for_leaf_session(
        self, client: TestClient, session_id: str
    ) -> None:
        resp = client.delete(f"/api/sessions/{session_id}")
        assert resp.status_code == 204

    def test_session_gone_after_delete(
        self, client: TestClient, session_id: str
    ) -> None:
        client.delete(f"/api/sessions/{session_id}")
        resp = client.get("/api/sessions?include_archived=true")
        ids = [s["id"] for s in resp.json()]
        assert session_id not in ids

    def test_returns_404_for_unknown_session(self, client: TestClient) -> None:
        resp = client.delete("/api/sessions/ghost")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_returns_409_when_children_exist(
        self, client: TestClient, db: DatabaseManager, session_id: str
    ) -> None:
        db.fork_session(session_id, turn_index=0)
        resp = client.delete(f"/api/sessions/{session_id}")
        assert resp.status_code == 409
        assert "child" in resp.json()["detail"].lower()

    def test_allowed_after_child_deleted(
        self, client: TestClient, db: DatabaseManager, session_id: str
    ) -> None:
        child_id = db.fork_session(session_id, turn_index=0)
        client.delete(f"/api/sessions/{child_id}")
        resp = client.delete(f"/api/sessions/{session_id}")
        assert resp.status_code == 204

    def test_archived_child_blocks_parent_delete(
        self, client: TestClient, db: DatabaseManager, session_id: str
    ) -> None:
        child_id = db.fork_session(session_id, turn_index=0)
        client.patch(f"/api/sessions/{child_id}/archive")
        resp = client.delete(f"/api/sessions/{session_id}")
        assert resp.status_code == 409


class TestListSessionsQueryParam:
    def test_default_excludes_archived(
        self, client: TestClient, db: DatabaseManager
    ) -> None:
        _seed(db, "live")
        _seed(db, "hidden")
        db.archive_session("hidden")

        resp = client.get("/api/sessions")
        ids = [s["id"] for s in resp.json()]
        assert "live" in ids
        assert "hidden" not in ids

    def test_include_archived_false_explicit(
        self, client: TestClient, db: DatabaseManager
    ) -> None:
        _seed(db, "live")
        _seed(db, "hidden")
        db.archive_session("hidden")

        resp = client.get("/api/sessions?include_archived=false")
        ids = [s["id"] for s in resp.json()]
        assert "hidden" not in ids

    def test_include_archived_true_shows_all(
        self, client: TestClient, db: DatabaseManager
    ) -> None:
        _seed(db, "live")
        _seed(db, "hidden")
        db.archive_session("hidden")

        resp = client.get("/api/sessions?include_archived=true")
        ids = [s["id"] for s in resp.json()]
        assert "live" in ids
        assert "hidden" in ids

    def test_archived_at_field_in_response(
        self, client: TestClient, session_id: str
    ) -> None:
        resp = client.get("/api/sessions")
        item = resp.json()[0]
        assert "archived_at" in item
        assert item["archived_at"] is None


class TestTreeQueryParam:
    def test_tree_includes_archived_by_default(
        self, client: TestClient, db: DatabaseManager
    ) -> None:
        _seed(db, "root-1")
        child_id = db.fork_session("root-1", turn_index=0)
        db.archive_session(child_id)

        tree = client.get("/api/sessions/tree").json()
        child_ids = [c["id"] for c in tree[0]["children"]]
        assert child_id in child_ids

    def test_tree_excludes_archived_when_false(
        self, client: TestClient, db: DatabaseManager
    ) -> None:
        _seed(db, "root-1")
        child_id = db.fork_session("root-1", turn_index=0)
        db.archive_session(child_id)

        tree = client.get("/api/sessions/tree?include_archived=false").json()
        child_ids = [c["id"] for c in tree[0]["children"]]
        assert child_id not in child_ids

    def test_archived_node_has_archived_at_set(
        self, client: TestClient, db: DatabaseManager
    ) -> None:
        _seed(db, "root-1")
        child_id = db.fork_session("root-1", turn_index=0)
        db.archive_session(child_id)

        tree = client.get("/api/sessions/tree").json()
        child_node = tree[0]["children"][0]
        assert child_node["archived_at"] is not None
