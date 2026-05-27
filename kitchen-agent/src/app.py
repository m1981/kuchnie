# src/app.py
import streamlit as st
from dotenv import load_dotenv
from agent import process_chat_turn

load_dotenv()

st.set_page_config(page_title="Kitchen Cabinet Agent", layout="wide")

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

    st.divider()
    st.header("Tasks")
    st.checkbox("Design layout")
    st.checkbox("Calculate materials")
    st.checkbox("Order hardware")

    st.divider()
    if st.button("Clear Chat History"):
        st.session_state.history = []
        st.session_state.ui_messages = []  # Clear UI state too
        st.rerun()

# --- STATE MANAGEMENT ---
# 1. API State (Strict Gemini format)
if "history" not in st.session_state:
    st.session_state.history = []

# 2. UI State (For rendering Streamlit chat bubbles and expanders)
if "ui_messages" not in st.session_state:
    st.session_state.ui_messages = []

# --- MAIN CHAT AREA ---
st.title("🪚 Kitchen Cabinet Assistant")
st.caption(f"Current Mode: **{selected_mode}**")

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