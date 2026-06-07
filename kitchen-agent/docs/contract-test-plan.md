# Contract Test Plan — Kitchen Agent

> **Rule: Every Protocol boundary needs a contract test that uses the real
> implementation on both sides. Mock the external dependency (API, DB),
> never the internal contract.**

Generated from `py-diagram` structural analysis on 2026-06-07.

---

## Architecture Boundaries Map

```
┌─────────────────────────────────────────────────────────────────────┐
│                        HTTP LAYER (FastAPI)                         │
│  api/chat ── api/sessions ── api/providers ── api/files ── api/... │
└────────┬────────────────────────────┬───────────────────────────────┘
         │                            │
    B1: API ↔ ChatService        B2: API ↔ Repository
         │                            │
┌────────▼────────────────────────────▼───────────────────────────────┐
│                       SERVICE LAYER                                 │
│  ChatService ── MessageEditService ── ExportService ── PromptManager│
└────────┬────────────────────────────────────────────────────────────┘
         │
    B3: ChatService ↔ TurnOrchestrator
         │
┌────────▼────────────────────────────────────────────────────────────┐
│                    ORCHESTRATION LAYER                               │
│  TurnOrchestrator                                                    │
│  ├── ContextAssembler (B4)                                           │
│  ├── LLMProvider.complete() / .stream() (B5) ← THE CRITICAL SEAM    │
│  ├── ResponseNormalizer (B6)                                         │
│  └── ToolExecutor (B7)                                               │
└────────┬────────────────────────────────────────────────────────────┘
         │
    B8: Orchestrator ↔ Repository (history persistence)
         │
┌────────▼────────────────────────────────────────────────────────────┐
│                      PROVIDER LAYER                                  │
│  GeminiProvider ── AnthropicProvider ── MimoProvider                 │
│           ↕               ↕               ↕                          │
│         B9: Provider ↔ Normalizer (stream events)                    │
└─────────────────────────────────────────────────────────────────────┘
         │
┌────────▼────────────────────────────────────────────────────────────┐
│                    INFRASTRUCTURE LAYER                              │
│  SQLiteSessionRepository ── SQLiteNoteRepository ── TokenCounter    │
│  FileOps ── ToolRegistry ── SearchCoordinator                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Boundary Inventory

| ID  | Boundary                        | Producer                                      | Consumer             | Contract Type                 |
| --- | ------------------------------- | --------------------------------------------- | -------------------- | ----------------------------- |
| B1  | API ↔ ChatService               | `api.chat`                                    | `ChatService`        | Request/Response shape        |
| B2  | API ↔ Repository                | `api.sessions`                                | `SessionRepository`  | Data persistence              |
| B3  | ChatService ↔ Orchestrator      | `ChatService`                                 | `TurnOrchestrator`   | TurnInput → TurnOutput        |
| B4  | Orchestrator ↔ ContextAssembler | `ContextAssembler`                            | `TurnOrchestrator`   | AssembledContext shape        |
| B5  | **Orchestrator ↔ Provider**     | `LLMProvider`                                 | `TurnOrchestrator`   | **complete/stream contract**  |
| B6  | **Orchestrator ↔ Normalizer**   | `ResponseNormalizer`                          | `TurnOrchestrator`   | **normalize/normalize_chunk** |
| B7  | Orchestrator ↔ ToolExecutor     | `ToolExecutor`                                | `TurnOrchestrator`   | ToolCall → ToolResult         |
| B8  | Orchestrator ↔ History format   | `TurnOrchestrator`                            | `SessionRepository`  | Message dict shape            |
| B9  | **Provider ↔ Normalizer**       | Provider.stream()                             | `ResponseNormalizer` | **Stream event shape**        |
| B10 | ToolRegistry ↔ ToolExecutor     | `ToolRegistry`                                | `ToolExecutor`       | Handler resolution            |
| B11 | ContextAssembler ↔ Protocols    | `PromptManager`, `NoteManager`, `FileManager` | `ContextAssembler`   | Protocol compliance           |
| B12 | Serializer ↔ Repository         | `dehydrate/hydrate`                           | `SessionRepository`  | JSON roundtrip                |
| B13 | Normalizer ↔ Consumers          | `NormalizedResponse`                          | All consumers        | Dataclass shape               |
| B14 | Schema ↔ API                    | Pydantic models                               | FastAPI endpoints    | Validation                    |

---

## Current Coverage Assessment

### Legend

- ✅ **Contract tested** — real implementations on both sides
- ⚠️ **Unit tested only** — one side mocked
- ❌ **Not tested** — gap

| ID     | Boundary                        | Status | Existing Tests                                           | Gap Description                                 |
| ------ | ------------------------------- | ------ | -------------------------------------------------------- | ----------------------------------------------- |
| B1     | API ↔ ChatService               | ⚠️     | `test_chat_service.py`, `test_chat_provider_routing.py`  | ChatService mocked in API tests                 |
| B2     | API ↔ Repository                | ⚠️     | `test_archive_delete.py`, `test_fork.py`                 | API tests use real SQLite repo ✅               |
| B3     | ChatService ↔ Orchestrator      | ⚠️     | `test_chat_service.py`                                   | Orchestrator mocked in ChatService tests        |
| B4     | Orchestrator ↔ ContextAssembler | ⚠️     | `test_context_assembler.py`, `test_turn_orchestrator.py` | Uses fake token counter                         |
| **B5** | **Orchestrator ↔ Provider**     | ❌     | `test_turn_orchestrator.py`                              | **FakeCompleter has no stream()**               |
| **B6** | **Orchestrator ↔ Normalizer**   | ❌     | `test_stream_final_message.py` (new)                     | **Just added — was completely missing**         |
| B7     | Orchestrator ↔ ToolExecutor     | ⚠️     | `test_tool_executor.py`, `test_turn_orchestrator.py`     | Fake registry, real executor                    |
| B8     | Orchestrator ↔ History format   | ⚠️     | `test_serializers.py`                                    | Serializer tested in isolation                  |
| **B9** | **Provider ↔ Normalizer**       | ❌     | `test_normalizer.py`, `test_provider_streaming.py`       | **Tests use mocks, never real provider output** |
| B10    | ToolRegistry ↔ ToolExecutor     | ⚠️     | `test_tool_registry.py`, `test_registry.py`              | Real registry, fake executor                    |
| B11    | ContextAssembler ↔ Protocols    | ⚠️     | `test_context_assembler.py`                              | Fake implementations                            |
| B12    | Serializer ↔ Repository         | ⚠️     | `test_serializers.py`                                    | Roundtrip tested, but not with real repo        |
| B13    | Normalizer ↔ Consumers          | ⚠️     | `test_normalizer.py`                                     | Shape tested, but not with real consumers       |
| B14    | Schema ↔ API                    | ✅     | `test_main.py`, `test_provider_endpoints.py`             | Pydantic validation tested                      |

---

## Priority 1 — Critical Boundaries (Fix Now)

### B5: Orchestrator ↔ Provider (complete + stream)

**Why critical:** This is the boundary where the Anthropic streaming bug lived.
The FakeCompleter in orchestrator tests had no `stream()` method.

**Contract rules:**

1. `complete(context)` must return an object `normalize(raw, provider)` can parse
2. `complete_with_tools(context, tool_calls, tool_results)` same
3. `stream(context)` must yield events where:
    - `normalize_chunk(chunk, provider)` returns `str` for text events
    - The last meaningful event (or a `__final_message__` event) must be
      parseable by `normalize(raw, provider)` for tool call detection
4. `stream_with_tools(context, tool_calls, tool_results)` same as `stream()`

**Test plan:**

```python
# tests/unit/agent/test_provider_orchestrator_contract.py

class TestProviderOrchestratorContract:
    """
    Contract: Provider.stream() output must be consumable by
    TurnOrchestrator.stream() without crashing.

    Uses REAL ResponseNormalizer, REAL ContextAssembler.
    Only the LLM API is mocked.
    """

    @pytest.fixture(params=["gemini", "anthropic", "mimo"])
    def provider(self, request):
        """Create real provider with mocked SDK client."""
        ...

    def test_complete_returns_normalizeable_response(self, provider):
        """complete() output must work with normalize()."""
        normalizer = ResponseNormalizer()
        context = _make_assembled_context()
        raw = provider.complete(context)
        result = normalizer.normalize(raw, provider_name)
        assert isinstance(result.text, str)
        assert isinstance(result.tool_calls, list)

    def test_stream_text_only(self, provider):
        """stream() text-only response: chunks extract text, final message normalizes."""
        normalizer = ResponseNormalizer()
        context = _make_assembled_context()

        chunks = list(provider.stream(context))
        # Must have yielded something
        assert len(chunks) > 0

        # All text chunks must be extractable
        text = ""
        final_message = None
        for chunk in chunks:
            if isinstance(chunk, dict) and chunk.get("type") == "__final_message__":
                final_message = chunk["message"]
                continue
            delta = normalizer.normalize_chunk(chunk, provider_name)
            text += delta

        # Final message (or last chunk) must normalize for tool detection
        msg = final_message or chunks[-1]
        normalized = normalizer.normalize(msg, provider_name)
        assert normalized.text  # non-empty for text response

    def test_stream_with_tool_calls(self, provider):
        """stream() with tool calls: final message must contain tool_calls."""
        normalizer = ResponseNormalizer()
        context = _make_assembled_context(tool_schemas=REAL_SCHEMAS)

        chunks = list(provider.stream(context))
        final_message = None
        for chunk in chunks:
            if isinstance(chunk, dict) and chunk.get("type") == "__final_message__":
                final_message = chunk["message"]

        if final_message:
            normalized = normalizer.normalize(final_message, provider_name)
            # If the model returned tool calls, they must be parseable
            if normalized.has_tool_calls:
                assert all(tc.name for tc in normalized.tool_calls)
```

### B9: Provider ↔ Normalizer (stream events)

**Why critical:** The normalizer's `_from_anthropic()` assumed `raw.content` exists.
Stream control events (ParsedMessageStopEvent) don't have `.content`.

**Contract rules:**

1. `normalize(raw, "gemini")` must handle objects with `candidates[0].content.parts`
2. `normalize(raw, "anthropic")` must handle objects with `.content` list
3. `normalize(raw, "mimo")` must handle objects with `choices[0].message`
4. `normalize_chunk(chunk, provider)` must never raise — returns `""` for unknown events
5. `normalize()` must handle objects WITHOUT `.content` gracefully (stream control events)

**Test plan:**

```python
# tests/unit/providers/test_normalizer_contract.py

class TestNormalizerContract:
    """
    Contract: ResponseNormalizer must handle ALL event types that
    providers can yield, including stream control events.
    """

    def test_anthropic_handles_message_stop_event(self):
        """ParsedMessageStopEvent has no .content — must not crash."""
        stop_event = MagicMock(spec=[])  # No .content attribute
        normalizer = ResponseNormalizer()
        # Should not raise AttributeError
        result = normalizer.normalize_chunk(stop_event, "anthropic")
        assert result == ""

    def test_anthropic_handles_content_block_delta(self):
        delta = MagicMock()
        delta.type = "content_block_delta"
        delta.delta = MagicMock(type="text_delta", text="hello")
        normalizer = ResponseNormalizer()
        assert normalizer.normalize_chunk(delta, "anthropic") == "hello"

    def test_gemini_handles_chunk_without_candidates(self):
        chunk = MagicMock()
        chunk.candidates = []
        normalizer = ResponseNormalizer()
        assert normalizer.normalize_chunk(chunk, "gemini") == ""

    def test_mimo_handles_chunk_without_choices(self):
        chunk = MagicMock()
        chunk.choices = []
        normalizer = ResponseNormalizer()
        assert normalizer.normalize_chunk(chunk, "mimo") == ""
```

### B6: Orchestrator ↔ Normalizer (streaming pipeline)

**Why critical:** This is the exact seam where the bug happened.
Orchestrator passed the last raw chunk to `normalize()`.

**Test plan:** ✅ Already added in `test_stream_final_message.py`

---

## Priority 2 — Important Boundaries (Next Sprint)

### B3: ChatService ↔ TurnOrchestrator

**Contract:** `ChatService.stream_turn()` consumes `TurnOrchestrator.stream()` events.

```python
# tests/test_chat_orchestrator_contract.py

class TestChatServiceOrchestratorContract:
    """
    Contract: ChatService.stream_turn() must correctly propagate
    all TurnOrchestrator.stream() event types to the caller.
    """

    def test_text_deltas_propagated(self):
        """text_delta events from orchestrator reach the caller."""

    def test_tool_call_events_propagated(self):
        """tool_call events from orchestrator reach the caller."""

    def test_done_event_propagated(self):
        """done event from orchestrator reaches the caller."""

    def test_error_propagated(self):
        """Exceptions from orchestrator are wrapped as error events."""
```

### B4: Orchestrator ↔ ContextAssembler

**Contract:** `ContextAssembler.assemble()` returns `AssembledContext` with all required fields.

```python
# tests/unit/agent/test_context_assembler_contract.py

class TestContextAssemblerContract:
    """
    Contract: AssembledContext must have all fields that
    TurnOrchestrator and providers depend on.
    """

    def test_assembled_context_has_required_fields(self):
        """All fields that orchestrator reads must be present."""
        context = assembler.assemble(session, mode, message, ...)
        assert hasattr(context, "system_prompt")
        assert hasattr(context, "messages")
        assert hasattr(context, "images")
        assert hasattr(context, "context_files")
        assert hasattr(context, "tool_schemas")
        assert hasattr(context, "total_tokens_estimated")
        assert hasattr(context, "slots_used")

    def test_messages_in_common_format(self):
        """Messages must be in the common format (role, content, tool_calls)."""
        context = assembler.assemble(session, mode, message, ...)
        for msg in context.messages:
            assert "role" in msg
            assert "content" in msg or "tool_calls" in msg
```

### B7: Orchestrator ↔ ToolExecutor

**Contract:** `ToolExecutor.execute_all()` returns `list[ToolResult]` that orchestrator can feed back.

```python
# tests/unit/agent/test_tool_executor_contract.py

class TestToolExecutorContract:
    """
    Contract: ToolResult must be feedable to provider.complete_with_tools().
    Uses real ToolRegistry + real file_ops handlers.
    """

    def test_read_file_returns_string_content(self):
        """read_file tool must return string content in ToolResult."""
        registry = build_default_registry()
        executor = ToolExecutor(registry)
        results = executor.execute_all([
            ToolCall(id="1", name="read_file", arguments={"filepath": __file__})
        ])
        assert results[0].is_error is False
        assert isinstance(results[0].content, str)
        assert len(results[0].content) > 0

    def test_unknown_tool_returns_error(self):
        """Unknown tool name must not crash — returns error result."""
        registry = build_default_registry()
        executor = ToolExecutor(registry)
        results = executor.execute_all([
            ToolCall(id="1", name="nonexistent", arguments={})
        ])
        assert results[0].is_error is True
```

### B8: Orchestrator ↔ History Format

**Contract:** `TurnOutput.updated_api_history` must be dehydratable by serializers.

```python
# tests/unit/agent/test_history_format_contract.py

class TestHistoryFormatContract:
    """
    Contract: History produced by TurnOrchestrator must survive
    serialize → deserialize roundtrip via dehydrate_history/hydrate_history.
    """

    def test_history_survives_roundtrip(self):
        orchestrator = make_orchestrator(text="Hello")
        output = orchestrator.run(session=make_session(), turn_input=...)

        # Serialize
        json_str = dehydrate_history(output.updated_api_history, turn_ids=None)

        # Deserialize
        restored = hydrate_history(json_str)

        # Must preserve structure
        assert len(restored) == len(output.updated_api_history)
        assert restored[-1]["role"] == "assistant"
        assert restored[-1]["content"] == "Hello"
```

---

## Priority 3 — Coverage Gaps (Backlog)

### B1: API ↔ ChatService

```python
# tests/test_api_chat_contract.py

class TestAPIChatContract:
    """SSE stream format contract with frontend."""

    def test_stream_sends_valid_sse_events(self):
        """Every SSE event must have 'data:' prefix and valid JSON."""

    def test_stream_text_delta_format(self):
        """text_delta events: {"type": "text_delta", "content": "..."}"""

    def test_stream_done_event_format(self):
        """done event includes provider, model, user_turn_id, assistant_turn_id."""
```

### B11: ContextAssembler ↔ Protocol Implementations

```python
# tests/unit/agent/test_protocol_implementation_contract.py

class TestProtocolImplementationContract:
    """Real implementations must satisfy their Protocol contracts."""

    def test_prompt_manager_satisfies_protocol(self):
        pm = PromptManager(prompts_dir=settings.prompts_dir)
        assert isinstance(pm, PromptManagerProtocol)

    def test_token_counter_satisfies_protocol(self):
        tc = TokenCounter()
        assert isinstance(tc, TokenCounterProtocol)

    def test_note_manager_satisfies_protocol(self):
        nm = NoteManager(repo=..., search=..., token_counter=...)
        assert isinstance(nm, NoteManagerProtocol)

    def test_file_manager_satisfies_protocol(self):
        fm = FileManager(token_counter=...)
        assert isinstance(fm, FileManagerProtocol)
```

### B12: Serializer ↔ Repository

```python
# tests/test_serializer_repo_contract.py

class TestSerializerRepoContract:
    """dehydrate → save → load → hydrate must be lossless."""

    def test_full_roundtrip_via_sqlite(self, tmp_path):
        """Write session, read back, hydrate — must match original."""
```

---

## Test Execution Matrix

| Priority  | Tests                           | Estimated    | Dependencies             |
| --------- | ------------------------------- | ------------ | ------------------------ |
| P1-B5     | Provider ↔ Orchestrator         | 12 tests     | Real providers, mock SDK |
| P1-B6     | Orchestrator ↔ Normalizer       | 7 tests ✅   | Done                     |
| P1-B9     | Provider ↔ Normalizer           | 9 tests      | Real normalizer          |
| P2-B3     | ChatService ↔ Orchestrator      | 6 tests      | Mock orchestrator events |
| P2-B4     | Orchestrator ↔ ContextAssembler | 5 tests      | Real assembler           |
| P2-B7     | Orchestrator ↔ ToolExecutor     | 4 tests      | Real registry            |
| P2-B8     | Orchestrator ↔ History          | 3 tests      | Real serializers         |
| P3-B1     | API ↔ ChatService               | 4 tests      | FastAPI TestClient       |
| P3-B11    | ContextAssembler ↔ Protocols    | 4 tests      | Real implementations     |
| P3-B12    | Serializer ↔ Repository         | 3 tests      | Real SQLite              |
| **Total** |                                 | **57 tests** |                          |

---

## Execution Order

1. **P1-B9** — Provider ↔ Normalizer (catches stream event shape bugs)
2. **P1-B5** — Provider ↔ Orchestrator (catches complete/stream contract bugs)
3. P2-B7 — ToolExecutor contract (catches tool dispatch bugs)
4. P2-B8 — History format contract (catches persistence bugs)
5. P2-B4 — ContextAssembler contract (catches context building bugs)
6. P2-B3 — ChatService ↔ Orchestrator (catches event propagation bugs)
7. P3-B11 — Protocol implementations (catches interface drift)
8. P3-B1 — API contract (catches SSE format bugs)
9. P3-B12 — Serializer roundtrip (catches data loss bugs)

---

## Checklist: Before Merging Any Provider Change

- [ ] `test_provider_orchestrator_contract.py` passes for the changed provider
- [ ] `test_normalizer_contract.py` passes for the changed provider's event types
- [ ] `test_stream_final_message.py` passes (streaming pipeline)
- [ ] `test_turn_orchestrator.py` passes (non-streaming pipeline)
- [ ] Full suite passes (`pytest tests/`)

---

## Progress Log

| Date       | Boundary     | Status  | Notes                                                    |
| ---------- | ------------ | ------- | -------------------------------------------------------- |
| 2026-06-07 | B6           | ✅ Done | `test_stream_final_message.py` — Anthropic streaming fix |
| 2026-06-07 | B5 (partial) | ✅ Done | `test_llm_provider_protocol.py` — Protocol completeness  |
|            |              |         |                                                          |
