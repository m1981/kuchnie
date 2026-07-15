"""Extraction r2 (wk-81a47ab8): drawer stacks read from the cage hierarchy.

The fake scene mirrors the committed proof of what a saved hb5 scene
demonstrably stores — exercises/e2e-d60-legrabox/generated/cage-hierarchy.json
for the D60 LEGRABOX cabinet:

    Bay -> Splitter Vertical (IS_FRAMELESS_SPLITTER_VERTICAL_CAGE)
        -> Opening 1..3 (IS_FRAMELESS_OPENING_CAGE, geo-node Dim Z
           0.140 / 0.254 / 0.254, named TOP-DOWN)
        -> Drawers insert -> Drawer Front (IS_DRAWER_FRONT)
        -> Drawer Box (IS_DRAWER_BOX + clearance props)

ORDER CONTRACT under test: CabinetInstance.drawers is BOTTOM-UP (G8,
tr-00330365, kuchnie-core/tests/test_drawer_order.py); hb5 openings
enumerate top-down, so extraction must reverse. Never imports bpy —
conftest installs the fake before src.* import.
"""

from __future__ import annotations

from kuchnie_core.decomposer import decompose
from kuchnie_core.serialize import kitchen_from_json_str, kitchen_to_json_str

from src.extract import cabinets_to_kitchen, extract_cabinets_from_scene
from tests.conftest import FakeBlenderObject, FakeMaterial

# Values verbatim from cage-hierarchy.json (meters, float noise included).
_DIM_Z_TOP = 0.14000000059604645     # Opening 1 — the top (M) drawer
_DIM_Z_MID = 0.25400009751319885     # Opening 2
_DIM_Z_BOT = 0.25400009751319885     # Opening 3 — the bottom drawer
_FINISH = "Default Style Finish"
_INTERIOR = "Default Style Interior"


def _drawer_opening(index: int, dim_z: float) -> FakeBlenderObject:
    """One 'Opening N' cage holding a Drawers insert -> front -> box."""
    box = FakeBlenderObject(
        name=f"Drawer Box.{index:03d}",
        props={"IS_DRAWER_BOX": True, "IS_FRAMELESS_INTERIOR_PART": True},
        gn_inputs={"Dim X": 0.5386, "Dim Y": 0.5166, "Dim Z": 0.108,
                   "Material": None},
    )
    front = FakeBlenderObject(
        name=f"Drawer Front.{index:03d}",
        props={
            "CABINET_PART": True, "IS_CABINET_FRONT": True,
            "IS_DRAWER_FRONT": True,
            "Drawer Box Side Clearance": 0.0127,
            "Drawer Box Top Clearance": 0.01905,
            "Drawer Box Rear Clearance": 0.0254,
            "Drawer Box Bottom Clearance": 0.0127,
        },
        children=[box],
        gn_inputs={"Top Surface": FakeMaterial(_FINISH)},
    )
    drawers_insert = FakeBlenderObject(
        name=f"Drawers.{index:03d}",
        props={"IS_FRAMELESS_OPENING_CAGE": True},
        children=[front],
        gn_inputs={"Dim Z": dim_z},
    )
    return FakeBlenderObject(
        name=f"Opening {index}",
        props={"IS_FRAMELESS_OPENING_CAGE": True},
        children=[drawers_insert],
        gn_inputs={"Dim X": 0.564, "Dim Y": 0.542, "Dim Z": dim_z},
    )


def _d60_cage(openings: list[FakeBlenderObject] | None = None,
              ) -> FakeBlenderObject:
    """The D60 LEGRABOX cage, three drawer openings named top-down."""
    if openings is None:
        openings = [_drawer_opening(1, _DIM_Z_TOP),
                    _drawer_opening(2, _DIM_Z_MID),
                    _drawer_opening(3, _DIM_Z_BOT)]
    splitter = FakeBlenderObject(
        name="Splitter Vertical",
        props={"IS_FRAMELESS_SPLITTER_VERTICAL_CAGE": True,
               "Material Thickness": 0.018},
        children=[
            FakeBlenderObject(name="Calc Object"),
            *openings,
            FakeBlenderObject(name="Vertical Splitter 1",
                              props={"CABINET_PART": True},
                              gn_inputs={"Top Surface":
                                         FakeMaterial(_INTERIOR)}),
        ],
    )
    bay = FakeBlenderObject(name="Bay",
                            props={"IS_FRAMELESS_BAY_CAGE": True},
                            children=[splitter])
    return FakeBlenderObject(
        name="B600-3DW-01 D60 Legrabox",
        props={"IS_FRAMELESS_CABINET_CAGE": True, "CABINET_TYPE": "BASE",
               "Toe Kick Height": 0.10000000149011612,
               "Material Thickness": 0.018},
        dimensions=(0.6000000238418579, 0.5600000023841858,
                    0.8199999928474426),
        children=[
            FakeBlenderObject(name="Left Side",
                              props={"CABINET_PART": True},
                              gn_inputs={"Top Surface":
                                         FakeMaterial(_INTERIOR)}),
            bay,
            FakeBlenderObject(name="Back", props={"CABINET_PART": True}),
        ],
    )


class TestDrawerStackExtraction:

    def _cab(self, fake_bpy, cage):
        fake_bpy.data.objects = [cage]
        cabs = extract_cabinets_from_scene()
        assert len(cabs) == 1
        return cabs[0]

    def test_drawer_stack_promotes_base_to_dolna_legrabox(self, fake_bpy):
        assert self._cab(fake_bpy, _d60_cage())["type"] == "dolna_legrabox"

    def test_drawer_count_is_three(self, fake_bpy):
        assert len(self._cab(fake_bpy, _d60_cage())["drawers"]) == 3

    def test_heights_reversed_to_bottom_up(self, fake_bpy):
        """Scene stores Opening 1..3 TOP-DOWN (140 = the top M drawer);
        the drawers contract is BOTTOM-UP (G8, tr-00330365) — so the M
        opening must come out LAST."""
        assert self._cab(fake_bpy, _d60_cage())["drawers"] == [254, 254, 140]

    def test_opening_name_index_wins_over_scene_child_order(self, fake_bpy):
        """Blender child order is not guaranteed; 'Opening N' names carry
        the top-down position and must be the ordering authority."""
        shuffled = [_drawer_opening(2, _DIM_Z_MID),
                    _drawer_opening(3, _DIM_Z_BOT),
                    _drawer_opening(1, _DIM_Z_TOP)]
        cab = self._cab(fake_bpy, _d60_cage(openings=shuffled))
        assert cab["drawers"] == [254, 254, 140]

    def test_envelope_still_read_from_bbox(self, fake_bpy):
        cab = self._cab(fake_bpy, _d60_cage())
        assert (cab["width_mm"], cab["depth_mm"], cab["height_mm"]) == \
            (600, 560, 820)
        assert cab["toe_kick_mm"] == 100

    def test_opening_without_drawer_front_is_not_a_drawer(self, fake_bpy):
        """A splitter opening holding a door/shelf insert must not count;
        with no drawer front anywhere the r1 BASE fallback stays."""
        door_opening = FakeBlenderObject(
            name="Opening 1",
            props={"IS_FRAMELESS_OPENING_CAGE": True},
            children=[FakeBlenderObject(
                name="Door", props={"CABINET_PART": True,
                                    "IS_CABINET_FRONT": True})],
            gn_inputs={"Dim Z": 0.684},
        )
        cab = self._cab(fake_bpy, _d60_cage(openings=[door_opening]))
        assert cab["drawers"] == []
        assert cab["type"] == "dolna_drzwiowa"

    def test_r1_cabinet_without_splitter_unchanged(self, fake_bpy,
                                                   base_cabinet_cage):
        """The r1 legacy path (opening_sizes ID prop, no cage hierarchy)
        must behave exactly as before r2."""
        cab = self._cab(fake_bpy, base_cabinet_cage)
        assert cab["type"] == "dolna_drzwiowa"
        assert cab["drawers"] == [176, 320]


class TestPartMaterials:

    def test_material_names_extracted_where_present(self, fake_bpy):
        fake_bpy.data.objects = [_d60_cage()]
        mats = extract_cabinets_from_scene()[0]["part_materials"]
        assert mats["Left Side"] == _INTERIOR
        assert mats["Drawer Front.001"] == _FINISH

    def test_unassigned_part_stays_none(self, fake_bpy):
        """'Back' has no material sockets and the Drawer Box 'Material'
        socket is None in the scene — both stay None (GAP posture)."""
        fake_bpy.data.objects = [_d60_cage()]
        mats = extract_cabinets_from_scene()[0]["part_materials"]
        assert mats["Back"] is None
        assert mats["Drawer Box.001"] is None


class TestKitchenLevel:

    def _kitchen(self, fake_bpy):
        fake_bpy.data.objects = [_d60_cage()]
        return cabinets_to_kitchen(extract_cabinets_from_scene())

    def test_drawer_entries_bottom_up_s1_is_bottom(self, fake_bpy):
        cab = self._kitchen(fake_bpy).rows[0].cabinets[0]
        assert cab.type == "dolna_legrabox"
        assert [d["wysokosc"] for d in cab.drawers] == [254, 254, 140]
        assert cab.drawers[0]["id"] == "S1"  # S1 = bottom drawer

    def test_kitchen_survives_hub_round_trip_and_decompose(self, fake_bpy):
        """The ADR-004 contract now exercised through the LEGRABOX path:
        JSON round-trip, then decompose emits drawer-box panels."""
        kitchen = self._kitchen(fake_bpy)
        kitchen2 = kitchen_from_json_str(kitchen_to_json_str(kitchen))
        cab = kitchen2.rows[0].cabinets[0]
        result = decompose(cab)
        assert result.panels
        drawer_panels = [p for p in result.panels if "drawer" in
                         (p.role.value if p.role else "")]
        assert drawer_panels, "LEGRABOX decompose emitted no drawer panels"
