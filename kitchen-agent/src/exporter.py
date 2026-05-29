"""
src/exporter.py
===============
Export functions for chat sessions.

Two export formats are provided:

1. ``export_session_to_markdown`` — Human-readable Markdown.
   Uses ``ui_history_json`` (the pretty, tool-summarised UI representation).
   Suitable for archiving, sharing, or reading.

2. ``export_session_to_llm_json`` — LLM-context debug export.
   Uses ``api_history_json`` (the raw dehydrated ``Content`` objects) so you
   can see *exactly* what the model had in its context window, including
   ``thought_signature`` hex bytes, function call IDs, and every Part.
   Suitable for debugging multi-turn tool-calling issues.

Pure functions only — no DB or HTTP concerns.
"""

import json
from datetime import datetime, timezone
from typing import Any


# ──────────────────────────────────────────────────────────────────────────────
# ── Format 1: Markdown export (existing, unchanged) ───────────────────────────
# ──────────────────────────────────────────────────────────────────────────────


def _render_tool_call(tool: dict[str, Any]) -> str:
    """Renders a single tool invocation as a collapsible ``<details>`` block."""
    name = tool.get("name", "unknown")
    args_json = json.dumps(tool.get("args", {}), indent=2, ensure_ascii=False)
    result_json = json.dumps(tool.get("result", {}), indent=2, ensure_ascii=False)

    return (
        "<details>\n"
        f"<summary>🔧 Tool call: <code>{name}</code></summary>\n\n"
        "**Arguments:**\n\n"
        f"```json\n{args_json}\n```\n\n"
        "**Result:**\n\n"
        f"```json\n{result_json}\n```\n\n"
        "</details>"
    )


def _render_message(message: dict[str, Any]) -> str:
    """Renders a single UI message (user or assistant) as Markdown."""
    role = message.get("role", "unknown")
    content = message.get("content", "")

    if role == "user":
        return f"## User\n\n{content}"

    if role == "assistant":
        tool_blocks = [_render_tool_call(t) for t in (message.get("tools") or [])]
        parts = [f"## Assistant\n\n{content}", *tool_blocks]
        return "\n\n".join(parts)

    # Fallback for unknown roles (future-proofing).
    return f"## {role.capitalize()}\n\n{content}"


def export_session_to_markdown(
    ui_messages: list[dict[str, Any]],
    title: str,
) -> str:
    """
    Renders a chat session as a Markdown document.

    Args:
        ui_messages: List of UI-format messages (role / content / tools).
        title:       Session title used as the document ``# heading``.

    Returns:
        A Markdown string ending with a trailing newline.
    """
    safe_title = title.strip() or "Untitled Session"
    sections = [f"# {safe_title}", *(_render_message(m) for m in ui_messages)]
    return "\n\n".join(sections) + "\n"


# ──────────────────────────────────────────────────────────────────────────────
# ── Format 2: LLM-context debug export (new) ──────────────────────────────────
# ──────────────────────────────────────────────────────────────────────────────


def _render_llm_part(item: dict[str, Any]) -> dict[str, Any]:
    """
    Converts a single dehydrated API-history item into a debug-friendly
    part dict that mirrors what the Gemini SDK sends to the model.

    Handles the four recognised types:
      - ``text``              → ``{type, text}``
      - ``function_call``     → ``{type, name, args, id, thought_signature_hex}``
      - ``function_response`` → ``{type, name, response, id}``
      - anything else         → ``{type: "unknown_part", raw: <original>}``
    """
    item_type = item.get("type")

    if item_type == "text":
        return {
            "type": "text",
            "text": item.get("data", ""),
        }

    if item_type == "function_call":
        return {
            "type": "function_call",
            "name": item.get("name"),
            "args": item.get("args"),
            "id": item.get("id"),
            # thought_signature is already stored as hex (or None) by the serializer
            "thought_signature_hex": item.get("signature"),
        }

    if item_type == "function_response":
        return {
            "type": "function_response",
            "name": item.get("name"),
            "response": item.get("response"),
            "id": item.get("id"),
        }

    # Unrecognised part — preserve raw data so nothing is silently dropped
    return {
        "type": "unknown_part",
        "raw": item,
    }


def _render_llm_turn(
    item: dict[str, Any],
    already_has_parts: bool = False,
) -> dict[str, Any]:
    """
    Converts a single dehydrated API-history item (or a pre-composed
    multi-part turn dict) into a turn dict suitable for the LLM debug export.

    Args:
        item:              A dehydrated item as stored in ``api_history_json``,
                           OR a dict with a ``"parts"`` key already populated
                           (multi-part turn, future-proofing path).
        already_has_parts: When ``True`` the caller supplies an item whose
                           ``"parts"`` key already holds a list of pre-rendered
                           part dicts.  The function wraps them unchanged under
                           the same role.

    Returns:
        ``{"role": str, "parts": [part_dict, ...]}``
    """
    role = item.get("role", "unknown")

    if already_has_parts:
        # Multi-part path: parts list was already built by the caller.
        return {
            "role": role,
            "parts": item.get("parts", []),
        }

    # Single-part path (current serializer stores one part per item).
    return {
        "role": role,
        "parts": [_render_llm_part(item)],
    }


def export_session_to_llm_json(
    api_items: list[dict[str, Any]],
    title: str,
    session_id: str,
) -> dict[str, Any]:
    """
    Renders the raw LLM context as a structured JSON document.

    Each element in ``api_items`` is a dehydrated ``Content`` object as stored
    in ``api_history_json`` by ``src/serializers.py``.  The output mirrors
    what the Gemini model actually receives in its context window.

    ``thought_signature`` bytes are represented as hex strings (they are
    already hex-encoded by the serializer; this function preserves that).

    Args:
        api_items:  List of dehydrated Content dicts from ``api_history_json``.
        title:      Session title (for metadata block).
        session_id: Session UUID (for metadata block).

    Returns:
        A dict with two top-level keys:
          - ``"metadata"``: session_id, title, turn_count, export_timestamp
          - ``"turns"``:    ordered list of turn dicts, each with role + parts
    """
    turns = [_render_llm_turn(item) for item in api_items]

    return {
        "metadata": {
            "session_id": session_id,
            "title": title,
            "turn_count": len(turns),
            "export_timestamp": datetime.now(tz=timezone.utc).isoformat(),
        },
        "turns": turns,
    }
