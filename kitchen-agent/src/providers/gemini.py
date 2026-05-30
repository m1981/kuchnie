"""
src/providers/gemini.py
=======================
GeminiProvider — wraps the Google Gemini SDK agentic loop.

This is a direct refactor of the original ``src/agent.py`` logic, extracted
into a class that satisfies the ``LLMProvider`` Protocol.  The agentic loop
itself is unchanged; only the module structure moves.

History format
--------------
Gemini uses SDK ``types.Content`` objects.  The history list passed in and
mutated in place must contain ``types.Content`` items (same as before the
refactor).

Tool dispatch
-------------
Uses ``FUNCTION_MAP`` and ``DECLARATIONS`` from the central tool registry
(``src/tools/registry.py``) — no tool definitions live here.
"""
from __future__ import annotations

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


class GeminiProvider:
    """
    LLM provider backed by the Google Gemini SDK.

    Creates a single ``genai.Client`` instance per ``GeminiProvider`` object.
    In production ``get_provider()`` is called per request, so the client is
    lightweight — the SDK reuses the underlying HTTP session.
    """

    def __init__(self, model_override: str | None = None) -> None:
        self._client = genai.Client()
        self._tools = types.Tool(function_declarations=DECLARATIONS)
        # Resolved at construction so it is stable for the lifetime of this
        # instance and visible to tests via provider._model.
        self._model: str = model_override or settings.gemini_model

    def process_chat_turn(
        self,
        user_message: str,
        history: list,
        system_instruction: str | None = None,
        images: list[dict] | None = None,
        context_files: list[str] | None = None,
    ) -> tuple[str, list[dict]]:
        """
        Drives a single conversational turn via the Gemini API.

        Mutates *history* in place by appending all new turns produced
        during this call (user message, model tool calls, tool responses,
        and the final model text).

        Returns:
            ``(final_text, tool_logs)`` — see LLMProvider docstring.
        """
        logger.info("gemini_turn_start", message_preview=user_message[:60])

        # ── Build user-turn parts ─────────────────────────────────────────────

        user_parts: list[types.Part] = []

        # 1a. Inject context files as a text block before the user message.
        if context_files:
            snippets: list[str] = []
            for fp in context_files:
                result = read_file(fp)
                if "content" in result:
                    snippets.append(f"=== {fp} ===\n{result['content']}")
                else:
                    logger.warning("context_file_unreadable", path=fp, error=result.get("error"))
            if snippets:
                block = "[Context files injected by user]\n\n" + "\n\n".join(snippets)
                user_parts.append(types.Part(text=block))

        # 1b. The user's text message.
        user_parts.append(types.Part(text=user_message))

        # 1c. Optional inline images.
        if images:
            for img in images:
                try:
                    raw_bytes = base64.b64decode(img["data"])
                    user_parts.append(
                        types.Part.from_bytes(data=raw_bytes, mime_type=img["mime_type"])
                    )
                except Exception as exc:  # noqa: BLE001
                    logger.warning("image_decode_failed", error=str(exc))

        history.append(types.Content(role="user", parts=user_parts))

        # ── API config ────────────────────────────────────────────────────────

        config = types.GenerateContentConfig(
            tools=[self._tools],
            temperature=settings.gemini_temperature,
            system_instruction=system_instruction,
        )

        tools_used: list[dict] = []

        # ── Agentic loop ──────────────────────────────────────────────────────

        while True:
            logger.info("gemini_api_call", model=self._model)
            response = self._client.models.generate_content(
                model=self._model,
                contents=history,
                config=config,
            )

            candidate = response.candidates[0]
            if not candidate.content.parts:
                logger.warning("gemini_no_parts_in_candidate")
                history.append(types.Content(role="model", parts=[types.Part(text="")]))
                return "", tools_used

            part = candidate.content.parts[0]

            # ── Tool call branch ──────────────────────────────────────────────
            if part.function_call:
                fc = part.function_call
                logger.info("gemini_tool_call", tool=fc.name, args=str(fc.args)[:120])

                # Append the EXACT model part to preserve thought_signature.
                history.append(types.Content(role="model", parts=[part]))

                # Dispatch the tool.
                tool_fn = FUNCTION_MAP.get(fc.name)
                if tool_fn is not None:
                    try:
                        result: dict = tool_fn(**fc.args)
                    except Exception as exc:  # noqa: BLE001
                        result = {"error": str(exc)}
                        logger.error("gemini_tool_error", tool=fc.name, error=str(exc))
                else:
                    result = {"error": f"Unknown tool: {fc.name}"}
                    logger.warning("gemini_unknown_tool", tool=fc.name)

                tools_used.append({"name": fc.name, "args": dict(fc.args), "result": result})
                logger.info("gemini_tool_result", snippet=str(result)[:120])

                # Feed the result back.
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

            # ── Final text branch ─────────────────────────────────────────────
            else:
                final_text: str = response.text or ""
                logger.info("gemini_final_response", length=len(final_text))
                history.append(
                    types.Content(role="model", parts=[types.Part(text=final_text)])
                )
                return final_text, tools_used
