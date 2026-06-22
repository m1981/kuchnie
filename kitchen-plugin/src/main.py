"""Kitchen generator — CLI entry point.

Usage (from project root):
    blender --background --python src/main.py -- configs/test.json --export-obj --render-wireframe

Args after '--' are passed to this script:
    <config.json>           Kitchen config file (required)
    --export-obj            Export OBJ to output/meshes/
    --export-gltf           Export GLTF to output/meshes/
    --export-blend          Save .blend to output/meshes/
    --export-manifest       Export geometry manifest JSON for validation
    --render-wireframe      Render wireframe to output/renders/
    --no-materials          Skip material creation
"""

import sys
import os
from pathlib import Path

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import bpy

from src.config_parser import load_config
from src.geometry_builder import clear_scene, build_kitchen, apply_materials
from src.exporters import export_obj, export_gltf, export_blend, render_wireframe
from src.geometry_validator import validate_and_export_manifest, print_manifest_summary
from src.geometry_inspector import export_geometry_inspection, print_inspection_summary, analyze_geometry
from src.validators import validate_config, compute_total_width


def parse_args() -> dict:
    """Parse CLI arguments after '--' separator."""
    argv = sys.argv
    if "--" not in argv:
        print("Usage: blender --background --python src/main.py -- <config.json> [options]")
        print("Options: --export-obj --export-gltf --render-wireframe --no-materials")
        sys.exit(1)

    args = argv[argv.index("--") + 1:]
    if not args:
        print("Error: config file path required")
        sys.exit(1)

    config_path = args[0]
    return {
        "config_path": config_path,
        "export_obj": "--export-obj" in args,
        "export_gltf": "--export-gltf" in args,
        "export_blend": "--export-blend" in args,
        "export_manifest": "--export-manifest" in args,
        "export_inspect": "--export-inspect" in args,
        "render_wireframe": "--render-wireframe" in args,
        "no_materials": "--no-materials" in args,
    }


def main() -> None:
    """Main entry point."""
    args = parse_args()
    config_path = args["config_path"]

    # Resolve path
    if not os.path.isabs(config_path):
        config_path = str(PROJECT_ROOT / config_path)

    if not os.path.exists(config_path):
        print(f"Error: config file not found: {config_path}")
        sys.exit(1)

    # Load config
    print(f"Loading config: {config_path}")
    config = load_config(config_path)
    print(f"  Name: {config.get('name', 'unnamed')}")
    print(f"  Runs: {len(config['runs'])}")

    # Validate
    warnings = validate_config(config)
    if warnings:
        print(f"  Warnings ({len(warnings)}):")
        for w in warnings:
            print(f"    - {w}")
    else:
        print("  Validation: OK")

    # Print run widths
    widths = compute_total_width(config)
    for key, w in widths.items():
        print(f"  {key}: {w}mm")

    # Clear scene
    print("Clearing scene...")
    clear_scene()

    # Build geometry
    print("Building kitchen...")
    objects = build_kitchen(config)
    print(f"  Created {len(objects)} objects")

    # Apply materials
    if not args["no_materials"]:
        print("Applying materials...")
        apply_materials(objects, config)

    # Determine output path stem
    stem = Path(config_path).stem

    # Export geometry inspection (detailed vertex data)
    if args["export_inspect"]:
        inspect_path = str(PROJECT_ROOT / "output" / "meshes" / f"{stem}_inspect.json")
        print(f"Exporting geometry inspection: {inspect_path}")
        inspection = export_geometry_inspection(
            objects, inspect_path, settings=config.get("settings")
        )
        print_inspection_summary(inspection)
        issues = analyze_geometry(inspection)
        if issues:
            print(f"\n⚠️  Found {len(issues)} issues:")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print("\n✓ No geometry issues found")

    # Export geometry manifest (for validation)
    if args["export_manifest"]:
        manifest_path = str(PROJECT_ROOT / "output" / "meshes" / f"{stem}_manifest.json")
        print(f"Exporting geometry manifest: {manifest_path}")
        manifest = validate_and_export_manifest(
            objects, manifest_path, settings=config.get("settings")
        )
        print_manifest_summary(manifest)

    # Export OBJ
    if args["export_obj"]:
        obj_path = str(PROJECT_ROOT / "output" / "meshes" / f"{stem}.obj")
        print(f"Exporting OBJ: {obj_path}")
        export_obj(objects, obj_path)

    # Export GLTF
    if args["export_gltf"]:
        gltf_path = str(PROJECT_ROOT / "output" / "meshes" / f"{stem}.gltf")
        print(f"Exporting GLTF: {gltf_path}")
        export_gltf(objects, gltf_path)

    # Export .blend
    if args["export_blend"]:
        blend_path = str(PROJECT_ROOT / "output" / "meshes" / f"{stem}.blend")
        print(f"Saving .blend: {blend_path}")
        export_blend(blend_path)

    # Render wireframe
    if args["render_wireframe"]:
        png_path = str(PROJECT_ROOT / "output" / "renders" / f"{stem}.png")
        print(f"Rendering wireframe: {png_path}")
        render_wireframe(objects, png_path)

    print("Done.")


if __name__ == "__main__":
    main()
