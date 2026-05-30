"""
src/main.py
===========
FastAPI application — HTTP layer only.

Responsibilities
----------------
* Declare routes and Pydantic request / response models.
* Validate input and translate service/domain errors into HTTP responses.
* Delegate all business logic to `ChatService`, Repositories, and PromptManager.
"""

import asyncio
import json
import structlog
from functools import partial
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from src.chat_service import ChatService
from src.config import settings
from src.message_editor import MessageEditService, EditError
from src.prompt_manager import PromptManager, prompt_manager as _default_prompt_manager
from src.tools.file_ops import append_to_file, revert_backup
from src.tools.repo_map import get_repo_map
from src.logger import setup_logging

# --- Clean imports for Schemas and Repositories ---
from src.schemas import (
    ChatRequest, ChatResponse, ForkRequest, ForkResponse,
    SessionSummary, SessionNode, FileReadResponse, FileWriteRequest,
    FileAppendRequest, FileListItem, NoteCreateRequest, NoteResponse,
    RevertResponse, PromptModeResponse, PromptModeDetail,
    LlmExportResponse, LlmExportMetadata, LlmExportConfig, LlmExportTurn,
    # Message editor schemas
    MessageEditRequest, MessageEditResponse,
    MessageDeleteResponse,
    TruncateRequest, TruncateResponse,
    SystemPromptUpdateRequest, SystemPromptResponse, SystemPromptUpdateResponse,
    # Token counting schemas
    TokenEstimateRequest, TokenEstimateResponse, SessionTokensResponse,
    # Provider catalogue schemas
    ModelInfo, ProviderInfo, ActiveProvider,
)
from src.token_counter import (
    count_session_tokens,
    build_pending_context_estimate,
)
from src.repositories import (
    SQLiteConnection,
    SQLiteSessionRepository,
    SQLiteNoteRepository,
    SessionRepository,
    NoteRepository
)

# Initialize structured logging
setup_logging(is_local_dev=True)
logger = structlog.get_logger(__name__)
# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Kitchen Cabinet Agent API",
    description="AI agent for kitchen cabinet design, materials and assembly.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Dependency injection
# ---------------------------------------------------------------------------

# Singleton connection manager for the app lifecycle
db_connection = SQLiteConnection()


def get_session_repo() -> SessionRepository:
    """FastAPI dependency: returns the Session Repository."""
    return SQLiteSessionRepository(db_connection)


def get_note_repo() -> NoteRepository:
    """FastAPI dependency: returns the Note Repository."""
    return SQLiteNoteRepository(db_connection)


def get_chat_service(session_repo: SessionRepository = Depends(get_session_repo)) -> ChatService:
    """FastAPI dependency: returns a ChatService wired to the Session Repo."""
    return ChatService(session_repo)


def get_prompt_manager() -> PromptManager:
    """
    FastAPI dependency: returns the module-level PromptManager singleton.

    Isolated via ``app.dependency_overrides`` in tests so no real disk I/O
    occurs during the test suite.
    """
    return _default_prompt_manager


def get_message_editor(
    session_repo: SessionRepository = Depends(get_session_repo),
) -> MessageEditService:
    """FastAPI dependency: returns a MessageEditService wired to the Session Repo."""
    return MessageEditService(session_repo)


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def _resolve_data_path(filepath: str) -> Path:
    """
    Resolves *filepath* relative to ``settings.data_dir`` and guards against
    path-traversal attacks.

    Raises:
        HTTPException 400: when the resolved path escapes the data directory.
    """
    resolved = (settings.data_dir / filepath).resolve()
    if not str(resolved).startswith(str(settings.data_dir.resolve())):
        raise HTTPException(status_code=400, detail="Path traversal not allowed.")
    return resolved


def _resolve_context_file_paths(
    context_files: list[str] | None,
) -> list[str] | None:
    """
    Resolve context file paths sent by the frontend to full filesystem paths.

    The frontend ``ContextSidebar`` sends ``FileListItem.path`` values that are
    relative to ``settings.data_dir`` (e.g. ``"kuchnia-kroki.md"``).  The agent's
    ``read_file`` function resolves paths relative to CWD, so a bare filename like
    ``"kuchnia-kroki.md"`` will fail unless the server is started from *inside*
    ``data/``.

    This function converts each path to a canonical absolute path under data_dir:

      1. If the path is already absolute AND inside data_dir → keep it.
      2. If the path is absolute but outside data_dir → silently drop it
         (path-traversal guard).
      3. If the path is relative → resolve it relative to data_dir
         (this is the normal frontend case: ``"file.md"`` → ``data_dir/file.md``).

    Note: we intentionally do NOT check ``Path(fp).exists()`` here because the
    file may exist in CWD by coincidence (e.g. a same-named file in the project
    root) which would yield the wrong content.  We always treat relative paths
    as relative to data_dir.

    Args:
        context_files: Raw list from the HTTP request, or ``None``.

    Returns:
        Resolved list of absolute path strings, or ``None`` when the input is
        empty / ``None``.
    """
    if not context_files:
        return None

    data_dir_resolved = settings.data_dir.resolve()
    resolved_paths: list[str] = []

    for fp in context_files:
        candidate = Path(fp)

        if candidate.is_absolute():
            # Already absolute — validate it's inside data_dir.
            try:
                candidate.resolve().relative_to(data_dir_resolved)
            except ValueError:
                logger.warning(
                    "context_file_path_traversal_dropped",
                    path=fp,
                    data_dir=str(data_dir_resolved),
                )
                continue
            resolved_paths.append(fp)
        else:
            # Relative path — always resolve relative to data_dir.
            # This is the normal case from the ContextSidebar frontend.
            prefixed = (settings.data_dir / fp).resolve()

            # Path-traversal guard: relative paths containing ".." could escape.
            if not str(prefixed).startswith(str(data_dir_resolved)):
                logger.warning(
                    "context_file_path_traversal_dropped",
                    path=fp,
                    resolved=str(prefixed),
                )
                continue

            resolved_paths.append(str(prefixed))

    return resolved_paths or None


# ---------------------------------------------------------------------------
# Session endpoints
# ---------------------------------------------------------------------------

@app.get("/api/sessions", response_model=list[SessionSummary])
def get_sessions(
    include_archived: bool = Query(False),
    session_repo: SessionRepository = Depends(get_session_repo),
) -> list[SessionSummary]:
    """
    Returns a flat list of all sessions ordered by most-recently updated.

    Archived sessions are hidden by default; pass ``?include_archived=true``
    to surface them (e.g. for an 'archived chats' management screen).
    """
    return [SessionSummary(**row) for row in session_repo.list_sessions(include_archived=include_archived)]


@app.get("/api/sessions/tree", response_model=list[SessionNode])
def get_session_tree(
    include_archived: bool = Query(True),
    session_repo: SessionRepository = Depends(get_session_repo),
) -> list[SessionNode]:
    """
    Returns all sessions as a forest of trees.

    Each root session (no parent) is a top-level element; its ``children``
    list contains forked sessions, recursively.  Use this endpoint to render
    the sidebar tree view.

    Archived sessions are included by default so the tree structure stays
    coherent — they appear greyed-out in the UI rather than leaving gaps
    in the ancestry chain.
    """
    def _build(node: dict) -> SessionNode:
        return SessionNode(
            **{k: v for k, v in node.items() if k != "children"},
            children=[_build(c) for c in node.get("children", [])],
        )
    return [_build(root) for root in session_repo.get_session_tree(include_archived=include_archived)]


@app.get("/api/sessions/{session_id}")
def get_session(
    session_id: str,
    session_repo: SessionRepository = Depends(get_session_repo),
) -> dict:
    _, ui_json, _ = session_repo.load_session(session_id)
    ui_messages = json.loads(ui_json) if ui_json and ui_json != "[]" else []
    return {"ui_messages": ui_messages}


@app.get("/api/sessions/{session_id}/export", response_class=PlainTextResponse)
def export_session(
    session_id: str,
    session_repo: SessionRepository = Depends(get_session_repo),
) -> PlainTextResponse:
    """
    Exports the session as a human-readable Markdown document.

    Uses ``ui_history_json`` — the pretty, tool-summarised UI representation.
    Suitable for archiving, sharing or reading.
    """
    try:
        markdown = session_repo.export_session(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return PlainTextResponse(content=markdown, media_type="text/markdown")


@app.get(
    "/api/sessions/{session_id}/export/llm",
    response_model=LlmExportResponse,
    summary="Export session as raw LLM context (debug)",
    description=(
        "Returns the complete LLM call context as structured JSON, mirroring "
        "exactly what the Gemini model received: the ``GenerateContentConfig`` "
        "envelope (model, temperature, system_instruction, tool schemas) followed "
        "by every ``Content`` turn from ``api_history_json``.\n\n"
        "Key order: ``metadata`` → ``config`` → ``turns``\n\n"
        "Intended for debugging multi-turn tool-calling sessions."
    ),
)
def export_session_llm(
    session_id: str,
    session_repo: SessionRepository = Depends(get_session_repo),
) -> LlmExportResponse:
    """
    F04 — LLM-context debug export with GenerateContentConfig envelope.

    HTTP status codes:
      200 — export succeeded
      404 — session not found
    """
    try:
        data = session_repo.export_session_llm_json(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return LlmExportResponse(
        metadata=LlmExportMetadata(**data["metadata"]),
        config=LlmExportConfig(**data["config"]),
        turns=[LlmExportTurn(**turn) for turn in data["turns"]],
    )


@app.post("/api/sessions/{session_id}/fork", response_model=ForkResponse)
def fork_session(
    session_id: str,
    request: ForkRequest,
    session_repo: SessionRepository = Depends(get_session_repo),
) -> ForkResponse:
    try:
        new_id = session_repo.fork_session(session_id, request.turn_index)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ForkResponse(new_session_id=new_id)


@app.patch("/api/sessions/{session_id}/archive", status_code=200)
def archive_session(
    session_id: str,
    session_repo: SessionRepository = Depends(get_session_repo),
) -> dict:
    archived = session_repo.archive_session(session_id)
    if not archived:
        raise HTTPException(status_code=404, detail=f"Session not found or already archived: {session_id}")
    return {"archived": True, "session_id": session_id}


@app.delete("/api/sessions/{session_id}/archive", status_code=200)
def unarchive_session(
    session_id: str,
    session_repo: SessionRepository = Depends(get_session_repo),
) -> dict:
    """
    Reverses an archive.  Returns 404 when the session does not exist or is
    not currently archived.
    """
    unarchived = session_repo.unarchive_session(session_id)
    if not unarchived:
        raise HTTPException(status_code=404, detail=f"Session not found or not archived: {session_id}")
    return {"archived": False, "session_id": session_id}


@app.delete("/api/sessions/{session_id}", status_code=204)
def delete_session(
    session_id: str,
    session_repo: SessionRepository = Depends(get_session_repo),
) -> None:
    """
    Permanently deletes a session and all its notes.

    Returns 404 when the session does not exist.
    Returns 409 Conflict when the session has living child sessions — delete
    all descendants (leaf-first) before deleting the parent.
    """
    try:
        session_repo.delete_session(session_id)
    except ValueError as exc:
        detail = str(exc)
        status = 409 if "child" in detail.lower() else 404
        raise HTTPException(status_code=status, detail=detail) from exc


# ---------------------------------------------------------------------------
# Message editing endpoints
# ---------------------------------------------------------------------------

@app.patch(
    "/api/sessions/{session_id}/messages/{turn_id}",
    response_model=MessageEditResponse,
    summary="Edit a message in the conversation",
    description=(
        "Replace the text content of the message identified by ``turn_id`` "
        "(the stable UUID stamped on the message at write time).  "
        "Both the display layer and the LLM API history are updated atomically.\n\n"
        "Use this to fix typos, rephrase a question, or correct an assistant "
        "answer — without restarting the conversation.\n\n"
        "HTTP status codes:\n"
        "  200 — edit applied\n"
        "  400 — turn_id not found, content is blank, or legacy session without turn_ids\n"
        "  404 — session not found"
    ),
)
def edit_message(
    session_id: str,
    turn_id: str,
    request: MessageEditRequest,
    editor: MessageEditService = Depends(get_message_editor),
) -> MessageEditResponse:
    """Edit the content of a single chat message identified by turn_id."""
    try:
        editor.edit_message(
            session_id=session_id,
            turn_id=turn_id,
            new_content=request.new_content,
        )
    except EditError as exc:
        detail = str(exc)
        status = 404 if "not found" in detail else 400
        raise HTTPException(status_code=status, detail=detail) from exc
    return MessageEditResponse(updated=True, turn_id=turn_id)


@app.delete(
    "/api/sessions/{session_id}/messages/{turn_id}",
    response_model=MessageDeleteResponse,
    summary="Delete a message from the conversation",
    description=(
        "Remove the message identified by ``turn_id`` from the conversation "
        "history.  Pass ``?delete_pair=true`` to also remove the immediately "
        "following message (useful for removing a user+assistant turn together).\n\n"
        "Both the display layer and the LLM API history are updated atomically.\n\n"
        "HTTP status codes:\n"
        "  200 — deletion applied\n"
        "  400 — turn_id not found or legacy session without turn_ids\n"
        "  404 — session not found"
    ),
)
def delete_message(
    session_id: str,
    turn_id: str,
    delete_pair: bool = Query(False, description="Also delete the next paired message"),
    editor: MessageEditService = Depends(get_message_editor),
) -> MessageDeleteResponse:
    """Delete a single chat message (optionally with its paired response)."""
    try:
        editor.delete_message(
            session_id=session_id,
            turn_id=turn_id,
            delete_pair=delete_pair,
        )
    except EditError as exc:
        detail = str(exc)
        status = 404 if "not found" in detail else 400
        raise HTTPException(status_code=status, detail=detail) from exc
    return MessageDeleteResponse(deleted=True, turn_id=turn_id, delete_pair=delete_pair)


@app.post(
    "/api/sessions/{session_id}/messages/truncate",
    response_model=TruncateResponse,
    summary="Truncate the last N turn-pairs from the conversation",
    description=(
        "Remove the last ``n`` complete turn-pairs (user + assistant) from the "
        "tail of the conversation.  Use this to trim context before sending a "
        "new message, or to discard a sequence of bad LLM responses.\n\n"
        "Both the display layer and the LLM API history are updated atomically.\n\n"
        "HTTP status codes:\n"
        "  200 — truncation applied\n"
        "  400 — n < 1 or n exceeds available pairs\n"
        "  404 — session not found"
    ),
)
def truncate_messages(
    session_id: str,
    request: TruncateRequest,
    editor: MessageEditService = Depends(get_message_editor),
) -> TruncateResponse:
    """Remove the last N turn-pairs from the conversation tail."""
    try:
        editor.truncate_turns(session_id=session_id, n=request.n)
    except EditError as exc:
        detail = str(exc)
        status = 404 if "not found" in detail else 400
        raise HTTPException(status_code=status, detail=detail) from exc
    return TruncateResponse(truncated=True, turns_removed=request.n)


# ---------------------------------------------------------------------------
# Session-scoped system prompt override endpoints
# ---------------------------------------------------------------------------

@app.get(
    "/api/sessions/{session_id}/system-prompt",
    response_model=SystemPromptResponse,
    summary="Get the session-scoped system prompt override",
    description=(
        "Returns the system prompt currently stored for this session.  "
        "This is either the original prompt used when the session was created "
        "or a user-applied override.\n\n"
        "``null`` means no override has been set (the next chat turn will use "
        "the PromptManager-resolved prompt for the selected mode).\n\n"
        "HTTP status codes:\n"
        "  200 — always succeeds for known sessions\n"
        "  404 — session not found"
    ),
)
def get_system_prompt(
    session_id: str,
    editor: MessageEditService = Depends(get_message_editor),
) -> SystemPromptResponse:
    """
    Retrieve the session-scoped system prompt (or null if unset).

    Returns null for brand-new sessions that have no messages yet — this
    is not an error; the next chat turn will use the mode-resolved default.
    """
    system_prompt = editor.get_system_prompt(session_id)
    return SystemPromptResponse(session_id=session_id, system_prompt=system_prompt)


@app.patch(
    "/api/sessions/{session_id}/system-prompt",
    response_model=SystemPromptUpdateResponse,
    summary="Override the session-scoped system prompt",
    description=(
        "Temporarily replace the system prompt for this specific session without "
        "editing any ``.md`` file.  The change only affects **this session** — "
        "other sessions and the PromptManager cache are unaffected.\n\n"
        "The override takes effect on the **next** message sent in this session.  "
        "Pass an empty string to clear the override (reverts to mode-resolved prompt).\n\n"
        "HTTP status codes:\n"
        "  200 — override applied\n"
        "  404 — session not found"
    ),
)
def update_system_prompt(
    session_id: str,
    request: SystemPromptUpdateRequest,
    editor: MessageEditService = Depends(get_message_editor),
) -> SystemPromptUpdateResponse:
    """
    Set or clear the session-scoped system prompt override.

    Safe to call on a brand-new session with no messages yet — the session
    row is created automatically so the prompt is ready for the first turn.
    """
    editor.update_system_prompt(
        session_id=session_id,
        system_prompt=request.system_prompt,
    )
    return SystemPromptUpdateResponse(updated=True)


# ---------------------------------------------------------------------------
# File-management endpoints
# ---------------------------------------------------------------------------

@app.get("/api/files", response_model=list[FileListItem])
def list_files() -> list[FileListItem]:
    if not settings.data_dir.exists():
        return []
    return [
        FileListItem(path=p.relative_to(settings.data_dir).as_posix(), name=p.name)
        for p in sorted(settings.data_dir.rglob("*.md"))
    ]


@app.get("/api/files/{filepath:path}", response_model=FileReadResponse)
def read_file_endpoint(filepath: str) -> FileReadResponse:
    resolved = _resolve_data_path(filepath)
    if not resolved.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {filepath}")
    return FileReadResponse(filepath=filepath, content=resolved.read_text(encoding="utf-8"))


@app.put("/api/files/{filepath:path}")
def write_file_endpoint(filepath: str, request: FileWriteRequest) -> dict:
    resolved = _resolve_data_path(filepath)
    if not resolved.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {filepath}")
    resolved.write_text(request.content, encoding="utf-8")
    return {"success": f"Saved {filepath}."}


@app.post("/api/files/append")
def append_to_file_endpoint(request: FileAppendRequest) -> dict:
    """Appends a snippet to a Markdown file (Highlight → Add to Docs)."""
    _resolve_data_path(request.filepath)  # path-traversal guard only
    result = append_to_file(request.filepath, request.content)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.post(
    "/api/files/revert/{revert_id}",
    response_model=RevertResponse,
    summary="Revert a file mutation made by the agent",
    description=(
        "Restores the file to its pre-mutation state using the snapshot "
        "identified by *revert_id*.  The backup is deleted after a successful "
        "revert so the same ID cannot be used twice."
    ),
)
def revert_file_edit(revert_id: str) -> RevertResponse:
    """
    F03 — API-Native Snapshot Pattern.

    Reads the backup JSON stored at ``settings.data_dir/.backups/{revert_id}.json``,
    validates that the target path is inside ``data_dir`` (path-traversal guard),
    and restores the file.

    HTTP status codes:
      200 — revert succeeded
      400 — backup is malformed, or the stored path is outside data_dir
      404 — no backup found for this revert_id
    """
    backup_file = settings.data_dir / ".backups" / f"{revert_id}.json"

    if not backup_file.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Backup not found or already reverted: {revert_id}",
        )

    # --- Parse backup JSON ---------------------------------------------------
    try:
        import json as _json
        state = _json.loads(backup_file.read_text(encoding="utf-8"))
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Backup file is malformed: {exc}",
        ) from exc

    # --- Path-traversal guard on the stored filepath ------------------------
    stored_filepath: str = state.get("filepath", "")
    try:
        target_resolved = Path(stored_filepath).resolve()
        data_dir_resolved = settings.data_dir.resolve()
        if not str(target_resolved).startswith(str(data_dir_resolved)):
            raise HTTPException(
                status_code=400,
                detail="Backup references a path outside the data directory.",
            )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Could not validate backup path: {exc}",
        ) from exc

    # --- Delegate restore to the service layer ------------------------------
    result = revert_backup(revert_id=revert_id, backup_dir=settings.data_dir)

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return RevertResponse(success=result["success"], message=result["message"])


@app.get("/api/repo-map")
def repo_map_endpoint() -> dict:
    """Returns the structured repo map (headings only) for the context sidebar."""
    result = get_repo_map(base_dir=str(settings.data_dir))
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    return result


# ---------------------------------------------------------------------------
# Notes endpoints
# ---------------------------------------------------------------------------

@app.post(
    "/api/sessions/{session_id}/notes",
    response_model=NoteResponse,
    status_code=201,
)
def create_note(
    session_id: str,
    request: NoteCreateRequest,
    note_repo: NoteRepository = Depends(get_note_repo),
) -> NoteResponse:
    """
    Saves a text selection from a chat message as a note scoped to *session_id*.

    Returns 404 when the session does not exist.
    Returns 422 when *selected_text* is blank (FastAPI / Pydantic validation).
    Returns 400 when the DB layer rejects the payload (e.g. empty after strip).
    """
    try:
        note = note_repo.add_note(
            session_id=session_id,
            selected_text=request.selected_text,
            source_role=request.source_role,
            note=request.note,
        )
    except ValueError as exc:
        detail = str(exc)
        status = 404 if "not found" in detail.lower() else 400
        raise HTTPException(status_code=status, detail=detail) from exc
    return NoteResponse(**note)


@app.get(
    "/api/sessions/{session_id}/notes",
    response_model=list[NoteResponse],
)
def list_notes(
    session_id: str,
    note_repo: NoteRepository = Depends(get_note_repo),
) -> list[NoteResponse]:
    return [NoteResponse(**n) for n in note_repo.list_notes(session_id)]


@app.delete(
    "/api/sessions/{session_id}/notes/{note_id}",
    status_code=204,
)
def delete_note(
    session_id: str,
    note_id: str,
    note_repo: NoteRepository = Depends(get_note_repo),
) -> None:
    deleted = note_repo.delete_note(note_id=note_id, session_id=session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Note not found: {note_id}")


# ---------------------------------------------------------------------------
# F05 — Prompt management endpoints
# ---------------------------------------------------------------------------

@app.get(
    "/api/prompts/modes",
    response_model=list[PromptModeResponse],
    summary="List available prompt modes",
    description=(
        "Returns metadata for all backend-managed prompt modes.\n\n"
        "Each item contains ``id``, ``label``, and ``eyebrow`` — **never** "
        "the full ``content`` string — so the frontend can render the mode "
        "switcher without receiving the system prompt text."
    ),
)
def get_prompt_modes(
    pm: PromptManager = Depends(get_prompt_manager),
) -> list[PromptModeResponse]:
    """
    F05 — Returns the list of available prompt modes for the frontend mode switcher.

    HTTP status codes:
      200 — always succeeds (returns empty list when prompts_dir is missing)
    """
    return [PromptModeResponse(**m) for m in pm.get_all_modes()]


@app.get(
    "/api/prompts/modes/{mode_id}",
    response_model=PromptModeDetail,
    summary="Get full prompt content for one mode",
    description=(
        "Returns the complete resolved system instruction for *mode_id* "
        "(``base_agent_rules.md`` + mode body concatenated). "
        "Intended for the frontend expand-to-inspect panel. "
        "Returns 404 when *mode_id* is not registered."
    ),
)
def get_prompt_mode_detail(
    mode_id: str,
    pm: PromptManager = Depends(get_prompt_manager),
) -> PromptModeDetail:
    """
    F05 — Returns the full prompt text for a single mode.

    HTTP status codes:
      200 — mode found; content is the full resolved system instruction
      404 — mode_id not registered in PromptManager
    """
    all_modes = {m["id"]: m for m in pm.get_all_modes()}
    if mode_id not in all_modes:
        raise HTTPException(
            status_code=404,
            detail=f"Prompt mode not found: {mode_id}",
        )
    content = pm.get_system_instruction(mode_id)
    meta = all_modes[mode_id]
    return PromptModeDetail(
        id=meta["id"],
        label=meta["label"],
        eyebrow=meta["eyebrow"],
        content=content,
    )


@app.post(
    "/api/prompts/reload",
    summary="Hot-reload prompt files",
    description=(
        "Re-reads all Markdown files in ``prompts/`` and refreshes the "
        "in-memory cache without restarting the server.\n\n"
        "Use this after editing a ``.md`` prompt file to pick up the changes "
        "instantly.  The next ``/api/chat`` call will use the updated prompt."
    ),
)
def reload_prompts(
    pm: PromptManager = Depends(get_prompt_manager),
) -> dict:
    """
    F05 — Hot-reload endpoint.

    HTTP status codes:
      200 — reload succeeded
    """
    pm.reload_prompts()
    return {"success": True}


# ---------------------------------------------------------------------------
# Chat endpoint
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Provider catalogue  (static — updated here when new models are released)
# ---------------------------------------------------------------------------

_PROVIDER_CATALOGUE: list[ProviderInfo] = [
    ProviderInfo(
        id="gemini",
        label="Google Gemini",
        default_model="gemini-2.5-flash",
        models=[
            ModelInfo(id="gemini-2.5-flash",       label="Gemini 2.5 Flash",       context_k=1000),
            ModelInfo(id="gemini-2.5-pro",          label="Gemini 2.5 Pro",          context_k=1000),
            ModelInfo(id="gemini-2.0-flash",        label="Gemini 2.0 Flash",        context_k=1000),
            ModelInfo(id="gemini-2.0-flash-lite",   label="Gemini 2.0 Flash Lite",   context_k=1000),
        ],
    ),
    ProviderInfo(
        id="anthropic",
        label="Anthropic Claude",
        default_model="claude-sonnet-4-5",
        models=[
            ModelInfo(id="claude-opus-4-5",    label="Claude Opus 4.5",    context_k=200),
            ModelInfo(id="claude-sonnet-4-5",  label="Claude Sonnet 4.5",  context_k=200),
            ModelInfo(id="claude-haiku-3-5",   label="Claude Haiku 3.5",   context_k=200),
        ],
    ),
]

# index for O(1) lookup: provider_id -> ProviderInfo
_PROVIDER_MAP: dict[str, ProviderInfo] = {p.id: p for p in _PROVIDER_CATALOGUE}


def _default_model_for(provider_id: str) -> str:
    """Return the catalogue default model for a provider, falling back to the
    matching settings field when the provider is not in the catalogue."""
    entry = _PROVIDER_MAP.get(provider_id)
    if entry:
        return entry.default_model
    # Fallback: read the appropriate settings field
    if provider_id == "gemini":
        return settings.gemini_model
    if provider_id == "anthropic":
        return settings.anthropic_model
    return ""


@app.get(
    "/api/providers",
    response_model=list[ProviderInfo],
    summary="List available LLM providers and their model catalogues",
    description=(
        "Returns metadata for every LLM backend the server knows about, "
        "including supported model ids, display labels, and context window "
        "sizes.\n\n"
        "The frontend uses this to populate the provider/model picker.  "
        "The list is static — it changes only when the server is updated "
        "to support new models."
    ),
)
def list_providers() -> list[ProviderInfo]:
    """
    Returns the full provider + model catalogue.

    HTTP status codes:
      200 — always succeeds
    """
    return _PROVIDER_CATALOGUE


@app.get(
    "/api/providers/active",
    response_model=ActiveProvider,
    summary="Get the server's currently configured default provider + model",
    description=(
        "Returns the provider id and model id that will be used when "
        "``POST /api/chat`` is called without explicit ``provider``/``model`` "
        "fields.  Driven by the ``LLM_PROVIDER`` and ``*_MODEL`` environment "
        "variables on the server.\n\n"
        "The frontend uses this to pre-select the correct option in the "
        "provider picker on first load."
    ),
)
def get_active_provider() -> ActiveProvider:
    """
    Returns the server-configured default.

    HTTP status codes:
      200 — always succeeds
    """
    return ActiveProvider(
        provider=settings.llm_provider,
        model=_default_model_for(settings.llm_provider),
    )


@app.post("/api/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    service: ChatService = Depends(get_chat_service),
    pm: PromptManager = Depends(get_prompt_manager),
) -> ChatResponse:
    """
    Processes a chat message through the Gemini agent and persists state.

    F05 — System instruction resolution
    ------------------------------------
    Priority (highest → lowest):
      1. ``request.system_prompt`` — explicit raw override (legacy / power-user)
      2. ``request.mode_id``       — resolved via PromptManager (new default)

    Context file path resolution
    ----------------------------
    The frontend ``ContextSidebar`` sends ``FileListItem.path`` values that are
    relative to ``data_dir`` (e.g. ``"kuchnia-kroki.md"``).  Before forwarding
    to the agent, each path is resolved to a full absolute path via
    ``_resolve_context_file_paths`` so that ``read_file`` can open the file
    regardless of the server's CWD.

    The synchronous agent call is dispatched to a thread-pool executor so the
    event loop remains free during the (potentially 10–30 s) model call.
    """
    # Resolve the system instruction with the F05 priority rules
    if request.system_prompt is not None:
        # Legacy / explicit override — pass through unchanged
        system_instruction: str | None = request.system_prompt
    else:
        # New path: resolve mode_id → full prompt via PromptManager
        resolved = pm.get_system_instruction(request.mode_id)
        # Use None when the resolved text is empty (missing prompts_dir etc.)
        # so the agent behaves the same as before F05 in degraded environments
        system_instruction = resolved if resolved else None

    # Resolve context file paths: bare filenames → absolute paths under data_dir.
    # This fixes the bug where ContextSidebar sends "file.md" but read_file
    # needs "data/file.md" (or the absolute path).
    resolved_context_files = _resolve_context_file_paths(request.context_files)

    # Validate the requested provider early so we can return HTTP 400
    # (bad request) rather than 500 (server error) for unknown names.
    if request.provider is not None and request.provider not in _PROVIDER_MAP:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unknown provider: '{request.provider}'. "
                f"Supported: {sorted(_PROVIDER_MAP.keys())}"
            ),
        )

    loop = asyncio.get_event_loop()

    try:
        final_text, tool_logs = await loop.run_in_executor(
            None,
            partial(
                service.handle_turn,
                session_id=request.session_id,
                user_message=request.message,
                system_prompt=system_instruction,
                images=(
                    [img.model_dump() for img in request.images]
                    if request.images
                    else None
                ),
                context_files=resolved_context_files,
                provider_name=request.provider,
                model_override=request.model,
            ),
        )
    except Exception as exc:
        logger.exception("agent_error", session_id=request.session_id[:8], error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return ChatResponse(text=final_text, tools_used=tool_logs)


# ---------------------------------------------------------------------------
# Token counting endpoints
# ---------------------------------------------------------------------------

@app.get(
    "/api/sessions/{session_id}/tokens",
    response_model=SessionTokensResponse,
    summary="Count tokens in a stored session",
    description=(
        "Returns the authoritative token count for all turns stored in the "
        "session by calling the Gemini ``count_tokens`` API.\n\n"
        "When the Gemini API is unavailable the endpoint degrades gracefully "
        "to a local heuristic and sets ``fallback_used=true`` in the response "
        "so the client can show an approximate indicator instead of failing.\n\n"
        "An empty session (no turns yet) returns ``total_tokens=0`` without "
        "making any API call.\n\n"
        "HTTP status codes:\n"
        "  200 — always succeeds for known sessions\n"
        "  404 — session not found"
    ),
)
def get_session_token_count(
    session_id: str,
    session_repo: SessionRepository = Depends(get_session_repo),
) -> SessionTokensResponse:
    api_json, _ui_json, system_prompt = session_repo.load_session(session_id)
    # load_session returns ("[]", "[]", None) for unknown sessions — the same
    # as an empty session.  We return 200 with zero tokens, consistent with
    # GET /api/sessions/{id} which also returns 200+empty for unknown IDs.
    estimate = count_session_tokens(api_json, system_prompt=system_prompt)

    return SessionTokensResponse(
        session_id=session_id,
        text_tokens=estimate.text_tokens,
        image_tokens=estimate.image_tokens,
        context_file_tokens=estimate.context_file_tokens,
        system_prompt_tokens=estimate.system_prompt_tokens,
        history_tokens=estimate.history_tokens,
        total_tokens=estimate.total_tokens,
        fallback_used=estimate.fallback_used,
    )


@app.post(
    "/api/tokens/estimate",
    response_model=TokenEstimateResponse,
    summary="Estimate tokens for a pending context",
    description=(
        "Returns a heuristic token estimate for a context that has **not yet "
        "been sent** to the model.  Use this to show an input-token indicator "
        "in the UI before the user presses Send.\n\n"
        "The estimate is calculated locally (no Gemini API call) using a "
        "4-chars-per-token rule for text and a tile-count proxy for images.  "
        "``fallback_used`` is always ``true``.\n\n"
        "Fields:\n"
        "  ``user_message``        — required, the message text\n"
        "  ``images``              — optional list of ``{mime_type, data}`` "
        "base64-encoded images\n"
        "  ``context_files``       — optional list of file paths (resolved "
        "the same way as ``/api/chat``)\n"
        "  ``system_prompt``       — optional system instruction text\n"
        "  ``history_token_count`` — optional prior session token count "
        "(default 0)"
    ),
)
def estimate_pending_tokens(
    request: TokenEstimateRequest,
) -> TokenEstimateResponse:
    # Resolve context file paths the same way as the chat endpoint so token
    # estimates are based on the actual files the agent would read.
    resolved_files = _resolve_context_file_paths(request.context_files)

    estimate = build_pending_context_estimate(
        user_message=request.user_message,
        images=(
            [img.model_dump() for img in request.images]
            if request.images
            else None
        ),
        context_files=resolved_files,
        system_prompt=request.system_prompt,
        history_token_count=request.history_token_count,
    )

    return TokenEstimateResponse(
        text_tokens=estimate.text_tokens,
        image_tokens=estimate.image_tokens,
        context_file_tokens=estimate.context_file_tokens,
        system_prompt_tokens=estimate.system_prompt_tokens,
        history_tokens=estimate.history_tokens,
        total_tokens=estimate.total_tokens,
        fallback_used=estimate.fallback_used,
    )
