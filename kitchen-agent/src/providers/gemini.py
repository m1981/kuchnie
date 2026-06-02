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

Provider-switching compatibility
---------------------------------
When a session was started with the Anthropic provider its history is stored
as plain ``{"role": ..., "content": ...}`` dicts (the Anthropic MessageParam
shape).  ``hydrate_history()`` returns those dicts as-is so that
``AnthropicProvider`` can continue using them.

If the same session is then continued with the **Gemini** provider (user
switches provider, or the server default changes) ``process_chat_turn``
receives those plain dicts in the ``history`` argument.  The Gemini SDK's
``generate_content`` call validates ``contents`` with Pydantic and only
accepts ``types.Content`` objects — plain dicts are rejected with a
``ValidationError`` → HTTP 500.

``_coerce_history_for_gemini()`` solves this by converting any plain-dict
items to ``types.Content`` objects before the API call.  Existing
``types.Content`` objects are returned unchanged (pure-Gemini sessions are
unaffected).  The caller's original list is **not mutated** — the conversion
is purely internal.

Tool dispatch
-------------
Uses ``FUNCTION_MAP`` and ``DECLARATIONS`` from the central tool registry
(``src/tools/registry.py``) — no tool definitions live here.
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
from src.tools.registry import DECLARATIONS, FUNCTION_MAP

load_dotenv()

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Adapter: FUNCTION_MAP → ToolRegistryProtocol
# ---------------------------------------------------------------------------

class _FunctionMapAdapter:
    """
    Adapts the module-level FUNCTION_MAP dict to the ToolRegistryProtocol
    so ToolExecutor can look up handlers.

    This adapter reads FUNCTION_MAP at call time (not at construction), so
    tests that patch FUNCTION_MAP via ``patch("src.providers.gemini.FUNCTION_MAP", ...)``
    still work — the adapter sees the patched version.
    """

    def get_handler(self, name: str):
        if name not in FUNCTION_MAP:
            raise ValueError(f"Unknown tool: {name!r}")
        return FUNCTION_MAP[name]


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

    Conversion rules
    ----------------
    * ``"assistant"`` role → ``"model"`` role  (Gemini vocabulary)
    * ``content`` is a plain string → ``[Part(text=content)]``
    * ``content`` is a list of blocks:
        - ``{"type": "text",       "text": "..."}``     → ``Part(text=...)``
        - ``{"type": "tool_use",  "id", "name", "input"}``
                                                         → ``Part(function_call=...)``
        - ``{"type": "tool_result", "tool_use_id", "content"}``
                                                         → ``Part(function_response=...)``
          The function name is recovered by scanning already-processed items
          backwards for a matching ``tool_use`` id.
        - Any other block type → ``Part(text=str(block))`` fallback (no crash)

    Multiple blocks of the same type in one message (parallel tool calls) are
    mapped to multiple ``Part`` objects in a single ``Content`` item.

    The original ``history`` list is **never mutated**.  Only a new list is
    returned.

    Args:
        history: The raw history list as returned by ``hydrate_history()``.
                 May contain ``types.Content`` objects, plain dicts, or a mix.

    Returns:
        A new list of ``types.Content`` objects ready for the Gemini SDK.
    """
    # Build a tool_id → function_name index as we scan forward, so that
    # tool_result items can recover the name of their matching tool_use.
    tool_id_to_name: dict[str, str] = {}

    result: list[types.Content] = []

    for item in history:
        # ── Already a Gemini Content object — pass through untouched ─────────
        if isinstance(item, types.Content):
            # Also index any function_call parts so tool_result lookup works
            # in mixed histories (Content tool_call + dict tool_result, unlikely
            # but defensive).
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

                    # Register so downstream tool_result blocks can find the name.
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
                    # Unknown block type — stringify as fallback, never crash.
                    logger.warning(
                        "coerce_history_for_gemini: unknown block type '%s' — using text fallback",
                        block_type,
                    )
                    parts.append(types.Part(text=str(block)))

            if parts:
                result.append(types.Content(role=gemini_role, parts=parts))
            else:
                # Empty content list — add an empty text part to keep position.
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
        self._tools = types.Tool(function_declarations=DECLARATIONS)
        # Resolved at construction so it is stable for the lifetime of this
        # instance and visible to tests via provider._model.
        self._model: str = model_override or settings.gemini_model
        self._normalizer = ResponseNormalizer()
        self._tool_executor = ToolExecutor(registry=_FunctionMapAdapter())

    def process_chat_turn(
        self,
        user_message: str,
        history: list,
        system_instruction: str | None = None,
        images: list[dict] | None = None,
        context_files: list[str] | None = None,
        use_tools: bool = True,
    ) -> tuple[str, list[dict]]:
        """
        Drives a single conversational turn via the Gemini API.

        Mutates *history* in place by appending all new turns produced
        during this call (user message, model tool calls, tool responses,
        and the final model text).

        Provider-switching note
        -----------------------
        If *history* contains plain dicts (e.g. from a session that was
        previously driven by the Anthropic provider), those items are coerced
        to ``types.Content`` objects *for the API call only*.  The caller's
        list keeps its original items; only new turns appended during this
        call are ``types.Content`` objects.

        use_tools=False
        ---------------
        Skips the agentic loop entirely: no tools are passed to the API and
        exactly one ``generate_content`` call is made.  The response text is
        returned immediately with an empty tool_logs list.

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

        new_user_content = types.Content(role="user", parts=user_parts)
        history.append(new_user_content)

        # ── API config ────────────────────────────────────────────────────────

        # When use_tools=False we omit the tools parameter entirely so the
        # Gemini API treats this as a plain generative call with no function
        # declarations.  This also means we never enter the agentic loop.
        config = types.GenerateContentConfig(
            tools=[self._tools] if use_tools else [],
            temperature=settings.gemini_temperature,
            system_instruction=system_instruction,
        )

        tools_used: list[dict] = []

        # ── Coerce full history to types.Content objects ──────────────────────
        # This handles the provider-switching case: if the session was previously
        # driven by AnthropicProvider its items are plain dicts that the Gemini
        # SDK's Pydantic validator would reject.  We convert them here without
        # mutating the caller's list.
        gemini_contents = _coerce_history_for_gemini(history)

        # ── Agentic loop ──────────────────────────────────────────────────────


        # ── Direct call branch (use_tools=False) ───────────────────────────
        # One API call, no loop, no tool dispatch, empty tool_logs.
        if not use_tools:
            logger.info("gemini_direct_call", model=self._model)
            response = self._client.models.generate_content(
                model=self._model,
                contents=gemini_contents,
                config=config,
            )
            normalized = self._normalizer.normalize(response, provider="gemini")
            final_text = normalized.text or ""
            logger.info("gemini_direct_response", length=len(final_text))
            history.append(
                types.Content(role="model", parts=[types.Part(text=final_text)])
            )
            return final_text, []

        while True:
            logger.info("gemini_api_call", model=self._model)
            response = self._client.models.generate_content(
                model=self._model,
                contents=gemini_contents,
                config=config,
            )

            candidate = response.candidates[0]
            if not candidate.content.parts:
                logger.warning("gemini_no_parts_in_candidate")
                empty_content = types.Content(role="model", parts=[types.Part(text="")])
                history.append(empty_content)
                gemini_contents.append(empty_content)
                return "", tools_used

            # Use normalizer to classify the response.
            normalized = self._normalizer.normalize(response, provider="gemini")

            # ── Tool call branch ──────────────────────────────────────────────
            if normalized.has_tool_calls:
                # The normalizer extracted tool_calls in a provider-agnostic
                # format, but we still need the raw SDK parts for history
                # mutation (to preserve thought_signature, function_call id, etc.)
                part = candidate.content.parts[0]
                fc = part.function_call
                logger.info("gemini_tool_call", tool=fc.name, args=str(fc.args)[:120])

                # Append the EXACT model part to preserve thought_signature.
                model_content = types.Content(role="model", parts=[part])
                history.append(model_content)
                gemini_contents.append(model_content)

                # Dispatch the tool using ToolExecutor.
                tool_call = normalized.tool_calls[0]
                tool_exec_result = self._tool_executor._execute_one(
                    ToolCall(id=tool_call.id, name=tool_call.name, arguments=tool_call.arguments)
                )

                if tool_exec_result.is_error:
                    result = {"error": tool_exec_result.content}
                    logger.warning("gemini_tool_error", tool=tool_call.name, error=tool_exec_result.content)
                else:
                    # ToolExecutor returns stringified results — parse back to dict
                    # for consistent tool_logs format
                    try:
                        import ast
                        result = ast.literal_eval(tool_exec_result.content)
                    except (ValueError, SyntaxError):
                        result = {"content": tool_exec_result.content}

                tools_used.append({"name": tool_call.name, "args": tool_call.arguments, "result": result})
                logger.info("gemini_tool_result", snippet=str(result)[:120])

                # Feed the result back using the raw SDK objects for id preservation.
                tool_response_content = types.Content(
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
                history.append(tool_response_content)
                gemini_contents.append(tool_response_content)

            # ── Final text branch ─────────────────────────────────────────────
            else:
                final_text: str = normalized.text or ""
                logger.info("gemini_final_response", length=len(final_text))
                final_content = types.Content(
                    role="model", parts=[types.Part(text=final_text)]
                )
                history.append(final_content)
                # No need to append to gemini_contents — loop ends here.
                return final_text, tools_used

    # ── LLMCompleter interface (for TurnOrchestrator) ─────────────────────

    def complete(self, context: "AssembledContext") -> Any:
        """
        New interface for TurnOrchestrator.
        Calls Gemini API with pre-assembled context.
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
            # Replace last user message with enriched version
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

        config_kwargs: dict = {}
        if context.system_prompt:
            config_kwargs["system_instruction"] = context.system_prompt
        config_kwargs["tools"] = [self._tools]
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
            # Parse result content back to dict for Gemini
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

        config_kwargs: dict = {}
        if context.system_prompt:
            config_kwargs["system_instruction"] = context.system_prompt
        config_kwargs["tools"] = [self._tools]
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
