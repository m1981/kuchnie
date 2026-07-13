"""hb5 headless helpers — importable ONLY inside Blender (needs bpy).

Encodes the bootstrap gotchas that cost real debugging time. Do not remove
a workaround without rerunning an exercise to prove it obsolete:

* run under `--background --enable-autoexec` — hb5 drivers call custom
  namespace functions (IF, ...) that Blender blocks by default;
* enable the addon BEFORE opening any saved scene — otherwise the driver
  namespace is missing at load and geometry collapses (tr-5e160a9a run);
* after building, `hb_utils.run_calc_fix` must run (Blender #133392);
* `ensure_main_scene()` + `ensure_default_style()` replicate load_post;
* finish_colors' custom-color store resolves an extension user-data path
  that does not exist for a legacy-module enable — patch it empty;
* scene `default_carcass_part_thickness` does NOT propagate on create —
  force `Material Thickness` on the built subtree, then calc-fix;
* the style's exterior finish paints carcass ends (US semantics); Polish
  decor-fronts-only needs per-part Finish-flag surgery.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

from .config import hb5_parent


def bootstrap(gaps=None):
    """Enable home_builder_5 and replicate its load_post handler.

    Returns (bpy, hb) where hb is a namespace of the hb5 modules used by
    exercises. Call once, at the top of a blender leg.
    """
    import addon_utils
    import bpy

    parent = str(hb5_parent())
    if parent not in sys.path:
        sys.path.append(parent)
    addon_utils.enable("home_builder_5", default_set=True, persistent=True)

    from home_builder_5 import hb_project, hb_types, hb_utils, units
    from home_builder_5.product_libraries.frameless import (
        finish_colors,
        types_frameless,
    )

    main = hb_project.ensure_main_scene()
    main.hb_frameless.ensure_default_style()
    scene = bpy.context.scene
    scene["IS_ROOM_SCENE"] = True
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.length_unit = "MILLIMETERS"

    try:
        finish_colors.get_all_stain_colors()
    except Exception as e:  # noqa: BLE001
        if gaps:
            gaps.gap(f"headless: finish_colors user-data path broken "
                     f"({type(e).__name__}) — custom colors patched to empty")
        finish_colors._load_custom_colors = lambda: {"stain": {}, "paint": {}}

    class HB:
        pass

    hb = HB()
    hb.project, hb.types, hb.utils, hb.units = hb_project, hb_types, hb_utils, units
    hb.frameless, hb.finish_colors = types_frameless, finish_colors
    hb.main_scene = main
    return bpy, hb


def metric_shop_profile(bpy, hb, gaps=None, toe_kick_mm=100,
                        top_front_mm=140, thickness_mm=18):
    """Polish shop defaults on the room scene (set BEFORE creating cabinets).

    NOTE: top_drawer_front_height is an OPENING size in hb5, not a front
    height (US overlay model) — fronts come out larger. thickness is set
    here for completeness but does not propagate reliably; call
    force_material_thickness() on each cabinet after create.
    """
    props = bpy.context.scene.hb_frameless
    mm = hb.units.millimeter
    for name, val in [("default_toe_kick_height", mm(toe_kick_mm)),
                      ("equal_drawer_stack_heights", False),
                      ("top_drawer_front_height", mm(top_front_mm)),
                      ("default_carcass_part_thickness", mm(thickness_mm))]:
        if hasattr(props, name):
            setattr(props, name, val)
        elif gaps:
            gaps.gap(f"hb_frameless.{name} missing")


def build_room(bpy, hb, length_mm=3000, width_mm=2400,
               height_mm=2400, wall_thickness_mm=100):
    """Four connected walls; returns the wall objects."""
    mm = hb.units.millimeter
    L, W = mm(length_mm), mm(width_mm)
    walls = []
    for loc, rot, length in [((0, 0, 0), 0.0, L),
                             ((L, 0, 0), math.radians(90), W),
                             ((L, W, 0), math.radians(180), L),
                             ((0, W, 0), math.radians(270), W)]:
        w = hb.types.GeoNodeWall()
        w.create("Wall")
        w.set_input("Thickness", mm(wall_thickness_mm))
        w.set_input("Height", mm(height_mm))
        w.set_input("Length", length)
        w.obj.location = loc
        w.obj.rotation_euler.z = rot
        walls.append(w)
    return walls


def force_material_thickness(bpy, hb, cab_obj, thickness_mm=18):
    """Metric board on a built cabinet (workaround, see module docstring)."""
    forced = 0
    for o in [cab_obj, *cab_obj.children_recursive]:
        if "Material Thickness" in o.keys():
            o["Material Thickness"] = hb.units.millimeter(thickness_mm)
            forced += 1
    hb.utils.run_calc_fix(bpy.context, cab_obj, passes=3)
    return forced


def apply_decor_split(bpy, hb, cab_obj, gaps=None, species="OAK",
                      stain_keywords=("espresso", "ebony", "dark", "walnut")):
    """Front decor != carcass, Polish semantics (decor restricted to fronts).

    Applies the active style (exterior finish -> fronts), then flips the
    Finish flags off on every non-front part and re-applies, because hb5's
    exterior finish otherwise paints the carcass ends too.
    """
    mprops = hb.main_scene.hb_frameless
    if not len(mprops.cabinet_styles):
        if gaps:
            gaps.gap("no cabinet style after ensure_default_style")
        return None
    style = mprops.cabinet_styles[mprops.active_cabinet_style_index]
    style.wood_species = species
    names = list(hb.finish_colors.get_all_stain_colors())
    dark = next((n for n in names if any(k in n.lower() for k in stain_keywords)),
                names[-1] if names else None)
    if dark:
        style.stain_color = dark
    style.assign_style_to_cabinet(cab_obj)
    surgically = 0
    for child in cab_obj.children_recursive:
        if "CABINET_PART" not in child or child.get("IS_CABINET_FRONT"):
            continue
        if child.get("Finish Top") or child.get("Finish Bottom", True):
            child["Finish Top"] = False
            child["Finish Bottom"] = False
            surgically += 1
    style.assign_style_to_cabinet(cab_obj)
    if gaps:
        gaps.gap(f"hb5 US finish semantics: Finish flags forced off on "
                 f"{surgically} carcass part(s) to keep decor on fronts")
    return style


def dump_cage_hierarchy(bpy, path: str | Path) -> int:
    """Full cage subtree with id props + geo-node inputs (extraction probe)."""
    def dump_obj(obj, depth=0):
        entry = {
            "name": obj.name,
            "depth": depth,
            "id_props": {k: str(obj.get(k)) for k in obj.keys()
                         if not k.startswith("_")},
            "children": [],
        }
        gn = {}
        for mod in getattr(obj, "modifiers", []):
            if mod.type == "NODES" and mod.node_group:
                for item in mod.node_group.interface.items_tree:
                    if item.item_type == "SOCKET" and item.in_out == "INPUT":
                        try:
                            gn[item.name] = str(mod[item.identifier])
                        except Exception:  # noqa: BLE001
                            pass
        if gn:
            entry["gn_inputs"] = gn
        for ch in obj.children:
            entry["children"].append(dump_obj(ch, depth + 1))
        return entry

    raw = {"cages": [dump_obj(o) for o in bpy.data.objects
                     if o.get("IS_FRAMELESS_CABINET_CAGE")]}
    Path(path).write_text(json.dumps(raw, indent=2))
    return len(raw["cages"])


def render_checks(bpy, out_dir: str | Path, iso=(2.4, -1.6, 1.3),
                  iso_rot=(72, 0, 38), front=(1.2, -2.2, 0.5)):
    """Own EEVEE shots — the inspection harness renders Workbench random
    colors, so decor is unobservable there; these are the decor eyes."""
    out = Path(out_dir)
    scene = bpy.context.scene
    cam = bpy.data.objects.new("e2e_cam", bpy.data.cameras.new("e2e_cam"))
    scene.collection.objects.link(cam)
    sun = bpy.data.objects.new("e2e_sun", bpy.data.lights.new("e2e_sun", "SUN"))
    scene.collection.objects.link(sun)
    sun.rotation_euler = (math.radians(45), math.radians(-20), 0)
    sun.data.energy = 3.0
    scene.camera = cam
    for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE", "BLENDER_WORKBENCH"):
        try:
            scene.render.engine = eng
            break
        except TypeError:
            continue
    scene.render.resolution_x, scene.render.resolution_y = 1280, 960
    cam.location = iso
    cam.rotation_euler = tuple(math.radians(a) for a in iso_rot)
    scene.render.filepath = str(out / "decor-check-iso.png")
    bpy.ops.render.render(write_still=True)
    cam.location = front
    cam.rotation_euler = (math.radians(90), 0, 0)
    scene.render.filepath = str(out / "decor-check-front.png")
    bpy.ops.render.render(write_still=True)


def extract_in_session(repo: str | Path, out_json: str | Path, gaps=None):
    """Run home-builder-adapter extraction inside the Blender session."""
    repo = Path(repo)
    sys.path.insert(0, str(repo / "kuchnie-core" / "src"))
    sys.path.insert(0, str(repo / "home-builder-adapter" / "src"))
    site = sorted((repo / "home-builder-adapter" / ".venv" / "lib").glob(
        "python*/site-packages"))
    if site:
        sys.path.append(str(site[-1]))  # pure-python yaml for kuchnie_core.loader

    import extract
    from kuchnie_core.serialize import kitchen_to_json

    try:
        kitchen = extract.extract_kitchen_from_blend()
    except Exception as e:  # noqa: BLE001
        # A failure the exploration run tolerates; strict mode escalates.
        if gaps:
            gaps.fail(f"adapter extraction failed: {type(e).__name__}: {e}")
        return None
    kitchen_to_json(kitchen, out_json)
    return kitchen
