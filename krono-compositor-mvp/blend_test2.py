import bpy
import json
import os
import math

# ==========================================
# 1. CONFIGURATION & SETUP
# ==========================================

JSON_PATH = "layout.json"
OUTPUT_DIR = os.path.abspath("assets")
os.makedirs(OUTPUT_DIR, exist_ok=True)

if not os.path.exists(JSON_PATH):
    default_layout = {
        "scene_name": "linear_kitchen_01",
        "cabinets": [
            {"type": "tall", "width_mm": 600, "height_mm": 2000, "depth_mm": 600, "id_hex": "#FF0000", "handle": "bar"},
            {"type": "base", "width_mm": 800, "height_mm": 820, "depth_mm": 600, "id_hex": "#00FF00", "handle": "bar"},
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

with open(JSON_PATH, 'r') as f:
    layout_data = json.load(f)

bpy.ops.wm.read_factory_settings(use_empty=True)

scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 64

scene.render.resolution_x = 800
scene.render.resolution_y = 600
scene.render.resolution_percentage = 100

cabinet_collection = bpy.data.collections.new("Cabinets")
handle_collection = bpy.data.collections.new("Handles")
scene.collection.children.link(cabinet_collection)
scene.collection.children.link(handle_collection)


# ==========================================
# 2. HELPER FUNCTIONS & MATERIALS
# ==========================================

def hex_to_rgb(hex_str):
    hex_str = hex_str.lstrip('#')
    return tuple(int(hex_str[i:i + 2], 16) / 255.0 for i in (0, 2, 4)) + (1.0,)


def setup_cabinet_materials(obj, hex_color):
    mat = bpy.data.materials.new(name=f"Mat_{obj.name}")
    obj.data.materials.append(mat)

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    for node in nodes: nodes.remove(node)

    out_node = nodes.new('ShaderNodeOutputMaterial')

    base_node = nodes.new('ShaderNodeBsdfPrincipled')
    base_node.inputs['Base Color'].default_value = (0.8, 0.8, 0.8, 1.0)
    base_node.inputs['Roughness'].default_value = 0.3

    uv_node = nodes.new('ShaderNodeEmission')
    uv_map_node = nodes.new('ShaderNodeUVMap')
    links.new(uv_map_node.outputs['UV'], uv_node.inputs['Color'])

    id_node = nodes.new('ShaderNodeEmission')
    id_node.inputs['Color'].default_value = hex_to_rgb(hex_color)

    refl_node = nodes.new('ShaderNodeBsdfPrincipled')
    refl_node.inputs['Base Color'].default_value = (0.0, 0.0, 0.0, 1.0)
    refl_node.inputs['Roughness'].default_value = 0.1

    obj['mat_out'] = out_node.name
    obj['mat_base'] = base_node.name
    obj['mat_uv'] = uv_node.name
    obj['mat_id'] = id_node.name
    obj['mat_reflection'] = refl_node.name

    links.new(base_node.outputs[0], out_node.inputs[0])


def create_handle_material():
    mat = bpy.data.materials.new(name="Mat_Handle_Metal")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    # FIX: Changed to Dark Metal so it contrasts against the white cabinets
    bsdf.inputs['Base Color'].default_value = (0.1, 0.1, 0.1, 1.0)
    bsdf.inputs['Metallic'].default_value = 1.0
    bsdf.inputs['Roughness'].default_value = 0.3
    return mat


handle_metal_mat = create_handle_material()

# ==========================================
# 3. GEOMETRY GENERATION
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
    bpy.ops.object.transform_apply(scale=True)
    obj.location = (current_x + w / 2, -d / 2, h / 2)

    bpy.context.scene.collection.objects.unlink(obj)
    cabinet_collection.objects.link(obj)

    if cab['type'] == 'base':
        base_cabinets.append({'min_x': current_x, 'max_x': current_x + w, 'h': h, 'd': d})

    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.cube_project(cube_size=1.0)
    bpy.ops.object.mode_set(mode='OBJECT')

    setup_cabinet_materials(obj, cab['id_hex'])

    if cab.get('handle') == 'bar':
        bpy.ops.mesh.primitive_cube_add(size=1.0)
        handle = bpy.context.active_object
        handle.name = f"Handle_{i}"

        handle.scale = (0.15, 0.015, 0.015)
        bpy.ops.object.transform_apply(scale=True)

        z_pos = h * 0.8 if cab['type'] == 'base' else h * 0.5
        handle.location = (current_x + w / 2, -d - 0.0075, z_pos)

        handle.data.materials.append(handle_metal_mat)

        bpy.context.scene.collection.objects.unlink(handle)
        handle_collection.objects.link(handle)

    current_x += w

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
    bpy.ops.object.transform_apply(scale=True)
    ct.location = (min_x + w / 2, -(max_d + ct_overhang) / 2, max_h + h / 2)

    bpy.context.scene.collection.objects.unlink(ct)
    cabinet_collection.objects.link(ct)

    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.cube_project(cube_size=1.0)
    bpy.ops.object.mode_set(mode='OBJECT')

    setup_cabinet_materials(ct, ct_data['id_hex'])

# ==========================================
# 4. CAMERA & LIGHTING SETUP
# ==========================================

all_meshes = cabinet_collection.objects[:]
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
scene.collection.objects.link(cam_obj)
scene.camera = cam_obj

fov = cam_data.angle_x
distance = (total_width / 2.0) / math.tan(fov / 2.0)
distance *= 1.6

cam_obj.location = (center_x, center_y - distance, center_z + distance * 0.3)

empty_target = bpy.data.objects.new("CamTarget", None)
empty_target.location = (center_x, center_y, center_z)
scene.collection.objects.link(empty_target)

tt = cam_obj.constraints.new(type='TRACK_TO')
tt.target = empty_target
tt.track_axis = 'TRACK_NEGATIVE_Z'
tt.up_axis = 'UP_Y'

world = bpy.data.worlds.new("World")
scene.world = world
world.use_nodes = True
bg_node = world.node_tree.nodes.get("Background")
bg_node.inputs[0].default_value = (1.0, 1.0, 1.0, 1.0)

sun_data = bpy.data.lights.new("Sun", 'SUN')
sun_data.energy = 3.0
sun_data.angle = math.radians(5.0)
sun_obj = bpy.data.objects.new("Sun", sun_data)
scene.collection.objects.link(sun_obj)
sun_obj.rotation_euler = (math.radians(60), math.radians(0), math.radians(45))


# ==========================================
# 5. SEQUENTIAL RENDER PIPELINE
# ==========================================

def switch_cabinet_materials(pass_name):
    for obj in cabinet_collection.objects:
        if obj.data.materials:
            mat = obj.data.materials[0]
            nodes = mat.node_tree.nodes
            links = mat.node_tree.links
            out_node = nodes[obj['mat_out']]
            target_node = nodes[obj[f'mat_{pass_name}']]
            for link in out_node.inputs[0].links:
                links.remove(link)
            links.new(target_node.outputs[0], out_node.inputs[0])


def set_handles_visibility(visible):
    for obj in handle_collection.objects:
        obj.hide_render = not visible


def set_shadow_catchers(active):
    for obj in cabinet_collection.objects:
        obj.is_shadow_catcher = active


def set_world_light(active):
    """FIX: Toggles the sky light so reflections don't get washed out."""
    if active:
        bg_node.inputs[1].default_value = 0.5  # 50% strength
    else:
        bg_node.inputs[1].default_value = 0.0  # Pitch black


print("Rendering Base Pass...")
switch_cabinet_materials('base')
set_handles_visibility(False)
set_shadow_catchers(False)
set_world_light(True)
scene.render.film_transparent = False
scene.view_settings.view_transform = 'Standard'
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_depth = '8'
scene.render.image_settings.color_mode = 'RGB'
scene.render.filepath = os.path.join(OUTPUT_DIR, "base_pass.png")
bpy.ops.render.render(write_still=True)

print("Rendering UV Pass...")
switch_cabinet_materials('uv')
set_handles_visibility(False)
set_world_light(False)
scene.view_settings.view_transform = 'Raw'
scene.render.image_settings.file_format = 'OPEN_EXR'
scene.render.image_settings.color_depth = '32'
scene.render.filepath = os.path.join(OUTPUT_DIR, "uv_pass.exr")
bpy.ops.render.render(write_still=True)

print("Rendering ID Mask Pass...")
switch_cabinet_materials('id')
set_handles_visibility(False)
set_world_light(False)
scene.view_settings.view_transform = 'Raw'
scene.render.filter_size = 0.0
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_depth = '8'
scene.render.filepath = os.path.join(OUTPUT_DIR, "id_mask.png")
bpy.ops.render.render(write_still=True)

print("Rendering Reflection Pass...")
switch_cabinet_materials('reflection')
set_handles_visibility(False)
set_world_light(False)  # FIX: World is black, so we ONLY get Sun reflections!
scene.render.filter_size = 1.5
scene.view_settings.view_transform = 'Standard'
scene.render.film_transparent = True  # FIX: Transparent background
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_depth = '8'
scene.render.image_settings.color_mode = 'RGBA'
scene.render.filepath = os.path.join(OUTPUT_DIR, "reflection_pass.png")
bpy.ops.render.render(write_still=True)

print("Rendering Handle Pass (Shadow Catcher)...")
switch_cabinet_materials('base')
set_handles_visibility(True)
set_shadow_catchers(True)
set_world_light(True)  # Handles need light to look metallic
scene.render.film_transparent = True
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_depth = '8'
scene.render.image_settings.color_mode = 'RGBA'
scene.render.filepath = os.path.join(OUTPUT_DIR, "handle_pass.png")
bpy.ops.render.render(write_still=True)

print(f"Pipeline complete! 5 Assets saved to: {OUTPUT_DIR}")