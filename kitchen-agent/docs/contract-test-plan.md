# Contract Test Plan — Kitchen Agent

> **Rule: Every Protocol boundary needs a contract test that uses the real
> implementation on both sides. Mock the external dependency (API, DB),
> never the internal contract.**

Generated from `py-diagram` structural analysis on 2026-06-07.

---

## Test Folder Structure

### Why Structure Matters

When an LLM agent (or a human) opens `tests/`, they need to answer
three questions in under 5 seconds:

1. **What kind of test is this?** → folder name tells you
2. **What component does it test?** → mirrors `src/` structure
3. **Is this boundary tested?** → contract/ folder has the answer

### Current State (Problem)

```
tests/                              # 41 files dumped at root
├── test_anthropic_provider.py      # unit? contract? integration? unclear
├── test_chat_service.py            # unit with mocks
├── test_chat_provider_routing.py   # integration
├── test_providers_base.py          # protocol contract
├── test_stream_final_message.py    # ← actually in unit/agent/
├── ...39 more files...
└── unit/                           # 12 more files, separate tree
    ├── agent/
    ├── providers/
    └── ...
```

**Problems:**

- Can't tell unit from contract from integration at a glance
- `unit/` duplicates the root-level structure
- No `contract/` folder — the most important tests are invisible
- LLM agent has to read every file to find what's tested

### Target State (Solution)

```
tests/
├── conftest.py                     # shared fixtures
│
├── unit/                           # Component in isolation (1 mock per test)
│   ├── agent/
│   │   ├── test_context_assembler.py
│   │   ├── test_tool_executor.py
│   │   └── test_turn_orchestrator.py
│   ├── providers/
│   │   ├── test_anthropic_provider.py
│   │   ├── test_gemini_provider.py
│   │   ├── test_mimo_provider.py
│   │   └── test_normalizer.py
│   ├── content/
│   │   ├── test_file_manager.py
│   │   ├── test_note_manager.py
│   │   └── test_search_coordinator.py
│   ├── tools/
│   │   ├── test_file_ops.py
│   │   └── test_registry.py
│   ├── repositories/
│   │   ├── test_session_repo.py
│   │   └── test_note_repo.py
│   └── services/
│       ├── test_chat_service.py
│       ├── test_export_service.py
│       └── test_message_editor.py
│
├── contract/                       # Real implementations on BOTH sides
│   ├── test_provider_normalizer.py   # Provider → Normalizer
│   ├── test_orchestrator_provider.py # Orchestrator → Provider
│   ├── test_orchestrator_normalizer.py # Orchestrator → Normalizer (streaming)
│   ├── test_orchestrator_tools.py    # Orchestrator → ToolExecutor
│   ├── test_orchestrator_history.py  # Orchestrator → Serializer
│   ├── test_chat_orchestrator.py     # ChatService → Orchestrator
│   ├── test_protocol_compliance.py   # All Protocol implementations
│   └── test_serializer_repo.py       # Serializer → Repository roundtrip
│
├── integration/                    # Multiple real components, mock external only
│   ├── test_chat_flow.py           # Full chat turn (mock LLM API only)
│   ├── test_streaming_flow.py      # Full streaming turn (mock LLM API only)
│   ├── test_tool_loop_flow.py      # Full agentic loop (mock LLM API only)
│   └── test_session_lifecycle.py   # Create → chat → fork → export
│
└── e2e/                            # Full system with real browser (Playwright)
    ├── message-delete.spec.ts
    ├── regenerate.spec.ts
    └── truncate.spec.ts
```

### Mapping: Current Files → Target Location

| Current file                                      | Target                     | Why                                |
| ------------------------------------------------- | -------------------------- | ---------------------------------- |
| `tests/test_anthropic_provider.py`                | `tests/unit/providers/`    | Unit test with mocks               |
| `tests/test_gemini_provider.py`                   | `tests/unit/providers/`    | Unit test with mocks               |
| `tests/test_mimo_provider.py`                     | `tests/unit/providers/`    | Unit test with mocks               |
| `tests/test_chat_service.py`                      | `tests/unit/services/`     | Unit test with mocked orchestrator |
| `tests/test_providers_base.py`                    | `tests/contract/`          | Tests Protocol compliance          |
| `tests/test_serializers.py`                       | `tests/unit/`              | Unit test with mock data           |
| `tests/test_chat_provider_routing.py`             | `tests/integration/`       | Tests provider routing flow        |
| `tests/test_archive_delete.py`                    | `tests/integration/`       | Tests full session lifecycle       |
| `tests/test_context_files.py`                     | `tests/integration/`       | Tests context file injection       |
| `tests/test_main.py`                              | `tests/integration/`       | Tests FastAPI app with TestClient  |
| `tests/test_repositories.py`                      | `tests/unit/repositories/` | Unit test with real SQLite         |
| `tests/test_exporter.py`                          | `tests/unit/`              | Pure function tests                |
| `tests/test_file_ops.py`                          | `tests/unit/tools/`        | Pure function tests                |
| `tests/test_config.py`                            | `tests/unit/`              | Config parsing tests               |
| `tests/unit/test_tool_call_canonical.py`          | `tests/contract/`          | Tests type identity contract       |
| `tests/unit/test_llm_provider_protocol.py`        | `tests/contract/`          | Tests Protocol contract            |
| `tests/unit/agent/test_stream_final_message.py`   | `tests/contract/`          | Tests streaming contract           |
| `tests/unit/providers/test_normalizer.py`         | `tests/unit/providers/`    | Unit test with mock inputs         |
| `tests/unit/providers/test_provider_streaming.py` | `tests/unit/providers/`    | Unit test with mock SDK            |

---

## LLM Agent Inspection Guide

### How to find what's tested

```bash
# List all contract tests (boundaries)
find tests/contract -name "test_*.py" -exec basename {} \;

# List all untested boundaries
# (compare contract/ files against boundary list below)

# Check if a specific boundary is tested
grep -l "Provider.*Normalizer" tests/contract/*.py
```

### How to find what's missing

Look at the **Boundary Status Table** below. Any row with ❌ needs a test
in `tests/contract/`.

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

## Boundary Status Table

> **For LLM agents:** Look at the `Test File` column. If it says `—`,
> the test doesn't exist yet. Check the `Gap` column for what to write.

| ID  | Boundary                        | Status | Test File                                  | Gap                          |
| --- | ------------------------------- | ------ | ------------------------------------------ | ---------------------------- |
| B1  | API ↔ ChatService               | ⚠️     | `integration/test_chat_flow.py`            | SSE event format             |
| B2  | API ↔ Repository                | ✅     | `integration/test_session_lifecycle.py`    | —                            |
| B3  | ChatService ↔ Orchestrator      | ❌     | —                                          | Event propagation contract   |
| B4  | Orchestrator ↔ ContextAssembler | ⚠️     | `unit/agent/test_context_assembler.py`     | Field completeness           |
| B5  | Orchestrator ↔ Provider         | ❌     | —                                          | **complete/stream contract** |
| B6  | Orchestrator ↔ Normalizer       | ✅     | `contract/test_orchestrator_normalizer.py` | —                            |
| B7  | Orchestrator ↔ ToolExecutor     | ⚠️     | `unit/agent/test_tool_executor.py`         | Real registry handlers       |
| B8  | Orchestrator ↔ History format   | ❌     | —                                          | Serialize roundtrip          |
| B9  | Provider ↔ Normalizer           | ✅     | `contract/test_provider_normalizer.py`     | —                            |
| B10 | ToolRegistry ↔ ToolExecutor     | ⚠️     | `unit/tools/test_registry.py`              | Handler dispatch             |
| B11 | ContextAssembler ↔ Protocols    | ⚠️     | `unit/agent/test_context_assembler.py`     | Real impl compliance         |
| B12 | Serializer ↔ Repository         | ❌     | —                                          | SQLite roundtrip             |
| B13 | Normalizer ↔ Consumers          | ⚠️     | `unit/providers/test_normalizer.py`        | Shape contract               |
| B14 | Schema ↔ API                    | ✅     | `integration/test_main.py`                 | —                            |

### Status Legend

- ✅ **Contract tested** — real implementations on both sides, file exists
- ⚠️ **Unit tested only** — one side mocked, needs contract test
- ❌ **Not tested** — gap, test file doesn't exist

---

## Priority 1 — Critical Boundaries (Fix Now)

### B9: Provider ↔ Normalizer (stream events) — ✅ DONE

**Why critical:** The normalizer's `_from_anthropic()` assumed `raw.content`
exists. Stream control events (ParsedMessageStopEvent) don't have `.content`.

**Contract rules:**

1. `normalize_chunk(chunk, provider)` must never raise — returns `""` for
   unknown events
2. `normalize(raw, "anthropic")` must handle objects WITHOUT `.content`
3. `normalize(raw, "mimo")` must handle objects with `choices[0].delta`
   (streaming) not just `choices[0].message` (complete)

**Test file:** `tests/contract/test_provider_normalizer.py` — **35 tests**

**What's tested:**

- Anthropic: all 7 stream event types (MessageStart, ContentBlockStart,
  ContentBlockDelta with TextDelta/InputJSONDelta, ContentBlockStop,
  MessageDelta, MessageStop) — MessageStop has no `.content`, must not crash
- Anthropic: complete Message with TextBlock, ToolUseBlock, mixed, usage
- Gemini: chunks with text, empty candidates, function_call
- Gemini: complete response with text, function_call, missing usage
- Mimo: chunks with delta.content, empty choices, None content
- Mimo: complete response with text, tool_calls, invalid JSON arguments
- Cross-provider: normalize_chunk never raises on empty/None input
- Contract: NormalizedResponse shape has all required fields

### B5: Orchestrator ↔ Provider (complete + stream) — ✅ DONE

**Why critical:** FakeCompleter in orchestrator tests had no `stream()`.
The streaming pipeline was completely untested.

**Contract rules:**

1. `complete(context)` output must be parseable by `normalize(raw, provider)`
2. `stream(context)` must yield events where:
    - Text events return non-empty string from `normalize_chunk()`
    - `__final_message__` event (or last chunk) must be parseable by `normalize()`
3. `stream_with_tools()` same as `stream()`

**Test file:** `tests/contract/test_orchestrator_provider.py` — **12 tests**

**What's tested:**

- complete(): Gemini, Anthropic, Mimo text responses
- complete(): Gemini, Anthropic, Mimo tool call detection + execution
- stream(): Gemini streaming text chunks
- stream(): Anthropic streaming (real Pydantic events + **final_message**)
- stream(): Mimo streaming (deltas + **final_message**)
- stream(): Tool call detection from **final_message**
- Provider routing: turn_input.provider override via get_provider()

```python
class TestOrchestratorProviderContract:
    """
    Uses REAL ResponseNormalizer, REAL ContextAssembler.
    Mocks only the LLM API client (anthropic.OpenAI, google.genai, etc).
    """

    @pytest.fixture(params=["gemini", "anthropic", "mimo"])
    def provider(self, request): ...

    def test_complete_returns_normalizeable(self, provider): ...
    def test_stream_text_only(self, provider): ...
    def test_stream_with_tool_calls(self, provider): ...
    def test_stream_with_tools_continues(self, provider): ...
```

---

## Priority 2 — Important Boundaries (Next Sprint)

### B3: ChatService ↔ TurnOrchestrator

**Test file:** `tests/contract/test_chat_orchestrator.py`

```python
class TestChatOrchestratorContract:
    """
    Uses REAL ChatService, REAL TurnOrchestrator.
    Mocks only the LLM API and Repository.
    """

    def test_text_deltas_reach_caller(self): ...
    def test_tool_call_events_reach_caller(self): ...
    def test_done_event_reaches_caller(self): ...
    def test_error_wrapped_as_event(self): ...
```

### B7: Orchestrator ↔ ToolExecutor

**Test file:** `tests/contract/test_orchestrator_tools.py`

```python
class TestOrchestratorToolContract:
    """
    Uses REAL ToolExecutor, REAL ToolRegistry with REAL handlers.
    Only mocks the LLM API.
    """

    def test_read_file_returns_string_content(self): ...
    def test_unknown_tool_returns_error_result(self): ...
    def test_tool_result_feedable_to_provider(self): ...
```

### B8: Orchestrator ↔ History Format

**Test file:** `tests/contract/test_orchestrator_history.py`

```python
class TestOrchestratorHistoryContract:
    """
    History from TurnOrchestrator must survive dehydrate/hydrate roundtrip.
    Uses REAL serializers.
    """

    def test_text_turn_survives_roundtrip(self): ...
    def test_tool_turn_survives_roundtrip(self): ...
    def test_multi_turn_survives_roundtrip(self): ...
```

### B4: Orchestrator ↔ ContextAssembler

**Test file:** `tests/contract/test_orchestrator_context.py`

```python
class TestOrchestratorContextContract:
    """
    AssembledContext must have all fields that orchestrator and providers read.
    Uses REAL ContextAssembler, REAL PromptManager, REAL TokenCounter.
    """

    def test_context_has_all_required_fields(self): ...
    def test_messages_in_common_format(self): ...
    def test_budget_enforced(self): ...
```

---

## Priority 3 — Coverage Gaps (Backlog)

### B11: ContextAssembler ↔ Protocol Implementations

**Test file:** `tests/contract/test_protocol_compliance.py`

```python
class TestProtocolCompliance:
    """Real implementations must satisfy their Protocol contracts."""

    def test_prompt_manager_satisfies_protocol(self): ...
    def test_token_counter_satisfies_protocol(self): ...
    def test_note_manager_satisfies_protocol(self): ...
    def test_file_manager_satisfies_protocol(self): ...
```

### B1: API ↔ ChatService (SSE format)

**Test file:** `tests/integration/test_chat_flow.py`

```python
class TestChatSSEFormat:
    """SSE events must match frontend expectations."""

    def test_text_delta_format(self): ...
    def test_done_event_format(self): ...
    def test_error_event_format(self): ...
```

### B12: Serializer ↔ Repository

**Test file:** `tests/contract/test_serializer_repo.py`

```python
class TestSerializerRepoContract:
    """dehydrate → save → load → hydrate must be lossless."""

    def test_full_roundtrip_via_sqlite(self, tmp_path): ...
```

---

## Test Execution Matrix

| Priority | Boundary | Test File                                  | Tests  | Status     |
| -------- | -------- | ------------------------------------------ | ------ | ---------- |
| P1       | B9       | `contract/test_provider_normalizer.py`     | 35     | ✅ Done    |
| P1       | B5       | `contract/test_orchestrator_provider.py`   | 12     | ❌ Write   |
| P1       | B6       | `contract/test_orchestrator_normalizer.py` | 7      | ✅ Done    |
| P2       | B3       | `contract/test_chat_orchestrator.py`       | 4      | ❌ Write   |
| P2       | B7       | `contract/test_orchestrator_tools.py`      | 3      | ❌ Write   |
| P2       | B8       | `contract/test_orchestrator_history.py`    | 3      | ❌ Write   |
| P2       | B4       | `contract/test_orchestrator_context.py`    | 3      | ❌ Write   |
| P3       | B11      | `contract/test_protocol_compliance.py`     | 4      | ⚠️ Partial |
| P3       | B1       | `integration/test_chat_flow.py`            | 3      | ⚠️ Partial |
| P3       | B12      | `contract/test_serializer_repo.py`         | 1      | ❌ Write   |
|          |          |                                            | **47** |            |

---

## Checklist: Before Merging Any Provider Change

- [ ] `contract/test_orchestrator_provider.py` passes for the changed provider
- [ ] `contract/test_provider_normalizer.py` passes for the changed provider
- [ ] `contract/test_orchestrator_normalizer.py` passes (streaming pipeline)
- [ ] `unit/agent/test_turn_orchestrator.py` passes (non-streaming pipeline)
- [ ] Full suite passes (`pytest tests/`)

---

## Migration Plan

Moving files is risky — it breaks git history and CI. Do it incrementally:

### Phase 1: Create contract/ — ✅ DONE

- [x] `tests/contract/test_orchestrator_normalizer.py` — B6 — 7 tests
- [x] `tests/contract/test_provider_normalizer.py` — B9 — 35 tests
- [ ] `tests/contract/test_orchestrator_provider.py` — B5 — 12 tests

### Phase 2: Move unit tests

- [ ] Move `tests/test_anthropic_provider.py` → `tests/unit/providers/`
- [ ] Move `tests/test_gemini_provider.py` → `tests/unit/providers/`
- [ ] Move `tests/test_mimo_provider.py` → `tests/unit/providers/`
- [ ] Move `tests/test_chat_service.py` → `tests/unit/services/`
- [ ] Move `tests/test_exporter.py` → `tests/unit/`
- [ ] Move `tests/test_file_ops.py` → `tests/unit/tools/`
- [ ] Move `tests/test_repositories.py` → `tests/unit/repositories/`
- [ ] Move remaining root-level unit tests → `tests/unit/`

### Phase 3: Move integration tests

- [ ] Move `tests/test_chat_provider_routing.py` → `tests/integration/`
- [ ] Move `tests/test_archive_delete.py` → `tests/integration/`
- [ ] Move `tests/test_context_files.py` → `tests/integration/`
- [ ] Move `tests/test_main.py` → `tests/integration/`
- [ ] Move remaining integration tests → `tests/integration/`

### Phase 4: Clean up

- [ ] Remove duplicate tests
- [ ] Update CI paths
- [ ] Update this document with final file locations

---

## Progress Log

| Date       | Boundary     | Status | Notes                                                                |
| ---------- | ------------ | ------ | -------------------------------------------------------------------- |
| 2026-06-07 | B6           | ✅     | `test_stream_final_message.py` — Anthropic streaming fix             |
| 2026-06-07 | B5 (partial) | ✅     | `test_llm_provider_protocol.py` — Protocol completeness              |
| 2026-06-07 | B9           | ✅     | `contract/test_provider_normalizer.py` — 35 tests, real SDK types    |
| 2026-06-07 | B5 (full)    | ✅     | `contract/test_orchestrator_provider.py` — 12 tests, all 3 providers |
|            |              |        |                                                                      |
