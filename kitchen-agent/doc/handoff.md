# 🏗️ PROJECT HANDOFF: Kitchen Cabinet Agentic Workspace

## 1. Domain Context & User Persona

The user is a solo kitchen cabinet designer and builder based in Poland. They are actively learning the trade and managing a self-made "second brain" (knowledge base) consisting of roughly 200KB of Markdown files stored in a local Git repository.

The application serves as a highly specialized, local-only AI assistant. Because the entire knowledge base is small enough to fit into modern LLM context windows (128k+ tokens), **traditional RAG (Vector Databases, Chunking, Embeddings) is explicitly out of scope.** The agent relies entirely on full-context window ingestion and autonomous tool-calling to read, search, and update the local file system.

## 2. Core App Functionality (User Perspective)

The application acts as an integrated workspace combining a chat interface, a text editor, and an autonomous agent.

- **Bidirectional Knowledge Management:** The user can ask questions (e.g., _"What thickness of MDF do we use for back panels?"_). The agent autonomously maps the repository, reads the relevant files, and answers. Conversely, the user can command the agent to update the knowledge base (e.g., _"I just learned a new way to install Blum hinges, please update the hardware file."_).
- **Contextual Personas (Prompt Templates):** The user can switch the agent's behavior mid-conversation via a UI dropdown:
    - _Design Mode:_ Focuses on ergonomics, spacing, and aesthetics.
    - _Assembly Mode:_ Acts as a master carpenter, focusing on structural integrity, hardware installation, and step-by-step instructions.
- **Transparent Reasoning:** The UI explicitly shows the user exactly which files the agent read and what raw text it extracted via expandable UI logs, building trust in the agent's answers.
- **Safe File Operations:** The agent is strictly forbidden from overwriting entire files. It must use a precise "Search and Replace" tool to edit files, preventing accidental data loss or hallucinated deletions.

## 3. Project Scope & Constraints

- **In-Scope:** Local file system manipulation (Markdown), multimodal chat (text + images), chat history branching/forking, manual text editing via UI, strict TDD backend development.
- **Out-of-Scope:** Cloud deployment, multi-user authentication, Vector Databases/Semantic Search, direct integration with CAD software.
- **Constraints:** Must run locally. Must use Google Gemini 3.5 Flash (via `google-genai` SDK). Must handle Gemini's strict `thought_signature` byte-encoding requirements for multi-turn tool calling.

---

## 4. Tech Stack

- **Backend:** Python 3.11, `uv` (package manager), FastAPI, `pytest` (TDD).
- **LLM Integration:** Google Gemini 3.5 Flash via the modern `google-genai` SDK.
- **Database:** SQLite3 (Local persistence).
- **Frontend:** SvelteKit (TypeScript/JavaScript), TailwindCSS.

## 5. Current Architecture (Decoupled)

We recently migrated from Streamlit to a headless FastAPI + SvelteKit architecture to support advanced UI state (branching, attachments, text editors).

- **`src/main.py`**: FastAPI entry point. Exposes REST endpoints (`/api/chat`, `/api/sessions`).
- **`src/agent.py`**: The core LLM engine. Implements a `while True` loop to handle multi-step autonomous tool calling. Strictly preserves Gemini 3+ `thought_signature` (bytes) and `id` fields during function calling.
- **`src/db.py`**: SQLite database manager.
- **`src/serializers.py`**: Dehydration/Hydration layer. Converts complex Google `types.Content` objects (and raw bytes) into JSON strings for SQLite storage, and rebuilds them on load.
- **`src/tools/`**: Pure Python implementations of file system operations.
- **`frontend/`**: SvelteKit application handling reactive UI, chat bubbles, and native HTML `<details>` expanders for raw tool logs.

## 6. Implemented Features (100% Working)

- **Agentic Tool Loop:** The LLM can chain multiple tools together before returning a final text response to the user.
- **State Persistence:** Chats are saved to SQLite. The UI state (tool expanders/raw JSON) and API state (strict Gemini objects) are tracked separately and survive app restarts.
- **TDD Test Suite:** Pytest covers serializers, database lifecycle, file operations, and the agent loop (using `unittest.mock`).

### 🛠️ Current LLM Tool Registry

1.  `read_file(filepath)`: Reads full content of a markdown file.
2.  `get_repo_map()`: Scans the `data/` directory, extracts `#` headers from `.md` files, and returns full POSIX paths to give the LLM spatial awareness.
3.  `edit_file(filepath, search_text, replace_text)`: Safe search-and-replace to prevent the LLM from accidentally deleting file contents.
4.  `create_file(filepath, content)`: Safely creates new files and directories (fails if file already exists).

## 7. Database Schema (SQLite)

**Table:** `sessions`

- `id` (TEXT PRIMARY KEY)
- `title` (TEXT)
- `api_history_json` (TEXT) - Dehydrated Gemini objects.
- `ui_history_json` (TEXT) - UI-friendly chat log with tool execution results.
- `updated_at` (TIMESTAMP)

---

## 8. Planned Features & Roadmap (To Be Implemented)

The following features have been architected but not yet coded. They are the priority for the new chat session:

### A. Advanced Chat Management

- **Forking/Branching:** Ability to slice the `api_history_json` array at a specific turn, generate a new `session_id`, and branch the conversation to explore different design angles.
- **Exporting:** Save a chat session as a formatted `.md` file.
- **Prompt Logging:** Append every user prompt to a running `data/prompt_log.md` file.

### B. UI & Workspace Enhancements (Svelte + FastAPI)

- **Right Sidebar (Context Injection):** UI to explicitly select files and inject them into the LLM's system prompt/context for the current turn.
- **Simple Text Editor:** `GET /api/files` and `PUT /api/files` endpoints to allow manual editing of markdown files directly in the Svelte UI.
- **Highlight -> Add to Docs:** Context menu in the chat UI. Highlight text -> click button -> `POST /api/files/append` to add the snippet to a specific markdown file.

### C. Multimodal & Advanced Tools

- **Image Pasting (CTRL+V):** Intercept pasted images in Svelte, convert to Base64, and pass to FastAPI to construct `types.Part.from_bytes(..., mime_type="image/jpeg")`.
- **Advanced Search Tool:** A new Python tool (`search_knowledge_base`) utilizing regex to simulate `grep -E` (OR logic) across the entire file contents, not just headers.
