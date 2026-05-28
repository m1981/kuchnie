Here is your comprehensive handoff document. You can copy and paste this entire message into your new chat window. It contains all the architectural context, technical decisions, and roadmaps we have established so far.

---

# 🏗️ PROJECT HANDOFF: Kitchen Cabinet Agentic Workspace

## 1. Project Overview

A local-only, agentic workspace designed for a solo kitchen cabinet designer/builder. The application acts as a bidirectional interface to a local Markdown knowledge base (~200KB). It allows the user to chat with their notes, autonomously read/edit files, and manage kitchen design/assembly workflows.

## 2. Tech Stack

- **Backend:** Python 3.11, `uv` (package manager), FastAPI, `pytest` (TDD).
- **LLM Integration:** Google Gemini 3.5 Flash via the modern `google-genai` SDK.
- **Database:** SQLite3 (Local persistence).
- **Frontend:** SvelteKit (TypeScript/JavaScript), TailwindCSS.

## 3. Current Architecture (Decoupled)

We recently migrated from Streamlit to a headless FastAPI + SvelteKit architecture to support advanced UI state (branching, attachments, text editors).

- **`src/main.py`**: FastAPI entry point. Exposes REST endpoints (`/api/chat`, `/api/sessions`).
- **`src/agent.py`**: The core LLM engine. Implements a `while True` loop to handle multi-step autonomous tool calling. Strictly preserves Gemini 3+ `thought_signature` (bytes) and `id` fields during function calling.
- **`src/db.py`**: SQLite database manager.
- **`src/serializers.py`**: Dehydration/Hydration layer. Converts complex Google `types.Content` objects (and raw bytes) into JSON strings for SQLite storage, and rebuilds them on load.
- **`src/tools/`**: Pure Python implementations of file system operations.
- **`frontend/`**: SvelteKit application handling reactive UI, chat bubbles, and native HTML `<details>` expanders for raw tool logs.

## 4. Implemented Features (100% Working)

- **Agentic Tool Loop:** The LLM can chain multiple tools together before returning a final text response to the user.
- **State Persistence:** Chats are saved to SQLite. The UI state (tool expanders/raw JSON) and API state (strict Gemini objects) are tracked separately and survive app restarts.
- **TDD Test Suite:** Pytest covers serializers, database lifecycle, file operations, and the agent loop (using `unittest.mock`).

### 🛠️ Current LLM Tool Registry

1.  `read_file(filepath)`: Reads full content of a markdown file.
2.  `get_repo_map()`: Scans the `data/` directory, extracts `#` headers from `.md` files, and returns full POSIX paths to give the LLM spatial awareness.
3.  `edit_file(filepath, search_text, replace_text)`: Safe search-and-replace to prevent the LLM from accidentally deleting file contents.
4.  `create_file(filepath, content)`: Safely creates new files and directories (fails if file already exists).

### 🌿 Session Management

- **Forking/Branching:** `POST /api/sessions/{session_id}/fork` with `{turn_index}` slices both `api_history_json` and `ui_history_json` inclusively up to the given turn and creates a new session with a derived title. Original session is untouched. Implemented in `DatabaseManager.fork_session()`.

## 5. Database Schema (SQLite)

**Table:** `sessions`

- `id` (TEXT PRIMARY KEY)
- `title` (TEXT)
- `api_history_json` (TEXT) - Dehydrated Gemini objects.
- `ui_history_json` (TEXT) - UI-friendly chat log with tool execution results.
- `updated_at` (TIMESTAMP)

---

## 6. Planned Features & Roadmap (To Be Implemented)

The following features have been architected but not yet coded. They are the priority for the new chat session:

### A. Advanced Chat Management

- ✅ **Forking/Branching:** ~~Ability to slice the `api_history_json` array at a specific turn, generate a new `session_id`, and branch the conversation to explore different design angles.~~ **DONE** — see `DatabaseManager.fork_session()` and `POST /api/sessions/{id}/fork`.
- ✅ **Exporting:** ~~Save a chat session as a formatted `.md` file.~~ **DONE** — see `DatabaseManager.export_session()`, `src/exporter.py`, and `GET /api/sessions/{id}/export`.
- ✅ **Prompt Logging:** ~~Append every user prompt to a running `data/prompt_log.md` file.~~ **DONE** — see `src/prompt_logger.py` (`log_prompt()`), wired into `POST /api/chat`.

### B. UI & Workspace Enhancements (Svelte + FastAPI)

- **Right Sidebar (Context Injection):** UI to explicitly select files and inject them into the LLM's system prompt/context for the current turn.
- **Simple Text Editor:** `GET /api/files` and `PUT /api/files` endpoints to allow manual editing of markdown files directly in the Svelte UI.
- **Highlight -> Add to Docs:** Context menu in the chat UI. Highlight text -> click button -> `POST /api/files/append` to add the snippet to a specific markdown file.

### C. Multimodal & Advanced Tools

- **Image Pasting (CTRL+V):** Intercept pasted images in Svelte, convert to Base64, and pass to FastAPI to construct `types.Part.from_bytes(..., mime_type="image/jpeg")`.
- **Advanced Search Tool:** A new Python tool (`search_knowledge_base`) utilizing regex to simulate `grep -E` (OR logic) across the entire file contents, not just headers.

---

**Next Immediate Action for New Chat:**
Review this document and select one feature from Section 6 (e.g., Image Pasting, Text Editor, or Forking) to begin implementation using the FastAPI + SvelteKit stack.
