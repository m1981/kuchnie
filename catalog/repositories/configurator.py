"""Configurator repository — session CRUD + step logic.

Handles the 6-step kitchen configurator flow:
  front → carcass → worktop → edge → side_panel → plinth → done
"""

from __future__ import annotations

import json
import sqlite3
import uuid

STEPS = ["front", "carcass", "worktop", "edge", "side_panel", "plinth", "done"]

# Steps that require a variant_id vs edge_id
VARIANT_STEPS = {"front", "carcass", "worktop", "side_panel", "plinth"}
EDGE_STEPS = {"edge"}


def _next_step(step: str) -> str | None:
    idx = STEPS.index(step)
    if idx < len(STEPS) - 1:
        return STEPS[idx + 1]
    return None


def _variant_step_column(step: str) -> str:
    """Map step name to the session column holding the chosen variant."""
    return {
        "front": "front_variant_id",
        "carcass": "carcass_variant_id",
        "worktop": "worktop_variant_id",
        "side_panel": "side_panel_variant_id",
        "plinth": "plinth_variant_id",
    }[step]


class ConfiguratorRepository:
    def __init__(self, db: sqlite3.Connection):
        self.db = db

    # ── Session CRUD ─────────────────────────────────────────────

    def create_session(self) -> dict:
        token = uuid.uuid4().hex[:24]
        self.db.execute(
            "INSERT INTO configurator_sessions (session_token, current_step) "
            "VALUES (?, 'front')",
            (token,),
        )
        self.db.commit()
        return {"session_token": token, "current_step": "front"}

    def get_session(self, token: str) -> dict | None:
        row = self.db.execute(
            "SELECT * FROM configurator_sessions WHERE session_token = ?",
            (token,),
        ).fetchone()
        return dict(row) if row else None

    def update_step(self, token: str, step: str, column: str, value) -> None:
        self.db.execute(
            f"UPDATE configurator_sessions "
            f"SET {column} = ?, current_step = ?, updated_at = datetime('now') "
            f"WHERE session_token = ?",
            (value, step, token),
        )
        self.db.commit()

    # ── Front options ────────────────────────────────────────────

    def front_options(self, color_family: str | None = None) -> list[dict]:
        sql = (
            "SELECT v.business_id AS variant_id, d.name AS decor_name, "
            "       COALESCE(cf.slug, '') AS color_family, "
            "       COALESCE(d.img, '') AS img, "
            "       COALESCE(mt.slug, '') AS material_type, "
            "       COALESCE(s.code, '') AS structure, "
            "       v.thickness_mm "
            "FROM variants v "
            "JOIN decors d ON d.id = v.decor_id "
            "JOIN materials m ON m.id = v.material_id "
            "JOIN material_types mt ON mt.id = m.material_type_id "
            "LEFT JOIN color_families cf ON cf.id = d.color_family_id "
            "LEFT JOIN structures s ON s.id = v.structure_id "
            "WHERE v.roles LIKE '%front%' "
        )
        params: list = []
        if color_family:
            sql += "AND cf.slug = ? "
            params.append(color_family)
        sql += "ORDER BY d.name"
        rows = self.db.execute(sql, params).fetchall()
        return [self._option_from_row(r) for r in rows]

    # ── Carcass options ──────────────────────────────────────────

    def carcass_options(self, front_variant_id: str) -> list[dict]:
        # Get front decor id
        front = self.db.execute(
            "SELECT d.id, d.business_id FROM variants v "
            "JOIN decors d ON d.id = v.decor_id "
            "WHERE v.business_id = ?",
            (front_variant_id,),
        ).fetchone()
        if not front:
            return []

        front_decor_pk = front["id"]

        # Try pairings first
        paired = self.db.execute(
            "SELECT v.business_id AS variant_id, td.name AS decor_name, "
            "       COALESCE(cf.slug, '') AS color_family, "
            "       COALESCE(td.img, '') AS img, "
            "       COALESCE(mt.slug, '') AS material_type, "
            "       COALESCE(s.code, '') AS structure, "
            "       v.thickness_mm, "
            "       p.match_type AS recommendation "
            "FROM pairings p "
            "JOIN decors td ON td.id = p.target_decor_id "
            "JOIN variants v ON v.decor_id = td.id "
            "JOIN materials m ON m.id = v.material_id "
            "JOIN material_types mt ON mt.id = m.material_type_id "
            "LEFT JOIN color_families cf ON cf.id = td.color_family_id "
            "LEFT JOIN structures s ON s.id = v.structure_id "
            "WHERE p.front_decor_id = ? AND p.pairing_type = 'carcass' "
            "ORDER BY p.priority",
            (front_decor_pk,),
        ).fetchall()

        if paired:
            return [self._option_from_row(r) for r in paired]

        # Fallback: all carcass-role variants
        return self._fallback_options("carcass")

    # ── Worktop options ──────────────────────────────────────────

    def worktop_options(self) -> list[dict]:
        return self._fallback_options("worktop")

    # ── Edge options ─────────────────────────────────────────────

    def edge_options(self, front_variant_id: str) -> list[dict]:
        variant = self.db.execute(
            "SELECT id FROM variants WHERE business_id = ?",
            (front_variant_id,),
        ).fetchone()
        if not variant:
            return []

        rows = self.db.execute(
            "SELECT e.id AS edge_id, e.code AS name, "
            "       COALESCE(es.name, '') AS supplier, "
            "       COALESCE(e.finish, '') AS finish, "
            "       COALESCE(e.material, '') AS material, "
            "       e.thickness_mm "
            "FROM variant_edges ve "
            "JOIN edges e ON e.id = ve.edge_id "
            "LEFT JOIN edge_suppliers es ON es.id = e.supplier_id "
            "WHERE ve.variant_id = ? "
            "ORDER BY e.code",
            (variant["id"],),
        ).fetchall()

        if rows:
            return [
                {
                    "edge_id": r["edge_id"],
                    "name": r["name"],
                    "decor_name": r["name"],
                    "material_type": r["material"],
                    "recommendation": "auto_match",
                    "color_family": None,
                    "img_url": None,
                    "structure": r["finish"],
                    "thickness_mm": r["thickness_mm"],
                }
                for r in rows
            ]

        # Fallback: all edges
        rows = self.db.execute(
            "SELECT e.id AS edge_id, e.code AS name, "
            "       COALESCE(es.name, '') AS supplier, "
            "       COALESCE(e.finish, '') AS finish, "
            "       COALESCE(e.material, '') AS material, "
            "       e.thickness_mm "
            "FROM edges e "
            "LEFT JOIN edge_suppliers es ON es.id = e.supplier_id "
            "ORDER BY e.code"
        ).fetchall()
        return [
            {
                "edge_id": r["edge_id"],
                "name": r["name"],
                "decor_name": r["name"],
                "material_type": r["material"],
                "recommendation": "default",
                "color_family": None,
                "img_url": None,
                "structure": r["finish"],
                "thickness_mm": r["thickness_mm"],
            }
            for r in rows
        ]

    # ── Side panel / plinth options ──────────────────────────────

    def side_panel_options(self) -> list[dict]:
        return self._fallback_options("side_panel") or self._fallback_options("front")

    def plinth_options(self) -> list[dict]:
        return self._fallback_options("plinth") or self._fallback_options("carcass")

    # ── BOM ──────────────────────────────────────────────────────

    def build_bom(self, session: dict) -> dict:
        items = []
        for step in ["front", "carcass", "worktop", "side_panel", "plinth"]:
            col = _variant_step_column(step)
            vid = session.get(col)
            if not vid:
                continue
            vrow = self.db.execute(
                "SELECT v.business_id, d.name AS decor_name, "
                "       COALESCE(mt.slug, '') AS material_type, "
                "       COALESCE(s.code, '') AS structure, "
                "       v.thickness_mm "
                "FROM variants v "
                "JOIN decors d ON d.id = v.decor_id "
                "JOIN materials m ON m.id = v.material_id "
                "JOIN material_types mt ON mt.id = m.material_type_id "
                "LEFT JOIN structures s ON s.id = v.structure_id "
                "WHERE v.business_id = ?",
                (vid,),
            ).fetchone()
            if vrow:
                items.append({
                    "role": step,
                    "variant_id": vrow["business_id"],
                    "name": vrow["decor_name"],
                    "decor_name": vrow["decor_name"],
                    "material_type": vrow["material_type"],
                    "structure": vrow["structure"],
                    "thickness_mm": vrow["thickness_mm"],
                })

        edge_id = session.get("edge_id")
        if edge_id:
            erow = self.db.execute(
                "SELECT e.code FROM edges e WHERE e.id = ?",
                (edge_id,),
            ).fetchone()
            if erow:
                items.append({
                    "role": "edge",
                    "edge_id": edge_id,
                    "name": erow["code"],
                    "decor_name": erow["code"],
                })

        complete = session["current_step"] == "done"
        return {"complete": complete, "items": items}

    # ── Helpers ──────────────────────────────────────────────────

    def _fallback_options(self, role: str) -> list[dict]:
        rows = self.db.execute(
            "SELECT v.business_id AS variant_id, d.name AS decor_name, "
            "       COALESCE(cf.slug, '') AS color_family, "
            "       COALESCE(d.img, '') AS img, "
            "       COALESCE(mt.slug, '') AS material_type, "
            "       COALESCE(s.code, '') AS structure, "
            "       v.thickness_mm "
            "FROM variants v "
            "JOIN decors d ON d.id = v.decor_id "
            "JOIN materials m ON m.id = v.material_id "
            "JOIN material_types mt ON mt.id = m.material_type_id "
            "LEFT JOIN color_families cf ON cf.id = d.color_family_id "
            "LEFT JOIN structures s ON s.id = v.structure_id "
            "WHERE v.roles LIKE ? "
            "ORDER BY d.name",
            (f"%{role}%",),
        ).fetchall()
        result = []
        for r in rows:
            opt = self._option_from_row(r)
            opt["recommendation"] = "default"
            result.append(opt)
        return result

    def _option_from_row(self, row) -> dict:
        return {
            "variant_id": row["variant_id"],
            "name": row["decor_name"],
            "decor_name": row["decor_name"],
            "color_family": row["color_family"] or None,
            "img_url": f"/producers/kronospan/decors/{row['img']}" if row["img"] else None,
            "material_type": row["material_type"] or None,
            "structure": row["structure"] or None,
            "thickness_mm": row["thickness_mm"],
            "recommendation": getattr(row, "recommendation", None),
        }
