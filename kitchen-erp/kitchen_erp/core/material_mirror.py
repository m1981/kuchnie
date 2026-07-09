# kitchen_erp/core/material_mirror.py
"""Material mirror — ADR-011 phase 3 (spec: docs/specs/material-mirror.md).

kitchen-erp's Material table stops being a place where material facts are
born: board identity (name, brand, woodgrain, sheet format) converges onto
the catalog service, keyed by catalog_variant_id. price_per_unit is NEVER
written by the mirror on existing rows — pricing is the ERP's own domain
(catalog's variant_prices is deferred); new rows arrive at 0.0 for the
admin to price.

Rows with catalog_variant_id IS NULL are local-born (admin UI, utility
materials) and are never touched. Mirrored rows whose variant left the
catalog are kept (projects may reference them), just no longer updated.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from sqlmodel import Session, select

from .catalog_client import CatalogClient
from .models import Material

BOARD_ROLES = {"front", "carcass"}
DEFAULT_SHEET_M2 = 5.796  # 2800 x 2070 fallback, same default as the model

# Identity fields the mirror owns on mirrored rows. price_per_unit is
# deliberately absent.
_MIRRORED_FIELDS = ("name", "brand", "category", "unit", "sheet_size_m2", "has_woodgrain")


@dataclass
class MirrorStats:
    added: int = 0
    updated: int = 0
    unchanged: int = 0


def _qualifies(row: dict) -> bool:
    if row.get("discontinued"):
        return False
    try:
        roles = set(json.loads(row.get("roles") or "[]"))
    except json.JSONDecodeError:
        return False
    return bool(roles & BOARD_ROLES)


def _identity_fields(row: dict) -> dict:
    name = f"{row['decor_id']} {row['decor_name']}"
    thickness = row.get("thickness_mm")
    if thickness:
        name += f" {thickness:g}mm"
    width, length = row.get("width_mm"), row.get("length_mm")
    sheet_m2 = (width * length) / 1_000_000 if width and length else DEFAULT_SHEET_M2
    return {
        "name": name,
        "brand": (row.get("producer") or "").replace("_", " ").title() or None,
        "category": "Board",
        "unit": "m2",
        "sheet_size_m2": sheet_m2,
        "has_woodgrain": row.get("structure_type") == "wood_grain",
    }


def refresh_material_mirror(session: Session, client: CatalogClient) -> MirrorStats:
    """Converge mirrored Material rows onto the catalog. Raises CatalogUnavailable."""
    mirrored = {
        m.catalog_variant_id: m
        for m in session.exec(
            select(Material).where(Material.catalog_variant_id.is_not(None))  # type: ignore[union-attr]
        )
    }
    stats = MirrorStats()
    for row in client.iter_rows():
        if not _qualifies(row):
            continue
        key = row["variant_id"]
        fields = _identity_fields(row)
        existing = mirrored.get(key)
        if existing is None:
            material = Material(**fields, price_per_unit=0.0, catalog_variant_id=key)
            session.add(material)
            mirrored[key] = material
            stats.added += 1
        elif any(getattr(existing, f) != v for f, v in fields.items()):
            for f, v in fields.items():
                setattr(existing, f, v)
            session.add(existing)
            stats.updated += 1
        else:
            stats.unchanged += 1
    session.commit()
    return stats
