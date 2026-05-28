# src/main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uuid
import json
from pathlib import Path

from src.agent import process_chat_turn
from src.db import DatabaseManager
from src.prompt_logger import log_prompt
from src.serializers import dehydrate_history, hydrate_history
from src.tools.file_ops import append_to_file
from src.tools.repo_map import get_repo_map

DATA_DIR = Path("data")

app = FastAPI(title="Kitchen Cabinet Agent API")

# Allow Svelte frontend to talk to this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to localhost:5173
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db = DatabaseManager()


# --- Pydantic Models (Data Validation) ---

class ChatImagePart(BaseModel):
    mime_type: str   # e.g. "image/jpeg"
    data: str        # base64-encoded bytes


class ChatRequest(BaseModel):
    session_id: str
    message: str
    system_prompt: Optional[str] = None
    images: Optional[List[ChatImagePart]] = None  # base64 image attachments
    context_files: Optional[List[str]] = None     # filepaths to inject as context


class ToolLog(BaseModel):
    name: str
    args: Dict[str, Any]
    result: Dict[str, Any]


class ChatResponse(BaseModel):
    text: str
    tools_used: List[ToolLog]


class ForkRequest(BaseModel):
    turn_index: int


class ForkResponse(BaseModel):
    new_session_id: str


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


# --- API Endpoints ---

@app.get("/api/sessions")
def get_sessions():
    """Returns a list of all saved chat sessions."""
    return db.list_sessions()


@app.get("/api/sessions/{session_id}")
def get_session(session_id: str):
    """Loads a specific chat session."""
    api_json, ui_json = db.load_session(session_id)
    if not ui_json or ui_json == "[]":
        return {"ui_messages": []}
    return {"ui_messages": json.loads(ui_json)}


@app.get("/api/sessions/{session_id}/export", response_class=PlainTextResponse)
def export_session(session_id: str):
    """Exports a session as a Markdown document."""
    try:
        markdown = db.export_session(session_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return PlainTextResponse(content=markdown, media_type="text/markdown")


@app.post("/api/sessions/{session_id}/fork", response_model=ForkResponse)
def fork_session(session_id: str, request: ForkRequest):
    """Forks a session at the given turn_index, returning the new session ID."""
    try:
        new_id = db.fork_session(session_id, request.turn_index)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return ForkResponse(new_session_id=new_id)


# ---------------------------------------------------------------------------
# File Management Endpoints
# ---------------------------------------------------------------------------

def _resolve_data_path(filepath: str) -> Path:
    """
    Resolves `filepath` relative to DATA_DIR and guards against path traversal.
    Raises HTTPException(400) if the resolved path escapes DATA_DIR.
    """
    resolved = (DATA_DIR / filepath).resolve()
    if not str(resolved).startswith(str(DATA_DIR.resolve())):
        raise HTTPException(status_code=400, detail="Path traversal not allowed.")
    return resolved


@app.get("/api/files", response_model=List[FileListItem])
def list_files():
    """Returns a flat list of all markdown files in the data/ directory.

    The `path` field is relative to DATA_DIR (e.g. '03_Finishes/paint.md'),
    so the frontend can pass it directly to GET/PUT /api/files/{path}.
    """
    if not DATA_DIR.exists():
        return []
    items = [
        FileListItem(path=p.relative_to(DATA_DIR).as_posix(), name=p.name)
        for p in sorted(DATA_DIR.rglob("*.md"))
    ]
    return items


@app.get("/api/files/{filepath:path}", response_model=FileReadResponse)
def read_file_endpoint(filepath: str):
    """Returns the raw text content of a single markdown file."""
    resolved = _resolve_data_path(filepath)
    if not resolved.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {filepath}")
    return FileReadResponse(filepath=filepath, content=resolved.read_text(encoding="utf-8"))


@app.put("/api/files/{filepath:path}")
def write_file_endpoint(filepath: str, request: FileWriteRequest):
    """Overwrites a markdown file with new content (manual editor save)."""
    resolved = _resolve_data_path(filepath)
    if not resolved.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {filepath}")
    resolved.write_text(request.content, encoding="utf-8")
    return {"success": f"Saved {filepath}."}


@app.post("/api/files/append")
def append_to_file_endpoint(request: FileAppendRequest):
    """Appends a snippet to a markdown file. Used by Highlight -> Add to Docs."""
    _resolve_data_path(request.filepath)  # path-traversal guard only
    result = append_to_file(request.filepath, request.content)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.get("/api/repo-map")
def repo_map_endpoint():
    """Returns the structured repo map (headers only) for the context sidebar."""
    result = get_repo_map()
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    return result


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------

@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """Processes a chat message and saves the state."""

    # 1. Load existing history from DB
    api_json, ui_json = db.load_session(request.session_id)
    history = hydrate_history(api_json)
    ui_messages = json.loads(ui_json) if ui_json != "[]" else []

    # 2. Add user message to UI state
    ui_messages.append({"role": "user", "content": request.message})

    # Log the prompt to the running prompt log
    log_prompt(request.message)

    # 3. Process with Agent
    try:
        final_text, tool_logs = process_chat_turn(
            user_message=request.message,
            history=history,
            system_instruction=request.system_prompt,
            images=[img.model_dump() for img in request.images] if request.images else None,
            context_files=request.context_files or None,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # 4. Add assistant response to UI state
    ui_messages.append({
        "role": "assistant",
        "content": final_text,
        "tools": tool_logs
    })

    # 5. Save back to DB
    title = ui_messages[0]["content"][:30] + "..." if len(ui_messages[0]["content"]) > 30 else ui_messages[0]["content"]
    db.save_session(
        session_id=request.session_id,
        title=title,
        api_history_json=dehydrate_history(history),
        ui_history_json=json.dumps(ui_messages)
    )

    # 6. Return response to frontend
    return ChatResponse(text=final_text, tools_used=tool_logs)
