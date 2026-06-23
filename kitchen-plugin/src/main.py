"""Kitchen generator — CLI entry point.

Usage (from project root):
    blender --background --python src/main.py -- configs/test.json --render-wireframe

Args after '--' are passed to this script:
    <config.json>           Kitchen config file (required)
    --export-blend          Save .blend to output/meshes/
    --validate              Run manifest validation after export
    --render-wireframe      Render wireframe to output/renders/
    --no-materials          Skip material creation
    --no-manifest           Skip manifest export (not recommended)

Primary output: JSON geometry manifest (always exported unless --no-manifest)
"""

import sys
import os
from pathlib import Path

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import bpy

from src.config_parser import load_config
from src.geometry_builder import clear_scene, build_kitchen_from_layout, apply_materials
from src.exporters import export_blend, render_wireframe
from src.geometry_manifest import export_manifest, print_manifest_summary
from src.manifest_validator import validate_manifest, print_validation_report
from src.validators import validate_config, compute_total_width
from src.wall_builder import build_domain_layout


def parse_args() -> dict:
    """Parse CLI arguments after '--' separator."""
    argv = sys.argv
    if "--" not in argv:
        print("Usage: blender --background --python src/main.py -- <config.json> [options]")
        print("Options: --export-blend --render-wireframe --no-materials --validate")
        sys.exit(1)

    args = argv[argv.index("--") + 1:]
    if not args:
        print("Error: config file path required")
        sys.exit(1)

    config_path = args[0]
    return {
        "config_path": config_path,
        "export_blend": "--export-blend" in args,
        "validate": "--validate" in args,
        "render_wireframe": "--render-wireframe" in args,
        "no_materials": "--no-materials" in args,
        "no_manifest": "--no-manifest" in args,
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

    # Build domain model (Kitchen Design context)
    print("\nBuilding domain layout...")
    domain_layout = build_domain_layout(config)
    print(f"  Walls: {len(domain_layout.room.walls)}")
    for wall in domain_layout.room.walls:
        print(f"    {wall.id}: {wall.length:.0f}mm")
    print(f"  Runs: {len(domain_layout.runs)}")
    for run in domain_layout.runs:
        print(f"    {run.label}: {run.direction.value}, "
              f"{len(run.cabinets)} cabinets")
    print(f"  Placements: {len(domain_layout.placed_cabinets)}")
    if domain_layout.corners:
        print(f"  Corners: {len(domain_layout.corners)}")

    # Clear scene
    print("Clearing scene...")
    clear_scene()

    # Build geometry from domain Layout
    print("Building kitchen...")
    objects = build_kitchen_from_layout(domain_layout, config["settings"])
    print(f"  Created {len(objects)} objects")

    # Apply materials
    if not args["no_materials"]:
        print("Applying materials...")
        apply_materials(objects, config)

    # Determine output path stem
    stem = Path(config_path).stem

    # Export geometry manifest (PRIMARY output — always unless --no-manifest)
    if not args["no_manifest"]:
        manifest_path = str(PROJECT_ROOT / "output" / "meshes" / f"{stem}_manifest.json")
        print(f"Exporting geometry manifest: {manifest_path}")
        manifest = export_manifest(
            objects, manifest_path,
            settings=config.get("settings"),
            config={**config, "_source_path": config_path},
            layout=domain_layout,
        )
        print_manifest_summary(manifest)

        # Run validation if requested
        if args["validate"]:
            print("\nRunning manifest validation...")
            result = validate_manifest(manifest)
            print_validation_report(result)
            if not result.is_valid:
                print(f"\n❌ Validation failed with {result.failed} errors")
            else:
                print("\n✓ Validation passed")

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
