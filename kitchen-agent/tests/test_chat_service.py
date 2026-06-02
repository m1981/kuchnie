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


# ---------------------------------------------------------------------------
# ChatService with TurnOrchestrator (new path)
# ---------------------------------------------------------------------------

from src.agent.turn_orchestrator import TurnInput, TurnOutput, ToolCallDetail
from src.agent.context_assembler import ContextSlot


class FakeOrchestrator:
    """
    Minimal fake for ChatService tests.
    Records calls. Returns controllable output.
    """

    def __init__(
        self,
        text: str = "response text",
        tool_details: list[ToolCallDetail] | None = None,
    ) -> None:
        self._text = text
        self._tool_details = tool_details or []
        self.run_call_count = 0
        self.last_turn_input: TurnInput | None = None
        self.last_session: dict | None = None

    def run(self, session: dict, turn_input: TurnInput) -> TurnOutput:
        self.run_call_count += 1
        self.last_turn_input = turn_input
        self.last_session = session
        return TurnOutput(
            assistant_message=self._text,
            tool_calls_made=[d.name for d in self._tool_details],
            tokens_used={"input": 10, "output": 5, "total": 15},
            context_slots={ContextSlot.SYSTEM_PROMPT: 20},
            tool_details=self._tool_details,
        )


@pytest.fixture
def fake_orchestrator():
    return FakeOrchestrator()


@patch("src.chat_service.log_turn")
def test_handle_turn_with_orchestrator_saves_session(
    mock_log: MagicMock,
    fake_orchestrator: FakeOrchestrator,
    repo: SQLiteSessionRepository,
) -> None:
    """With orchestrator injected, handle_turn should use the new path."""
    service = ChatService(
        session_repo=repo,
        turn_orchestrator=fake_orchestrator,
    )
    session_id = "test-orch-001"

    text, tools = service.handle_turn(
        session_id=session_id,
        user_message="What hinges should I use?",
    )

    assert text == "response text"
    assert tools == []
    assert fake_orchestrator.run_call_count == 1

    # Verify session persisted
    _, ui_json, _ = repo.load_session(session_id)
    ui_messages = json.loads(ui_json)
    assert len(ui_messages) == 2
    assert ui_messages[0]["role"] == "user"
    assert ui_messages[0]["content"] == "What hinges should I use?"
    assert "turn_id" in ui_messages[0]
    assert ui_messages[1]["role"] == "assistant"
    assert ui_messages[1]["content"] == "response text"
    assert "turn_id" in ui_messages[1]


@patch("src.chat_service.log_turn")
def test_handle_turn_with_orchestrator_appends_to_history(
    mock_log: MagicMock,
    fake_orchestrator: FakeOrchestrator,
    repo: SQLiteSessionRepository,
) -> None:
    """Second turn with orchestrator must append to existing history."""
    service = ChatService(
        session_repo=repo,
        turn_orchestrator=fake_orchestrator,
    )

    service.handle_turn("sess-orch-1", "Turn 1")

    fake_orchestrator._text = "Answer 2"
    service.handle_turn("sess-orch-1", "Turn 2")

    _, ui_json, _ = repo.load_session("sess-orch-1")
    ui_messages = json.loads(ui_json)
    assert len(ui_messages) == 4
    assert ui_messages[2]["content"] == "Turn 2"
    assert ui_messages[3]["content"] == "Answer 2"


@patch("src.chat_service.log_turn")
def test_handle_turn_with_orchestrator_passes_images_and_context(
    mock_log: MagicMock,
    repo: SQLiteSessionRepository,
) -> None:
    """Images and context_files must be forwarded to the orchestrator."""
    orchestrator = FakeOrchestrator()
    service = ChatService(
        session_repo=repo,
        turn_orchestrator=orchestrator,
    )

    images = [{"mime_type": "image/png", "data": "abc123"}]
    context = ["/data/file.txt"]

    service.handle_turn(
        "sess-orch-img",
        "describe this",
        images=images,
        context_files=context,
    )

    assert orchestrator.last_turn_input is not None
    assert orchestrator.last_turn_input.images == images
    assert orchestrator.last_turn_input.context_files == context


@patch("src.chat_service.log_turn")
def test_handle_turn_with_orchestrator_persists_tool_calls(
    mock_log: MagicMock,
    repo: SQLiteSessionRepository,
) -> None:
    """Tool calls from orchestrator must be persisted in history."""
    tool_details = [
        ToolCallDetail(
            id="call_1",
            name="read_file",
            arguments={"filepath": "/test.md"},
            result_content="file content here",
            is_error=False,
        )
    ]
    orchestrator = FakeOrchestrator(
        text="Based on the file, here is my answer.",
        tool_details=tool_details,
    )
    service = ChatService(
        session_repo=repo,
        turn_orchestrator=orchestrator,
    )

    text, tool_logs = service.handle_turn(
        "sess-orch-tools",
        "Read the file",
    )

    assert text == "Based on the file, here is my answer."
    assert len(tool_logs) == 1
    assert tool_logs[0]["name"] == "read_file"
    assert tool_logs[0]["args"] == {"filepath": "/test.md"}

    # Verify history includes tool call and result
    api_json, _, _ = repo.load_session("sess-orch-tools")
    api_items = json.loads(api_json)
    # Should have: user msg, tool_use, tool_result, assistant response
    assert len(api_items) >= 4


@patch("src.chat_service.log_turn")
def test_handle_turn_with_orchestrator_logs_prompt(
    mock_log: MagicMock,
    fake_orchestrator: FakeOrchestrator,
    repo: SQLiteSessionRepository,
) -> None:
    """log_turn must be called even with orchestrator path."""
    service = ChatService(
        session_repo=repo,
        turn_orchestrator=fake_orchestrator,
    )

    service.handle_turn("sess-orch-log", "Log me")

    assert mock_log.called
    _, kwargs = mock_log.call_args
    assert kwargs.get("user_message") == "Log me"
    assert kwargs.get("session_id") == "sess-orch-log"


@patch("src.chat_service.process_chat_turn")
@patch("src.chat_service.log_turn")
def test_provider_override_bypasses_orchestrator(
    mock_log: MagicMock,
    mock_agent: MagicMock,
    fake_orchestrator: FakeOrchestrator,
    repo: SQLiteSessionRepository,
) -> None:
    """
    When provider_name is explicitly set, the legacy path must
    be used regardless of whether an orchestrator is injected.
    The orchestrator is built with the default provider and
    cannot honour per-request provider overrides.
    """
    mock_agent.return_value = ("legacy response", [])

    service = ChatService(
        session_repo=repo,
        turn_orchestrator=fake_orchestrator,
    )

    text, tools = service.handle_turn(
        session_id="sess-provider-override",
        user_message="hello",
        provider_name="anthropic",   # explicit override
    )

    # Legacy path must have been called
    assert mock_agent.called
    # Orchestrator must NOT have been called
    assert fake_orchestrator.run_call_count == 0
    assert text == "legacy response"


@patch("src.chat_service.log_turn")
def test_use_tools_false_forwarded_to_orchestrator(
    mock_log: MagicMock,
    repo: SQLiteSessionRepository,
) -> None:
    """use_tools=False must be forwarded to TurnInput."""
    orchestrator = FakeOrchestrator()
    service = ChatService(
        session_repo=repo,
        turn_orchestrator=orchestrator,
    )

    service.handle_turn(
        session_id="sess-no-tools",
        user_message="hello",
        use_tools=False,
    )

    assert orchestrator.last_turn_input is not None
    assert orchestrator.last_turn_input.use_tools is False
