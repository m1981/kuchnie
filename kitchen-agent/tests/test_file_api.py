"""
Tests for the file-management REST endpoints:
  GET  /api/files
  GET  /api/files/{path}
  PUT  /api/files/{path}
  POST /api/files/append
  GET  /api/repo-map
"""
import json
import pytest
from pathlib import Path
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    """
    Point the app's DATA_DIR to a temporary directory and create sample files.
    We monkeypatch main.DATA_DIR before importing the app so the endpoints use
    the temp directory.
    """
    (tmp_path / "materials.md").write_text("# Materials\n\n18mm Birch Plywood.\n", encoding="utf-8")
    (tmp_path / "hardware.md").write_text("# Hardware\n\nBlum hinges.\n", encoding="utf-8")
    return tmp_path


@pytest.fixture
def client(data_dir, monkeypatch):
    import src.main as main_module

    monkeypatch.setattr(main_module, "DATA_DIR", data_dir)
    from fastapi.testclient import TestClient
    return TestClient(main_module.app)


# ---------------------------------------------------------------------------
# GET /api/files
# ---------------------------------------------------------------------------

def test_list_files_returns_md_files(client):
    resp = client.get("/api/files")
    assert resp.status_code == 200
    paths = [item["path"] for item in resp.json()]
    # Both files should appear (path contains the name)
    names = [item["name"] for item in resp.json()]
    assert "materials.md" in names
    assert "hardware.md" in names


def test_list_files_empty_dir(tmp_path, monkeypatch):
    import src.main as main_module
    monkeypatch.setattr(main_module, "DATA_DIR", tmp_path)
    from fastapi.testclient import TestClient
    c = TestClient(main_module.app)
    resp = c.get("/api/files")
    assert resp.status_code == 200
    assert resp.json() == []


# ---------------------------------------------------------------------------
# GET /api/files/{filepath}
# ---------------------------------------------------------------------------

def test_read_file_returns_content(client, data_dir):
    resp = client.get("/api/files/materials.md")
    assert resp.status_code == 200
    body = resp.json()
    assert body["filepath"] == "materials.md"
    assert "Birch Plywood" in body["content"]


def test_read_file_not_found(client):
    resp = client.get("/api/files/nonexistent.md")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PUT /api/files/{filepath}
# ---------------------------------------------------------------------------

def test_write_file_updates_content(client, data_dir):
    new_content = "# Materials\n\nUpdated content.\n"
    resp = client.put("/api/files/materials.md", json={"content": new_content})
    assert resp.status_code == 200
    assert "success" in resp.json() or "Success" in str(resp.json())

    # Verify the file was actually written
    written = (data_dir / "materials.md").read_text(encoding="utf-8")
    assert "Updated content" in written


def test_write_file_not_found(client):
    resp = client.put("/api/files/ghost.md", json={"content": "hello"})
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/files/append
# ---------------------------------------------------------------------------

def test_append_adds_content(client, data_dir):
    payload = {
        "filepath": str(data_dir / "materials.md"),
        "content": "\n## Appended\n\nHighlighted snippet.\n",
    }
    resp = client.post("/api/files/append", json=payload)
    assert resp.status_code == 200

    written = (data_dir / "materials.md").read_text(encoding="utf-8")
    assert "Highlighted snippet" in written


# ---------------------------------------------------------------------------
# GET /api/repo-map
# ---------------------------------------------------------------------------

def test_repo_map_returns_content(client, monkeypatch, data_dir):
    # Monkeypatch get_repo_map used inside the endpoint
    import src.main as main_module

    monkeypatch.setattr(main_module, "get_repo_map", lambda: {"content": "=== materials.md ===\n1: # Materials"})
    from fastapi.testclient import TestClient
    c = TestClient(main_module.app)
    resp = c.get("/api/repo-map")
    assert resp.status_code == 200
    assert "content" in resp.json()
