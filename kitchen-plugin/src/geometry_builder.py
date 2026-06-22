"""Kitchen geometry builder — uses Blender bpy API.

Creates cabinet meshes from parsed config. External shell only.
"""

import bpy
from math import pi

from .config_parser import mm_to_m, CABINET_LEVELS


def clear_scene() -> None:
    """Remove all objects from the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)

    # Clean orphan data
    for mesh in bpy.data.meshes:
        if mesh.users == 0:
            bpy.data.meshes.remove(mesh)
    for mat in bpy.data.materials:
        if mat.users == 0:
            bpy.data.materials.remove(mat)


def build_kitchen(config: dict) -> list[bpy.types.Object]:
    """Build all kitchen geometry from config.

    Returns list of created top-level objects.
    """
    settings = config["settings"]
    all_objects = []

    for run_idx, run in enumerate(config["runs"]):
        run_objects = _build_run(run, settings, run_idx)
        all_objects.extend(run_objects)

    return all_objects


def _build_run(run: dict, settings: dict, run_idx: int) -> list[bpy.types.Object]:
    """Build a single run (wall segment)."""
    objects = []
    gap = settings["gap"]

    # Base cabinets
    x = 0.0
    for cab_idx, cab in enumerate(run.get("base", [])):
        obj = _build_cabinet(cab, settings, "base", run_idx, cab_idx)
        if obj:
            obj.location = (
                mm_to_m(x),
                0.0,
                mm_to_m(settings["plinthHeight"]),
            )
            objects.append(obj)
        x += cab["width"] + gap

    # Upper cabinets
    x = 0.0
    for cab_idx, cab in enumerate(run.get("upper", [])):
        obj = _build_cabinet(cab, settings, "upper", run_idx, cab_idx)
        if obj:
            obj.location = (
                mm_to_m(x),
                0.0,
                mm_to_m(settings["wallMountHeight"]),
            )
            objects.append(obj)
        x += cab["width"] + gap

    # Tall cabinets
    x = 0.0
    for cab_idx, cab in enumerate(run.get("tall", [])):
        obj = _build_cabinet(cab, settings, "tall", run_idx, cab_idx)
        if obj:
            obj.location = (mm_to_m(x), 0.0, 0.0)
            objects.append(obj)
        x += cab["width"] + gap

    # Countertop for base section
    if run.get("base"):
        total_width = sum(c["width"] for c in run["base"]) + gap * (len(run["base"]) - 1)
        ct = _build_countertop(total_width, settings, run.get("countertop"))
        if ct:
            ct.location = (
                -mm_to_m(settings.get("counterOverhangEnd", 30)),
                mm_to_m(settings["counterOverhangFront"]),
                mm_to_m(settings["baseBodyHeight"] + settings["plinthHeight"]),
            )
            objects.append(ct)

    return objects


def _build_cabinet(cab: dict, settings: dict, level: str,
                   run_idx: int, cab_idx: int) -> bpy.types.Object | None:
    """Build a single cabinet."""
    cab_type = cab["type"]

    if cab_type == "filler":
        return _build_filler(cab, settings, level)

    w = mm_to_m(cab["width"])

    if level == "base":
        d = mm_to_m(settings["baseDepth"])
        h = mm_to_m(settings["baseBodyHeight"])
    elif level == "upper":
        d = mm_to_m(settings["wallDepth"])
        h = mm_to_m(settings["wallHeight"])
    else:  # tall
        d = mm_to_m(settings["tallDepth"])
        h = mm_to_m(settings["tallHeight"])

    # Adjust depth/height with offsets
    d += mm_to_m(cab.get("depthOffset", 0))
    h += mm_to_m(cab.get("heightOffset", 0))

    name = f"run{run_idx}_{level}_{cab_idx}_{cab_type}"
    obj = _create_box(name, w, d, h)
    _add_front(obj, cab, settings, level, w, d, h)

    return obj


def _create_box(name: str, w: float, d: float, h: float) -> bpy.types.Object:
    """Create a box mesh (external shell only)."""
    verts = [
        (0, 0, 0),    (w, 0, 0),    (w, -d, 0),    (0, -d, 0),
        (0, 0, h),    (w, 0, h),    (w, -d, h),    (0, -d, h),
    ]
    faces = [
        (0, 1, 2, 3),  # bottom
        (4, 5, 6, 7),  # top
        (0, 1, 5, 4),  # front
        (1, 2, 6, 5),  # right
        (2, 3, 7, 6),  # back
        (3, 0, 4, 7),  # left
    ]

    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()

    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj


def _add_front(obj: bpy.types.Object, cab: dict, settings: dict,
               level: str, w: float, d: float, h: float) -> None:
    """Add door/drawer front(s) to a cabinet."""
    cab_type = cab["type"]
    gap = mm_to_m(settings.get("gap", 2))
    front_thickness = 0.018  # 18mm standard

    # Door front types
    single_door_types = {
        "base-door", "wall-door", "tall-oven", "tall-fridge", "tall-pantry",
    }
    double_door_types = {"base-door-double", "wall-door-double", "base-sink"}
    drawer_types = {"base-drawers", "wall-drawers"}
    drawer_door_types = {"base-drawer-door"}

    if cab_type in single_door_types:
        _add_door_front(obj, w, h, front_thickness, cab, level)

    elif cab_type in double_door_types:
        door_w = (w - gap) / 2
        _add_door_front(obj, door_w, h, front_thickness, cab, level,
                        x_offset=0)
        _add_door_front(obj, door_w, h, front_thickness, cab, level,
                        x_offset=door_w + gap, name_suffix="_R")

    elif cab_type in drawer_types:
        drawer_count = cab.get("drawers", 3)
        if isinstance(drawer_count, int):
            drawer_h = (h - gap * (drawer_count - 1)) / drawer_count
            heights = [drawer_h] * drawer_count
        else:
            heights = [mm_to_m(hh) for hh in drawer_count]

        z = 0
        for i, dh in enumerate(heights):
            _add_drawer_front(obj, w, dh, front_thickness, z, i)
            z += dh + gap

    elif cab_type in drawer_door_types:
        drawer_h = mm_to_m(cab.get("drawerHeight", 150))
        _add_drawer_front(obj, w, drawer_h, front_thickness, 0, 0)
        door_h = h - drawer_h - gap
        _add_door_front(obj, w, door_h, front_thickness,
                        cab, level, z_offset=drawer_h + gap)

    elif cab_type == "corner-blind":
        blind_depth = mm_to_m(cab.get("blindDepth", 300))
        door_w = w - blind_depth - 0.001
        _add_door_front(obj, door_w, h, front_thickness, cab, level,
                        x_offset=blind_depth + 0.001)

    elif cab_type == "corner-diagonal":
        # Diagonal door — simplified as angled front
        _add_door_front(obj, w, h, front_thickness, cab, level)


def _add_door_front(parent: bpy.types.Object, w: float, h: float,
                    thickness: float, cab: dict, level: str,
                    x_offset: float = 0.0, z_offset: float = 0.0,
                    name_suffix: str = "") -> None:
    """Add a door front to a cabinet."""
    name = parent.name + "_door" + name_suffix
    d = parent.dimensions.y  # same depth as cabinet

    verts = [
        (x_offset, 0, z_offset),
        (x_offset + w, 0, z_offset),
        (x_offset + w, 0, z_offset + h),
        (x_offset, 0, z_offset + h),
    ]
    faces = [(0, 1, 2, 3)]

    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()

    obj = bpy.data.objects.new(name, mesh)
    obj.location = (0, -parent.dimensions.y - 0.001, 0)
    bpy.context.collection.objects.link(obj)
    obj.parent = parent


def _add_drawer_front(parent: bpy.types.Object, w: float, h: float,
                      thickness: float, z: float, index: int) -> None:
    """Add a drawer front to a cabinet."""
    name = f"{parent.name}_drawer{index}"

    verts = [
        (0, 0, z),
        (w, 0, z),
        (w, 0, z + h),
        (0, 0, z + h),
    ]
    faces = [(0, 1, 2, 3)]

    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()

    obj = bpy.data.objects.new(name, mesh)
    obj.location = (0, -parent.dimensions.y - 0.001, 0)
    bpy.context.collection.objects.link(obj)
    obj.parent = parent


def _build_filler(cab: dict, settings: dict, level: str) -> bpy.types.Object:
    """Build a filler strip."""
    w = mm_to_m(cab["width"])
    if level == "base":
        d = mm_to_m(settings["baseDepth"])
        h = mm_to_m(settings["baseBodyHeight"])
    elif level == "upper":
        d = mm_to_m(settings["wallDepth"])
        h = mm_to_m(settings["wallHeight"])
    else:
        d = mm_to_m(settings["tallDepth"])
        h = mm_to_m(settings["tallHeight"])

    return _create_box("filler", w, d, h)


def _build_countertop(total_width: int, settings: dict,
                      override: dict | None) -> bpy.types.Object | None:
    """Build a countertop spanning the run."""
    ct = settings.copy()
    if override:
        ct.update(override)

    w = mm_to_m(total_width + 2 * ct.get("counterOverhangEnd", 30))
    d = mm_to_m(settings["baseDepth"] + ct.get("counterOverhangFront", 20))
    h = mm_to_m(ct.get("counterThickness", 30))

    return _create_box("countertop", w, d, h)


def apply_materials(objects: list[bpy.types.Object], config: dict) -> None:
    """Apply Cycles materials to objects."""
    from .material_manager import create_materials
    create_materials(objects, config)
