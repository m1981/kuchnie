# R004 — Tools Toggle (Option C)

**Date:** 2026-06-01  
**Status:** Implemented, 739/739 tests green

---

## Problem

Every chat request ran through the full agentic tool-calling loop, even for
simple conversational queries where the user just wanted a direct LLM reply
without the agent scanning the knowledge base.

---

## Decision — Option C (mode default + per-request override)

Two orthogonal axes:

| Axis                     | Where                                                     | Meaning                                 |
| ------------------------ | --------------------------------------------------------- | --------------------------------------- |
| **Mode default**         | `prompts/modes.json` → `PromptMode.tools_enabled_default` | Expected behaviour for this domain/mode |
| **Per-request override** | `ChatRequest.tools_enabled` (bool)                        | User's explicit intent for this message |

Resolution rule in `POST /api/chat`:

```python
use_tools = request.tools_enabled and mode_obj.tools_enabled_default
```

- `request.tools_enabled=False` → **always off** (explicit user disable)
- `request.tools_enabled=True` (default) + mode default `False` → **off** (mode wins)
- `request.tools_enabled=True` + mode default `True` → **on** (normal agentic)

This means `tools_enabled=False` in the request is a hard override; `True` defers to the mode.

---

## Changes

### Backend

#### `prompts/modes.json`

Optional `"tools_enabled"` key per entry (default `true` when absent):

```json
{
    "id": "chat",
    "label": "Chat",
    "eyebrow": "Direct conversation",
    "file": "chat.md",
    "tools_enabled": false
}
```

#### `src/prompt_manager.py`

- `PromptMode` — new field `tools_enabled_default: bool = True`
- `_load_mode_registry()` — preserves `tools_enabled` key from JSON (previously dropped all optional keys)
- `reload_prompts()` — reads `tools_enabled`, coerces non-bool to `True` (safe default)
- `get_all_modes()` — includes `tools_enabled_default` in metadata dicts
- `get_mode(mode_id)` — new method returning the full `PromptMode | None`

#### `src/schemas.py`

- `ChatRequest` — new field `tools_enabled: bool = True`
- `AppInfo` — (from R003, added in same session)

#### `src/agent.py`

- `process_chat_turn()` — new `use_tools: bool = True` parameter, forwarded to provider

#### `src/providers/base.py`

- `LLMProvider` Protocol — `process_chat_turn` signature updated with `use_tools: bool = True`

#### `src/providers/gemini.py`

- `process_chat_turn()` — accepts `use_tools`
- `GenerateContentConfig` — `tools=[self._tools] if use_tools else []`
- New **direct call branch**: when `use_tools=False`, one `generate_content` call, no `while True` loop, returns `(text, [])`

#### `src/providers/anthropic_provider.py`

- `process_chat_turn()` — accepts `use_tools`
- `create_kwargs["tools"]` — `tool_schemas if use_tools else []`
- New **direct call branch**: when `use_tools=False`, one `messages.create` call, no loop, returns `(text, [])`

#### `src/chat_service.py`

- `handle_turn()` — new `use_tools: bool = True` parameter, forwarded to `process_chat_turn`
- Log line includes `use_tools` for observability

#### `src/main.py`

- `POST /api/chat` — resolves effective `use_tools` from request + mode default, passes to `service.handle_turn()`

---

### Frontend

#### `frontend/src/lib/api.ts`

- `PromptMode` type — `tools_enabled_default: boolean` field added
- `ChatRequest` type — `tools_enabled?: boolean` field added

#### `frontend/src/lib/stores/chat.svelte.ts`

- New `toolsEnabled` `$state<boolean>(true)` rune
- `get toolsEnabled()` getter exposed
- `toggleTools()` — flip the flag
- `setToolsEnabled(value)` — explicit set
- `setSelectedModeId(id, modes?)` — when `modes` provided, syncs `toolsEnabled` to `mode.tools_enabled_default`
- `loadModes()` — syncs `toolsEnabled` to active mode default after fetch
- `sendMessage()` — sends `tools_enabled: false` only when off (omits field when `true` to let server use mode default)

#### `frontend/src/lib/components/ChatComposer.svelte`

- Mode pills now call `setSelectedModeId(mode.id, modes)` to trigger tool-sync
- New **⚡ Tools / 💬 Chat** toggle button in the bottom toolbar
    - `aria-pressed` for accessibility
    - Descriptive `title` tooltip explaining current state
    - Visual state: accent-tinted when on, muted when off

---

## UX

```
[ 🔧 General ▾ ] [ 📐 Design ▾ ] [ 🔨 Assembly ▾ ]   ···   [ ⚡ Tools ] [ + New chat ]
                                                              ↑
                                                   click toggles to [ 💬 Chat ]
```

- Switching to a mode with `tools_enabled: false` in `modes.json` auto-flips the button to Chat
- User can override at any time regardless of mode
- State is **per-composer** (not per-session) — intentionally resets when a new chat starts

---

## Tests added

| File                               | Tests     | What                                                                     |
| ---------------------------------- | --------- | ------------------------------------------------------------------------ |
| `tests/test_tools_toggle.py`       | 24 new    | PromptMode default, ChatService threading, HTTP endpoint, agent dispatch |
| `tests/test_gemini_provider.py`    | 4 new     | `use_tools=False` path: single call, no tools in config, correct history |
| `tests/test_anthropic_provider.py` | 4 new     | `use_tools=False` path: single call, empty tools list, correct history   |
| `tests/test_agent_dispatcher.py`   | 2 updated | `use_tools=True` included in expected call assertions                    |

**Total: 739 tests, 0 failures.**
