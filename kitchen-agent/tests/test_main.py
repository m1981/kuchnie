"""
tests/test_main.py
==================
"""

import json
from functools import partial
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient
import src.main
from src import config
from src.chat_service import ChatService
from src.repositories import SQLiteConnection, SQLiteSessionRepository
from src.main import app, get_session_repo, get_chat_service
from src.main import _resolve_data_path
from fastapi import HTTPException
import base64

import src.main as main_module
import src.config as config_module


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    (tmp_path / "materials.md").write_text("# Materials\n18mm Birch.\n", encoding="utf-8")
    (tmp_path / "hardware.md").write_text("# Hardware\nBlum hinges.\n", encoding="utf-8")
    return tmp_path


@pytest.fixture
def client(data_dir: Path, monkeypatch) -> TestClient:
    monkeypatch.setattr(config_module.settings, "data_dir", data_dir)
    monkeypatch.setattr(main_module.settings, "data_dir", data_dir)
    return TestClient(app)


# ---------------------------------------------------------------------------
# DI factory functions
# ---------------------------------------------------------------------------

def test_get_session_repo_returns_repo() -> None:
    result = get_session_repo()
    assert isinstance(result, SQLiteSessionRepository)


def test_get_chat_service_returns_chat_service() -> None:
    repo = get_session_repo()
    svc = get_chat_service(repo)
    assert isinstance(svc, ChatService)


# ---------------------------------------------------------------------------
# GET /api/sessions
# ---------------------------------------------------------------------------

def test_get_sessions_empty(tmp_path: Path, monkeypatch) -> None:
    conn = SQLiteConnection(db_path=str(tmp_path / "empty.db"))
    repo = SQLiteSessionRepository(conn)
    monkeypatch.setattr(config_module.settings, "data_dir", tmp_path)
    monkeypatch.setattr(main_module.settings, "data_dir", tmp_path)
    app.dependency_overrides[get_session_repo] = lambda: repo
    try:
        resp = TestClient(app).get("/api/sessions")
        assert resp.status_code == 200
        assert resp.json() == []
    finally:
        app.dependency_overrides.pop(get_session_repo, None)


def test_get_sessions_with_data(tmp_path: Path, monkeypatch) -> None:
    conn = SQLiteConnection(db_path=str(tmp_path / "t.db"))
    repo = SQLiteSessionRepository(conn)
    repo.save_session("s1", "First", "[]", "[]")

    monkeypatch.setattr(config_module.settings, "data_dir", tmp_path)
    monkeypatch.setattr(main_module.settings, "data_dir", tmp_path)
    app.dependency_overrides[get_session_repo] = lambda: repo
    try:
        c = TestClient(app)
        resp = c.get("/api/sessions")
        ids = [s["id"] for s in resp.json()]
        assert "s1" in ids
    finally:
        app.dependency_overrides.pop(get_session_repo, None)


# ---------------------------------------------------------------------------
# GET /api/sessions/{session_id}
# ---------------------------------------------------------------------------

def test_get_session_existing(tmp_path: Path, monkeypatch) -> None:
    conn = SQLiteConnection(db_path=str(tmp_path / "t.db"))
    repo = SQLiteSessionRepository(conn)
    ui = [{"role": "user", "content": "Hello"}]
    repo.save_session("abc", "Chat", "[]", json.dumps(ui))

    monkeypatch.setattr(config_module.settings, "data_dir", tmp_path)
    monkeypatch.setattr(main_module.settings, "data_dir", tmp_path)
    app.dependency_overrides[get_session_repo] = lambda: repo
    try:
        resp = TestClient(app).get("/api/sessions/abc")
        assert resp.json()["ui_messages"] == ui
    finally:
        app.dependency_overrides.pop(get_session_repo, None)


def test_get_session_nonexistent_returns_empty(tmp_path: Path, monkeypatch) -> None:
    conn = SQLiteConnection(db_path=str(tmp_path / "t.db"))
    repo = SQLiteSessionRepository(conn)
    monkeypatch.setattr(config_module.settings, "data_dir", tmp_path)
    monkeypatch.setattr(main_module.settings, "data_dir", tmp_path)
    app.dependency_overrides[get_session_repo] = lambda: repo
    try:
        resp = TestClient(app).get("/api/sessions/nonexistent")
        assert resp.status_code == 200
        assert resp.json()["ui_messages"] == []
    finally:
        app.dependency_overrides.pop(get_session_repo, None)


# ---------------------------------------------------------------------------
# GET /api/sessions/{session_id}/export
# ---------------------------------------------------------------------------

def test_export_session_success(tmp_path: Path, monkeypatch) -> None:
    conn = SQLiteConnection(db_path=str(tmp_path / "t.db"))
    repo = SQLiteSessionRepository(conn)
    ui = [{"role": "user", "content": "Hello"}]
    repo.save_session("s1", "Export Chat", "[]", json.dumps(ui))

    monkeypatch.setattr(config_module.settings, "data_dir", tmp_path)
    monkeypatch.setattr(main_module.settings, "data_dir", tmp_path)
    app.dependency_overrides[get_session_repo] = lambda: repo
    try:
        resp = TestClient(app).get("/api/sessions/s1/export")
        assert resp.status_code == 200
        assert "Export Chat" in resp.text
    finally:
        app.dependency_overrides.pop(get_session_repo, None)


def test_export_session_not_found(tmp_path: Path, monkeypatch) -> None:
    conn = SQLiteConnection(db_path=str(tmp_path / "t.db"))
    repo = SQLiteSessionRepository(conn)
    monkeypatch.setattr(config_module.settings, "data_dir", tmp_path)
    monkeypatch.setattr(main_module.settings, "data_dir", tmp_path)
    app.dependency_overrides[get_session_repo] = lambda: repo
    try:
        resp = TestClient(app).get("/api/sessions/ghost/export")
        assert resp.status_code == 404
    finally:
        app.dependency_overrides.pop(get_session_repo, None)


# ---------------------------------------------------------------------------
# POST /api/sessions/{session_id}/fork
# ---------------------------------------------------------------------------

def test_fork_session_success(tmp_path: Path, monkeypatch) -> None:
    conn = SQLiteConnection(db_path=str(tmp_path / "t.db"))
    repo = SQLiteSessionRepository(conn)
    ui = [{"role": "user", "content": "a"}, {"role": "assistant", "content": "b"}]
    repo.save_session("s1", "T", "[]", json.dumps(ui))

    monkeypatch.setattr(config_module.settings, "data_dir", tmp_path)
    monkeypatch.setattr(main_module.settings, "data_dir", tmp_path)
    app.dependency_overrides[get_session_repo] = lambda: repo
    try:
        resp = TestClient(app).post("/api/sessions/s1/fork", json={"turn_index": 0})
        assert resp.status_code == 200
        assert "new_session_id" in resp.json()
    finally:
        app.dependency_overrides.pop(get_session_repo, None)


def test_fork_session_invalid_index(tmp_path: Path, monkeypatch) -> None:
    conn = SQLiteConnection(db_path=str(tmp_path / "t.db"))
    repo = SQLiteSessionRepository(conn)
    monkeypatch.setattr(config_module.settings, "data_dir", tmp_path)
    monkeypatch.setattr(main_module.settings, "data_dir", tmp_path)
    app.dependency_overrides[get_session_repo] = lambda: repo
    try:
        resp = TestClient(app).post("/api/sessions/missing/fork", json={"turn_index": 0})
        assert resp.status_code == 400
    finally:
        app.dependency_overrides.pop(get_session_repo, None)


# ---------------------------------------------------------------------------
# Path traversal guard
# ---------------------------------------------------------------------------

def test_path_traversal_blocked(data_dir: Path, monkeypatch) -> None:
    from src.main import _resolve_data_path
    from fastapi import HTTPException

    monkeypatch.setattr(config_module.settings, "data_dir", data_dir)
    monkeypatch.setattr(main_module.settings, "data_dir", data_dir)

    with pytest.raises(HTTPException) as exc_info:
        _resolve_data_path("../../../etc/passwd")
    assert exc_info.value.status_code == 400
    assert "Path traversal" in exc_info.value.detail


# ---------------------------------------------------------------------------
# GET /api/files  when data_dir does not exist
# ---------------------------------------------------------------------------

def test_list_files_missing_data_dir(tmp_path: Path, monkeypatch) -> None:
    missing = tmp_path / "nonexistent"
    monkeypatch.setattr(config_module.settings, "data_dir", missing)
    monkeypatch.setattr(main_module.settings, "data_dir", missing)
    resp = TestClient(app).get("/api/files")
    assert resp.status_code == 200
    assert resp.json() == []


# ---------------------------------------------------------------------------
# GET /api/files
# ---------------------------------------------------------------------------

def test_list_files_returns_md_files(client: TestClient) -> None:
    resp = client.get("/api/files")
    assert resp.status_code == 200
    names = [f["name"] for f in resp.json()]
    assert "materials.md" in names


# ---------------------------------------------------------------------------
# GET /api/files/{filepath}
# ---------------------------------------------------------------------------

def test_read_file_endpoint_success(client: TestClient) -> None:
    resp = client.get("/api/files/materials.md")
    assert resp.status_code == 200
    assert "18mm Birch" in resp.json()["content"]


def test_read_file_endpoint_not_found(client: TestClient) -> None:
    resp = client.get("/api/files/nonexistent.md")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PUT /api/files/{filepath}
# ---------------------------------------------------------------------------

def test_write_file_endpoint_success(client: TestClient, data_dir: Path) -> None:
    resp = client.put("/api/files/materials.md", json={"content": "# New\n"})
    assert resp.status_code == 200
    assert (data_dir / "materials.md").read_text() == "# New\n"


def test_write_file_endpoint_not_found(client: TestClient) -> None:
    resp = client.put("/api/files/ghost.md", json={"content": "x"})
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/files/append — error branch
# ---------------------------------------------------------------------------

def test_append_error_branch(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(
        main_module,
        "append_to_file",
        lambda filepath, content: {"error": "simulated write failure"},
    )
    resp = client.post("/api/files/append", json={"filepath": "materials.md", "content": "x"})
    assert resp.status_code == 400
    assert "simulated write failure" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# GET /api/repo-map
# ---------------------------------------------------------------------------

def test_repo_map_error_branch(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(
        main_module,
        "get_repo_map",
        lambda base_dir=None: {"error": "scan failed"},
    )
    resp = client.get("/api/repo-map")
    assert resp.status_code == 500
    assert "scan failed" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# POST /api/chat
# ---------------------------------------------------------------------------

def _chat_override(text: str = "Great answer", tools: list | None = None):
    svc = MagicMock(spec=ChatService)
    svc.handle_turn.return_value = (text, tools or [])
    return lambda: svc


def test_chat_basic_success(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(config_module.settings, "data_dir", tmp_path)
    monkeypatch.setattr(main_module.settings, "data_dir", tmp_path)
    app.dependency_overrides[get_chat_service] = _chat_override("Hello back")
    try:
        resp = TestClient(app).post("/api/chat", json={
            "session_id": "sess-1",
            "message": "hello",
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["text"] == "Hello back"
        assert body["tools_used"] == []
    finally:
        app.dependency_overrides.pop(get_chat_service, None)


def test_chat_with_images_and_context(tmp_path: Path, monkeypatch) -> None:
    """
    Context files sent as bare names (relative to data_dir, as the frontend does)
    must be resolved to absolute paths before reaching the service.

    The assertion checks:
      - images are forwarded as-is
      - context_files list has exactly 1 entry
      - the path is absolute and inside data_dir
      - the filename is correct
    """
    monkeypatch.setattr(config_module.settings, "data_dir", tmp_path)
    monkeypatch.setattr(main_module.settings, "data_dir", tmp_path)

    captured: dict = {}

    class CapturingSvc:
        def handle_turn(self, **kwargs):
            captured.update(kwargs)
            return ("done", [])

    app.dependency_overrides[get_chat_service] = lambda: CapturingSvc()
    try:
        img_b64 = base64.b64encode(b"PNG").decode()
        resp = TestClient(app).post("/api/chat", json={
            "session_id": "sess-2",
            "message": "look at this",
            "images": [{"mime_type": "image/png", "data": img_b64}],
            # Frontend sends bare name (relative to data_dir, NOT "data/materials.md")
            "context_files": ["materials.md"],
        })
        assert resp.status_code == 200
        assert captured.get("images") is not None

        # After the fix: path is resolved to absolute path under data_dir
        ctx = captured.get("context_files")
        assert ctx is not None and len(ctx) == 1
        resolved = Path(ctx[0])
        assert resolved.is_absolute(), f"Expected absolute path, got: {ctx[0]!r}"
        assert resolved.name == "materials.md"
        assert str(resolved).startswith(str(tmp_path.resolve()))
    finally:
        app.dependency_overrides.pop(get_chat_service, None)


def test_chat_with_tools_used(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(config_module.settings, "data_dir", tmp_path)
    monkeypatch.setattr(main_module.settings, "data_dir", tmp_path)
    tool_log = {"name": "read_file", "args": {"filepath": "x.md"}, "result": {"content": "ok"}}
    app.dependency_overrides[get_chat_service] = _chat_override("answer", [tool_log])
    try:
        resp = TestClient(app).post("/api/chat", json={
            "session_id": "sess-3",
            "message": "do something",
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["text"] == "answer"
        assert len(body["tools_used"]) == 1
        assert body["tools_used"][0]["name"] == "read_file"
    finally:
        app.dependency_overrides.pop(get_chat_service, None)


def test_chat_service_exception_returns_500(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(config_module.settings, "data_dir", tmp_path)
    monkeypatch.setattr(main_module.settings, "data_dir", tmp_path)

    class BoomSvc:
        def handle_turn(self, **kwargs):
            raise RuntimeError("kaboom")

    app.dependency_overrides[get_chat_service] = lambda: BoomSvc()
    try:
        resp = TestClient(app).post("/api/chat", json={
            "session_id": "sess-4",
            "message": "boom",
        })
        assert resp.status_code == 500
    finally:
        app.dependency_overrides.pop(get_chat_service, None)
