"""
tests/test_prompt_routes.py
============================
TDD tests for F05 backend-prompt endpoints and the updated /api/chat flow.

Tests are written RED-first before the implementation exists.

Coverage contract:
  GET  /api/prompts/modes        — returns list[{id, label, eyebrow}]
  POST /api/prompts/reload       — hot-reloads files; returns {success: true}
  POST /api/chat with mode_id    — resolves mode_id → system_instruction via PromptManager
  POST /api/chat backward compat — system_prompt field still accepted (legacy)
  Dependency override ensures PromptManager is isolated from real disk
"""
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

import src.main as main_module
from src import config as config_module
from src.main import app, get_chat_service, get_prompt_manager
from src.prompt_manager import PromptManager, PromptMode


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _make_prompt_manager(tmp_path: Path) -> PromptManager:
    """Create an isolated PromptManager backed by tmp_path prompt files."""
    (tmp_path / "base_agent_rules.md").write_text("BASE RULES\n", encoding="utf-8")
    (tmp_path / "general.md").write_text("GENERAL CONTENT\n", encoding="utf-8")
    (tmp_path / "design.md").write_text("DESIGN CONTENT\n", encoding="utf-8")
    (tmp_path / "assembly.md").write_text("ASSEMBLY CONTENT\n", encoding="utf-8")
    return PromptManager(prompts_dir=str(tmp_path))


def _stub_chat_service(text: str = "ok", tools: list | None = None):
    """Returns a FastAPI dependency override that yields a stubbed ChatService."""
    svc = MagicMock()
    svc.handle_turn.return_value = (text, tools or [])
    return lambda: svc


# ---------------------------------------------------------------------------
# GET /api/prompts/modes
# ---------------------------------------------------------------------------

def test_get_prompt_modes_returns_200(tmp_path: Path, monkeypatch) -> None:
    """Endpoint must return HTTP 200."""
    pm = _make_prompt_manager(tmp_path)
    app.dependency_overrides[get_prompt_manager] = lambda: pm
    monkeypatch.setattr(config_module.settings, "data_dir", tmp_path)
    monkeypatch.setattr(main_module.settings, "data_dir", tmp_path)
    try:
        resp = TestClient(app).get("/api/prompts/modes")
        assert resp.status_code == 200
    finally:
        app.dependency_overrides.pop(get_prompt_manager, None)


def test_get_prompt_modes_returns_list(tmp_path: Path, monkeypatch) -> None:
    """Response must be a JSON array."""
    pm = _make_prompt_manager(tmp_path)
    app.dependency_overrides[get_prompt_manager] = lambda: pm
    monkeypatch.setattr(config_module.settings, "data_dir", tmp_path)
    monkeypatch.setattr(main_module.settings, "data_dir", tmp_path)
    try:
        resp = TestClient(app).get("/api/prompts/modes")
        assert isinstance(resp.json(), list)
    finally:
        app.dependency_overrides.pop(get_prompt_manager, None)


def test_get_prompt_modes_has_three_modes(tmp_path: Path, monkeypatch) -> None:
    """Must return exactly the three built-in modes."""
    pm = _make_prompt_manager(tmp_path)
    app.dependency_overrides[get_prompt_manager] = lambda: pm
    monkeypatch.setattr(config_module.settings, "data_dir", tmp_path)
    monkeypatch.setattr(main_module.settings, "data_dir", tmp_path)
    try:
        modes = TestClient(app).get("/api/prompts/modes").json()
        ids = {m["id"] for m in modes}
        assert ids == {"general", "design", "assembly"}
    finally:
        app.dependency_overrides.pop(get_prompt_manager, None)


def test_get_prompt_modes_shape(tmp_path: Path, monkeypatch) -> None:
    """Each item must have id, label, eyebrow — never content."""
    pm = _make_prompt_manager(tmp_path)
    app.dependency_overrides[get_prompt_manager] = lambda: pm
    monkeypatch.setattr(config_module.settings, "data_dir", tmp_path)
    monkeypatch.setattr(main_module.settings, "data_dir", tmp_path)
    try:
        modes = TestClient(app).get("/api/prompts/modes").json()
        for m in modes:
            assert "id" in m
            assert "label" in m
            assert "eyebrow" in m
            assert "content" not in m, "content must NOT be exposed to the frontend"
    finally:
        app.dependency_overrides.pop(get_prompt_manager, None)


def test_get_prompt_modes_correct_labels(tmp_path: Path, monkeypatch) -> None:
    """Labels must match the spec from f05.md."""
    pm = _make_prompt_manager(tmp_path)
    app.dependency_overrides[get_prompt_manager] = lambda: pm
    monkeypatch.setattr(config_module.settings, "data_dir", tmp_path)
    monkeypatch.setattr(main_module.settings, "data_dir", tmp_path)
    try:
        modes = TestClient(app).get("/api/prompts/modes").json()
        by_id = {m["id"]: m for m in modes}
        assert by_id["general"]["label"]    == "General"
        assert by_id["design"]["label"]     == "Design"
        assert by_id["assembly"]["label"]   == "Assembly"
        assert by_id["general"]["eyebrow"]  == "Workspace help"
        assert by_id["design"]["eyebrow"]   == "Ergonomics and layout"
        assert by_id["assembly"]["eyebrow"] == "Build and fitting"
    finally:
        app.dependency_overrides.pop(get_prompt_manager, None)


# ---------------------------------------------------------------------------
# POST /api/prompts/reload
# ---------------------------------------------------------------------------

def test_reload_endpoint_returns_200(tmp_path: Path, monkeypatch) -> None:
    """POST /api/prompts/reload must return HTTP 200."""
    pm = _make_prompt_manager(tmp_path)
    app.dependency_overrides[get_prompt_manager] = lambda: pm
    monkeypatch.setattr(config_module.settings, "data_dir", tmp_path)
    monkeypatch.setattr(main_module.settings, "data_dir", tmp_path)
    try:
        resp = TestClient(app).post("/api/prompts/reload")
        assert resp.status_code == 200
    finally:
        app.dependency_overrides.pop(get_prompt_manager, None)


def test_reload_endpoint_returns_success_true(tmp_path: Path, monkeypatch) -> None:
    """POST /api/prompts/reload must return {success: true}."""
    pm = _make_prompt_manager(tmp_path)
    app.dependency_overrides[get_prompt_manager] = lambda: pm
    monkeypatch.setattr(config_module.settings, "data_dir", tmp_path)
    monkeypatch.setattr(main_module.settings, "data_dir", tmp_path)
    try:
        body = TestClient(app).post("/api/prompts/reload").json()
        assert body.get("success") is True
    finally:
        app.dependency_overrides.pop(get_prompt_manager, None)


def test_reload_endpoint_calls_reload_prompts(tmp_path: Path, monkeypatch) -> None:
    """POST /api/prompts/reload must actually call pm.reload_prompts()."""
    pm = MagicMock(spec=PromptManager)
    pm.reload_prompts.return_value = None
    app.dependency_overrides[get_prompt_manager] = lambda: pm
    monkeypatch.setattr(config_module.settings, "data_dir", tmp_path)
    monkeypatch.setattr(main_module.settings, "data_dir", tmp_path)
    try:
        TestClient(app).post("/api/prompts/reload")
        pm.reload_prompts.assert_called_once()
    finally:
        app.dependency_overrides.pop(get_prompt_manager, None)


# ---------------------------------------------------------------------------
# POST /api/chat — mode_id resolves to system_instruction
# ---------------------------------------------------------------------------

def test_chat_with_mode_id_resolves_instruction(tmp_path: Path, monkeypatch) -> None:
    """When mode_id='design' is sent, the ChatService must receive the
    resolved design system_instruction, NOT the raw mode_id string."""
    pm = _make_prompt_manager(tmp_path)
    captured: dict = {}

    class CaptureSvc:
        def handle_turn(self, **kwargs):
            captured.update(kwargs)
            return ("done", [])

    app.dependency_overrides[get_prompt_manager] = lambda: pm
    app.dependency_overrides[get_chat_service] = lambda: CaptureSvc()
    monkeypatch.setattr(config_module.settings, "data_dir", tmp_path)
    monkeypatch.setattr(main_module.settings, "data_dir", tmp_path)
    try:
        resp = TestClient(app).post("/api/chat", json={
            "session_id": "s1",
            "message":    "test",
            "mode_id":    "design",
        })
        assert resp.status_code == 200
        passed_prompt = captured.get("system_prompt", "")
        assert "DESIGN CONTENT" in passed_prompt, (
            f"Expected DESIGN CONTENT in system_prompt, got: {passed_prompt!r}"
        )
        assert "BASE RULES" in passed_prompt, (
            f"Expected BASE RULES in system_prompt, got: {passed_prompt!r}"
        )
    finally:
        app.dependency_overrides.pop(get_prompt_manager, None)
        app.dependency_overrides.pop(get_chat_service, None)


def test_chat_mode_id_defaults_to_general(tmp_path: Path, monkeypatch) -> None:
    """When no mode_id is supplied, the general prompt must be used."""
    pm = _make_prompt_manager(tmp_path)
    captured: dict = {}

    class CaptureSvc:
        def handle_turn(self, **kwargs):
            captured.update(kwargs)
            return ("done", [])

    app.dependency_overrides[get_prompt_manager] = lambda: pm
    app.dependency_overrides[get_chat_service] = lambda: CaptureSvc()
    monkeypatch.setattr(config_module.settings, "data_dir", tmp_path)
    monkeypatch.setattr(main_module.settings, "data_dir", tmp_path)
    try:
        resp = TestClient(app).post("/api/chat", json={
            "session_id": "s2",
            "message":    "hello",
        })
        assert resp.status_code == 200
        passed_prompt = captured.get("system_prompt", "")
        assert "GENERAL CONTENT" in passed_prompt
    finally:
        app.dependency_overrides.pop(get_prompt_manager, None)
        app.dependency_overrides.pop(get_chat_service, None)


def test_chat_unknown_mode_id_falls_back_to_base(tmp_path: Path, monkeypatch) -> None:
    """An unrecognised mode_id must not crash; it falls back to base rules."""
    pm = _make_prompt_manager(tmp_path)
    captured: dict = {}

    class CaptureSvc:
        def handle_turn(self, **kwargs):
            captured.update(kwargs)
            return ("done", [])

    app.dependency_overrides[get_prompt_manager] = lambda: pm
    app.dependency_overrides[get_chat_service] = lambda: CaptureSvc()
    monkeypatch.setattr(config_module.settings, "data_dir", tmp_path)
    monkeypatch.setattr(main_module.settings, "data_dir", tmp_path)
    try:
        resp = TestClient(app).post("/api/chat", json={
            "session_id": "s3",
            "message":    "hello",
            "mode_id":    "nonexistent_mode",
        })
        assert resp.status_code == 200
        passed_prompt = captured.get("system_prompt", "")
        assert "BASE RULES" in passed_prompt
    finally:
        app.dependency_overrides.pop(get_prompt_manager, None)
        app.dependency_overrides.pop(get_chat_service, None)


def test_chat_assembly_mode_resolves_correctly(tmp_path: Path, monkeypatch) -> None:
    """mode_id='assembly' must resolve to the assembly prompt."""
    pm = _make_prompt_manager(tmp_path)
    captured: dict = {}

    class CaptureSvc:
        def handle_turn(self, **kwargs):
            captured.update(kwargs)
            return ("done", [])

    app.dependency_overrides[get_prompt_manager] = lambda: pm
    app.dependency_overrides[get_chat_service] = lambda: CaptureSvc()
    monkeypatch.setattr(config_module.settings, "data_dir", tmp_path)
    monkeypatch.setattr(main_module.settings, "data_dir", tmp_path)
    try:
        resp = TestClient(app).post("/api/chat", json={
            "session_id": "s4",
            "message":    "how do I mount hinges?",
            "mode_id":    "assembly",
        })
        assert resp.status_code == 200
        passed_prompt = captured.get("system_prompt", "")
        assert "ASSEMBLY CONTENT" in passed_prompt
    finally:
        app.dependency_overrides.pop(get_prompt_manager, None)
        app.dependency_overrides.pop(get_chat_service, None)


# ---------------------------------------------------------------------------
# POST /api/chat — backward compatibility (system_prompt field still works)
# ---------------------------------------------------------------------------

def test_chat_legacy_system_prompt_still_accepted(tmp_path: Path, monkeypatch) -> None:
    """Sending system_prompt directly (old frontend behaviour) must still work.
    The raw value must be forwarded to ChatService unchanged."""
    pm = _make_prompt_manager(tmp_path)
    captured: dict = {}

    class CaptureSvc:
        def handle_turn(self, **kwargs):
            captured.update(kwargs)
            return ("done", [])

    app.dependency_overrides[get_prompt_manager] = lambda: pm
    app.dependency_overrides[get_chat_service] = lambda: CaptureSvc()
    monkeypatch.setattr(config_module.settings, "data_dir", tmp_path)
    monkeypatch.setattr(main_module.settings, "data_dir", tmp_path)
    try:
        resp = TestClient(app).post("/api/chat", json={
            "session_id":    "s5",
            "message":       "legacy call",
            "system_prompt": "MY CUSTOM LEGACY PROMPT",
        })
        assert resp.status_code == 200
        # system_prompt overrides mode_id — raw value must reach the service
        assert captured.get("system_prompt") == "MY CUSTOM LEGACY PROMPT"
    finally:
        app.dependency_overrides.pop(get_prompt_manager, None)
        app.dependency_overrides.pop(get_chat_service, None)


def test_chat_system_prompt_overrides_mode_id(tmp_path: Path, monkeypatch) -> None:
    """When both system_prompt and mode_id are provided,
    system_prompt takes precedence (backward compat guarantee)."""
    pm = _make_prompt_manager(tmp_path)
    captured: dict = {}

    class CaptureSvc:
        def handle_turn(self, **kwargs):
            captured.update(kwargs)
            return ("done", [])

    app.dependency_overrides[get_prompt_manager] = lambda: pm
    app.dependency_overrides[get_chat_service] = lambda: CaptureSvc()
    monkeypatch.setattr(config_module.settings, "data_dir", tmp_path)
    monkeypatch.setattr(main_module.settings, "data_dir", tmp_path)
    try:
        resp = TestClient(app).post("/api/chat", json={
            "session_id":    "s6",
            "message":       "override test",
            "mode_id":       "design",
            "system_prompt": "EXPLICIT OVERRIDE PROMPT",
        })
        assert resp.status_code == 200
        assert captured.get("system_prompt") == "EXPLICIT OVERRIDE PROMPT"
    finally:
        app.dependency_overrides.pop(get_prompt_manager, None)
        app.dependency_overrides.pop(get_chat_service, None)


# ---------------------------------------------------------------------------
# DI factory
# ---------------------------------------------------------------------------

def test_get_prompt_manager_dependency_returns_instance(tmp_path: Path, monkeypatch) -> None:
    """The get_prompt_manager DI factory must return a PromptManager instance."""
    monkeypatch.setattr(config_module.settings, "data_dir", tmp_path)
    monkeypatch.setattr(main_module.settings, "data_dir", tmp_path)
    from src.main import get_prompt_manager as gpm
    result = gpm()
    assert isinstance(result, PromptManager)
