"""
src/agent.py
============
Gemini agentic loop.

``process_chat_turn`` drives a single conversational turn.  It may call
zero or more tools before the model produces a final text response.

Design notes
------------
* The function mutates the *history* list in place AND returns the final text
  plus tool logs.  This dual approach is intentional: the caller (main.py)
  owns the history list and passes it around; returning it again would require
  a copy which is wasteful for large histories.
* Model name and temperature come from ``settings`` — no magic strings here.
* All tool execution is synchronous.  The FastAPI handler wraps the whole call
  inside ``asyncio.run_in_executor`` so the event loop is never blocked.
"""

import base64
import structlog


from dotenv import load_dotenv
from google import genai
from google.genai import types

from src.config import settings
from src.tools.file_ops import read_file
from src.tools.registry import DECLARATIONS, FUNCTION_MAP

load_dotenv()

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Gemini client & tool registry
# ---------------------------------------------------------------------------

_client = genai.Client()

# FUNCTION_MAP and DECLARATIONS are derived from the single ToolEntry registry
# in src/tools/registry.py — no duplication of tool names here.
_gemini_tools = types.Tool(function_declarations=DECLARATIONS)

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def process_chat_turn(
    user_message: str,
    history: list,
    system_instruction: str | None = None,
    images: list[dict] | None = None,
    context_files: list[str] | None = None,
) -> tuple[str, list[dict]]:
    """
    Handles a single conversational turn, allowing for multiple tool calls.

    Mutates *history* in place by appending all new turns (user message,
    model tool calls, tool responses, and the final model answer).

    Args:
        user_message:       Plain text from the user.
        history:            Gemini conversation history (mutated in place).
        system_instruction: Optional system-prompt override.
        images:             List of ``{mime_type, data}`` dicts (base64-encoded).
        context_files:      File paths whose contents are prepended as context.

    Returns:
        A tuple of ``(final_text, tool_logs)`` where *tool_logs* is a list of
        dicts with keys ``name``, ``args``, and ``result``.
    """
    logger.info("User asked: '%s'", user_message)

    # ── Build the user-turn parts list ───────────────────────────────────────

    user_parts: list[types.Part] = []

    # 1a. Inject selected context files as readable text before the message.
    if context_files:
        snippets: list[str] = []
        for fp in context_files:
            result = read_file(fp)
            if "content" in result:
                snippets.append(f"=== {fp} ===\n{result['content']}")
            else:
                logger.warning("Context file not readable: %s — %s", fp, result.get("error"))
        if snippets:
            block = "[Context files injected by user]\n\n" + "\n\n".join(snippets)
            user_parts.append(types.Part(text=block))

    # 1b. The user's text message.
    user_parts.append(types.Part(text=user_message))

    # 1c. Optional inline images (pasted via Ctrl+V).
    if images:
        for img in images:
            try:
                raw_bytes = base64.b64decode(img["data"])
                user_parts.append(
                    types.Part.from_bytes(data=raw_bytes, mime_type=img["mime_type"])
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to decode image: %s", exc)

    history.append(types.Content(role="user", parts=user_parts))

    # ── Gemini config (built once per turn) ──────────────────────────────────

    config = types.GenerateContentConfig(
        tools=[_gemini_tools],
        temperature=settings.gemini_temperature,
        system_instruction=system_instruction,
    )

    tools_used: list[dict] = []

    # ── Agentic loop ─────────────────────────────────────────────────────────

    while True:
        logger.info("Calling Gemini API (model=%s)…", settings.gemini_model)
        response = _client.models.generate_content(
            model=settings.gemini_model,
            contents=history,
            config=config,
        )

        candidate = response.candidates[0]
        if not candidate.content.parts:
            # Safety / refusal — treat as empty final response.
            logger.warning("Gemini returned a candidate with no parts.")
            history.append(types.Content(role="model", parts=[types.Part(text="")]))
            return "", tools_used

        part = candidate.content.parts[0]

        # ── Tool call branch ─────────────────────────────────────────────────
        if part.function_call:
            fc = part.function_call
            logger.info("🛠  Model requested tool: %s | args: %s", fc.name, fc.args)

            # Append the EXACT model part to preserve thought_signature.
            history.append(types.Content(role="model", parts=[part]))

            # Execute the tool.
            tool_fn = FUNCTION_MAP.get(fc.name)
            if tool_fn is not None:
                try:
                    result: dict = tool_fn(**fc.args)
                except Exception as exc:  # noqa: BLE001
                    result = {"error": str(exc)}
                    logger.error("Tool execution failed (%s): %s", fc.name, exc)
            else:
                result = {"error": f"Unknown tool: {fc.name}"}
                logger.warning("Model tried unknown tool: %s", fc.name)

            tools_used.append({"name": fc.name, "args": dict(fc.args), "result": result})
            logger.info("✅ Tool result snippet: %.120s", str(result))

            # Feed the result back into the conversation.
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
            # Loop → call Gemini again with updated history.

        # ── Final text branch ────────────────────────────────────────────────
        else:
            final_text: str = response.text or ""
            logger.info("💬 Model provided final text response.")
            history.append(
                types.Content(role="model", parts=[types.Part(text=final_text)])
            )
            return final_text, tools_used
