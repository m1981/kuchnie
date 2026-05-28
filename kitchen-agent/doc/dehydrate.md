sequenceDiagram
autonumber
actor User
participant UI as Streamlit UI (app.py)
participant Agent as Agent (agent.py)
participant Gemini as Gemini API
participant DataMgr as DataManager (db.py + serializers)
participant DB as SQLite DB

    %% ==========================================
    %% SCENARIO 1: POSITIVE - Standard Chat & Save
    %% ==========================================
    rect rgb(230, 245, 230)
        Note over User, DB: SCENARIO 1: Standard Chat Turn & Persistence
        User->>UI: Types message & clicks Send
        UI->>Agent: process_chat_turn(msg, history)

        Agent->>Gemini: generate_content(history)
        Gemini-->>Agent: Response (Text or Tool Call)

        Agent-->>UI: final_text, tool_logs, updated_history
        UI-->>User: Renders chat bubbles & expanders

        Note over UI, DB: Background Persistence
        UI->>DataMgr: save_session(session_id, updated_history)
        DataMgr->>DataMgr: dehydrate(updated_history) -> JSON
        DataMgr->>DB: UPDATE sessions SET history = JSON
    end

    %% ==========================================
    %% SCENARIO 2: POSITIVE - Forking a Chat
    %% ==========================================
    rect rgb(230, 240, 255)
        Note over User, DB: SCENARIO 2: Branching / Forking a Chat
        User->>UI: Clicks "✂️ Fork from Message 4"
        UI->>DataMgr: fork_session(old_id, slice_index=4)

        DataMgr->>DB: SELECT history FROM sessions WHERE id = old_id
        DB-->>DataMgr: raw_json

        DataMgr->>DataMgr: Slice JSON array [:4]
        DataMgr->>DB: INSERT INTO sessions (new_id, sliced_json)
        DB-->>DataMgr: new_session_id

        DataMgr->>DataMgr: hydrate(sliced_json) -> List[types.Content]
        DataMgr-->>UI: new_session_id, hydrated_history

        UI->>UI: st.session_state.history = hydrated_history
        UI-->>User: Renders new branched chat UI
    end

    %% ==========================================
    %% SCENARIO 3: EDGE CASE - Corrupted DB State
    %% ==========================================
    rect rgb(255, 230, 230)
        Note over User, DB: SCENARIO 3: EDGE - Corrupted History Load
        User->>UI: Selects "Old Chat" from Sidebar
        UI->>DataMgr: load_session(old_id)
        DataMgr->>DB: SELECT history
        DB-->>DataMgr: raw_json (Missing thought_signature!)

        alt Hydration Fails
            DataMgr->>DataMgr: hydrate(raw_json)
            Note right of DataMgr: Validation Error: Missing required bytes
            DataMgr-->>UI: Raise HydrationError
            UI-->>User: st.error("Chat corrupted. Cannot load.")
        else Graceful Degradation (Architectural Choice)
            DataMgr->>DataMgr: hydrate(raw_json)
            Note right of DataMgr: Strips tool calls, keeps only text
            DataMgr-->>UI: partial_hydrated_history
            UI-->>User: st.warning("Some tool context lost, but text recovered.")
        end
    end

    %% ==========================================
    %% SCENARIO 4: EDGE CASE - Attachments
    %% ==========================================
    rect rgb(255, 245, 220)
        Note over User, DB: SCENARIO 4: EDGE - Attachment Handling
        User->>UI: Uploads 50MB PDF & clicks Send

        UI->>UI: Validate Attachment (Size, MIME type)
        alt File too large or unsupported
            UI-->>User: st.toast("File exceeds 20MB limit or unsupported format")
        else File Valid
            UI->>Agent: process_chat_turn(msg, history, attachments=[bytes])
            Agent->>Agent: Convert bytes to types.Part(mime_type)
            Agent->>Gemini: generate_content(history + attachments)
            Gemini-->>Agent: Response
            Agent-->>UI: final_text
            UI-->>User: Renders response
        end
    end
