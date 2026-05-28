"""
Markdown export of chat sessions.

Pure functions only — no DB or HTTP concerns. Given a list of UI messages
(as stored in `ui_history_json`), produces a human-readable Markdown
document suitable for archiving or sharing.
"""
import json
from typing import Any


def _render_tool_call(tool: dict[str, Any]) -> str:
    """Renders a single tool invocation as a collapsible <details> block."""
    name = tool.get("name", "unknown")
    args = tool.get("args", {})
    result = tool.get("result", {})

    args_json = json.dumps(args, indent=2, ensure_ascii=False)
    result_json = json.dumps(result, indent=2, ensure_ascii=False)

    return (
        f"<details>\n"
        f"<summary>🔧 Tool call: <code>{name}</code></summary>\n\n"
        f"**Arguments:**\n\n"
        f"```json\n{args_json}\n```\n\n"
        f"**Result:**\n\n"
        f"```json\n{result_json}\n```\n\n"
        f"</details>"
    )


def _render_message(message: dict[str, Any]) -> str:
    """Renders a single UI message (user or assistant) as Markdown."""
    role = message.get("role", "unknown")
    content = message.get("content", "")

    if role == "user":
        return f"## User\n\n{content}"

    if role == "assistant":
        parts = [f"## Assistant\n\n{content}"]
        tools = message.get("tools") or []
        for tool in tools:
            parts.append(_render_tool_call(tool))
        return "\n\n".join(parts)

    # Fallback for unknown roles
    return f"## {role.capitalize()}\n\n{content}"


def export_session_to_markdown(ui_messages: list[dict[str, Any]], title: str) -> str:
    """
    Renders a chat session as a Markdown document.

    Args:
        ui_messages: List of UI-format messages (role/content/tools).
        title: Session title for the document header.

    Returns:
        A Markdown string.
    """
    safe_title = title.strip() if title else "Untitled Session"
    sections = [f"# {safe_title}"]
    for message in ui_messages:
        sections.append(_render_message(message))
    return "\n\n".join(sections) + "\n"
