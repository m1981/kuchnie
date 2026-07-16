"""SQLite-backed material catalog repository.

Reads from the catalog database created by catalog/scripts/importer.py.
This is the production implementation of the MaterialCatalog protocol.

Usage:
    from kuchnie_core.materials import SqliteMaterialCatalog

    catalog = SqliteMaterialCatalog("catalog/db/catalog.db")
    variant = catalog.get_variant("K8685-CH-18-SM")
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .exceptions import CatalogUnavailableError
from .models import EdgeInfo, VariantInfo, WorktopInfo


class SqliteMaterialCatalog:
    """Material catalog backed by a SQLite database.

    Implements the MaterialCatalog protocol. All queries are read-only.
    The connection is opened lazily on first query.
    """

    def __init__(self, db_path: str | Path):
        self._db_path = Path(db_path)
        self._db: sqlite3.Connection | None = None

    def _connect(self) -> sqlite3.Connection:
        """Lazy connection — opens on first use."""
        if self._db is None:
            if not self._db_path.exists():
                raise CatalogUnavailableError(str(self._db_path))
            self._db = sqlite3.connect(
                str(self._db_path), check_same_thread=False
            )
            self._db.row_factory = sqlite3.Row
            self._db.execute("PRAGMA foreign_keys = ON")
            self._db.execute("PRAGMA query_only = ON")  # safety: read-only
        return self._db

    def close(self) -> None:
        """Close the database connection."""
        if self._db is not None:
            self._db.close()
            self._db = None

    # ── MaterialCatalog protocol ─────────────────────────────────

    def get_variant(self, code: str) -> VariantInfo | None:
        db = self._connect()
        row = db.execute(
            """
            SELECT
                v.business_id   AS code,
                d.business_id   AS decor_code,
                d.name          AS decor_name,
                p.slug          AS producer,
                mt.slug         AS material_type,
                COALESCE(s.code, '') AS structure,
                v.thickness_mm,
                v.roles,
                v.format_mm,
                COALESCE(v.sidedness, '') AS sidedness,
                v.hpl_available,
                v.splashback_available
            FROM variants v
            JOIN decors d          ON d.id = v.decor_id
            JOIN producers p       ON p.id = d.producer_id
            JOIN materials m       ON m.id = v.material_id
            JOIN material_types mt ON mt.id = m.material_type_id
            LEFT JOIN structures s ON s.id = v.structure_id
            WHERE v.business_id = ?
            """,
            (code,),
        ).fetchone()

        if row is None:
            return None

        roles = tuple(json.loads(row["roles"])) if row["roles"] else ()
        fmt = tuple(json.loads(row["format_mm"])) if row["format_mm"] else (0, 0)

        return VariantInfo(
            code=row["code"],
            decor_code=row["decor_code"],
            decor_name=row["decor_name"],
            producer=row["producer"],
            material_type=row["material_type"],
            structure=row["structure"],
            thickness_mm=row["thickness_mm"],
            roles=roles,
            format_mm=fmt,  # type: ignore[arg-type]
            sidedness=row["sidedness"],
            hpl_available=bool(row["hpl_available"]),
            splashback_available=bool(row["splashback_available"]),
        )

    def get_edge(self, code: str) -> EdgeInfo | None:
        db = self._connect()
        row = db.execute(
            """
            SELECT
                e.code,
                COALESCE(es.slug, '') AS supplier,
                COALESCE(e.material, '') AS material,
                e.thickness_mm,
                e.width_mm,
                e.radius_mm
            FROM edges e
            LEFT JOIN edge_suppliers es ON es.id = e.supplier_id
            WHERE e.code = ?
            """,
            (code,),
        ).fetchone()

        if row is None:
            return None

        return EdgeInfo(
            code=row["code"],
            supplier=row["supplier"],
            material=row["material"],
            thickness_mm=row["thickness_mm"] or 0,
            width_mm=row["width_mm"] or 0,
            radius_mm=row["radius_mm"] or 0,
        )

    def find_worktops(self, decor_code: str) -> list[WorktopInfo]:
        db = self._connect()
        rows = db.execute(
            """
            SELECT
                v.business_id   AS variant_code,
                d.business_id   AS decor_code,
                d.name          AS decor_name,
                wc.slug         AS construction,
                wp.code         AS profile,
                wp.edge_radius_mm,
                ws.available_widths_mm,
                ws.max_length_mm,
                COALESCE(ws.edge_material, '') AS edge_material,
                v.thickness_mm,
                COALESCE(ws.core_color, '') AS core_color
            FROM worktop_specs ws
            JOIN variants v                ON v.id = ws.variant_id
            JOIN decors d                  ON d.id = v.decor_id
            JOIN worktop_constructions wc  ON wc.id = ws.construction_id
            JOIN worktop_profiles wp       ON wp.id = ws.profile_id
            WHERE d.business_id = ?
            """,
            (decor_code,),
        ).fetchall()

        results = []
        for row in rows:
            widths = tuple(json.loads(row["available_widths_mm"]))
            results.append(WorktopInfo(
                variant_code=row["variant_code"],
                decor_code=row["decor_code"],
                decor_name=row["decor_name"],
                construction=row["construction"],
                profile=row["profile"],
                edge_radius_mm=row["edge_radius_mm"],
                available_widths_mm=widths,
                max_length_mm=row["max_length_mm"],
                edge_material=row["edge_material"],
                thickness_mm=row["thickness_mm"],
                core_color=row["core_color"],
            ))
        return results

    def find_edges_for_variant(self, variant_code: str) -> list[EdgeInfo]:
        db = self._connect()
        rows = db.execute(
            """
            SELECT
                e.code,
                COALESCE(es.slug, '') AS supplier,
                COALESCE(e.material, '') AS material,
                e.thickness_mm,
                e.width_mm,
                e.radius_mm
            FROM variant_edges ve
            JOIN edges e                   ON e.id = ve.edge_id
            LEFT JOIN edge_suppliers es    ON es.id = e.supplier_id
            JOIN variants v                ON v.id = ve.variant_id
            WHERE v.business_id = ?
            """,
            (variant_code,),
        ).fetchall()

        return [
            EdgeInfo(
                code=row["code"],
                supplier=row["supplier"],
                material=row["material"],
                thickness_mm=row["thickness_mm"] or 0,
                width_mm=row["width_mm"] or 0,
                radius_mm=row["radius_mm"] or 0,
            )
            for row in rows
        ]
