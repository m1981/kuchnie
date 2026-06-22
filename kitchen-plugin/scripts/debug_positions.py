"""Debug script to check actual Blender world positions."""
import bpy, sys
sys.path.insert(0, '.')
from src.config_parser import load_config
from src.geometry_builder import clear_scene, build_kitchen

config = load_config('configs/u_shape.json')
clear_scene()
objects = build_kitchen(config)

print()
print('=== BLENDER WORLD BOUNDING BOXES ===')
for obj in objects:
    if obj.type != 'MESH': continue
    bb = [obj.matrix_world @ v.co for v in obj.data.vertices]
    x0,x1 = min(v.x for v in bb), max(v.x for v in bb)
    y0,y1 = min(v.y for v in bb), max(v.y for v in bb)
    z0,z1 = min(v.z for v in bb), max(v.z for v in bb)
    print(f'{obj.name} X={x0:.3f}..{x1:.3f} Y={y0:.3f}..{y1:.3f} Z={z0:.3f}..{z1:.3f}')
