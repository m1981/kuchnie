"""
TDD suite for session forking/branching.

Forking creates a new session by slicing both api_history_json and
ui_history_json from an existing session up to (and including) a given
turn index. The original session remains untouched.
"""
import json
import pytest

from src.db import DatabaseManager


def _seed_session(db: DatabaseManager) -> tuple[str, list, list]:
    """Helper: seeds a 4-turn session and returns (session_id, ui, api)."""
    session_id = "src-session-1"
    ui_messages = [
        {"role": "user", "content": "Turn 0 user"},
        {"role": "assistant", "content": "Turn 1 assistant", "tools": []},
        {"role": "user", "content": "Turn 2 user"},
        {"role": "assistant", "content": "Turn 3 assistant", "tools": []},
    ]
    api_history = [
        {"role": "user", "parts": [{"text": "Turn 0 user"}]},
        {"role": "model", "parts": [{"text": "Turn 1 assistant"}]},
        {"role": "user", "parts": [{"text": "Turn 2 user"}]},
        {"role": "model", "parts": [{"text": "Turn 3 assistant"}]},
    ]
    db.save_session(
        session_id=session_id,
        title="Original Title",
        api_history_json=json.dumps(api_history),
        ui_history_json=json.dumps(ui_messages),
    )
    return session_id, ui_messages, api_history


def test_fork_returns_new_unique_session_id(tmp_path):
    """Forking produces a brand-new session ID distinct from the source."""

    # 1. Arrange
    db = DatabaseManager(db_path=str(tmp_path / "test_chats.db"))
    source_id, _, _ = _seed_session(db)

    # 2. Act
    new_id = db.fork_session(source_id, turn_index=1)

    # 3. Assert
    assert new_id != source_id
    assert isinstance(new_id, str) and len(new_id) > 0


def test_fork_slices_ui_history_inclusive(tmp_path):
    """Forking at turn_index=N keeps UI messages [0..N] inclusive."""

    # 1. Arrange
    db = DatabaseManager(db_path=str(tmp_path / "test_chats.db"))
    source_id, ui_messages, _ = _seed_session(db)

    # 2. Act
    new_id = db.fork_session(source_id, turn_index=1)

    # 3. Assert
    _, new_ui_json = db.load_session(new_id)
    assert json.loads(new_ui_json) == ui_messages[:2]


def test_fork_slices_api_history_inclusive(tmp_path):
    """Forking at turn_index=N keeps API history [0..N] inclusive."""

    # 1. Arrange
    db = DatabaseManager(db_path=str(tmp_path / "test_chats.db"))
    source_id, _, api_history = _seed_session(db)

    # 2. Act
    new_id = db.fork_session(source_id, turn_index=2)

    # 3. Assert
    new_api_json, _ = db.load_session(new_id)
    assert json.loads(new_api_json) == api_history[:3]


def test_fork_does_not_modify_source_session(tmp_path):
    """The original session histories remain untouched after forking."""

    # 1. Arrange
    db = DatabaseManager(db_path=str(tmp_path / "test_chats.db"))
    source_id, ui_messages, api_history = _seed_session(db)

    # 2. Act
    db.fork_session(source_id, turn_index=1)

    # 3. Assert
    src_api_json, src_ui_json = db.load_session(source_id)
    assert json.loads(src_ui_json) == ui_messages
    assert json.loads(src_api_json) == api_history


def test_fork_derives_title_from_source(tmp_path):
    """Forked session title references source title and fork point."""

    # 1. Arrange
    db = DatabaseManager(db_path=str(tmp_path / "test_chats.db"))
    source_id, _, _ = _seed_session(db)

    # 2. Act
    new_id = db.fork_session(source_id, turn_index=1)

    # 3. Assert
    sessions = {s["id"]: s for s in db.list_sessions()}
    assert new_id in sessions
    forked_title = sessions[new_id]["title"]
    assert "Original Title" in forked_title
    assert "fork" in forked_title.lower()


def test_fork_at_index_zero_keeps_first_turn_only(tmp_path):
    """turn_index=0 keeps exactly the first turn."""

    # 1. Arrange
    db = DatabaseManager(db_path=str(tmp_path / "test_chats.db"))
    source_id, ui_messages, _ = _seed_session(db)

    # 2. Act
    new_id = db.fork_session(source_id, turn_index=0)

    # 3. Assert
    _, new_ui_json = db.load_session(new_id)
    assert json.loads(new_ui_json) == ui_messages[:1]


def test_fork_index_beyond_history_is_clamped(tmp_path):
    """A turn_index past the end of history clamps to full history."""

    # 1. Arrange
    db = DatabaseManager(db_path=str(tmp_path / "test_chats.db"))
    source_id, ui_messages, api_history = _seed_session(db)

    # 2. Act
    new_id = db.fork_session(source_id, turn_index=999)

    # 3. Assert
    new_api_json, new_ui_json = db.load_session(new_id)
    assert json.loads(new_ui_json) == ui_messages
    assert json.loads(new_api_json) == api_history


def test_fork_nonexistent_session_raises(tmp_path):
    """Forking from an unknown session raises ValueError."""

    # 1. Arrange
    db = DatabaseManager(db_path=str(tmp_path / "test_chats.db"))

    # 2. Act / 3. Assert
    with pytest.raises(ValueError):
        db.fork_session("does-not-exist", turn_index=0)


def test_fork_negative_index_raises(tmp_path):
    """Negative turn_index is rejected."""

    # 1. Arrange
    db = DatabaseManager(db_path=str(tmp_path / "test_chats.db"))
    source_id, _, _ = _seed_session(db)

    # 2. Act / 3. Assert
    with pytest.raises(ValueError):
        db.fork_session(source_id, turn_index=-1)


def test_forked_session_appears_in_list(tmp_path):
    """Both source and forked sessions are listed by list_sessions()."""

    # 1. Arrange
    db = DatabaseManager(db_path=str(tmp_path / "test_chats.db"))
    source_id, _, _ = _seed_session(db)

    # 2. Act
    new_id = db.fork_session(source_id, turn_index=1)

    # 3. Assert
    session_ids = [s["id"] for s in db.list_sessions()]
    assert new_id in session_ids
    assert source_id in session_ids
