# src/main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uuid
import json

from src.agent import process_chat_turn
from src.db import DatabaseManager
from src.serializers import dehydrate_history, hydrate_history

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
class ChatRequest(BaseModel):
    session_id: str
    message: str
    system_prompt: Optional[str] = None


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


@app.post("/api/sessions/{session_id}/fork", response_model=ForkResponse)
def fork_session(session_id: str, request: ForkRequest):
    """Forks a session at the given turn_index, returning the new session ID."""
    try:
        new_id = db.fork_session(session_id, request.turn_index)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return ForkResponse(new_session_id=new_id)


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """Processes a chat message and saves the state."""

    # 1. Load existing history from DB
    api_json, ui_json = db.load_session(request.session_id)
    history = hydrate_history(api_json)
    ui_messages = json.loads(ui_json) if ui_json != "[]" else []

    # 2. Add user message to UI state
    ui_messages.append({"role": "user", "content": request.message})

    # 3. Process with Agent
    try:
        final_text, tool_logs = process_chat_turn(
            user_message=request.message,
            history=history,
            system_instruction=request.system_prompt
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
