"""Material manager — creates Cycles materials for kitchen objects."""

import bpy


def create_materials(objects: list[bpy.types.Object], config: dict) -> None:
    """Create and apply materials to kitchen objects."""
    materials = config.get("materials", {})
    engine = bpy.context.scene.render.engine

    if engine not in ('CYCLES', 'BLENDER_EEVEE'):
        return

    # Create material library
    mat_lib = {}
    mat_lib["carcass"] = _create_material(
        "K_Carcass", materials.get("carcass", {}).get("color", [0.9, 0.9, 0.88])
    )
    mat_lib["front"] = _create_material(
        "K_Front", materials.get("front", {}).get("color", [0.85, 0.85, 0.82])
    )
    mat_lib["counter"] = _create_material(
        "K_Counter", materials.get("counter", {}).get("color", [0.72, 0.70, 0.68])
    )
    mat_lib["plinth"] = _create_material(
        "K_Plinth", materials.get("plinth", {}).get("color", [0.6, 0.6, 0.6])
    )
    mat_lib["filler"] = _create_material(
        "K_Filler", materials.get("filler", {}).get("color", [0.85, 0.85, 0.82])
    )

    # Apply materials based on object name
    for obj in objects:
        if obj.type != 'MESH':
            continue

        name = obj.name.lower()
        if "countertop" in name:
            obj.data.materials.append(mat_lib["counter"])
        elif "door" in name or "drawer" in name:
            obj.data.materials.append(mat_lib["front"])
        elif "filler" in name:
            obj.data.materials.append(mat_lib["filler"])
        else:
            obj.data.materials.append(mat_lib["carcass"])


def _create_material(name: str, color: list[float]) -> bpy.types.Material:
    """Create a simple diffuse material."""
    mat = bpy.data.materials.get(name)
    if mat:
        return mat

    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()

    # Diffuse BSDF
    node = nodes.new('ShaderNodeBsdfDiffuse')
    node.inputs['Color'].default_value = (*color[:3], 1.0)
    node.location = (0, 0)

    # Material output
    output = nodes.new('ShaderNodeOutputMaterial')
    output.location = (200, 0)

    mat.node_tree.links.new(node.outputs['BSDF'], output.inputs['Surface'])

    return mat
