"""Decomposer — the single entry point for turning a cabinet into panels.

This module is intentionally thin: it dispatches to the correct
construction method in the catalog and nothing else.
"""

from .model import CabinetInstance, DecompositionResult
from .catalog import TYPE_REGISTRY


def decompose(cab: CabinetInstance) -> DecompositionResult:
    """Decompose a cabinet instance into physical panels and accessories."""
    fn = TYPE_REGISTRY.get(cab.type)
    if fn is None:
        raise ValueError(
            f"Unknown cabinet type: {cab.type!r}. "
            f"Known types: {list(TYPE_REGISTRY.keys())}"
        )
    return fn(cab)
