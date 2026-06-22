"""Kitchen geometry builder — uses Blender bpy API.

Creates cabinet meshes from parsed config.
Uses CabinetGeometry for accurate European construction:
- 18mm corpus board (carcass walls)
- 19mm front panels (doors/drawers)
- 3mm HDF back panel in grooves
"""

import bpy
from math import pi

from .config_parser import mm_to_m, CABINET_LEVELS
from .kitchen.cabinet_geometry import CabinetGeometry

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
        obj, cab_objs = _build_cabinet(cab, settings, "base", run_idx, cab_idx)
        if obj:
            obj.location = (
                mm_to_m(x),
                mm_to_m(y),
                mm_to_m(settings["plinthHeight"]),
            )
            _rotate_for_direction(obj, direction)
            objects.extend(cab_objs)
            print(f"    base[{cab_idx}] {cab['type']}: "
                  f"pos=({x:.0f}, {y:.0f}) w={cab['width']} "
                  f"({len(cab_objs)} objects)")
        x += (cab["width"] + cabinet_gap) * dx
        y += (cab["width"] + cabinet_gap) * dy

    # Upper cabinets
    ux, uy = start_x, start_y
    for cab_idx, cab in enumerate(run.get("upper", [])):
        obj, cab_objs = _build_cabinet(cab, settings, "upper", run_idx, cab_idx)
        if obj:
            obj.location = (
                mm_to_m(ux),
                mm_to_m(uy),
                mm_to_m(settings["wallMountHeight"]),
            )
            _rotate_for_direction(obj, direction)
            objects.extend(cab_objs)
        ux += (cab["width"] + cabinet_gap) * dx
        uy += (cab["width"] + cabinet_gap) * dy

    # Tall cabinets
    tx, ty = start_x, start_y
    for cab_idx, cab in enumerate(run.get("tall", [])):
        obj, cab_objs = _build_cabinet(cab, settings, "tall", run_idx, cab_idx)
        if obj:
            obj.location = (
                mm_to_m(tx),
                mm_to_m(ty),
                0.0,
            )
            _rotate_for_direction(obj, direction)
            objects.extend(cab_objs)
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
                   run_idx: int, cab_idx: int) -> tuple[bpy.types.Object | None, list]:
    """Build a single cabinet with proper European construction.

    Uses CabinetGeometry for accurate dimensions:
    - corpusThickness (default 18mm) corpus board (carcass walls)
    - frontThickness (default 19mm) front panels (doors/drawers)
    - backThickness (default 3mm) HDF back panel in grooves

    Construction parameters are read from settings.

    Returns:
        Tuple of (main_object, all_objects_list)
    """
    cab_type = cab["type"]

    if cab_type == "filler":
        obj = _build_filler(cab, settings, level)
        return obj, [obj] if obj else []

    # Get external dimensions in mm
    width_mm = cab["width"]

    if level == "base":
        depth_mm = settings["baseDepth"]
        height_mm = settings["baseBodyHeight"]
    elif level == "upper":
        depth_mm = settings["wallDepth"]
        height_mm = settings["wallHeight"]
    else:  # tall
        depth_mm = settings["tallDepth"]
        height_mm = settings["tallHeight"]

    depth_mm += cab.get("depthOffset", 0)
    height_mm += cab.get("heightOffset", 0)

    # Create geometry calculator with construction params from settings
    geom = CabinetGeometry(
        external_width=width_mm,
        external_depth=depth_mm,
        external_height=height_mm,
        corpus_thickness=settings.get("corpusThickness", 18),
        back_thickness=settings.get("backThickness", 3),
        front_thickness=settings.get("frontThickness", 19),
        groove_offset=settings.get("grooveOffset", 10),
    )

    name = f"run{run_idx}_{level}_{cab_idx}_{cab_type}"

    # Track all objects created for this cabinet
    all_objs = []

    # Create carcass (hollow box with walls, open front)
    obj = _create_carcass(name, geom)
    all_objs.append(obj)

    # Add back panel (HDF in groove)
    back_obj = _add_back_panel(obj, geom)
    if back_obj:
        all_objs.append(back_obj)

    # Add front panels (doors/drawers with overlay)
    front_objs = _add_front(obj, cab, settings, level, geom)
    all_objs.extend(front_objs)

    return obj, all_objs


def _create_box(name: str, w: float, d: float, h: float) -> bpy.types.Object:
    """Create a solid box mesh.

    Geometry: origin at front-left-bottom corner.
    - Width:  along +X (0 to w)
    - Depth:  along +Y (0 to d) — extends INTO room from wall
    - Height: along +Z (0 to h)

    Used for fillers, countertops, and other solid elements.
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


def _create_carcass(name: str, geom: CabinetGeometry) -> bpy.types.Object:
    """Create a hollow carcass mesh with 18mm walls.

    Creates a box with proper wall thickness for European frameless construction.
    Front face is open (will be covered by door/drawer fronts).

    Args:
        name: Object name
        geom: CabinetGeometry with calculated dimensions
    """
    # External dimensions in meters
    w = geom.external_width / 1000
    d = geom.external_depth / 1000
    h = geom.external_height / 1000

    # Wall thickness in meters
    t = geom.corpus_thickness / 1000

    # Create vertices for hollow box (24 vertices for 6 faces with thickness)
    # Outer shell
    verts = [
        # Outer bottom (z=0)
        (0, 0, 0),       # 0
        (w, 0, 0),       # 1
        (w, d, 0),       # 2
        (0, d, 0),       # 3
        # Outer top (z=h)
        (0, 0, h),       # 4
        (w, 0, h),       # 5
        (w, d, h),       # 6
        (0, d, h),       # 7
        # Inner bottom (z=t)
        (t, t, t),       # 8
        (w-t, t, t),     # 9
        (w-t, d-t, t),   # 10
        (t, d-t, t),     # 11
        # Inner top (z=h-t)
        (t, t, h-t),     # 12
        (w-t, t, h-t),   # 13
        (w-t, d-t, h-t), # 14
        (t, d-t, h-t),   # 15
    ]

    # Faces for hollow box (12 faces, open front)
    # Bottom rim: connects outer bottom (z=0) to inner bottom (z=t)
    # Top rim: connects outer top (z=h) to inner top (z=h-t)
    # Sides: left and right walls
    # Back: outer back face and inner back face
    faces = [
        # Bottom rim (4 faces around the bottom edge)
        (0, 1, 9, 8),    # front-bottom rim
        (1, 2, 10, 9),   # right-bottom rim
        (2, 3, 11, 10),  # back-bottom rim
        (3, 0, 8, 11),   # left-bottom rim
        # Top rim (4 faces around the top edge)
        (4, 5, 13, 12),  # front-top rim
        (5, 6, 14, 13),  # right-top rim
        (6, 7, 15, 14),  # back-top rim
        (7, 4, 12, 15),  # left-top rim
        # Left wall (1 face)
        (0, 4, 7, 3),    # left side outer
        # Right wall (1 face)
        (1, 2, 6, 5),    # right side outer
        # Back wall (2 faces)
        (2, 3, 7, 6),    # back outer
        (10, 11, 15, 14), # back inner
    ]

    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()

    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj


def _add_back_panel(parent: bpy.types.Object, geom: CabinetGeometry) -> bpy.types.Object:
    """Add 3mm HDF back panel to cabinet.

    Back panel sits in grooves offset from rear edge.

    Returns:
        The created back panel object.
    """
    name = parent.name + "_back"

    # Back panel dimensions in meters
    w = geom.back_panel_width / 1000
    h = geom.back_panel_height / 1000
    thickness = geom.back_thickness / 1000

    # Position: in groove at rear of cabinet
    # Y position = external depth - groove offset
    y_pos = (geom.external_depth - geom.groove_offset) / 1000

    # Create back panel as thin box
    verts = [
        (0, y_pos, 0),
        (w, y_pos, 0),
        (w, y_pos, h),
        (0, y_pos, h),
        (0, y_pos + thickness, 0),
        (w, y_pos + thickness, 0),
        (w, y_pos + thickness, h),
        (0, y_pos + thickness, h),
    ]

    faces = [
        (0, 1, 2, 3),  # front
        (4, 5, 6, 7),  # back
        (0, 1, 5, 4),  # bottom
        (1, 2, 6, 5),  # right
        (2, 3, 7, 6),  # top
        (3, 0, 4, 7),  # left
    ]

    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()

    obj = bpy.data.objects.new(name, mesh)
    # Offset to center horizontally (corpus thickness from left)
    obj.location = (geom.corpus_thickness / 1000, 0, 0)
    bpy.context.collection.objects.link(obj)
    obj.parent = parent

    return obj


def _add_front(obj: bpy.types.Object, cab: dict, settings: dict,
               level: str, geom: CabinetGeometry) -> list:
    """Add door/drawer front(s) to a cabinet.

    Uses CabinetGeometry for proper dimensions and overlay.
    Fronts are thick boxes (not flat quads).

    Uses frontGap for door/drawer spacing (not cabinetGap).
    Uses frontOffset for how far fronts protrude from cabinet face.
    Uses clearanceOffset for geometric clearance (blind corners, etc.).
    Uses frontOverlay from settings for overlay amount.

    Returns:
        List of created front panel objects.
    """
    cab_type = cab["type"]
    front_objs = []

    # Get overlay from settings (default 2mm)
    overlay = settings.get("frontOverlay", 2)

    # Get front dimensions with overlay
    front_w_mm, front_h_mm = geom.front_dimensions(
        overlay_side=overlay,
        overlay_top=overlay,
        overlay_bottom=overlay,
    )
    front_w = front_w_mm / 1000
    front_h = front_h_mm / 1000

    # Use frontGap for door/drawer visual spacing
    front_gap = mm_to_m(settings.get("frontGap", 2))
    # Tolerance offsets from settings
    front_offset = settings.get("frontOffset", 0.001)  # meters
    clearance_offset = settings.get("clearanceOffset", 0.001)  # meters

    single_door_types = {
        "base-door", "wall-door", "tall-oven", "tall-fridge", "tall-pantry",
    }
    double_door_types = {"base-door-double", "wall-door-double", "base-sink"}
    drawer_types = {"base-drawers", "wall-drawers"}
    drawer_door_types = {"base-drawer-door"}

    if cab_type in single_door_types:
        door_obj = _add_door_front(obj, front_w, front_h, geom, overlay, cab, level,
                        front_offset=front_offset)
        front_objs.append(door_obj)

    elif cab_type in double_door_types:
        door_w = (front_w - front_gap) / 2
        door_obj_l = _add_door_front(obj, door_w, front_h, geom, overlay, cab, level,
                        x_offset=0, front_offset=front_offset)
        door_obj_r = _add_door_front(obj, door_w, front_h, geom, overlay, cab, level,
                        x_offset=door_w + front_gap, name_suffix="_R",
                        front_offset=front_offset)
        front_objs.extend([door_obj_l, door_obj_r])

    elif cab_type in drawer_types:
        drawer_count = cab.get("drawers", 3)
        if isinstance(drawer_count, int):
            drawer_h = (front_h - front_gap * (drawer_count - 1)) / drawer_count
            heights = [drawer_h] * drawer_count
        else:
            heights = [hh / 1000 for hh in drawer_count]

        z = 0
        for i, dh in enumerate(heights):
            drawer_obj = _add_drawer_front(obj, front_w, dh, geom, overlay, z, i,
                              front_offset=front_offset)
            front_objs.append(drawer_obj)
            z += dh + front_gap

    elif cab_type in drawer_door_types:
        drawer_h = mm_to_m(cab.get("drawerHeight", 150))
        drawer_obj = _add_drawer_front(obj, front_w, drawer_h, geom, overlay, 0, 0,
                          front_offset=front_offset)
        front_objs.append(drawer_obj)
        door_h = front_h - drawer_h - front_gap
        door_obj = _add_door_front(obj, front_w, door_h, geom, overlay,
                        cab, level, z_offset=drawer_h + front_gap,
                        front_offset=front_offset)
        front_objs.append(door_obj)

    elif cab_type == "corner-blind":
        blind_depth = mm_to_m(cab.get("blindDepth", 300))
        door_w = front_w - blind_depth - clearance_offset
        door_obj = _add_door_front(obj, door_w, front_h, geom, overlay, cab, level,
                        x_offset=blind_depth + clearance_offset,
                        front_offset=front_offset)
        front_objs.append(door_obj)

    elif cab_type == "corner-diagonal":
        door_obj = _add_door_front(obj, front_w, front_h, geom, overlay, cab, level,
                        front_offset=front_offset)
        front_objs.append(door_obj)

    return front_objs


def _add_door_front(parent: bpy.types.Object, w: float, h: float,
                    geom: CabinetGeometry, overlay: float,
                    cab: dict, level: str,
                    x_offset: float = 0.0, z_offset: float = 0.0,
                    name_suffix: str = "", front_offset: float = 0.001) -> bpy.types.Object:
    """Add a door front to a cabinet.

    Creates a thick box instead of a flat quad.

    Args:
        w: Front width (meters, with overlay)
        h: Front height (meters, with overlay)
        geom: CabinetGeometry for thickness calculation
        overlay: overlay amount in mm (from settings)
        front_offset: how far front protrudes from cabinet face (meters)

    Returns:
        The created door front object.
    """
    name = parent.name + "_door" + name_suffix
    thickness = geom.front_thickness / 1000  # Convert mm to meters

    # Get overlay offsets from geometry
    overlay_x, overlay_y, overlay_z = geom.front_position(
        overlay_side=overlay,
        overlay_top=overlay,
        overlay_bottom=overlay,
    )
    overlay_x_m = overlay_x / 1000
    overlay_z_m = overlay_z / 1000

    # Create front as a thick box (8 vertices)
    verts = [
        # Front face (facing into room)
        (x_offset + overlay_x_m, 0, z_offset + overlay_z_m),
        (x_offset + overlay_x_m + w, 0, z_offset + overlay_z_m),
        (x_offset + overlay_x_m + w, 0, z_offset + overlay_z_m + h),
        (x_offset + overlay_x_m, 0, z_offset + overlay_z_m + h),
        # Back face (facing towards cabinet)
        (x_offset + overlay_x_m, -thickness, z_offset + overlay_z_m),
        (x_offset + overlay_x_m + w, -thickness, z_offset + overlay_z_m),
        (x_offset + overlay_x_m + w, -thickness, z_offset + overlay_z_m + h),
        (x_offset + overlay_x_m, -thickness, z_offset + overlay_z_m + h),
    ]

    # 6 faces for closed box
    faces = [
        (0, 1, 2, 3),  # front
        (4, 5, 6, 7),  # back
        (0, 1, 5, 4),  # bottom
        (1, 2, 6, 5),  # right
        (2, 3, 7, 6),  # top
        (3, 0, 4, 7),  # left
    ]

    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()

    obj = bpy.data.objects.new(name, mesh)
    # Door local Y goes from -thickness to 0
    # We want back face (local Y=-thickness) to be at carcass front (Y=depth) + front_offset
    # So position Y = depth + front_offset + thickness
    obj.location = (0, geom.external_depth / 1000 + front_offset + thickness, 0)
    bpy.context.collection.objects.link(obj)
    obj.parent = parent

    return obj


def _add_drawer_front(parent: bpy.types.Object, w: float, h: float,
                      geom: CabinetGeometry, overlay: float,
                      z: float, index: int,
                      front_offset: float = 0.001) -> bpy.types.Object:
    """Add a drawer front to a cabinet.

    Creates a thick box instead of a flat quad.

    Args:
        w: Front width (meters, with overlay)
        h: Front height (meters, with overlay)
        geom: CabinetGeometry for thickness calculation
        overlay: overlay amount in mm (from settings)
        z: Vertical position offset (meters)
        front_offset: how far front protrudes from cabinet face (meters)

    Returns:
        The created drawer front object.
    """
    name = f"{parent.name}_drawer{index}"
    thickness = geom.front_thickness / 1000  # Convert mm to meters

    # Get overlay offsets from geometry
    overlay_x, overlay_y, overlay_z = geom.front_position(
        overlay_side=overlay,
        overlay_top=overlay,
        overlay_bottom=overlay,
    )
    overlay_x_m = overlay_x / 1000
    overlay_z_m = overlay_z / 1000

    # Create drawer front as a thick box (8 vertices)
    verts = [
        # Front face (facing into room)
        (overlay_x_m, 0, z + overlay_z_m),
        (overlay_x_m + w, 0, z + overlay_z_m),
        (overlay_x_m + w, 0, z + overlay_z_m + h),
        (overlay_x_m, 0, z + overlay_z_m + h),
        # Back face (facing towards cabinet)
        (overlay_x_m, -thickness, z + overlay_z_m),
        (overlay_x_m + w, -thickness, z + overlay_z_m),
        (overlay_x_m + w, -thickness, z + overlay_z_m + h),
        (overlay_x_m, -thickness, z + overlay_z_m + h),
    ]

    # 6 faces for closed box
    faces = [
        (0, 1, 2, 3),  # front
        (4, 5, 6, 7),  # back
        (0, 1, 5, 4),  # bottom
        (1, 2, 6, 5),  # right
        (2, 3, 7, 6),  # top
        (3, 0, 4, 7),  # left
    ]

    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()

    obj = bpy.data.objects.new(name, mesh)
    # Drawer local Y goes from -thickness to 0
    # We want back face (local Y=-thickness) to be at carcass front (Y=depth) + front_offset
    # So position Y = depth + front_offset + thickness
    obj.location = (0, geom.external_depth / 1000 + front_offset + thickness, 0)
    bpy.context.collection.objects.link(obj)
    obj.parent = parent

    return obj


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
