"""
src/exporter.py
===============
Markdown export of chat sessions.

Pure functions only — no DB or HTTP concerns.  Given a list of UI messages
(as stored in ``ui_history_json``), produces a human-readable Markdown
document suitable for archiving or sharing.
"""

import json
from typing import Any


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

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
