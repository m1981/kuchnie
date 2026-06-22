#!/usr/bin/env python3
"""Compare Generated Cabinets with Reference Object.

Compares our generated cabinet geometry against the myster-box.obj reference
to validate dimensions and positioning.

Usage:
    python scripts/compare_with_reference.py configs/single_cabinet_test.json
"""

import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from analyze_reference_obj import parse_obj, analyze_object, detect_coordinate_system
from analyze_gltf_v2 import analyze_gltf


# Reference dimensions from myster-box.obj (in mm)
REFERENCE_DIMS = {
    "Cabinet1": {
        "width": 600,
        "depth": 590,
        "height": 700,
        "description": "Main cabinet body"
    },
    "Cabinet1_Door": {
        "width": 599,
        "depth": 18,
        "height": 698,
        "description": "Door panel"
    },
    "Handle": {
        "width": 8,
        "depth": 30,
        "height": 144,
        "description": "Handle"
    },
    "Baseboard1": {
        "width": 600,
        "depth": 18,
        "height": 160,
        "description": "Base panel"
    }
}

# Expected dimensions for our cabinet (in mm)
# Note: Object names in glTF may vary based on config
EXPECTED_DIMS = {
    "run0_base_0_base-door": {
        "width": 600,
        "depth": 560,
        "height": 720,
        "description": "Carcass (18mm walls)",
        "aliases": ["corpus", "cabinet_corpus"]
    },
    "run0_base_0_base-door_back": {
        "width": 564,
        "depth": 3,
        "height": 717,
        "description": "Back panel (3mm HDF)",
        "aliases": ["back_panel", "cabinet_back"]
    },
    "run0_base_0_base-door_door": {
        "width": 604,
        "depth": 19,
        "height": 724,
        "description": "Door with 2mm overlay",
        "aliases": ["door", "cabinet_door"]
    },
    "countertop": {
        "width": 660,
        "depth": 580,
        "height": 30,
        "description": "Countertop with overhangs",
        "aliases": []
    }
}


def load_gltf_dimensions(gltf_path: str) -> dict:
    """Load dimensions from a glTF file."""
    analysis = analyze_gltf(gltf_path)

    dimensions = {}
    for obj in analysis['objects']:
        name = obj['name']
        mesh = obj.get('mesh')

        if not mesh:
            continue

        for prim in mesh.get('primitives', []):
            bounds = prim.get('bounds')
            if bounds:
                dims = bounds['dimensions']
                dimensions[name] = {
                    "width": dims[0] * 1000,  # Convert to mm
                    "depth": dims[1] * 1000,
                    "height": dims[2] * 1000,
                    "position": obj.get('world_translation', (0, 0, 0))
                }

    return dimensions


def compare_dimensions(actual: dict, expected: dict, tolerance: float = 2.0) -> list:
    """Compare actual dimensions against expected.

    Args:
        actual: Actual dimensions dict
        expected: Expected dimensions dict
        tolerance: Allowed difference in mm

    Returns:
        List of comparison results
    """
    results = []

    for name, expected_dims in expected.items():
        if name not in actual:
            results.append({
                "name": name,
                "status": "MISSING",
                "message": f"Object '{name}' not found in generated geometry"
            })
            continue

        actual_dims = actual[name]
        issues = []

        for dim in ['width', 'depth', 'height']:
            exp_val = expected_dims[dim]
            act_val = actual_dims[dim]
            diff = abs(act_val - exp_val)

            if diff > tolerance:
                issues.append({
                    "dimension": dim,
                    "expected": exp_val,
                    "actual": act_val,
                    "difference": diff
                })

        if issues:
            results.append({
                "name": name,
                "status": "MISMATCH",
                "issues": issues,
                "description": expected_dims.get('description', '')
            })
        else:
            results.append({
                "name": name,
                "status": "OK",
                "description": expected_dims.get('description', ''),
                "dimensions": actual_dims
            })

    return results


def print_comparison_report(results: list, title: str) -> None:
    """Print comparison report."""
    print(f"\n{'=' * 80}")
    print(f"{title}")
    print(f"{'=' * 80}")

    ok_count = sum(1 for r in results if r['status'] == 'OK')
    mismatch_count = sum(1 for r in results if r['status'] == 'MISMATCH')
    missing_count = sum(1 for r in results if r['status'] == 'MISSING')

    print(f"\nSummary: {ok_count} OK, {mismatch_count} Mismatch, {missing_count} Missing")

    for result in results:
        name = result['name']
        status = result['status']

        if status == 'OK':
            print(f"\n✓ {name}")
            print(f"    {result.get('description', '')}")
            dims = result.get('dimensions', {})
            if dims:
                print(f"    Dims: {dims.get('width', 0):.1f} × {dims.get('depth', 0):.1f} × {dims.get('height', 0):.1f} mm")

        elif status == 'MISMATCH':
            print(f"\n❌ {name}")
            print(f"    {result.get('description', '')}")
            for issue in result.get('issues', []):
                dim = issue['dimension']
                exp = issue['expected']
                act = issue['actual']
                diff = issue['difference']
                print(f"    {dim}: expected {exp:.1f}mm, got {act:.1f}mm (diff: {diff:.1f}mm)")

        elif status == 'MISSING':
            print(f"\n⚠️  {name}")
            print(f"    {result.get('message', '')}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/compare_with_reference.py <config.json>")
        print("\nCompares generated cabinet geometry against reference dimensions.")
        sys.exit(1)

    config_path = sys.argv[1]
    if not Path(config_path).exists():
        print(f"Error: config file not found: {config_path}")
        sys.exit(1)

    # Find the generated glTF file
    stem = Path(config_path).stem
    gltf_path = Path(__file__).parent.parent / "output" / "meshes" / f"{stem}.gltf"

    if not gltf_path.exists():
        print(f"Error: glTF file not found: {gltf_path}")
        print(f"Please generate it first with:")
        print(f"  blender --background --python src/main.py -- {config_path} --export-gltf --no-materials")
        sys.exit(1)

    # Load generated dimensions
    print(f"Loading generated geometry from: {gltf_path}")
    generated_dims = load_gltf_dimensions(str(gltf_path))

    # Compare against expected dimensions
    results = compare_dimensions(generated_dims, EXPECTED_DIMS)

    # Print report
    print_comparison_report(results, f"COMPARISON: Generated vs Expected")

    # Also compare against reference object
    ref_path = Path(__file__).parent.parent / "output" / "meshes" / "myster-box.obj"
    if ref_path.exists():
        print(f"\n\n{'=' * 80}")
        print("REFERENCE OBJECT ANALYSIS")
        print(f"{'=' * 80}")

        ref_data = parse_obj(str(ref_path))
        coord_info = detect_coordinate_system(ref_data)

        print(f"\nReference: {ref_path.name}")
        print(f"Coordinate System: {coord_info['system']}")

        print(f"\nReference Dimensions:")
        for name, dims in REFERENCE_DIMS.items():
            print(f"  {name}: {dims['width']} × {dims['depth']} × {dims['height']} mm")

        # Compare our cabinet with reference cabinet
        print(f"\n{'=' * 80}")
        print("CABINET COMPARISON")
        print(f"{'=' * 80}")

        ref_cabinet = REFERENCE_DIMS.get("Cabinet1", {})
        # Find our cabinet in expected dims (could be "corpus" or "run0_base_0_base-door")
        our_cabinet = EXPECTED_DIMS.get("run0_base_0_base-door", EXPECTED_DIMS.get("corpus", {}))

        print(f"\nReference Cabinet1: {ref_cabinet.get('width', 0)} × {ref_cabinet.get('depth', 0)} × {ref_cabinet.get('height', 0)} mm")
        print(f"Our Corpus:         {our_cabinet.get('width', 0)} × {our_cabinet.get('depth', 0)} × {our_cabinet.get('height', 0)} mm")

        width_diff = abs(ref_cabinet.get('width', 0) - our_cabinet.get('width', 0))
        depth_diff = abs(ref_cabinet.get('depth', 0) - our_cabinet.get('depth', 0))
        height_diff = abs(ref_cabinet.get('height', 0) - our_cabinet.get('height', 0))

        print(f"\nDifferences:")
        print(f"  Width:  {width_diff:.1f}mm {'✓' if width_diff < 2 else '❌'}")
        print(f"  Depth:  {depth_diff:.1f}mm {'✓' if depth_diff < 2 else '❌'}")
        print(f"  Height: {height_diff:.1f}mm {'✓' if height_diff < 2 else '❌'}")


if __name__ == "__main__":
    main()
