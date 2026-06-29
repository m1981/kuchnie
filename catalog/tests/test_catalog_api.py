"""Expectancy tests for the catalog API.

These tests define the expected behavior BEFORE implementation.
Each test exercises a specific contract from the API spec.
"""

from __future__ import annotations


# ── 1. PRODUCERS ─────────────────────────────────────────────────


class TestProducers:
    def test_list_returns_all_producers(self, client):
        resp = client.get("/catalog/producers")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_producer_has_expected_fields(self, client):
        resp = client.get("/catalog/producers")
        prod = resp.json()[0]
        assert "id" in prod
        assert "slug" in prod
        assert "name" in prod
        assert prod["slug"] == "kronospan"
        assert prod["name"] == "Kronospan"


# ── 2. DECORS (list) ────────────────────────────────────────────


class TestDecorsList:
    def test_list_all_decors(self, client):
        resp = client.get("/catalog/decors")
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        assert "total" in body
        assert body["total"] >= 5  # 7 decors in sample, but each variant = 1 row

    def test_filter_by_producer(self, client):
        resp = client.get("/catalog/decors?producer=kronospan")
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            assert item["producer"] == "kronospan"

    def test_filter_by_color_family(self, client):
        resp = client.get("/catalog/decors?color_family=bialy")
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            assert item["color_family"] == "bialy"

    def test_filter_by_material_type(self, client):
        resp = client.get("/catalog/decors?material_type=chipboard")
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            assert item["material_type"] == "chipboard"

    def test_filter_by_structure(self, client):
        resp = client.get("/catalog/decors?structure=SM")
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            assert item["structure"] == "SM"

    def test_filter_by_role(self, client):
        resp = client.get("/catalog/decors?role=worktop")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 2  # 868S-PF, 7045-PF, K749-SL
        for item in resp.json()["items"]:
            assert "worktop" in item["roles"]

    def test_search_by_name(self, client):
        resp = client.get("/catalog/decors?search=Biel")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_search_by_code(self, client):
        resp = client.get("/catalog/decors?search=K8685")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_pagination(self, client):
        resp = client.get("/catalog/decors?page=1&page_size=2")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["items"]) <= 2
        assert body["page"] == 1
        assert body["page_size"] == 2


# ── 3. DECOR DETAIL ─────────────────────────────────────────────


class TestDecorDetail:
    def test_get_existing_decor(self, client):
        resp = client.get("/catalog/decors/K8685")
        assert resp.status_code == 200
        body = resp.json()
        assert body["decor_id"] == "K8685"
        assert body["decor_name"] == "Biel Alpejska"
        assert body["producer"] == "kronospan"
        assert isinstance(body["variants"], list)
        assert len(body["variants"]) >= 1

    def test_get_nonexistent_decor(self, client):
        resp = client.get("/catalog/decors/ZZZZZ")
        assert resp.status_code == 404

    def test_variant_has_expected_fields(self, client):
        resp = client.get("/catalog/decors/K8685")
        variant = resp.json()["variants"][0]
        assert "variant_id" in variant
        assert "material_type" in variant
        assert "roles" in variant


# ── 4. DECOR VARIANTS ───────────────────────────────────────────


class TestDecorVariants:
    def test_get_variants(self, client):
        resp = client.get("/catalog/decors/K8685/variants")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["variant_id"] == "K8685-CH-18-SM"

    def test_filter_variants_by_material_type(self, client):
        resp = client.get("/catalog/decors/K8685/variants?material_type=chipboard")
        assert resp.status_code == 200
        for v in resp.json():
            assert v["material_type"] == "chipboard"


# ── 5. DECOR PAIRINGS ───────────────────────────────────────────


class TestDecorPairings:
    def test_get_pairings(self, client):
        resp = client.get("/catalog/decors/K8685/pairings")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_pairing_has_expected_fields(self, client):
        resp = client.get("/catalog/decors/K8685/pairings")
        pairing = resp.json()[0]
        assert pairing["front_decor_id"] == "K8685"
        assert "target_decor_id" in pairing
        assert "pairing_type" in pairing
        assert "match_type" in pairing
        assert "priority" in pairing

    def test_filter_by_pairing_type(self, client):
        resp = client.get("/catalog/decors/K8685/pairings?pairing_type=worktop")
        assert resp.status_code == 200
        for p in resp.json():
            assert p["pairing_type"] == "worktop"


# ── 6. WORKTOPS ─────────────────────────────────────────────────


class TestWorktops:
    def test_list_all_worktops(self, client):
        resp = client.get("/catalog/worktops")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 3  # 868S-PF-U-600, 7045-PF-UU-900, K749-SL-12

    def test_filter_by_construction(self, client):
        resp = client.get("/catalog/worktops?construction=postformed")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2  # 868S-PF-U-600, 7045-PF-UU-900
        for w in data:
            assert w["construction"] == "postformed"

    def test_worktop_has_expected_fields(self, client):
        resp = client.get("/catalog/worktops?construction=postformed")
        wt = resp.json()[0]
        assert "variant_id" in wt
        assert "decor_id" in wt
        assert "construction" in wt
        assert "profile_code" in wt
        assert "max_length_mm" in wt
        assert "available_widths_mm" in wt
        assert wt["max_length_mm"] == 4100

    def test_slim_line_worktop(self, client):
        resp = client.get("/catalog/worktops?construction=slim_line")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["variant_id"] == "K749-SL-12"
        assert data[0]["core_color"] == "Beżowy"


# ── 7. AVAILABILITY ─────────────────────────────────────────────


class TestAvailability:
    def test_no_availability_in_sample(self, client):
        """Sample YAML has no availability section → empty result."""
        resp = client.get("/catalog/availability")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_filter_returns_empty_for_unknown_channel(self, client):
        resp = client.get("/catalog/availability?channel=express_24h")
        assert resp.status_code == 200
        assert resp.json() == []


# ── 8. ADMIN ────────────────────────────────────────────────────


class TestAdmin:
    def test_stats(self, client):
        resp = client.get("/catalog/admin/stats")
        assert resp.status_code == 200
        stats = resp.json()
        assert stats["producers"] == 1
        assert stats["decors"] == 7
        assert stats["variants"] == 5
        assert stats["pairings"] == 3
        assert stats["worktops"] == 3


# ── 9. IMPORTER (direct) ────────────────────────────────────────


class TestImporter:
    def test_import_returns_correct_counts(self, db_seeded):
        """Verify importer populated the DB correctly."""
        db = db_seeded
        decors = db.execute("SELECT COUNT(*) FROM decors").fetchone()[0]
        variants = db.execute("SELECT COUNT(*) FROM variants").fetchone()[0]
        pairings = db.execute("SELECT COUNT(*) FROM pairings").fetchone()[0]
        worktops = db.execute("SELECT COUNT(*) FROM worktop_specs").fetchone()[0]
        assert decors == 7
        assert variants == 5
        assert pairings == 3
        assert worktops == 3

    def test_worktop_specs_joined_correctly(self, db_seeded):
        """Verify the worktop_specs → variants join works."""
        db = db_seeded
        row = db.execute(
            "SELECT v.business_id, ws.max_length_mm "
            "FROM worktop_specs ws "
            "JOIN variants v ON v.id = ws.variant_id "
            "WHERE v.business_id = '868S-PF-U-600'"
        ).fetchone()
        assert row is not None
        assert row[1] == 4100

    def test_pairings_resolved_to_decors(self, db_seeded):
        """Verify pairings → decors FK works."""
        db = db_seeded
        row = db.execute(
            "SELECT fd.business_id, td.business_id, p.pairing_type "
            "FROM pairings p "
            "JOIN decors fd ON fd.id = p.front_decor_id "
            "JOIN decors td ON td.id = p.target_decor_id "
            "WHERE fd.business_id = 'K8685' AND p.pairing_type = 'worktop'"
        ).fetchone()
        assert row is not None
        assert row[0] == "K8685"
        assert row[1] == "868S"
        assert row[2] == "worktop"

    def test_views_return_data(self, db_seeded):
        """Verify all views produce results from sample data."""
        db = db_seeded
        assert db.execute("SELECT COUNT(*) FROM v_decors_full").fetchone()[0] == 5
        assert db.execute("SELECT COUNT(*) FROM v_pairings_full").fetchone()[0] == 3
        assert db.execute("SELECT COUNT(*) FROM v_worktops_full").fetchone()[0] == 3
