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
# Tool definitions (Ordered: Discovery -> Ingestion -> Mutation)
# ---------------------------------------------------------------------------

_get_repo_map_entry = ToolEntry(
    declaration=types.FunctionDeclaration(
        name="get_repo_map",
        description=(
            "Scans the knowledge base and returns a list of all markdown files and their headers. "
            "ALWAYS use this tool FIRST if the user asks you to read, update, or elaborate on a topic "
            "but does not provide a specific file path. Do not guess file paths."
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

_search_knowledge_base_entry = ToolEntry(
    declaration=types.FunctionDeclaration(
        name="search_knowledge_base",
        description=(
            "Searches all markdown files for lines matching a regex pattern. "
            "Use this if get_repo_map doesn't give you enough detail, or if you need to find "
            "specific terms, part numbers, or dimensions across the entire workspace. "
            "Supports OR logic (e.g., 'hinge|blum|runner')."
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

_read_file_entry = ToolEntry(
    declaration=types.FunctionDeclaration(
        name="read_file",
        description=(
            "Reads the full contents of a local markdown file. "
            "CRITICAL: You MUST use this tool to read a file BEFORE you attempt to use edit_file. "
            "You cannot edit a file safely without reading its exact current contents first."
        ),
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "filepath": types.Schema(
                    type=types.Type.STRING,
                    description="Exact path to the file, e.g., 'data/test.md'",
                ),
            },
            required=["filepath"],
        ),
    ),
    fn=read_file,
)

_edit_file_entry = ToolEntry(
    declaration=types.FunctionDeclaration(
        name="edit_file",
        description=(
            "Edits an existing file using exact search and replace. "
            "CRITICAL RULES: "
            "1. You MUST know the EXACT existing text. "
            "2. If you have not called read_file on this path yet, do so NOW before using this tool. "
            "3. Do not ask the user for the text, find it yourself."
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
                    description=(
                        "The EXACT text currently in the file to replace. "
                        "WARNING: This must match character-for-character. Pay strict attention to "
                        "leading/trailing spaces, newlines (\\n), and punctuation."
                    ),
                ),
                "replace_text": types.Schema(
                    type=types.Type.STRING,
                    description="The new text to insert. Ensure you include necessary markdown formatting and newlines.",
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
            "DO NOT use this to update existing files (use edit_file for that)."
        ),
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "filepath": types.Schema(
                    type=types.Type.STRING,
                    description=(
                        "Path to the new file. You may specify nested directories "
                        "(e.g., 'data/04_NewTopic/file.md') and they will be created automatically."
                    ),
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


# ---------------------------------------------------------------------------
# Registry — single ordered list; everything else is derived from it
# ---------------------------------------------------------------------------

# Reordered to prime the LLM: Discovery -> Ingestion -> Mutation
TOOLS: list[ToolEntry] = [
    _get_repo_map_entry,
    _search_knowledge_base_entry,
    _read_file_entry,
    _edit_file_entry,
    _create_file_entry,
]

# Derived: name → callable mapping used by the agent dispatch loop.
FUNCTION_MAP: dict[str, Callable[..., dict]] = {  # type: ignore[type-arg]
    entry.declaration.name: entry.fn for entry in TOOLS
}

# Derived: ordered list of declarations sent to types.Tool().
DECLARATIONS: list[types.FunctionDeclaration] = [
    entry.declaration for entry in TOOLS
]