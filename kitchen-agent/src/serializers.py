"""
src/serializers.py
==================
Round-trip serialization for conversation history stored in SQLite.

**Provider-Agnostic Format (v2)**
---------------------------------
All messages are stored in a common OpenAI-compatible format:

    {"role": "user", "content": "Hello", "turn_id": "uuid"}
    {"role": "assistant", "content": "Hi!", "tool_calls": [...], "turn_id": "uuid"}
    {"role": "tool", "tool_call_id": "call_123", "content": "result", "turn_id": "uuid"}

This format is provider-agnostic — both Gemini and Anthropic providers
can consume it by converting to their native API format internally.

**Migration from v1**
---------------------
Legacy sessions may contain:
- Gemini format: {"type": "text", "role": "user", "data": "..."}
- Anthropic format: {"__provider": "anthropic", "role": "user", "content": "..."}

These are automatically converted to the common format on load.
"""

import json
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Legacy format detection
# ---------------------------------------------------------------------------

_ANTHROPIC_PROVIDER_KEY = "__provider"
_ANTHROPIC_PROVIDER_VAL = "anthropic"


def _is_legacy_gemini(item: dict) -> bool:
    """Check if item is in legacy Gemini format (has 'type' field)."""
    return "type" in item and "data" in item


def _is_legacy_anthropic(item: dict) -> bool:
    """Check if item is in legacy Anthropic format (has __provider sentinel)."""
    return item.get(_ANTHROPIC_PROVIDER_KEY) == _ANTHROPIC_PROVIDER_VAL


# ---------------------------------------------------------------------------
# Legacy → Common format conversion
# ---------------------------------------------------------------------------

def _legacy_gemini_to_common(item: dict, turn_id: str | None) -> dict | None:
    """Convert legacy Gemini format to common format."""
    item_type = item.get("type")
    role = item.get("role", "user")

    if item_type == "text":
        msg: dict[str, Any] = {"role": role, "content": item.get("data", "")}
    elif item_type == "function_call":
        # Assistant message with tool call
        msg = {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": item.get("id", ""),
                    "name": item.get("name", ""),
                    "arguments": item.get("args", {}),
                }
            ],
        }
    elif item_type == "function_response":
        # Tool response message
        msg = {
            "role": "tool",
            "tool_call_id": item.get("id", ""),
            "content": json.dumps(item.get("response", {}))
            if isinstance(item.get("response"), dict)
            else str(item.get("response", "")),
        }
    else:
        logger.warning("Unknown legacy Gemini type '%s' — skipped.", item_type)
        return None

    if turn_id:
        msg["turn_id"] = turn_id
    return msg


def _legacy_anthropic_to_common(item: dict, turn_id: str | None) -> dict:
    """Convert legacy Anthropic format to common format."""
    # Strip internal keys
    clean = {
        k: v
        for k, v in item.items()
        if k not in (_ANTHROPIC_PROVIDER_KEY, "turn_id")
    }
    if turn_id:
        clean["turn_id"] = turn_id
    return clean


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def dehydrate_history(history: list, turn_ids: list[str] | None = None) -> str:
    """
    Convert a conversation history to a JSON string for DB storage.

    Accepts:
      - Common format dicts (pass through)
      - Gemini ``types.Content`` objects (convert to common format)
      - Legacy format dicts (convert to common format)

    Args:
        history:  History list in any supported format.
        turn_ids: Optional parallel list of ``turn_id`` strings.

    Returns:
        JSON string of the dehydrated history in common format.
    """
    simple_list: list[dict] = []

    for idx, item in enumerate(history):
        turn_id: str | None = turn_ids[idx] if turn_ids is not None else None

        if isinstance(item, dict):
            # Already a dict — could be common format or legacy
            if _is_legacy_anthropic(item):
                # Legacy Anthropic format
                converted = _legacy_anthropic_to_common(item, turn_id)
                simple_list.append(converted)
            elif _is_legacy_gemini(item):
                # Legacy Gemini format
                converted = _legacy_gemini_to_common(item, turn_id)
                if converted is not None:
                    simple_list.append(converted)
            else:
                # Already common format — pass through
                if turn_id and "turn_id" not in item:
                    item = {**item, "turn_id": turn_id}
                simple_list.append(item)

        else:
            # Assume Gemini types.Content object
            try:
                from google.genai import types

                if isinstance(item, types.Content):
                    converted = _gemini_content_to_common(item, turn_id)
                    if converted is not None:
                        simple_list.append(converted)
                else:
                    logger.warning(
                        "dehydrate_history: skipping unknown item type %s",
                        type(item).__name__,
                    )
            except ImportError:
                logger.warning(
                    "dehydrate_history: skipping non-dict item (no Gemini SDK)",
                )

    return json.dumps(simple_list)


def _gemini_content_to_common(content: Any, turn_id: str | None) -> dict | None:
    """Convert Gemini types.Content to common format."""
    if not content.parts:
        return None

    role = content.role
    part = content.parts[0]

    if part.text is not None:
        msg: dict[str, Any] = {"role": role, "content": part.text}

    elif part.function_call is not None:
        msg = {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": part.function_call.id or "",
                    "name": part.function_call.name,
                    "arguments": part.function_call.args or {},
                }
            ],
        }

    elif part.function_response is not None:
        msg = {
            "role": "tool",
            "tool_call_id": part.function_response.id or "",
            "content": json.dumps(part.function_response.response)
            if isinstance(part.function_response.response, dict)
            else str(part.function_response.response),
        }

    else:
        logger.warning("Skipping unrecognised Gemini part type")
        return None

    if turn_id:
        msg["turn_id"] = turn_id
    return msg


def hydrate_history(json_string: str) -> list[dict]:
    """
    Rebuild a conversation history from a DB JSON string.

    Always returns a list of dicts in **common format**:
        {"role": "user"|"assistant"|"tool", "content": "...", ...}

    Legacy formats are automatically converted.

    ``turn_id`` is preserved in the output for stable message identity.
    """
    if not json_string or json_string.strip() in ("", "[]"):
        return []

    simple_list: list[dict] = json.loads(json_string)
    history: list[dict] = []

    for item in simple_list:
        # Legacy Anthropic format
        if _is_legacy_anthropic(item):
            converted = _legacy_anthropic_to_common(item, item.get("turn_id"))
            history.append(converted)
            continue

        # Legacy Gemini format
        if _is_legacy_gemini(item):
            converted = _legacy_gemini_to_common(item, item.get("turn_id"))
            if converted is not None:
                history.append(converted)
            continue

        # Already common format — pass through
        history.append(item)

    return history
