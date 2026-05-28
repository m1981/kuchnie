"""
tests/test_main.py
==================
Integration tests for *all* FastAPI routes in src/main.py.

Uses FastAPI's TestClient (synchronous wrapper around the ASGI app) so async
endpoints are exercised without spinning up a real server.

Covers every previously-uncovered line:
 - get_db / get_chat_service DI constructors         (lines 66, 71)
 - _resolve_data_path path-traversal guard            (line 143)
 - GET  /api/sessions                                 (line 154)
 - GET  /api/sessions/{id}                            (lines 163-165)
 - GET  /api/sessions/{id}/export  success + 404      (lines 177-181)
 - POST /api/sessions/{id}/fork    success + 400      (lines 191-195)
 - GET  /api/files  when data_dir missing             (line 206)
 - GET  /api/files/{path}                             (lines 191-195)
 - PUT  /api/files/{path}  404                        (line 206)
 - POST /api/files/append  error branch               (line 244)
 - GET  /api/repo-map      error branch               (line 253)
 - POST /api/chat          success, with images+context, 500 (lines 272-294)
"""
import json
from functools import partial
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

import src.main as main_module
from src import config as config_module
from src.chat_service import ChatService
from src.db import DatabaseManager
from src.main import app, get_db, get_chat_service


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    """Temporary knowledge base with two sample .md files."""
    (tmp_path / "materials.md").write_text("# Materials\n18mm Birch.\n", encoding="utf-8")
    (tmp_path / "hardware.md").write_text("# Hardware\nBlum hinges.\n", encoding="utf-8")
    return tmp_path


@pytest.fixture
def client(data_dir: Path, monkeypatch) -> TestClient:
    """TestClient whose settings.data_dir is redirected to *data_dir*."""
    monkeypatch.setattr(config_module.settings, "data_dir", data_dir)
    monkeypatch.setattr(main_module.settings, "data_dir", data_dir)
    return TestClient(app)


@pytest.fixture
def db(tmp_path: Path) -> DatabaseManager:
    return DatabaseManager(db_path=str(tmp_path / "test.db"))


# ---------------------------------------------------------------------------
# DI factory functions (lines 66, 71)
# ---------------------------------------------------------------------------

def test_get_db_returns_database_manager() -> None:
    """get_db() must return a DatabaseManager instance."""
    result = get_db()
    assert isinstance(result, DatabaseManager)


def test_get_chat_service_returns_chat_service() -> None:
    """get_chat_service() must return a ChatService wired to the provided db."""
    db = get_db()
    svc = get_chat_service(db)
    assert isinstance(svc, ChatService)


# ---------------------------------------------------------------------------
# GET /api/sessions  (line 154)
# ---------------------------------------------------------------------------

def test_get_sessions_empty(tmp_path: Path, monkeypatch) -> None:
    """Returns an empty list when no sessions have been saved."""
    # Use a fresh DB by wiring DI directly — avoids mutating the property.
    fresh_db = DatabaseManager(db_path=str(tmp_path / "empty.db"))
    monkeypatch.setattr(config_module.settings, "data_dir", tmp_path)
    monkeypatch.setattr(main_module.settings, "data_dir", tmp_path)
    app.dependency_overrides[get_db] = lambda: fresh_db
    try:
        resp = TestClient(app).get("/api/sessions")
        assert resp.status_code == 200
        assert resp.json() == []
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_get_sessions_with_data(tmp_path: Path, monkeypatch) -> None:
    """Returns the seeded sessions list."""
    db = DatabaseManager(db_path=str(tmp_path / "t.db"))
    db.save_session("s1", "First", "[]", "[]")

    monkeypatch.setattr(config_module.settings, "data_dir", tmp_path)
    monkeypatch.setattr(main_module.settings, "data_dir", tmp_path)
    app.dependency_overrides[get_db] = lambda: db
    try:
        c = TestClient(app)
        resp = c.get("/api/sessions")
        assert resp.status_code == 200
        ids = [s["id"] for s in resp.json()]
        assert "s1" in ids
    finally:
        app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# GET /api/sessions/{session_id}  (lines 163-165)
# ---------------------------------------------------------------------------

def test_get_session_existing(tmp_path: Path, monkeypatch) -> None:
    db = DatabaseManager(db_path=str(tmp_path / "t.db"))
    ui = [{"role": "user", "content": "Hello"}]
    db.save_session("abc", "Chat", "[]", json.dumps(ui))

    monkeypatch.setattr(config_module.settings, "data_dir", tmp_path)
    monkeypatch.setattr(main_module.settings, "data_dir", tmp_path)
    app.dependency_overrides[get_db] = lambda: db
    try:
        resp = TestClient(app).get("/api/sessions/abc")
        assert resp.status_code == 200
        assert resp.json()["ui_messages"] == ui
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_get_session_nonexistent_returns_empty(tmp_path: Path, monkeypatch) -> None:
    db = DatabaseManager(db_path=str(tmp_path / "t.db"))
    monkeypatch.setattr(config_module.settings, "data_dir", tmp_path)
    monkeypatch.setattr(main_module.settings, "data_dir", tmp_path)
    app.dependency_overrides[get_db] = lambda: db
    try:
        resp = TestClient(app).get("/api/sessions/nonexistent")
        assert resp.status_code == 200
        assert resp.json() == {"ui_messages": []}
    finally:
        app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# GET /api/sessions/{id}/export  (lines 177-181)
# ---------------------------------------------------------------------------

def test_export_session_success(tmp_path: Path, monkeypatch) -> None:
    db = DatabaseManager(db_path=str(tmp_path / "t.db"))
    db.save_session("e1", "My Export", "[]",
                    json.dumps([{"role": "user", "content": "hi"}]))

    monkeypatch.setattr(config_module.settings, "data_dir", tmp_path)
    monkeypatch.setattr(main_module.settings, "data_dir", tmp_path)
    app.dependency_overrides[get_db] = lambda: db
    try:
        resp = TestClient(app).get("/api/sessions/e1/export")
        assert resp.status_code == 200
        assert "My Export" in resp.text
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_export_session_not_found(tmp_path: Path, monkeypatch) -> None:
    db = DatabaseManager(db_path=str(tmp_path / "t.db"))
    monkeypatch.setattr(config_module.settings, "data_dir", tmp_path)
    monkeypatch.setattr(main_module.settings, "data_dir", tmp_path)
    app.dependency_overrides[get_db] = lambda: db
    try:
        resp = TestClient(app).get("/api/sessions/nobody/export")
        assert resp.status_code == 404
    finally:
        app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# POST /api/sessions/{id}/fork  (lines 191-195)
# ---------------------------------------------------------------------------

def test_fork_session_success(tmp_path: Path, monkeypatch) -> None:
    db = DatabaseManager(db_path=str(tmp_path / "t.db"))
    ui = [{"role": "user", "content": "t0"}, {"role": "assistant", "content": "r0"}]
    db.save_session("src1", "Original", "[]", json.dumps(ui))

    monkeypatch.setattr(config_module.settings, "data_dir", tmp_path)
    monkeypatch.setattr(main_module.settings, "data_dir", tmp_path)
    app.dependency_overrides[get_db] = lambda: db
    try:
        resp = TestClient(app).post("/api/sessions/src1/fork",
                                    json={"turn_index": 0})
        assert resp.status_code == 200
        body = resp.json()
        assert "new_session_id" in body
        assert body["new_session_id"] != "src1"
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_fork_session_invalid_index(tmp_path: Path, monkeypatch) -> None:
    db = DatabaseManager(db_path=str(tmp_path / "t.db"))
    db.save_session("src2", "Src", "[]", "[]")

    monkeypatch.setattr(config_module.settings, "data_dir", tmp_path)
    monkeypatch.setattr(main_module.settings, "data_dir", tmp_path)
    app.dependency_overrides[get_db] = lambda: db
    try:
        resp = TestClient(app).post("/api/sessions/src2/fork",
                                    json={"turn_index": -1})
        assert resp.status_code == 400
    finally:
        app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# _resolve_data_path — path traversal guard (line 143)
# ---------------------------------------------------------------------------

def test_path_traversal_blocked(data_dir: Path, monkeypatch) -> None:
    """_resolve_data_path raises 400 when the resolved path escapes data_dir."""
    # HTTP clients normalise paths before sending, so we test the guard function
    # directly rather than through an HTTP request.
    from src.main import _resolve_data_path
    from fastapi import HTTPException

    # A path that resolves outside settings.data_dir must raise 400.
    monkeypatch.setattr(config_module.settings, "data_dir", data_dir)
    monkeypatch.setattr(main_module.settings, "data_dir", data_dir)

    with pytest.raises(HTTPException) as exc_info:
        _resolve_data_path("../../../etc/passwd")
    assert exc_info.value.status_code == 400
    assert "Path traversal" in exc_info.value.detail


# ---------------------------------------------------------------------------
# GET /api/files  when data_dir does not exist (line 206)
# ---------------------------------------------------------------------------

def test_list_files_missing_data_dir(tmp_path: Path, monkeypatch) -> None:
    missing = tmp_path / "does_not_exist"
    monkeypatch.setattr(config_module.settings, "data_dir", missing)
    monkeypatch.setattr(main_module.settings, "data_dir", missing)
    resp = TestClient(app).get("/api/files")
    assert resp.status_code == 200
    assert resp.json() == []


# ---------------------------------------------------------------------------
# GET /api/files  (existing — kept for completeness)
# ---------------------------------------------------------------------------

def test_list_files_returns_md_files(client: TestClient) -> None:
    resp = client.get("/api/files")
    assert resp.status_code == 200
    names = [i["name"] for i in resp.json()]
    assert "materials.md" in names
    assert "hardware.md" in names


# ---------------------------------------------------------------------------
# GET /api/files/{filepath}
# ---------------------------------------------------------------------------

def test_read_file_endpoint_success(client: TestClient) -> None:
    resp = client.get("/api/files/materials.md")
    assert resp.status_code == 200
    assert "Birch" in resp.json()["content"]


def test_read_file_endpoint_not_found(client: TestClient) -> None:
    resp = client.get("/api/files/ghost.md")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PUT /api/files/{filepath}  404 branch (line ~230)
# ---------------------------------------------------------------------------

def test_write_file_endpoint_success(client: TestClient, data_dir: Path) -> None:
    resp = client.put("/api/files/materials.md", json={"content": "# New\n"})
    assert resp.status_code == 200
    assert "success" in resp.json() or "Success" in str(resp.json())


def test_write_file_endpoint_not_found(client: TestClient) -> None:
    resp = client.put("/api/files/ghost.md", json={"content": "x"})
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/files/append  — error branch (line 244)
# ---------------------------------------------------------------------------

def test_append_error_branch(client: TestClient, monkeypatch) -> None:
    """When append_to_file returns an error dict, the endpoint must return 400."""
    monkeypatch.setattr(
        main_module,
        "append_to_file",
        lambda filepath, content: {"error": "simulated write failure"},
    )
    resp = client.post("/api/files/append",
                       json={"filepath": "materials.md", "content": "x"})
    assert resp.status_code == 400
    assert "simulated write failure" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# GET /api/repo-map  — error branch (line 253)
# ---------------------------------------------------------------------------

def test_repo_map_error_branch(client: TestClient, monkeypatch) -> None:
    """When get_repo_map returns an error dict, the endpoint must return 500."""
    monkeypatch.setattr(
        main_module,
        "get_repo_map",
        lambda base_dir=None: {"error": "scan failed"},
    )
    resp = client.get("/api/repo-map")
    assert resp.status_code == 500
    assert "scan failed" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# POST /api/chat  (lines 272-294)
# ---------------------------------------------------------------------------

def _chat_override(text: str = "Great answer", tools: list | None = None):
    """Returns a ChatService dependency override that yields a canned response."""
    svc = MagicMock(spec=ChatService)
    svc.handle_turn.return_value = (text, tools or [])
    return lambda: svc


def test_chat_basic_success(tmp_path: Path, monkeypatch) -> None:
    """A minimal chat POST must return text and tools_used."""
    monkeypatch.setattr(config_module.settings, "data_dir", tmp_path)
    monkeypatch.setattr(main_module.settings, "data_dir", tmp_path)
    app.dependency_overrides[get_chat_service] = _chat_override("Hello back")
    try:
        resp = TestClient(app).post("/api/chat", json={
            "session_id": "sess-1",
            "message": "Hello",
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["text"] == "Hello back"
        assert body["tools_used"] == []
    finally:
        app.dependency_overrides.pop(get_chat_service, None)


def test_chat_with_images_and_context(tmp_path: Path, monkeypatch) -> None:
    """Images and context_files must be forwarded to handle_turn."""
    monkeypatch.setattr(config_module.settings, "data_dir", tmp_path)
    monkeypatch.setattr(main_module.settings, "data_dir", tmp_path)

    captured: dict = {}

    class CapturingSvc:
        def handle_turn(self, **kwargs):
            captured.update(kwargs)
            return ("done", [])

    app.dependency_overrides[get_chat_service] = lambda: CapturingSvc()
    try:
        import base64
        img_b64 = base64.b64encode(b"PNG").decode()
        resp = TestClient(app).post("/api/chat", json={
            "session_id": "sess-2",
            "message": "look at this",
            "images": [{"mime_type": "image/png", "data": img_b64}],
            "context_files": ["data/materials.md"],
        })
        assert resp.status_code == 200
        assert captured.get("images") is not None
        assert captured.get("context_files") == ["data/materials.md"]
    finally:
        app.dependency_overrides.pop(get_chat_service, None)


def test_chat_with_tools_used(tmp_path: Path, monkeypatch) -> None:
    """Tool logs from the service are serialised into the response."""
    monkeypatch.setattr(config_module.settings, "data_dir", tmp_path)
    monkeypatch.setattr(main_module.settings, "data_dir", tmp_path)

    tool_log = {"name": "read_file", "args": {"filepath": "x.md"}, "result": {"content": "ok"}}
    app.dependency_overrides[get_chat_service] = _chat_override("answer", [tool_log])
    try:
        resp = TestClient(app).post("/api/chat", json={
            "session_id": "sess-3",
            "message": "read x",
        })
        assert resp.status_code == 200
        assert resp.json()["tools_used"][0]["name"] == "read_file"
    finally:
        app.dependency_overrides.pop(get_chat_service, None)


def test_chat_service_exception_returns_500(tmp_path: Path, monkeypatch) -> None:
    """When handle_turn raises, the endpoint must return 500 (lines 290-292)."""
    monkeypatch.setattr(config_module.settings, "data_dir", tmp_path)
    monkeypatch.setattr(main_module.settings, "data_dir", tmp_path)

    class BoomSvc:
        def handle_turn(self, **kwargs):
            raise RuntimeError("model meltdown")

    app.dependency_overrides[get_chat_service] = lambda: BoomSvc()
    try:
        resp = TestClient(app).post("/api/chat", json={
            "session_id": "sess-err",
            "message": "crash",
        })
        assert resp.status_code == 500
        assert "model meltdown" in resp.json()["detail"]
    finally:
        app.dependency_overrides.pop(get_chat_service, None)
