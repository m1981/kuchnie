import bpy
import json
import os
import math

# ==========================================
# 1. SETUP
# ==========================================
JSON_PATH = "layout.json"
OUTPUT_DIR = os.path.abspath("assets")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Updated JSON to use the new "edge_pull" handle
default_layout = {
    "scene_name": "linear_kitchen_01",
    "cabinets": [
        {"type": "tall", "width_mm": 600, "height_mm": 2000, "depth_mm": 600, "id_hex": "#FF0000",
         "handle": "edge_pull"},
        {"type": "base", "width_mm": 800, "height_mm": 820, "depth_mm": 600, "id_hex": "#00FF00",
         "handle": "edge_pull"},
        {"type": "base", "width_mm": 600, "height_mm": 820, "depth_mm": 600, "id_hex": "#0000FF", "handle": "edge_pull"}
    ],
    "countertop": {"thickness_mm": 40, "overhang_mm": 20, "id_hex": "#FFFF00"}
}
with open(JSON_PATH, 'w') as f: json.dump(default_layout, f, indent=4)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = 16
scene.render.resolution_x = 1200
scene.render.resolution_y = 800

# ==========================================
# 2. NEON WIREFRAME MATERIAL
# ==========================================
mat = bpy.data.materials.new("WireframeMat")
mat.use_nodes = True
nodes = mat.node_tree.nodes
links = mat.node_tree.links
for n in nodes: nodes.remove(n)

out = nodes.new('ShaderNodeOutputMaterial')
emit = nodes.new('ShaderNodeEmission')
mix = nodes.new('ShaderNodeMixRGB')
wire = nodes.new('ShaderNodeWireframe')

wire.inputs[0].default_value = 0.02
mix.inputs[1].default_value = (0.05, 0.05, 0.05, 1.0)
mix.inputs[2].default_value = (0.0, 1.0, 0.5, 1.0)

links.new(wire.outputs[0], mix.inputs[0])
links.new(mix.outputs[0], emit.inputs[0])
links.new(emit.outputs[0], out.inputs[0])

# ==========================================
# 3. ADVANCED GEOMETRY GENERATION
# ==========================================
current_x = 0.0
base_cabinets = []

GAP = 0.004  # 4mm gap between fronts
FRONT_T = 0.018  # 18mm thick MDF/Krono board

for i, cab in enumerate(default_layout['cabinets']):
    w = cab['width_mm'] / 1000.0
    h = cab['height_mm'] / 1000.0
    d = cab['depth_mm'] / 1000.0

    # --- 1. THE CARCASS (The box behind the door) ---
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    carcass = bpy.context.active_object
    carcass.scale = (w, d - FRONT_T, h)
    bpy.ops.object.transform_apply(scale=True)
    carcass.location = (current_x + w / 2, -(d - FRONT_T) / 2, h / 2)
    carcass.data.materials.append(mat)

    # --- 2. THE FRONT (The Door/Drawer with 4mm gaps) ---
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    front = bpy.context.active_object
    # Subtract the gap from width and height!
    front.scale = (w - GAP, FRONT_T, h - GAP)
    bpy.ops.object.transform_apply(scale=True)
    front.location = (current_x + w / 2, -d + FRONT_T / 2, h / 2)
    front.data.materials.append(mat)

    if cab['type'] == 'base':
        base_cabinets.append({'min_x': current_x, 'max_x': current_x + w, 'h': h, 'd': d})

    # --- 3. THE EDGE PULL HANDLE ---
    if cab.get('handle') == 'edge_pull':
        handle_w = min(0.2, w - 0.05)  # 20cm wide, or slightly less than door

        if cab['type'] == 'base':
            # Horizontal handle on TOP edge
            # Top Lip
            bpy.ops.mesh.primitive_cube_add(size=1.0)
            lip = bpy.context.active_object
            lip.scale = (handle_w, 0.02, 0.002)
            bpy.ops.object.transform_apply(scale=True)
            lip.location = (current_x + w / 2, -d + 0.01, h - GAP / 2 + 0.001)

            # Front Drop
            bpy.ops.mesh.primitive_cube_add(size=1.0)
            drop = bpy.context.active_object
            drop.scale = (handle_w, 0.002, 0.02)
            bpy.ops.object.transform_apply(scale=True)
            drop.location = (current_x + w / 2, -d - 0.001, h - GAP / 2 - 0.01)

        elif cab['type'] == 'tall':
            # Vertical handle on LEFT edge
            # Side Lip
            bpy.ops.mesh.primitive_cube_add(size=1.0)
            lip = bpy.context.active_object
            lip.scale = (0.002, 0.02, handle_w * 2)  # Longer for tall cabinets
            bpy.ops.object.transform_apply(scale=True)
            lip.location = (current_x + GAP / 2 - 0.001, -d + 0.01, h / 2)

            # Front Drop
            bpy.ops.mesh.primitive_cube_add(size=1.0)
            drop = bpy.context.active_object
            drop.scale = (0.02, 0.002, handle_w * 2)
            bpy.ops.object.transform_apply(scale=True)
            drop.location = (current_x + GAP / 2 + 0.01, -d - 0.001, h / 2)

        # Join handle parts
        bpy.ops.object.select_all(action='DESELECT')
        lip.select_set(True)
        drop.select_set(True)
        bpy.context.view_layer.objects.active = lip
        bpy.ops.object.join()
        lip.data.materials.append(mat)

    current_x += w

# Countertop
if base_cabinets:
    ct_t = 0.04
    ct_overhang = 0.02
    min_x = min(c['min_x'] for c in base_cabinets)
    max_x = max(c['max_x'] for c in base_cabinets)
    max_h = max(c['h'] for c in base_cabinets)
    max_d = max(c['d'] for c in base_cabinets)

    bpy.ops.mesh.primitive_cube_add(size=1.0)
    ct = bpy.context.active_object
    ct.scale = (max_x - min_x, max_d + ct_overhang, ct_t)
    bpy.ops.object.transform_apply(scale=True)
    ct.location = (min_x + (max_x - min_x) / 2, -(max_d + ct_overhang) / 2, max_h + ct_t / 2)
    ct.data.materials.append(mat)

# ==========================================
# 4. CAMERA & RENDER
# ==========================================
cam_data = bpy.data.cameras.new("Camera")
cam_obj = bpy.data.objects.new("Camera", cam_data)
scene.collection.objects.link(cam_obj)
scene.camera = cam_obj

total_width = current_x
center_x = total_width / 2.0
distance = (total_width / 2.0) / math.tan(cam_data.angle_x / 2.0) * 1.4
# Moved camera slightly to the right and down to see the gaps and handles better
cam_obj.location = (center_x + 0.5, -distance, 0.8)

empty_target = bpy.data.objects.new("CamTarget", None)
empty_target.location = (center_x, -0.3, 0.5)
scene.collection.objects.link(empty_target)
tt = cam_obj.constraints.new(type='TRACK_TO')
tt.target = empty_target
tt.track_axis = 'TRACK_NEGATIVE_Z'
tt.up_axis = 'UP_Y'

scene.render.filepath = os.path.join(OUTPUT_DIR, "wireframe_view.png")
bpy.ops.render.render(write_still=True)
print(f"Wireframe saved to: {scene.render.filepath}")