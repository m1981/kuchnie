import bpy
import json
import os
import math
from mathutils import Vector

# ==========================================
# 1. CONFIGURATION & SETUP
# ==========================================

JSON_PATH = "layout.json"
OUTPUT_DIR = os.path.abspath("assets")

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Generate a dummy JSON file if it doesn't exist
if not os.path.exists(JSON_PATH):
    print(f"[{JSON_PATH}] not found. Generating default layout...")
    default_layout = {
        "scene_name": "linear_kitchen_01",
        "cabinets": [
            {"type": "tall", "width_mm": 600, "height_mm": 2000, "depth_mm": 600, "id_hex": "#FF0000"},
            {"type": "base", "width_mm": 800, "height_mm": 820, "depth_mm": 600, "id_hex": "#00FF00"},
            {"type": "base", "width_mm": 600, "height_mm": 820, "depth_mm": 600, "id_hex": "#0000FF"}
        ],
        "countertop": {
            "thickness_mm": 40,
            "overhang_mm": 20,
            "id_hex": "#FFFF00"
        }
    }
    with open(JSON_PATH, 'w') as f:
        json.dump(default_layout, f, indent=4)

# Load the JSON layout
with open(JSON_PATH, 'r') as f:
    layout_data = json.load(f)

# Clear the default Blender scene
bpy.ops.wm.read_factory_settings(use_empty=True)

# Set Render Engine to EEVEE
scene = bpy.context.scene
try:
    scene.render.engine = 'BLENDER_EEVEE_NEXT'  # Blender 4.2+
except TypeError:
    scene.render.engine = 'BLENDER_EEVEE'  # Blender 3.x - 4.1

# Resolution
scene.render.resolution_x = 800
scene.render.resolution_y = 600
scene.render.resolution_percentage = 100


# ==========================================
# 2. HELPER FUNCTIONS
# ==========================================

def hex_to_rgb(hex_str):
    """Converts a hex color string to a linear RGB tuple."""
    hex_str = hex_str.lstrip('#')
    return tuple(int(hex_str[i:i + 2], 16) / 255.0 for i in (0, 2, 4)) + (1.0,)


def setup_materials(obj, hex_color):
    """
    Creates a single material with 3 distinct shader nodes (Base, UV, ID).
    We store references to these nodes so we can hot-swap them before each render pass.
    """
    mat = bpy.data.materials.new(name=f"Mat_{obj.name}")

    # In modern bpy, materials use nodes by default.
    # We don't set mat.use_nodes = True to avoid the DeprecationWarning.
    obj.data.materials.append(mat)

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    # Clear default nodes
    for node in nodes:
        nodes.remove(node)

    # Material Output
    out_node = nodes.new('ShaderNodeOutputMaterial')
    out_node.location = (300, 0)

    # --- Pass 1: Base (Principled BSDF) ---
    base_node = nodes.new('ShaderNodeBsdfPrincipled')
    base_node.location = (0, 200)
    base_node.inputs['Base Color'].default_value = (0.8, 0.8, 0.8, 1.0)  # White/Gray diffuse

    # --- Pass 2: UV (Emission) ---
    uv_node = nodes.new('ShaderNodeEmission')
    uv_node.location = (0, 0)
    uv_map_node = nodes.new('ShaderNodeUVMap')
    uv_map_node.location = (-200, 0)
    links.new(uv_map_node.outputs['UV'], uv_node.inputs['Color'])

    # --- Pass 3: ID Mask (Emission) ---
    id_node = nodes.new('ShaderNodeEmission')
    id_node.location = (0, -200)
    id_node.inputs['Color'].default_value = hex_to_rgb(hex_color)

    # Store node names in object custom properties for easy switching later
    obj['mat_out'] = out_node.name
    obj['mat_base'] = base_node.name
    obj['mat_uv'] = uv_node.name
    obj['mat_id'] = id_node.name

    # Default to base
    links.new(base_node.outputs[0], out_node.inputs[0])


# ==========================================
# 3. GEOMETRY & UV GENERATION
# ==========================================

current_x = 0.0
base_cabinets = []

for i, cab in enumerate(layout_data['cabinets']):
    w = cab['width_mm'] / 1000.0
    h = cab['height_mm'] / 1000.0
    d = cab['depth_mm'] / 1000.0

    bpy.ops.mesh.primitive_cube_add(size=1.0)
    obj = bpy.context.active_object
    obj.name = f"Cabinet_{cab['type']}_{i}"

    obj.scale = (w, d, h)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.location = (current_x + w / 2, -d / 2, h / 2)

    if cab['type'] == 'base':
        base_cabinets.append({'min_x': current_x, 'max_x': current_x + w, 'h': h, 'd': d})

    current_x += w

    # UV Mapping
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.cube_project(cube_size=1.0)
    bpy.ops.object.mode_set(mode='OBJECT')

    setup_materials(obj, cab['id_hex'])

# Generate Countertop
if base_cabinets and 'countertop' in layout_data:
    ct_data = layout_data['countertop']
    ct_t = ct_data['thickness_mm'] / 1000.0
    ct_overhang = ct_data['overhang_mm'] / 1000.0

    min_x = min(c['min_x'] for c in base_cabinets)
    max_x = max(c['max_x'] for c in base_cabinets)
    max_h = max(c['h'] for c in base_cabinets)
    max_d = max(c['d'] for c in base_cabinets)

    w = max_x - min_x
    d = max_d + ct_overhang
    h = ct_t

    bpy.ops.mesh.primitive_cube_add(size=1.0)
    ct = bpy.context.active_object
    ct.name = "Countertop"

    ct.scale = (w, d, h)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    ct.location = (min_x + w / 2, -(max_d + ct_overhang) / 2, max_h + h / 2)

    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.cube_project(cube_size=1.0)
    bpy.ops.object.mode_set(mode='OBJECT')

    setup_materials(ct, ct_data['id_hex'])

# ==========================================
# 4. CAMERA & LIGHTING SETUP
# ==========================================

all_meshes = [obj for obj in bpy.data.objects if obj.type == 'MESH']
min_x = min((obj.location.x - obj.dimensions.x / 2) for obj in all_meshes)
max_x = max((obj.location.x + obj.dimensions.x / 2) for obj in all_meshes)
min_y = min((obj.location.y - obj.dimensions.y / 2) for obj in all_meshes)
max_y = max((obj.location.y + obj.dimensions.y / 2) for obj in all_meshes)
max_z = max((obj.location.z + obj.dimensions.z / 2) for obj in all_meshes)

center_x = (min_x + max_x) / 2.0
center_y = (min_y + max_y) / 2.0
center_z = max_z / 2.0
total_width = max_x - min_x

cam_data = bpy.data.cameras.new("Camera")
cam_obj = bpy.data.objects.new("Camera", cam_data)
bpy.context.scene.collection.objects.link(cam_obj)
bpy.context.scene.camera = cam_obj

fov = cam_data.angle_x
distance = (total_width / 2.0) / math.tan(fov / 2.0)
distance *= 1.4

cam_obj.location = (center_x, center_y + distance, center_z + distance * 0.3)

empty_target = bpy.data.objects.new("CamTarget", None)
empty_target.location = (center_x, center_y, center_z)
bpy.context.scene.collection.objects.link(empty_target)

tt = cam_obj.constraints.new(type='TRACK_TO')
tt.target = empty_target
tt.track_axis = 'TRACK_NEGATIVE_Z'
tt.up_axis = 'UP_Y'

sun_data = bpy.data.lights.new("Sun", 'SUN')
sun_data.energy = 2.0
sun_obj = bpy.data.objects.new("Sun", sun_data)
bpy.context.scene.collection.objects.link(sun_obj)
sun_obj.rotation_euler = (math.radians(45), math.radians(30), math.radians(45))

if hasattr(scene, 'eevee'):
    if hasattr(scene.eevee, 'use_gtao'):
        scene.eevee.use_gtao = True
    elif hasattr(scene.eevee, 'use_raytracing'):
        scene.eevee.use_raytracing = True

    # ==========================================


# 5. DIRECT RENDER PIPELINE (No Compositor)
# ==========================================

def switch_materials_to_pass(pass_name):
    """Iterates through all meshes and connects the requested shader to the Material Output."""
    for obj in bpy.data.objects:
        if obj.type == 'MESH' and obj.data.materials:
            mat = obj.data.materials[0]
            nodes = mat.node_tree.nodes
            links = mat.node_tree.links

            out_node = nodes[obj['mat_out']]
            target_node = nodes[obj[f'mat_{pass_name}']]

            for link in out_node.inputs[0].links:
                links.remove(link)

            links.new(target_node.outputs[0], out_node.inputs[0])


# ------------------------------------------
# RENDER PASS 1: BASE PASS (8-bit RGB)
# ------------------------------------------
print("Rendering Base Pass...")
switch_materials_to_pass('base')
scene.view_settings.view_transform = 'Standard'

scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_depth = '8'
scene.render.filepath = os.path.join(OUTPUT_DIR, "base_pass.png")

bpy.ops.render.render(write_still=True)

# ------------------------------------------
# RENDER PASS 2: UV PASS (32-bit Float EXR)
# ------------------------------------------
print("Rendering UV Pass...")
switch_materials_to_pass('uv')
scene.view_settings.view_transform = 'Raw'

scene.render.image_settings.file_format = 'OPEN_EXR'
scene.render.image_settings.color_depth = '32'
scene.render.filepath = os.path.join(OUTPUT_DIR, "uv_pass.exr")

bpy.ops.render.render(write_still=True)

# ------------------------------------------
# RENDER PASS 3: ID MASK (8-bit RGB, NO AA)
# ------------------------------------------
print("Rendering ID Mask Pass...")
switch_materials_to_pass('id')
scene.view_settings.view_transform = 'Raw'

# CRITICAL: Disable Anti-Aliasing for OpenCV edge detection
scene.render.filter_size = 0.0
if hasattr(scene, 'eevee'):
    if hasattr(scene.eevee, 'taa_render_samples'):
        scene.eevee.taa_render_samples = 1

scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_depth = '8'
scene.render.filepath = os.path.join(OUTPUT_DIR, "id_mask.png")

bpy.ops.render.render(write_still=True)

print(f"Pipeline complete! Assets saved to: {OUTPUT_DIR}")