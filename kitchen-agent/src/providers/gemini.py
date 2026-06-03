"""
src/providers/gemini.py
=======================
GeminiProvider — wraps the Google Gemini SDK agentic loop.

History format
--------------
Gemini uses SDK ``types.Content`` objects.  The history list passed in and
mutated in place must contain ``types.Content`` items (same as before the
refactor).

Provider-switching compatibility
---------------------------------
When a session was started with the Anthropic provider its history is stored
as plain ``{"role": ..., "content": ...}`` dicts (the Anthropic MessageParam
shape).  ``_coerce_history_for_gemini()`` converts any plain-dict items to
``types.Content`` objects before the API call.  Existing ``types.Content``
objects are returned unchanged (pure-Gemini sessions are unaffected).
"""
from __future__ import annotations

import base64
import json
from typing import Any

import structlog
from dotenv import load_dotenv
from google import genai
from google.genai import types

from src.config import settings
from src.agent.tool_executor import ToolCall, ToolExecutor, ToolResult
from src.providers.normalizer import ResponseNormalizer
from src.tools.file_ops import read_file

load_dotenv()

logger = structlog.get_logger(__name__)


def _build_default_registry():
    """Lazy-load the default ToolRegistry."""
    from src.tools.registry import build_default_registry
    return build_default_registry()


# ---------------------------------------------------------------------------
# Anthropic → Gemini history coercion
# ---------------------------------------------------------------------------

def _coerce_history_for_gemini(history: list) -> list:
    """
    Return a new list where every Anthropic plain-dict item has been converted
    to a ``types.Content`` object.  Existing ``types.Content`` objects are
    passed through unchanged (same object, not a copy).

    This is needed when a session was created with the Anthropic provider and
    is then continued with the Gemini provider.

    The original ``history`` list is **never mutated**.  Only a new list is
    returned.
    """
    # Build a tool_id → function_name index as we scan forward, so that
    # tool_result items can recover the name of their matching tool_use.
    tool_id_to_name: dict[str, str] = {}

    result: list[types.Content] = []

    for item in history:
        # ── Already a Gemini Content object — pass through untouched ─────────
        if isinstance(item, types.Content):
            for part in item.parts or []:
                if part.function_call and part.function_call.id:
                    tool_id_to_name[part.function_call.id] = part.function_call.name
            result.append(item)
            continue

        # ── Plain dict — Anthropic MessageParam shape ─────────────────────────
        if not isinstance(item, dict):
            logger.warning(
                "coerce_history_for_gemini: skipping unknown item type %s",
                type(item).__name__,
            )
            continue

        anthropic_role: str = item.get("role", "user")
        gemini_role: str = "model" if anthropic_role == "assistant" else anthropic_role
        content_raw: Any = item.get("content", "")

        # 1. Plain-string content
        if isinstance(content_raw, str):
            result.append(
                types.Content(role=gemini_role, parts=[types.Part(text=content_raw)])
            )
            continue

        # 2. List-of-blocks content
        if isinstance(content_raw, list):
            parts: list[types.Part] = []

            for block in content_raw:
                block_type = block.get("type") if isinstance(block, dict) else None

                if block_type == "text":
                    parts.append(types.Part(text=block["text"]))

                elif block_type == "tool_use":
                    tid = block.get("id", "")
                    name = block.get("name", "unknown")
                    tool_input = block.get("input", {})

                    if tid:
                        tool_id_to_name[tid] = name

                    parts.append(
                        types.Part(
                            function_call=types.FunctionCall(
                                name=name,
                                args=tool_input,
                                id=tid,
                            )
                        )
                    )

                elif block_type == "tool_result":
                    tid = block.get("tool_use_id", "")
                    func_name = tool_id_to_name.get(tid, "unknown")

                    raw_content = block.get("content", "{}")
                    if isinstance(raw_content, str):
                        try:
                            response_dict: dict = json.loads(raw_content)
                        except (json.JSONDecodeError, ValueError):
                            response_dict = {"content": raw_content}
                    elif isinstance(raw_content, dict):
                        response_dict = raw_content
                    else:
                        response_dict = {"content": str(raw_content)}

                    parts.append(
                        types.Part(
                            function_response=types.FunctionResponse(
                                name=func_name,
                                response=response_dict,
                                id=tid,
                            )
                        )
                    )

                else:
                    logger.warning(
                        "coerce_history_for_gemini: unknown block type '%s' — using text fallback",
                        block_type,
                    )
                    parts.append(types.Part(text=str(block)))

            if parts:
                result.append(types.Content(role=gemini_role, parts=parts))
            else:
                result.append(
                    types.Content(role=gemini_role, parts=[types.Part(text="")])
                )
            continue

        # 3. Unexpected content type — stringify fallback.
        logger.warning(
            "coerce_history_for_gemini: unexpected content type %s for role=%s",
            type(content_raw).__name__,
            anthropic_role,
        )
        result.append(
            types.Content(
                role=gemini_role,
                parts=[types.Part(text=str(content_raw))],
            )
        )

    return result


# ---------------------------------------------------------------------------
# Provider
# ---------------------------------------------------------------------------

class GeminiProvider:
    """
    LLM provider backed by the Google Gemini SDK.

    Creates a single ``genai.Client`` instance per ``GeminiProvider`` object.
    In production ``get_provider()`` is called per request, so the client is
    lightweight — the SDK reuses the underlying HTTP session.
    """

    def __init__(self, model_override: str | None = None) -> None:
        self._client = genai.Client()
        # Resolved at construction so it is stable for the lifetime of this
        # instance and visible to tests via provider._model.
        self._model: str = model_override or settings.gemini_model
        self._normalizer = ResponseNormalizer()
        self._registry = _build_default_registry()
        self._declarations = [
            e.declaration
            for e in self._registry.get_all_entries()
            if e.declaration is not None
        ]
        self._tool_executor = ToolExecutor(registry=self._registry)

    # ── LLMProvider interface (for TurnOrchestrator) ─────────────────────

    def complete(self, context: "AssembledContext") -> Any:
        """
        Single turn completion via the Gemini API.
        Returns raw SDK response — normalizer handles parsing.
        """
        from src.agent.context_assembler import AssembledContext

        # Build user parts with context files and images
        user_parts: list[types.Part] = []

        if context.context_files:
            snippets: list[str] = []
            for fp in context.context_files:
                result = read_file(fp)
                if "content" in result:
                    snippets.append(f"=== {fp} ===\n{result['content']}")
                else:
                    logger.warning("context_file_unreadable", path=fp, error=result.get("error"))
            if snippets:
                block = "[Context files injected by user]\n\n" + "\n\n".join(snippets)
                user_parts.append(types.Part(text=block))

        # Build messages list, injecting user parts into the last user message
        messages = list(context.messages)
        if messages and messages[-1].get("role") == "user":
            user_parts.append(types.Part(text=messages[-1]["content"]))
            messages[-1] = {"role": "user", "content": "", "_parts": user_parts}

        if context.images:
            for img in context.images:
                try:
                    raw_bytes = base64.b64decode(img["data"])
                    user_parts.append(
                        types.Part.from_bytes(data=raw_bytes, mime_type=img["mime_type"])
                    )
                except Exception as exc:
                    logger.warning("image_decode_failed", error=str(exc))

        # Convert messages to Gemini Content objects
        self._conversation_state = _coerce_history_for_gemini(messages)

        # If we have enriched user parts, replace the last user Content
        if user_parts and self._conversation_state:
            last = self._conversation_state[-1]
            if last.role == "user":
                self._conversation_state[-1] = types.Content(role="user", parts=user_parts)

        # Always use provider's captured declarations
        declarations = self._declarations
        gemini_tools = types.Tool(function_declarations=declarations)

        config_kwargs: dict = {}
        if context.system_prompt:
            config_kwargs["system_instruction"] = context.system_prompt
        config_kwargs["tools"] = [gemini_tools]
        config_kwargs["temperature"] = settings.gemini_temperature

        response = self._client.models.generate_content(
            model=self._model,
            contents=self._conversation_state,
            config=types.GenerateContentConfig(**config_kwargs),
        )

        # Store response in conversation state for tool loop continuity
        if response.candidates and response.candidates[0].content:
            self._conversation_state.append(response.candidates[0].content)

        return response

    def complete_with_tools(
        self,
        context: "AssembledContext",
        tool_calls: list["ToolCall"],
        tool_results: list["ToolResult"],
    ) -> Any:
        """
        Continue generation after tool execution.
        Builds tool call and result messages, appends to conversation state.
        """
        from src.agent.context_assembler import AssembledContext

        # Build tool call message (assistant Content with function_call parts)
        parts: list[types.Part] = []
        for tc in tool_calls:
            parts.append(types.Part(
                function_call=types.FunctionCall(
                    name=tc.name, args=tc.arguments, id=tc.id,
                )
            ))
        tool_call_content = types.Content(role="model", parts=parts)
        self._conversation_state.append(tool_call_content)

        # Build tool result message (user Content with function_response parts)
        result_parts: list[types.Part] = []
        for tr in tool_results:
            try:
                import ast
                response_dict = ast.literal_eval(tr.content)
            except (ValueError, SyntaxError):
                response_dict = {"content": tr.content}
            result_parts.append(types.Part(
                function_response=types.FunctionResponse(
                    name=tr.name,
                    response=response_dict,
                    id=tr.tool_call_id,
                )
            ))
        tool_result_content = types.Content(role="user", parts=result_parts)
        self._conversation_state.append(tool_result_content)

        # Always use provider's captured declarations
        declarations = self._declarations
        gemini_tools = types.Tool(function_declarations=declarations)

        config_kwargs: dict = {}
        if context.system_prompt:
            config_kwargs["system_instruction"] = context.system_prompt
        config_kwargs["tools"] = [gemini_tools]
        config_kwargs["temperature"] = settings.gemini_temperature

        response = self._client.models.generate_content(
            model=self._model,
            contents=self._conversation_state,
            config=types.GenerateContentConfig(**config_kwargs),
        )

        # Store response in conversation state for next iteration
        if response.candidates and response.candidates[0].content:
            self._conversation_state.append(response.candidates[0].content)

        return response
