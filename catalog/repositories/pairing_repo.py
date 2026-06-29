"""Repository for pairing queries against v_pairings_full."""

from __future__ import annotations

import sqlite3
from typing import Optional

from catalog.models.domain import PairingOut


class PairingRepository:
    def __init__(self, db: sqlite3.Connection):
        self.db = db

    def get_for_decor(
        self,
        business_id: str,
        *,
        pairing_type: Optional[str] = None,
    ) -> list[PairingOut]:
        """Get all pairings where this decor is the front."""
        sql = "SELECT * FROM v_pairings_full WHERE front_decor_id = ?"
        params: list = [business_id]
        if pairing_type:
            sql += " AND pairing_type = ?"
            params.append(pairing_type)
        sql += " ORDER BY priority"

        rows = self.db.execute(sql, params).fetchall()
        return [PairingOut.model_validate(dict(r)) for r in rows]
