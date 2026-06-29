"""Repository for decor + variant queries against v_decors_full."""

from __future__ import annotations

import sqlite3
from typing import Optional

from catalog.models.domain import DecorSummary, DecorWithVariants, VariantOut


class DecorRepository:
    def __init__(self, db: sqlite3.Connection):
        self.db = db

    def list_filtered(
        self,
        *,
        producer: Optional[str] = None,
        color_family: Optional[str] = None,
        material_type: Optional[str] = None,
        structure: Optional[str] = None,
        role: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[DecorSummary], int]:
        """Return filtered decors from v_decors_full with total count."""
        where, params = self._build_where(
            producer=producer,
            color_family=color_family,
            material_type=material_type,
            structure=structure,
            role=role,
            search=search,
        )
        count_sql = f"SELECT COUNT(*) FROM v_decors_full {where}"
        total = self.db.execute(count_sql, params).fetchone()[0]

        offset = (page - 1) * page_size
        data_sql = (
            f"SELECT * FROM v_decors_full {where} "
            f"ORDER BY decor_name, variant_id "
            f"LIMIT ? OFFSET ?"
        )
        rows = self.db.execute(data_sql, params + [page_size, offset]).fetchall()
        items = [DecorSummary.model_validate(dict(r)) for r in rows]
        return items, total

    def get_by_id(self, business_id: str) -> Optional[DecorWithVariants]:
        """Get a single decor with all its variants, grouped."""
        rows = self.db.execute(
            "SELECT * FROM v_decors_full WHERE decor_id = ? ORDER BY variant_id",
            (business_id,),
        ).fetchall()
        if not rows:
            return None

        first = dict(rows[0])
        variants = []
        for r in rows:
            rd = dict(r)
            variants.append(VariantOut(
                variant_pk=rd["variant_pk"],
                variant_id=rd["variant_id"],
                material_type=rd["material_type"],
                material=rd["material"],
                structure=rd.get("structure"),
                structure_name=rd.get("structure_name"),
                structure_type=rd.get("structure_type"),
                roles=rd["roles"],
                thickness_mm=rd.get("thickness_mm"),
                width_mm=rd.get("width_mm"),
                length_mm=rd.get("length_mm"),
                format_mm=rd.get("format_mm"),
                sidedness=rd.get("sidedness"),
                express=rd.get("express"),
                konfekcja=rd.get("konfekcja", False),
                splashback_available=rd.get("splashback_available", False),
                hpl_available=rd.get("hpl_available", False),
                countertop=rd.get("countertop"),
                multi_structures=rd.get("multi_structures"),
            ))

        return DecorWithVariants(
            decor_id=first["decor_id"],
            decor_name=first["decor_name"],
            decor_name_en=first.get("decor_name_en"),
            group_name=first.get("group_name"),
            color_family=first.get("color_family"),
            ncs=first.get("ncs"),
            ral=first.get("ral"),
            pantone=first.get("pantone"),
            img=first.get("img"),
            producer=first["producer"],
            variants=variants,
        )

    def get_variants(
        self,
        business_id: str,
        *,
        material_type: Optional[str] = None,
    ) -> list[VariantOut]:
        """Get variants for a decor, optionally filtered by material type."""
        sql = "SELECT * FROM v_decors_full WHERE decor_id = ?"
        params: list = [business_id]
        if material_type:
            sql += " AND material_type = ?"
            params.append(material_type)
        sql += " ORDER BY variant_id"

        rows = self.db.execute(sql, params).fetchall()
        return [
            VariantOut(
                variant_pk=dict(r)["variant_pk"],
                variant_id=dict(r)["variant_id"],
                material_type=dict(r)["material_type"],
                material=dict(r)["material"],
                structure=dict(r).get("structure"),
                structure_name=dict(r).get("structure_name"),
                structure_type=dict(r).get("structure_type"),
                roles=dict(r)["roles"],
                thickness_mm=dict(r).get("thickness_mm"),
                width_mm=dict(r).get("width_mm"),
                length_mm=dict(r).get("length_mm"),
                format_mm=dict(r).get("format_mm"),
                sidedness=dict(r).get("sidedness"),
                express=dict(r).get("express"),
                konfekcja=dict(r).get("konfekcja", False),
                splashback_available=dict(r).get("splashback_available", False),
                hpl_available=dict(r).get("hpl_available", False),
                countertop=dict(r).get("countertop"),
                multi_structures=dict(r).get("multi_structures"),
            )
            for r in rows
        ]

    @staticmethod
    def _build_where(
        *,
        producer: Optional[str],
        color_family: Optional[str],
        material_type: Optional[str],
        structure: Optional[str],
        role: Optional[str],
        search: Optional[str],
    ) -> tuple[str, list]:
        clauses: list[str] = []
        params: list = []
        if producer:
            clauses.append("producer = ?")
            params.append(producer)
        if color_family:
            clauses.append("color_family = ?")
            params.append(color_family)
        if material_type:
            clauses.append("material_type = ?")
            params.append(material_type)
        if structure:
            clauses.append("structure = ?")
            params.append(structure)
        if role:
            clauses.append("EXISTS (SELECT 1 FROM json_each(roles) WHERE json_each.value = ?)")
            params.append(role)
        if search:
            q = f"%{search}%"
            clauses.append(
                "(decor_name LIKE ? OR decor_id LIKE ? OR structure LIKE ? OR group_name LIKE ?)"
            )
            params.extend([q, q, q, q])

        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        return where, params
