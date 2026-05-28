"""
src/tools/registry.py
=====================
Single source of truth for every tool the agent can call.

Each ``ToolEntry`` binds together:
  - ``declaration`` — the typed ``FunctionDeclaration`` sent to the Gemini API.
  - ``fn``          — the Python callable that executes when the model picks
                      that tool.

Derived constants (used by agent.py):
  ``FUNCTION_MAP``  — ``{name: callable}`` — looked up at call-dispatch time.
  ``DECLARATIONS``  — ordered list of ``FunctionDeclaration`` objects passed to
                      ``types.Tool(function_declarations=DECLARATIONS)``.

Why this exists
---------------
Previously ``schemas.py`` held raw dicts (no type validation) and ``agent.py``
maintained a separate ``FUNCTION_MAP`` that duplicated every tool name as a
plain string.  A rename in one place silently broke the other.

This module eliminates both problems:
  1. ``FunctionDeclaration`` / ``Schema`` objects validate field names at import
     time — a typo like ``desciption`` raises immediately.
  2. ``FUNCTION_MAP`` is *derived* from the same registry list, so name and
     callable can never drift apart.
  3. ``base_dir`` is fixed inside a lambda so it is never part of the public
     tool API surface (prevents a potential path-traversal vector).
"""

from dataclasses import dataclass
from typing import Callable

from google.genai import types

from src.config import settings
from src.tools.file_ops import (
    create_file,
    edit_file,
    read_file,
    search_knowledge_base,
)
from src.tools.repo_map import get_repo_map


# ---------------------------------------------------------------------------
# Registry entry
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ToolEntry:
    """Pairs a Gemini FunctionDeclaration with its Python implementation."""

    declaration: types.FunctionDeclaration
    fn: Callable[..., dict]  # type: ignore[type-arg]


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

_read_file_entry = ToolEntry(
    declaration=types.FunctionDeclaration(
        name="read_file",
        description=(
            "Reads the full contents of a local markdown file from the knowledge base."
        ),
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "filepath": types.Schema(
                    type=types.Type.STRING,
                    description="Path to the file, e.g., 'data/test.md'",
                ),
            },
            required=["filepath"],
        ),
    ),
    fn=read_file,
)

_get_repo_map_entry = ToolEntry(
    declaration=types.FunctionDeclaration(
        name="get_repo_map",
        description=(
            "Scans the knowledge base and returns a list of all markdown files and "
            "their headers. Use this to figure out which file you need to read."
        ),
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={},
            required=[],
        ),
    ),
    # base_dir is fixed to settings.data_dir — never exposed to the LLM.
    fn=lambda: get_repo_map(base_dir=str(settings.data_dir)),
)

_edit_file_entry = ToolEntry(
    declaration=types.FunctionDeclaration(
        name="edit_file",
        description=(
            "Edits an existing file using exact search and replace. "
            "ONLY use this tool if the user EXPLICITLY asks you to update, change, or "
            "edit a file. DO NOT proactively edit files to add information unless commanded."
        ),
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "filepath": types.Schema(
                    type=types.Type.STRING,
                    description="Path to the file, e.g., 'data/test.md'",
                ),
                "search_text": types.Schema(
                    type=types.Type.STRING,
                    description="The exact text currently in the file that you want to replace.",
                ),
                "replace_text": types.Schema(
                    type=types.Type.STRING,
                    description="The new text to insert in place of the search_text.",
                ),
            },
            required=["filepath", "search_text", "replace_text"],
        ),
    ),
    fn=edit_file,
)

_create_file_entry = ToolEntry(
    declaration=types.FunctionDeclaration(
        name="create_file",
        description=(
            "Creates a brand new markdown file. "
            "Use this when starting a new topic that does not fit in existing files. "
            "DO NOT use this to update existing files."
        ),
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "filepath": types.Schema(
                    type=types.Type.STRING,
                    description="Path to the new file, e.g., 'data/03_Finishes/paint.md'",
                ),
                "content": types.Schema(
                    type=types.Type.STRING,
                    description="The full markdown content to write into the new file.",
                ),
            },
            required=["filepath", "content"],
        ),
    ),
    fn=create_file,
)

_search_knowledge_base_entry = ToolEntry(
    declaration=types.FunctionDeclaration(
        name="search_knowledge_base",
        description=(
            "Searches all markdown files in the knowledge base for lines that match a "
            "regex pattern. "
            "Use this to find specific terms, part numbers, or topics without reading "
            "every file manually. "
            "Supports OR logic with the pipe character (e.g., 'hinge|blum|runner'). "
            "Returns file path, line number, and matching line content."
        ),
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "query": types.Schema(
                    type=types.Type.STRING,
                    description=(
                        "A regex pattern to search for, e.g., 'Blum|hinge' or '18mm'. "
                        "Matching is case-insensitive."
                    ),
                ),
            },
            required=["query"],
        ),
    ),
    # base_dir is fixed to settings.data_dir — never exposed to the LLM.
    fn=lambda query: search_knowledge_base(query, base_dir=str(settings.data_dir)),
)


# ---------------------------------------------------------------------------
# Registry — single ordered list; everything else is derived from it
# ---------------------------------------------------------------------------

TOOLS: list[ToolEntry] = [
    _read_file_entry,
    _get_repo_map_entry,
    _edit_file_entry,
    _create_file_entry,
    _search_knowledge_base_entry,
]

# Derived: name → callable mapping used by the agent dispatch loop.
FUNCTION_MAP: dict[str, Callable[..., dict]] = {  # type: ignore[type-arg]
    entry.declaration.name: entry.fn for entry in TOOLS
}

# Derived: ordered list of declarations sent to types.Tool().
DECLARATIONS: list[types.FunctionDeclaration] = [
    entry.declaration for entry in TOOLS
]
