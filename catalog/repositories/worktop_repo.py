"""Repository for worktop queries against v_worktops_full."""

from __future__ import annotations

import sqlite3
from typing import Optional

from catalog.models.domain import WorktopOut


class WorktopRepository:
    def __init__(self, db: sqlite3.Connection):
        self.db = db

    def list_filtered(
        self,
        *,
        construction: Optional[str] = None,
        producer: Optional[str] = None,
    ) -> list[WorktopOut]:
        """Return worktops, optionally filtered."""
        sql = "SELECT * FROM v_worktops_full"
        clauses: list[str] = []
        params: list = []

        if construction:
            clauses.append("construction = ?")
            params.append(construction)
        if producer:
            clauses.append("producer = ?")
            params.append(producer)

        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY decor_name_pl, variant_id"

        rows = self.db.execute(sql, params).fetchall()
        return [WorktopOut.model_validate(dict(r)) for r in rows]
