"""Exporters — .blend save and wireframe render.

OBJ and glTF exports were removed (manifest-first pipeline replaced them).
"""

import bpy
from pathlib import Path


def export_blend(path: str) -> None:
    """Save scene as .blend file."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)

    bpy.ops.wm.save_as_mainfile(filepath=str(out))
    print(f"Saved .blend: {out}")


def render_wireframe(objects: list[bpy.types.Object], path: str,
                     resolution: tuple[int, int] = (1920, 1080)) -> None:
    """Render a wireframe screenshot of the scene."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)

    # Setup camera
    _setup_camera(objects)

    # Setup lighting
    _setup_light()

    # Set render settings
    scene = bpy.context.scene
    scene.render.resolution_x = resolution[0]
    scene.render.resolution_y = resolution[1]
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.filepath = str(out)
    scene.render.image_settings.file_format = 'PNG'

    # Enable wireframe overlay
    for obj in objects:
        if obj.type == 'MESH':
            obj.display_type = 'WIRE'

    bpy.ops.render.render(write_still=True)
    print(f"Rendered wireframe: {out}")


def _setup_camera(objects: list[bpy.types.Object]) -> None:
    """Create and position camera to frame all objects."""
    # Calculate bounds
    min_x = min_y = min_z = float('inf')
    max_x = max_y = max_z = float('-inf')

    for obj in objects:
        if obj.type != 'MESH':
            continue
        for v in obj.data.vertices:
            world_v = obj.matrix_world @ v.co
            min_x = min(min_x, world_v.x)
            max_x = max(max_x, world_v.x)
            min_y = min(min_y, world_v.y)
            max_y = max(max_y, world_v.y)
            min_z = min(min_z, world_v.z)
            max_z = max(max_z, world_v.z)

    if min_x == float('inf'):
        return

    # Center and size
    cx = (min_x + max_x) / 2
    cy = (min_y + max_y) / 2
    cz = (min_z + max_z) / 2
    size = max(max_x - min_x, max_z - min_z)

    # Camera position: front view, elevated
    cam_dist = size * 1.8
    cam = bpy.data.cameras.new("KitchenCam")
    cam.lens = 35
    cam_obj = bpy.data.objects.new("KitchenCam", cam)
    bpy.context.collection.objects.link(cam_obj)

    cam_obj.location = (cx, -cam_dist, cz + size * 0.3)
    cam_obj.rotation_euler = (1.2, 0, 0)  # looking down at ~30°

    bpy.context.scene.camera = cam_obj


def _setup_light() -> None:
    """Create basic lighting."""
    light = bpy.data.lights.new("KitchenLight", 'SUN')
    light.energy = 3.0
    light_obj = bpy.data.objects.new("KitchenLight", light)
    bpy.context.collection.objects.link(light_obj)
    light_obj.location = (0, -5, 10)
    light_obj.rotation_euler = (0.8, 0, 0.3)
