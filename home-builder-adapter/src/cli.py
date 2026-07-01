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


def main() -> None:
    """Extract kitchen from current Blender scene and print JSON."""
    from .extract import extract_cabinets_from_scene, cabinets_to_kitchen
    from kuchnie_core.serialize import kitchen_to_dict

    cabinets = extract_cabinets_from_scene()

    if not cabinets:
        print("No cabinets found in scene.", file=sys.stderr)
        sys.exit(1)

    kitchen = cabinets_to_kitchen(cabinets)
    data = kitchen_to_dict(kitchen)
    print(json.dumps(data, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
