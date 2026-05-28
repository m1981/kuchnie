"""
src/tools/schemas.py
====================
.. deprecated::
    This module previously held raw-dict tool schemas.  It has been superseded
    by ``src/tools/registry.py``, which uses typed ``FunctionDeclaration`` /
    ``Schema`` objects and co-locates each declaration with its callable so
    that tool names can never drift out of sync.

    This file is kept only as a compatibility shim.  Import from
    ``src.tools.registry`` directly for all new code.
"""

# Re-export the typed declarations under the old names so that any test or
# external code that still does ``from src.tools.schemas import read_file_fn``
# continues to work unchanged.
from src.tools.registry import (
    _create_file_entry,
    _edit_file_entry,
    _get_repo_map_entry,
    _read_file_entry,
    _search_knowledge_base_entry,
)

read_file_fn = _read_file_entry.declaration
get_repo_map_fn = _get_repo_map_entry.declaration
edit_file_fn = _edit_file_entry.declaration
create_file_fn = _create_file_entry.declaration
search_knowledge_base_fn = _search_knowledge_base_entry.declaration

__all__ = [
    "read_file_fn",
    "get_repo_map_fn",
    "edit_file_fn",
    "create_file_fn",
    "search_knowledge_base_fn",
]
