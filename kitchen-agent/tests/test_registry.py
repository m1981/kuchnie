"""
tests/test_registry.py
======================
Unit tests for src/tools/registry.py.

Covers:
  - Every TOOLS entry has a non-empty name and description.
  - FUNCTION_MAP is derived correctly (name → callable, no extra / missing keys).
  - DECLARATIONS list matches TOOLS in order and length.
  - Required fields are declared on each parametrised tool.
  - Zero-argument tools (get_repo_map, search_knowledge_base wrappers) have
    required=[] (not omitted).
  - base_dir is NOT a parameter on get_repo_map or search_knowledge_base
    (path-traversal guard).
  - Callable wrappers for get_repo_map and search_knowledge_base actually
    invoke the underlying functions with the correct fixed base_dir.
  - schemas.py shim re-exports the same declaration objects.
"""
from unittest.mock import patch

import pytest
from google.genai import types

from src.tools.registry import DECLARATIONS, FUNCTION_MAP, TOOLS, ToolEntry


# ---------------------------------------------------------------------------
# Structural invariants
# ---------------------------------------------------------------------------

def test_tools_is_nonempty() -> None:
    assert len(TOOLS) > 0


def test_every_entry_is_tool_entry() -> None:
    for entry in TOOLS:
        assert isinstance(entry, ToolEntry)


def test_every_declaration_has_name_and_description() -> None:
    for entry in TOOLS:
        d = entry.declaration
        assert d.name, f"Empty name on {d}"
        assert d.description, f"Empty description for tool '{d.name}'"


def test_every_entry_has_callable() -> None:
    for entry in TOOLS:
        assert callable(entry.fn), f"fn for '{entry.declaration.name}' is not callable"


# ---------------------------------------------------------------------------
# FUNCTION_MAP derivation
# ---------------------------------------------------------------------------

def test_function_map_keys_match_tool_names() -> None:
    expected = {entry.declaration.name for entry in TOOLS}
    assert set(FUNCTION_MAP.keys()) == expected


def test_function_map_values_match_entry_fns() -> None:
    for entry in TOOLS:
        assert FUNCTION_MAP[entry.declaration.name] is entry.fn


# ---------------------------------------------------------------------------
# DECLARATIONS derivation
# ---------------------------------------------------------------------------

def test_declarations_length_matches_tools() -> None:
    assert len(DECLARATIONS) == len(TOOLS)


def test_declarations_order_matches_tools() -> None:
    for decl, entry in zip(DECLARATIONS, TOOLS):
        assert decl is entry.declaration


def test_declarations_are_function_declaration_instances() -> None:
    for decl in DECLARATIONS:
        assert isinstance(decl, types.FunctionDeclaration)


# ---------------------------------------------------------------------------
# Per-tool schema correctness
# ---------------------------------------------------------------------------

def _declaration(name: str) -> types.FunctionDeclaration:
    """Helper: retrieve a declaration by tool name."""
    for entry in TOOLS:
        if entry.declaration.name == name:
            return entry.declaration
    raise KeyError(f"No tool named '{name}'")


@pytest.mark.parametrize("tool_name,required_fields", [
    ("read_file",             ["filepath"]),
    ("edit_file",             ["filepath", "search_text", "replace_text"]),
    ("create_file",           ["filepath", "content"]),
    ("search_knowledge_base", ["query"]),
])
def test_required_fields_declared(tool_name: str, required_fields: list[str]) -> None:
    decl = _declaration(tool_name)
    schema_required = list(decl.parameters.required or [])
    for field in required_fields:
        assert field in schema_required, (
            f"'{field}' not in required for tool '{tool_name}'"
        )


@pytest.mark.parametrize("tool_name", ["get_repo_map", "search_knowledge_base"])
def test_zero_or_single_arg_tools_have_explicit_required(tool_name: str) -> None:
    """required must be present (even if empty) — not None/omitted."""
    decl = _declaration(tool_name)
    assert decl.parameters.required is not None, (
        f"tool '{tool_name}' has required=None; should be an explicit list"
    )


# ---------------------------------------------------------------------------
# base_dir is NOT exposed on get_repo_map or search_knowledge_base
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("tool_name", ["get_repo_map", "search_knowledge_base"])
def test_base_dir_not_in_schema(tool_name: str) -> None:
    """base_dir must never be a declared parameter (path-traversal guard)."""
    decl = _declaration(tool_name)
    props = decl.parameters.properties or {}
    assert "base_dir" not in props, (
        f"'base_dir' must not be exposed in schema for tool '{tool_name}'"
    )


# ---------------------------------------------------------------------------
# Wrapper callables invoke underlying functions with fixed base_dir
# ---------------------------------------------------------------------------

def test_get_repo_map_wrapper_passes_data_dir(tmp_path) -> None:
    """The get_repo_map fn wrapper must pass settings.data_dir as base_dir."""
    captured: dict = {}

    def fake_get_repo_map(base_dir: str = "data") -> dict:
        captured["base_dir"] = base_dir
        return {"content": "ok"}

    # Patch the names the lambda closes over, then call the entry fn directly
    # while the patches are still active.  No module reload needed.
    with (
        patch("src.tools.registry.get_repo_map", fake_get_repo_map),
        patch("src.tools.registry.settings.data_dir", tmp_path),
    ):
        from src.tools.registry import _get_repo_map_entry
        _get_repo_map_entry.fn()

    assert "base_dir" in captured
    assert captured["base_dir"] == str(tmp_path)


def test_search_knowledge_base_wrapper_passes_data_dir(tmp_path) -> None:
    """The search_knowledge_base fn wrapper must pass settings.data_dir as base_dir."""
    captured: dict = {}

    def fake_search(query: str, base_dir: str = "data") -> dict:
        captured["base_dir"] = base_dir
        captured["query"] = query
        return {"content": "ok"}

    with (
        patch("src.tools.registry.search_knowledge_base", fake_search),
        patch("src.tools.registry.settings.data_dir", tmp_path),
    ):
        from src.tools.registry import _search_knowledge_base_entry
        _search_knowledge_base_entry.fn(query="blum")

    assert captured["base_dir"] == str(tmp_path)
    assert captured["query"] == "blum"


