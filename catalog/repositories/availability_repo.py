"""Repository for availability queries against v_variants_availability."""

from __future__ import annotations

import sqlite3
from typing import Optional

from catalog.models.domain import AvailabilityOut


class AvailabilityRepository:
    def __init__(self, db: sqlite3.Connection):
        self.db = db

    def list_filtered(
        self,
        *,
        channel: Optional[str] = None,
        producer: Optional[str] = None,
    ) -> list[AvailabilityOut]:
        """Return variant availability, optionally filtered."""
        sql = "SELECT * FROM v_variants_availability"
        clauses: list[str] = []
        params: list = []

        if channel:
            clauses.append("channel = ?")
            params.append(channel)
        if producer:
            clauses.append("producer = ?")
            params.append(producer)

        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY variant_id, channel"

        rows = self.db.execute(sql, params).fetchall()
        return [AvailabilityOut.model_validate(dict(r)) for r in rows]
