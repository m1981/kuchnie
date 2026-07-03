"""Shared fixtures for kitchen-cam tests.

Fixtures build kuchnie_core.CabinetInstance directly (ADR-010 migration).
The YAML loader populates the legacy fields (shelves, fronts) from YAML;
here we set them directly to match what the loader would produce.
"""

from __future__ import annotations

import pytest

from kuchnie_core.blum_hinges import HingeGeometry
from kuchnie_core.model import (
    CabinetInstance,
    HandleSpec,
    ShelfPinSpec,
)


@pytest.fixture()
def base_door_cabinet() -> CabinetInstance:
    """Standard 800×720×510 base cabinet with one door and one shelf.

    Matches the K01-type dolna_drzwiowa decomposition.
    Side height = 720 - 100 (plinth) = 620mm.
    """
    return CabinetInstance(
        id="K01",
        type="dolna_drzwiowa",
        description="Szafka dolna drzwiowa 800",
        width_mm=800,
        height_mm=720,
        depth_mm=510,
        body_material="U119_VL",
        back_material="HDF_3mm_bialy",
        front_material="U119_EM",
        thickness_side_mm=18,
        thickness_back_mm=3,
        groove_depth_mm=8,
        edge_banding_type="ABS",
        edge_banding_thickness_mm=0.8,
        handles=HandleSpec(spacing_mm=256.0),
        shelf_pins=ShelfPinSpec(
            diameter_mm=5.0,
            depth_mm=8.0,
            front_offset_mm=50.0,
            back_offset_mm=80.0,
            max_per_row=3,
        ),
        hinges=HingeGeometry(
            cup_diameter_mm=35,
            cup_drill_depth_mm=13,
            edge_to_cup_centre_mm=5.0,
            screw_spacing_mm=45.0,
            screw_diameter_mm=3.0,
            screw_depth_mm=2.0,
            first_position_mm=100.0,
        ),
        # Legacy fields — what the YAML loader populates:
        shelves=[{"id": "P1", "pozycja_od_dolu": 352}],
        fronts=[
            {
                "id": "F1",
                "typ": "drzwiowy_lewy",
                "zawias": "blum_clip_35",
                "ilosc_zawiasow": 2,
                "pozycja_pierwszego_zawiasu": 100,
            },
        ],
    )


@pytest.fixture()
def base_drawer_cabinet() -> CabinetInstance:
    """Standard 800×720×510 base cabinet with two drawer fronts.

    Side height = 720 - 100 (plinth) = 620mm.
    """
    return CabinetInstance(
        id="K02",
        type="dolna_szufladowa",
        description="Szafka dolna szufladowa 800",
        width_mm=800,
        height_mm=720,
        depth_mm=510,
        body_material="U119_VL",
        back_material="HDF_3mm_bialy",
        front_material="U119_EM",
        thickness_side_mm=18,
        thickness_back_mm=3,
        groove_depth_mm=8,
        edge_banding_type="ABS",
        edge_banding_thickness_mm=0.8,
        handles=HandleSpec(spacing_mm=256.0),
        shelves=[],
        fronts=[
            {"id": "F1", "typ": "szufladowy"},
            {"id": "F2", "typ": "szufladowy"},
        ],
        drawers=[
            {"id": "S1", "typ": "metabox", "wysokosc": 150},
            {"id": "S2", "typ": "metabox", "wysokosc": 270},
        ],
    )


@pytest.fixture()
def wall_door_cabinet() -> CabinetInstance:
    """Standard 800×720×300 wall cabinet with one door and one shelf."""
    return CabinetInstance(
        id="G01",
        type="gorna_drzwiowa",
        description="Szafka wisząca drzwiowa 800",
        width_mm=800,
        height_mm=720,
        depth_mm=300,
        body_material="U119_VL",
        back_material="HDF_3mm_bialy",
        front_material="U119_EM",
        thickness_side_mm=18,
        thickness_back_mm=3,
        groove_depth_mm=8,
        edge_banding_type="ABS",
        edge_banding_thickness_mm=0.8,
        hinges=HingeGeometry(
            cup_diameter_mm=35,
            cup_drill_depth_mm=13,
            first_position_mm=100.0,
        ),
        shelves=[{"id": "P1", "pozycja_od_dolu": 352}],
        fronts=[
            {
                "id": "F1",
                "typ": "drzwiowy_lewy",
                "zawias": "blum_clip_35",
                "ilosc_zawiasow": 2,
            },
        ],
    )
