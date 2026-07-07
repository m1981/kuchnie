"""Intermediate format — JSON serialization of Kitchen.

This is THE contract between home-builder-adapter, krono-compositor-mvp,
kitchen-cam, and kitchen-erp. The format is self-contained: no external file
references.

Round-trip:  Kitchen → dict → JSON → dict → Kitchen

See ADR-004 (intermediate format is logical) and ADR-009 (home-builder-adapter
produces this format from home_builder_5 Blender scenes).
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .blum_hinges import HingeGeometry
from .model import (
    CabinetInstance,
    HandleSpec,
    Kitchen,
    Row,
    ShelfPinSpec,
    WorktopSegment,
)


# ── To dict / JSON ──────────────────────────────────────────────

def kitchen_to_dict(kitchen: Kitchen) -> dict:
    """Kitchen → plain dict (JSON-serializable)."""
    return asdict(kitchen)


def kitchen_to_json(kitchen: Kitchen, path: str | Path) -> Path:
    """Write kitchen to a JSON file.  Returns the path written."""
    p = Path(path)
    data = kitchen_to_dict(kitchen)
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    return p


def kitchen_to_json_str(kitchen: Kitchen) -> str:
    """Kitchen → JSON string."""
    return json.dumps(kitchen_to_dict(kitchen), indent=2, ensure_ascii=False)


# ── From dict / JSON ────────────────────────────────────────────

def _build_cabinet(d: dict) -> CabinetInstance:
    """Reconstruct a CabinetInstance from a dict (handles extra/missing keys).

    ``asdict`` flattens nested spec dataclasses to plain dicts; they must be
    rehydrated here or every downstream attribute access breaks. ``config``
    is a discriminated union whose variant name is not stored in JSON, so it
    is re-synthesised from the legacy fields — the same (deterministic) path
    the YAML loader uses.
    """
    # Only pass fields that CabinetInstance actually accepts
    known = {f.name for f in CabinetInstance.__dataclass_fields__.values()}
    filtered = {k: v for k, v in d.items() if k in known}

    if isinstance(filtered.get("handles"), dict):
        filtered["handles"] = HandleSpec(**filtered["handles"])
    if isinstance(filtered.get("shelf_pins"), dict):
        filtered["shelf_pins"] = ShelfPinSpec(**filtered["shelf_pins"])
    if isinstance(filtered.get("hinges"), dict):
        filtered["hinges"] = HingeGeometry(**filtered["hinges"])
    filtered.pop("config", None)

    cab = CabinetInstance(**filtered)

    from .loader import _apply_synthesised_config
    return _apply_synthesised_config(cab)


def _build_row(d: dict) -> Row:
    cabinets = [_build_cabinet(c) for c in d.get("cabinets", [])]
    return Row(
        id=d["id"],
        label=d.get("label", ""),
        wall_width_mm=d["wall_width_mm"],
        wall_height_mm=d["wall_height_mm"],
        cabinets=cabinets,
    )


def _build_worktop(d: dict) -> WorktopSegment:
    known = {f.name for f in WorktopSegment.__dataclass_fields__.values()}
    filtered = {k: v for k, v in d.items() if k in known}
    return WorktopSegment(**filtered)


def kitchen_from_dict(data: dict) -> Kitchen:
    """Reconstruct a Kitchen from a plain dict."""
    rows = [_build_row(r) for r in data.get("rows", [])]
    worktops = [_build_worktop(w) for w in data.get("worktops", [])]
    return Kitchen(
        version=data.get("version", "1.0"),
        project_name=data.get("project_name", ""),
        created=data.get("created", ""),
        rows=rows,
        worktops=worktops,
    )


def kitchen_from_json(path: str | Path) -> Kitchen:
    """Read a Kitchen from a JSON file."""
    data = json.loads(Path(path).read_text())
    return kitchen_from_dict(data)


def kitchen_from_json_str(text: str) -> Kitchen:
    """Reconstruct a Kitchen from a JSON string."""
    return kitchen_from_dict(json.loads(text))
