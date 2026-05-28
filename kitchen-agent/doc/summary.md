# Project Summary — Kitchen Cabinet Agentic Workspace

## Project in one sentence

A local-only AI workspace for a Polish kitchen cabinet designer: SvelteKit frontend ↔ FastAPI backend ↔ Gemini agentic loop that reads/writes a Markdown knowledge base.

---

## What was already working (baseline)

- Agentic tool loop with `thought_signature` bytes preservation
- SQLite persistence (dehydrate/hydrate serializers)
- 4 tools: `read_file`, `get_repo_map`, `edit_file`, `create_file`
- Session list, fork, export, prompt templates, tool log expanders
- 34 unit tests

---

## What was implemented (session 2026-05-28)

### Backend (Python / FastAPI)

| Feature                          | Details                                                                                                                                                             |
| -------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **`search_knowledge_base` tool** | `tools/file_ops.py` — regex grep across all `.md` files, OR logic, 200-line cap, case-insensitive; schema in `tools/schemas.py`; wired into `agent.py` FUNCTION_MAP |
| **`append_to_file` tool**        | `tools/file_ops.py` — appends snippet, creates file+dirs if missing                                                                                                 |
| **`GET /api/files`**             | Lists all `.md` files in `data/`                                                                                                                                    |
| **`GET /api/files/{path}`**      | Returns file content for the editor                                                                                                                                 |
| **`PUT /api/files/{path}`**      | Saves manual edits back to disk (path-traversal guarded)                                                                                                            |
| **`POST /api/files/append`**     | Used by Highlight → Add to Docs                                                                                                                                     |
| **`GET /api/repo-map`**          | Exposes the repo map for the sidebar                                                                                                                                |
| **Multimodal images**            | `ChatRequest.images` → base64 → `types.Part.from_bytes(...)` in `agent.py`                                                                                          |
| **Context file injection**       | `ChatRequest.context_files` → files prepended as text block before user message                                                                                     |
| **17 new TDD tests**             | `test_search_tool.py`, `test_file_api.py` — all pass                                                                                                                |

### Frontend (Svelte 5)

| Feature                     | Details                                                                                               |
| --------------------------- | ----------------------------------------------------------------------------------------------------- |
| **`ContextSidebar.svelte`** | Right panel with two tabs: **Context** (checkboxes to inject files) and **Editor** (opens FileEditor) |
| **`FileEditor.svelte`**     | Inline monospace textarea with `GET`/`PUT` file endpoints, dirty tracking, ⌘S save                    |
| **Image paste (Ctrl+V)**    | `onpaste` handler on textarea → FileReader → base64 → preview thumbnails; sent as `images[]` to API   |
| **Highlight → Add to Docs** | `onmouseup` on the whole page → floating popup with file selector → `POST /api/files/append`          |
| **⎇ Fork button**           | Per-message fork button that calls `/api/sessions/{id}/fork` and switches to the new session          |
| **Export button**           | Left sidebar "Export session" downloads `.md` via the existing export endpoint                        |
| **Context pill indicator**  | Shows which files are queued for injection; reflected in footer status line                           |
| **Sidebar toggle**          | Header button shows/hides the right panel                                                             |

---

## Tech Stack

| Layer    | Technology                                       |
| -------- | ------------------------------------------------ |
| Backend  | Python 3.11, FastAPI, `uv`                       |
| LLM      | Google Gemini 3.5 Flash via `google-genai` SDK   |
| Database | SQLite3                                          |
| Frontend | SvelteKit (Svelte 5), TypeScript, TailwindCSS v4 |
| Tests    | `pytest` (51 unit tests, TDD)                    |

---

## File Structure (key files)

```
kitchen-agent/
├── src/
│   ├── main.py            # FastAPI entry point + all REST endpoints
│   ├── agent.py           # Gemini agentic loop (tool calling, multimodal)
│   ├── db.py              # SQLite manager (save/load/fork/export)
│   ├── serializers.py     # Dehydrate/hydrate Gemini Content objects
│   ├── exporter.py        # Session → Markdown export
│   ├── prompt_logger.py   # Appends every user prompt to data/prompt_log.md
│   └── tools/
│       ├── file_ops.py    # read_file, edit_file, create_file, append_to_file, search_knowledge_base
│       ├── repo_map.py    # get_repo_map (scans data/ for .md headers)
│       └── schemas.py     # Gemini function declaration schemas
├── frontend/
│   └── src/
│       ├── routes/+page.svelte              # Main chat page (full workspace)
│       └── lib/components/
│           ├── Markdown.svelte              # Rendered markdown with syntax highlight
│           ├── ContextSidebar.svelte        # Right sidebar: context injection + editor
│           └── FileEditor.svelte            # Inline markdown file editor
├── tests/
│   ├── test_agent.py
│   ├── test_db.py
│   ├── test_file_ops.py
│   ├── test_file_api.py       # NEW — REST endpoint tests
│   ├── test_search_tool.py    # NEW — search + append tool tests
│   ├── test_serializers.py
│   ├── test_exporter.py
│   ├── test_fork.py
│   ├── test_prompt_logger.py
│   ├── test_repo_map.py
│   └── test_tools.py
└── doc/
    ├── handoff.md
    └── summary.md             # ← this file
```

---

## Remaining Roadmap (not yet implemented)

- Streaming responses (SSE) for real-time token display
- Search tool exposed in UI (explicit search panel)
- Mobile-responsive left sidebar (drawer)
- Vitest frontend component tests
