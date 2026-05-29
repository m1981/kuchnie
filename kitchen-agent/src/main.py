"""
src/main.py
===========
FastAPI application — HTTP layer only.

Responsibilities
----------------
* Declare routes and Pydantic request / response models.
* Validate input and translate service/domain errors into HTTP responses.
* Delegate all business logic to `ChatService` and Repositories.
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
from src.tools.file_ops import append_to_file, revert_backup
from src.tools.repo_map import get_repo_map
from src.logger import setup_logging

# --- Clean imports for Schemas and Repositories ---
from src.schemas import (
    ChatRequest, ChatResponse, ForkRequest, ForkResponse,
    SessionSummary, SessionNode, FileReadResponse, FileWriteRequest,
    FileAppendRequest, FileListItem, NoteCreateRequest, NoteResponse,
    RevertResponse,
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
    _, ui_json = session_repo.load_session(session_id)
    ui_messages = json.loads(ui_json) if ui_json and ui_json != "[]" else []
    return {"ui_messages": ui_messages}


@app.get("/api/sessions/{session_id}/export", response_class=PlainTextResponse)
def export_session(
    session_id: str,
    session_repo: SessionRepository = Depends(get_session_repo),
) -> PlainTextResponse:
    try:
        markdown = session_repo.export_session(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return PlainTextResponse(content=markdown, media_type="text/markdown")


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
# Chat endpoint
# ---------------------------------------------------------------------------

@app.post("/api/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    service: ChatService = Depends(get_chat_service),
) -> ChatResponse:
    """
    Processes a chat message through the Gemini agent and persists state.

    The synchronous agent call is dispatched to a thread-pool executor so the
    event loop remains free during the (potentially 10–30 s) model call.
    """
    loop = asyncio.get_event_loop()

    try:
        final_text, tool_logs = await loop.run_in_executor(
            None,
            partial(
                service.handle_turn,
                session_id=request.session_id,
                user_message=request.message,
                system_prompt=request.system_prompt,
                images=(
                    [img.model_dump() for img in request.images]
                    if request.images
                    else None
                ),
                context_files=request.context_files or None,
            ),
        )
    except Exception as exc:
        logger.exception("agent_error", session_id=request.session_id[:8], error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return ChatResponse(text=final_text, tools_used=tool_logs)
