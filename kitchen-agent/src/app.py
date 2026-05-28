# src/app.py
import streamlit as st
import uuid
import json
from dotenv import load_dotenv

from agent import process_chat_turn
from db import DatabaseManager
from serializers import dehydrate_history, hydrate_history

load_dotenv()

# NEW: Initialize Database
db = DatabaseManager()

st.set_page_config(page_title="Kitchen Cabinet Agent", layout="wide")

# --- STATE MANAGEMENT ---
# NEW: Track the current session ID
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "history" not in st.session_state:
    st.session_state.history = []

if "ui_messages" not in st.session_state:
    st.session_state.ui_messages = []

# --- SIDEBAR ---
with st.sidebar:
    st.header("Context & Settings")

    template_options = {
        "General Assistant": "You are a helpful assistant for a kitchen cabinet builder. Read files to answer questions, but NEVER edit or create files unless the user explicitly asks you to.",

        "Design Mode": "You are an expert kitchen designer. Focus on ergonomics, spacing, and aesthetics. Always check the repo map for design guidelines. NEVER edit files unless explicitly requested.",

        "Assembly Mode": "You are a master carpenter. Focus on structural integrity, hardware installation, and step-by-step assembly instructions. Answer the user's questions based on the files, but DO NOT modify the files yourself unless told to do so."
    }
    selected_mode = st.selectbox("Prompt Template", list(template_options.keys()))
    current_system_prompt = template_options[selected_mode]

    # --- NEW: Expander to show the raw system prompt ---
    with st.expander("👀 View Active Prompt"):
        st.caption("This is the hidden instruction sent to the LLM:")
        st.info(current_system_prompt)
    # ---------------------------------------------------

    st.divider()
    st.header("Tasks")
    st.checkbox("Design layout")
    st.checkbox("Calculate materials")
    st.checkbox("Order hardware")

    st.divider()

    # --- NEW: PERSISTENCE UI ---
    st.header("💾 Chat History")

    # Save Button
    if st.button("Save Current Chat", use_container_width=True):
        if st.session_state.ui_messages:
            # Generate a title based on the first user message
            first_msg = next((m["content"] for m in st.session_state.ui_messages if m["role"] == "user"), "New Chat")
            title = first_msg[:30] + "..." if len(first_msg) > 30 else first_msg

            # Dehydrate and Save
            api_json = dehydrate_history(st.session_state.history)
            ui_json = json.dumps(st.session_state.ui_messages)

            db.save_session(st.session_state.session_id, title, api_json, ui_json)
            st.toast("Chat saved successfully!", icon="✅")
        else:
            st.toast("Nothing to save yet.", icon="⚠️")

    # Load Dropdown
    saved_sessions = db.list_sessions()
    if saved_sessions:
        # Create a dictionary mapping titles to IDs for the selectbox
        session_dict = {f"{s['title']} ({s['updated_at'][:10]})": s['id'] for s in saved_sessions}

        selected_session_name = st.selectbox("Load Previous Chat", ["-- Select --"] + list(session_dict.keys()))

        if selected_session_name != "-- Select --":
            if st.button("Load Selected Chat", type="primary", use_container_width=True):
                load_id = session_dict[selected_session_name]
                api_json, ui_json = db.load_session(load_id)

                # Hydrate and restore state
                st.session_state.session_id = load_id
                st.session_state.history = hydrate_history(api_json)
                st.session_state.ui_messages = json.loads(ui_json)
                st.rerun()

    st.divider()
    if st.button("Start New Chat", use_container_width=True):
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.history = []
        st.session_state.ui_messages = []
        st.rerun()

# --- MAIN CHAT AREA ---
st.title("🪚 Kitchen Cabinet Assistant")
st.caption(f"Current Mode: **{selected_mode}** | Session: `{st.session_state.session_id[:8]}`")

# Render existing UI history
for msg in st.session_state.ui_messages:
    with st.chat_message(msg["role"]):

        # If this message has tool logs, render the expanders first
        if "tools" in msg and msg["tools"]:
            for tool in msg["tools"]:
                with st.expander(f"🛠️ Agent used tool: `{tool['name']}`"):
                    st.markdown(f"**Arguments:** `{tool['args']}`")
                    st.markdown("**Raw Output:**")

                    # Use st.text to render raw content safely without markdown formatting issues
                    if "content" in tool["result"]:
                        st.text(tool["result"]["content"])
                    else:
                        st.json(tool["result"])

        # Render the actual text response
        st.markdown(msg["content"])

# --- CHAT INPUT ---
if prompt := st.chat_input("Ask about your kitchen designs..."):

    # 1. Add user message to UI state and render it
    st.session_state.ui_messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. Process with Agent
    with st.chat_message("assistant"):
        with st.spinner("Thinking and reading files..."):

            final_text, tool_logs = process_chat_turn(
                user_message=prompt,
                history=st.session_state.history,
                system_instruction=current_system_prompt
            )

            # 3. Render the tool expanders immediately for the new response
            if tool_logs:
                for tool in tool_logs:
                    with st.expander(f"🛠️ Agent used tool: `{tool['name']}`"):
                        st.markdown(f"**Arguments:** `{tool['args']}`")
                        st.markdown("**Raw Output:**")
                        if "content" in tool["result"]:
                            st.text(tool["result"]["content"])
                        else:
                            st.json(tool["result"])

            # 4. Render the final text
            st.markdown(final_text)

            # 5. Save the assistant's response and tool logs to UI state
            st.session_state.ui_messages.append({
                "role": "assistant",
                "content": final_text,
                "tools": tool_logs
            })