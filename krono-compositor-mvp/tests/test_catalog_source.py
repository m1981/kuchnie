# tests/test_catalog_source.py
"""Catalog source tests (spec: docs/specs/catalog-routing.md Acceptance 2):
decor-row mapping, allowed-zone derivation, offline degradation to
snapshot, and the /api/v1/catalog contract shape — all against a faked
catalog client."""
import json

import pytest

from compositor.presentation.catalog_source import (
    DEFAULT_HEX,
    DEFAULT_TEXTURE_WIDTH_MM,
    CatalogSource,
    CatalogUnavailable,
    _derive_allowed_zone,
    build_materials,
)


def row(decor_id="K5307", name="Dąb Artisan", roles=("front", "carcass"),
        img=None, producer="kronospan", discontinued=False):
    return {
        "decor_id": decor_id,
        "decor_name": name,
        "roles": json.dumps(list(roles)),
        "img": img,
        "producer": producer,
        "discontinued": discontinued,
    }


class FakeClient:
    origin = "http://127.0.0.1:8000"

    def __init__(self, rows=None, hex_map=None, fail_rows=False, fail_hex=False):
        self.rows = rows or []
        self.hex = hex_map or {}
        self.fail_rows = fail_rows
        self.fail_hex = fail_hex

    def iter_rows(self):
        if self.fail_rows:
            raise CatalogUnavailable("down")
        yield from self.rows

    def decor_hex_map(self):
        if self.fail_hex:
            raise CatalogUnavailable("down")
        return self.hex


# ── mapping ──────────────────────────────────────────────────────────────

def test_row_mapping_fields():
    materials = build_materials(
        [row(img="K5307.jpg")], {"K5307": "#A88B68"}, "http://127.0.0.1:8000"
    )
    assert len(materials) == 1
    m = materials[0]
    assert m["id"] == "K5307"
    assert m["name"] == "Dąb Artisan"
    assert m["hex_color"] == "#A88B68"
    assert m["img_url"] == "http://127.0.0.1:8000/producers/kronospan/decors/K5307.jpg"
    assert m["texture_width_mm"] == 1200.0  # local override table
    assert m["price_group"] == 1


def test_unknown_decor_gets_defaults():
    m = build_materials([row(decor_id="K9999", roles=("front",))], {})[0]
    assert m["texture_width_mm"] == DEFAULT_TEXTURE_WIDTH_MM
    assert m["hex_color"] == DEFAULT_HEX
    assert m["img_url"] is None


def test_variants_fold_to_one_material_per_decor():
    rows = [
        row(roles=("front", "carcass")),
        row(roles=("worktop",)),
        row(decor_id="K190", name="Czarny", roles=("front", "carcass")),
    ]
    materials = build_materials(rows, {})
    assert [m["id"] for m in materials] == ["K190", "K5307"]


def test_discontinued_decor_skipped():
    materials = build_materials([row(discontinued=True)], {})
    assert materials == []


# ── allowed-zone derivation ──────────────────────────────────────────────

@pytest.mark.parametrize("roles,expected", [
    ({"front"}, "FRONT_ONLY"),
    ({"worktop"}, "COUNTERTOP_ONLY"),
    ({"front", "carcass"}, "ANY"),
    ({"front", "worktop"}, "ANY"),
    ({"carcass"}, "ANY"),
    (set(), "ANY"),
])
def test_allowed_zone_derivation(roles, expected):
    assert _derive_allowed_zone(roles) == expected


def test_zone_derived_from_union_across_variants():
    # K552: chipboard variant (front+carcass) + worktop variant -> ANY
    rows = [row(decor_id="K552", roles=("front", "carcass")),
            row(decor_id="K552", roles=("worktop",))]
    assert build_materials(rows, {})[0]["allowed_zone"] == "ANY"


# ── contract shape ───────────────────────────────────────────────────────

def test_catalog_payload_contract_shape(tmp_path):
    source = CatalogSource(FakeClient(rows=[row()]), snapshot_path=str(tmp_path / "snap.json"))
    payload = source.get_catalog()
    assert set(payload) == {"price_groups", "materials", "scenes"}
    assert payload["scenes"][0]["angles"]  # frontend reads scenes[0].angles
    assert {"id", "name", "price_group", "allowed_zone", "texture_width_mm",
            "hex_color", "img_url", "renderable"} <= set(payload["materials"][0])


def test_find_material():
    source = CatalogSource(FakeClient(rows=[row()]), snapshot_path="/dev/null")
    assert source.find_material("K5307")["name"] == "Dąb Artisan"
    assert source.find_material("nope") is None


def test_hex_map_failure_is_cosmetic(tmp_path):
    source = CatalogSource(FakeClient(rows=[row()], fail_hex=True),
                           snapshot_path=str(tmp_path / "snap.json"))
    assert source.get_catalog()["materials"][0]["hex_color"] == DEFAULT_HEX


def test_renderable_flag_from_texture_dir(tmp_path):
    (tmp_path / "K5307.jpg").write_bytes(b"\xff\xd8")
    source = CatalogSource(
        FakeClient(rows=[row(), row(decor_id="K190", name="Czarny")]),
        snapshot_path=str(tmp_path / "snap.json"),
        texture_dir=str(tmp_path),
    )
    materials = {m["id"]: m for m in source.get_catalog()["materials"]}
    assert materials["K5307"]["renderable"] is True
    assert materials["K190"]["renderable"] is False


# ── offline degradation ──────────────────────────────────────────────────

def test_offline_degrades_to_snapshot(tmp_path):
    snap = str(tmp_path / "snap.json")
    CatalogSource(FakeClient(rows=[row()]), snapshot_path=snap).get_catalog()

    offline = CatalogSource(FakeClient(fail_rows=True), snapshot_path=snap)
    payload = offline.get_catalog()
    assert payload["materials"][0]["id"] == "K5307"


def test_offline_without_snapshot_serves_empty_materials(tmp_path):
    source = CatalogSource(FakeClient(fail_rows=True),
                           snapshot_path=str(tmp_path / "missing.json"))
    payload = source.get_catalog()
    assert payload["materials"] == []
    assert payload["scenes"]  # scenes are local; the app stays usable
