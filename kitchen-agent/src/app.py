# src/app.py
import streamlit as st
from dotenv import load_dotenv
from agent import process_chat_turn

# Load environment variables (.env)
load_dotenv()

st.set_page_config(page_title="Kitchen Cabinet Agent", layout="wide")

# --- SIDEBAR (From your sketch) ---
with st.sidebar:
    st.header("Context & Settings")

    # 1. Prompt Templates Dropdown
    template_options = {
        "General Assistant": "You are a helpful assistant for a kitchen cabinet builder.",
        "Design Mode": "You are an expert kitchen designer. Focus on ergonomics, spacing, and aesthetics. Always check the repo map for design guidelines.",
        "Assembly Mode": "You are a master carpenter. Focus on structural integrity, hardware installation, and step-by-step assembly instructions."
    }
    selected_mode = st.selectbox("Prompt Template", list(template_options.keys()))
    current_system_prompt = template_options[selected_mode]

    st.divider()

    # 2. Tasks Checklist
    st.header("Tasks")
    st.checkbox("Design layout")
    st.checkbox("Calculate materials")
    st.checkbox("Order hardware")

    st.divider()
    if st.button("Clear Chat History"):
        st.session_state.history = []
        st.rerun()

# --- MAIN CHAT AREA ---
st.title("🪚 Kitchen Cabinet Assistant")
st.caption("Your local knowledge base agent.")

# Initialize chat history in Streamlit session state
if "history" not in st.session_state:
    st.session_state.history = []

# Render existing chat history
for msg in st.session_state.history:
    # We only want to display standard text messages in the UI,
    # not the raw JSON function calls/responses.
    part = msg.parts[0]
    if part.text:
        role = "user" if msg.role == "user" else "assistant"
        with st.chat_message(role):
            st.markdown(part.text)

# Chat input
if prompt := st.chat_input("Ask about your kitchen designs..."):

    # Display user message immediately
    with st.chat_message("user"):
        st.markdown(prompt)

    # Process with the Agent
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            # Pass the system prompt from the sidebar into the agent
            response_text, tool_used = process_chat_turn(
                user_message=prompt,
                history=st.session_state.history,
                system_instruction=current_system_prompt
            )

            # If the agent used a tool, show a small badge in the UI
            if tool_used:
                st.caption(f"🛠️ *Agent used tool: `{tool_used}`*")

            st.markdown(response_text)