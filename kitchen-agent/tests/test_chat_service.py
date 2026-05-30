"""
tests/test_chat_service.py
==========================
Unit tests for ChatService — the business-logic layer between the HTTP
handler and the agent.

All external I/O (DB, agent, prompt logger) is mocked so these tests run
instantly without network or disk access.

Migration note
--------------
log_prompt → log_turn: ChatService now calls ``log_turn`` (enriched, with
tool data and session context) instead of the bare ``log_prompt`` shim.
All patches and assertions have been updated accordingly.
"""
import json
from unittest.mock import MagicMock, call, patch

import pytest

from src.chat_service import ChatService, _make_title
from src.repositories import SQLiteConnection, SQLiteSessionRepository


# ---------------------------------------------------------------------------
# _make_title helper
# ---------------------------------------------------------------------------

def test_make_title_short_message() -> None:
    msgs = [{"role": "user", "content": "Hello"}]
    assert _make_title(msgs) == "Hello"


def test_make_title_long_message_truncated() -> None:
    msgs = [{"role": "user", "content": "A" * 40}]
    title = _make_title(msgs)
    assert title.endswith("...")
    assert len(title) == 33  # 30 chars + "..."


def test_make_title_no_user_message() -> None:
    msgs = [{"role": "assistant", "content": "Hi"}]
    assert _make_title(msgs) == "New Chat"


def test_make_title_empty_list() -> None:
    assert _make_title([]) == "New Chat"


# ---------------------------------------------------------------------------
# ChatService.handle_turn
# ---------------------------------------------------------------------------

@pytest.fixture
def repo(tmp_path):
    conn = SQLiteConnection(db_path=str(tmp_path / "test.db"))
    return SQLiteSessionRepository(conn)


@patch("src.chat_service.log_turn")
@patch("src.chat_service.process_chat_turn")
def test_handle_turn_saves_session(
    mock_agent: MagicMock,
    mock_log: MagicMock,
    repo: SQLiteSessionRepository,
) -> None:
    """After handle_turn the session should exist in the DB."""
    mock_agent.return_value = ("Great, noted!", [])

    service = ChatService(repo)
    session_id = "test-session-001"

    text, tools = service.handle_turn(
        session_id=session_id,
        user_message="What hinges should I use?",
    )

    assert text == "Great, noted!"
    assert tools == []

    # load_session now returns 3-tuple
    _, ui_json, _ = repo.load_session(session_id)
    ui_messages = json.loads(ui_json)
    assert len(ui_messages) == 2
    assert ui_messages[0]["role"] == "user"
    assert ui_messages[0]["content"] == "What hinges should I use?"
    assert "turn_id" in ui_messages[0]          # Decision 1: turn_id stamped
    assert ui_messages[1]["role"] == "assistant"
    assert ui_messages[1]["content"] == "Great, noted!"
    assert "turn_id" in ui_messages[1]          # Decision 1: turn_id stamped


@patch("src.chat_service.log_turn")
@patch("src.chat_service.process_chat_turn")
def test_handle_turn_appends_to_existing_history(
    mock_agent: MagicMock,
    mock_log: MagicMock,
    repo: SQLiteSessionRepository,
) -> None:
    """A second turn must append to (not replace) the existing UI history."""
    mock_agent.return_value = ("Answer 1", [])
    service = ChatService(repo)

    service.handle_turn("sess-1", "Turn 1")

    mock_agent.return_value = ("Answer 2", [])
    service.handle_turn("sess-1", "Turn 2")

    # load_session now returns 3-tuple
    _, ui_json, _ = repo.load_session("sess-1")
    ui_messages = json.loads(ui_json)
    assert len(ui_messages) == 4
    assert ui_messages[2]["content"] == "Turn 2"
    assert ui_messages[3]["content"] == "Answer 2"


@patch("src.chat_service.log_turn")
@patch("src.chat_service.process_chat_turn")
def test_handle_turn_logs_prompt(
    mock_agent: MagicMock,
    mock_log: MagicMock,
    repo: SQLiteSessionRepository,
) -> None:
    """log_turn must be called with the user message, tool_logs, and session_id."""
    mock_agent.return_value = ("ok", [])
    service = ChatService(repo)

    service.handle_turn("sess-log", "Log me please")

    assert mock_log.called
    args, kwargs = mock_log.call_args
    # user_message is the first positional or keyword arg
    user_msg = kwargs.get("user_message") or (args[0] if args else None)
    assert user_msg == "Log me please"
    # session_id must be forwarded
    sid = kwargs.get("session_id")
    assert sid == "sess-log"


@patch("src.chat_service.log_turn")
@patch("src.chat_service.process_chat_turn")
def test_handle_turn_passes_images_and_context(
    mock_agent: MagicMock,
    mock_log: MagicMock,
    repo: SQLiteSessionRepository,
) -> None:
    """Extra kwargs (images, context_files) must be forwarded to the agent."""
    mock_agent.return_value = ("done", [])
    service = ChatService(repo)

    images = [{"mime_type": "image/png", "data": "abc123"}]
    context = ["data/materials.md"]

    service.handle_turn(
        "sess-kwargs",
        "Here is an image",
        images=images,
        context_files=context,
    )

    _call_kwargs = mock_agent.call_args[1]
    assert _call_kwargs["images"] == images
    assert _call_kwargs["context_files"] == context
