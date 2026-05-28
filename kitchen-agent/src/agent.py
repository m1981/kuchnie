# src/agent.py
import os
import logging
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Import our schemas
from tools.schemas import read_file_fn, get_repo_map_fn, edit_file_fn, create_file_fn

# Import our actual Python functions
from tools.file_ops import read_file, edit_file, create_file
from tools.repo_map import get_repo_map

# --- SET UP LOGGING ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)

load_dotenv()

# Initialize client
client = genai.Client()

# Map the string name from the schema to the actual Python function
FUNCTION_MAP = {
    "read_file": read_file,
    "get_repo_map": get_repo_map,
    "edit_file": edit_file,
    "create_file": create_file,
}

# Configure the tools for Gemini
gemini_tools = types.Tool(function_declarations=[
    read_file_fn,
    get_repo_map_fn,
    edit_file_fn,
    create_file_fn
])


def process_chat_turn(user_message: str, history: list, system_instruction: str = None) -> tuple[str, list]:
    """
    Handles a single turn of conversation, allowing for MULTIPLE tool calls.
    Mutates the `history` list in place.
    Returns: (Final text response, List of dictionaries containing tool execution details)
    """
    logger.info(f"User asked: '{user_message}'")

    # 1. Append user message to history
    history.append(types.Content(role="user", parts=[types.Part(text=user_message)]))

    # 2. Create config dynamically to include the system instruction (Prompt Template)
    config = types.GenerateContentConfig(
        tools=[gemini_tools],
        temperature=0.2,  # Low temperature for factual, grounded answers
        system_instruction=system_instruction
    )

    tools_used_this_turn = []

    # 3. The Agentic Loop
    while True:
        logger.info("Calling Gemini API...")
        response = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=history,
            config=config,
        )

        part = response.candidates[0].content.parts[0]

        # 4. Check if Gemini wants to use a tool
        if part.function_call:
            fc = part.function_call
            tool_name = fc.name
            tool_args = fc.args

            logger.info(f"🛠️ Model requested tool: {tool_name} | Args: {tool_args}")

            # CRITICAL FIX: Append the EXACT part returned by the model to preserve the thought_signature.
            history.append(types.Content(role="model", parts=[part]))

            # Execute the real Python function
            if tool_name in FUNCTION_MAP:
                try:
                    result = FUNCTION_MAP[tool_name](**tool_args)
                except Exception as e:
                    result = {"error": str(e)}
                    logger.error(f"Tool execution failed: {e}")
            else:
                result = {"error": f"Unknown tool: {tool_name}"}
                logger.warning(f"Model tried to use unknown tool: {tool_name}")

            # Save the detailed tool execution data for the Streamlit UI
            tools_used_this_turn.append({
                "name": tool_name,
                "args": tool_args,
                "result": result
            })

            result_str = str(result)
            logger.info(f"✅ Tool result snippet: {result_str[:100]}...")

            # Append the tool result back to history (CRITICAL: must include fc.id)
            history.append(
                types.Content(
                    role="user",
                    parts=[
                        types.Part(
                            function_response=types.FunctionResponse(
                                id=fc.id,
                                name=fc.name,
                                response=result,
                            )
                        )
                    ],
                )
            )

            # The loop continues! It will call Gemini again with the new history.

        else:
            # 5. No tool was called, meaning we have our final text response!
            final_text = response.text
            logger.info("💬 Model provided final text response.")

            # Append final answer to history
            history.append(types.Content(role="model", parts=[types.Part(text=final_text)]))

            # Return the detailed list instead of a string
            return final_text, tools_used_this_turn
