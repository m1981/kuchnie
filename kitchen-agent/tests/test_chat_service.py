"""
tests/test_chat_service.py
==========================
Unit tests for ChatService — the business-logic layer between the HTTP
handler and the agent.

All external I/O (DB, agent, prompt logger) is mocked so these tests run
instantly without network or disk access.
"""
import json
from unittest.mock import MagicMock, patch

import pytest

from src.chat_service import ChatService, ChatTurnRequest, _make_title
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
# ChatService with TurnOrchestrator
# ---------------------------------------------------------------------------

from src.agent.turn_orchestrator import TurnInput, TurnOutput, ToolCallDetail, ToolCall
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

        # Build tool_logs and tool_calls_made from tool_details
        tool_logs = []
        tool_calls_made = []
        for d in self._tool_details:
            tool_calls_made.append(
                ToolCall(id=d.id, name=d.name, arguments=d.arguments)
            )
            tool_logs.append({
                "name": d.name,
                "args": d.arguments,
                "result": {"content": d.result_content} if not d.is_error else {"error": d.result_content},
            })

        # Build updated_api_history
        updated_api_history = list(session.get("messages", []))
        updated_api_history.append({"role": "user", "content": turn_input.user_message})
        for d in self._tool_details:
            updated_api_history.append({
                "role": "assistant",
                "content": [{"type": "tool_use", "id": d.id, "name": d.name, "input": d.arguments}],
            })
            updated_api_history.append({
                "role": "user",
                "content": [{"type": "tool_result", "tool_use_id": d.id, "content": d.result_content}],
            })
        updated_api_history.append({
            "role": "assistant",
            "content": [{"type": "text", "text": self._text}],
        })

        return TurnOutput(
            assistant_message=self._text,
            updated_api_history=updated_api_history,
            user_turn_id="test-user-turn-id",
            assistant_turn_id="test-assistant-turn-id",
            tool_calls_made=tool_calls_made,
            tool_logs=tool_logs,
            tokens_used={"input": 10, "output": 5, "total": 15},
            context_slots={ContextSlot.SYSTEM_PROMPT: 20},
        )


@pytest.fixture
def fake_orchestrator():
    return FakeOrchestrator()


@patch("src.chat_service.log_turn")
def test_handle_turn_saves_session(
    mock_log: MagicMock,
    fake_orchestrator: FakeOrchestrator,
    repo: SQLiteSessionRepository,
) -> None:
    """handle_turn should persist the session and return structured response."""
    service = ChatService(
        session_repo=repo,
        turn_orchestrator=fake_orchestrator,
    )
    session_id = "test-orch-001"

    result = service.handle_turn(ChatTurnRequest(
        session_id=session_id,
        user_message="What hinges should I use?",
    ))

    assert result.assistant_message == "response text"
    assert result.tool_calls_made == []
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
def test_handle_turn_appends_to_history(
    mock_log: MagicMock,
    fake_orchestrator: FakeOrchestrator,
    repo: SQLiteSessionRepository,
) -> None:
    """Second turn must append to existing history."""
    service = ChatService(
        session_repo=repo,
        turn_orchestrator=fake_orchestrator,
    )

    service.handle_turn(ChatTurnRequest(session_id="sess-orch-1", user_message="Turn 1"))

    fake_orchestrator._text = "Answer 2"
    service.handle_turn(ChatTurnRequest(session_id="sess-orch-1", user_message="Turn 2"))

    _, ui_json, _ = repo.load_session("sess-orch-1")
    ui_messages = json.loads(ui_json)
    assert len(ui_messages) == 4
    assert ui_messages[2]["content"] == "Turn 2"
    assert ui_messages[3]["content"] == "Answer 2"


@patch("src.chat_service.log_turn")
def test_handle_turn_passes_images_and_context(
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

    service.handle_turn(ChatTurnRequest(
        session_id="sess-orch-img",
        user_message="describe this",
        images=images,
        context_files=context,
    ))

    assert orchestrator.last_turn_input is not None
    assert orchestrator.last_turn_input.images == images
    assert orchestrator.last_turn_input.context_files == context


@patch("src.chat_service.log_turn")
def test_handle_turn_persists_tool_calls(
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

    result = service.handle_turn(ChatTurnRequest(
        session_id="sess-orch-tools",
        user_message="Read the file",
    ))

    assert result.assistant_message == "Based on the file, here is my answer."
    assert len(result.tool_calls_made) == 1
    assert result.tool_calls_made[0] == "read_file"


@patch("src.chat_service.log_turn")
def test_handle_turn_logs_prompt(
    mock_log: MagicMock,
    fake_orchestrator: FakeOrchestrator,
    repo: SQLiteSessionRepository,
) -> None:
    """log_turn must be called."""
    service = ChatService(
        session_repo=repo,
        turn_orchestrator=fake_orchestrator,
    )

    service.handle_turn(ChatTurnRequest(session_id="sess-orch-log", user_message="Log me"))

    assert mock_log.called
    _, kwargs = mock_log.call_args
    assert kwargs.get("user_message") == "Log me"
    assert kwargs.get("session_id") == "sess-orch-log"


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

    service.handle_turn(ChatTurnRequest(
        session_id="sess-no-tools",
        user_message="hello",
        use_tools=False,
    ))

    assert orchestrator.last_turn_input is not None
    assert orchestrator.last_turn_input.use_tools is False
