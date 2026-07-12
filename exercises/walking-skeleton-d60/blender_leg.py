"""Walking skeleton D60 — Blender leg (wk-9f1ad053).

Run:  blender --background --python blender_leg.py

Builds a 4-wall room + one 600mm 3-drawer base cabinet using
home_builder_5's own type classes (non-modal path), saves the .blend,
then runs home-builder-adapter extraction IN-SESSION and dumps the
extracted Kitchen JSON + a raw dump of what the scene actually stores.
"""
import json
import math
import sys
from pathlib import Path

import addon_utils
import bpy

HERE = Path("/Users/michal/PycharmProjects/kuchnie/exercises/walking-skeleton-d60")
REPO = Path("/Users/michal/PycharmProjects/kuchnie")
GEN = HERE / "generated"
GEN.mkdir(exist_ok=True)

LOG: list[str] = []


def log(msg: str) -> None:
    print(f"[skeleton] {msg}")
    LOG.append(msg)


# ── 1. Enable home_builder_5 as legacy addon ────────────────────
sys.path.append("/Users/michal/PycharmProjects")
addon_utils.enable("home_builder_5", default_set=True, persistent=True)
log("addon enabled")

from home_builder_5 import hb_project, hb_types, hb_utils, units  # noqa: E402
from home_builder_5.product_libraries.frameless import types_frameless  # noqa: E402

ctx = bpy.context
scene = ctx.scene

# ── 2. What load_post would normally do ─────────────────────────
main = hb_project.ensure_main_scene()
main.hb_frameless.ensure_default_style()
scene["IS_ROOM_SCENE"] = True
scene.unit_settings.system = "METRIC"
scene.unit_settings.length_unit = "MILLIMETERS"

# Shop defaults (meters). Guard each — property names may drift.
props = scene.hb_frameless
for name, val in [("default_toe_kick_height", units.millimeter(100)),
                  ("equal_drawer_stack_heights", False),
                  ("top_drawer_front_height", units.millimeter(140))]:
    if hasattr(props, name):
        setattr(props, name, val)
        log(f"set hb_frameless.{name}")
    else:
        log(f"GAP: hb_frameless.{name} missing")

# ── 3. Room: 4 walls, 3.0 x 2.4 m ───────────────────────────────
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

# ── 4. One 600mm base cabinet, 3-drawer stack ───────────────────
cab = types_frameless.BaseCabinet()
cab.default_exterior = "3 Drawers"
cab.width = units.millimeter(600)
cab.depth = units.millimeter(560)
cab.height = units.millimeter(820)  # incl. toe kick, per adapter semantics
cab.create("Base 600 3-Drawer")
cab.obj.location = (units.millimeter(600), 0, 0)
hb_utils.run_calc_fix(ctx, cab.obj, passes=3)
log("cabinet created")

bpy.ops.wm.save_as_mainfile(filepath=str(GEN / "d60-room.blend"))
log("blend saved")

# ── 5. Raw dump: what does the cage ACTUALLY store? ─────────────
raw: dict = {"cages": []}
for obj in bpy.data.objects:
    if not obj.get("IS_FRAMELESS_CABINET_CAGE"):
        continue
    raw["cages"].append({
        "name": obj.name,
        "id_props": {k: str(obj.get(k)) for k in obj.keys()},
        "dimensions_bbox_m": [round(v, 4) for v in obj.dimensions],
    })
(GEN / "raw-cage-dump.json").write_text(json.dumps(raw, indent=2))
log(f"raw dump: {len(raw['cages'])} cage(s)")

# ── 6. Adapter extraction in-session ────────────────────────────
sys.path.insert(0, str(REPO / "kuchnie-core" / "src"))
sys.path.insert(0, str(REPO / "home-builder-adapter" / "src"))
site = sorted((REPO / "home-builder-adapter" / ".venv" / "lib").glob(
    "python*/site-packages"))
if site:
    sys.path.append(str(site[-1]))  # pure-python yaml for kuchnie_core.loader

import extract  # noqa: E402
from kuchnie_core.serialize import kitchen_to_json  # noqa: E402

try:
    kitchen = extract.extract_kitchen_from_blend()
    log("extraction OK (adapter as-is)")
except Exception as e:  # noqa: BLE001
    log(f"GAP CONFIRMED: adapter extraction failed: {type(e).__name__}: {e}")
    # SHIM (exercise-only, NOT a fix): read what a corrected extractor
    # would — hb5 stores dimensions on the evaluated cage bbox and
    # toe-kick as an ID prop; Dim X/Y/Z + opening_sizes ID props do not
    # exist (see raw-cage-dump.json / gap E6-E7).
    cabs = []
    for obj in bpy.data.objects:
        if not obj.get("IS_FRAMELESS_CABINET_CAGE"):
            continue
        cabs.append({
            "type": extract._TYPE_MAP.get(obj.get("CABINET_TYPE", "BASE"),
                                          "dolna_drzwiowa"),
            "width_mm": round(obj.dimensions.x * 1000),
            "height_mm": round(obj.dimensions.z * 1000),
            "depth_mm": round(obj.dimensions.y * 1000),
            "toe_kick_mm": round(obj.get("Toe Kick Height", 0.0) * 1000),
            "drawers": [],  # opening_sizes unreachable — gap E6
            "shelves": 0,
        })
    kitchen = extract.cabinets_to_kitchen(cabs)
    log(f"shim extraction: {len(cabs)} cabinet(s) via bbox")

kitchen_to_json(kitchen, GEN / "extracted-kitchen.json")
for r in kitchen.rows:
    for c in r.cabinets:
        log(f"  extracted: {c.type} {c.width_mm}x{c.height_mm}x"
            f"{c.depth_mm} plinth={c.plinth_height_mm} "
            f"drawers={c.drawers}")

(GEN / "blender-leg-log.txt").write_text("\n".join(LOG) + "\n")
print("[skeleton] DONE")
