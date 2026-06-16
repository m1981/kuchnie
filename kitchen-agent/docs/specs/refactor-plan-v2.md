# Frontend Refactor Plan v2

## Problem Statement

1. **Critical Bug**: Drag & drop sessions onto expanded folders don't update the session list (requires page reload)
2. **Architecture**: Closure-based `folderStore` with getter indirection breaks Svelte 5 reactivity chains
3. **Code Smell**: `FolderItem` owns session state locally via `$effect` — split state ownership
4. **Anti-pattern**: `$effect` used for data fetching in `FolderItem` (race conditions, hard to test)
5. **Size**: `ChatComposer` is 589 lines — too many responsibilities

---

## Phase 1: Class-Based FolderStore with Co-Located Session State

### Goal

Fix drag & drop bug by consolidating all folder-related state into a single class-based store.

### Changes

#### `frontend/src/lib/stores/folder.svelte.ts`

- Convert from closure-based factory to class-based store
- Move session cache (`sessions[]`, `sessionsLoading`, `sessionsError`) from `FolderItem` into store
- Move `expandedFolders` from `FolderTree` into store
- Replace `sessionsVersion` counter with direct cache invalidation
- Add `getSessions(folderId)` with lazy-fetch pattern
- Add `invalidateSessions(folderId)` for cache busting

#### `frontend/src/lib/components/FolderItem.svelte`

- Remove local `sessions`, `sessionsLoading`, `sessionsError` state
- Remove `$effect` for data fetching
- Use `$derived` to read from `folderStore.getSessions()`, `folderStore.sessionsLoading`, etc.
- Remove `isExpanded` and `ontoggle` props — read from store directly

#### `frontend/src/lib/components/FolderTree.svelte`

- Remove local `expandedFolders` SvelteSet
- Remove local `toggleExpand()` function
- Use `folderStore.isExpanded()` and `folderStore.toggleExpand()`

### Test Plan

- Store unit tests: assignSession optimistic + rollback, getSessions cache behavior, invalidateSessions
- No component tests (vitest browser tests are slow; verify manually)

---

## Phase 2: Extract Shared Types

### Goal

Centralize duplicated types for reuse across stores.

### Changes

#### `frontend/src/lib/types/stores.ts` (new)

- `RemoteData<T>` — async state machine
- `DragPayload` — drag payload type
- `DropTarget` — drop target type
- `FolderSession` — lightweight session for folder view

#### `frontend/src/lib/stores/folder.svelte.ts`

- Import types from `$lib/types/stores`

---

## Phase 3: Decompose ChatComposer

### Goal

Reduce `ChatComposer` from 589 lines to ~150 lines orchestrator.

### Changes

#### Extract `ComposerTextarea.svelte` (~80 lines)

- Auto-resize textarea with keydown handling
- `use:autoResize` action
- `use:pasteImage` action
- Bindable `value` and `textareaEl`

#### Extract `ModelSelector.svelte` (~60 lines)

- Optgroup select for model picker
- Receives `providers`, `selectedProvider`, `selectedModel`
- Emits `onproviderchange`

#### Keep in ChatComposer

- Image previews (inline, simple)
- Context files strip (inline, simple)
- Token indicator (already separate)
- Send/stop button (inline, tightly coupled to state)
- Placeholder toast (inline, trivial)

---

## Implementation Order

| Phase                         | Priority    | Effort | Files   |
| ----------------------------- | ----------- | ------ | ------- |
| 1. Class-based store          | 🔴 Critical | 3-4h   | 3 files |
| 2. Shared types               | 🟡 Medium   | 30m    | 2 files |
| 3. ChatComposer decomposition | 🟡 Medium   | 2h     | 3 files |

**Total: ~6 hours**

---

## Existing Test Coverage

| Test File                 | What it Tests              | Action     |
| ------------------------- | -------------------------- | ---------- |
| `editor.svelte.spec.ts`   | editorStore override logic | Keep as-is |
| `token_estimator.spec.ts` | Token math functions       | Keep as-is |
| `greet.spec.ts`           | Example test               | Keep as-is |
| `Welcome.svelte.spec.ts`  | Example component          | Keep as-is |

**New tests needed**: `folder.test.ts` for store logic (Phase 1)

---

## Success Criteria

- [ ] Drag session to expanded folder → session list updates immediately
- [ ] No `$effect` for data fetching in FolderItem
- [ ] All folder state co-located in class-based store
- [ ] ChatComposer < 200 lines
- [ ] Unit tests for folder store logic
- [ ] No TypeScript errors
- [ ] No console warnings about reactivity
