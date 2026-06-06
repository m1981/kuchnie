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
    Convert common format dicts to Gemini ``types.Content`` objects.

    Common format:
        {"role": "user", "content": "Hello"}
        {"role": "assistant", "content": "Hi!", "tool_calls": [...]}
        {"role": "tool", "tool_call_id": "...", "content": "result"}

    Existing ``types.Content`` objects are passed through unchanged.
    """
    result: list[types.Content] = []

    for item in history:
        # Already a Gemini Content object — pass through
        if isinstance(item, types.Content):
            result.append(item)
            continue

        # Skip non-dict items
        if not isinstance(item, dict):
            logger.warning(
                "coerce_history_for_gemini: skipping unknown item type %s",
                type(item).__name__,
            )
            continue

        role: str = item.get("role", "user")
        content: Any = item.get("content", "")
        tool_calls: list[dict] | None = item.get("tool_calls")
        tool_call_id: str | None = item.get("tool_call_id")

        # Map roles: common format uses "assistant", Gemini uses "model"
        gemini_role = "model" if role == "assistant" else role

        # Handle tool response messages
        if role == "tool" and tool_call_id:
            # Parse content as JSON response
            if isinstance(content, str):
                try:
                    response_dict: dict = json.loads(content)
                except (json.JSONDecodeError, ValueError):
                    response_dict = {"content": content}
            elif isinstance(content, dict):
                response_dict = content
            else:
                response_dict = {"content": str(content)}

            result.append(
                types.Content(
                    role="user",  # Gemini uses "user" for tool responses
                    parts=[
                        types.Part(
                            function_response=types.FunctionResponse(
                                name="unknown",  # Will be resolved by tool_call_id
                                response=response_dict,
                                id=tool_call_id,
                            )
                        )
                    ],
                )
            )
            continue

        # Handle assistant messages with tool calls
        if tool_calls:
            parts: list[types.Part] = []

            # Add text content if present
            if content and isinstance(content, str):
                parts.append(types.Part(text=content))

            # Add tool calls
            for tc in tool_calls:
                parts.append(
                    types.Part(
                        function_call=types.FunctionCall(
                            name=tc.get("name", "unknown"),
                            args=tc.get("arguments", {}),
                            id=tc.get("id", ""),
                        )
                    )
                )

            if parts:
                result.append(types.Content(role=gemini_role, parts=parts))
            continue

        # Handle regular text messages
        if isinstance(content, str):
            result.append(
                types.Content(role=gemini_role, parts=[types.Part(text=content)])
            )
            continue

        # Handle list content (structured content)
        if isinstance(content, list):
            parts = []
            for block in content:
                if isinstance(block, dict):
                    if block.get("type") == "text":
                        parts.append(types.Part(text=block.get("text", "")))
                    else:
                        parts.append(types.Part(text=str(block)))
                else:
                    parts.append(types.Part(text=str(block)))

            if parts:
                result.append(types.Content(role=gemini_role, parts=parts))
            continue

        # Fallback: stringify
        logger.warning(
            "coerce_history_for_gemini: unexpected content type %s",
            type(content).__name__,
        )
        result.append(
            types.Content(role=gemini_role, parts=[types.Part(text=str(content))])
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
