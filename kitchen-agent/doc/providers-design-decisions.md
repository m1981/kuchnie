# Critical Design & Implementation Decisions

_Living document — updated as the codebase evolves._  
_Audience: any developer joining the project or resuming after a break._

---

## How to read this document

Each decision is structured as:

- **Context** — what problem forced the decision
- **Decision** — what was chosen and why
- **Consequences** — what the choice rules in or out going forward
- **Location** — the exact files that implement it

---

## D-01 — Provider Abstraction (Strategy Pattern)

**Context.**  
The original `agent.py` was a single 170-line function hard-wired to the Google Gemini SDK (`google-genai`). Adding Anthropic Claude support would have required forking the entire agentic loop.

**Decision.**  
Extract a `LLMProvider` **runtime-checkable Protocol** (`src/providers/base.py`). Every provider implements one method:

```python
def process_chat_turn(
    self, user_message, history, system_instruction, images, context_files,
) -> tuple[str, list[dict]]: ...
```

`get_provider(provider_name, model_override)` is the single factory. `agent.py` becomes a thin 1-function dispatcher that calls `get_provider()` and delegates.

```
POST /api/chat
  → chat_service.handle_turn(provider_name, model_override)
    → agent.process_chat_turn(provider_name, model_override)
      → get_provider(provider_name, model_override)
        → GeminiProvider(model_override) | AnthropicProvider(model_override)
```

**Why Protocol, not ABC.**  
Structural subtyping means tests can use plain `MagicMock` objects as providers without subclassing anything. `isinstance(obj, LLMProvider)` still works at runtime.

**Consequences.**

- Adding a third provider requires: one new file in `src/providers/`, one branch in `get_provider()`, one entry in `_PROVIDER_CATALOGUE` in `main.py`. No other file changes.
- `chat_service.py`, `repositories.py`, and `serializers.py` are completely provider-agnostic.
- `get_provider()` reads `settings.llm_provider` **at call time** (not at import time) so `patch("src.config.settings")` in tests takes effect without process restart.

**Location.**  
`src/providers/base.py`, `src/providers/gemini.py`, `src/providers/anthropic_provider.py`, `src/agent.py`

---

## D-02 — Per-Request Provider + Model Override

**Context.**  
The server default provider/model is set via environment variables (`LLM_PROVIDER`, `GEMINI_MODEL`, `ANTHROPIC_MODEL`). The frontend needs to let users switch provider and model per-message without restarting the server.

**Decision.**  
`ChatRequest` gains two optional fields:

```python
provider: str | None = None   # "gemini" | "anthropic" | None → server default
model:    str | None = None   # model id override | None → provider default
```

Both are forwarded through the entire call chain:

```
ChatRequest.provider / .model
  → main.chat() validates provider ∈ _PROVIDER_MAP (→ HTTP 400 if unknown)
    → service.handle_turn(provider_name, model_override)
      → agent.process_chat_turn(provider_name, model_override)
        → get_provider(provider_name, model_override)
          → GeminiProvider(model_override=...)   # self._model = override or settings.gemini_model
          → AnthropicProvider(model_override=...) # self._model = override or settings.anthropic_model
```

**Why validate at the HTTP boundary.**  
An unknown provider name at the route level returns HTTP 400 (client error) rather than HTTP 500 (server crash). The validation is O(1) against `_PROVIDER_MAP`.

**Why `model_override` stored on the instance (`self._model`).**  
The provider is constructed once per request. Storing the resolved model name at construction time makes the value stable for the lifetime of the instance and directly inspectable in tests (`provider._model`).

**Consequences.**

- Omitting both fields is fully backward-compatible — behaviour identical to before.
- A model name that is not in the catalogue is **not** validated at the HTTP boundary (only the provider name is). Invalid model names are rejected by the upstream SDK at API call time with a clear error message.
- Sessions are single-provider. Switching provider mid-session is allowed by the API but produces a mixed-format `api_history_json` that the serializer handles correctly (see D-04).

**Location.**  
`src/schemas.py` (`ChatRequest`, `ModelInfo`, `ProviderInfo`, `ActiveProvider`), `src/main.py` (`_PROVIDER_CATALOGUE`, `_PROVIDER_MAP`, `list_providers`, `get_active_provider`), `src/providers/base.py`, `src/providers/gemini.py`, `src/providers/anthropic_provider.py`

---

## D-03 — Provider Catalogue as a Static Dict in `main.py`

**Context.**  
The frontend needs a list of available providers and their models to render the picker. Options were: (a) static dict, (b) dynamic discovery from the SDK, (c) database table.

**Decision.**  
Static dict (`_PROVIDER_CATALOGUE`) defined directly in `main.py`. No database table, no SDK discovery.

**Why static.**  
Model catalogues change a handful of times per year when providers release new models, not at runtime. Dynamic SDK discovery requires one authenticated API call per server start just to list models — wasteful and fragile. A static dict is O(1), testable without mocks, and requires zero network calls.

**When to update.**  
Edit `_PROVIDER_CATALOGUE` in `main.py` whenever a new model is released or an old one deprecated. Commit the change. No migration needed.

**Consequences.**  
The `GET /api/providers` response is static for the lifetime of a server process. This is intentional and correct.

**Location.**  
`src/main.py` (`_PROVIDER_CATALOGUE`, `_PROVIDER_MAP`, `list_providers`, `get_active_provider`)

---

## D-04 — Provider-Agnostic Serializer via `__provider` Sentinel

**Context.**  
`dehydrate_history` / `hydrate_history` in `src/serializers.py` originally assumed all history items were Gemini `types.Content` SDK objects and accessed `.parts` directly. When the Anthropic provider runs, it appends plain dicts to the history list — causing `AttributeError: 'dict' object has no attribute 'parts'` at persistence time.

**Decision.**  
`dehydrate_history` dispatches on the item type:

```python
if isinstance(item, types.Content):   # Gemini path — unchanged
    ...
elif isinstance(item, dict):          # Anthropic path — store verbatim + sentinel
    item["__provider"] = "anthropic"
```

`hydrate_history` uses the `__provider` sentinel as the discriminator:

```python
if item.get("__provider") == "anthropic":
    # strip sentinel + turn_id, return plain dict
else:
    # reconstruct types.Content (Gemini path — unchanged)
```

**Why a sentinel key, not content-shape inspection.**  
Shape inspection is fragile — both Gemini and Anthropic use `{"role": "user", "content": ...}` dicts in some forms. A sentinel is unambiguous, stable, and backwards-compatible: every legacy row without `__provider` is implicitly treated as Gemini.

**Why the serializer, not the provider.**  
The serializer is the single point of truth for on-disk format. Fixing it there means `chat_service.py` needs zero changes — it calls `dehydrate_history(history)` regardless of which provider ran. Any new provider only needs to append plain dicts; the serializer handles the rest.

**Consequences.**

- Existing sessions (Gemini) load without any migration — no `__provider` key means Gemini path.
- A session that switches provider mid-conversation serialises correctly because each item carries its own discriminator.
- `turn_id` is stripped from restored Anthropic dicts (as it is already for Gemini items) — it exists only in the stored JSON for `MessageEditService` lookups.

**Location.**  
`src/serializers.py`

---

## D-05 — Anthropic History Format (Plain Dicts, MessageParam Shape)

**Context.**  
Gemini history is a list of `types.Content` SDK objects. Anthropic history is a list of plain dicts in the `MessageParam` shape the SDK accepts directly. These two formats cannot be unified without a custom AST.

**Decision.**  
Each provider owns its history format. The `history` list passed into `process_chat_turn` is opaque to `chat_service.py` — it only passes it through and persists whatever the provider left in it. The serializer (D-04) handles the persistence boundary.

**Anthropic history items written by `AnthropicProvider`:**

```python
# User text turn (plain string content)
{"role": "user", "content": "What hinges?"}

# User turn with context files + images (list of blocks)
{"role": "user", "content": [{"type": "text", "text": "..."}, {"type": "image", ...}]}

# Assistant tool-use turn
{"role": "assistant", "content": [{"type": "tool_use", "id": "...", "name": "...", "input": {...}}]}

# User tool-result turn (fed back into next API call)
{"role": "user", "content": [{"type": "tool_result", "tool_use_id": "...", "content": "..."}]}

# Assistant final text turn
{"role": "assistant", "content": [{"type": "text", "text": "..."}]}
```

Tool results are JSON-serialised strings (`json.dumps(result)`) inside the `content` field — required by the Anthropic SDK.

**Consequences.**

- `hydrate_history` returns plain dicts for Anthropic sessions. When the Anthropic provider loads an existing session it receives exactly the dict list it originally wrote — the SDK accepts this directly in the next `messages.create` call.
- `MessageEditService` works on the raw `api_history_json` string and does turn-level operations via `turn_id` filtering — it never needs to understand provider-specific formats.

**Location.**  
`src/providers/anthropic_provider.py`, `src/serializers.py`

---

## D-06 — Tool Schema Conversion (Gemini → Anthropic)

**Context.**  
Tools are defined once in `src/tools/registry.py` as Gemini `FunctionDeclaration` objects. Anthropic requires a different schema format (`ToolParam` with `input_schema` as JSON Schema).

**Decision.**  
`AnthropicProvider.__init__` converts the registry declarations at construction time via `_declaration_to_anthropic_tool()`. The conversion is:

```
types.Schema (Gemini)  →  {"type": "object", "properties": {...}, "required": [...]}  (JSON Schema)
```

The converted schemas are cached on `self._tool_schemas`. `_build_tool_schemas()` is also called inside the agentic loop to pick up any `FUNCTION_MAP` patches applied by tests.

**Fallback.**  
If `DECLARATIONS` is empty (e.g., in tests with fully patched `FUNCTION_MAP`), minimal schemas are built directly from `FUNCTION_MAP.keys()` so tests never need to supply declaration objects.

**Consequences.**

- Tool definitions live in exactly one place (`src/tools/registry.py`). Adding a tool requires no changes to any provider.
- The Gemini `FunctionDeclaration` remains the source of truth for tool metadata (name, description, parameters). The Anthropic schema is always derived from it, never separately maintained.

**Location.**  
`src/providers/anthropic_provider.py` (`_schema_to_json_schema`, `_declaration_to_anthropic_tool`, `_build_tool_schemas`)

---

## D-07 — Turn Identity via Stable UUID (`turn_id`)

**Context.**  
`api_history_json` and `ui_history_json` are two flat lists of different lengths with no shared identity. Message editing required a 60-line positional reconstruction algorithm (`_api_footprint_start_and_length`) that was fragile and untestable in isolation.

**Decision.**  
Two UUIDs are generated per logical turn in `chat_service.handle_turn`:

```python
user_turn_id:      str = str(uuid.uuid4())  # stamps the user message
assistant_turn_id: str = str(uuid.uuid4())  # stamps ALL agent output for this turn
```

Both UUIDs are written to `ui_history_json` entries and propagated via `turn_ids` to `dehydrate_history`, which stamps every `api_history_json` item.

**Turn ownership rules:**

| History item                          | `turn_id` value     |
| ------------------------------------- | ------------------- |
| User `types.Content` (first new item) | `user_turn_id`      |
| All tool call / response items        | `assistant_turn_id` |
| Final model text                      | `assistant_turn_id` |

**Consequences.**

- `MessageEditService` finds items by filtering: `[i for i in api_items if i["turn_id"] == t]` — no positional walking.
- Delete/truncate become set operations on `turn_id` values.
- Frontend receives `turn_id` in `ui_messages` and uses it in `PATCH /api/sessions/{id}/messages/{turn_id}` — the identifier never shifts when items are deleted.
- Legacy sessions (no `turn_id`) load without error; `hydrate_history` fills in `None`. Turn-level edit/delete is unavailable for legacy turns (returns HTTP 400 with a clear message).

**Location.**  
`src/chat_service.py`, `src/serializers.py`, `src/message_editor.py`

---

## D-08 — Repository Pattern with Python Protocols

**Context.**  
The application needs to be testable without a real SQLite database and without monkey-patching the entire persistence layer.

**Decision.**  
`SessionRepository` and `NoteRepository` are defined as Python `Protocol` classes in `src/repositories.py`. The concrete implementations (`SQLiteSessionRepository`, `SQLiteNoteRepository`) are not imported anywhere except `main.py`. All business logic (`ChatService`, `MessageEditService`) depends only on the Protocol.

**Consequences.**

- Any test that needs a repository can pass a `MagicMock()` — it satisfies the Protocol structurally.
- Swapping SQLite for Postgres requires only a new concrete class; no business logic changes.
- `SQLiteConnection` is injected into the repositories (not constructed inside them) — the DB path is configurable in tests via `tmp_path`.

**Location.**  
`src/repositories.py`, `src/chat_service.py`, `src/message_editor.py`

---

## D-09 — Synchronous Agent in `ThreadPoolExecutor`

**Context.**  
The Gemini and Anthropic SDK calls are synchronous (blocking HTTP). FastAPI is async. Calling blocking code directly in an `async def` handler blocks the entire event loop.

**Decision.**  
The `chat()` route handler offloads `service.handle_turn(...)` to `loop.run_in_executor(None, partial(...))`. The executor uses the default `ThreadPoolExecutor` — one thread per concurrent chat request.

**Consequences.**

- The event loop stays free during 10–30 second model calls.
- `handle_turn` and everything below it can be plain synchronous Python — no `async/await` threading complexity inside the business logic or providers.
- Concurrent requests each get their own thread, own history list, and own provider instance — no shared mutable state.

**Location.**  
`src/main.py` (`chat()` handler)

---

## D-10 — File Mutation Safety: Search-and-Replace Only + Snapshot/Revert

**Context.**  
An autonomous agent with write access to the knowledge base can corrupt files if given an overwrite tool. One LLM hallucination can silently destroy months of notes.

**Decision.**  
Two constraints enforced architecturally:

1. **No overwrite tool.** The agent only has `edit_file(filepath, search_text, replace_text)` — it must know the exact existing text before it can change anything.

2. **Every mutation snapshots first.** `_create_backup(target_path, backup_dir)` writes a JSON file to `data/.backups/<uuid>.json` before any write. The `revert_id` is returned in the tool result and stored in `ui_history_json`. `POST /api/files/revert/{revert_id}` restores the file and deletes the backup (no double-revert).

**Backup format:**

```json
{
    "filepath": "data/notes.md",
    "existed": true,
    "content": "# Original content…"
}
```

**Consequences.**

- `backup_dir` is injected, not hard-coded — `file_ops.py` has zero dependency on `settings` (testable in isolation).
- A path-traversal guard validates the `filepath` stored **inside** the backup JSON at revert time.
- `backup_dir=None` (default) skips backup entirely — all pre-F03 tests pass unchanged.

**Location.**  
`src/tools/file_ops.py` (`_create_backup`, `revert_backup`, `edit_file`, `create_file`, `append_to_file`), `src/main.py` (`revert_file_edit`)

---

## D-11 — Path Traversal Guard

**Context.**  
The file API exposes `GET /api/files/{filepath:path}` and write endpoints. A crafted path like `../../etc/passwd` could escape `data/`.

**Decision.**  
`_resolve_data_path(filepath)` in `main.py` resolves the path and asserts it is under `settings.data_dir`:

```python
resolved = (settings.data_dir / filepath).resolve()
if not str(resolved).startswith(str(settings.data_dir.resolve())):
    raise HTTPException(status_code=400, detail="Path traversal not allowed.")
```

The same check runs at revert time on the `filepath` stored inside the backup JSON.

**Consequences.**

- Applies to the HTTP file API and the revert endpoint.
- Does **not** apply to agent tool calls — the tool registry hard-codes `base_dir=settings.data_dir` inside lambdas so the LLM never receives a `base_dir` parameter to manipulate.

**Location.**  
`src/main.py` (`_resolve_data_path`), `src/tools/file_ops.py` (`revert_backup`)

---

## D-12 — Prompt Architecture: Backend-Managed Markdown Files

**Context.**  
System prompts were originally sent from the frontend as raw strings. This made prompts hard to version-control, impossible to hot-reload, and duplicated across clients.

**Decision.**  
System prompts are Markdown files in `prompts/`. `PromptManager` loads and caches them at startup. `ChatRequest.mode_id` (default: `"general"`) selects the active prompt. The frontend sends only the mode id — never the raw prompt text.

**Resolution priority** (highest → lowest):

1. `request.system_prompt` — explicit raw override (legacy / power-user path)
2. `request.mode_id` → `PromptManager.get_system_instruction(mode_id)`

`POST /api/prompts/reload` hot-reloads files without server restart.

**Session-scoped override.**  
`PATCH /api/sessions/{id}/system-prompt` stores a raw override in the session row. It takes effect on the next message in that session only.

**Consequences.**

- Prompt changes are git-diff-able.
- The frontend mode switcher only needs `GET /api/prompts/modes` (returns `id`, `label`, `eyebrow` — never the full content).
- Full content is fetched lazily via `GET /api/prompts/modes/{id}` for the inspector panel only.

**Location.**  
`src/prompt_manager.py`, `src/main.py` (`get_prompt_modes`, `get_prompt_mode_detail`, `reload_prompts`), `prompts/`

---

## D-13 — Settings as a Pydantic-Settings Singleton

**Context.**  
Configuration values (model names, paths, API keys, CORS origins) need to be readable from environment variables, a `.env` file, or test-time overrides — without constructing `Settings()` in every module.

**Decision.**  
`settings = Settings()` is a module-level singleton in `src/config.py`. Every module imports it:

```python
from src.config import settings
```

**Test override pattern.**  
Because `get_provider()` accesses settings via `import src.config as _config; _config.settings.llm_provider`, patching `src.config.settings` correctly intercepts all attribute lookups:

```python
with patch.object(src.config.settings, "llm_provider", "anthropic"):
    ...
```

Using `patch("src.config.settings")` (whole object replacement) also works and is used in factory tests.

**Consequences.**

- Never instantiate `Settings()` outside `config.py` — it re-reads the `.env` file every time and bypasses the singleton.
- `Settings(_env_file=None)` in tests skips `.env` entirely to test pure defaults.

**Location.**  
`src/config.py`

---

## D-14 — Strict TDD: Tests Written Before Implementation

**Convention adopted for this project.**

Every feature and bugfix follows:

1. Write failing tests (RED) — assert the interface contract, not the implementation.
2. Run tests — confirm all new tests fail, all existing tests pass.
3. Write minimal implementation (GREEN).
4. Run full suite — confirm zero regressions.

**Patch targets follow the import, not the definition.**  
If `chat_service.py` does `from agent import process_chat_turn`, the correct patch target is `src.chat_service.process_chat_turn`, not `src.agent.process_chat_turn`. Patching the definition module has no effect on the already-bound name.

**Test isolation.**

- No test touches the real Gemini or Anthropic API.
- No test touches the real filesystem outside `tmp_path`.
- DB tests use `SQLiteConnection(db_path=str(tmp_path / "test.db"))`.
- Provider tests use `patch("src.providers.gemini.genai.Client")` / `patch("src.providers.anthropic_provider.anthropic.Anthropic")`.

**Coverage gate.**  
`pytest-cov` enforces ≥ 80 % branch coverage. The gate runs on every CI push.

---

## D-15 — Known Deferred Decisions (Deliberate Technical Debt)

These are limitations acknowledged and accepted in the current implementation.

| #   | Issue                                                                                                  | Current state                                                      | Correct future fix                                                                                                  |
| --- | ------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------- |
| 1   | `api_history_json` / `ui_history_json` as JSON blobs                                                   | Two unsynchronised flat lists in SQLite TEXT columns               | Normalise into `turns` + `api_parts` tables (see `doc/r002.md` for full schema)                                     |
| 2   | `save_session` full overwrite                                                                          | O(n) write for O(1) logical change                                 | Granular `update_turn_content(turn_id, content)` SQL                                                                |
| 3   | No schema migrations                                                                                   | Raw `CREATE TABLE` / `ALTER TABLE` in `repositories.py`            | Alembic                                                                                                             |
| 4   | SQLite WAL mode not enabled                                                                            | `database is locked` under concurrent requests                     | `PRAGMA journal_mode=WAL` at connection time                                                                        |
| 5   | Backup TTL not enforced                                                                                | `.backups/` grows unbounded                                        | Startup/cron job to purge entries older than 7 days                                                                 |
| 6   | Single provider per session not enforced                                                               | Switching mid-session produces mixed `__provider` items in history | Per-session provider stored in DB; reject mid-session switch at API boundary                                        |
| 7   | `main.py` monolith                                                                                     | All routes in one 1000-line file                                   | Split into `routers/chat.py`, `routers/sessions.py`, `routers/files.py`, `routers/notes.py`, `routers/providers.py` |
| 8   | Anthropic `AnthropicProvider` constructs `_tool_schemas` twice (once at init, once per loop iteration) | Redundant work in tests with patched `FUNCTION_MAP`                | Cache invalidation: rebuild only when `FUNCTION_MAP` changes identity                                               |
