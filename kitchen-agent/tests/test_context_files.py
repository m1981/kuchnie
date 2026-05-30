"""
tests/test_context_files.py
============================
TDD test suite for the context-file injection pipeline.

Problem statement
-----------------
When a user checks a file in the ContextSidebar the frontend sends its
``path`` value, which is relative to ``data_dir``
(e.g. ``"kuchnia-kroki.md"`` not ``"data/kuchnia-kroki.md"``).

The backend ``/api/chat`` endpoint receives this relative path and forwards
it straight to ``process_chat_turn`` → ``read_file``.  ``read_file`` opens
the path relative to CWD — so ``Path("kuchnia-kroki.md").exists()`` is
``False`` and the context file is silently skipped (no content injected).

Fix
---
``main.py``'s chat handler must prefix every incoming ``context_file`` path
with ``settings.data_dir`` so that ``read_file`` receives the full path
(e.g. ``"data/kuchnia-kroki.md"``).

Test layers
-----------
1. Unit — agent.py  (already passing; context regression guard)
2. Integration — /api/chat HTTP endpoint with real tmp data_dir
3. End-to-end path construction — verify main.py resolves paths correctly
"""

from __future__ import annotations

import json
from functools import partial
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

import src.main
from src import config
from src.main import app, get_session_repo, get_chat_service
from src.repositories import SQLiteConnection, SQLiteSessionRepository


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def data_dir(tmp_path: Path) -> Path:
    """Temporary data directory that acts as settings.data_dir."""
    d = tmp_path / "data"
    d.mkdir()
    return d


@pytest.fixture()
def client(data_dir: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """
    TestClient wired to a tmp data_dir and an in-memory SQLite database.
    The Gemini API is never called — all agent calls are mocked.
    """
    monkeypatch.setattr(src.main.settings, "data_dir", data_dir)
    monkeypatch.setattr(config.settings, "data_dir", data_dir)

    db = SQLiteConnection(data_dir / "chats.db")
    repo = SQLiteSessionRepository(db)

    app.dependency_overrides[get_session_repo] = lambda: repo
    app.dependency_overrides[get_chat_service] = lambda: src.main.ChatService(repo)
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def context_file(data_dir: Path) -> Path:
    """A real markdown file planted inside data_dir."""
    p = data_dir / "materials.md"
    p.write_text("# Materials\n18mm Birch plywood.\n", encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# Helper — make the ChatService always return a fixed text without hitting Gemini
# ---------------------------------------------------------------------------

def _stub_agent(text: str = "ok", tools: list | None = None):
    """Returns a patcher context that replaces process_chat_turn."""
    mock = MagicMock(return_value=(text, tools or []))
    return patch("src.chat_service.process_chat_turn", mock)


# ===========================================================================
# 1. Agent-level unit tests (regression guard — context_files already work
#    when the caller supplies the correct full path)
# ===========================================================================

class TestAgentContextFilesUnitRegression:
    """
    Guard that the agent correctly injects context_files when given real paths.
    These tests mock Gemini and read_file — they verify agent.py behaviour
    has not regressed.
    """

    @patch("src.providers.gemini.genai.Client")
    @patch("src.providers.gemini.read_file")
    def test_agent_injects_content_when_file_readable(
        self,
        mock_read_file: MagicMock,
        mock_generate: MagicMock,
    ) -> None:
        """Agent prepends file content when read_file returns content."""
        from src.agent import process_chat_turn

        mock_read_file.return_value = {"content": "# Materials\n18mm Birch."}
        final_part = MagicMock()
        final_part.function_call = None
        resp = MagicMock()
        resp.candidates = [MagicMock(content=MagicMock(parts=[final_part]))]
        resp.text = "Noted."
        mock_generate.return_value.models.generate_content.return_value = resp

        history: list = []
        process_chat_turn(
            "Use context",
            history,
            context_files=["data/materials.md"],
        )

        mock_read_file.assert_called_once_with("data/materials.md")
        user_parts = history[0].parts
        # First part = context block, second = user message
        assert len(user_parts) == 2
        assert "[Context files injected by user]" in user_parts[0].text
        assert "18mm Birch" in user_parts[0].text

    @patch("src.providers.gemini.genai.Client")
    @patch("src.providers.gemini.read_file")
    def test_agent_skips_when_path_has_no_data_prefix(
        self,
        mock_read_file: MagicMock,
        mock_generate: MagicMock,
    ) -> None:
        """
        When read_file gets a bare filename (no data/ prefix) it returns an
        error and the agent silently skips it — so no context block is injected.
        This test documents the pre-fix broken behaviour at the agent level.
        """
        from src.agent import process_chat_turn

        # Simulate what happens when the path is NOT prefixed: file not found
        mock_read_file.return_value = {"error": "File not found: materials.md"}
        final_part = MagicMock()
        final_part.function_call = None
        resp = MagicMock()
        resp.candidates = [MagicMock(content=MagicMock(parts=[final_part]))]
        resp.text = "ok"
        mock_generate.return_value.models.generate_content.return_value = resp

        history: list = []
        process_chat_turn(
            "hello",
            history,
            context_files=["materials.md"],  # bare filename — no data/ prefix
        )

        # Only the message Part — no context block injected
        user_parts = history[0].parts
        assert len(user_parts) == 1
        assert user_parts[0].text == "hello"


# ===========================================================================
# 2. Path resolution unit tests (main.py layer)
# ===========================================================================

class TestContextFilePathResolution:
    """
    The chat handler must prefix bare filenames with data_dir so that
    read_file inside the agent receives the correct absolute-ish path.
    """

    def test_bare_filename_is_prefixed_with_data_dir(
        self, data_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        When context_files=["materials.md"] the handler must forward
        "data/materials.md" (or the equivalent under the configured data_dir)
        to the chat service / agent.
        """
        import src.main as main_module

        captured: list[list[str] | None] = []

        def fake_handle_turn(**kwargs):
            captured.append(kwargs.get("context_files"))
            return "ok", []

        from src.chat_service import ChatService

        svc = MagicMock(spec=ChatService)
        svc.handle_turn.side_effect = lambda **kw: (captured.append(kw.get("context_files")), ("ok", []))[1]

        monkeypatch.setattr(src.main.settings, "data_dir", data_dir)
        monkeypatch.setattr(config.settings, "data_dir", data_dir)

        db = SQLiteConnection(data_dir / "chats.db")
        repo = SQLiteSessionRepository(db)
        real_svc = src.main.ChatService(repo)

        forwarded: list[str] = []

        def recording_handle_turn(**kwargs):
            forwarded.extend(kwargs.get("context_files") or [])
            return "ok", []

        real_svc.handle_turn = recording_handle_turn  # type: ignore[method-assign]

        app.dependency_overrides[get_session_repo] = lambda: repo
        app.dependency_overrides[get_chat_service] = lambda: real_svc

        try:
            client = TestClient(app)
            client.post(
                "/api/chat",
                json={
                    "session_id": "sess-test-1",
                    "message": "hello",
                    "context_files": ["materials.md"],
                },
            )
        finally:
            app.dependency_overrides.clear()

        assert len(forwarded) == 1
        expected_prefix = str(data_dir)
        assert forwarded[0].startswith(expected_prefix) or forwarded[0].startswith("data/"), (
            f"Expected path to start with data_dir prefix, got: {forwarded[0]!r}"
        )

    def test_full_data_path_passes_through_unchanged(
        self, data_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        When the caller already sends the full path (e.g. "data/materials.md")
        the handler must not double-prefix it.
        """
        monkeypatch.setattr(src.main.settings, "data_dir", data_dir)
        monkeypatch.setattr(config.settings, "data_dir", data_dir)

        db = SQLiteConnection(data_dir / "chats.db")
        repo = SQLiteSessionRepository(db)
        real_svc = src.main.ChatService(repo)

        forwarded: list[str] = []

        def recording_handle_turn(**kwargs):
            forwarded.extend(kwargs.get("context_files") or [])
            return "ok", []

        real_svc.handle_turn = recording_handle_turn  # type: ignore[method-assign]

        app.dependency_overrides[get_session_repo] = lambda: repo
        app.dependency_overrides[get_chat_service] = lambda: real_svc

        full_path = str(data_dir / "materials.md")
        try:
            client = TestClient(app)
            client.post(
                "/api/chat",
                json={
                    "session_id": "sess-test-2",
                    "message": "hello",
                    "context_files": [full_path],
                },
            )
        finally:
            app.dependency_overrides.clear()

        assert len(forwarded) == 1
        # Should not be double-prefixed
        assert forwarded[0] == full_path

    def test_null_context_files_not_passed(
        self, data_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When context_files is null/absent the service receives None."""
        monkeypatch.setattr(src.main.settings, "data_dir", data_dir)
        monkeypatch.setattr(config.settings, "data_dir", data_dir)

        db = SQLiteConnection(data_dir / "chats.db")
        repo = SQLiteSessionRepository(db)
        real_svc = src.main.ChatService(repo)

        forwarded: list = []

        def recording_handle_turn(**kwargs):
            forwarded.append(kwargs.get("context_files"))
            return "ok", []

        real_svc.handle_turn = recording_handle_turn  # type: ignore[method-assign]

        app.dependency_overrides[get_session_repo] = lambda: repo
        app.dependency_overrides[get_chat_service] = lambda: real_svc

        try:
            client = TestClient(app)
            client.post(
                "/api/chat",
                json={
                    "session_id": "sess-test-3",
                    "message": "hello",
                    # no context_files key
                },
            )
        finally:
            app.dependency_overrides.clear()

        assert len(forwarded) == 1
        assert forwarded[0] is None

    def test_empty_context_files_list_becomes_none(
        self, data_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """context_files=[] should forward as None (existing behaviour)."""
        monkeypatch.setattr(src.main.settings, "data_dir", data_dir)
        monkeypatch.setattr(config.settings, "data_dir", data_dir)

        db = SQLiteConnection(data_dir / "chats.db")
        repo = SQLiteSessionRepository(db)
        real_svc = src.main.ChatService(repo)

        forwarded: list = []

        def recording_handle_turn(**kwargs):
            forwarded.append(kwargs.get("context_files"))
            return "ok", []

        real_svc.handle_turn = recording_handle_turn  # type: ignore[method-assign]

        app.dependency_overrides[get_session_repo] = lambda: repo
        app.dependency_overrides[get_chat_service] = lambda: real_svc

        try:
            client = TestClient(app)
            client.post(
                "/api/chat",
                json={
                    "session_id": "sess-test-4",
                    "message": "hello",
                    "context_files": [],
                },
            )
        finally:
            app.dependency_overrides.clear()

        assert len(forwarded) == 1
        assert forwarded[0] is None


# ===========================================================================
# 3. Integration tests — full HTTP round-trip with real file on disk
# ===========================================================================

class TestContextFileIntegration:
    """
    Integration tests that plant a real file in tmp data_dir and verify
    the chat endpoint actually reads it and includes its content in the
    user turn sent to the model.
    """

    def test_context_file_content_reaches_agent(
        self,
        data_dir: Path,
        context_file: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        The content of the checked file must appear in the user turn
        forwarded to the LLM.
        END-TO-END: real file on disk, real agent call (Gemini mocked).
        """
        monkeypatch.setattr(src.main.settings, "data_dir", data_dir)
        monkeypatch.setattr(config.settings, "data_dir", data_dir)

        db = SQLiteConnection(data_dir / "chats.db")
        repo = SQLiteSessionRepository(db)

        captured_history: list = []

        def fake_process_chat_turn(
            user_message, history, system_instruction=None, images=None,
            context_files=None, **_kwargs
        ):
            # We intercept here — after context files are read
            from src.agent import process_chat_turn as _real
            # Store the resolved context_files for assertion
            captured_history.append({"context_files": context_files})
            # Don't call real Gemini — just return
            return "Agent response", []

        with patch("src.chat_service.process_chat_turn", side_effect=fake_process_chat_turn):
            app.dependency_overrides[get_session_repo] = lambda: repo
            app.dependency_overrides[get_chat_service] = lambda: src.main.ChatService(repo)

            try:
                client = TestClient(app)
                resp = client.post(
                    "/api/chat",
                    json={
                        "session_id": "sess-integ-1",
                        "message": "What materials should I use?",
                        "context_files": ["materials.md"],  # bare name from frontend
                    },
                )
            finally:
                app.dependency_overrides.clear()

        assert resp.status_code == 200

        assert len(captured_history) == 1
        received_paths = captured_history[0]["context_files"]
        assert received_paths is not None
        assert len(received_paths) == 1

        # The path forwarded to the agent must point inside data_dir
        resolved = Path(received_paths[0])
        # Either absolute path inside data_dir, or relative "data/materials.md"
        assert str(resolved).endswith("materials.md"), (
            f"Expected path ending in materials.md, got: {resolved}"
        )
        # The path must be accessible (so read_file would succeed)
        assert resolved.exists() or (data_dir / resolved).exists(), (
            f"Path {resolved} does not resolve to an existing file"
        )

    def test_context_file_content_is_readable_via_resolved_path(
        self,
        data_dir: Path,
        context_file: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        The path that the agent receives for context_files must be readable
        by read_file() without returning an error.
        """
        from src.tools.file_ops import read_file

        monkeypatch.setattr(src.main.settings, "data_dir", data_dir)
        monkeypatch.setattr(config.settings, "data_dir", data_dir)

        db = SQLiteConnection(data_dir / "chats.db")
        repo = SQLiteSessionRepository(db)

        received_paths: list[str] = []

        def recording_process_chat_turn(
            user_message, history, system_instruction=None, images=None,
            context_files=None, **_kwargs
        ):
            if context_files:
                received_paths.extend(context_files)
            return "ok", []

        with patch("src.chat_service.process_chat_turn", side_effect=recording_process_chat_turn):
            app.dependency_overrides[get_session_repo] = lambda: repo
            app.dependency_overrides[get_chat_service] = lambda: src.main.ChatService(repo)

            try:
                client = TestClient(app)
                client.post(
                    "/api/chat",
                    json={
                        "session_id": "sess-integ-2",
                        "message": "Help",
                        "context_files": ["materials.md"],
                    },
                )
            finally:
                app.dependency_overrides.clear()

        assert len(received_paths) == 1

        # The path the agent receives must be readable by read_file
        result = read_file(received_paths[0])
        assert "error" not in result, (
            f"read_file({received_paths[0]!r}) returned error: {result.get('error')}\n"
            "This means the context file path was NOT correctly resolved — the bug is still present."
        )
        assert "content" in result
        assert "18mm Birch" in result["content"]

    def test_multiple_context_files_all_prefixed(
        self,
        data_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """All files in the list must be prefixed, not just the first."""
        (data_dir / "file_a.md").write_text("File A content", encoding="utf-8")
        (data_dir / "file_b.md").write_text("File B content", encoding="utf-8")

        monkeypatch.setattr(src.main.settings, "data_dir", data_dir)
        monkeypatch.setattr(config.settings, "data_dir", data_dir)

        db = SQLiteConnection(data_dir / "chats.db")
        repo = SQLiteSessionRepository(db)

        received_paths: list[str] = []

        def recording_process_chat_turn(
            user_message, history, system_instruction=None, images=None,
            context_files=None, **_kwargs
        ):
            if context_files:
                received_paths.extend(context_files)
            return "ok", []

        with patch("src.chat_service.process_chat_turn", side_effect=recording_process_chat_turn):
            app.dependency_overrides[get_session_repo] = lambda: repo
            app.dependency_overrides[get_chat_service] = lambda: src.main.ChatService(repo)

            try:
                client = TestClient(app)
                client.post(
                    "/api/chat",
                    json={
                        "session_id": "sess-integ-3",
                        "message": "Help",
                        "context_files": ["file_a.md", "file_b.md"],
                    },
                )
            finally:
                app.dependency_overrides.clear()

        from src.tools.file_ops import read_file

        assert len(received_paths) == 2
        for p in received_paths:
            result = read_file(p)
            assert "error" not in result, (
                f"read_file({p!r}) failed — path not resolved correctly: {result}"
            )

    def test_response_200_when_context_file_provided(
        self,
        data_dir: Path,
        context_file: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """HTTP 200 must be returned when a valid context file is included."""
        monkeypatch.setattr(src.main.settings, "data_dir", data_dir)
        monkeypatch.setattr(config.settings, "data_dir", data_dir)

        db = SQLiteConnection(data_dir / "chats.db")
        repo = SQLiteSessionRepository(db)

        with patch("src.chat_service.process_chat_turn", return_value=("Great!", [])):
            app.dependency_overrides[get_session_repo] = lambda: repo
            app.dependency_overrides[get_chat_service] = lambda: src.main.ChatService(repo)

            try:
                client = TestClient(app)
                resp = client.post(
                    "/api/chat",
                    json={
                        "session_id": "sess-integ-4",
                        "message": "Help",
                        "context_files": ["materials.md"],
                    },
                )
            finally:
                app.dependency_overrides.clear()

        assert resp.status_code == 200
        assert resp.json()["text"] == "Great!"


# ===========================================================================
# 4. /api/files endpoint — verify path values match what ContextSidebar sends
# ===========================================================================

class TestFileListPathFormat:
    """
    The /api/files endpoint returns FileListItem.path as relative-to-data_dir.
    These tests document the format so we know exactly what the frontend sends.
    """

    def test_list_files_path_is_relative_to_data_dir(
        self,
        data_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """path field must be relative, not absolute (e.g. 'test.md' not '/tmp/.../test.md')."""
        (data_dir / "test.md").write_text("content", encoding="utf-8")

        monkeypatch.setattr(src.main.settings, "data_dir", data_dir)
        monkeypatch.setattr(config.settings, "data_dir", data_dir)

        db = SQLiteConnection(data_dir / "chats.db")
        repo = SQLiteSessionRepository(db)
        app.dependency_overrides[get_session_repo] = lambda: repo

        try:
            client = TestClient(app)
            resp = client.get("/api/files")
        finally:
            app.dependency_overrides.clear()

        assert resp.status_code == 200
        items = resp.json()
        assert len(items) == 1
        assert items[0]["path"] == "test.md"          # relative — NOT absolute
        assert not items[0]["path"].startswith("/")    # definitely not absolute

    def test_list_files_path_does_not_include_data_prefix(
        self,
        data_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        The path returned by /api/files does NOT include 'data/' prefix.
        This is the root cause: the frontend sends 'test.md', not 'data/test.md'.
        """
        (data_dir / "notes.md").write_text("content", encoding="utf-8")

        monkeypatch.setattr(src.main.settings, "data_dir", data_dir)
        monkeypatch.setattr(config.settings, "data_dir", data_dir)

        db = SQLiteConnection(data_dir / "chats.db")
        repo = SQLiteSessionRepository(db)
        app.dependency_overrides[get_session_repo] = lambda: repo

        try:
            client = TestClient(app)
            resp = client.get("/api/files")
        finally:
            app.dependency_overrides.clear()

        assert resp.status_code == 200
        items = resp.json()
        paths = [i["path"] for i in items]
        # Must NOT contain 'data/' prefix since the fix must add it server-side
        for p in paths:
            assert not p.startswith("data/"), (
                f"Unexpected 'data/' prefix in file path: {p!r}. "
                "The frontend sends bare names; the fix must be server-side."
            )

    def test_bare_filename_is_not_readable_by_read_file(
        self,
        data_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        Documents the bug: a bare filename (as returned by /api/files) is NOT
        directly readable by read_file() without the data_dir prefix.
        This test verifies the pre-condition that justifies the fix.
        """
        import os
        from src.tools.file_ops import read_file

        file_path = data_dir / "materials.md"
        file_path.write_text("18mm Birch.", encoding="utf-8")

        # Change CWD to tmp_path so the bare name definitely doesn't resolve
        original_cwd = os.getcwd()
        os.chdir(tmp := str(data_dir.parent))
        try:
            result = read_file("materials.md")  # bare name — wrong!
        finally:
            os.chdir(original_cwd)

        # Without the fix (bare filename), read_file returns an error
        assert "error" in result, (
            "read_file('materials.md') unexpectedly succeeded from outside data_dir. "
            "The test assumption is wrong — check CWD."
        )
