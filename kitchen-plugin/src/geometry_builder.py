"""Kitchen geometry builder — uses Blender bpy API.

Creates cabinet meshes from parsed config.
Uses CabinetGeometry for accurate European construction:
- 18mm corpus board (carcass walls)
- 19mm front panels (doors/drawers)
- 3mm HDF back panel in grooves
"""

import bpy

from .core.geometry import mm_to_m
from .kitchen.cabinet_geometry import CabinetGeometry


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


def build_kitchen_from_layout(layout, settings: dict) -> list[bpy.types.Object]:
    """Build kitchen geometry from a domain Layout object.

    Uses pre-computed world positions and rotations from LayoutEngine
    instead of recomputing them from raw config.

    Args:
        layout: kitchen.layout.Layout with placed_cabinets
        settings: construction settings dict (corpusThickness, etc.)

    Returns:
        List of created top-level bpy objects.
    """
    from .kitchen.layout import Layout
    from .kitchen.cabinet import CabinetPlacement

    all_objects = []

    print("\n" + "=" * 60)
    print("KITCHEN LAYOUT BUILDER (domain model)")
    print("=" * 60)
    print(f"  Walls: {len(layout.room.walls)}")
    print(f"  Runs: {len(layout.runs)}")
    print(f"  Placements: {len(layout.placed_cabinets)}")

    for run_idx, run in enumerate(layout.runs):
        run_label = run.label
        print(f"\n--- Run {run_idx}: {run_label} ({run.direction.value}) ---")

        # Get placements for this run's cabinets
        run_cab_ids = {c.id for c in run.cabinets}
        run_placements = [
            p for p in layout.placed_cabinets
            if p.cabinet.id in run_cab_ids
        ]

        for cab_idx, placement in enumerate(run_placements):
            cab = placement.cabinet
            level = cab.level.value

            # Build mesh using domain Cabinet directly
            obj, cab_objs = _build_cabinet(
                cab, settings, level, run_idx, cab_idx
            )
            if obj:
                # Position from domain Layout (pre-computed)
                obj.location = (
                    mm_to_m(placement.world_position.x),
                    mm_to_m(placement.world_position.y),
                    mm_to_m(placement.world_position.z),
                )
                obj.rotation_euler = (0, 0, placement.rotation_rad)
                all_objects.extend(cab_objs)
                print(f"    {level}[{cab_idx}] {cab.cabinet_type.value}: "
                      f"pos=({placement.world_position.x:.0f}, "
                      f"{placement.world_position.y:.0f}, "
                      f"{placement.world_position.z:.0f})"
                      f" ({len(cab_objs)} objects)")

        # Countertop
        if run.countertop:
            ct = run.countertop
            ct_dict = {
                "counterOverhangFront": ct.overhang_front,
                "counterOverhangEnd": ct.overhang_end,
                "counterThickness": ct.thickness,
            }
            total_width = ct.length
            ct_obj = _build_countertop(total_width, settings, ct_dict)
            if ct_obj:
                # Position at wall start, accounting for end overhang
                wall = layout.room.get_wall(run_label)
                if wall:
                    dx, dy = wall.direction.x, wall.direction.y
                    base_height = settings.get("baseBodyHeight", 720)
                    plinth_height = settings.get("plinthHeight", 120)
                    ct_obj.location = (
                        mm_to_m(wall.start.x - ct.overhang_end * dx),
                        mm_to_m(wall.start.y - ct.overhang_end * dy),
                        mm_to_m(base_height + plinth_height),
                    )
                    ct_obj.rotation_euler = (0, 0, wall.angle_rad)
                    all_objects.append(ct_obj)

    print("\n" + "=" * 60)
    print(f"Total objects: {len(all_objects)}")
    print("=" * 60)

    return all_objects



def _build_cabinet(cab, settings: dict, level: str,
                   run_idx: int, cab_idx: int,
                   ) -> tuple[bpy.types.Object | None, list]:
    """Build a single cabinet with proper European construction.

    Accepts a domain Cabinet object. Uses CabinetGeometry for accurate
    dimensions and construction params from settings.

    Returns:
        Tuple of (main_object, all_objects_list)
    """
    cab_type = cab.cabinet_type.value

    if cab_type == "filler":
        obj = _build_filler(cab, settings, level)
        return obj, [obj] if obj else []

    # Dimensions from domain Cabinet (offsets already baked in)
    width_mm = cab.width
    depth_mm = cab.depth
    height_mm = cab.height

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

    # Create carcass as 4 separate boards with technical gaps
    parent, boards = _create_carcass(name, geom)
    all_objs.append(parent)
    all_objs.extend(boards)

    # Add back panel (HDF in groove) — parented to the carcass parent
    back_obj = _add_back_panel(parent, geom)
    if back_obj:
        all_objs.append(back_obj)

    # Add front panels (doors/drawers with gap) — parented to carcass parent
    front_objs = _add_front(parent, cab, settings, level, geom)
    all_objs.extend(front_objs)

    return parent, all_objs


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


def _create_carcass(name: str, geom: CabinetGeometry) -> tuple:
    """Create carcass as 4 separate solid boards with technical gaps.

    European frameless construction:
    - Left side panel:   full height × full depth × T
    - Right side panel:  full height × full depth × T
    - Top panel:         between sides × between front/back × T
    - Bottom panel:      between sides × between front/back × T

    Each board is a separate solid box (8 vertices, 6 faces).
    Technical gaps between all boards — no shared surfaces.

    Returns:
        (parent_empty, [left, right, top, bottom])
    """
    # External dimensions in meters
    w = geom.external_width / 1000
    d = geom.external_depth / 1000
    h = geom.external_height / 1000
    t = geom.corpus_thickness / 1000
    gap = 0.001  # 1mm technical gap

    # Board dimensions
    # Side panels: full height × full depth × thickness
    side_w = t
    side_d = d
    side_h = h

    # Top/bottom: fit BETWEEN sides, full depth minus back panel offset
    tb_w = w - 2 * t
    tb_d = d - t
    tb_h = t

    # Create parent empty to group boards
    parent = bpy.data.objects.new(name, None)
    parent.empty_display_type = 'PLAIN_AXES'
    parent.empty_display_size = 0.05
    bpy.context.collection.objects.link(parent)

    boards = []

    # Left side panel: at X=0
    left = _make_solid_box(
        f"{name}_left", 0, 0, 0, side_w, side_d, side_h
    )
    left.parent = parent
    boards.append(left)

    # Right side panel: at X = width - thickness
    right = _make_solid_box(
        f"{name}_right", w - t, 0, 0, side_w, side_d, side_h
    )
    right.parent = parent
    boards.append(right)

    # Bottom panel: between sides, at Z=0
    bottom = _make_solid_box(
        f"{name}_bottom",
        t + gap, 0, 0,
        tb_w - 2 * gap, tb_d, tb_h
    )
    bottom.parent = parent
    boards.append(bottom)

    # Top panel: between sides, at Z = height - thickness
    top = _make_solid_box(
        f"{name}_top",
        t + gap, 0, h - t,
        tb_w - 2 * gap, tb_d, tb_h
    )
    top.parent = parent
    boards.append(top)

    return parent, boards


def _make_solid_box(name: str, x: float, y: float, z: float,
                    w: float, d: float, h: float) -> bpy.types.Object:
    """Create a solid box mesh at position (x,y,z) with size (w,d,h).

    8 vertices, 6 faces. Simple closed box.
    """
    verts = [
        (x,     y,     z),     (x+w, y,   z),
        (x+w,   y+d,   z),     (x,   y+d, z),
        (x,     y,     z+h),   (x+w, y,   z+h),
        (x+w,   y+d,   z+h),   (x,   y+d, z+h),
    ]
    faces = [
        [0, 1, 2, 3],  # bottom
        [4, 5, 6, 7],  # top
        [0, 1, 5, 4],  # front (Y=min)
        [1, 2, 6, 5],  # right (X=max)
        [2, 3, 7, 6],  # back (Y=max)
        [3, 0, 4, 7],  # left (X=min)
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


def _add_front(obj: bpy.types.Object, cab, settings: dict,
               level: str, geom: CabinetGeometry) -> list:
    """Add door/drawer front(s) to a cabinet.

    European frameless construction (32mm system):
    - Front is SMALLER than carcass opening
    - Gap between front edge and carcass sides (typically 2-3mm per side)
    - Front width = carcass_width - 2 × frontGap
    - Front height = carcass_height - 2 × frontGap
    - Drawer fronts: additional vertical gap between each drawer
    - Pull handles: extra 4mm clearance on top (layout concern, not front sizing)

    Returns:
        List of created front panel objects.
    """
    cab_type = cab.cabinet_type.value
    front_objs = []

    # Gap between front edge and carcass side (mm)
    front_gap = settings.get("frontGap", 2)  # 2-3mm per side

    # Handle clearance: extra space above cabinet for pull handles
    # This is a layout concern, not a front sizing concern
    handle_clearance = 0
    if cab.handle_type.value in ("rail", "knob"):
        handle_clearance = settings.get("handleClearance", 4)  # mm

    # European frameless: front is SMALLER than carcass
    # Front width = carcass_width - 2 × frontGap (gap on each side)
    # Front height = carcass_height - 2 × frontGap (gap top + bottom)
    front_w_mm = geom.external_width - 2 * front_gap
    front_h_mm = geom.external_height - 2 * front_gap

    front_w = mm_to_m(front_w_mm)
    front_h = mm_to_m(front_h_mm)

    # Front is centered on carcass: offset by front_gap from each edge
    front_offset_x = mm_to_m(front_gap)  # offset from left edge
    front_offset_z = mm_to_m(front_gap)  # offset from bottom edge

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
        door_obj = _add_door_front(obj, front_w, front_h, geom, front_gap, cab, level,
                        x_offset=front_offset_x, z_offset=front_offset_z,
                        front_offset=front_offset)
        front_objs.append(door_obj)

    elif cab_type in double_door_types:
        # Double doors: split width, gap between them
        door_gap = mm_to_m(front_gap)
        door_w = (front_w - door_gap) / 2
        door_obj_l = _add_door_front(obj, door_w, front_h, geom, front_gap, cab, level,
                        x_offset=front_offset_x, z_offset=front_offset_z,
                        front_offset=front_offset)
        door_obj_r = _add_door_front(obj, door_w, front_h, geom, front_gap, cab, level,
                        x_offset=front_offset_x + door_w + door_gap,
                        z_offset=front_offset_z,
                        name_suffix="_R", front_offset=front_offset)
        front_objs.extend([door_obj_l, door_obj_r])

    elif cab_type in drawer_types:
        drawer_count = cab.drawer_count or 3
        drawer_gap = mm_to_m(front_gap)
        if isinstance(drawer_count, int):
            drawer_h = (front_h - drawer_gap * (drawer_count - 1)) / drawer_count
            heights = [drawer_h] * drawer_count
        else:
            heights = [mm_to_m(hh) for hh in drawer_count]

        z = front_offset_z
        for i, dh in enumerate(heights):
            drawer_obj = _add_drawer_front(obj, front_w, dh, geom, front_gap, z, i,
                              front_offset=front_offset)
            front_objs.append(drawer_obj)
            z += dh + drawer_gap

    elif cab_type in drawer_door_types:
        drawer_gap = mm_to_m(front_gap)
        drawer_h = mm_to_m(cab.drawer_heights[0] if cab.drawer_heights else 150)
        drawer_obj = _add_drawer_front(obj, front_w, drawer_h, geom, front_gap,
                          front_offset_z, 0, front_offset=front_offset)
        front_objs.append(drawer_obj)
        door_h = front_h - drawer_h - drawer_gap
        door_obj = _add_door_front(obj, front_w, door_h, geom, front_gap,
                        cab, level,
                        x_offset=front_offset_x,
                        z_offset=front_offset_z + drawer_h + drawer_gap,
                        front_offset=front_offset)
        front_objs.append(door_obj)

    elif cab_type == "corner-blind":
        blind_depth = mm_to_m(cab.blind_depth or 300)
        door_w = front_w - blind_depth - clearance_offset
        door_obj = _add_door_front(obj, door_w, front_h, geom, front_gap, cab, level,
                        x_offset=front_offset_x + blind_depth + clearance_offset,
                        z_offset=front_offset_z,
                        front_offset=front_offset)
        front_objs.append(door_obj)

    elif cab_type == "corner-diagonal":
        door_obj = _add_door_front(obj, front_w, front_h, geom, front_gap, cab, level,
                        x_offset=front_offset_x, z_offset=front_offset_z,
                        front_offset=front_offset)
        front_objs.append(door_obj)

    return front_objs


def _add_door_front(parent: bpy.types.Object, w: float, h: float,
                    geom: CabinetGeometry, front_gap: float,
                    cab, level: str,
                    x_offset: float = 0.0, z_offset: float = 0.0,
                    name_suffix: str = "", front_offset: float = 0.001) -> bpy.types.Object:
    """Add a door front to a cabinet.

    Creates a thick box instead of a flat quad.
    Front is positioned with gap from carcass edges (European frameless).

    Args:
        w: Front width (meters, already reduced by gap)
        h: Front height (meters, already reduced by gap)
        geom: CabinetGeometry for thickness calculation
        front_gap: gap between front and carcass edge (mm)
        x_offset: X position offset (meters, includes gap offset)
        z_offset: Z position offset (meters, includes gap offset)
        front_offset: how far front protrudes from cabinet face (meters)

    Returns:
        The created door front object.
    """
    name = parent.name + "_door" + name_suffix
    thickness = geom.front_thickness / 1000  # Convert mm to meters

    # Create front as a thick box (8 vertices)
    # Position is already offset by front_gap from _add_front()
    verts = [
        # Front face (facing into room)
        (x_offset, 0, z_offset),
        (x_offset + w, 0, z_offset),
        (x_offset + w, 0, z_offset + h),
        (x_offset, 0, z_offset + h),
        # Back face (facing towards cabinet)
        (x_offset, -thickness, z_offset),
        (x_offset + w, -thickness, z_offset),
        (x_offset + w, -thickness, z_offset + h),
        (x_offset, -thickness, z_offset + h),
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
    # Front face (local Y=0) should be at carcass front (Y=0) - front_offset
    # So position Y = -front_offset
    # Back face (local Y=-thickness) will be at Y = -front_offset - thickness
    obj.location = (0, -front_offset, 0)
    bpy.context.collection.objects.link(obj)
    obj.parent = parent

    return obj


def _add_drawer_front(parent: bpy.types.Object, w: float, h: float,
                      geom: CabinetGeometry, front_gap: float,
                      z: float, index: int,
                      front_offset: float = 0.001) -> bpy.types.Object:
    """Add a drawer front to a cabinet.

    Creates a thick box instead of a flat quad.
    Front is positioned with gap from carcass edges (European frameless).

    Args:
        w: Front width (meters, already reduced by gap)
        h: Front height (meters, already reduced by gap)
        geom: CabinetGeometry for thickness calculation
        front_gap: gap between front and carcass edge (mm)
        z: Vertical position offset (meters, includes gap offset)
        front_offset: how far front protrudes from cabinet face (meters)

    Returns:
        The created drawer front object.
    """
    name = f"{parent.name}_drawer{index}"
    thickness = geom.front_thickness / 1000  # Convert mm to meters

    # X offset: gap from left edge of carcass
    x_offset = mm_to_m(front_gap)

    # Create drawer front as a thick box (8 vertices)
    # Position is already offset by front_gap from _add_front()
    verts = [
        # Front face (facing into room)
        (x_offset, 0, z),
        (x_offset + w, 0, z),
        (x_offset + w, 0, z + h),
        (x_offset, 0, z + h),
        # Back face (facing towards cabinet)
        (x_offset, -thickness, z),
        (x_offset + w, -thickness, z),
        (x_offset + w, -thickness, z + h),
        (x_offset, -thickness, z + h),
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
    # Front face (local Y=0) should be at carcass front (Y=0) - front_offset
    # So position Y = -front_offset
    # Back face (local Y=-thickness) will be at Y = -front_offset - thickness
    obj.location = (0, -front_offset, 0)
    bpy.context.collection.objects.link(obj)
    obj.parent = parent

    return obj


def _build_filler(cab, settings: dict, level: str) -> bpy.types.Object:
    """Build a filler strip."""
    w = mm_to_m(cab.width)
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
