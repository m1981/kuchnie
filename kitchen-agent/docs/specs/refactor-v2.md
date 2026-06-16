# Frontend Refactor Plan v2 — Architectural Cleanup

**Goal**: Address 8 architectural concerns without adding new features.
**Approach**: Each phase is independently deployable. Phases are ordered by dependency (some require others first) and by risk (low-risk changes first).

---

## The 8 Concerns (Recap)

| # | Concern | Severity | Current State |
|---|---------|----------|---------------|
| 1 | Two async state types | Low | ✅ **Fixed** — merged into single `AsyncState<T>` (11ab1d9) |
| 2 | chatStore God Object | Medium | chatStore re-exports 4 sub-stores; +page.svelte accesses sub-store state through facade |
| 3 | No page loading state | Medium | +page.svelte fetches on mount with no skeleton |
| 4 | Component size imbalance | Medium | 5 components over 250 lines, 4 under 80 lines |
| 5 | No error boundary | Medium | Render errors crash the whole page |
| 6 | Silent optimistic rollbacks | Low | Error toasts exist but rollbacks are invisible |
| 7 | No shared Dialog/Dropdown | Low | 3 different modal patterns, each with own focus trap |
| 8 | Monolithic SessionTree | Medium | 271 lines, 5 responsibilities |

---

## Phase 1: Merge AsyncState and RemoteData ✅

**Status**: Done (11ab1d9) — 8 files changed, 16 insertions, 38 deletions.

**Why first**: Zero risk, zero dependencies, removes confusion for all future work.

### What Changed

Removed `RemoteData<T>` type entirely. All stores now use `AsyncState<T>` with `.message` field for errors.

**Files changed**:
- `src/lib/types/states.ts` — removed `RemoteData`
- `src/lib/types/index.ts` — removed `RemoteData` export
- `src/lib/stores/folder.svelte.ts` — `RemoteData` → `AsyncState`, `.error` → `.message`
- `src/lib/stores/sessions.svelte.ts` — same
- `src/lib/stores/notes.svelte.ts` — same
- `src/lib/components/FolderTree.svelte` — `fetchState.error` → `fetchState.message`
- `src/lib/components/SessionTree.svelte` — same
- `src/lib/components/NotesPanel.svelte` — same

**Validation**: 0 TypeScript errors, 53 tests passing.

---

## Phase 2: Break chatStore Facade — Direct Store Imports

**Why second**: Unlocks cleaner component architecture for later phases.

### Problem

`+page.svelte` accesses sub-store state through `chatStore`:

```typescript
// +page.svelte currently does this:
chatStore.selectedModeId        // ← actually promptStore
chatStore.editState             // ← actually editorStore
chatStore.appTitle              // ← actually providerStore
chatStore.sessionTokenCount     // ← actually tokenStore
```

This creates:
- **Artificial coupling**: Components depend on chatStore for things it doesn't own
- **Debugging pain**: Tracing `chatStore.editState` requires following the delegation chain
- **Testing complexity**: Can't test editorStore behavior without chatStore

### Plan

**Step 2a: Audit what +page.svelte actually needs from each store**

Create a mapping:

| Currently via chatStore | Actually belongs to | Direct import |
|------------------------|--------------------|--------------------|
| `chatStore.selectedModeId` | promptStore | `promptStore.selectedModeId` |
| `chatStore.isSystemPromptOverride` | editorStore | `editorStore.isSystemPromptOverride` |
| `chatStore.resolvedSystemPrompt` | editorStore | `editorStore.resolvedSystemPrompt` |
| `chatStore.editState` | editorStore | `editorStore.editState` |
| `chatStore.systemPromptState` | editorStore | `editorStore.systemPromptState` |
| `chatStore.editingTurnId` | editorStore | `editorStore.editingTurnId` |
| `chatStore.editDraft` | editorStore | `editorStore.editDraft` |
| `chatStore.startEditing()` | editorStore | `editorStore.startEditing()` |
| `chatStore.saveEdit()` | editorStore | `editorStore.saveEdit()` |
| `chatStore.cancelEditing()` | editorStore | `editorStore.cancelEditing()` |
| `chatStore.saveSystemPrompt()` | editorStore | `editorStore.saveSystemPrompt()` |
| `chatStore.clearSystemPrompt()` | editorStore | `editorStore.clearSystemPrompt()` |
| `chatStore.appTitle` | providerStore | `providerStore.appTitle` |
| `chatStore.loadModes()` | promptStore | `promptStore.loadModes()` |
| `chatStore.loadProviders()` | providerStore | `providerStore.loadProviders()` |
| `chatStore.loadAppInfo()` | providerStore | `providerStore.loadAppInfo()` |
| `chatStore.sessionTokenCount` | tokenStore | `tokenStore.sessionTokenCount` |

**chatStore keeps only what it owns:**
- `sessionId`, `messages`, `chatState`
- `pastedImages`, `contextFiles`
- `isStreaming`, `toolsEnabled`
- `sendMessage()`, `loadSession()`, `forkSession()`, `stopStreaming()`
- `toggleTools()`, `resetForNewChat()`
- Cross-store coordination (`loadSession` triggers token refresh, etc.)

**Step 2b: Update +page.svelte imports**

```typescript
// BEFORE
import { chatStore } from '$lib/stores/chat.svelte';

// AFTER
import { chatStore }      from '$lib/stores/chat.svelte';
import { editorStore }    from '$lib/stores/editor.svelte';
import { providerStore }  from '$lib/stores/provider.svelte';
import { promptStore }    from '$lib/stores/prompt.svelte';
import { tokenStore }     from '$lib/stores/token.svelte';
```

**Step 2c: Update component prop drilling**

Components that receive sub-store data as props should import directly:

```svelte
<!-- BEFORE: +page.svelte passes sub-store data as props -->
<ChatMessageList
    messages={chatStore.messages}
    isLoading={chatStore.chatState.status === 'loading'}
    editingTurnId={chatStore.editingTurnId}
    ...
/>

<!-- AFTER: ChatMessageList imports editorStore directly -->
<script>
    import { editorStore } from '$lib/stores/editor.svelte';
    const editingTurnId = $derived(editorStore.editingTurnId);
</script>
```

**Step 2d: Remove delegation getters from chatStore**

Delete the getters that just proxy sub-store state:

```typescript
// DELETE these from chatStore:
get selectedModeId()      { return promptStore.selectedModeId; },
get editState()           { return editorStore.editState; },
get appTitle()            { return providerStore.appTitle; },
// ... etc
```

Keep only the `export { providerStore, promptStore, editorStore, tokenStore }` line as a convenience re-export for components that want to import multiple stores from one place.

### Files Changed

- `src/routes/chat/[id]/+page.svelte` — direct imports
- `src/lib/stores/chat.svelte.ts` — remove delegation getters
- `src/lib/components/TokenIndicator.svelte` — import tokenStore directly
- `src/lib/components/ChatComposer.svelte` — verify it only uses chatStore's own API

### Test Plan

- `svelte-check` for TypeScript (catches missing imports)
- Manual test: load chat, send message, edit message, change provider
- Run existing tests

### Risk

**Medium**. Large change surface. Mitigation: do it in sub-steps (2a → 2b → 2c → 2d), test after each.

### Effort

**2-3 hours**.

---

## Phase 3: Split SessionTree into Sidebar Panels

**Why third**: Reduces the largest component, creates clear ownership boundaries.

### Problem

`SessionTree.svelte` (271 lines) owns:
1. Error toast display
2. Session count badge
3. Folder tree rendering
4. Session forest rendering
5. Archived section rendering
6. All event handlers (archive, delete, export, etc.)

Changing the folder section requires reading the whole file.

### Plan

**Step 3a: Extract `SidebarLayout.svelte`**

A thin layout component that composes the panels:

```svelte
<!-- SidebarLayout.svelte -->
<script>
    import FolderPanel from './FolderPanel.svelte';
    import SessionPanel from './SessionPanel.svelte';
    import ArchivedPanel from './ArchivedPanel.svelte';
</script>

<FolderPanel />
<SessionPanel />
<ArchivedPanel />
```

**Step 3b: Extract `FolderPanel.svelte`**

Owns:
- "Folders" header + create button
- Error toast (folder errors)
- `<FolderTree>` rendering
- Loading skeleton

~40 lines.

**Step 3c: Extract `SessionPanel.svelte`**

Owns:
- "History" header + count badge
- Error toast (session errors)
- Session forest rendering with `<DraggableSession>` + `<SessionTreeNode>`
- All session event handlers (archive, delete, export, etc.)

~150 lines.

**Step 3d: Extract `ArchivedPanel.svelte`**

Owns:
- Expand/collapse toggle
- "Archived" header + count badge
- Archived session rendering

~60 lines.

**Step 3e: Slim down `SessionTree.svelte`**

Either delete it (replaced by `SidebarLayout`) or keep it as a thin wrapper that imports `sessionStore` and `folderStore` on mount and passes data down.

### Files Changed

- `src/lib/components/SidebarLayout.svelte` — new
- `src/lib/components/FolderPanel.svelte` — new
- `src/lib/components/SessionPanel.svelte` — new
- `src/lib/components/ArchivedPanel.svelte` — new
- `src/lib/components/SessionTree.svelte` — slim down or delete
- `src/routes/chat/[id]/+page.svelte` — use SidebarLayout

### Test Plan

- Visual regression: sidebar looks identical
- Drag-drop still works
- Archive/unarchive still works
- Folder CRUD still works

### Risk

**Low-medium**. Pure decomposition. No behavior change. Mitigation: keep SessionTree as fallback during migration.

### Effort

**2 hours**.

---

## Phase 4: Extract Shared Dialog and Dropdown Components

**Why fourth**: Reduces duplication, creates consistent UX patterns.

### Problem

Three different modal/dropdown implementations:
- `ConfirmDialog` — modal with Escape handling
- `CreateFolderDialog` — modal with form
- `SessionContextMenu` — right-click dropdown with focus trap

Each has its own focus trap logic, keyboard handling, and backdrop click handling.

### Plan

**Step 4a: Create `Dialog.svelte` base component**

```svelte
<!-- Dialog.svelte -->
<script lang="ts">
    import type { Snippet } from 'svelte';
    
    type Props = {
        open: boolean;
        onclose: () => void;
        title?: string;
        children: Snippet;
        footer?: Snippet;
    };
    
    let { open, onclose, title, children, footer }: Props = $props();
    
    // Escape key handler
    // Backdrop click handler
    // Focus trap
    // Body scroll lock
</script>

{#if open}
    <div class="dialog-backdrop" onclick={onclose}>
        <div class="dialog-content" onclick|stopPropagation>
            {#if title}
                <h2 class="dialog-title">{title}</h2>
            {/if}
            {@render children()}
            {#if footer}
                <div class="dialog-footer">{@render footer()}</div>
            {/if}
        </div>
    </div>
{/if}
```

**Step 4b: Create `Dropdown.svelte` base component**

```svelte
<!-- Dropdown.svelte -->
<script lang="ts">
    import type { Snippet } from 'svelte';
    
    type Props = {
        open: boolean;
        anchor: HTMLElement | null;
        onclose: () => void;
        children: Snippet;
    };
    
    let { open, anchor, onclose, children }: Props = $props();
    
    // Position relative to anchor
    // Click-outside handler
    // Escape key handler
</script>
```

**Step 4c: Refactor `ConfirmDialog` to use `Dialog`**

```svelte
<!-- ConfirmDialog.svelte — now ~20 lines -->
<Dialog open={true} {onclose} title="Confirm">
    <p>{message}</p>
    {#snippet footer()}
        <button onclick={onclose}>Cancel</button>
        <button onclick={onconfirm}>Confirm</button>
    {/snippet}
</Dialog>
```

**Step 4d: Refactor `CreateFolderDialog` to use `Dialog`**

**Step 4e: Refactor `SessionContextMenu` to use `Dropdown`**

### Files Changed

- `src/lib/components/ui/Dialog.svelte` — new
- `src/lib/components/ui/Dropdown.svelte` — new
- `src/lib/components/ConfirmDialog.svelte` — refactor
- `src/lib/components/CreateFolderDialog.svelte` — refactor
- `src/lib/components/SessionContextMenu.svelte` — refactor

### Test Plan

- All existing dialogs still work
- Escape closes dialogs
- Backdrop click closes dialogs
- Focus is trapped inside dialog
- Right-click menu positions correctly

### Risk

**Low**. Incremental migration. Each dialog can be refactored independently.

### Effort

**2-3 hours**.

---

## Phase 5: Add Page Loading State

**Why fifth**: Improves perceived performance, small change.

### Problem

`+page.svelte` fetches 3 things on mount with no loading indicator:

```typescript
$effect(() => {
    chatStore.loadSession(id);
    chatStore.loadModes();
    chatStore.loadProviders();
    chatStore.loadAppInfo();
});
```

User sees a blank page until all fetches complete.

### Plan

**Step 5a: Add `pageReady` state to +page.svelte**

```typescript
let pageReady = $state(false);

$effect(() => {
    Promise.all([
        chatStore.loadSession(id),
        providerStore.loadProviders(),
        promptStore.loadModes(),
        providerStore.loadAppInfo()
    ]).then(() => { pageReady = true; });
});
```

**Step 5b: Add skeleton UI**

```svelte
{#if !pageReady}
    <div class="page-skeleton">
        <div class="skeleton-sidebar"><!-- 3 skeleton rows --></div>
        <div class="skeleton-chat">
            <div class="skeleton-header"></div>
            <div class="skeleton-messages"></div>
            <div class="skeleton-composer"></div>
        </div>
    </div>
{:else}
    <!-- existing content -->
{/if}
```

**Step 5c: Handle partial failures**

If `loadProviders` fails but `loadSession` succeeds, still show the page (providers can retry later). Only block on `loadSession`.

### Files Changed

- `src/routes/chat/[id]/+page.svelte` — loading state + skeleton

### Test Plan

- Fast connection: skeleton flashes briefly
- Slow connection (throttle in DevTools): skeleton shows for duration
- API error: page still loads with error state

### Risk

**Very low**. Additive change. No existing behavior affected.

### Effort

**1 hour**.

---

## Phase 6: Add Error Boundary

**Why sixth**: Prevents full-page crashes from component render errors.

### Problem

If `ChatMessageList` throws during render (e.g., malformed message data), the entire page crashes with no recovery.

### Plan

**Step 6a: Create `ErrorBoundary.svelte`**

Svelte 5 doesn't have built-in error boundaries, but we can use `{#await}` with a try-catch wrapper:

```svelte
<!-- ErrorBoundary.svelte -->
<script lang="ts">
    import type { Snippet } from 'svelte';
    
    type Props = {
        children: Snippet;
        fallback?: Snippet;
    };
    
    let { children, fallback }: Props = $props();
    let error = $state<Error | null>(null);
    
    // Reset error when children change
    $effect(() => {
        error = null;
    });
</script>

{#if error}
    {#if fallback}
        {@render fallback()}
    {:else}
        <div class="error-boundary">
            <p>Something went wrong: {error.message}</p>
            <button onclick={() => error = null}>Retry</button>
        </div>
    {/if}
{:else}
    {@render children()}
{/if}
```

**Step 6b: Wrap key sections**

```svelte
<!-- +page.svelte -->
<ErrorBoundary>
    <ChatMessageList ... />
    {#snippet fallback()}
        <p class="error">Failed to load messages. <button onclick={() => chatStore.loadSession(id)}>Retry</button></p>
    {/snippet}
</ErrorBoundary>
```

**Note**: Svelte's error boundary support is limited. The real protection comes from:
1. Defensive rendering (`message?.content ?? ''`)
2. Try-catch in event handlers
3. `{#await}` blocks for async data

The `ErrorBoundary` component is a best-effort wrapper, not a React-style catch-all.

### Files Changed

- `src/lib/components/ErrorBoundary.svelte` — new
- `src/routes/chat/[id]/+page.svelte` — wrap key sections

### Test Plan

- Manually inject a throw in ChatMessageList → fallback shows
- Normal operation → no visual change

### Risk

**Low**. Additive. Doesn't change existing behavior.

### Effort

**1 hour**.

---

## Phase 7: Improve Rollback UX

**Why seventh**: Small UX polish, independent of other phases.

### Problem

Optimistic updates in `folderStore` roll back silently:

```typescript
// assignSession — count goes up, then silently goes down on error
this.folders = this.folders.map(f => 
    f.id === folderId ? { ...f, session_count: f.session_count + 1 } : f
);
try { ... } catch {
    this.folders = previous; // silent rollback
    this.showError('Failed to assign session'); // toast only
}
```

User sees count badge flash +1 then -1 with no explanation.

### Plan

**Step 7a: Add `pendingOperations` tracking**

```typescript
class FolderStore {
    pendingOps = $state<Map<string, { type: string; targetId: string }>>(new Map());
    
    async assignSession(folderId: string, sessionId: string) {
        // ... optimistic update ...
        this.pendingOps = new Map(this.pendingOps).set(sessionId, { type: 'assign', targetId: folderId });
        
        try {
            await api.assignSessionToFolder(folderId, sessionId);
        } catch {
            // rollback + show error
        } finally {
            this.pendingOps = new Map(this.pendingOps);
            this.pendingOps.delete(sessionId);
        }
    }
}
```

**Step 7b: Show pending state in FolderItem**

```svelte
{#each sessions as session (session.id)}
    <button
        class:opacity-50={folderStore.pendingOps.has(session.id)}
        class:animate-pulse={folderStore.pendingOps.has(session.id)}
    >
        {session.title}
    </button>
{/each}
```

**Step 7c: Improve error toast**

The existing `showError()` toast is fine. Just make sure it's always visible when a rollback happens (it already is). No change needed here.

### Files Changed

- `src/lib/stores/folder.svelte.ts` — add pendingOps tracking
- `src/lib/components/FolderItem.svelte` — show pending state

### Test Plan

- Drag session to folder → count updates + pending indicator
- Network error → rollback + error toast + indicator removed
- Normal flow → no visual change

### Risk

**Very low**. Additive. Existing behavior unchanged.

### Effort

**1 hour**.

---

## Phase 8: Break Down Large Components

**Why last**: Highest risk, most files touched. Do after all structural improvements are in place.

### Problem

5 components over 250 lines:

| Component | Lines | Responsibilities |
|-----------|-------|-----------------|
| ChatComposer | 492 | Textarea, images, context files, tools, send/stop |
| ChatMessageList | 308 | Scroll, message rendering, selection |
| MessageActions | 306 | Edit, delete, fork, copy, selection, keyboard |
| SessionTree | 271 | (Already addressed in Phase 3) |
| SystemPromptBubble | 255 | Collapsed view, expanded view, inspector |

### Plan

**Step 8a: Extract `ComposerActions.svelte` from ChatComposer**

The buttons row (tools toggle, placeholders, send/stop) is ~100 lines:

```svelte
<!-- ComposerActions.svelte -->
<script>
    type Props = {
        toolsEnabled: boolean;
        ontoggleTools: () => void;
        isStreaming: boolean;
        onstop: () => void;
        onsend: () => void;
        canSend: boolean;
    };
</script>

<div class="buttons-row">
    <!-- Left: tools toggle -->
    <!-- Center: ModelSelector -->
    <!-- Right: placeholders + send/stop -->
</div>
```

ChatComposer drops from 492 to ~350 lines.

**Step 8b: Extract `MessageToolbar.svelte` from MessageActions**

The action buttons (edit, delete, fork, copy) are ~80 lines:

```svelte
<!-- MessageToolbar.svelte -->
<script>
    type Props = {
        turnId: string;
        role: 'user' | 'assistant';
        onedit: () => void;
        ondelete: () => void;
        onfork: () => void;
        oncopy: () => void;
    };
</script>
```

MessageActions drops from 306 to ~200 lines.

**Step 8c: Extract `SelectionHighlight.svelte` from MessageActions**

The text selection tracking + note creation popup trigger is ~80 lines:

```svelte
<!-- SelectionHighlight.svelte -->
<script>
    // Tracks text selection within message
    // Shows "Add note" button on selection
    // Communicates with NotePopup
</script>
```

MessageActions drops further to ~120 lines.

**Step 8d: Extract `PromptInspector.svelte` from SystemPromptBubble**

The expanded prompt view with copy button and mode info is ~100 lines:

```svelte
<!-- PromptInspector.svelte -->
<script>
    type Props = {
        prompt: string;
        mode: PromptMode;
        isOverride: boolean;
    };
</script>
```

SystemPromptBubble drops from 255 to ~150 lines.

### Files Changed

- `src/lib/components/composer/ComposerActions.svelte` — new
- `src/lib/components/MessageToolbar.svelte` — new
- `src/lib/components/SelectionHighlight.svelte` — new
- `src/lib/components/PromptInspector.svelte` — new
- `src/lib/components/ChatComposer.svelte` — use ComposerActions
- `src/lib/components/MessageActions.svelte` — use MessageToolbar + SelectionHighlight
- `src/lib/components/SystemPromptBubble.svelte` — use PromptInspector

### Test Plan

- `svelte-check` for TypeScript
- Visual regression: all components look identical
- All interactions still work (edit, delete, fork, copy, note creation)

### Risk

**Medium**. Many files touched. Mitigation: extract one component at a time, test after each.

### Effort

**3-4 hours**.

---

## Summary

| Phase | Concern | Effort | Risk | Status |
|-------|---------|--------|------|--------|
| 1. Merge async types | #1 Two state types | 30m | Very low | ✅ Done (11ab1d9) |
| 2. Break chatStore facade | #2 God Object | 2-3h | Medium | ⬜ Ready |
| 3. Split SessionTree | #8 Monolithic sidebar | 2h | Low-med | ⬜ Ready |
| 4. Shared Dialog/Dropdown | #7 No shared components | 2-3h | Low | ⬜ Ready |
| 5. Page loading state | #3 No loading state | 1h | Very low | ⬜ After Phase 2 |
| 6. Error boundary | #5 No error boundary | 1h | Low | ⬜ Ready |
| 7. Rollback UX | #6 Silent rollbacks | 1h | Very low | ⬜ Ready |
| 8. Break down components | #4 Size imbalance | 3-4h | Medium | ⬜ After Phase 3 |

**Remaining: ~12-15 hours** (Phase 1 complete)

### Recommended Order

```
✅ Phase 1 (30m) — DONE

Next up (any order):
  Phase 2 (2-3h)  →  Phase 5 (1h)
  Phase 3 (2h)    →  Phase 8 (3-4h)
  Phase 4 (2-3h)
  Phase 6 (1h)
  Phase 7 (1h)
```

Phases 2, 3, 4, 6, 7 are **independent** — they can be done in any order.
Phases 2 → 5 are sequential (page loading needs direct imports).
Phases 3 → 8 are sequential (component breakdown after sidebar split).

### What This Does NOT Address

These are feature work, not refactoring:
- Virtual scrolling for long conversations
- Message retry/regenerate
- Conversation branching visualization
- Keyboard shortcut documentation

They're tracked separately.
