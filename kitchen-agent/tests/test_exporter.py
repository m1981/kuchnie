"""
TDD suite for Markdown export of chat sessions.

Covers the pure rendering function and the DatabaseManager integration.
"""
import json
import pytest

from src.exporter import export_session_to_markdown
from src.db import DatabaseManager


# --- Pure function tests ---

def test_export_empty_session_has_title_only():
    """An empty session renders just the document title."""

    # 1. Arrange
    ui_messages = []
    title = "Empty Chat"

    # 2. Act
    result = export_session_to_markdown(ui_messages, title)

    # 3. Assert
    assert result.startswith("# Empty Chat")
    assert "## User" not in result
    assert "## Assistant" not in result


def test_export_single_user_turn():
    """A user-only message renders a User section."""

    # 1. Arrange
    ui_messages = [{"role": "user", "content": "Hello there"}]

    # 2. Act
    result = export_session_to_markdown(ui_messages, "Greeting")

    # 3. Assert
    assert "# Greeting" in result
    assert "## User" in result
    assert "Hello there" in result


def test_export_full_user_assistant_exchange():
    """Both user and assistant sections appear with their content."""

    # 1. Arrange
    ui_messages = [
        {"role": "user", "content": "What is 2+2?"},
        {"role": "assistant", "content": "4", "tools": []},
    ]

    # 2. Act
    result = export_session_to_markdown(ui_messages, "Math")

    # 3. Assert
    assert "## User" in result
    assert "What is 2+2?" in result
    assert "## Assistant" in result
    assert "\n4" in result


def test_export_renders_tool_calls_as_details_blocks():
    """Tool invocations are rendered inside <details> blocks."""

    # 1. Arrange
    ui_messages = [
        {"role": "user", "content": "Read foo.md"},
        {
            "role": "assistant",
            "content": "Here is the file.",
            "tools": [
                {
                    "name": "read_file",
                    "args": {"filepath": "foo.md"},
                    "result": {"content": "# Foo"},
                }
            ],
        },
    ]

    # 2. Act
    result = export_session_to_markdown(ui_messages, "File Read")

    # 3. Assert
    assert "<details>" in result
    assert "</details>" in result
    assert "read_file" in result
    assert "foo.md" in result
    assert "# Foo" in result


def test_export_preserves_turn_order():
    """Turns appear in the order they were provided."""

    # 1. Arrange
    ui_messages = [
        {"role": "user", "content": "FIRST_USER_MSG"},
        {"role": "assistant", "content": "FIRST_ASSISTANT_MSG", "tools": []},
        {"role": "user", "content": "SECOND_USER_MSG"},
        {"role": "assistant", "content": "SECOND_ASSISTANT_MSG", "tools": []},
    ]

    # 2. Act
    result = export_session_to_markdown(ui_messages, "Ordered")

    # 3. Assert
    positions = [
        result.index("FIRST_USER_MSG"),
        result.index("FIRST_ASSISTANT_MSG"),
        result.index("SECOND_USER_MSG"),
        result.index("SECOND_ASSISTANT_MSG"),
    ]
    assert positions == sorted(positions)


def test_export_special_markdown_chars_preserved():
    """Markdown content inside messages is passed through verbatim."""

    # 1. Arrange
    content = "Here is `code`, **bold**, and a [link](http://x.test)."
    ui_messages = [{"role": "user", "content": content}]

    # 2. Act
    result = export_session_to_markdown(ui_messages, "Markdown")

    # 3. Assert
    assert content in result


def test_export_handles_missing_tools_key():
    """Assistant messages without a 'tools' key render without error."""

    # 1. Arrange
    ui_messages = [{"role": "assistant", "content": "No tools here"}]

    # 2. Act
    result = export_session_to_markdown(ui_messages, "Toolless")

    # 3. Assert
    assert "## Assistant" in result
    assert "No tools here" in result
    assert "<details>" not in result


def test_export_falls_back_for_empty_title():
    """An empty or whitespace title falls back to 'Untitled Session'."""

    # 1. Arrange / 2. Act
    result = export_session_to_markdown([], "   ")

    # 3. Assert
    assert "# Untitled Session" in result


# --- DatabaseManager integration tests ---

def _seed(db: DatabaseManager) -> str:
    """Helper: seeds a session with one user/assistant exchange."""
    session_id = "exp-session-1"
    ui_messages = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi back", "tools": []},
    ]
    db.save_session(
        session_id=session_id,
        title="Export Test",
        api_history_json="[]",
        ui_history_json=json.dumps(ui_messages),
    )
    return session_id


def test_db_export_session_returns_markdown(tmp_path):
    """DatabaseManager.export_session returns a non-empty markdown string."""

    # 1. Arrange
    db = DatabaseManager(db_path=str(tmp_path / "test_chats.db"))
    session_id = _seed(db)

    # 2. Act
    result = db.export_session(session_id)

    # 3. Assert
    assert isinstance(result, str)
    assert "# Export Test" in result
    assert "## User" in result
    assert "Hello" in result
    assert "## Assistant" in result
    assert "Hi back" in result


def test_db_export_nonexistent_session_raises(tmp_path):
    """Exporting an unknown session raises ValueError."""

    # 1. Arrange
    db = DatabaseManager(db_path=str(tmp_path / "test_chats.db"))

    # 2. Act / 3. Assert
    with pytest.raises(ValueError):
        db.export_session("does-not-exist")


def test_db_export_empty_session(tmp_path):
    """Exporting a session with no UI messages still renders the title."""

    # 1. Arrange
    db = DatabaseManager(db_path=str(tmp_path / "test_chats.db"))
    db.save_session(
        session_id="empty-1",
        title="Empty One",
        api_history_json="[]",
        ui_history_json="[]",
    )

    # 2. Act
    result = db.export_session("empty-1")

    # 3. Assert
    assert "# Empty One" in result
