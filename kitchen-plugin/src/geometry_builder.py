"""Kitchen geometry builder — uses Blender bpy API.

Creates cabinet meshes from parsed config. External shell only.
"""

import bpy
from math import pi

from .config_parser import mm_to_m, CABINET_LEVELS

# Direction vectors: which way cabinets are placed along the wall
DIRECTIONS = {
    "east":  (1, 0),   # +X
    "north": (0, 1),   # +Y
    "west":  (-1, 0),  # -X
    "south": (0, -1),  # -Y
}

# Turn mapping: current direction + turn → new direction
# Based on ROOM perspective:
# - "left" = wall to the LEFT when facing the back wall
# - "right" = wall to the RIGHT when facing the back wall
#
# When standing in room facing the back wall (facing -Y):
# - Left is +X direction
# - Right is -X direction
# - Both side walls go TOWARD the viewer (-Y direction)
#
# The turn determines which CORNER to turn at:
# - "left" = turn at the LEFT end of current wall
# - "right" = turn at the RIGHT end of current wall
TURNS = {
    ("east", "left"):   "south",   # back wall → left wall (toward viewer)
    ("east", "right"):  "south",   # back wall → right wall (toward viewer)
    ("north", "left"):  "west",    # left wall → back wall
    ("north", "right"): "west",    # right wall → back wall
    ("west", "left"):   "north",   # back wall → right wall (toward viewer)
    ("west", "right"):  "north",   # back wall → left wall (toward viewer)
    ("south", "left"):  "east",    # left wall → back wall
    ("south", "right"): "east",    # right wall → back wall
}

# Wall location and depth direction for each travel direction
# WALL_SIDE: which side the wall is on
# DEPTH_DIR: which direction cabinet depth extends (INTO the room)
WALL_INFO = {
    "east":  {"wall": "south", "depth": (0, 1)},    # wall at -Y, depth goes +Y
    "south": {"wall": "east",  "depth": (-1, 0)},    # wall at +X, depth goes -X
    "west":  {"wall": "north", "depth": (0, -1)},    # wall at +Y, depth goes -Y
    "north": {"wall": "west",  "depth": (1, 0)},     # wall at -X, depth goes +X
}


def clear_scene() -> None:
    """Remove all objects from the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)

    for mesh in bpy.data.meshes:
        if mesh.users == 0:
            bpy.data.meshes.remove(mesh)
    for mat in bpy.data.materials:
        if mat.users == 0:
            bpy.data.materials.remove(mat)


def build_kitchen(config: dict) -> list[bpy.types.Object]:
    """Build all kitchen geometry from config.

    Returns list of created top-level objects.

    Turn logic:
    - "left" = turn at the LEFT end of current wall (when facing the wall)
    - "right" = turn at the RIGHT end of current wall (when facing the wall)
    - Both turns go TOWARD the viewer (into the room)
    """
    settings = config["settings"]
    all_objects = []

    # Track position and direction across runs
    pos_x = 0.0  # mm
    pos_y = 0.0  # mm
    direction = "east"

    print("\n" + "=" * 60)
    print("KITCHEN LAYOUT BUILDER")
    print("=" * 60)

    for run_idx, run in enumerate(config["runs"]):
        turn = run.get("turn")
        info = WALL_INFO[direction]

        print(f"\n--- Run {run_idx}: {run.get('label', 'unnamed')} ---")

        # Apply turn BEFORE building this run (not after previous)
        if turn and run_idx > 0:
            old_dir = direction
            new_dir = TURNS.get((direction, turn))
            if new_dir:
                direction = new_dir
                info = WALL_INFO[direction]
                print(f"  Turn: {old_dir} → {direction} ({turn})")
            else:
                print(f"  WARNING: invalid turn '{turn}' from direction '{direction}'")

        print(f"  Direction: {direction}")
        print(f"  Wall side: {info['wall']}")
        print(f"  Depth dir: {info['depth']}")
        print(f"  Start pos: ({pos_x:.0f}, {pos_y:.0f})")

        run_objects, end_x, end_y = _build_run(
            run, settings, run_idx, pos_x, pos_y, direction
        )
        all_objects.extend(run_objects)

        print(f"  End pos:   ({end_x:.0f}, {end_y:.0f})")

        # Update position for next run
        # The next run starts at the end of the current run
        pos_x = end_x
        pos_y = end_y

    print("\n" + "=" * 60)
    print(f"Total objects: {len(all_objects)}")
    print("=" * 60)

    return all_objects


def _build_run(run: dict, settings: dict, run_idx: int,
               start_x: float, start_y: float, direction: str
               ) -> tuple[list[bpy.types.Object], float, float]:
    """Build a single run (wall segment).

    Returns (objects, end_x, end_y) where end position is in mm.

    Uses cabinetGap for carcass positioning (not frontGap).
    frontGap is used in _add_front for door/drawer spacing.
    """
    objects = []
    # Use cabinetGap for carcass positioning
    cabinet_gap = settings.get("cabinetGap", 0)
    dx, dy = DIRECTIONS[direction]
    info = WALL_INFO[direction]
    ddx, ddy = info["depth"]

    print(f"  Along wall: dx={dx}, dy={dy}")
    print(f"  Into room:  ddx={ddx}, ddy={ddy}")

    # Base cabinets
    x, y = start_x, start_y
    for cab_idx, cab in enumerate(run.get("base", [])):
        obj = _build_cabinet(cab, settings, "base", run_idx, cab_idx)
        if obj:
            obj.location = (
                mm_to_m(x),
                mm_to_m(y),
                mm_to_m(settings["plinthHeight"]),
            )
            _rotate_for_direction(obj, direction)
            objects.append(obj)
            print(f"    base[{cab_idx}] {cab['type']}: "
                  f"pos=({x:.0f}, {y:.0f}) w={cab['width']}")
        x += (cab["width"] + cabinet_gap) * dx
        y += (cab["width"] + cabinet_gap) * dy

    # Upper cabinets
    ux, uy = start_x, start_y
    for cab_idx, cab in enumerate(run.get("upper", [])):
        obj = _build_cabinet(cab, settings, "upper", run_idx, cab_idx)
        if obj:
            obj.location = (
                mm_to_m(ux),
                mm_to_m(uy),
                mm_to_m(settings["wallMountHeight"]),
            )
            _rotate_for_direction(obj, direction)
            objects.append(obj)
        ux += (cab["width"] + cabinet_gap) * dx
        uy += (cab["width"] + cabinet_gap) * dy

    # Tall cabinets
    tx, ty = start_x, start_y
    for cab_idx, cab in enumerate(run.get("tall", [])):
        obj = _build_cabinet(cab, settings, "tall", run_idx, cab_idx)
        if obj:
            obj.location = (
                mm_to_m(tx),
                mm_to_m(ty),
                0.0,
            )
            _rotate_for_direction(obj, direction)
            objects.append(obj)
        tx += (cab["width"] + cabinet_gap) * dx
        ty += (cab["width"] + cabinet_gap) * dy

    # Countertop for base section
    if run.get("base"):
        total_width = sum(c["width"] for c in run["base"]) + cabinet_gap * (len(run["base"]) - 1)
        ct = _build_countertop(total_width, settings, run.get("countertop"))
        if ct:
            ct.location = (
                mm_to_m(start_x - settings.get("counterOverhangEnd", 30) * dx),
                mm_to_m(start_y - settings.get("counterOverhangEnd", 30) * dy),
                mm_to_m(settings["baseBodyHeight"] + settings["plinthHeight"]),
            )
            _rotate_for_direction(ct, direction)
            objects.append(ct)

    # Calculate end position
    base_cabs = run.get("base", [])
    if base_cabs:
        total = sum(c["width"] for c in base_cabs) + cabinet_gap * (len(base_cabs) - 1)
        end_x = start_x + total * dx
        end_y = start_y + total * dy
    else:
        end_x, end_y = start_x, start_y

    return objects, end_x, end_y


def _rotate_for_direction(obj: bpy.types.Object, direction: str) -> None:
    """Rotate object so front faces INTO the room (away from wall).

    Box geometry: front at Y=0 faces +Y (north).
    Rotation makes front face the depth direction for each wall.

    east  (wall south): front → +Y (north) → 0°
    south (wall east):  front → -X (west)  → +90° CCW
    west  (wall north): front → -Y (south) → 180°
    north (wall west):  front → +X (east)  → -90° CW
    """
    if direction == "east":
        obj.rotation_euler = (0, 0, 0)
    elif direction == "south":
        obj.rotation_euler = (0, 0, -pi / 2)   # 90° CW: front → -X (west)
    elif direction == "west":
        obj.rotation_euler = (0, 0, pi)         # 180°: front → -Y (south)
    elif direction == "north":
        obj.rotation_euler = (0, 0, pi / 2)    # 90° CCW: front → +X (east)


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

    d += mm_to_m(cab.get("depthOffset", 0))
    h += mm_to_m(cab.get("heightOffset", 0))

    name = f"run{run_idx}_{level}_{cab_idx}_{cab_type}"
    obj = _create_box(name, w, d, h)
    _add_front(obj, cab, settings, level, w, d, h)

    return obj


def _create_box(name: str, w: float, d: float, h: float) -> bpy.types.Object:
    """Create a box mesh (external shell only).

    Geometry: origin at front-left-bottom corner.
    - Width:  along +X (0 to w)
    - Depth:  along +Y (0 to d) — extends INTO room from wall
    - Height: along +Z (0 to h)

    Front face at Y=0 faces +Y (into room).
    Back face at Y=d faces -Y (toward wall).
    """
    verts = [
        (0, 0, 0),    (w, 0, 0),    (w, d, 0),    (0, d, 0),
        (0, 0, h),    (w, 0, h),    (w, d, h),    (0, d, h),
    ]
    faces = [
        (0, 1, 2, 3),  # bottom
        (4, 5, 6, 7),  # top
        (0, 1, 5, 4),  # front (Y=0)
        (1, 2, 6, 5),  # right
        (2, 3, 7, 6),  # back (Y=d)
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
    """Add door/drawer front(s) to a cabinet.

    Uses frontGap for door/drawer spacing (not cabinetGap).
    Uses frontOffset for how far fronts protrude from cabinet face.
    Uses clearanceOffset for geometric clearance (blind corners, etc.).
    """
    cab_type = cab["type"]
    # Use frontGap for door/drawer visual spacing
    front_gap = mm_to_m(settings.get("frontGap", 2))
    # Tolerance offsets from settings
    front_offset = settings.get("frontOffset", 0.001)  # meters
    clearance_offset = settings.get("clearanceOffset", 0.001)  # meters
    front_thickness = 0.018

    single_door_types = {
        "base-door", "wall-door", "tall-oven", "tall-fridge", "tall-pantry",
    }
    double_door_types = {"base-door-double", "wall-door-double", "base-sink"}
    drawer_types = {"base-drawers", "wall-drawers"}
    drawer_door_types = {"base-drawer-door"}

    if cab_type in single_door_types:
        _add_door_front(obj, w, h, front_thickness, cab, level,
                        front_offset=front_offset)

    elif cab_type in double_door_types:
        door_w = (w - front_gap) / 2
        _add_door_front(obj, door_w, h, front_thickness, cab, level,
                        x_offset=0, front_offset=front_offset)
        _add_door_front(obj, door_w, h, front_thickness, cab, level,
                        x_offset=door_w + front_gap, name_suffix="_R",
                        front_offset=front_offset)

    elif cab_type in drawer_types:
        drawer_count = cab.get("drawers", 3)
        if isinstance(drawer_count, int):
            drawer_h = (h - front_gap * (drawer_count - 1)) / drawer_count
            heights = [drawer_h] * drawer_count
        else:
            heights = [mm_to_m(hh) for hh in drawer_count]

        z = 0
        for i, dh in enumerate(heights):
            _add_drawer_front(obj, w, dh, front_thickness, z, i,
                              front_offset=front_offset)
            z += dh + front_gap

    elif cab_type in drawer_door_types:
        drawer_h = mm_to_m(cab.get("drawerHeight", 150))
        _add_drawer_front(obj, w, drawer_h, front_thickness, 0, 0,
                          front_offset=front_offset)
        door_h = h - drawer_h - front_gap
        _add_door_front(obj, w, door_h, front_thickness,
                        cab, level, z_offset=drawer_h + front_gap,
                        front_offset=front_offset)

    elif cab_type == "corner-blind":
        blind_depth = mm_to_m(cab.get("blindDepth", 300))
        door_w = w - blind_depth - clearance_offset
        _add_door_front(obj, door_w, h, front_thickness, cab, level,
                        x_offset=blind_depth + clearance_offset,
                        front_offset=front_offset)

    elif cab_type == "corner-diagonal":
        _add_door_front(obj, w, h, front_thickness, cab, level,
                        front_offset=front_offset)


def _add_door_front(parent: bpy.types.Object, w: float, h: float,
                    thickness: float, cab: dict, level: str,
                    x_offset: float = 0.0, z_offset: float = 0.0,
                    name_suffix: str = "", front_offset: float = 0.001) -> None:
    """Add a door front to a cabinet.

    Args:
        front_offset: how far front protrudes from cabinet face (meters)
    """
    name = parent.name + "_door" + name_suffix

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
    obj.location = (0, -front_offset, 0)  # slightly in front of cabinet face
    bpy.context.collection.objects.link(obj)
    obj.parent = parent


def _add_drawer_front(parent: bpy.types.Object, w: float, h: float,
                      thickness: float, z: float, index: int,
                      front_offset: float = 0.001) -> None:
    """Add a drawer front to a cabinet.

    Args:
        front_offset: how far front protrudes from cabinet face (meters)
    """
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
    obj.location = (0, -front_offset, 0)  # slightly in front of cabinet face
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

    # Countertop: width along X, depth along +Y (into room)
    return _create_box("countertop", w, d, h)


def apply_materials(objects: list[bpy.types.Object], config: dict) -> None:
    """Apply Cycles materials to objects."""
    from .material_manager import create_materials
    create_materials(objects, config)
