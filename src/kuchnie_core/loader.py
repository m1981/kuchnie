"""YAML loader — reads cabinet and kitchen definition files.

The loader is an ADAPTER between the YAML format (Polish keys, user-facing)
and the domain model (English fields, engine-facing).  It has no business logic.
"""

from pathlib import Path

import yaml

from .model import CabinetInstance, Kitchen, Row, WorktopSegment


def load_cabinet(yaml_path: str | Path) -> CabinetInstance:
    """Load a single cabinet definition from a YAML file."""
    data = yaml.safe_load(Path(yaml_path).read_text())
    k = data["korpus"]

    return CabinetInstance(
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
        # Interior
        drawers=k["wnetrze"].get("szuflady", []),
        shelves=k["wnetrze"].get("polki", []),
        fronts=k.get("fronty", []),
        handles=k.get("uchwyty", {}),
        # Plinth (0 for wall cabinets)
        plinth_height_mm=k.get("nozki", {}).get("wysokosc", 0),
    )


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
