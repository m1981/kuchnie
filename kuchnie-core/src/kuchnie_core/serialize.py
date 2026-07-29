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
    CornerLink,
    HandleSpec,
    Kitchen,
    Row,
    ShelfPinSpec,
    WorktopSegment,
)


# L-layout additive fields (spec: kuchnie-core/docs/specs/l-layout-model.md).
# Omitted from the serialized dict while unset so a flat legacy Kitchen keeps
# producing byte-identical JSON (spec invariant 4); carried when set.
_ROW_LAYOUT_FIELDS = (
    "start_position_mm",
    "end_position_mm",
    "direction",
    "turn",
    "corner_participation",
)


# ── To dict / JSON ──────────────────────────────────────────────

def kitchen_to_dict(kitchen: Kitchen) -> dict:
    """Kitchen → plain dict (JSON-serializable).

    L-layout fields (row positions, ``legs``, ``corner``) appear in the
    dict when set and are omitted while unset, so consumers of the flat
    legacy shape see exactly the keys they saw before (spec invariant 4).
    """
    data = asdict(kitchen)
    for row in data.get("rows", []):
        for key in _ROW_LAYOUT_FIELDS:
            if row.get(key) is None:
                row.pop(key, None)
    if not data.get("legs"):
        data.pop("legs", None)
    if data.get("corner") is None:
        data.pop("corner", None)
    return data


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

    from .loader import apply_synthesised_config
    return apply_synthesised_config(cab)


def _build_row(d: dict) -> Row:
    cabinets = [_build_cabinet(c) for c in d.get("cabinets", [])]
    return Row(
        id=d["id"],
        label=d.get("label", ""),
        wall_width_mm=d["wall_width_mm"],
        wall_height_mm=d["wall_height_mm"],
        cabinets=cabinets,
        # L-layout additive fields — absent keys stay at their None default
        start_position_mm=d.get("start_position_mm"),
        end_position_mm=d.get("end_position_mm"),
        direction=d.get("direction"),
        turn=d.get("turn"),
        corner_participation=d.get("corner_participation"),
    )


def _build_corner(d: dict | None) -> CornerLink | None:
    if not d:
        return None
    known = {f.name for f in CornerLink.__dataclass_fields__.values()}
    filtered = {k: v for k, v in d.items() if k in known}
    return CornerLink(**filtered)


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
        legs=list(data.get("legs") or []),
        corner=_build_corner(data.get("corner")),
    )


def kitchen_from_json(path: str | Path) -> Kitchen:
    """Read a Kitchen from a JSON file."""
    data = json.loads(Path(path).read_text())
    return kitchen_from_dict(data)


def kitchen_from_json_str(text: str) -> Kitchen:
    """Reconstruct a Kitchen from a JSON string."""
    return kitchen_from_dict(json.loads(text))
