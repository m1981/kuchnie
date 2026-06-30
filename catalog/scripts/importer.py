"""Catalog importer — YAML dict → SQLite rows.

Design:
    - Takes a plain dict (from YAML) and a live sqlite3.Connection
    - Each section of YAML maps to one import_*() method
    - All methods use INSERT OR IGNORE (idempotent re-runs)
    - FK resolution: slug/code lookup → integer ID
    - Validates required fields (raises ValueError on missing)
    - Returns ImportStats with counts per entity

Usage:
    from catalog.scripts.importer import CatalogImporter, load_yaml

    data = load_yaml("data/kronospan_sample.yaml")
    with get_db("catalog.db") as db:
        importer = CatalogImporter(db)
        stats = importer.import_all(data)
        print(stats)
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

import yaml


# ──────────────────────────────────────────────────────────────────
# Stats
# ──────────────────────────────────────────────────────────────────


@dataclass
class ImportStats:
    producers: int = 0
    collections: int = 0
    structures: int = 0
    materials: int = 0
    decors: int = 0
    variants: int = 0
    worktop_specs: int = 0
    decor_structures: int = 0
    pairings: int = 0
    edges: int = 0
    variant_edges: int = 0
    availability: int = 0
    property_flags: int = 0

    def total(self) -> int:
        return (
            self.producers + self.collections + self.structures
            + self.materials + self.decors + self.variants
            + self.worktop_specs + self.decor_structures + self.pairings
            + self.edges + self.variant_edges
            + self.availability + self.property_flags
        )

    def __repr__(self) -> str:
        parts = []
        for k, v in self.__dict__.items():
            if v > 0:
                parts.append(f"{k}={v}")
        return f"ImportStats({', '.join(parts)})"


# ──────────────────────────────────────────────────────────────────
# Loader
# ──────────────────────────────────────────────────────────────────


def load_yaml(path: str | Path) -> dict:
    """Load a YAML file and return its contents as a dict."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"YAML file not found: {path}")
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


# ──────────────────────────────────────────────────────────────────
# Importer
# ──────────────────────────────────────────────────────────────────


class CatalogImporter:
    """Imports a parsed YAML dict into a SQLite catalog database.

    Call import_all(data) for the full pipeline, or individual
    import_*() methods for selective import.
    """

    def __init__(self, db: sqlite3.Connection):
        self.db = db
        self.db.execute("PRAGMA foreign_keys = ON")

    # ── FK resolution helpers ────────────────────────────────────

    def _lookup_id(
        self, table: str, column: str, value: str | int
    ) -> int | None:
        row = self.db.execute(
            f"SELECT id FROM {table} WHERE {column} = ?", (value,)
        ).fetchone()
        return row[0] if row else None

    def _require_id(
        self, table: str, column: str, value: str | int, context: str
    ) -> int:
        id_ = self._lookup_id(table, column, value)
        if id_ is None:
            raise ValueError(
                f"{context}: {table}.{column}='{value}' not found in DB"
            )
        return id_

    # ── Top-level dispatch ───────────────────────────────────────

    def import_all(self, data: dict) -> ImportStats:
        """Import all sections from a parsed YAML dict.

        Sections are imported in dependency order:
        1. producers (no deps)
        2. structures (depends on producers)
        3. collections (depends on producers)
        4. materials (depends on collections, material_types)
        5. decors (depends on producers, color_families)
        6. variants (depends on decors, materials, structures)
        7. worktops (depends on variants, worktop_constructions, worktop_profiles)
        8. decor_structures (depends on decors, structures)
        9. pairings (depends on decors)
        """
        stats = ImportStats()

        if "producers" in data:
            stats.producers = self.import_producers(data["producers"])

        if "structures" in data:
            stats.structures = self.import_structures(data["structures"])

        if "collections" in data:
            stats.collections = self.import_collections(data["collections"])

        if "materials" in data:
            stats.materials = self.import_materials(data["materials"])

        if "decors" in data:
            stats.decors = self.import_decors(data["decors"])

        if "variants" in data:
            stats.variants = self.import_variants(data["variants"])

        if "worktops" in data:
            stats.worktop_specs = self.import_worktops(data["worktops"])

        if "decor_structures" in data:
            stats.decor_structures = self.import_decor_structures(
                data["decor_structures"]
            )

        if "pairings" in data:
            stats.pairings = self.import_pairings(data["pairings"])

        if "edges" in data:
            stats.edges, stats.variant_edges = self.import_edges(data["edges"])

        if "availability" in data:
            stats.availability = self.import_availability(
                data["availability"]
            )

        if "property_flags" in data:
            stats.property_flags = self.import_property_flags(
                data["property_flags"]
            )

        self.db.commit()
        return stats

    # ── Individual importers ─────────────────────────────────────

    def import_producers(self, items: list[dict]) -> int:
        count = 0
        for item in items:
            _require(item, "slug", "producers")
            _require(item, "name", "producers")
            self.db.execute(
                "INSERT OR IGNORE INTO producers "
                "(slug, name, country, website) "
                "VALUES (?, ?, ?, ?)",
                (
                    item["slug"],
                    item["name"],
                    item.get("country"),
                    item.get("website"),
                ),
            )
            count += 1
        return count

    def import_structures(self, items: list[dict]) -> int:
        count = 0
        for item in items:
            _require(item, "code", "structures")
            _require(item, "name", "structures")
            producer_id = None
            if "producer_slug" in item:
                producer_id = self._require_id(
                    "producers", "slug", item["producer_slug"],
                    f"structure {item['code']}"
                )
            self.db.execute(
                "INSERT OR IGNORE INTO structures "
                "(code, name, type, finish, fingerprint_resistant, "
                " synchronized_texture, producer_id) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    item["code"],
                    item["name"],
                    item.get("type"),
                    item.get("finish"),
                    item.get("fingerprint_resistant", False),
                    item.get("synchronized_texture", False),
                    producer_id,
                ),
            )
            count += 1
        return count

    def import_collections(self, items: list[dict]) -> int:
        count = 0
        for item in items:
            _require(item, "slug", "collections")
            _require(item, "producer_slug", "collections")
            _require(item, "name", "collections")
            producer_id = self._require_id(
                "producers", "slug", item["producer_slug"],
                f"collection {item['slug']}"
            )
            self.db.execute(
                "INSERT OR IGNORE INTO collections "
                "(slug, producer_id, name, source_pdf, "
                " has_edgebanding, has_countertops, has_express) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    item["slug"],
                    producer_id,
                    item["name"],
                    item.get("source_pdf"),
                    item.get("has_edgebanding", True),
                    item.get("has_countertops", False),
                    item.get("has_express", False),
                ),
            )
            count += 1
        return count

    def import_materials(self, items: list[dict]) -> int:
        count = 0
        for item in items:
            _require(item, "slug", "materials")
            _require(item, "collection_slug", "materials")
            _require(item, "name", "materials")

            # material_type is optional — resolve from slug if given,
            # otherwise infer from other fields. For now, require it.
            _require(item, "material_type_slug", "materials")
            mt_id = self._require_id(
                "material_types", "slug", item["material_type_slug"],
                f"material {item['slug']}"
            )
            col_id = self._require_id(
                "collections", "slug", item["collection_slug"],
                f"material {item['slug']}"
            )
            sc_id = None
            if "subcollection_slug" in item:
                sc_id = self._require_id(
                    "subcollections", "slug", item["subcollection_slug"],
                    f"material {item['slug']}"
                )
            self.db.execute(
                "INSERT OR IGNORE INTO materials "
                "(slug, material_type_id, collection_id, subcollection_id, "
                " name, sidedness, has_edgebanding, has_hdf, has_express) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    item["slug"],
                    mt_id,
                    col_id,
                    sc_id,
                    item["name"],
                    item.get("sidedness"),
                    item.get("has_edgebanding", True),
                    item.get("has_hdf", False),
                    item.get("has_express", False),
                ),
            )
            count += 1
        return count

    def import_decors(self, items: list[dict]) -> int:
        count = 0
        for item in items:
            _require(item, "business_id", "decors")
            _require(item, "producer_slug", "decors")
            _require(item, "name", "decors")

            producer_id = self._require_id(
                "producers", "slug", item["producer_slug"],
                f"decor {item['business_id']}"
            )
            color_family_id = None
            if "color_family_slug" in item:
                color_family_id = self._lookup_id(
                    "color_families", "slug", item["color_family_slug"]
                )

            self.db.execute(
                "INSERT OR IGNORE INTO decors "
                "(business_id, producer_id, name, name_en, group_name, "
                " color_family_id, ncs, ral, pantone, img, "
                " one_global, new_2024, discontinued, notes) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    item["business_id"],
                    producer_id,
                    item["name"],
                    item.get("name_en"),
                    item.get("group_name"),
                    color_family_id,
                    item.get("ncs"),
                    item.get("ral"),
                    item.get("pantone"),
                    item.get("img"),
                    item.get("one_global", False),
                    item.get("new_2024", False),
                    item.get("discontinued", False),
                    item.get("notes"),
                ),
            )
            count += 1
        return count

    def import_variants(self, items: list[dict]) -> int:
        count = 0
        for item in items:
            _require(item, "business_id", "variants")
            _require(item, "decor_code", "variants")
            _require(item, "material_slug", "variants")

            decor_id = self._require_id(
                "decors", "business_id", item["decor_code"],
                f"variant {item['business_id']}"
            )
            material_id = self._require_id(
                "materials", "slug", item["material_slug"],
                f"variant {item['business_id']}"
            )
            structure_id = None
            if "structure_code" in item:
                structure_id = self._require_id(
                    "structures", "code", item["structure_code"],
                    f"variant {item['business_id']}"
                )
            sheet_format_id = None
            if "sheet_format_slug" in item:
                sheet_format_id = self._require_id(
                    "sheet_formats", "slug", item["sheet_format_slug"],
                    f"variant {item['business_id']}"
                )

            # roles can be a list or a JSON string
            roles = item.get("roles", ["front"])
            if isinstance(roles, list):
                import json as _json
                roles_str = _json.dumps(roles)
            else:
                roles_str = str(roles)

            self.db.execute(
                "INSERT OR IGNORE INTO variants "
                "(business_id, decor_id, material_id, structure_id, "
                " sheet_format_id, thickness_mm, width_mm, length_mm, "
                " sidedness, roles, multi_structures, "
                " hpl_available, splashback_available, notes) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    item["business_id"],
                    decor_id,
                    material_id,
                    structure_id,
                    sheet_format_id,
                    item.get("thickness_mm"),
                    item.get("width_mm"),
                    item.get("length_mm"),
                    item.get("sidedness"),
                    roles_str,
                    item.get("multi_structures"),
                    item.get("hpl_available", False),
                    item.get("splashback_available", False),
                    item.get("notes"),
                ),
            )
            count += 1
        return count

    def import_worktops(self, items: list[dict]) -> int:
        count = 0
        for item in items:
            _require(item, "variant_business_id", "worktops")
            _require(item, "construction_slug", "worktops")
            _require(item, "profile_code", "worktops")
            _require(item, "available_widths_mm", "worktops")

            variant_id = self._require_id(
                "variants", "business_id", item["variant_business_id"],
                f"worktop_spec for {item['variant_business_id']}"
            )
            construction_id = self._require_id(
                "worktop_constructions", "slug", item["construction_slug"],
                f"worktop_spec for {item['variant_business_id']}"
            )
            profile_id = self._require_id(
                "worktop_profiles", "code", item["profile_code"],
                f"worktop_spec for {item['variant_business_id']}"
            )

            widths = item["available_widths_mm"]
            if isinstance(widths, list):
                import json as _json
                widths_str = _json.dumps(widths)
            else:
                widths_str = str(widths)

            self.db.execute(
                "INSERT OR IGNORE INTO worktop_specs "
                "(variant_id, construction_id, profile_id, "
                " max_length_mm, available_widths_mm, edge_material, "
                " edge_material_thickness_mm, core_color, "
                " splashback_available, matching_board_available, "
                " pieces_per_pallet, pallet_weight_kg, notes) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    variant_id,
                    construction_id,
                    profile_id,
                    item.get("max_length_mm", 4100),
                    widths_str,
                    item.get("edge_material"),
                    item.get("edge_material_thickness_mm"),
                    item.get("core_color"),
                    item.get("splashback_available", False),
                    item.get("matching_board_available", False),
                    item.get("pieces_per_pallet"),
                    item.get("pallet_weight_kg"),
                    item.get("notes"),
                ),
            )
            count += 1
        return count

    def import_decor_structures(self, items: list[dict]) -> int:
        count = 0
        for item in items:
            _require(item, "decor_code", "decor_structures")
            _require(item, "structure_code", "decor_structures")

            decor_id = self._require_id(
                "decors", "business_id", item["decor_code"],
                f"decor_structure {item['decor_code']}"
            )
            structure_id = self._require_id(
                "structures", "code", item["structure_code"],
                f"decor_structure {item['structure_code']}"
            )
            self.db.execute(
                "INSERT OR IGNORE INTO decor_structures "
                "(decor_id, structure_id, is_primary) "
                "VALUES (?, ?, ?)",
                (
                    decor_id,
                    structure_id,
                    item.get("is_primary", False),
                ),
            )
            count += 1
        return count

    def import_pairings(self, items: list[dict]) -> int:
        count = 0
        for item in items:
            _require(item, "front_decor_code", "pairings")
            _require(item, "target_decor_code", "pairings")
            _require(item, "pairing_type", "pairings")

            front_id = self._require_id(
                "decors", "business_id", item["front_decor_code"],
                f"pairing {item['front_decor_code']}→{item['target_decor_code']}"
            )
            target_id = self._require_id(
                "decors", "business_id", item["target_decor_code"],
                f"pairing {item['front_decor_code']}→{item['target_decor_code']}"
            )
            self.db.execute(
                "INSERT OR IGNORE INTO pairings "
                "(front_decor_id, target_decor_id, pairing_type, "
                " match_type, priority, notes) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    front_id,
                    target_id,
                    item["pairing_type"],
                    item.get("match_type", "exact"),
                    item.get("priority", 1),
                    item.get("notes"),
                ),
            )
            count += 1
        return count

    def import_edges(self, items: list[dict]) -> tuple[int, int]:
        """Import edges and variant-edge links.

        YAML format:
          edges:
            - code: K-0110-SM
              supplier_slug: schilsner
              material: ABS
              variant_ids:
                - K110-CH-18-SM

        Returns (edges_added, variant_edges_added).
        """
        edges_count = 0
        links_count = 0
        for item in items:
            _require(item, "code", "edges")

            supplier_id = None
            if item.get("supplier_slug"):
                supplier_id = self._require_id(
                    "edge_suppliers", "slug", item["supplier_slug"],
                    f"edge {item['code']}"
                )

            self.db.execute(
                "INSERT OR IGNORE INTO edges "
                "(code, supplier_id, material, finish, thickness_mm, width_mm, notes) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    item["code"],
                    supplier_id,
                    item.get("material", "ABS"),
                    item.get("finish"),
                    item.get("thickness_mm"),
                    item.get("width_mm"),
                    item.get("notes"),
                ),
            )
            edges_count += 1

            edge_id = self.db.execute(
                "SELECT id FROM edges WHERE code = ?", (item["code"],)
            ).fetchone()[0]

            for vid in item.get("variant_ids", []):
                variant_id = self._require_id(
                    "variants", "business_id", vid,
                    f"variant_edge {vid}→{item['code']}"
                )
                self.db.execute(
                    "INSERT OR IGNORE INTO variant_edges (variant_id, edge_id) "
                    "VALUES (?, ?)",
                    (variant_id, edge_id),
                )
                links_count += 1

        return edges_count, links_count

    def import_availability(self, items: list[dict]) -> int:
        """Import variant availability data.

        YAML format:
          availability:
            - variant_business_id: "K8685-CH-18-SM"
              channel: express_24h
              available: true
              warehouse: Mielec
              lead_time: 24h
        """
        count = 0
        for item in items:
            _require(item, "variant_business_id", "availability")
            _require(item, "channel", "availability")

            variant_id = self._require_id(
                "variants", "business_id", item["variant_business_id"],
                f"availability for {item['variant_business_id']}"
            )
            self.db.execute(
                "INSERT OR IGNORE INTO variant_availability "
                "(variant_id, channel, available, min_order_qty, "
                " warehouse, lead_time, notes) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    variant_id,
                    item["channel"],
                    item.get("available", True),
                    item.get("min_order_qty", 1),
                    item.get("warehouse"),
                    item.get("lead_time"),
                    item.get("notes"),
                ),
            )
            count += 1
        return count

    def import_property_flags(self, items: list[dict]) -> int:
        """Import variant property flags (EAV-style).

        YAML format:
          property_flags:
            - variant_business_id: "U190-BW-12"
              property: antibacterial
              value: true
        """
        count = 0
        for item in items:
            _require(item, "variant_business_id", "property_flags")
            _require(item, "property", "property_flags")

            variant_id = self._require_id(
                "variants", "business_id", item["variant_business_id"],
                f"property_flags for {item['variant_business_id']}"
            )
            self.db.execute(
                "INSERT OR IGNORE INTO property_flags "
                "(variant_id, property, value, source, notes) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    variant_id,
                    item["property"],
                    item.get("value", True),
                    item.get("source"),
                    item.get("notes"),
                ),
            )
            count += 1
        return count


# ──────────────────────────────────────────────────────────────────
# Validation helper
# ──────────────────────────────────────────────────────────────────


def _require(item: dict, key: str, section: str):
    """Raise ValueError if key is missing or None in item dict."""
    if key not in item or item[key] is None:
        raise ValueError(
            f"[{section}] Required field '{key}' missing. "
            f"Available keys: {list(item.keys())}"
        )
