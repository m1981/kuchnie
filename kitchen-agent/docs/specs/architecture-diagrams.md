# Kitchen Agent — Architecture Diagrams

Mermaid diagrams documenting the system architecture. Render in GitHub,
GitLab, Obsidian, or any Mermaid-compatible Markdown viewer.

---

## 1. High-Level Architecture Overview

```mermaid
graph TB
    subgraph Frontend["Frontend (Svelte 5)"]
        Page["+page.svelte"]
        Stores["Stores (runes)"]
        Components["Components"]
        API["api.ts (fetch client)"]
    end

    subgraph Backend["Backend (FastAPI)"]
        subgraph API_Layer["API Layer"]
            ChatRoute["api/chat.py"]
            SessionRoute["api/sessions.py"]
            ProviderRoute["api/providers.py"]
            NoteRoute["api/notes.py"]
            FileRoute["api/files.py"]
            PromptRoute["api/prompts.py"]
        end

        subgraph Service_Layer["Service Layer"]
            ChatSvc["ChatService"]
            MsgEditor["MessageEditService"]
            ExportSvc["ExportService"]
        end

        subgraph Agent_Layer["Agent Layer"]
            Orchestrator["TurnOrchestrator"]
            Context["ContextAssembler"]
            ToolExec["ToolExecutor"]
        end

        subgraph Provider_Layer["Provider Layer"]
            LLMProvider["LLMProvider (Protocol)"]
            Gemini["GeminiProvider"]
            Anthropic["AnthropicProvider"]
            Mimo["MimoProvider"]
            Normalizer["ResponseNormalizer"]
        end

        subgraph Content_Layer["Content Layer"]
            NoteMgr["NoteManager"]
            FileMgr["FileManager"]
            SearchCoord["SearchCoordinator"]
        end

        subgraph Data_Layer["Data Layer"]
            SessionRepo["SessionRepository"]
            NoteRepo["NoteRepository"]
            SQLite["SQLite"]
        end

        DI["dependencies.py"]
        Config["config.py / Settings"]
        Schemas["schemas.py (Pydantic)"]
        Prompts["PromptManager"]
    end

    Page --> Stores
    Stores --> API
    Components --> Stores
    API -->|HTTP/SSE| ChatRoute
    API -->|HTTP| SessionRoute
    API -->|HTTP| ProviderRoute

    ChatRoute --> ChatSvc
    SessionRoute --> MsgEditor
    SessionRoute --> ExportSvc

    ChatSvc --> Orchestrator
    Orchestrator --> Context
    Orchestrator --> ToolExec
    Orchestrator --> LLMProvider
    Orchestrator --> Normalizer

    LLMProvider -.-> Gemini
    LLMProvider -.-> Anthropic
    LLMProvider -.-> Mimo

    Context --> Prompts
    Context --> NoteMgr
    Context --> FileMgr

    ChatSvc --> SessionRepo
    MsgEditor --> SessionRepo
    ExportSvc --> SessionRepo
    NoteMgr --> NoteRepo
    SessionRepo --> SQLite
    NoteRepo --> SQLite

    DI --> ChatSvc
    DI --> Orchestrator
    DI --> LLMProvider

    style Frontend fill:#e8f4f8,stroke:#2196F3
    style API_Layer fill:#fff3e0,stroke:#FF9800
    style Service_Layer fill:#e8f5e9,stroke:#4CAF50
    style Agent_Layer fill:#fce4ec,stroke:#E91E63
    style Provider_Layer fill:#f3e5f5,stroke:#9C27B0
    style Content_Layer fill:#fff8e1,stroke:#FFC107
    style Data_Layer fill:#efebe9,stroke:#795548
```

---

## 2. Provider System

```mermaid
classDiagram
    class LLMProvider {
        <<Protocol>>
        +complete(context: AssembledContext) Any
        +complete_with_tools(context, tool_calls, tool_results) Any
        +stream(context: AssembledContext) Iterator
        +stream_with_tools(context, tool_calls, tool_results) Iterator
    }

    class GeminiProvider {
        -_model: str
        -_client: genai.Client
        -_config: GeminiConfig
        -_normalizer: ResponseNormalizer
        +complete(context) Any
        +stream(context) Iterator
    }

    class AnthropicProvider {
        -_model: str
        -_client: Anthropic
        -_config: AnthropicConfig
        +complete(context) Any
        +stream(context) Iterator
    }

    class MimoProvider {
        -_model: str
        -_client: OpenAI
        -_config: MimoConfig
        +complete(context) Any
        +stream(context) Iterator
    }

    class GeminiConfig {
        <<frozen dataclass>>
        +model: str = "gemini-3.1-pro-preview"
        +temperature: float = 0.2
    }

    class AnthropicConfig {
        <<frozen dataclass>>
        +api_key: str | None
        +model: str = "claude-sonnet-4-6"
        +temperature: float = 0.2
        +max_tokens: int = 8096
    }

    class MimoConfig {
        <<frozen dataclass>>
        +api_key: str | None
        +base_url: str
        +model: str = "mimo-v2.5-pro"
        +temperature: float = 0.2
        +max_tokens: int = 8096
    }

    class ResponseNormalizer {
        +normalize(raw, provider) NormalizedResponse
        +normalize_chunk(chunk, provider) str
    }

    class NormalizedResponse {
        <<frozen dataclass>>
        +text: str
        +has_tool_calls: bool
        +tool_calls: list~ToolCall~
        +usage: dict
        +raw: Any
    }

    class get_provider {
        <<function>>
        +get_provider(provider_name, model_override) LLMProvider
    }

    GeminiProvider ..|> LLMProvider
    AnthropicProvider ..|> LLMProvider
    MimoProvider ..|> LLMProvider

    GeminiProvider --> GeminiConfig
    AnthropicProvider --> AnthropicConfig
    MimoProvider --> MimoConfig

    GeminiProvider --> ResponseNormalizer
    AnthropicProvider --> ResponseNormalizer
    ResponseNormalizer --> NormalizedResponse

    get_provider --> GeminiProvider : creates
    get_provider --> AnthropicProvider : creates
    get_provider --> MimoProvider : creates
```

---

## 3. Agent Layer — Turn Lifecycle

```mermaid
sequenceDiagram
    participant CS as ChatService
    participant TO as TurnOrchestrator
    participant CA as ContextAssembler
    participant LLM as LLMProvider
    participant NR as ResponseNormalizer
    participant TE as ToolExecutor
    participant SR as SessionRepository

    CS->>SR: load_session(session_id)
    SR-->>CS: api_history, ui_history, system_prompt

    CS->>TO: run(session, turn_input)

    TO->>CA: assemble(session, mode, user_message)
    CA-->>TO: AssembledContext

    TO->>LLM: complete(context) or stream(context)
    LLM-->>TO: raw response

    TO->>NR: normalize(raw, provider)
    NR-->>TO: NormalizedResponse

    alt has_tool_calls
        loop Tool Loop (max iterations)
            TO->>TE: execute_all(tool_calls)
            TE-->>TO: tool_results
            TO->>LLM: complete_with_tools(context, tool_calls, tool_results)
            LLM-->>TO: raw response
            TO->>NR: normalize(raw, provider)
            NR-->>TO: NormalizedResponse
        end
    end

    TO-->>CS: TurnOutput

    CS->>SR: save_session(session_id, title, api_history, ui_history)
```

---

## 4. Chat Request Data Flow

```mermaid
flowchart LR
    subgraph Client["Frontend"]
        Composer["ChatComposer"]
        Store["chatStore"]
        SSE["SSE Parser"]
    end

    subgraph Server["Backend"]
        Route["POST /api/chat/stream"]
        Service["ChatService.stream_turn()"]
        Orchestrator["TurnOrchestrator.stream()"]
        Provider["LLMProvider.stream()"]
        Tools["ToolExecutor"]
        Repo["SessionRepository"]
    end

    Composer -->|"user message"| Store
    Store -->|"ChatRequest (SSE)"| Route
    Route --> Service

    Service -->|"1. Load session"| Repo
    Repo -->|"api_history, ui_history"| Service

    Service -->|"2. Execute turn"| Orchestrator
    Orchestrator -->|"AssembledContext"| Provider
    Provider -->|"text_delta"| Orchestrator
    Provider -->|"tool_call"| Orchestrator
    Orchestrator -->|"execute"| Tools
    Tools -->|"tool_result"| Orchestrator
    Orchestrator -->|"done event"| Service

    Service -->|"3. Persist"| Repo
    Service -->|"SSE events"| Route
    Route -->|"text_delta, tool_call, done"| SSE
    SSE -->|"update messages[]"| Store
```

---

## 5. Frontend Store Topology

```mermaid
graph TB
    subgraph Stores["Svelte 5 Rune Stores — chatStore split into 5 focused stores"]
        ChatStore["chatStore (facade)<br/><i>chat.svelte.ts</i><br/>470 lines — session, messaging"]
        ProviderStore["providerStore<br/><i>provider.svelte.ts</i><br/>120 lines — provider/model, app info"]
        PromptStore["promptStore<br/><i>prompt.svelte.ts</i><br/>130 lines — modes, tools, inspector"]
        EditorStore["editorStore<br/><i>editor.svelte.ts</i><br/>240 lines — message & prompt editing"]
        TokenStore["tokenStore<br/><i>token.svelte.ts</i><br/>110 lines — token counting"]
        SessionStore["sessionStore<br/><i>sessions.svelte.ts</i><br/>158 lines"]
        NotesStore["notesStore<br/><i>notes.svelte.ts</i><br/>106 lines"]
    end

    subgraph ChatState["chatStore owns (core only)"]
        CS_Session["sessionId, messages"]
        CS_Async["chatState (AsyncState)"]
        CS_Images["pastedImages"]
        CS_Context["contextFiles"]
    end

    subgraph ProviderState["providerStore owns"]
        PS_Providers["providers (catalog)"]
        PS_Selected["selectedProvider, selectedModel"]
        PS_App["appTitle, appDescription"]
    end

    subgraph PromptState["promptStore owns"]
        PR_Mode["selectedModeId, modesState"]
        PR_Tools["toolsEnabled"]
        PR_Inspector["promptDetail*, inspectorOpen"]
    end

    subgraph EditorState["editorStore owns"]
        ES_Edit["editingTurnId, editDraft, editState"]
        ES_System["sessionSystemPrompt (loaded on session switch)"]
    end

    subgraph TokenState["tokenStore owns"]
        TS_Count["sessionTokenCount, fallback"]
        TS_Cache["contextFileTokenEstimate, systemPromptText"]
    end

    subgraph SessionState["sessionStore owns"]
        SS_Tree["tree (SessionNode[])"]
        SS_Flat["flat (derived)"]
        SS_Active["activeId"]
    end

    subgraph NotesState["notesStore owns"]
        NS_BySession["bySession (Record&lt;string, Note[]&gt;)"]
        NS_Fetch["fetchStates"]
    end

    subgraph Consumers["Component Consumers"]
        Page["+page.svelte"]
        ChatComposer["ChatComposer"]
        TokenIndicator["TokenIndicator"]
        SessionTree["SessionTree"]
        NotePopup["NotePopup"]
        NotesPanel["NotesPanel"]
    end

    %% Facade pattern — consumers import chatStore, it delegates
    ChatStore -->|"delegates"| ProviderStore
    ChatStore -->|"delegates"| PromptStore
    ChatStore -->|"delegates"| EditorStore
    ChatStore -->|"delegates"| TokenStore
    ChatStore -->|"refresh after mutations"| SessionStore

    %% Consumer reads
    Page -->|"reads all getters"| ChatStore
    Page -->|"loadSession, startNewChat"| ChatStore
    Page -->|"refresh, setActive"| SessionStore

    ChatComposer -->|"providers, selectedProvider"| ChatStore
    ChatComposer -->|"sendMessage, addPastedImage"| ChatStore

    TokenIndicator -->|"sessionTokenCount, estimateInputTokensFor()"| ChatStore

    SessionTree -->|"tree, activeId"| SessionStore

    NotePopup -->|"create, delete"| NotesStore
    NotesPanel -->|"forSession(), load()"| NotesStore

    style ChatStore fill:#e3f2fd,stroke:#1565C0
    style ProviderStore fill:#f3e5f5,stroke:#9C27B0
    style PromptStore fill:#fce4ec,stroke:#E91E63
    style EditorStore fill:#fff8e1,stroke:#FFC107
    style TokenStore fill:#e8f5e9,stroke:#2E7D32
    style SessionStore fill:#e8f5e9,stroke:#2E7D32
    style NotesStore fill:#fff3e0,stroke:#E65100
```

---

## 6. Dependency Injection Graph

```mermaid
graph TD
    subgraph Singletons["@lru_cache — Process Lifetime"]
        Settings["get_settings()"]
        DB["get_db_connection()"]
        ToolRegistry["get_tool_registry()"]
        PromptMgr["get_prompt_manager()"]
        Normalizer["get_response_normalizer()"]
        TokenCounter["get_token_counter()"]
        SearchCoord["get_search_coordinator()"]
        NoteMgr["get_note_manager()"]
        FileMgr["get_file_manager()"]
        ContextBudget["get_context_budget()"]
        ContextAssembler["get_context_assembler()"]
        ToolExec["get_tool_executor()"]
        Orchestrator["get_turn_orchestrator()"]
    end

    subgraph RequestScoped["Request Lifetime"]
        SessionRepo["get_session_repo()"]
        NoteRepo["get_note_repo()"]
        ChatSvc["get_chat_service()"]
        MsgEditor["get_message_editor()"]
        ExportSvc["get_export_service()"]
    end

    Settings --> DB
    Settings --> ContextBudget
    Settings --> Orchestrator
    DB --> SessionRepo
    DB --> NoteRepo
    SearchCoord --> ToolRegistry
    PromptMgr --> ContextAssembler
    TokenCounter --> ContextAssembler
    NoteMgr --> ContextAssembler
    FileMgr --> ContextAssembler
    ContextBudget --> ContextAssembler
    ContextAssembler --> Orchestrator
    ToolExec --> Orchestrator
    Normalizer --> Orchestrator
    SessionRepo --> ChatSvc
    Orchestrator --> ChatSvc
    SessionRepo --> MsgEditor
    SessionRepo --> ExportSvc

    style Singletons fill:#e8f5e9,stroke:#2E7D32
    style RequestScoped fill:#fff3e0,stroke:#E65100
```

---

## Diagram Maintenance

When the architecture changes:

1. **Adding a new provider** → Update Diagram 2 (Provider System)
2. **Adding a new API endpoint** → Update Diagram 1 (High-Level) and Diagram 4 (Data Flow)
3. **Changing turn orchestration** → Update Diagram 3 (Agent Layer)
4. **Adding a new store** → Update Diagram 5 (Store Topology). chatStore is now a facade; sub-stores are providerStore, promptStore, editorStore, tokenStore
5. **Adding a new DI dependency** → Update Diagram 6 (DI Graph)
