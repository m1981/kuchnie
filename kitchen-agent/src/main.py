"""
src/main.py
===========
FastAPI application — HTTP layer only.

Responsibilities
----------------
* Declare routes and Pydantic request / response models.
* Validate input and translate service/domain errors into HTTP responses.
* Delegate all business logic to ``ChatService`` and ``DatabaseManager``.

No business logic lives here.

Async strategy
--------------
The Gemini SDK call and all SQLite operations are synchronous (blocking I/O).
We run them inside ``asyncio.get_event_loop().run_in_executor(None, ...)`` so
that the FastAPI event loop is never blocked and can serve other requests while
the model is thinking.
"""

import asyncio
import json
import logging
from functools import partial
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from src.chat_service import ChatService
from src.config import settings
from src.db import DatabaseManager
from src.tools.file_ops import append_to_file
from src.tools.repo_map import get_repo_map

logger = logging.getLogger(__name__)

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

def get_db() -> DatabaseManager:
    """FastAPI dependency: returns a DatabaseManager instance."""
    return DatabaseManager()


def get_chat_service(db: DatabaseManager = Depends(get_db)) -> ChatService:
    """FastAPI dependency: returns a ChatService wired to the DB."""
    return ChatService(db)


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class ChatImagePart(BaseModel):
    mime_type: str  # e.g. "image/jpeg"
    data: str       # base64-encoded bytes


class ChatRequest(BaseModel):
    session_id: str
    message: str
    system_prompt: str | None = None
    images: list[ChatImagePart] | None = None
    context_files: list[str] | None = None


class ToolLog(BaseModel):
    name: str
    args: dict[str, Any]
    result: dict[str, Any]


class ChatResponse(BaseModel):
    text: str
    tools_used: list[ToolLog]


class ForkRequest(BaseModel):
    turn_index: int


class ForkResponse(BaseModel):
    new_session_id: str


class SessionSummary(BaseModel):
    """Flat representation of a session as returned by GET /api/sessions."""

    id: str
    title: str | None
    updated_at: str | None
    parent_id: str | None = None
    fork_turn_index: int | None = None
    root_id: str | None = None
    archived_at: str | None = None


class SessionNode(BaseModel):
    """One node in the session tree returned by GET /api/sessions/tree."""

    id: str
    title: str | None
    updated_at: str | None
    parent_id: str | None = None
    fork_turn_index: int | None = None
    root_id: str | None = None
    archived_at: str | None = None
    children: list["SessionNode"] = []


# Required so Pydantic can resolve the self-referential type.
SessionNode.model_rebuild()


class FileReadResponse(BaseModel):
    filepath: str
    content: str


class FileWriteRequest(BaseModel):
    content: str


class FileAppendRequest(BaseModel):
    filepath: str
    content: str


class FileListItem(BaseModel):
    path: str
    name: str


class NoteCreateRequest(BaseModel):
    selected_text: str
    source_role: str  # "user" | "assistant"
    note: str = ""


class NoteResponse(BaseModel):
    id: str
    session_id: str
    selected_text: str
    note: str
    source_role: str
    created_at: str


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
    include_archived: bool = Query(False, description="Include archived sessions in the list."),
    db: DatabaseManager = Depends(get_db),
) -> list[SessionSummary]:
    """
    Returns a flat list of all sessions ordered by most-recently updated.

    Archived sessions are hidden by default; pass ``?include_archived=true``
    to surface them (e.g. for an 'archived chats' management screen).
    """
    return [SessionSummary(**row) for row in db.list_sessions(include_archived=include_archived)]


@app.get("/api/sessions/tree", response_model=list[SessionNode])
def get_session_tree(
    include_archived: bool = Query(True, description="Include archived sessions to preserve tree structure."),
    db: DatabaseManager = Depends(get_db),
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

    return [_build(root) for root in db.get_session_tree(include_archived=include_archived)]


@app.get("/api/sessions/{session_id}")
def get_session(
    session_id: str,
    db: DatabaseManager = Depends(get_db),
) -> dict:
    """Loads a specific chat session."""
    _, ui_json = db.load_session(session_id)
    ui_messages = json.loads(ui_json) if ui_json and ui_json != "[]" else []
    return {"ui_messages": ui_messages}


@app.get(
    "/api/sessions/{session_id}/export",
    response_class=PlainTextResponse,
)
def export_session(
    session_id: str,
    db: DatabaseManager = Depends(get_db),
) -> PlainTextResponse:
    """Exports a session as a Markdown document."""
    try:
        markdown = db.export_session(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return PlainTextResponse(content=markdown, media_type="text/markdown")


@app.post("/api/sessions/{session_id}/fork", response_model=ForkResponse)
def fork_session(
    session_id: str,
    request: ForkRequest,
    db: DatabaseManager = Depends(get_db),
) -> ForkResponse:
    """Forks a session at *turn_index*, returning the new session ID."""
    try:
        new_id = db.fork_session(session_id, request.turn_index)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ForkResponse(new_session_id=new_id)


@app.patch("/api/sessions/{session_id}/archive", status_code=200)
def archive_session(
    session_id: str,
    db: DatabaseManager = Depends(get_db),
) -> dict:
    """
    Soft-archives a session.  The session is hidden from normal listings but
    all data and lineage are preserved.  Returns 404 when the session does not
    exist or is already archived.
    """
    archived = db.archive_session(session_id)
    if not archived:
        raise HTTPException(
            status_code=404,
            detail=f"Session not found or already archived: {session_id}",
        )
    return {"archived": True, "session_id": session_id}


@app.delete("/api/sessions/{session_id}/archive", status_code=200)
def unarchive_session(
    session_id: str,
    db: DatabaseManager = Depends(get_db),
) -> dict:
    """
    Reverses an archive.  Returns 404 when the session does not exist or is
    not currently archived.
    """
    unarchived = db.unarchive_session(session_id)
    if not unarchived:
        raise HTTPException(
            status_code=404,
            detail=f"Session not found or not archived: {session_id}",
        )
    return {"archived": False, "session_id": session_id}


@app.delete("/api/sessions/{session_id}", status_code=204)
def delete_session(
    session_id: str,
    db: DatabaseManager = Depends(get_db),
) -> None:
    """
    Permanently deletes a session and all its notes.

    Returns 404 when the session does not exist.
    Returns 409 Conflict when the session has living child sessions — delete
    all descendants (leaf-first) before deleting the parent.
    """
    try:
        db.delete_session(session_id)
    except ValueError as exc:
        detail = str(exc)
        status = 409 if "child" in detail.lower() else 404
        raise HTTPException(status_code=status, detail=detail) from exc


# ---------------------------------------------------------------------------
# File-management endpoints
# ---------------------------------------------------------------------------

@app.get("/api/files", response_model=list[FileListItem])
def list_files() -> list[FileListItem]:
    """Returns a flat list of all Markdown files in the data directory."""
    if not settings.data_dir.exists():
        return []
    return [
        FileListItem(
            path=p.relative_to(settings.data_dir).as_posix(),
            name=p.name,
        )
        for p in sorted(settings.data_dir.rglob("*.md"))
    ]


@app.get("/api/files/{filepath:path}", response_model=FileReadResponse)
def read_file_endpoint(filepath: str) -> FileReadResponse:
    """Returns the raw text content of a single Markdown file."""
    resolved = _resolve_data_path(filepath)
    if not resolved.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {filepath}")
    return FileReadResponse(
        filepath=filepath,
        content=resolved.read_text(encoding="utf-8"),
    )


@app.put("/api/files/{filepath:path}")
def write_file_endpoint(filepath: str, request: FileWriteRequest) -> dict:
    """Overwrites a Markdown file with new content (manual editor save)."""
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
    db: DatabaseManager = Depends(get_db),
) -> NoteResponse:
    """
    Saves a text selection from a chat message as a note scoped to *session_id*.

    Returns 404 when the session does not exist.
    Returns 422 when *selected_text* is blank (FastAPI / Pydantic validation).
    Returns 400 when the DB layer rejects the payload (e.g. empty after strip).
    """
    try:
        note = db.add_note(
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
    db: DatabaseManager = Depends(get_db),
) -> list[NoteResponse]:
    """Returns all notes for *session_id* ordered by creation time (oldest first)."""
    return [NoteResponse(**n) for n in db.list_notes(session_id)]


@app.delete(
    "/api/sessions/{session_id}/notes/{note_id}",
    status_code=204,
)
def delete_note(
    session_id: str,
    note_id: str,
    db: DatabaseManager = Depends(get_db),
) -> None:
    """Deletes a single note.  Returns 404 when the note is not found."""
    deleted = db.delete_note(note_id=note_id, session_id=session_id)
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=f"Note not found: {note_id}",
        )


# ---------------------------------------------------------------------------
# Chat endpoint  (async — runs blocking work in thread-pool executor)
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
        logger.exception("Agent error for session %s", request.session_id[:8])
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return ChatResponse(text=final_text, tools_used=tool_logs)
