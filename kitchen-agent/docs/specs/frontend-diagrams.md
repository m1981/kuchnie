# Kitchen Agent — Frontend Architecture Diagrams

Mermaid diagrams documenting the Svelte 5 frontend architecture.
Generated from `svelte-map` analysis, updated 2026-06-16.

---

## 1. Component Hierarchy

```mermaid
graph TB
    subgraph Routes["SvelteKit Routes"]
        Layout["+layout.svelte<br/>favicon, global head"]
        RootPage["+page.svelte<br/>redirect → /chat/{uuid}"]
        ChatPage["chat/[id]/+page.svelte<br/>402 lines — main orchestrator"]
    end

    subgraph ChatArea["Chat Area (left panel)"]
        ChatHeader["ChatHeader<br/>148 lines — title, mode badge"]
        ChatMessageList["ChatMessageList<br/>308 lines — scrollable messages"]
        ChatComposer["ChatComposer<br/>492 lines — input orchestrator"]
    end

    subgraph Sidebar["Sidebar (right panel)"]
        SessionTree["SessionTree<br/>271 lines — session forest + folders"]
        ContextSidebar["ContextSidebar<br/>188 lines — files + notes"]
    end

    subgraph ComposerSubs["Composer Sub-Components"]
        ModelSelector["ModelSelector<br/>118 lines — optgroup select"]
        TokenIndicator["TokenIndicator<br/>107 lines — token bar"]
    end

    subgraph MessageSubs["Message Sub-Components"]
        MessageActions["MessageActions<br/>306 lines — edit/delete/fork"]
        MessageEditor["MessageEditor<br/>94 lines — inline edit"]
        SystemPromptBubble["SystemPromptBubble<br/>255 lines — prompt display"]
        Markdown["Markdown<br/>49 lines — parsed markdown"]
    end

    subgraph SessionSubs["Session Sub-Components"]
        DraggableSession["DraggableSession<br/>54 lines — drag wrapper"]
        FolderTree["FolderTree<br/>127 lines — folder list + drop zones"]
        FolderItem["FolderItem<br/>210 lines — single folder + sessions"]
        SessionTreeNode["SessionTreeNode<br/>163 lines — recursive tree node"]
        SessionContextMenu["SessionContextMenu<br/>262 lines — right-click menu"]
        CreateFolderDialog["CreateFolderDialog<br/>161 lines — new folder modal"]
    end

    subgraph SidebarSubs["Sidebar Sub-Components"]
        NotesPanel["NotesPanel<br/>205 lines — notes list"]
        NotePopup["NotePopup<br/>136 lines — create note"]
        FileEditor["FileEditor<br/>116 lines — edit context file"]
    end

    subgraph Shared["Shared / Utility"]
        ConfirmDialog["ConfirmDialog<br/>81 lines — modal confirm"]
        ProviderPicker["ProviderPicker<br/>107 lines — provider select"]
    end

    %% Route hierarchy
    Layout --> RootPage
    Layout --> ChatPage

    %% Page composition
    ChatPage --> ChatHeader
    ChatPage --> ChatMessageList
    ChatPage --> ChatComposer
    ChatPage --> SessionTree
    ChatPage --> ContextSidebar
    ChatPage --> NotePopup

    %% Chat area composition
    ChatMessageList --> MessageActions
    ChatMessageList --> MessageEditor
    ChatMessageList --> SystemPromptBubble
    ChatMessageList --> Markdown
    ChatMessageList --> ConfirmDialog

    ChatComposer --> ModelSelector
    ChatComposer --> TokenIndicator

    %% Session tree composition
    SessionTree --> DraggableSession
    SessionTree --> FolderTree
    SessionTree --> SessionTreeNode
    FolderTree --> FolderItem
    FolderTree --> CreateFolderDialog
    SessionTreeNode --> SessionContextMenu

    %% Context sidebar composition
    ContextSidebar --> NotesPanel
    ContextSidebar --> FileEditor

    %% NotePopup is a portal (renders at page level)
    NotePopup -.->|"portal"| ChatPage

    style Routes fill:#e8f4f8,stroke:#2196F3
    style ChatArea fill:#e3f2fd,stroke:#1565C0
    style Sidebar fill:#fff3e0,stroke:#FF9800
    style ComposerSubs fill:#f3e5f5,stroke:#9C27B0
    style MessageSubs fill:#fce4ec,stroke:#E91E63
    style SessionSubs fill:#e8f5e9,stroke:#4CAF50
    style SidebarSubs fill:#fff8e1,stroke:#FFC107
    style Shared fill:#efebe9,stroke:#795548
```

---

## 2. Store Architecture

```mermaid
graph TB
    subgraph Facade["chatStore — Facade Pattern"]
        ChatCore["chat.svelte.ts<br/>536 lines<br/>closure-based factory"]
        ChatOwns["Owns:<br/>sessionId, messages<br/>chatState (AsyncState)<br/>pastedImages, contextFiles<br/>isStreaming, toolsEnabled"]
    end

    subgraph Delegated["Delegated Stores (chatStore re-exports)"]
        ProviderStore["providerStore<br/>113 lines — closure-based<br/>providers, selectedProvider/Model<br/>appTitle, appDescription"]
        PromptStore["promptStore<br/>87 lines — closure-based<br/>selectedModeId, modesState<br/>toolsEnabled, inspectorOpen"]
        EditorStore["editorStore<br/>235 lines — closure-based<br/>editingTurnId, editDraft<br/>sessionSystemPrompt"]
        TokenStore["tokenStore<br/>108 lines — closure-based<br/>sessionTokenCount, fallback<br/>contextFileTokenEstimate"]
    end

    subgraph Independent["Independent Stores"]
        FolderStore["folderStore<br/>309 lines — <b>class-based</b><br/>folders, folderSessions (SvelteMap)<br/>expandedFolders (SvelteSet)<br/>dragPayload, dropTarget"]
        SessionStore["sessionStore<br/>158 lines — closure-based<br/>tree (SessionNode[])<br/>flat (derived), activeId"]
        NotesStore["notesStore<br/>101 lines — closure-based<br/>bySession (Record&lt;string, Note[]&gt;)<br/>fetchStates"]
    end

    subgraph Patterns["Store Patterns"]
        Closure["Closure Factory<br/>function createXStore() {<br/>  let state = $state(...);<br/>  return { get x() { return state; } }<br/>}"]
        ClassBased["Class-Based<br/>class XStore {<br/>  state = $state(...);<br/>  get derived() { ... }<br/>}"]
        SvelteReactivity["Svelte Reactivity<br/>SvelteMap — reactive .get()/.set()<br/>SvelteSet — reactive .has()/.add()"]
    end

    ChatCore -->|"delegates getters"| ProviderStore
    ChatCore -->|"delegates"| PromptStore
    ChatCore -->|"delegates"| EditorStore
    ChatCore -->|"delegates"| TokenStore
    ChatCore -->|"refresh after mutations"| SessionStore

    FolderStore -.->|"uses"| ClassBased
    FolderStore -.->|"uses"| SvelteReactivity
    ChatCore -.->|"uses"| Closure
    ProviderStore -.->|"uses"| Closure

    style Facade fill:#e3f2fd,stroke:#1565C0
    style Delegated fill:#f3e5f5,stroke:#9C27B0
    style Independent fill:#e8f5e9,stroke:#4CAF50
    style Patterns fill:#fff8e1,stroke:#FFC107
```

---

## 3. Store → Component Consumer Map

```mermaid
graph LR
    subgraph Stores["Stores"]
        CS["chatStore"]
        PS["providerStore"]
        PR["promptStore"]
        ES["editorStore"]
        TS["tokenStore"]
        FS["folderStore"]
        SS["sessionStore"]
        NS["notesStore"]
    end

    subgraph Components["Components"]
        CP["ChatComposer"]
        TI["TokenIndicator"]
        ST["SessionTree"]
        FT["FolderTree"]
        FI["FolderItem"]
        DS["DraggableSession"]
        NP["NotePopup"]
        NPL["NotesPanel"]
        PG["+page.svelte"]
    end

    CS -->|"providers, selectedModel<br/>sendMessage, pastedImages"| CP
    CS -->|"sessionTokenCount"| TI
    TS -->|"estimateInputTokens()"| TI

    PS -->|"via chatStore facade"| CP

    SS -->|"tree, activeId"| ST
    FS -->|"sortedFolders"| FT
    FS -->|"getSessions, isExpanded"| FI
    FS -->|"startDrag, endDrag"| DS
    FS -->|"assignSession, refresh"| ST

    NS -->|"create, delete"| NP
    NS -->|"forSession(), load()"| NPL

    CS -->|"loadSession, all getters"| PG
    SS -->|"refresh, setActive"| PG

    style Stores fill:#e8f5e9,stroke:#4CAF50
    style Components fill:#e3f2fd,stroke:#1565C0
```

---

## 4. Chat Data Flow (Send → Stream → Display)

```mermaid
sequenceDiagram
    participant User
    participant Composer as ChatComposer
    participant Store as chatStore
    participant API as api.ts
    participant Backend as FastAPI

    User->>Composer: Types message + Enter
    Composer->>Composer: handleSend()
    Composer->>Store: sendMessage(text)

    Store->>Store: Optimistic: push user message to messages[]
    Store->>Store: chatState = { status: 'loading' }
    Store->>Store: isStreaming = true

    Store->>API: chatStream(ChatRequest)
    API->>Backend: POST /api/chat/stream (SSE)

    loop SSE Stream
        Backend-->>API: event: text_delta
        API-->>Store: yield { type: 'text_delta', content }
        Store->>Store: Append to last assistant message
        Store-->>Composer: Reactive update → re-render

        Backend-->>API: event: tool_call
        API-->>Store: yield { type: 'tool_call', name, args }
        Store->>Store: Add tool log to message

        Backend-->>API: event: tool_result
        API-->>Store: yield { type: 'tool_result', name, result }
        Store->>Store: Update tool log with result
    end

    Backend-->>API: event: done
    API-->>Store: yield { type: 'done', turn_ids, tokens }
    Store->>Store: Save turn_ids to messages
    Store->>Store: chatState = { status: 'idle' }
    Store->>Store: isStreaming = false
    Store->>Store: refreshSessionTokens()

    Note over Store: If first turn (messages.length ≤ 3):<br/>generateTitleInBackground()
```

---

## 5. Sidebar Architecture (Sessions + Folders + Drag-Drop)

```mermaid
graph TB
    subgraph SessionTree["SessionTree — Top-Level Container"]
        Header["Header: 'History' + count badge"]
        ErrorToast["Error toast (opError)"]
        FolderSection["Folder Section"]
        SessionSection["Session Section"]
        ArchivedSection["Archived Section"]
    end

    subgraph FolderSystem["Folder System"]
        FolderTree["FolderTree<br/>Creates drop zones per folder"]
        FolderItem["FolderItem<br/>Expandable folder with sessions"]
        CreateFolder["CreateFolderDialog"]
        DropZone["use:droppable<br/>accepts: session"]
    end

    subgraph SessionSystem["Session System"]
        DraggableSession["DraggableSession<br/>use:draggable"]
        SessionTreeNode["SessionTreeNode<br/>Recursive: renders children"]
        ContextMenu["SessionContextMenu<br/>Right-click actions"]
    end

    subgraph DragDrop["Drag & Drop Flow"]
        DragStart["Drag Start<br/>folderStore.startDrag(payload)"]
        DragOver["Drag Over<br/>folderStore.setDropTarget(target)"]
        Drop["Drop<br/>folderStore.assignSession(folderId, sessionId)"]
        DragEnd["Drag End<br/>folderStore.endDrag()"]
    end

    subgraph folderStore["folderStore (class-based)"]
        Folders["$state: folders[]"]
        Expanded["$state: expandedFolders (SvelteSet)"]
        Sessions["$state: folderSessions (SvelteMap)"]
        Drag["$state: dragPayload, dropTarget"]
        Methods["assignSession(), invalidateSessions()<br/>toggleExpand(), isExpanded()<br/>getSessions(), fetchSessions()"]
    end

    Header --> FolderSection
    FolderSection --> FolderTree
    FolderTree --> DropZone
    DropZone --> FolderItem
    FolderItem -->|"expanded"| Sessions
    FolderTree --> CreateFolder

    SessionSection --> DraggableSession
    DraggableSession --> SessionTreeNode
    SessionTreeNode --> ContextMenu
    SessionTreeNode -->|"children"| SessionTreeNode

    DraggableSession -->|"ondragstart"| DragStart
    DropZone -->|"ondragenter"| DragOver
    DropZone -->|"ondrop"| Drop
    DraggableSession -->|"ondragend"| DragEnd

    DragStart --> Drag
    DragOver --> Drag
    Drop --> Methods
    Drop --> Sessions
    DragEnd --> Drag

    SessionTree --> folderStore
    FolderTree --> folderStore
    FolderItem --> folderStore
    DraggableSession --> folderStore

    style SessionTree fill:#e3f2fd,stroke:#1565C0
    style FolderSystem fill:#e8f5e9,stroke:#4CAF50
    style SessionSystem fill:#fff3e0,stroke:#FF9800
    style DragDrop fill:#fce4ec,stroke:#E91E63
    style folderStore fill:#f3e5f5,stroke:#9C27B0
```

---

## 6. Svelte 5 Features Usage Map

```mermaid
graph TB
    subgraph Runes["Runes (Reactivity Primitives)"]
        State["$state()"]
        Derived["$derived()"]
        Props["$props()"]
        Bindable["$bindable()"]
        Effect["$effect()"]
    end

    subgraph Reactivity["Svelte Reactivity Collections"]
        SvelteMap["SvelteMap<br/>folderSessions, sessionsLoading,<br/>sessionsError"]
        SvelteSet["SvelteSet<br/>expandedFolders"]
    end

    subgraph Actions["Svelte Actions (use:)"]
        Draggable["use:draggable<br/>HTML5 drag start/end"]
        Droppable["use:droppable<br/>HTML5 drag enter/over/leave/drop"]
        PasteImage["use:pasteImage<br/>Ctrl+V image paste"]
        AutoResize["use:autoResize<br/>Textarea auto-grow"]
        FocusTrap["use:focusTrap<br/>Focus containment"]
    end

    subgraph Components["Svelte 5 Component Features"]
        Snippets["Snippets<br/>{#snippet name()}...{/snippet}<br/>{@render name()}"]
        Children["children prop<br/>Replaces <slot>"]
        TransitionBlock["{#key} blocks<br/>Transition triggers"]
    end

    subgraph Legacy["Svelte 4 Patterns Still Used"]
        IfEach["{#if} / {#each}<br/>Control flow"]
        BindThis["bind:this<br/>Element refs"]
        BindValue["bind:value<br/>Two-way binding"]
        OnMount["onMount()<br/>Lifecycle"]
        SvelteWindow["<svelte:window><br/>Global listeners"]
        SvelteHead["<svelte:head><br/>Meta tags"]
    end

    State -->|"folderStore, chatStore"| SvelteMap
    State -->|"folderStore"| SvelteSet
    Derived -->|"computed values"| Components
    Props -->|"every component"| Components
    Bindable -->|"ChatComposer.currentMessage"| Components

    Draggable -->|"DraggableSession"| SessionTree["SessionTree"]
    Droppable -->|"FolderTree drop zones"| FolderTree["FolderTree"]
    PasteImage -->|"ChatComposer"| Composer["ChatComposer"]
    AutoResize -->|"ChatComposer textarea"| Composer
    FocusTrap -->|"SessionContextMenu, NotePopup"| Modals["Modals"]

    Snippets -->|"FolderTree, SessionTree"| Layout["Layout"]
    Children -->|"FolderTree"| Layout

    style Runes fill:#e3f2fd,stroke:#1565C0
    style Reactivity fill:#f3e5f5,stroke:#9C27B0
    style Actions fill:#e8f5e9,stroke:#4CAF50
    style Components fill:#fff8e1,stroke:#FFC107
    style Legacy fill:#efebe9,stroke:#795548
```

---

## 7. Route Structure & Navigation

```mermaid
graph TB
    subgraph Routes["SvelteKit File-Based Routing"]
        Root["/<br/>+page.svelte<br/>Redirects to /chat/{uuid}"]
        Chat["/chat/[id]/<br/>+page.svelte<br/>URL-driven session"]
        Layout["+layout.svelte<br/>Global: favicon, head"]
    end

    subgraph ChatPage["/chat/[id] Internal Structure"]
        LeftPanel["Left Panel (flex-1)"]
        RightPanel["Right Panel (sidebar)"]
    end

    subgraph LeftContent["Left Panel Content"]
        Header["ChatHeader"]
        Messages["ChatMessageList"]
        Composer["ChatComposer"]
    end

    subgraph RightContent["Right Panel Content"]
        SessionTree["SessionTree"]
        ContextSidebar["ContextSidebar"]
    end

    subgraph Navigation["Navigation Patterns"]
        Goto["goto(/chat/{uuid})"]
        BeforeNav["beforeNavigate<br/>cancel() during streaming"]
        PageStore["$page.params.id<br/>Reactive URL param"]
    end

    Layout --> Root
    Layout --> Chat

    Root -->|"goto()"| Chat

    Chat --> LeftPanel
    Chat --> RightPanel

    LeftPanel --> Header
    LeftPanel --> Messages
    LeftPanel --> Composer

    RightPanel --> SessionTree
    RightPanel --> ContextSidebar

    SessionTree -->|"click session"| Goto
    Root -->|"new UUID"| Goto
    Chat -->|"streaming"| BeforeNav
    Chat -->|"params.id changes"| PageStore
    PageStore -->|"loadSession()"| ChatPage

    style Routes fill:#e8f4f8,stroke:#2196F3
    style ChatPage fill:#e3f2fd,stroke:#1565C0
    style LeftContent fill:#f3e5f5,stroke:#9C27B0
    style RightContent fill:#fff3e0,stroke:#FF9800
    style Navigation fill:#fce4ec,stroke:#E91E63
```

---

## 8. Component Responsibility Matrix

```mermaid
graph LR
    subgraph Orchestration["Page-Level Orchestrators"]
        ChatPage["+page.svelte<br/>━━━━━━━━━━━━━━<br/>• Mount + load session<br/>• Sidebar resize<br/>• Keyboard shortcuts<br/>• Navigation guards<br/>• Note popup state"]
        SessionTree["SessionTree<br/>━━━━━━━━━━━━━━<br/>• Fetch sessions on mount<br/>• Render folder tree<br/>• Render session forest<br/>• Drag-drop coordination<br/>• Archive/delete handlers"]
    end

    subgraph ChatComponents["Chat Components"]
        ChatHeader["ChatHeader<br/>━━━━━━━━━━━━━━<br/>• Title display + edit<br/>• Mode badge<br/>• Provider info"]
        ChatMessageList["ChatMessageList<br/>━━━━━━━━━━━━━━<br/>• Scroll management<br/>• Auto-scroll on new msg<br/>• Message rendering<br/>• Selection tracking"]
        ChatComposer["ChatComposer<br/>━━━━━━━━━━━━━━<br/>• Textarea + auto-resize<br/>• Image paste handling<br/>• Context files strip<br/>• Tools toggle<br/>• Send/stop button"]
        ModelSelector["ModelSelector<br/>━━━━━━━━━━━━━━<br/>• Optgroup select<br/>• Provider grouping<br/>• Model validation"]
    end

    subgraph MessageComponents["Message Components"]
        MessageActions["MessageActions<br/>━━━━━━━━━━━━━━<br/>• Edit button<br/>• Delete button<br/>• Fork button<br/>• Copy button<br/>• Selection highlight"]
        MessageEditor["MessageEditor<br/>━━━━━━━━━━━━━━<br/>• Inline textarea<br/>• Save/cancel<br/>• Auto-resize"]
        SystemPromptBubble["SystemPromptBubble<br/>━━━━━━━━━━━━━━<br/>• Collapsed preview<br/>• Expanded content<br/>• Prompt inspector"]
    end

    subgraph SidebarComponents["Sidebar Components"]
        FolderTree["FolderTree<br/>━━━━━━━━━━━━━━<br/>• Drop zones<br/>• Create button<br/>• Error toast"]
        FolderItem["FolderItem<br/>━━━━━━━━━━━━━━<br/>• Expand/collapse<br/>• Session list<br/>• Context menu<br/>• Color picker"]
        SessionTreeNode["SessionTreeNode<br/>━━━━━━━━━━━━━━<br/>• Recursive rendering<br/>• Active highlight<br/>• Archive indicator<br/>• Depth indentation"]
    end

    subgraph UtilityComponents["Utility Components"]
        TokenIndicator["TokenIndicator<br/>━━━━━━━━━━━━━━<br/>• Progress bar<br/>• Session tokens<br/>• Input estimate<br/>• Context %"]
        NotesPanel["NotesPanel<br/>━━━━━━━━━━━━━━<br/>• Notes list<br/>• Create/delete<br/>• Source role badge"]
        Markdown["Markdown<br/>━━━━━━━━━━━━━━<br/>• Parse markdown<br/>• Render HTML<br/>• tick() updates"]
    end

    style Orchestration fill:#e3f2fd,stroke:#1565C0
    style ChatComponents fill:#f3e5f5,stroke:#9C27B0
    style MessageComponents fill:#fce4ec,stroke:#E91E63
    style SidebarComponents fill:#e8f5e9,stroke:#4CAF50
    style UtilityComponents fill:#fff8e1,stroke:#FFC107
```

---

## 9. Hotspot Analysis (Import Frequency)

```mermaid
graph TB
    subgraph Hotspots["Most Imported Modules"]
        FS["folderStore — 4 importers<br/>DraggableSession, FolderItem,<br/>FolderTree, SessionTree"]
        API["api.ts — 4 importers<br/>SessionTree, ContextSidebar,<br/>FileEditor, +page"]
        CS["chatStore — 3 importers<br/>ChatComposer, TokenIndicator,<br/>+page"]
        PI["ProviderInfo — 3 importers<br/>ChatComposer, ModelSelector,<br/>ProviderPicker"]
        NOTE["Note type — 3 importers<br/>ContextSidebar, NotePopup,<br/>NotesPanel"]
    end

    subgraph Risk["Coupling Risk Assessment"]
        LowRisk["Low Risk<br/>Leaf components with<br/>no dependents"]
        MedRisk["Medium Risk<br/>Used by 2-3 siblings"]
        HighRisk["High Risk<br/>Used by many components<br/>or is a type dependency"]
    end

    FS -->|"High"| HighRisk
    API -->|"High"| HighRisk
    CS -->|"Medium"| MedRisk
    PI -->|"Low"| LowRisk
    NOTE -->|"Low"| LowRisk

    subgraph Recommendations["Recommendations"]
        R1["folderStore: Keep stable API<br/>— most imported store"]
        R2["api.ts: Consider typed wrappers<br/>— reduces import surface"]
        R3["chatStore: Facade pattern works<br/>— delegation is clean"]
    end

    style Hotspots fill:#e3f2fd,stroke:#1565C0
    style Risk fill:#fce4ec,stroke:#E91E63
    style Recommendations fill:#e8f5e9,stroke:#4CAF50
```

---

## 10. File Size Distribution

```mermaid
xychart-beta
    title "Component Line Counts"
    x-axis ["Composer", "MsgList", "MsgActions", "SessionTree", "SysPrompt", "FolderItem", "SessionCtx", "CtxSidebar", "NotesPanel", "FolderTree", "ChatHeader", "NotePopup", "FileEditor", "ProvPicker", "TokenInd", "ModelSel", "MsgEditor", "Confirm", "DragSess", "Markdown"]
    y-axis "Lines" 0 --> 550
    bar [492, 308, 306, 271, 255, 210, 262, 188, 205, 127, 148, 136, 116, 107, 107, 118, 94, 81, 54, 49]
```

```mermaid
xychart-beta
    title "Store Line Counts"
    x-axis ["chatStore", "folderStore", "editorStore", "sessionStore", "providerStore", "tokenStore", "notesStore", "promptStore"]
    y-axis "Lines" 0 --> 600
    bar [536, 309, 235, 158, 113, 108, 101, 87]
```

---

## 11. Shared Types Architecture

```mermaid
graph TB
    subgraph Types["$lib/types/"]
        Index["index.ts<br/>Re-exports all types"]
        States["states.ts<br/>AsyncState, RemoteData"]
        TypesOwn["Owns:<br/>PastedImage, NotePopupState<br/>DragPayload, DropTarget<br/>FolderSession"]
    end

    subgraph AsyncTypes["Async State Machines"]
        AsyncState["AsyncState&lt;T&gt;<br/>{ status: 'idle' }<br/>{ status: 'loading' }<br/>{ status: 'error', message }<br/>{ status: 'success', data }"]
        RemoteData["RemoteData&lt;T&gt;<br/>{ status: 'idle' }<br/>{ status: 'loading' }<br/>{ status: 'error', error }<br/>{ status: 'success', data }"]
    end

    subgraph DragTypes["Drag & Drop Types"]
        DragPayload["DragPayload<br/>{ type, id, title }"]
        DropTarget["DropTarget<br/>{ type, id }"]
    end

    subgraph Consumers["Store Consumers"]
        ChatStore["chatStore → AsyncState"]
        EditorStore["editorStore → AsyncState"]
        PromptStore["promptStore → AsyncState"]
        FolderStore["folderStore → RemoteData"]
        SessionStore["sessionStore → RemoteData"]
        NotesStore["notesStore → RemoteData"]
        DragActions["dragdrop.ts → DragPayload, DropTarget"]
    end

    Index --> States
    Index --> TypesOwn
    States --> AsyncState
    States --> RemoteData
    TypesOwn --> DragPayload
    TypesOwn --> DropTarget

    AsyncState --> ChatStore
    AsyncState --> EditorStore
    AsyncState --> PromptStore
    RemoteData --> FolderStore
    RemoteData --> SessionStore
    RemoteData --> NotesStore
    DragPayload --> DragActions
    DropTarget --> DragActions

    style Types fill:#e8f4f8,stroke:#2196F3
    style AsyncTypes fill:#f3e5f5,stroke:#9C27B0
    style DragTypes fill:#e8f5e9,stroke:#4CAF50
    style Consumers fill:#fff3e0,stroke:#FF9800
```

---

## Diagram Maintenance

| Change | Diagrams to Update |
|--------|-------------------|
| New component | 1 (Hierarchy), 8 (Responsibility), 10 (Size) |
| New store | 2 (Architecture), 3 (Consumer Map), 10 (Size) |
| New route | 7 (Routes) |
| New action (use:) | 6 (Svelte 5 Features) |
| New type | 11 (Shared Types) |
| Store refactor | 2 (Architecture), 3 (Consumer Map), 9 (Hotspots) |
| Component refactor | 1 (Hierarchy), 8 (Responsibility), 10 (Size) |
| Drag-drop changes | 5 (Sidebar Architecture) |
| Chat flow changes | 4 (Chat Data Flow) |

### Last Updated

| Date | Change | Diagrams |
|------|--------|----------|
| 2026-06-16 | Initial creation from svelte-map analysis | All (new) |
