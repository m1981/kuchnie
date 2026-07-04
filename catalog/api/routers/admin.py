"""GET /catalog/admin/stats, GET /catalog/full"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends

from catalog.api.deps import get_db
from catalog.models.domain import StatsOut



router = APIRouter(tags=["admin"])


@router.get("/admin/stats", response_model=StatsOut)
def get_stats(
    db: Annotated[sqlite3.Connection, Depends(get_db)],
) -> dict:
    producers = db.execute("SELECT COUNT(*) FROM producers").fetchone()[0]
    decors = db.execute("SELECT COUNT(*) FROM decors").fetchone()[0]
    variants = db.execute("SELECT COUNT(*) FROM variants").fetchone()[0]
    pairings = db.execute("SELECT COUNT(*) FROM pairings").fetchone()[0]
    worktops = db.execute("SELECT COUNT(*) FROM worktop_specs").fetchone()[0]
    return {
        "producers": producers,
        "decors": decors,
        "variants": variants,
        "pairings": pairings,
        "worktops": worktops,
    }


@router.get("/full")
def get_full_catalog(
    db: Annotated[sqlite3.Connection, Depends(get_db)],
) -> dict:
    """Return the full catalog in the shape expected by the frontend.

    Shape:
      { _generated, producers: { slug: { collections, decors: [...] } }, shared }
    """
    # ── Producers ──────────────────────────────────────────────
    producers_rows = db.execute(
        "SELECT slug, name, country, website FROM producers"
    ).fetchall()

    # ── Structures ─────────────────────────────────────────────
    structures = {}
    for row in db.execute(
        "SELECT s.code, s.name, s.type, s.finish, "
        "       s.fingerprint_resistant, s.synchronized_texture, "
        "       COALESCE(p.slug, '') AS producer "
        "FROM structures s "
        "LEFT JOIN producers p ON p.id = s.producer_id"
    ).fetchall():
        structures[row["code"]] = {
            "name": row["name"],
            "type": row["type"] or "",
            "finish": row["finish"] or "",
            "description": f"{row['type'] or ''} {row['finish'] or ''}".strip(),
            "fingerprint_resistant": bool(row["fingerprint_resistant"]),
            "synchronized": bool(row["synchronized_texture"]),
            "producer": row["producer"],
        }

    # ── Edge finishes ──────────────────────────────────────────
    edge_finishes = {}
    for row in db.execute(
        "SELECT DISTINCT finish FROM edges WHERE finish IS NOT NULL"
    ).fetchall():
        edge_finishes[row["finish"]] = row["finish"]

    # ── Surface types mapping ──────────────────────────────────
    surface_types = {}
    for row in db.execute(
        "SELECT code, type, finish FROM structures"
    ).fetchall():
        key = f"{row['type']}_{row['finish']}" if row["type"] and row["finish"] else (row["type"] or "other")
        if key not in surface_types:
            surface_types[key] = {"kronospan_structures": [], "swiss_krono_structures": [], "egger_structures": []}
        # We don't know which producer from the structure alone, so put in kronospan
        surface_types[key]["kronospan_structures"].append(row["code"])

    # ── Decors + Variants per producer ─────────────────────────
    producers_data = {}
    for prow in producers_rows:
        pslug = prow["slug"]

        # Decors for this producer
        decors = []
        for drow in db.execute(
            "SELECT d.id AS decor_pk, d.business_id, d.name, d.name_en, "
            "       d.group_name, d.ncs, d.ral, d.pantone, d.img, "
            "       d.discontinued, "
            "       COALESCE(cf.slug, '') AS color_family, "
            "       cf.hex_approx AS color_hex "
            "FROM decors d "
            "LEFT JOIN color_families cf ON cf.id = d.color_family_id "
            "WHERE d.producer_id = (SELECT id FROM producers WHERE slug = ?) "
            "ORDER BY d.business_id",
            (pslug,),
        ).fetchall():
            # Tags for this decor
            tags = [
                r["slug"]
                for r in db.execute(
                    "SELECT t.slug FROM decor_tags dt "
                    "JOIN tags t ON t.id = dt.tag_id "
                    "WHERE dt.decor_id = ?",
                    (drow["decor_pk"],),
                ).fetchall()
            ]

            # Variants for this decor
            variants = []
            for vrow in db.execute(
                "SELECT v.id, v.business_id, COALESCE(mt.slug, '') AS material_type, "
                "       m.slug AS material_slug, COALESCE(s.code, '') AS structure, "
                "       v.thickness_mm, v.width_mm, v.length_mm, "
                "       v.format_mm, v.sidedness, v.roles, "
                "       v.express, v.konfekcja, v.splashback_available, "
                "       v.hpl_available, v.countertop, v.multi_structures "
                "FROM variants v "
                "JOIN materials m ON m.id = v.material_id "
                "JOIN material_types mt ON mt.id = m.material_type_id "
                "LEFT JOIN structures s ON s.id = v.structure_id "
                "WHERE v.decor_id = ? "
                "ORDER BY v.business_id",
                (drow["decor_pk"],),
            ).fetchall():
                # Edge for this variant (from variant_edges)
                edge_data = None
                edge_row = db.execute(
                    "SELECT e.code, COALESCE(es.slug, '') AS supplier, "
                    "       COALESCE(e.finish, '') AS finish, "
                    "       COALESCE(e.material, '') AS material "
                    "FROM variant_edges ve "
                    "JOIN edges e ON e.id = ve.edge_id "
                    "LEFT JOIN edge_suppliers es ON es.id = e.supplier_id "
                    "WHERE ve.variant_id = ? "
                    "LIMIT 1",
                    (vrow["id"],),
                ).fetchone()
                if edge_row:
                    edge_data = {
                        "code": edge_row["code"],
                        "supplier": edge_row["supplier"],
                        "finish": edge_row["finish"],
                        "material": edge_row["material"],
                    }

                # Availability
                express_list = []
                konfekcja = False
                for arow in db.execute(
                    "SELECT channel FROM variant_availability "
                    "WHERE variant_id = ("
                    "  SELECT id FROM variants WHERE business_id = ?)",
                    (vrow["business_id"],),
                ).fetchall():
                    if arow["channel"] == "express_24h":
                        # Express thicknesses from the variant itself
                        if vrow["thickness_mm"]:
                            express_list.append(int(vrow["thickness_mm"]))
                    if arow["channel"] == "konfekcja":
                        konfekcja = True

                fmt = None
                if vrow["format_mm"]:
                    try:
                        fmt = json.loads(vrow["format_mm"])
                    except (json.JSONDecodeError, TypeError):
                        fmt = None

                roles_list = []
                if vrow["roles"]:
                    try:
                        roles_list = json.loads(vrow["roles"])
                    except (json.JSONDecodeError, TypeError):
                        roles_list = []

                variants.append({
                    "id": vrow["business_id"],
                    "material": vrow["material_type"],
                    "collection": vrow["material_slug"],
                    "structure": vrow["structure"] or "",
                    "roles": roles_list,
                    "thickness_mm": vrow["thickness_mm"],
                    "format": fmt,
                    "sidedness": vrow["sidedness"] or "",
                    "edge": edge_data,
                    "multi_structures": vrow["multi_structures"] or "",
                    "express": express_list or None,
                    "konfekcja": konfekcja,
                    "splashback_available": bool(vrow["splashback_available"]),
                    "hpl_available": bool(vrow["hpl_available"]),
                    "countertop": vrow["countertop"] or "",
                })

            # Multi-structures string for this decor (from first variant)
            multi_str = ""
            if variants:
                multi_str = variants[0].get("multi_structures", "")

            decors.append({
                "id": drow["business_id"],
                "name": drow["name"],
                "name_en": drow["name_en"] or "",
                "group": drow["group_name"] or "",
                "color_family": drow["color_family"] or "",
                "color_hex": drow["color_hex"],
                "ncs": drow["ncs"] or "",
                "ral": drow["ral"] or "",
                "pantone": drow["pantone"] or "",
                "img_url": f"/producers/{pslug}/decors/{drow['img']}" if drow["img"] else None,
                "tags": tags,
                # collection flags live in decor_tags since schema 1.5.0
                "one_global": "one-global" in tags,
                "new_2024": "new-2024" in tags,
                "discontinued": bool(drow["discontinued"]),
                "variants": variants,
            })

        producers_data[pslug] = {
            "collections": {
                "country": prow["country"] or "",
                "website": prow["website"] or "",
                "structures": structures,
                "edge_finishes": edge_finishes,
            },
            "decors": decors,
        }

    # ── Stats ──────────────────────────────────────────────────
    stats = {
        "producers": len(producers_rows),
        "decors": db.execute("SELECT COUNT(*) FROM decors").fetchone()[0],
        "variants": db.execute("SELECT COUNT(*) FROM variants").fetchone()[0],
    }

    return {
        "_generated": datetime.now(timezone.utc).isoformat(),
        "producers": producers_data,
        "shared": {
            "surface_types": surface_types,
        },
        "stats": stats,
    }
