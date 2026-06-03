"""
api/notes.py
────────────
Note management endpoints.

Routes:
  POST   /api/sessions/{id}/notes        → create note
  GET    /api/sessions/{id}/notes        → list notes
  DELETE /api/sessions/{id}/notes/{nid}  → delete note
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from src.dependencies import get_note_repo
from src.repositories import NoteRepository
from src.schemas import NoteCreateRequest, NoteResponse

router = APIRouter()


@router.post(
    "/api/sessions/{session_id}/notes",
    response_model=NoteResponse,
    status_code=201,
)
def create_note(
    session_id: str,
    request: NoteCreateRequest,
    note_repo: NoteRepository = Depends(get_note_repo),
) -> NoteResponse:
    """Saves a text selection from a chat message as a note."""
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


@router.get(
    "/api/sessions/{session_id}/notes",
    response_model=list[NoteResponse],
)
def list_notes(
    session_id: str,
    note_repo: NoteRepository = Depends(get_note_repo),
) -> list[NoteResponse]:
    return [NoteResponse(**n) for n in note_repo.list_notes(session_id)]


@router.delete(
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
