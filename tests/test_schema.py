"""Schema validation tests — proves YAML structure correctness.

Tests:
  1. Valid kitchen passes schema
  2. Missing required fields fail
  3. Invalid values fail (zero dimensions, bad codes)
  4. Derived validations (cabinets fit in wall, width > 2*sides)
"""

import pytest
import yaml
from pathlib import Path

from kuchnie_core.schema import (
    CabinetSpec,
    DrawerSpec,
    FrontSpec,
    HandleSpec,
    KitchenSchema,
    MaterialSpec,
    RowSpec,
    SettingsSpec,
    ShelfSpec,
    WorktopSpec,
)


# ── Fixtures ─────────────────────────────────────────────────────

@pytest.fixture
def valid_drawer():
    return {
        'id': 'S1',
        'height_mm': 150,
        'system': 'tandembox_antaro',
        'height_code': 'N',
        'nl': 500,
    }


@pytest.fixture
def valid_cabinet():
    return {
        'id': 'K01',
        'type': 'dolna_szufladowa',
        'width_mm': 800,
        'height_mm': 720,
        'depth_mm': 510,
        'body_material': 'swiss_krono.U119_VL',
        'back_material': 'HDF_3mm',
        'front_material': 'swiss_krono.U119_EM',
    }


@pytest.fixture
def valid_kitchen_dict():
    return {
        'version': '2.0',
        'project_name': 'Test Kitchen',
        'materials': {
            'body': 'swiss_krono.U119_VL',
            'front': 'swiss_krono.U119_EM',
        },
        'rows': [{
            'label': 'Wall 1',
            'wall_width_mm': 2400,
            'cabinets': [{
                'id': 'K01',
                'type': 'dolna_szufladowa',
                'width_mm': 800,
                'height_mm': 720,
                'depth_mm': 510,
                'body_material': 'swiss_krono.U119_VL',
                'back_material': 'HDF_3mm',
                'front_material': 'swiss_krono.U119_EM',
            }],
        }],
    }


# ── DrawerSpec ───────────────────────────────────────────────────

class TestDrawerSpec:
    def test_valid_drawer(self, valid_drawer):
        d = DrawerSpec(**valid_drawer)
        assert d.id == 'S1'
        assert d.height_mm == 150
        assert d.height_code == 'N'
        assert d.nl == 500
    
    def test_invalid_height_code(self, valid_drawer):
        valid_drawer['height_code'] = 'X'
        with pytest.raises(ValueError, match='Invalid height code'):
            DrawerSpec(**valid_drawer)
    
    def test_invalid_nl(self, valid_drawer):
        valid_drawer['nl'] = 999
        with pytest.raises(ValueError, match='Invalid NL'):
            DrawerSpec(**valid_drawer)
    
    def test_invalid_system(self, valid_drawer):
        valid_drawer['system'] = 'invalid'
        with pytest.raises(ValueError, match='Invalid system'):
            DrawerSpec(**valid_drawer)
    
    def test_invalid_capacity(self, valid_drawer):
        valid_drawer['capacity_kg'] = 50
        with pytest.raises(ValueError, match='Invalid capacity'):
            DrawerSpec(**valid_drawer)
    
    def test_zero_height_fails(self, valid_drawer):
        valid_drawer['height_mm'] = 0
        with pytest.raises(ValueError):
            DrawerSpec(**valid_drawer)


# ── FrontSpec ────────────────────────────────────────────────────

class TestFrontSpec:
    def test_valid_drawer_front(self):
        f = FrontSpec(id='F1', type='drawer', linked_to='S1')
        assert f.type == 'drawer'
        assert f.linked_to == 'S1'
    
    def test_valid_door_front(self):
        f = FrontSpec(id='F1', type='door', side='right', hinge_count=2)
        assert f.type == 'door'
        assert f.side == 'right'
    
    def test_invalid_type(self):
        with pytest.raises(ValueError, match='Invalid front type'):
            FrontSpec(id='F1', type='invalid')
    
    def test_invalid_side(self):
        with pytest.raises(ValueError, match='Invalid side'):
            FrontSpec(id='F1', type='door', side='invalid')


# ── CabinetSpec ──────────────────────────────────────────────────

class TestCabinetSpec:
    def test_valid_cabinet(self, valid_cabinet):
        c = CabinetSpec(**valid_cabinet)
        assert c.id == 'K01'
        assert c.width_mm == 800
    
    def test_zero_width_fails(self, valid_cabinet):
        valid_cabinet['width_mm'] = 0
        with pytest.raises(ValueError):
            CabinetSpec(**valid_cabinet)
    
    def test_negative_height_fails(self, valid_cabinet):
        valid_cabinet['height_mm'] = -100
        with pytest.raises(ValueError):
            CabinetSpec(**valid_cabinet)
    
    def test_invalid_type_fails(self, valid_cabinet):
        valid_cabinet['type'] = 'invalid_type'
        with pytest.raises(ValueError, match='Invalid cabinet type'):
            CabinetSpec(**valid_cabinet)
    
    def test_width_too_small_for_sides(self, valid_cabinet):
        valid_cabinet['width_mm'] = 30
        valid_cabinet['thickness_side_mm'] = 18
        with pytest.raises(ValueError, match='too small for'):
            CabinetSpec(**valid_cabinet)
    
    def test_with_drawers(self, valid_cabinet, valid_drawer):
        valid_cabinet['drawers'] = [valid_drawer]
        c = CabinetSpec(**valid_cabinet)
        assert len(c.drawers) == 1
        assert c.drawers[0].id == 'S1'


# ── RowSpec ──────────────────────────────────────────────────────

class TestRowSpec:
    def test_valid_row(self, valid_cabinet):
        r = RowSpec(
            label='Wall 1',
            wall_width_mm=2400,
            cabinets=[CabinetSpec(**valid_cabinet)]
        )
        assert r.label == 'Wall 1'
        assert len(r.cabinets) == 1
    
    def test_cabinets_exceed_wall(self, valid_cabinet):
        valid_cabinet['width_mm'] = 3000
        with pytest.raises(ValueError, match='exceeds wall width'):
            RowSpec(
                label='Wall 1',
                wall_width_mm=2400,
                cabinets=[CabinetSpec(**valid_cabinet)]
            )
    
    def test_empty_cabinets_fails(self):
        with pytest.raises(ValueError):
            RowSpec(label='Wall 1', wall_width_mm=2400, cabinets=[])


# ── KitchenSchema ────────────────────────────────────────────────

class TestKitchenSchema:
    def test_valid_kitchen(self, valid_kitchen_dict):
        k = KitchenSchema(**valid_kitchen_dict)
        assert k.version == '2.0'
        assert len(k.rows) == 1
    
    def test_missing_version_fails(self, valid_kitchen_dict):
        del valid_kitchen_dict['version']
        with pytest.raises(ValueError):
            KitchenSchema(**valid_kitchen_dict)
    
    def test_missing_materials_fails(self, valid_kitchen_dict):
        del valid_kitchen_dict['materials']
        with pytest.raises(ValueError):
            KitchenSchema(**valid_kitchen_dict)
    
    def test_missing_rows_fails(self, valid_kitchen_dict):
        del valid_kitchen_dict['rows']
        with pytest.raises(ValueError):
            KitchenSchema(**valid_kitchen_dict)
    
    def test_from_yaml(self, tmp_path, valid_kitchen_dict):
        yaml_path = tmp_path / 'kitchen.yaml'
        yaml_path.write_text(yaml.dump(valid_kitchen_dict))
        
        k = KitchenSchema.from_yaml(yaml_path)
        assert k.version == '2.0'
    
    def test_from_yaml_missing_file(self):
        with pytest.raises(FileNotFoundError):
            KitchenSchema.from_yaml('/nonexistent/kitchen.yaml')
    
    def test_to_yaml(self, tmp_path, valid_kitchen_dict):
        k = KitchenSchema(**valid_kitchen_dict)
        yaml_path = k.to_yaml(tmp_path / 'output.yaml')
        
        assert yaml_path.exists()
        
        # Reload and verify
        k2 = KitchenSchema.from_yaml(yaml_path)
        assert k2.version == k.version


# ── SettingsSpec ─────────────────────────────────────────────────

class TestSettingsSpec:
    def test_defaults(self):
        s = SettingsSpec()
        assert s.base_height == 720
        assert s.corpus_thickness == 18
    
    def test_custom_values(self):
        s = SettingsSpec(base_height=900, corpus_thickness=16)
        assert s.base_height == 900
        assert s.corpus_thickness == 16
    
    def test_zero_base_height_fails(self):
        with pytest.raises(ValueError):
            SettingsSpec(base_height=0)


# ── MaterialSpec ─────────────────────────────────────────────────

class TestMaterialSpec:
    def test_valid_materials(self):
        m = MaterialSpec(body='swiss_krono.U119_VL', front='swiss_krono.U119_EM')
        assert m.body == 'swiss_krono.U119_VL'
        assert m.back == 'HDF_3mm'  # default
    
    def test_missing_body_fails(self):
        with pytest.raises(ValueError):
            MaterialSpec(front='test')
