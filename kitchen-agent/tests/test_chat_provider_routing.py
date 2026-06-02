"""
tests/test_chat_provider_routing.py
=====================================
Tests for per-request provider + model routing in POST /api/chat.

Verifies that ``provider`` and ``model`` fields in ChatRequest are
accepted, validated, and forwarded to get_provider() so each turn can
use a different backend without changing server config.

Covers
------
- ChatRequest accepts optional provider / model fields (schema)
- Omitting both fields → server default used (backward compat)
- Providing provider="gemini" routes to GeminiProvider
- Providing provider="anthropic" routes to AnthropicProvider
- Providing model="..." overrides the provider's default model
- Unknown provider name → HTTP 400 (not 500)
- provider field is forwarded through agent.process_chat_turn
- model_override is passed into GeminiProvider / AnthropicProvider
- GeminiProvider respects model_override in the API call
- AnthropicProvider respects model_override in the API call
"""
from functools import partial
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from src.main import app, get_chat_service, get_session_repo
from src.repositories import SQLiteConnection, SQLiteSessionRepository
from src.schemas import ChatRequest
from src.chat_service import ChatService
from tests.test_chat_service import FakeOrchestrator


# ---------------------------------------------------------------------------
# Schema validation — ChatRequest accepts new fields
# ---------------------------------------------------------------------------

def test_chat_request_accepts_provider_field() -> None:
    req = ChatRequest(
        session_id="s1", message="hi",
        provider="anthropic",
    )
    assert req.provider == "anthropic"


def test_chat_request_accepts_model_field() -> None:
    req = ChatRequest(
        session_id="s1", message="hi",
        model="claude-sonnet-4-5",
    )
    assert req.model == "claude-sonnet-4-5"


def test_chat_request_provider_defaults_to_none() -> None:
    req = ChatRequest(session_id="s1", message="hi")
    assert req.provider is None


def test_chat_request_model_defaults_to_none() -> None:
    req = ChatRequest(session_id="s1", message="hi")
    assert req.model is None


def test_chat_request_provider_and_model_together() -> None:
    req = ChatRequest(
        session_id="s1", message="hi",
        provider="gemini", model="gemini-2.5-pro",
    )
    assert req.provider == "gemini"
    assert req.model    == "gemini-2.5-pro"


# ---------------------------------------------------------------------------
# get_provider() factory honours model_override
# ---------------------------------------------------------------------------

def test_get_provider_passes_model_to_gemini() -> None:
    from src.providers.base import get_provider
    with patch("src.providers.gemini.genai.Client"):
        provider = get_provider(provider_name="gemini", model_override="gemini-2.5-pro")
    from src.providers.gemini import GeminiProvider
    assert isinstance(provider, GeminiProvider)
    assert provider._model == "gemini-2.5-pro"


def test_get_provider_passes_model_to_anthropic() -> None:
    from src.providers.base import get_provider
    with patch("src.providers.anthropic_provider.anthropic.Anthropic"):
        provider = get_provider(provider_name="anthropic", model_override="claude-opus-4-5")
    from src.providers.anthropic_provider import AnthropicProvider
    assert isinstance(provider, AnthropicProvider)
    assert provider._model == "claude-opus-4-5"


def test_get_provider_uses_settings_default_when_no_override() -> None:
    import src.config as cfg
    from src.providers.base import get_provider
    with patch.object(cfg.settings, "llm_provider", "gemini"), \
         patch.object(cfg.settings, "gemini_model",  "gemini-2.5-flash"), \
         patch("src.providers.gemini.genai.Client"):
        provider = get_provider()
    from src.providers.gemini import GeminiProvider
    assert isinstance(provider, GeminiProvider)
    assert provider._model == "gemini-2.5-flash"


def test_get_provider_raises_for_unknown_provider_name() -> None:
    from src.providers.base import get_provider
    with pytest.raises(ValueError, match="Unknown LLM provider"):
        get_provider(provider_name="openai")


# ---------------------------------------------------------------------------
# GeminiProvider uses _model in API call
# ---------------------------------------------------------------------------

def test_gemini_provider_uses_model_override_in_api_call() -> None:
    from google.genai import types
    from src.providers.gemini import GeminiProvider

    with patch("src.providers.gemini.genai.Client") as mock_cls:
        provider = GeminiProvider(model_override="gemini-2.5-pro")
        mock_client = mock_cls.return_value

        part = types.Part(text="ok")
        resp = MagicMock()
        resp.candidates = [MagicMock(content=types.Content(role="model", parts=[part]))]
        resp.text = "ok"
        mock_client.models.generate_content.return_value = resp

        provider.process_chat_turn("test", [])

    call_kwargs = mock_client.models.generate_content.call_args[1]
    assert call_kwargs["model"] == "gemini-2.5-pro"


def test_gemini_provider_uses_settings_model_by_default() -> None:
    import src.config as cfg
    from google.genai import types
    from src.providers.gemini import GeminiProvider

    with patch.object(cfg.settings, "gemini_model", "gemini-2.5-flash"), \
         patch("src.providers.gemini.genai.Client") as mock_cls:
        provider = GeminiProvider()
        mock_client = mock_cls.return_value

        part = types.Part(text="ok")
        resp = MagicMock()
        resp.candidates = [MagicMock(content=types.Content(role="model", parts=[part]))]
        resp.text = "ok"
        mock_client.models.generate_content.return_value = resp

        provider.process_chat_turn("test", [])

    call_kwargs = mock_client.models.generate_content.call_args[1]
    assert call_kwargs["model"] == "gemini-2.5-flash"


# ---------------------------------------------------------------------------
# AnthropicProvider uses _model in API call
# ---------------------------------------------------------------------------

def test_anthropic_provider_uses_model_override_in_api_call() -> None:
    from src.providers.anthropic_provider import AnthropicProvider

    with patch("src.providers.anthropic_provider.anthropic.Anthropic") as mock_cls:
        provider = AnthropicProvider(model_override="claude-opus-4-5")
        mock_client = mock_cls.return_value

        tb = MagicMock()
        tb.type = "text"
        tb.text = "ok"
        resp = MagicMock()
        resp.content = [tb]
        resp.stop_reason = "end_turn"
        mock_client.messages.create.return_value = resp

        provider.process_chat_turn("test", [])

    call_kwargs = mock_client.messages.create.call_args[1]
    assert call_kwargs["model"] == "claude-opus-4-5"


def test_anthropic_provider_uses_settings_model_by_default() -> None:
    import src.config as cfg
    from src.providers.anthropic_provider import AnthropicProvider

    with patch.object(cfg.settings, "anthropic_model", "claude-sonnet-4-5"), \
         patch("src.providers.anthropic_provider.anthropic.Anthropic") as mock_cls:
        provider = AnthropicProvider()
        mock_client = mock_cls.return_value

        tb = MagicMock()
        tb.type = "text"
        tb.text = "ok"
        resp = MagicMock()
        resp.content = [tb]
        resp.stop_reason = "end_turn"
        mock_client.messages.create.return_value = resp

        provider.process_chat_turn("test", [])

    call_kwargs = mock_client.messages.create.call_args[1]
    assert call_kwargs["model"] == "claude-sonnet-4-5"


# ---------------------------------------------------------------------------
# POST /api/chat — provider / model forwarded end-to-end
# ---------------------------------------------------------------------------

@pytest.fixture
def repo(tmp_path):
    conn = SQLiteConnection(db_path=str(tmp_path / "t.db"))
    return SQLiteSessionRepository(conn)


def _make_chat_client(repo: SQLiteSessionRepository) -> TestClient:
    app.dependency_overrides[get_session_repo] = lambda: repo
    app.dependency_overrides[get_chat_service] = lambda: ChatService(
        session_repo=repo,
        turn_orchestrator=FakeOrchestrator(),
    )
    return TestClient(app)


def test_chat_endpoint_accepts_provider_and_model(repo, tmp_path) -> None:
    """POST /api/chat with provider+model must not be rejected (HTTP 200 or 500 from agent, not 422)."""
    client = TestClient(app)
    app.dependency_overrides[get_session_repo] = lambda: repo

    mock_provider = MagicMock()
    mock_provider.process_chat_turn.return_value = ("ok", [])

    with patch("src.providers.base.get_provider", return_value=mock_provider):
        resp = client.post("/api/chat", json={
            "session_id": "sess-001",
            "message": "hello",
            "provider": "anthropic",
            "model": "claude-sonnet-4-5",
        })

    # 422 = validation error (schema rejected the fields) — must not happen
    assert resp.status_code != 422, f"Schema rejected provider/model fields: {resp.text}"
    app.dependency_overrides.clear()


def test_chat_endpoint_routes_to_correct_provider(repo, tmp_path) -> None:
    """provider + model fields must be forwarded to the provider."""
    client = TestClient(app)
    app.dependency_overrides[get_session_repo] = lambda: repo

    mock_provider = MagicMock()
    mock_provider.process_chat_turn.return_value = ("response text", [])

    # Patch get_provider so the legacy path uses our mock.
    with patch("src.providers.base.get_provider", return_value=mock_provider):
        client.post("/api/chat", json={
            "session_id": "sess-002",
            "message": "test",
            "provider": "anthropic",
            "model": "claude-haiku-3-5",
        })

    mock_provider.process_chat_turn.assert_called_once()
    call_kwargs = mock_provider.process_chat_turn.call_args.kwargs
    assert call_kwargs["user_message"] == "test"
    app.dependency_overrides.clear()


def test_chat_endpoint_uses_server_default_when_no_provider(repo) -> None:
    """Omitting provider/model must use the orchestrator path."""
    client = TestClient(app)
    app.dependency_overrides[get_session_repo] = lambda: repo

    orchestrator = FakeOrchestrator()
    app.dependency_overrides[get_chat_service] = lambda: ChatService(
        session_repo=repo,
        turn_orchestrator=orchestrator,
    )

    client.post("/api/chat", json={
        "session_id": "sess-003",
        "message": "hello",
    })

    assert orchestrator.run_call_count == 1
    assert orchestrator.last_turn_input is not None
    assert orchestrator.last_turn_input.user_message == "hello"
    app.dependency_overrides.clear()


def test_chat_unknown_provider_returns_400(repo) -> None:
    """An unknown provider name must return HTTP 400, not 500."""
    client = TestClient(app)
    app.dependency_overrides[get_session_repo] = lambda: repo
    app.dependency_overrides[get_chat_service] = lambda: ChatService(
        session_repo=repo,
        turn_orchestrator=FakeOrchestrator(),
    )

    resp = client.post("/api/chat", json={
        "session_id": "sess-004",
        "message": "hello",
        "provider": "openai",
    })

    assert resp.status_code == 400
    assert "openai" in resp.json()["detail"].lower()
    app.dependency_overrides.clear()
