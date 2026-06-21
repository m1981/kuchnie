import bpy
import json
import os
import math

# ==========================================
# 1. CONFIGURATION & SETUP
# ==========================================
JSON_PATH = "layout.json"
# Output to scenes folder matching the API path structure
SCENE_ID = "kitchen_01"
ANGLE_ID = "main"
OUTPUT_DIR = os.path.abspath(f"assets/scenes/{SCENE_ID}/{ANGLE_ID}")
os.makedirs(OUTPUT_DIR, exist_ok=True)

with open(JSON_PATH, 'r') as f:
    layout_data = json.load(f)

bpy.ops.wm.read_factory_settings(use_empty=True)

scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'

scene.render.resolution_x = 800
scene.render.resolution_y = 600
scene.render.resolution_percentage = 200

# Organize our geometry into collections
fronts_collection = bpy.data.collections.new("Fronts")
carcass_collection = bpy.data.collections.new("Carcasses")
handle_collection = bpy.data.collections.new("Handles")
scene.collection.children.link(fronts_collection)
scene.collection.children.link(carcass_collection)
scene.collection.children.link(handle_collection)


# ==========================================
# 2. MATERIALS
# ==========================================
def hex_to_rgb(hex_str):
    hex_str = hex_str.lstrip('#')
    return tuple(int(hex_str[i:i + 2], 16) / 255.0 for i in (0, 2, 4)) + (1.0,)


def setup_front_materials(obj, hex_color):
    """Materials for the doors (These get textured by OpenCV)"""
    mat = bpy.data.materials.new(name=f"Mat_{obj.name}")
    obj.data.materials.append(mat)
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    for node in nodes: nodes.remove(node)

    out_node = nodes.new('ShaderNodeOutputMaterial')

    base_node = nodes.new('ShaderNodeBsdfPrincipled')
    base_node.inputs['Base Color'].default_value = (0.8, 0.8, 0.8, 1.0)

    uv_node = nodes.new('ShaderNodeEmission')
    uv_map_node = nodes.new('ShaderNodeUVMap')
    links.new(uv_map_node.outputs['UV'], uv_node.inputs['Color'])

    id_node = nodes.new('ShaderNodeEmission')
    id_node.inputs['Color'].default_value = hex_to_rgb(hex_color)

    refl_node = nodes.new('ShaderNodeBsdfPrincipled')
    refl_node.inputs['Base Color'].default_value = (0.0, 0.0, 0.0, 1.0)
    # TWEAK: Lower roughness for a smoother, cleaner laminate reflection
    refl_node.inputs['Roughness'].default_value = 0.05

    obj['mat_out'] = out_node.name
    obj['mat_base'] = base_node.name
    obj['mat_uv'] = uv_node.name
    obj['mat_id'] = id_node.name
    obj['mat_reflection'] = refl_node.name

    links.new(base_node.outputs[0], out_node.inputs[0])


# Material for the Carcass (Always dark, acts as the shadow gap)
carcass_mat = bpy.data.materials.new(name="Mat_Carcass")
carcass_mat.use_nodes = True
carcass_mat.node_tree.nodes["Principled BSDF"].inputs['Base Color'].default_value = (0.02, 0.02, 0.02, 1.0)

# Material for the Handles
handle_mat = bpy.data.materials.new(name="Mat_Handle")
handle_mat.use_nodes = True
h_bsdf = handle_mat.node_tree.nodes["Principled BSDF"]
h_bsdf.inputs['Base Color'].default_value = (0.8, 0.8, 0.8, 1.0)  # Silver
h_bsdf.inputs['Metallic'].default_value = 1.0
h_bsdf.inputs['Roughness'].default_value = 0.2

# ==========================================
# 3. ADVANCED GEOMETRY GENERATION
# ==========================================
current_x = 0.0
base_cabinets = []
GAP = 0.004  # 4mm gap
FRONT_T = 0.018  # 18mm thick door

for i, cab in enumerate(layout_data['cabinets']):
    w = cab['width_mm'] / 1000.0
    h = cab['height_mm'] / 1000.0
    d = cab['depth_mm'] / 1000.0

    # 1. CARCASS (The dark box behind)
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    carcass = bpy.context.active_object
    carcass.scale = (w, d - FRONT_T, h)
    bpy.ops.object.transform_apply(scale=True)
    carcass.location = (current_x + w / 2, -(d - FRONT_T) / 2, h / 2)
    carcass.data.materials.append(carcass_mat)
    bpy.context.scene.collection.objects.unlink(carcass)
    carcass_collection.objects.link(carcass)

    # 2. FRONT (The Door with 4mm gaps)
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    front = bpy.context.active_object
    front.scale = (w - GAP, FRONT_T, h - GAP)
    bpy.ops.object.transform_apply(scale=True)
    front.location = (current_x + w / 2, -d + FRONT_T / 2, h / 2)
    bpy.context.scene.collection.objects.unlink(front)
    fronts_collection.objects.link(front)

    # UV Map the Front
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.cube_project(cube_size=1.0)
    bpy.ops.object.mode_set(mode='OBJECT')
    setup_front_materials(front, cab['id_hex'])

    if cab['type'] == 'base':
        base_cabinets.append({'min_x': current_x, 'max_x': current_x + w, 'h': h, 'd': d})

    # 3. EDGE PULL HANDLE
    if cab.get('handle') == 'edge_pull':
        handle_w = min(0.2, w - 0.05)
        if cab['type'] == 'base':
            bpy.ops.mesh.primitive_cube_add(size=1.0)
            lip = bpy.context.active_object
            lip.scale = (handle_w, 0.02, 0.002)
            bpy.ops.object.transform_apply(scale=True)
            lip.location = (current_x + w / 2, -d + 0.01, h - GAP / 2 + 0.001)

            bpy.ops.mesh.primitive_cube_add(size=1.0)
            drop = bpy.context.active_object
            drop.scale = (handle_w, 0.002, 0.02)
            bpy.ops.object.transform_apply(scale=True)
            drop.location = (current_x + w / 2, -d - 0.001, h - GAP / 2 - 0.01)
        elif cab['type'] == 'tall':
            bpy.ops.mesh.primitive_cube_add(size=1.0)
            lip = bpy.context.active_object
            lip.scale = (0.002, 0.02, handle_w * 2)
            bpy.ops.object.transform_apply(scale=True)
            lip.location = (current_x + GAP / 2 - 0.001, -d + 0.01, h / 2)

            bpy.ops.mesh.primitive_cube_add(size=1.0)
            drop = bpy.context.active_object
            drop.scale = (0.02, 0.002, handle_w * 2)
            bpy.ops.object.transform_apply(scale=True)
            drop.location = (current_x + GAP / 2 + 0.01, -d - 0.001, h / 2)

        bpy.ops.object.select_all(action='DESELECT')
        lip.select_set(True)
        drop.select_set(True)
        bpy.context.view_layer.objects.active = lip
        bpy.ops.object.join()
        lip.data.materials.append(handle_mat)
        bpy.context.scene.collection.objects.unlink(lip)
        handle_collection.objects.link(lip)

    current_x += w

# Countertop
if base_cabinets and 'countertop' in layout_data:
    ct_data = layout_data['countertop']
    ct_t = ct_data['thickness_mm'] / 1000.0
    ct_overhang = ct_data['overhang_mm'] / 1000.0
    min_x = min(c['min_x'] for c in base_cabinets)
    max_x = max(c['max_x'] for c in base_cabinets)
    max_h = max(c['h'] for c in base_cabinets)
    max_d = max(c['d'] for c in base_cabinets)

    bpy.ops.mesh.primitive_cube_add(size=1.0)
    ct = bpy.context.active_object
    ct.scale = (max_x - min_x, max_d + ct_overhang, ct_t)
    bpy.ops.object.transform_apply(scale=True)
    ct.location = (min_x + (max_x - min_x) / 2, -(max_d + ct_overhang) / 2, max_h + ct_t / 2)

    bpy.context.scene.collection.objects.unlink(ct)
    fronts_collection.objects.link(ct)

    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.cube_project(cube_size=1.0)
    bpy.ops.object.mode_set(mode='OBJECT')
    setup_front_materials(ct, ct_data['id_hex'])

# ==========================================
# 4. CAMERA & LIGHTING (STUDIO SETUP)
# ==========================================
cam_data = bpy.data.cameras.new("Camera")
cam_obj = bpy.data.objects.new("Camera", cam_data)
scene.collection.objects.link(cam_obj)
scene.camera = cam_obj

total_width = current_x
center_x = total_width / 2.0

# Wider FOV (50 degrees) for better perspective visibility
cam_data.angle = math.radians(50)
distance = (total_width / 2.0) / math.tan(cam_data.angle / 2.0) * 1.4

# --- 3/4 ANGLE: Shift camera right and up for depth perception ---
cam_obj.location = (
    center_x + total_width * 0.35,  # Shift right for 3/4 view
    -distance * 1.15,                # Pull back slightly
    distance * 0.5                   # Raise camera higher
)

empty_target = bpy.data.objects.new("CamTarget", None)
empty_target.location = (center_x, 0, 0.85)  # Look slightly above center
scene.collection.objects.link(empty_target)
tt = cam_obj.constraints.new(type='TRACK_TO')
tt.target = empty_target
tt.track_axis = 'TRACK_NEGATIVE_Z'
tt.up_axis = 'UP_Y'

world = bpy.data.worlds.new("World")
scene.world = world
world.use_nodes = True
bg_node = world.node_tree.nodes.get("Background")
bg_node.inputs[0].default_value = (0.8, 0.85, 0.9, 1.0)  # Slight blue tint for realism
bg_node.inputs[1].default_value = 0.05  # Very low ambient — let the light do the work

# --- 3-POINT STUDIO LIGHTING ---

# KEY LIGHT: Main softbox, top-right, warm
key_data = bpy.data.lights.new("KeyLight", 'AREA')
key_data.energy = 800.0
key_data.shape = 'RECTANGLE'
key_data.size = 3.0
key_data.size_y = 2.0
key_data.color = (1.0, 0.95, 0.9)  # Slightly warm
key_obj = bpy.data.objects.new("KeyLight", key_data)
scene.collection.objects.link(key_obj)
key_obj.location = (center_x + total_width * 0.3, -distance + 1.5, distance * 0.9)
tt_key = key_obj.constraints.new(type='TRACK_TO')
tt_key.target = empty_target
tt_key.track_axis = 'TRACK_NEGATIVE_Z'
tt_key.up_axis = 'UP_Y'

# FILL LIGHT: Left side, cooler, softer
fill_data = bpy.data.lights.new("FillLight", 'AREA')
fill_data.energy = 250.0
fill_data.shape = 'RECTANGLE'
fill_data.size = 4.0
fill_data.size_y = 3.0
fill_data.color = (0.9, 0.95, 1.0)  # Slightly cool
fill_obj = bpy.data.objects.new("FillLight", fill_data)
scene.collection.objects.link(fill_obj)
fill_obj.location = (center_x - total_width * 0.4, -distance * 0.6, distance * 0.5)
tt_fill = fill_obj.constraints.new(type='TRACK_TO')
tt_fill.target = empty_target
tt_fill.track_axis = 'TRACK_NEGATIVE_Z'
tt_fill.up_axis = 'UP_Y'

# RIM LIGHT: Behind camera, edge highlight on cabinet tops
rim_data = bpy.data.lights.new("RimLight", 'AREA')
rim_data.energy = 400.0
rim_data.shape = 'RECTANGLE'
rim_data.size = total_width * 1.2
rim_data.size_y = 0.5
rim_obj = bpy.data.objects.new("RimLight", rim_data)
scene.collection.objects.link(rim_obj)
rim_obj.location = (center_x, -distance * 1.5, distance * 0.15)
tt_rim = rim_obj.constraints.new(type='TRACK_TO')
tt_rim.target = empty_target
tt_rim.track_axis = 'TRACK_NEGATIVE_Z'
tt_rim.up_axis = 'UP_Y'


# ==========================================
# 5. SEQUENTIAL RENDER PIPELINE
# ==========================================

# Switch helper functions to lock down render mathematics based on layer needs
def configure_engine_for_art():
    scene.cycles.samples = 128
    scene.cycles.use_denoising = True
    scene.cycles.use_fast_gi = True  # Fast AO approximation for Cycles
    scene.cycles.fast_gi_method = 'REPLACE'  # Use Fast GI to replace bounces with AO
    scene.cycles.ao_bounces_render = 4  # AO bounces for render quality
    scene.cycles.max_bounces = 8  # More bounces = better indirect lighting
    scene.render.filter_size = 1.5
    scene.render.dither_intensity = 1.0 # Art wants dither gradient

def configure_engine_for_math():
    scene.cycles.samples = 1            # Never blur light bounces. We only need the precise value.
    scene.cycles.use_denoising = False  # NEVER AI smudge coordinates!
    scene.render.filter_size = 0.0      # MUST disable Anti-aliasing perfectly sharp masking.
    scene.render.dither_intensity = 0.0 # <--- ADD THIS FIX FOR MATH. NEUTRALIZE PIXEL SHAKING!

def switch_front_materials(pass_name):
    for obj in fronts_collection.objects:
        if obj.data.materials:
            mat = obj.data.materials[0]
            nodes = mat.node_tree.nodes
            links = mat.node_tree.links
            out_node = nodes[obj['mat_out']]
            target_node = nodes[obj[f'mat_{pass_name}']]
            for link in out_node.inputs[0].links: links.remove(link)
            links.new(target_node.outputs[0], out_node.inputs[0])


def set_handles_visibility(visible):
    for obj in handle_collection.objects: obj.hide_render = not visible


def set_shadow_catchers(active):
    for obj in fronts_collection.objects: obj.is_shadow_catcher = active
    for obj in carcass_collection.objects: obj.is_shadow_catcher = active


# --- PASS 1: BASE PASS ---
print("Rendering Base Pass...")
configure_engine_for_art()
switch_front_materials('base')
set_handles_visibility(False)
set_shadow_catchers(False)
scene.view_settings.view_transform = 'Standard'
scene.render.film_transparent = False
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_depth = '8'
scene.render.image_settings.color_mode = 'RGB'
scene.render.filepath = os.path.join(OUTPUT_DIR, "base_pass.png")
bpy.ops.render.render(write_still=True)

# --- PASS 2: UV PASS ---
print("Rendering UV Pass...")
configure_engine_for_math()  # Lock out blurring
switch_front_materials('uv')
set_handles_visibility(False)
scene.view_settings.view_transform = 'Raw'
scene.render.film_transparent = True
scene.render.image_settings.file_format = 'OPEN_EXR'
scene.render.image_settings.color_depth = '32'
scene.render.image_settings.color_mode = 'RGB'
scene.render.filepath = os.path.join(OUTPUT_DIR, "uv_pass.exr")
bpy.ops.render.render(write_still=True)

# --- PASS 3: ID MASK ---
print("Rendering ID Mask Pass...")
configure_engine_for_math() # Lock out blurring
switch_front_materials('id')
set_handles_visibility(False)
scene.view_settings.view_transform = 'Raw'
scene.render.film_transparent = True
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_depth = '8'
scene.render.image_settings.color_mode = 'RGB'
scene.render.filepath = os.path.join(OUTPUT_DIR, "id_mask.png")
bpy.ops.render.render(write_still=True)

# --- PASS 4: REFLECTION PASS ---
print("Rendering Reflection Pass...")
configure_engine_for_art()
switch_front_materials('reflection')
set_handles_visibility(False)

# --- THE FIX: TURN WORLD BLACK FOR REFLECTIONS ---
bg_node = scene.world.node_tree.nodes.get("Background")
bg_node.inputs[0].default_value = (0.0, 0.0, 0.0, 1.0)
scene.view_settings.view_transform = 'Standard'
scene.render.film_transparent = True
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_depth = '8'
scene.render.image_settings.color_mode = 'RGB'
scene.render.filepath = os.path.join(OUTPUT_DIR, "reflection_pass.png")
bpy.ops.render.render(write_still=True)

# --- PASS 5: HANDLE PASS ---
print("Rendering Handle Pass (Shadow Catcher)...")
configure_engine_for_art()
switch_front_materials('base')
set_handles_visibility(True)
set_shadow_catchers(True)
bg_node.inputs[0].default_value = (1.0, 1.0, 1.0, 1.0)
scene.render.film_transparent = True
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_depth = '8'
scene.render.image_settings.color_mode = 'RGBA'
scene.render.filepath = os.path.join(OUTPUT_DIR, "handle_pass.png")
bpy.ops.render.render(write_still=True)

print(f"Pipeline complete! 5 Assets saved to: {OUTPUT_DIR}")