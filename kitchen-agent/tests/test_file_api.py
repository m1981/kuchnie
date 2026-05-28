"""
tests/test_file_api.py
======================
Integration tests for the file-management REST endpoints:

  GET  /api/files
  GET  /api/files/{path}
  PUT  /api/files/{path}
  POST /api/files/append
  GET  /api/repo-map
"""
import pytest
from pathlib import Path
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    """Creates a temporary knowledge base with two sample files."""
    (tmp_path / "materials.md").write_text(
        "# Materials\n\n18mm Birch Plywood.\n", encoding="utf-8"
    )
    (tmp_path / "hardware.md").write_text(
        "# Hardware\n\nBlum hinges.\n", encoding="utf-8"
    )
    return tmp_path


@pytest.fixture
def client(data_dir: Path, monkeypatch) -> TestClient:
    """Returns a TestClient whose DATA_DIR is pointed at *data_dir*."""
    import src.main as main_module
    from src import config as config_module

    # Patch settings.data_dir in both the config singleton and main module.
    monkeypatch.setattr(config_module.settings, "data_dir", data_dir)
    monkeypatch.setattr(main_module.settings, "data_dir", data_dir)

    return TestClient(main_module.app)


# ---------------------------------------------------------------------------
# GET /api/files
# ---------------------------------------------------------------------------

def test_list_files_returns_md_files(client: TestClient) -> None:
    resp = client.get("/api/files")
    assert resp.status_code == 200
    items = resp.json()
    names = [item["name"] for item in items]
    paths = [item["path"] for item in items]
    assert "materials.md" in names
    assert "hardware.md" in names
    # paths must be relative to DATA_DIR — no absolute prefix.
    for path in paths:
        assert not path.startswith("/"), f"Expected relative path, got: {path}"


def test_list_files_empty_dir(tmp_path: Path, monkeypatch) -> None:
    import src.main as main_module
    from src import config as config_module

    monkeypatch.setattr(config_module.settings, "data_dir", tmp_path)
    monkeypatch.setattr(main_module.settings, "data_dir", tmp_path)

    c = TestClient(main_module.app)
    resp = c.get("/api/files")
    assert resp.status_code == 200
    assert resp.json() == []


# ---------------------------------------------------------------------------
# GET /api/files/{filepath}
# ---------------------------------------------------------------------------

def test_read_file_returns_content(client: TestClient, data_dir: Path) -> None:
    resp = client.get("/api/files/materials.md")
    assert resp.status_code == 200
    body = resp.json()
    assert body["filepath"] == "materials.md"
    assert "Birch Plywood" in body["content"]


def test_read_file_not_found(client: TestClient) -> None:
    resp = client.get("/api/files/nonexistent.md")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PUT /api/files/{filepath}
# ---------------------------------------------------------------------------

def test_write_file_updates_content(client: TestClient, data_dir: Path) -> None:
    new_content = "# Materials\n\nUpdated content.\n"
    resp = client.put("/api/files/materials.md", json={"content": new_content})
    assert resp.status_code == 200
    assert "success" in resp.json() or "Success" in str(resp.json())

    written = (data_dir / "materials.md").read_text(encoding="utf-8")
    assert "Updated content" in written


def test_write_file_not_found(client: TestClient) -> None:
    resp = client.put("/api/files/ghost.md", json={"content": "hello"})
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/files/append
# ---------------------------------------------------------------------------

def test_append_adds_content(client: TestClient, data_dir: Path) -> None:
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

def test_repo_map_returns_content(monkeypatch, data_dir: Path) -> None:
    import src.main as main_module
    from src import config as config_module

    monkeypatch.setattr(config_module.settings, "data_dir", data_dir)
    monkeypatch.setattr(main_module.settings, "data_dir", data_dir)
    monkeypatch.setattr(
        main_module,
        "get_repo_map",
        lambda base_dir=None: {"content": "=== materials.md ===\n1: # Materials"},
    )

    c = TestClient(main_module.app)
    resp = c.get("/api/repo-map")
    assert resp.status_code == 200
    assert "content" in resp.json()
