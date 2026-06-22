"""OBJ dimension validator — parses OBJ and checks against config.

Usage:
    python src/validate_obj.py output/meshes/i_shape.obj configs/i_shape.json
"""

import sys
import json
from pathlib import Path
from dataclasses import dataclass


@dataclass
class BBox:
    """Bounding box of an object."""
    name: str
    min_x: float
    max_x: float
    min_y: float
    max_y: float
    min_z: float
    max_z: float

    @property
    def width(self) -> float:
        return self.max_x - self.min_x

    @property
    def depth(self) -> float:
        return self.max_z - self.min_z

    @property
    def height(self) -> float:
        return self.max_y - self.min_y


def parse_obj(path: str) -> dict[str, BBox]:
    """Parse OBJ file, compute bounding box per object."""
    objects: dict[str, BBox] = {}
    current = None
    verts = []

    with open(path) as f:
        for line in f:
            line = line.strip()
            if line.startswith("o "):
                # Save previous object
                if current and verts:
                    objects[current] = _bbox(current, verts)
                current = line[2:]
                verts = []
            elif line.startswith("v "):
                parts = line.split()
                x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
                verts.append((x, y, z))

    # Save last object
    if current and verts:
        objects[current] = _bbox(current, verts)

    return objects


def _bbox(name: str, verts: list[tuple[float, float, float]]) -> BBox:
    """Compute bounding box from vertices."""
    xs = [v[0] for v in verts]
    ys = [v[1] for v in verts]
    zs = [v[2] for v in verts]
    return BBox(
        name=name,
        min_x=min(xs), max_x=max(xs),
        min_y=min(ys), max_y=max(ys),
        min_z=min(zs), max_z=max(zs),
    )


def validate(obj_path: str, config_path: str) -> list[str]:
    """Validate OBJ dimensions against config. Returns list of errors."""
    errors = []

    objects = parse_obj(obj_path)
    with open(config_path) as f:
        config = json.load(f)

    settings = config.get("settings", {})
    base_height = settings.get("baseBodyHeight", 720) / 1000
    base_depth = settings.get("baseDepth", 560) / 1000
    wall_height = settings.get("wallHeight", 720) / 1000
    wall_depth = settings.get("wallDepth", 300) / 1000
    plinth_height = settings.get("plinthHeight", 120) / 1000
    gap = settings.get("gap", 2) / 1000

    print(f"\n=== OBJ Validation: {obj_path} ===\n")
    print(f"Objects found: {len(objects)}")
    for name, bb in objects.items():
        print(f"  {name}: w={bb.width:.4f}m d={bb.depth:.4f}m h={bb.height:.4f}m "
              f"pos=({bb.min_x:.4f}, {bb.min_y:.4f}, {bb.min_z:.4f})")

    # Check each base cabinet
    print(f"\n--- Base cabinet checks ---")
    for run_idx, run in enumerate(config["runs"]):
        expected_x = 0.0
        for cab_idx, cab in enumerate(run.get("base", [])):
            cab_type = cab["type"]
            expected_w = cab["width"] / 1000

            # Find matching object in OBJ
            obj_name = f"run{run_idx}_base_{cab_idx}_{cab_type}"
            if obj_name not in objects:
                # Try filler with sequential numbering
                if cab_type == "filler":
                    # Find next available filler
                    for fi in range(20):
                        candidate = "filler" if fi == 0 else f"filler.{fi:03d}"
                        if candidate in objects:
                            bb_test = objects[candidate]
                            # Match by expected width
                            if abs(bb_test.width - expected_w) < 0.002:
                                obj_name = candidate
                                break

            if obj_name in objects:
                bb = objects[obj_name]
                tolerance = 0.002  # 2mm tolerance

                # Check width
                if abs(bb.width - expected_w) > tolerance:
                    errors.append(
                        f"{obj_name}: width {bb.width:.4f}m != expected {expected_w:.4f}m "
                        f"(diff: {abs(bb.width - expected_w)*1000:.1f}mm)"
                    )
                else:
                    print(f"  ✓ {obj_name} width: {bb.width:.4f}m")

                # Check height (skip for fillers)
                if cab_type != "filler":
                    if abs(bb.height - base_height) > tolerance:
                        errors.append(
                            f"{obj_name}: height {bb.height:.4f}m != expected {base_height:.4f}m "
                            f"(diff: {abs(bb.height - base_height)*1000:.1f}mm)"
                        )
                    else:
                        print(f"  ✓ {obj_name} height: {bb.height:.4f}m")

                # Check X position (skip for fillers)
                if cab_type != "filler":
                    if abs(bb.min_x - expected_x) > tolerance:
                        errors.append(
                            f"{obj_name}: x={bb.min_x:.4f}m != expected {expected_x:.4f}m "
                            f"(diff: {abs(bb.min_x - expected_x)*1000:.1f}mm)"
                        )
                    else:
                        print(f"  ✓ {obj_name} x-pos: {bb.min_x:.4f}m")

            else:
                errors.append(f"Object not found in OBJ: {obj_name}")

            expected_x += expected_w + gap

    # Check upper cabinets
    print(f"\n--- Upper cabinet checks ---")
    wall_mount = settings.get("wallMountHeight", 1400) / 1000
    for run_idx, run in enumerate(config["runs"]):
        expected_x = 0.0
        for cab_idx, cab in enumerate(run.get("upper", [])):
            cab_type = cab["type"]
            expected_w = cab["width"] / 1000

            obj_name = f"run{run_idx}_upper_{cab_idx}_{cab_type}"
            if obj_name not in objects and cab_type == "filler":
                for fi in range(20):
                    candidate = "filler" if fi == 0 else f"filler.{fi:03d}"
                    if candidate in objects:
                        bb_test = objects[candidate]
                        if abs(bb_test.width - expected_w) < 0.002:
                            obj_name = candidate
                            break

            if obj_name in objects:
                bb = objects[obj_name]
                tolerance = 0.002

                if abs(bb.width - expected_w) > tolerance:
                    errors.append(
                        f"{obj_name}: width {bb.width:.4f}m != expected {expected_w:.4f}m"
                    )
                else:
                    print(f"  ✓ {obj_name} width: {bb.width:.4f}m")

                # Check Z position (skip for fillers)
                if cab_type != "filler":
                    if abs(bb.min_y - wall_mount) > tolerance:
                        errors.append(
                            f"{obj_name}: z={bb.min_y:.4f}m != expected {wall_mount:.4f}m (wall mount)"
                        )
                    else:
                        print(f"  ✓ {obj_name} z-pos: {bb.min_y:.4f}m (wall mount)")

            expected_x += expected_w + gap

    # Check countertop
    print(f"\n--- Countertop checks ---")
    ct_objects = [n for n in objects if "countertop" in n.lower()]
    if ct_objects:
        bb = objects[ct_objects[0]]
        ct_z = settings.get("baseBodyHeight", 720) / 1000 + plinth_height
        tolerance = 0.005  # 5mm tolerance for countertop
        if abs(bb.min_y - ct_z) > tolerance:
            errors.append(
                f"Countertop: z={bb.min_y:.4f}m != expected {ct_z:.4f}m"
            )
        else:
            print(f"  ✓ Countertop z-pos: {bb.min_y:.4f}m")
        print(f"  Countertop size: {bb.width:.4f}m x {bb.depth:.4f}m x {bb.height:.4f}m")
    else:
        errors.append("No countertop found in OBJ")

    # Summary
    print(f"\n{'='*40}")
    if errors:
        print(f"ERRORS: {len(errors)}")
        for e in errors:
            print(f"  ✗ {e}")
    else:
        print("ALL CHECKS PASSED ✓")

    return errors


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python src/validate_obj.py <obj_path> <config_path>")
        sys.exit(1)

    errors = validate(sys.argv[1], sys.argv[2])
    sys.exit(1 if errors else 0)
