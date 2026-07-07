"""CLI entry point for home-builder-adapter.

Usage:
    # Inside Blender's Python:
    blender --background scene.blend --python -m home_builder_adapter.cli

    # Or as a standalone script (requires bpy installed):
    python -m home_builder_adapter.cli path/to/scene.blend

Outputs kuchnie_core.Kitchen JSON to stdout.
"""

from __future__ import annotations

import json
import sys


def main(argv: list[str] | None = None) -> None:
    """Extract kitchen from a .blend file (or the current scene) and print JSON.

    A ``.blend`` path in the args is opened first; without one, whatever
    scene the interpreter already holds is used. Inside Blender, script
    args arrive after the ``--`` separator — everything before it belongs
    to Blender itself and is ignored here.
    """
    from .extract import extract_cabinets_from_scene, cabinets_to_kitchen
    from kuchnie_core.serialize import kitchen_to_dict

    args = list(sys.argv[1:] if argv is None else argv)
    if "--" in args:
        args = args[args.index("--") + 1:]
    blend_path = next((a for a in args if a.endswith(".blend")), None)

    if blend_path is not None:
        import bpy
        bpy.ops.wm.open_mainfile(filepath=blend_path)

    cabinets = extract_cabinets_from_scene()

    if not cabinets:
        print("No cabinets found in scene.", file=sys.stderr)
        sys.exit(1)

    kitchen = cabinets_to_kitchen(cabinets)
    data = kitchen_to_dict(kitchen)
    print(json.dumps(data, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
