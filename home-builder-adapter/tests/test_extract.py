"""Seam tests: fake Blender scene → extract → kuchnie_core.Kitchen → JSON.

The adapter is the Anti-Corruption Layer (ADR-009): its one job is to emit
a VALID kuchnie_core.Kitchen. The decisive test is therefore behavioural —
the produced Kitchen must survive the hub's own serialize round-trip and
decompose without error. Constructor drift (Row(name=...), Kitchen(name=...))
is exactly what this catches.
"""

from __future__ import annotations

import pytest

from kuchnie_core.decomposer import decompose
from kuchnie_core.model import Kitchen
from kuchnie_core.serialize import kitchen_from_json_str, kitchen_to_json_str

from src.extract import (
    cabinets_to_kitchen,
    extract_cabinets_from_scene,
)
from tests.conftest import FakeBlenderObject


class TestSceneExtraction:

    def test_meters_become_millimetres(self, fake_bpy, base_cabinet_cage):
        fake_bpy.data.objects = [base_cabinet_cage]
        cabs = extract_cabinets_from_scene()
        assert len(cabs) == 1
        cab = cabs[0]
        assert cab["width_mm"] == 600
        assert cab["depth_mm"] == 560
        assert cab["height_mm"] == 720
        assert cab["toe_kick_mm"] == 100
        assert cab["drawers"] == [176, 320]

    def test_real_hb5_cage_uses_bbox(self, fake_bpy):
        """The real hb5 cage (see walking-skeleton raw-cage-dump.json,
        tr-e60f4fe0) has NO Dim X/Y/Z or opening_sizes ID props — dimensions
        come from the evaluated bounding box, toe kick from its ID prop."""
        cage = FakeBlenderObject(
            props={"IS_FRAMELESS_CABINET_CAGE": True, "CABINET_TYPE": "BASE",
                   "Toe Kick Height": 0.1},
            dimensions=(0.6, 0.56, 0.82),
        )
        fake_bpy.data.objects = [cage]
        cab = extract_cabinets_from_scene()[0]
        assert (cab["width_mm"], cab["depth_mm"], cab["height_mm"]) == \
            (600, 560, 820)
        assert cab["toe_kick_mm"] == 100
        assert cab["drawers"] == []

    def test_non_cage_objects_are_ignored(self, fake_bpy, base_cabinet_cage):
        fake_bpy.data.objects = [
            FakeBlenderObject(props={"IS_FRAMELESS_INTERIOR_PART": True}),
            base_cabinet_cage,
            FakeBlenderObject(),  # lamp, camera, whatever
        ]
        assert len(extract_cabinets_from_scene()) == 1

    def test_shelf_children_are_counted(self, fake_bpy, base_cabinet_cage):
        base_cabinet_cage.children = [
            FakeBlenderObject(props={"IS_FRAMELESS_INTERIOR_PART": True}),
            FakeBlenderObject(props={"IS_FRAMELESS_INTERIOR_PART": True}),
            FakeBlenderObject(),
        ]
        fake_bpy.data.objects = [base_cabinet_cage]
        assert extract_cabinets_from_scene()[0]["shelves"] == 2


class TestKitchenConstruction:

    def _kitchen(self, fake_bpy, cage) -> Kitchen:
        fake_bpy.data.objects = [cage]
        return cabinets_to_kitchen(extract_cabinets_from_scene())

    def test_produces_a_kitchen(self, fake_bpy, base_cabinet_cage):
        """Cold review: Row(name=...) / Kitchen(name=...) / CabinetInstance
        missing four required fields — this constructor path must not raise."""
        kitchen = self._kitchen(fake_bpy, base_cabinet_cage)
        assert isinstance(kitchen, Kitchen)
        assert len(kitchen.rows[0].cabinets) == 1

    def test_toe_kick_maps_to_plinth_height(self, fake_bpy, base_cabinet_cage):
        kitchen = self._kitchen(fake_bpy, base_cabinet_cage)
        assert kitchen.rows[0].cabinets[0].plinth_height_mm == 100

    def test_upper_cabinet_gets_no_plinth(self, fake_bpy):
        cage = FakeBlenderObject(props={
            "IS_FRAMELESS_CABINET_CAGE": True,
            "CABINET_TYPE": "UPPER",
            "Dim X": 0.8, "Dim Y": 0.3, "Dim Z": 0.72,
            "Toe Kick Height": 0.0,
        })
        kitchen = self._kitchen(fake_bpy, cage)
        cab = kitchen.rows[0].cabinets[0]
        assert cab.type == "gorna_drzwiowa"
        assert cab.plinth_height_mm == 0

    def test_drawer_openings_become_drawer_entries(self, fake_bpy, base_cabinet_cage):
        kitchen = self._kitchen(fake_bpy, base_cabinet_cage)
        drawers = kitchen.rows[0].cabinets[0].drawers
        assert [d["wysokosc"] for d in drawers] == [176, 320]
        assert len({d["id"] for d in drawers}) == 2  # unique ids

    def test_kitchen_survives_hub_round_trip_and_decompose(
        self, fake_bpy, base_cabinet_cage
    ):
        """THE contract (ADR-004): adapter output must be consumable by the
        hub — JSON round-trip, then decompose every cabinet."""
        kitchen = self._kitchen(fake_bpy, base_cabinet_cage)
        kitchen2 = kitchen_from_json_str(kitchen_to_json_str(kitchen))
        for row in kitchen2.rows:
            for cab in row.cabinets:
                result = decompose(cab)
                assert result.panels, f"{cab.id}: no panels out of decompose"
