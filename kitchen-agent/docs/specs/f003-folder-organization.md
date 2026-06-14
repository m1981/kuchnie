# F003: Folder Organization

## Overview

Feature for organizing chat sessions into folders with colors, ordering, and
expand/collapse functionality. Inspired by the chat_collector's folder system.

**Status**: Design  
**Date**: 2026-06-14  
**Vertical Slices**: Backend API → Frontend UI → E2E Tests

---

## 1. Design Review — 5 Ownership Questions

### 1. WHO owns this data?

| Data Element                               | Owner                         | Notes                       |
| ------------------------------------------ | ----------------------------- | --------------------------- |
| **Folder**                                 | `FolderRepository` (Protocol) | Single persistence owner    |
| **Session-Folder assignment**              | `FolderRepository`            | Junction table relationship |
| **Folder tree state (expanded/collapsed)** | Frontend store                | UI-only, not persisted      |
| **Folder color**                           | `FolderRepository`            | Persisted in DB             |

### 2. WHO constructs this object?

| Object           | Construction Site         | Pattern              |
| ---------------- | ------------------------- | -------------------- |
| `Folder`         | `FolderService`           | Business logic layer |
| `FolderResponse` | FastAPI (auto-serialized) | Pydantic model       |
| `FolderStore`    | Svelte component          | Frontend state       |

### 3. WHERE does this logic live?

| Logic                 | Location                | Correct?         |
| --------------------- | ----------------------- | ---------------- |
| Folder CRUD           | `FolderService`         | ✅ Service layer |
| Folder validation     | `FolderService`         | ✅ Fail fast     |
| Session assignment    | `FolderService`         | ✅ Service layer |
| Tree state management | `folderStore.svelte.ts` | ✅ Frontend      |
| Color picker          | Svelte component        | ✅ UI concern    |

### 4. WHAT crosses this boundary?

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  API Layer (FastAPI)                                                        │
│  Input:  FolderRequest {name, color?, parent_id?}                          │
│  Output: FolderResponse {id, name, color, session_count, parent_id}        │
│  Contract: Pydantic BaseModel                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  Service Layer (FolderService)                                              │
│  Receives: FolderRequest (typed)                                           │
│  Calls:    FolderRepository (Protocol)                                     │
│  Returns:  FolderResponse (typed)                                          │
└─────────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  Repository Layer (FolderRepository Protocol)                               │
│  Methods: create_folder, list_folders, update_folder, delete_folder,       │
│           assign_session, unassign_session, get_folder_sessions            │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5. HOW is this tested?

| Layer           | Test Approach                            | Mocking Required     |
| --------------- | ---------------------------------------- | -------------------- |
| `FolderService` | Unit — mock `FolderRepository`           | Protocol mocks       |
| API endpoints   | Contract — `TestClient` with DI override | `FolderService` mock |
| E2E             | Playwright with real backend             | Seed fixtures        |

---

## 2. Database Schema

### 2.1 New Tables

```sql
-- Folders table
CREATE TABLE IF NOT EXISTS folders (
    id TEXT PRIMARY KEY,           -- UUID
    name TEXT NOT NULL,
    color TEXT DEFAULT '#6B7280',   -- Hex color
    icon TEXT DEFAULT '📁',        -- Emoji icon
    parent_id TEXT,                -- For nested folders (nullable = root)
    order_index INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (parent_id) REFERENCES folders(id) ON DELETE CASCADE
);

-- Session-Folder junction table
CREATE TABLE IF NOT EXISTS session_folders (
    session_id TEXT NOT NULL,
    folder_id TEXT NOT NULL,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (session_id, folder_id),
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (folder_id) REFERENCES folders(id) ON DELETE CASCADE
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_folders_parent_id ON folders(parent_id);
CREATE INDEX IF NOT EXISTS idx_session_folders_session ON session_folders(session_id);
CREATE INDEX IF NOT EXISTS idx_session_folders_folder ON session_folders(folder_id);
```

### 2.2 Schema Diagram

```
┌─────────────────┐       ┌─────────────────────┐       ┌─────────────────┐
│    sessions     │       │   session_folders   │       │     folders     │
├─────────────────┤       ├─────────────────────┤       ├─────────────────┤
│ id (PK)        │◄──┐   │ session_id (FK,PK)  │   ┌──►│ id (PK)        │
│ title          │   └───│ folder_id (FK,PK)   │───┘   │ name           │
│ ...            │       │ assigned_at         │       │ color          │
└─────────────────┘       └─────────────────────┘       │ icon           │
                                                        │ parent_id (FK) │──┐
                                                        │ order_index    │  │
                                                        └─────────────────┘  │
                                                             ▲               │
                                                             └───────────────┘
                                                               (self-ref)
```

---

## 3. API Design

### 3.1 Endpoints

| Method   | Path                                      | Description          | Status |
| -------- | ----------------------------------------- | -------------------- | ------ |
| `POST`   | `/api/folders`                            | Create folder        | 201    |
| `GET`    | `/api/folders`                            | List all folders     | 200    |
| `GET`    | `/api/folders/{id}`                       | Get folder details   | 200    |
| `PATCH`  | `/api/folders/{id}`                       | Update folder        | 200    |
| `DELETE` | `/api/folders/{id}`                       | Delete folder        | 204    |
| `POST`   | `/api/folders/{id}/sessions/{session_id}` | Assign session       | 201    |
| `DELETE` | `/api/folders/{id}/sessions/{session_id}` | Unassign session     | 204    |
| `GET`    | `/api/folders/{id}/sessions`              | List folder sessions | 200    |

### 3.2 Schemas

```python
class FolderCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    color: str = Field(default="#6B7280", pattern=r"^#[0-9A-Fa-f]{6}$")
    icon: str = Field(default="📁", max_length=10)
    parent_id: str | None = None

class FolderUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    icon: str | None = Field(default=None, max_length=10)
    order_index: int | None = None

class FolderResponse(BaseModel):
    id: str
    name: str
    color: str
    icon: str
    parent_id: str | None
    order_index: int
    session_count: int
    created_at: str
    updated_at: str

class FolderListResponse(BaseModel):
    folders: list[FolderResponse]
    total: int
```

---

## 4. Vertical Slice Plan

### Slice 1: Backend — Folder Repository + Service (TDD)

**Files:**

- `src/repositories/folder_repo.py` — SQLite implementation
- `src/folder_service.py` — Business logic
- `src/schemas.py` — Add folder schemas
- `src/dependencies.py` — Wire DI
- `tests/unit/repositories/test_folder_repo.py`
- `tests/unit/services/test_folder_service.py`

**Test First:**

1. `test_create_folder` — CRUD basics
2. `test_list_folders` — With session counts
3. `test_update_folder` — Name, color, icon
4. `test_delete_folder` — Cascade behavior
5. `test_assign_session` — Many-to-many
6. `test_unassign_session` — Remove assignment
7. `test_folder_not_found` — Error handling

### Slice 2: Backend — API Endpoints (Contract Tests)

**Files:**

- `src/api/folders.py` — FastAPI router
- `src/main.py` — Register router
- `tests/integration/test_folder_endpoints.py`

**Test First:**

1. `test_create_folder_returns_201`
2. `test_list_folders_returns_200`
3. `test_update_folder_returns_200`
4. `test_delete_folder_returns_204`
5. `test_assign_session_returns_201`
6. `test_validation_errors` — 422 for bad input

### Slice 3: Frontend — Folder Store + Components

**Files:**

- `frontend/src/lib/stores/folder.svelte.ts` — Folder state
- `frontend/src/lib/components/FolderTree.svelte` — Tree component
- `frontend/src/lib/components/FolderItem.svelte` — Single folder
- `frontend/src/lib/components/CreateFolderDialog.svelte` — Dialog
- `frontend/src/lib/components/ColorPicker.svelte` — Color selection

**Test First (Vitest):**

1. `test_folder_store_creates_folder`
2. `test_folder_store_lists_folders`
3. `test_folder_store_expands_collapses`
4. `test_folder_store_assigns_session`

### Slice 4: Frontend — Session Sidebar Integration

**Files:**

- `frontend/src/lib/components/SessionTree.svelte` — Update to show folders
- `frontend/src/lib/stores/sessions.svelte.ts` — Add folder filtering

### Slice 5: E2E Tests (Playwright)

**Files:**

- `e2e/tests/folder-organization.spec.ts`
- `e2e/page-objects/FolderPage.ts` — Page object

**Tests:**

1. `test_create_folder_via_ui`
2. `test_assign_session_to_folder`
3. `test_folder_expand_collapse`
4. `test_folder_color_change`
5. `test_delete_folder_moves_sessions`

---

## 5. Implementation Order

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Phase 1: Backend Core (TDD)                                               │
│  ├── 1.1 Schema migration (folders + session_folders tables)               │
│  ├── 1.2 FolderRepository Protocol + SQLite implementation                 │
│  ├── 1.3 FolderService with validation                                     │
│  └── 1.4 Unit tests for all                                               │
├─────────────────────────────────────────────────────────────────────────────┤
│  Phase 2: API Layer (Contract Tests)                                       │
│  ├── 2.1 Pydantic schemas (FolderCreateRequest, etc.)                      │
│  ├── 2.2 FastAPI router (POST, GET, PATCH, DELETE)                         │
│  ├── 2.3 DI wiring (get_folder_service)                                    │
│  └── 2.4 Integration tests                                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│  Phase 3: Frontend Store (Vitest)                                          │
│  ├── 3.1 folderStore.svelte.ts                                             │
│  ├── 3.2 API client functions                                              │
│  └── 3.3 Store unit tests                                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│  Phase 4: Frontend Components                                              │
│  ├── 4.1 FolderTree, FolderItem components                                 │
│  ├── 4.2 CreateFolderDialog                                                │
│  ├── 4.3 ColorPicker                                                       │
│  └── 4.4 Session sidebar integration                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│  Phase 5: E2E Tests (Playwright)                                           │
│  ├── 5.1 Page objects for folder interactions                              │
│  ├── 5.2 Full workflow tests                                               │
│  └── 5.3 Visual regression (screenshots)                                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 6. Color Palette

Default folder colors (inspired by chat_collector):

| Name   | Hex       | Preview |
| ------ | --------- | ------- |
| Gray   | `#6B7280` | ⬜      |
| Red    | `#EF4444` | 🟥      |
| Orange | `#F97316` | 🟧      |
| Yellow | `#EAB308` | 🟨      |
| Green  | `#22C55E` | 🟩      |
| Blue   | `#3B82F6` | 🟦      |
| Purple | `#A855F7` | 🟪      |
| Pink   | `#EC4899` | 🩷      |

---

## 7. UI Mockup

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Sidebar                                                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ [+ New Folder]                                                      │   │
│  │                                                                     │   │
│  │ ▼ 📁 Kitchen Projects (#3B82F6)                    [3]              │   │
│  │   ├── Modern Kitchen Reno                                          │   │
│  │   ├── Classic Style Discussion                                     │   │
│  │   └── Budget Planning                                              │   │
│  │                                                                     │   │
│  │ ▶ 📁 Bathroom Ideas (#22C55E)                    [2]              │   │
│  │                                                                     │   │
│  │ ▶ 📁 Living Room (#F97316)                       [1]              │   │
│  │                                                                     │   │
│  │ ─── Unorganized ──────────────────────────────── [5]              │   │
│  │   ├── Random Chat 1                                                │   │
│  │   ├── Random Chat 2                                                │   │
│  │   └── ...                                                          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 8. Migration Strategy

Since we're adding new tables (not modifying existing), migration is straightforward:

1. Add `CREATE TABLE IF NOT EXISTS` in `connection.py` `_init_db()`
2. No data migration needed
3. All existing sessions become "unorganized" (no folder assignment)

---

## 9. Success Criteria

| Criteria                         | Verification         |
| -------------------------------- | -------------------- |
| Create folder via API            | Unit + Contract test |
| Assign session to folder         | Unit + Contract test |
| Folder shows in sidebar          | E2E test             |
| Color persists                   | E2E test             |
| Delete folder unassigns sessions | Unit test            |
| Empty folder deletable           | Unit test            |
| Sessions without folder shown    | UI verification      |

---

## 10. File Reference

| File                                            | Purpose                  | Phase |
| ----------------------------------------------- | ------------------------ | ----- |
| `src/repositories/folder_repo.py`               | SQLite folder repository | 1     |
| `src/folder_service.py`                         | Folder business logic    | 1     |
| `src/schemas.py`                                | Add folder schemas       | 2     |
| `src/api/folders.py`                            | FastAPI router           | 2     |
| `src/dependencies.py`                           | Add folder DI            | 2     |
| `frontend/src/lib/stores/folder.svelte.ts`      | Frontend state           | 3     |
| `frontend/src/lib/components/FolderTree.svelte` | Tree component           | 4     |
| `e2e/tests/folder-organization.spec.ts`         | E2E tests                | 5     |
