"""YAML loader — reads a cabinet definition file into a CabinetInstance.

The loader is an ADAPTER between the YAML format (Polish keys, user-facing)
and the domain model (English fields, engine-facing).  It has no business logic.
"""

from pathlib import Path

import yaml

from .model import CabinetInstance


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
