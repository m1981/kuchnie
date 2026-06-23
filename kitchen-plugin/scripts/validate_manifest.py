#!/usr/bin/env python3
"""Standalone manifest validator — no Blender dependency.

Validates a kitchen geometry manifest against:
- Schema structure (if jsonschema available)
- Dimension tolerance checks
- Object overlap detection
- Standard width compliance
- Run direction continuity
- Construction parameter sanity

Usage:
    python scripts/validate_manifest.py output/meshes/kitchen_manifest.json
    python scripts/validate_manifest.py output/meshes/kitchen_manifest.json --strict
"""

import json
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from manifest_validator import validate_manifest, print_validation_report


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/validate_manifest.py <manifest.json> [--strict]")
        print("\nValidates a kitchen geometry manifest against construction rules.")
        sys.exit(1)

    manifest_path = sys.argv[1]
    strict = "--strict" in sys.argv

    if not Path(manifest_path).exists():
        print(f"Error: manifest file not found: {manifest_path}")
        sys.exit(1)

    # Load manifest
    print(f"Loading manifest: {manifest_path}")
    with open(manifest_path) as f:
        manifest = json.load(f)

    # Basic structure check
    required_fields = [
        "format", "version", "units", "coordinate_system",
        "settings", "layout", "objects", "validation_summary",
    ]
    missing = [f for f in required_fields if f not in manifest]
    if missing:
        print(f"Error: manifest missing required fields: {missing}")
        print(f"  Format: {manifest.get('format', 'unknown')}")
        print(f"  Version: {manifest.get('version', 'unknown')}")
        sys.exit(1)

    # Validate
    print(f"Format: {manifest['format']} v{manifest['version']}")
    print(f"Units: {manifest['units']}")
    print(f"Objects: {len(manifest['objects'])}")

    result = validate_manifest(manifest)

    # Print report
    print_validation_report(result)

    # Try schema validation if jsonschema available
    schema_path = PROJECT_ROOT / "schemas" / "manifest_v2.schema.json"
    if schema_path.exists():
        try:
            import jsonschema
            schema = json.loads(schema_path.read_text())
            jsonschema.validate(manifest, schema)
            print("\n✓ Schema validation passed")
        except jsonschema.ValidationError as e:
            print(f"\n❌ Schema validation failed: {e.message}")
            if strict:
                sys.exit(1)
        except ImportError:
            print("\n⚠️  jsonschema not installed — skipping schema validation")
            print("   Install with: pip install jsonschema")

    # Exit code
    if not result.is_valid:
        print(f"\n❌ Validation failed with {result.failed} errors")
        sys.exit(1)
    else:
        print(f"\n✓ Validation passed ({result.passed} objects, {result.warnings} warnings)")
        sys.exit(0)


if __name__ == "__main__":
    main()
