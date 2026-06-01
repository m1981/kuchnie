# R004 — Tools Toggle: End-to-End Sequence Diagram

## Option C Resolution Rule

```
use_tools = request.tools_enabled AND mode.tools_enabled_default
```

| request.tools_enabled | mode.tools_enabled_default | effective use_tools | Scenario                       |
| --------------------- | -------------------------- | ------------------- | ------------------------------ |
| `true` (default)      | `true` (default)           | **true**            | Normal agentic loop            |
| `true` (default)      | `false`                    | **false**           | Mode defaults to chat-only     |
| `false` (explicit)    | `true`                     | **false**           | User explicitly disabled tools |
| `false` (explicit)    | `false`                    | **false**           | Both off                       |

---

## Full Request Flow

```mermaid
sequenceDiagram
    participant User as User (Browser)
    participant Composer as ChatComposer<br/>Svelte Component
    participant Store as chatStore<br/>Svelte Rune Store
    participant API as api.chat()<br/>Fetch Client
    participant FastAPI as POST /api/chat<br/>FastAPI Route
    participant PM as PromptManager
    participant Svc as ChatService
    participant Agent as agent.process_chat_turn
    participant Provider as GeminiProvider /<br/>AnthropicProvider
    participant LLM as LLM API<br/>(Gemini / Claude)

    %% ── Frontend: Mode Selection ──────────────────────────────
    rect rgb(230, 245, 255)
    Note over User,Store: 1. Mode selection (sets tools default)
    User->>Composer: Clicks mode pill (e.g. "Chat")
    Composer->>Store: setSelectedModeId("chat", modes)
    Store->>Store: toolsEnabled = mode.tools_enabled_default<br/>(false for "chat" mode)
    end

    %% ── Frontend: Manual Override ─────────────────────────────
    rect rgb(255, 245, 230)
    Note over User,Store: 2. Manual toggle (optional override)
    User->>Composer: Clicks ⚡Tools / 💬Chat toggle
    Composer->>Store: toggleTools()
    Store->>Store: toolsEnabled = !toolsEnabled
    end

    %% ── Frontend: Send Message ────────────────────────────────
    rect rgb(230, 255, 230)
    Note over User,API: 3. Send message with tools_enabled flag
    User->>Composer: Types message + Send
    Composer->>Store: sendMessage(text)
    Store->>Store: Build ChatRequest:<br/>tools_enabled = toolsEnabled ? undefined : false
    Store->>API: api.chat({session_id, message, mode_id,<br/>tools_enabled: false | undefined})
    API->>FastAPI: POST /api/chat (JSON body)
    end

    %% ── Backend: Option C Resolution ──────────────────────────
    rect rgb(255, 230, 255)
    Note over FastAPI,PM: 4. Option C resolution in route handler
    FastAPI->>FastAPI: Parse ChatRequest<br/>tools_enabled defaults to True
    FastAPI->>PM: get_mode(request.mode_id)
    PM-->>FastAPI: PromptMode | None<br/>(includes tools_enabled_default)
    FastAPI->>FastAPI: use_tools = request.tools_enabled<br/>AND mode.tools_enabled_default
    end

    %% ── Backend: Service Layer ────────────────────────────────
    rect rgb(255, 255, 230)
    Note over FastAPI,Agent: 5. ChatService forwards use_tools
    FastAPI->>Svc: handle_turn(session_id, message,<br/>use_tools=True|False, ...)
    Svc->>Svc: Load history from SQLite
    Svc->>Svc: Generate turn_ids (UUID)
    Svc->>Agent: process_chat_turn(message, history,<br/>use_tools=True|False)
    end

    %% ── Backend: Agent Dispatch ───────────────────────────────
    rect rgb(230, 230, 255)
    Note over Agent,Provider: 6. Agent dispatches to active provider
    Agent->>Agent: get_provider(provider_name)
    Agent->>Provider: provider.process_chat_turn(<br/>message, history, use_tools=True|False)
    end

    %% ── Provider: use_tools=True (Agentic Loop) ──────────────
    alt use_tools = True
        rect rgb(220, 255, 220)
        Note over Provider,LLM: 7a. Agentic loop (tools enabled)
        Provider->>Provider: config.tools = [tool_declarations]
        Provider->>LLM: generate_content(model, contents,<br/>config WITH tools)
        loop Model returns function_call
            LLM-->>Provider: FunctionCall(name, args)
            Provider->>Provider: Dispatch tool via FUNCTION_MAP
            Provider->>Provider: Append tool_result to history
            Provider->>LLM: generate_content(updated contents)
        end
        LLM-->>Provider: Final text response
        Provider-->>Agent: (final_text, tool_logs)
        end
    end

    %% ── Provider: use_tools=False (Direct Call) ──────────────
    alt use_tools = False
        rect rgb(255, 220, 220)
        Note over Provider,LLM: 7b. Direct call (tools disabled)
        Provider->>Provider: config.tools = []  (empty)
        Provider->>LLM: Single generate_content(model,<br/>contents, config WITHOUT tools)
        LLM-->>Provider: Text response
        Provider-->>Agent: (final_text, [])  ← empty tool_logs
        end
    end

    %% ── Backend: Persist & Return ─────────────────────────────
    rect rgb(255, 255, 240)
    Note over Svc,FastAPI: 8. Persist and return
    Agent-->>Svc: (final_text, tool_logs)
    Svc->>Svc: Append assistant ui_message<br/>with tools=tool_logs
    Svc->>Svc: Dehydrate history with turn_ids
    Svc->>Svc: Save session to SQLite
    Svc->>Svc: log_turn() → prompt activity log
    Svc-->>FastAPI: (final_text, tool_logs)
    FastAPI-->>API: ChatResponse(text, tools_used)
    end

    %% ── Frontend: Render Response ─────────────────────────────
    rect rgb(240, 255, 255)
    Note over Store,User: 9. Render response in UI
    API-->>Store: ChatResponse
    Store->>Store: Push assistant message<br/>(tools=[] when use_tools was False)
    Store->>Composer: Reactive re-render
    Composer->>User: Shows assistant reply<br/>(no tool badges when tools=[])
    end
```

---

## Data Flow Summary

### Frontend → Backend

```mermaid
graph LR
    A["modes.json<br/>tools_enabled: false"] -->|loaded by| B[PromptManager]
    B -->|get_mode| C["PromptMode<br/>tools_enabled_default: false"]

    D["ChatComposer<br/>toggle ⚡/💬"] -->|toggleTools| E["chatStore<br/>toolsEnabled: boolean"]
    F["Mode pill click"] -->|setSelectedModeId| E

    E -->|sendMessage| G["ChatRequest<br/>tools_enabled?: boolean"]
    G -->|"false → always off<br/>undefined → defer to mode"| H["POST /api/chat"]
```

### Backend Resolution

```mermaid
graph TD
    A["request.tools_enabled<br/>(default: True)"] --> C{"AND"}
    B["mode.tools_enabled_default<br/>(from modes.json)"] --> C
    C -->|"True AND True"| D["use_tools = True<br/>Agentic loop"]
    C -->|"True AND False"| E["use_tools = False<br/>Direct call"]
    C -->|"False AND _"| E
```

### Provider Branching

```mermaid
graph TD
    A["use_tools flag"] --> B{use_tools?}
    B -->|True| C["tools=[tool_declarations]<br/>while True: agentic loop<br/>dispatch tool calls"]
    B -->|False| D["tools=[]<br/>single generate_content<br/>return (text, [])"]
    C --> E["(final_text, tool_logs)"]
    D --> F["(final_text, [])"]
```

---

## Key Files

| Layer           | File                                              | Role                                    |
| --------------- | ------------------------------------------------- | --------------------------------------- |
| Config          | `prompts/modes.json`                              | `tools_enabled` per mode (optional key) |
| Schema          | `src/schemas.py` → `ChatRequest`                  | `tools_enabled: bool = True`            |
| Prompt Manager  | `src/prompt_manager.py` → `PromptMode`            | `tools_enabled_default: bool = True`    |
| Route           | `src/main.py` → `chat()`                          | Option C resolution: `AND` logic        |
| Service         | `src/chat_service.py` → `handle_turn()`           | `use_tools` param forwarded             |
| Agent           | `src/agent.py` → `process_chat_turn()`            | `use_tools` param forwarded             |
| Provider (base) | `src/providers/base.py` → `LLMProvider`           | Protocol includes `use_tools`           |
| Gemini          | `src/providers/gemini.py`                         | `use_tools=False` → direct call branch  |
| Anthropic       | `src/providers/anthropic_provider.py`             | `use_tools=False` → direct call branch  |
| Frontend store  | `frontend/src/lib/stores/chat.svelte.ts`          | `toolsEnabled` state + toggle           |
| Frontend UI     | `frontend/src/lib/components/ChatComposer.svelte` | ⚡/💬 toggle button                     |
| Frontend API    | `frontend/src/lib/api.ts` → `ChatRequest`         | `tools_enabled?: boolean`               |

---

## Validation Checklist

- [x] `prompts/modes.json` supports optional `tools_enabled` key
- [x] `PromptMode.tools_enabled_default` defaults to `True` when absent
- [x] Non-bool `tools_enabled` in modes.json coerced to `True` (safe default)
- [x] `ChatRequest.tools_enabled` defaults to `True` in Pydantic schema
- [x] `main.py` resolves `use_tools = request.tools_enabled AND mode.tools_enabled_default`
- [x] `ChatService.handle_turn(use_tools=...)` forwards to agent
- [x] `agent.process_chat_turn(use_tools=...)` forwards to provider
- [x] `LLMProvider` protocol includes `use_tools: bool = True`
- [x] `GeminiProvider`: `use_tools=False` → empty tools config + single call
- [x] `AnthropicProvider`: `use_tools=False` → empty tools list + single call
- [x] Frontend `chatStore.toolsEnabled` syncs with mode default on switch
- [x] Frontend `sendMessage` sends `tools_enabled: false` only when off
- [x] 739/739 tests pass
