"""E2E D60 LEGRABOX — Blender leg (wk-641a80a8).

Run:  /Applications/Blender.app/Contents/MacOS/Blender --background \
          --enable-autoexec --python blender_leg.py

Builds a room + one D60 3-drawer base cabinet via hb5 type classes
(headless, non-modal), applies a front decor DIFFERENT from the carcass
via the hb5 style system, renders an EEVEE check shot (the inspection
harness renders Workbench random colors — decor is unobservable there),
dumps the cage child hierarchy (splitter/opening probing for wk-81a47ab8),
runs adapter extraction as-is, and saves everything under generated/.
"""
import json
import math
import sys
from pathlib import Path

import addon_utils
import bpy

HERE = Path("/Users/michal/PycharmProjects/kuchnie/exercises/e2e-d60-legrabox")
REPO = Path("/Users/michal/PycharmProjects/kuchnie")
GEN = HERE / "generated"
GEN.mkdir(exist_ok=True)

LOG: list[str] = []


def log(msg: str) -> None:
    print(f"[e2e] {msg}")
    LOG.append(msg)


# ── 1. Addon + main-scene bootstrap ─────────────────────────────
sys.path.append("/Users/michal/PycharmProjects")
addon_utils.enable("home_builder_5", default_set=True, persistent=True)
log("addon enabled")

from home_builder_5 import hb_project, hb_types, hb_utils, units  # noqa: E402
from home_builder_5.product_libraries.frameless import (  # noqa: E402
    types_frameless,
    wood_materials,
)

ctx = bpy.context
scene = ctx.scene

main = hb_project.ensure_main_scene()
main.hb_frameless.ensure_default_style()
scene["IS_ROOM_SCENE"] = True
scene.unit_settings.system = "METRIC"
scene.unit_settings.length_unit = "MILLIMETERS"

# ── 2. Shop defaults: toe kick 100, drawer stack M(140)+C+C ─────
props = scene.hb_frameless
for name, val in [("default_toe_kick_height", units.millimeter(100)),
                  ("equal_drawer_stack_heights", False),
                  # NOTE: hb5 semantics — this is the top OPENING size, not
                  # the front height; fronts add overlays (US model). Kept
                  # at 140 to measure the delta vs the designed 140 front.
                  ("top_drawer_front_height", units.millimeter(140)),
                  # metric shop: 18mm board, not the imperial 3/4" default
                  ("default_carcass_part_thickness", units.millimeter(18))]:
    if hasattr(props, name):
        setattr(props, name, val)
        log(f"set hb_frameless.{name}")
    else:
        log(f"GAP: hb_frameless.{name} missing")

# ── 3. Headless shim: finish_colors user-data path is extension-bound ──
# GAP (flow): finish_colors._load_custom_colors resolves an extension
# user-data folder that does not exist under `--background` with the addon
# enabled as a legacy module — get_all_stain_colors raises ValueError.
# Patch custom colors to empty so the BUILT-IN stain table works.
from home_builder_5.product_libraries.frameless import finish_colors  # noqa: E402

try:
    finish_colors.get_all_stain_colors()
    log("finish_colors works unpatched")
except Exception as e:  # noqa: BLE001
    log(f"GAP-headless: finish_colors user-data path broken "
        f"({type(e).__name__}: {e}) — patching custom colors to empty")
    finish_colors._load_custom_colors = lambda: {"stain": {}, "paint": {}}

# ── 4. Room: 4 walls, 3.0 x 2.4 m ───────────────────────────────
L = units.millimeter(3000)
W = units.millimeter(2400)
for loc, rot, length in [((0, 0, 0), 0.0, L),
                         ((L, 0, 0), math.radians(90), W),
                         ((L, W, 0), math.radians(180), L),
                         ((0, W, 0), math.radians(270), W)]:
    w = hb_types.GeoNodeWall()
    w.create("Wall")
    w.set_input("Thickness", units.millimeter(100))
    w.set_input("Height", units.millimeter(2400))
    w.set_input("Length", length)
    w.obj.location = loc
    w.obj.rotation_euler.z = rot
log("4 walls built")

# ── 5. The cabinet (named per the inspection naming discipline) ─
cab = types_frameless.BaseCabinet()
cab.default_exterior = "3 Drawers"
cab.width = units.millimeter(600)
cab.depth = units.millimeter(560)
cab.height = units.millimeter(820)  # incl. toe kick
cab.create("B600-3DW-01 D60 Legrabox")
cab.obj.location = (units.millimeter(900), 0, 0)
hb_utils.run_calc_fix(ctx, cab.obj, passes=3)
log(f"cabinet created: {cab.obj.name}")

# GAP (metric): scene default_carcass_part_thickness did not propagate on
# create (parts came out 19.05 = 3/4"); force the property on every object
# in the subtree that carries it, then re-settle drivers.
forced = 0
for o in [cab.obj, *cab.obj.children_recursive]:
    if "Material Thickness" in o.keys():
        o["Material Thickness"] = units.millimeter(18)
        forced += 1
hb_utils.run_calc_fix(ctx, cab.obj, passes=3)
log(f"GAP-metric: Material Thickness forced to 18mm on {forced} object(s)")

# ── 5b. Front decor != carcass, via the hb5 style system ────────
# hb5 vocabulary: exterior finish (fronts, Finish Top/Bottom=True) vs
# interior material. OAK + darkest stain stands in for decor K5307;
# interior stays UV-ply — the analogue of 'fronty K5307, korpus bialy'.
mprops = main.hb_frameless
style = mprops.cabinet_styles[mprops.active_cabinet_style_index] \
    if len(mprops.cabinet_styles) else None
if style is None:
    log("GAP: no cabinet style after ensure_default_style")
else:
    try:
        style.wood_species = "OAK"
        names = list(finish_colors.get_all_stain_colors())
        dark = next((n for n in names if any(
            k in n.lower() for k in ("espresso", "ebony", "dark", "walnut"))),
            names[-1] if names else None)
        if dark:
            style.stain_color = dark
        style.assign_style_to_cabinet(cab.obj)
        log(f"style applied: OAK + stain '{dark}' on fronts; "
            f"finish mat = {style.material.name if style.material else None}")
        # GAP (semantics): hb5 'exterior finish' covers ALL exterior faces,
        # incl. carcass ends — US semantics. Polish melamine flow is
        # 'decor FRONTS ONLY, carcass white incl. visible ends'. The style
        # system cannot express that; per-part Finish-flag surgery below.
        surgically = 0
        for child in cab.obj.children_recursive:
            if "CABINET_PART" not in child:
                continue
            if child.get("IS_CABINET_FRONT"):
                continue
            if child.get("Finish Top") or child.get("Finish Bottom", True):
                child["Finish Top"] = False
                child["Finish Bottom"] = False
                surgically += 1
        style.assign_style_to_cabinet(cab.obj)  # re-apply with fixed flags
        log(f"GAP-semantics: carcass Finish flags forced off on "
            f"{surgically} part(s) so decor stays on fronts only")
    except Exception as e:  # noqa: BLE001
        log(f"GAP: style-driven decor failed: {type(e).__name__}: {e}")

# ── 6. EEVEE decor-check render (own eyes for the material split) ─
try:
    cam_data = bpy.data.cameras.new("e2e_cam")
    cam = bpy.data.objects.new("e2e_cam", cam_data)
    scene.collection.objects.link(cam)
    cam.location = (2.4, -1.6, 1.3)
    cam.rotation_euler = (math.radians(72), 0, math.radians(38))
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
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 960
    scene.render.filepath = str(GEN / "decor-check-iso.png")
    bpy.ops.render.render(write_still=True)
    log(f"decor check rendered ({scene.render.engine})")
    # straight-on front view for reveals
    cam.location = (1.2, -2.2, 0.5)
    cam.rotation_euler = (math.radians(90), 0, 0)
    scene.render.filepath = str(GEN / "decor-check-front.png")
    bpy.ops.render.render(write_still=True)
    log("front check rendered")
except Exception as e:  # noqa: BLE001
    log(f"GAP: own render failed: {type(e).__name__}: {e}")

bpy.ops.wm.save_as_mainfile(filepath=str(GEN / "d60-room.blend"))
log("blend saved")

# ── 7. Cage hierarchy dump — splitter/opening probe (wk-81a47ab8) ─
def dump_obj(obj, depth=0):
    entry = {
        "name": obj.name,
        "depth": depth,
        "id_props": {k: str(obj.get(k)) for k in obj.keys()
                     if not k.startswith("_")},
        "children": [],
    }
    # geo-node inputs live on modifiers; capture names+values where cheap
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


raw = {"cages": []}
for obj in bpy.data.objects:
    if obj.get("IS_FRAMELESS_CABINET_CAGE"):
        raw["cages"].append(dump_obj(obj))
(GEN / "cage-hierarchy.json").write_text(json.dumps(raw, indent=2))
log(f"hierarchy dump: {len(raw['cages'])} cage(s)")

# ── 8. Adapter extraction as-is ─────────────────────────────────
sys.path.insert(0, str(REPO / "kuchnie-core" / "src"))
sys.path.insert(0, str(REPO / "home-builder-adapter" / "src"))
site = sorted((REPO / "home-builder-adapter" / ".venv" / "lib").glob(
    "python*/site-packages"))
if site:
    sys.path.append(str(site[-1]))

import extract  # noqa: E402
from kuchnie_core.serialize import kitchen_to_json  # noqa: E402

try:
    kitchen = extract.extract_kitchen_from_blend()
    log("extraction OK (adapter as-is)")
    kitchen_to_json(kitchen, GEN / "extracted-kitchen.json")
    for r in kitchen.rows:
        for c in r.cabinets:
            log(f"  extracted: {c.type} {c.width_mm}x{c.height_mm}x"
                f"{c.depth_mm} plinth={c.plinth_height_mm} "
                f"drawers={c.drawers} body={c.body_material} "
                f"front={c.front_material}")
except Exception as e:  # noqa: BLE001
    log(f"GAP: adapter extraction failed: {type(e).__name__}: {e}")

(GEN / "blender-leg-log.txt").write_text("\n".join(LOG) + "\n")
print("[e2e] DONE")
