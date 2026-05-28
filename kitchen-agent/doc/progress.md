# 📊 Project Progress: Kitchen Cabinet Agentic Workspace

## ✅ Done

### Core Architecture
- FastAPI backend (`src/main.py`) with REST endpoints.
- Agentic tool loop (`src/agent.py`) with multi-step tool calling.
- SQLite persistence (`src/db.py`).
- Dehydration/Hydration serializers (`src/serializers.py`).
- TDD suite via `pytest`.

### LLM Tool Registry
- `read_file(filepath)`
- `get_repo_map()`
- `edit_file(filepath, search_text, replace_text)`
- `create_file(filepath, content)`
- `write_file(filepath, content)` — overwrite primitive (`src/tools/file_ops.py`).

### Section 6.A — Advanced Chat Management
- ✅ **Forking/Branching** — `DatabaseManager.fork_session()`, `POST /api/sessions/{id}/fork`.
- ✅ **Exporting** — `src/exporter.py`, `DatabaseManager.export_session()`, `GET /api/sessions/{id}/export`.
- ✅ **Prompt Logging** — `src/prompt_logger.py` (`log_prompt()`), wired into `POST /api/chat`.

### Section 6.B — UI & Workspace Enhancements
- ✅ **Simple Text Editor** — `write_file()` plus `GET /api/files` and `PUT /api/files` endpoints.

## 🚧 To Do

### Section 6.B — UI & Workspace Enhancements
- **Right Sidebar (Context Injection):** UI to select files and inject them into the LLM's system prompt/context for the current turn.
- **Highlight → Add to Docs:** Context menu in the chat UI; `POST /api/files/append` to add a snippet to a markdown file.

### Section 6.C — Multimodal & Advanced Tools
- **Image Pasting (CTRL+V):** Intercept pasted images in Svelte, convert to Base64, pass to FastAPI as `types.Part.from_bytes(...)`.
- **Advanced Search Tool:** `search_knowledge_base` using regex (`grep -E` OR logic) across full file contents.
