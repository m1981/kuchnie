"""Contract tests — proves kuchnie_core can consume Blender export YAML.

Tests:
  1. load_kitchen() succeeds with fixture
  2. decompose_kitchen() produces panels
  3. All panels have positive dimensions
  4. Drawer cabinets have runners
  5. Door cabinets have hinges
"""

import pytest
from pathlib import Path

from kuchnie_core.schema import KitchenSchema
from kuchnie_core.loader import load_kitchen_from_schema
from kuchnie_core.decomposer import decompose
from kuchnie_core.kitchen import decompose_kitchen, all_panels, all_accessories, kitchen_bom
from kuchnie_core.export.cutlist_csv import export_cutlist_csv


FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "contract_test_kitchen.yaml"


# ── Fixture loading ──────────────────────────────────────────────

class TestFixtureLoading:
    """Prove fixture is valid and loadable."""
    
    def test_fixture_exists(self):
        assert FIXTURE_PATH.exists()
    
    def test_fixture_passes_schema(self):
        kitchen = KitchenSchema.from_yaml(FIXTURE_PATH)
        assert kitchen.version == "2.0"
        assert len(kitchen.rows) == 1
    
    def test_fixture_loads_in_kuchnie_core(self):
        kitchen = load_kitchen_from_schema(FIXTURE_PATH)
        assert kitchen.project_name == "Contract Test Kitchen"
        assert len(kitchen.rows) == 1
    
    def test_fixture_has_all_cabinets(self):
        kitchen = load_kitchen_from_schema(FIXTURE_PATH)
        cab_ids = [c.id for c in kitchen.rows[0].cabinets]
        assert "K01" in cab_ids
        assert "K02" in cab_ids
        assert "K03" in cab_ids
        assert "K04" in cab_ids


# ── Decomposition ────────────────────────────────────────────────

class TestDecomposition:
    """Prove all cabinets decompose successfully."""
    
    def test_decompose_kitchen_succeeds(self):
        kitchen = load_kitchen_from_schema(FIXTURE_PATH)
        results = decompose_kitchen(kitchen)
        assert len(results) == 4
    
    def test_all_cabinets_have_panels(self):
        kitchen = load_kitchen_from_schema(FIXTURE_PATH)
        results = decompose_kitchen(kitchen)
        
        for cab_id, result in results.items():
            assert len(result.panels) > 0, f"{cab_id} produced no panels"
    
    def test_all_panels_positive_dimensions(self):
        kitchen = load_kitchen_from_schema(FIXTURE_PATH)
        results = decompose_kitchen(kitchen)
        
        for cab_id, result in results.items():
            for panel in result.panels:
                assert panel.width_mm > 0, f"{cab_id}/{panel.id} width <= 0"
                assert panel.height_mm > 0, f"{cab_id}/{panel.id} height <= 0"
                assert panel.thickness_mm > 0, f"{cab_id}/{panel.id} thickness <= 0"
    
    def test_K01_drawer_cabinet_panels(self):
        """K01 (dolna_szufladowa) should have sides, bottom, back + drawer fronts."""
        kitchen = load_kitchen_from_schema(FIXTURE_PATH)
        cab = kitchen.rows[0].cabinets[0]
        result = decompose(cab)
        
        panel_names = [p.name.lower() for p in result.panels]
        
        # Carcass panels
        assert any("lew" in n for n in panel_names), "Missing left side"
        assert any("praw" in n for n in panel_names), "Missing right side"
        assert any("dno" in n for n in panel_names), "Missing bottom"
        assert any("plecy" in n for n in panel_names), "Missing back"
        
        # Drawer fronts
        fronts = [p for p in result.panels if "front" in p.id.lower()]
        assert len(fronts) == 2, f"Expected 2 drawer fronts, got {len(fronts)}"
    
    def test_K02_door_cabinet_panels(self):
        """K02 (dolna_drzwiowa) should have sides, bottom, back + door front."""
        kitchen = load_kitchen_from_schema(FIXTURE_PATH)
        cab = kitchen.rows[0].cabinets[1]
        result = decompose(cab)
        
        panel_names = [p.name.lower() for p in result.panels]
        
        # Carcass panels
        assert any("lew" in n for n in panel_names), "Missing left side"
        assert any("praw" in n for n in panel_names), "Missing right side"
        assert any("dno" in n for n in panel_names), "Missing bottom"
        assert any("plecy" in n for n in panel_names), "Missing back"
        
        # Door front
        fronts = [p for p in result.panels if "front" in p.id.lower()]
        assert len(fronts) == 1, f"Expected 1 door front, got {len(fronts)}"
    
    def test_K03_wall_cabinet_panels(self):
        """K03 (gorna_drzwiowa) should have sides, top, bottom, back + shelves + doors."""
        kitchen = load_kitchen_from_schema(FIXTURE_PATH)
        cab = kitchen.rows[0].cabinets[2]
        result = decompose(cab)
        
        # Should have shelves
        shelves = [p for p in result.panels if "półka" in p.name.lower()]
        assert len(shelves) == 2, f"Expected 2 shelves, got {len(shelves)}"
    
    def test_K04_legrabox_cabinet_panels(self):
        """K04 (dolna_legrabox) should have drawer box panels."""
        kitchen = load_kitchen_from_schema(FIXTURE_PATH)
        cab = kitchen.rows[0].cabinets[3]
        result = decompose(cab)
        
        # Should have drawer box panels (back + base per drawer)
        drawer_panels = [p for p in result.panels if "szuflada" in p.name.lower()]
        assert len(drawer_panels) >= 4, f"Expected >=4 drawer box panels, got {len(drawer_panels)}"


# ── Accessories ──────────────────────────────────────────────────

class TestAccessories:
    """Prove correct accessories are produced."""
    
    def test_K01_has_runners(self):
        kitchen = load_kitchen_from_schema(FIXTURE_PATH)
        cab = kitchen.rows[0].cabinets[0]
        result = decompose(cab)
        
        runners = [a for a in result.accessories if a.type == "runner"]
        assert len(runners) == 2, f"Expected 2 runners, got {len(runners)}"
    
    def test_K01_has_handles(self):
        kitchen = load_kitchen_from_schema(FIXTURE_PATH)
        cab = kitchen.rows[0].cabinets[0]
        result = decompose(cab)
        
        handles = [a for a in result.accessories if a.type == "handle"]
        assert len(handles) >= 1, "Missing handles"
    
    def test_K02_has_hinges(self):
        kitchen = load_kitchen_from_schema(FIXTURE_PATH)
        cab = kitchen.rows[0].cabinets[1]
        result = decompose(cab)
        
        hinges = [a for a in result.accessories if a.type == "hinge"]
        assert len(hinges) >= 1, f"Expected hinges, got {len(hinges)}"
    
    def test_K02_has_shelf_pins(self):
        kitchen = load_kitchen_from_schema(FIXTURE_PATH)
        cab = kitchen.rows[0].cabinets[1]
        result = decompose(cab)
        
        pins = [a for a in result.accessories if a.type == "shelf_pin"]
        assert len(pins) >= 1, f"Expected shelf pins, got {len(pins)}"
    
    def test_K03_has_hinges(self):
        kitchen = load_kitchen_from_schema(FIXTURE_PATH)
        cab = kitchen.rows[0].cabinets[2]
        result = decompose(cab)
        
        hinges = [a for a in result.accessories if a.type == "hinge"]
        assert len(hinges) >= 2, f"Expected >=2 hinges (2 doors), got {len(hinges)}"
    
    def test_K04_has_legrabox_runners(self):
        kitchen = load_kitchen_from_schema(FIXTURE_PATH)
        cab = kitchen.rows[0].cabinets[3]
        result = decompose(cab)
        
        runners = [a for a in result.accessories if a.type == "runner"]
        assert len(runners) == 2, f"Expected 2 runners, got {len(runners)}"
        
        # Check runner names contain LEGRABOX
        for runner in runners:
            assert "legrabox" in runner.name.lower() or "LEGRABOX" in runner.name, \
                f"Runner name doesn't contain LEGRABOX: {runner.name}"


# ── Kitchen-level aggregation ────────────────────────────────────

class TestKitchenAggregation:
    """Prove kitchen-level functions work correctly."""
    
    def test_all_panels_returns_all(self):
        kitchen = load_kitchen_from_schema(FIXTURE_PATH)
        panels = all_panels(kitchen)
        
        # Should have panels from all 4 cabinets
        assert len(panels) > 10, f"Expected >10 panels, got {len(panels)}"
    
    def test_all_accessories_returns_all(self):
        kitchen = load_kitchen_from_schema(FIXTURE_PATH)
        accessories = all_accessories(kitchen)
        
        # Should have runners, hinges, handles, shelf pins
        types = {a.type for a in accessories}
        assert "runner" in types, "Missing runners"
        assert "hinge" in types, "Missing hinges"
        assert "handle" in types, "Missing handles"
    
    def test_panel_materials_not_empty(self):
        kitchen = load_kitchen_from_schema(FIXTURE_PATH)
        panels = all_panels(kitchen)
        
        for panel in panels:
            assert panel.material, f"Panel {panel.id} has empty material"
            assert panel.thickness_mm > 0, f"Panel {panel.id} has zero thickness"


# ── Integration: BOM + Cut List ──────────────────────────────────

class TestIntegration:
    """Prove full pipeline produces valid output."""
    
    def test_bom_has_all_categories(self):
        kitchen = load_kitchen_from_schema(FIXTURE_PATH)
        bom = kitchen_bom(kitchen)
        
        categories = {item.category for item in bom.items}
        assert "panel" in categories, "Missing panel category"
        assert "edge_band" in categories, "Missing edge_band category"
        assert "accessory" in categories, "Missing accessory category"
    
    def test_bom_items_have_descriptions(self):
        kitchen = load_kitchen_from_schema(FIXTURE_PATH)
        bom = kitchen_bom(kitchen)
        
        for item in bom.items:
            assert item.description, f"BOM item has empty description"
            assert item.material, f"BOM item has empty material"
    
    def test_bom_total_is_sum_of_items(self):
        kitchen = load_kitchen_from_schema(FIXTURE_PATH)
        bom = kitchen_bom(kitchen)
        
        expected = round(sum(i.total for i in bom.items), 2)
        assert abs(bom.total_cost - expected) < 0.01, \
            f"BOM total {bom.total_cost} != sum of items {expected}"
    
    def test_cutlist_csv_is_valid(self, tmp_path):
        kitchen = load_kitchen_from_schema(FIXTURE_PATH)
        csv_path = export_cutlist_csv(kitchen, tmp_path / "cuts.csv")
        
        assert csv_path.exists()
        content = csv_path.read_text()
        lines = content.strip().split("\n")
        
        # Header + at least one data row
        assert len(lines) > 1, "CSV should have header + data rows"
        
        # Header has expected columns
        header = lines[0]
        assert "material" in header.lower() or "materiał" in header.lower(), \
            f"CSV header missing material column: {header}"
    
    def test_cutlist_has_all_panels(self, tmp_path):
        kitchen = load_kitchen_from_schema(FIXTURE_PATH)
        csv_path = export_cutlist_csv(kitchen, tmp_path / "cuts.csv")
        
        content = csv_path.read_text()
        
        # Should have entries for each material type
        assert "swiss_krono.U119_VL" in content, "Missing body material in cut list"
        assert "HDF" in content, "Missing back material in cut list"
