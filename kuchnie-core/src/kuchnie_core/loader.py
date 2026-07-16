"""YAML loader — reads cabinet and kitchen definition files.

The loader is an ADAPTER between the YAML format (Polish keys, user-facing)
and the domain model (English fields, engine-facing).  It has no business logic.

Supports two formats:
  1. Legacy format (Polish keys, cabinet_files references)
  2. New schema format (English keys, inline cabinets)
"""

from pathlib import Path

import yaml

from .model import (
    BaseDoorConfig,
    BaseDrawerConfig,
    CabinetConfig,
    CabinetInstance,
    CargoConfig,
    CornerBlindConfig,
    CornerInternalConfig,
    DrawerSlot,
    HandleSpec,
    Kitchen,
    OvenConfig,
    Row,
    ShelfPinSpec,
    SinkConfig,
    WorktopSegment,
)


# ── Handle translation tables (ADR-012 §4) ────────────────────

_HANDLE_TYPE_PL_TO_EN = {
    "relingowy": "bar",
    "reling":    "bar",
    "kulisty":   "knob",
    "kula":      "knob",
    "profilowy": "profile",
    "profil":    "profile",
    "wpuszczany": "recessed",
    "krawedziowy": "edge_pull",
    "krawędziowy": "edge_pull",
    "frezowany":  "recessed",
}

_HANDLE_POSITION_PL_TO_EN = {
    "srodek_frontu": "center",
    "srodek":        "center",
    "centrum":       "center",
    "gora":          "top",
    "góra":          "top",
    "dol":           "bottom",
    "dól":           "bottom",
}


def _handle_spec_from_polish(d: dict | None) -> HandleSpec | None:
    """Polish YAML ``uchwyty`` block → ``HandleSpec``.

    Returns ``None`` for an empty/missing dict so ``if cab.handles is not None``
    still short-circuits when the fixture has no handles.
    """
    if not d:
        return None
    return HandleSpec(
        type=_HANDLE_TYPE_PL_TO_EN.get(d.get("typ", "bar"), d.get("typ", "bar")),
        spacing_mm=float(d.get("rozstaw", 128.0)),
        hole_diameter_mm=float(d.get("srednica_otworu", 5.0)),
        position=_HANDLE_POSITION_PL_TO_EN.get(
            d.get("pozycja", "center"), d.get("pozycja", "center")
        ),
    )


def _shelf_pins_from_polish(d: dict | None) -> ShelfPinSpec:
    """Polish YAML ``kolki_polkowe`` block → ``ShelfPinSpec``.

    Missing block yields the ADR-012 default spec (5mm × 8mm, standard
    50/80 offsets). Recognised Polish keys:

      * ``srednica``   → ``diameter_mm``
      * ``glebokosc``  → ``depth_mm``
      * ``odsuniecie_przod``  → ``front_offset_mm``
      * ``odsuniecie_tyl``    → ``back_offset_mm``
      * ``maks_na_rzad`` → ``max_per_row``
    """
    if not d:
        return ShelfPinSpec()
    return ShelfPinSpec(
        diameter_mm=float(d.get("srednica", 5.0)),
        depth_mm=float(d.get("glebokosc", 8.0)),
        front_offset_mm=float(d.get("odsuniecie_przod", 50.0)),
        back_offset_mm=float(d.get("odsuniecie_tyl", 80.0)),
        max_per_row=int(d.get("maks_na_rzad", 3)),
    )


def _shelf_pins_from_schema(d: dict | None) -> ShelfPinSpec:
    """Schema-format (English keys) shelf-pin dict → ``ShelfPinSpec``."""
    if not d:
        return ShelfPinSpec()
    return ShelfPinSpec(
        diameter_mm=float(d.get("diameter_mm", 5.0)),
        depth_mm=float(d.get("depth_mm", 8.0)),
        front_offset_mm=float(d.get("front_offset_mm", 50.0)),
        back_offset_mm=float(d.get("back_offset_mm", 80.0)),
        max_per_row=int(d.get("max_per_row", 3)),
    )


def _handle_spec_from_schema(d: dict | None) -> HandleSpec | None:
    """Schema-format (English keys) handles dict → ``HandleSpec``.

    Values are already English; this is a straight field lift with type
    coercion and safe defaults.
    """
    if not d:
        return None
    return HandleSpec(
        type=d.get("type", "bar"),
        spacing_mm=float(d.get("spacing_mm", 128.0)),
        hole_diameter_mm=float(d.get("hole_diameter_mm", 5.0)),
        position=d.get("position", "center"),
    )


# ── ADR-012 §6: legacy loose fields → typed ``CabinetConfig`` ──
#
# Mirrors ``kitchen_cam.models.CorpusSpec._sync_config_from_legacy``.
# Called from every ``load_cabinet`` path (Polish YAML + schema YAML).
# The loose ``drawers`` / ``shelves`` / ``fronts`` fields stay on the
# instance until every caller migrates — the synthesised ``config`` is
# purely additive information.

# Polish ``CabinetInstance.type`` values grouped by variant.
_DOOR_TYPES = {
    "dolna_drzwiowa",
    "gorna_drzwiowa",
    "wysoka_drzwiowa",
    "slupek_drzwiowy",
}
_DRAWER_TYPES = {
    "dolna_szufladowa",
    "dolna_legrabox",
    "dolna_tandembox",
    "dolna_merivobox",
}
_CORNER_BLIND_TYPES = {"dolna_narozna_slepa", "gorna_narozna_slepa"}
_CORNER_INTERNAL_TYPES = {"dolna_narozna_karuzela", "dolna_narozna_wewnetrzna"}
_SINK_TYPES = {"dolna_zlewozmywakowa", "dolna_zlew"}
_CARGO_TYPES = {"dolna_cargo"}
_OVEN_TYPES = {"slupek_piekarnikowy", "slupek_agd"}


def _shelf_positions(cab: CabinetInstance) -> list[float]:
    """Extract shelf Y-positions from the loose ``shelves`` list of dicts.

    Recognised keys (either allowed): ``pozycja_od_dolu`` (Polish YAML),
    ``position_mm`` (English schema). Shelves without a position contribute
    nothing — downstream code either ignores or spaces them evenly.
    """
    out: list[float] = []
    for s in cab.shelves:
        if not isinstance(s, dict):
            continue
        if "pozycja_od_dolu" in s:
            out.append(float(s["pozycja_od_dolu"]))
        elif "position_mm" in s:
            out.append(float(s["position_mm"]))
    return out


def _door_hinge_counts(cab: CabinetInstance) -> list[int]:
    """Collect ``ilosc_zawiasow`` per door-type front, in declaration order."""
    counts: list[int] = []
    for f in cab.fronts:
        if not isinstance(f, dict):
            continue
        typ = f.get("typ", "")
        if typ.startswith("drzwiowy") or typ == "drzwi":
            counts.append(int(f.get("ilosc_zawiasow", 2)))
    return counts


def _drawer_slot_from_dict(d: dict) -> DrawerSlot:
    """Legacy drawer dict → ``DrawerSlot``.

    Accepts both Polish (``typ`` / ``wysokosc`` / ``nl``) and English
    (``system`` / ``height_mm`` / ``nl_mm``) key names — the schema loader
    already normalises to Polish, but be forgiving.
    """
    return DrawerSlot(
        id=str(d.get("id", "")),
        system=str(d.get("typ") or d.get("system") or "tandembox_antaro"),
        height_mm=float(d.get("wysokosc") or d.get("height_mm") or 0),
        height_code=str(d.get("height_code", "M")),
        nl_mm=float(d.get("nl") or d.get("nl_mm") or 500),
        capacity_kg=float(d.get("capacity_kg", 40)),
    )


def _synthesise_config(cab: CabinetInstance) -> CabinetConfig | None:
    """Build the ADR-012 §6 discriminated ``config`` from legacy loose fields.

    Returns ``None`` for cabinet types not recognised as any variant, so
    hand-built ``CabinetInstance`` objects with unusual types keep
    ``config = None`` (opt-in explicit assignment still works).
    """
    t = cab.type
    if t in _DOOR_TYPES:
        return BaseDoorConfig(
            shelves=_shelf_positions(cab),
            doors=_door_hinge_counts(cab),
        )
    if t in _DRAWER_TYPES:
        return BaseDrawerConfig(
            drawers=[_drawer_slot_from_dict(d) for d in cab.drawers if isinstance(d, dict)],
        )
    if t in _CORNER_BLIND_TYPES:
        return CornerBlindConfig(
            corner_side="left",
            second_width_mm=float(cab.depth_mm),
            shelves=_shelf_positions(cab),
            doors=_door_hinge_counts(cab),
        )
    if t in _CORNER_INTERNAL_TYPES:
        return CornerInternalConfig(
            shelves=_shelf_positions(cab),
            doors=_door_hinge_counts(cab),
        )
    if t in _SINK_TYPES:
        return SinkConfig(
            doors=_door_hinge_counts(cab),
        )
    if t in _CARGO_TYPES:
        return CargoConfig(
            doors=_door_hinge_counts(cab),
        )
    if t in _OVEN_TYPES:
        return OvenConfig(
            cavity_height_mm=float(cab.height_mm) * 0.6,
        )
    return None


def apply_synthesised_config(cab: CabinetInstance) -> CabinetInstance:
    """Populate ``cab.config`` from legacy loose fields when caller left it ``None``.

    Kept as a tiny helper so both load paths share the same guard.
    """
    if cab.config is None:
        cab.config = _synthesise_config(cab)
    return cab


def _normalize_drawer_order(drawers: list, order: str | None,
                            cabinet_id: str) -> list:
    """Enforce the model contract: CabinetInstance.drawers is BOTTOM-UP.

    G8 (UC-2 extension 3a): a multi-drawer stack with unequal heights and
    no explicit order declaration is AMBIGUOUS — entering fronts top-down
    puts the top drawer's runner drillings at the floor (demonstrated
    scrap-risk, tr-0958807f). Ambiguity is rejected at load; declared
    top-down input is normalized by reversal.

    order: 'od_dolu'/'bottom_up' | 'od_gory'/'top_down' | None
    """
    if not drawers or len(drawers) < 2:
        return drawers
    if order in ("od_gory", "top_down"):
        return list(reversed(drawers))
    if order in ("od_dolu", "bottom_up"):
        return drawers
    if order is not None:
        raise ValueError(
            f"{cabinet_id}: unknown drawer order '{order}' "
            f"(use od_dolu/od_gory or bottom_up/top_down)")
    heights = {d.get("wysokosc") for d in drawers if isinstance(d, dict)}
    if len(heights) > 1:
        raise ValueError(
            f"{cabinet_id}: drawer stack order is ambiguous — {len(drawers)} "
            f"drawers with unequal heights and no order declaration. Add "
            f"'kolejnosc_szuflad: od_dolu|od_gory' (Polish YAML) or "
            f"'drawer_order: bottom_up|top_down' (schema YAML). The model "
            f"consumes drawers BOTTOM-UP.")
    return drawers


def load_cabinet(yaml_path: str | Path) -> CabinetInstance:
    """Load a single cabinet definition from a YAML file."""
    data = yaml.safe_load(Path(yaml_path).read_text())
    k = data["korpus"]

    cab = CabinetInstance(
        id=k["id"],
        type=k["typ"],
        description=k.get("opis", ""),
        width_mm=k["wymiary"]["szerokosc"],
        height_mm=k["wymiary"]["wysokosc"],
        depth_mm=k["wymiary"]["glebokosc"],
        # Materials
        body_material=k["material"]["korpus"],
        back_material=k["material"]["plecy"],
        front_material=k["material"]["fronty"],
        # Thicknesses
        thickness_side_mm=k["grubosci"].get("boki", 18),
        thickness_shelf_mm=k["grubosci"].get("polki", 18),
        thickness_bottom_mm=k["grubosci"].get("dna", 18),
        thickness_back_mm=k["grubosci"].get("plecy", 3),
        thickness_front_mm=k["grubosci"].get("fronty", 18),
        # Back panel
        back_type=k["plecy"]["typ"],
        groove_depth_mm=k["plecy"]["nut"],
        # Edge banding
        edge_banding_type=k["oklejanie"]["typ"],
        edge_banding_thickness_mm=k["oklejanie"]["grubosc"],
        # Interior (drawer list normalized to the bottom-up model contract)
        drawers=_normalize_drawer_order(
            k["wnetrze"].get("szuflady", []),
            k["wnetrze"].get("kolejnosc_szuflad"),
            k["id"]),
        shelves=k["wnetrze"].get("polki", []),
        fronts=k.get("fronty", []),
        handles=_handle_spec_from_polish(k.get("uchwyty")),
        shelf_pins=_shelf_pins_from_polish(k.get("kolki_polkowe")),
        # Plinth (0 for wall cabinets)
        plinth_height_mm=k.get("nozki", {}).get("wysokosc", 0),
    )
    return apply_synthesised_config(cab)


def _cabinet_from_schema(cab_data: dict) -> CabinetInstance:
    """Convert schema format cabinet to CabinetInstance."""
    cab = CabinetInstance(
        id=cab_data["id"],
        type=cab_data["type"],
        description=cab_data.get("description", ""),
        width_mm=cab_data["width_mm"],
        height_mm=cab_data["height_mm"],
        depth_mm=cab_data["depth_mm"],
        body_material=cab_data["body_material"],
        back_material=cab_data["back_material"],
        front_material=cab_data["front_material"],
        thickness_side_mm=cab_data.get("thickness_side_mm", 18),
        thickness_shelf_mm=cab_data.get("thickness_shelf_mm", 18),
        thickness_bottom_mm=cab_data.get("thickness_bottom_mm", 18),
        thickness_back_mm=cab_data.get("thickness_back_mm", 3),
        thickness_front_mm=cab_data.get("thickness_front_mm", 18),
        groove_depth_mm=cab_data.get("groove_depth_mm", 8),
        plinth_height_mm=cab_data.get("plinth_height_mm", 100),
        drawers=_normalize_drawer_order([
            {
                "id": d["id"],
                "typ": d.get("system", "tandembox_antaro"),
                "wysokosc": d["height_mm"],
                "height_code": d.get("height_code", "M"),
                "nl": d.get("nl", 500),
                "capacity_kg": d.get("capacity_kg", 40),
            }
            for d in cab_data.get("drawers", [])
        ], cab_data.get("drawer_order"), cab_data["id"]),
        shelves=[{"id": s["id"]} for s in cab_data.get("shelves", [])],
        fronts=[
            {
                "id": f["id"],
                "typ": "szufladowy" if f["type"] == "drawer" else "drzwiowy",
                "powiazany": f.get("linked_to"),
                "strona": f.get("side"),
                "ilosc_zawiasow": f.get("hinge_count", 2),
                "margines_lewo": f.get("margins", {}).get("left", 3),
                "margines_prawo": f.get("margins", {}).get("right", 3),
            }
            for f in cab_data.get("fronts", [])
        ],
        handles=_handle_spec_from_schema(cab_data.get("handles")),
        shelf_pins=_shelf_pins_from_schema(cab_data.get("shelf_pins")),
    )
    return apply_synthesised_config(cab)


def load_kitchen(yaml_path: str | Path) -> Kitchen:
    """Load a kitchen definition from YAML.

    Cabinet definitions are loaded from separate YAML files referenced
    by ``cabinet_files`` (paths relative to the kitchen YAML).
    """
    path = Path(yaml_path).resolve()
    data = yaml.safe_load(path.read_text())
    k = data["kitchen"]

    rows: list[Row] = []
    for rd in k.get("rows", []):
        cabinets = [
            load_cabinet(path.parent / cf)
            for cf in rd.get("cabinet_files", [])
        ]
        rows.append(Row(
            id=rd["id"],
            label=rd.get("label", ""),
            wall_width_mm=rd["wall_width_mm"],
            wall_height_mm=rd["wall_height_mm"],
            cabinets=cabinets,
        ))

    worktops: list[WorktopSegment] = []
    for wt in k.get("worktops", []):
        worktops.append(WorktopSegment(
            row_id=wt["row_id"],
            length_mm=wt["length_mm"],
            depth_mm=wt.get("depth_mm", 600),
            thickness_mm=wt.get("thickness_mm", 40),
            material=wt.get("material", ""),
        ))

    return Kitchen(
        version=k.get("version", "1.0"),
        project_name=k.get("project", {}).get("name", ""),
        created=k.get("project", {}).get("created", ""),
        rows=rows,
        worktops=worktops,
    )


def load_kitchen_from_schema(yaml_path: str | Path) -> Kitchen:
    """Load kitchen from new schema format (English keys, inline cabinets).

    This is the format produced by the Blender export operator.
    """
    path = Path(yaml_path).resolve()
    data = yaml.safe_load(path.read_text())

    # Detect format: new schema has 'version' at top level
    if "version" in data and "rows" in data:
        return _load_schema_format(data, path)
    else:
        # Legacy format
        return load_kitchen(yaml_path)


def _load_schema_format(data: dict, path: Path) -> Kitchen:
    """Load from new schema format."""
    rows: list[Row] = []
    for rd in data.get("rows", []):
        cabinets = [_cabinet_from_schema(c) for c in rd.get("cabinets", [])]
        rows.append(Row(
            id=rd["label"].replace(" ", "_").lower(),
            label=rd["label"],
            wall_width_mm=rd["wall_width_mm"],
            wall_height_mm=rd.get("wall_height_mm", 2800),
            cabinets=cabinets,
        ))

    worktops: list[WorktopSegment] = []
    for wt in data.get("worktops", []):
        worktops.append(WorktopSegment(
            row_id=wt["row_label"].replace(" ", "_").lower(),
            length_mm=0,  # Will be calculated from cabinets
            depth_mm=wt.get("depth_mm", 600),
            thickness_mm=wt.get("thickness_mm", 40),
            material=wt.get("material", ""),
        ))

    return Kitchen(
        version=data.get("version", "2.0"),
        project_name=data.get("project_name", ""),
        rows=rows,
        worktops=worktops,
    )
