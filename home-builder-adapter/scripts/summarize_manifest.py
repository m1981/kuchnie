#!/usr/bin/env python3
"""Manifest summarizer — human/LLM-friendly summary of geometry manifest.

Reads a kitchen geometry manifest and prints a structured summary
suitable for LLM agents or quick human inspection.

Usage:
    python scripts/summarize_manifest.py output/meshes/kitchen_manifest.json
"""

import json
import sys
from pathlib import Path


def summarize_manifest(manifest: dict) -> str:
    """Generate human-readable summary of manifest."""
    lines = []

    # Header
    layout = manifest.get("layout", {})
    lines.append(f"Kitchen: {layout.get('type', 'unknown')}")
    lines.append(f"Layout: {layout.get('run_count', 0)} runs, "
                 f"{layout.get('total_cabinets', 0)} cabinets")
    lines.append(f"Units: {manifest.get('units', 'unknown')}")
    lines.append("")

    # Runs
    lines.append("Runs:")
    for run in layout.get("runs", []):
        turn_str = f" (turn: {run['turn']})" if run.get("turn") else ""
        lines.append(
            f"  {run['index']}. {run['label']}: "
            f"{run['direction']}{turn_str} — "
            f"{run['total_width_mm']}mm, {run['cabinet_count']} cabinets"
        )
    lines.append("")

    # Objects summary
    objects = manifest.get("objects", [])
    primary = [o for o in objects if not o.get("parent")]

    lines.append(f"Objects: {len(objects)} total ({len(primary)} primary, "
                 f"{len(objects) - len(primary)} children)")
    lines.append("")

    # Group by classification
    by_class = {}
    for obj in objects:
        cls = obj.get("classification", "other")
        by_class.setdefault(cls, []).append(obj)

    lines.append("By type:")
    for cls, objs in sorted(by_class.items()):
        lines.append(f"  {cls}: {len(objs)}")
    lines.append("")

    # Dimensions table for primary objects
    lines.append("Primary objects:")
    lines.append(f"  {'Name':<40} {'W×D×H (mm)':<25} {'Status'}")
    lines.append(f"  {'─' * 40} {'─' * 25} {'─' * 10}")

    for obj in primary:
        name = obj.get("name", "unknown")
        dims = obj.get("local_dimensions_mm", [0, 0, 0])
        validation = obj.get("validation", {})
        issues = validation.get("issues", [])

        dim_str = f"{dims[0]:.0f}×{dims[1]:.0f}×{dims[2]:.0f}"

        if any(i.get("severity") == "error" for i in issues):
            status = "❌"
        elif any(i.get("severity") == "warning" for i in issues):
            status = "⚠️"
        else:
            status = "✓"

        # Truncate name if too long
        display_name = name if len(name) <= 40 else name[:37] + "..."
        lines.append(f"  {display_name:<40} {dim_str:<25} {status}")

    lines.append("")

    # Validation summary
    summary = manifest.get("validation_summary", {})
    lines.append(f"Validation: {summary.get('passed', 0)} passed, "
                 f"{summary.get('failed', 0)} failed, "
                 f"{summary.get('warnings', 0)} warnings")

    # Issues
    issues = summary.get("issues", [])
    if issues:
        lines.append("")
        lines.append(f"Issues ({len(issues)}):")
        for issue in issues:
            severity = issue.get("severity", "error")
            icon = "❌" if severity == "error" else "⚠️"
            lines.append(f"  {icon} {issue.get('object', '?')}: {issue.get('message', '')}")
    else:
        lines.append("")
        lines.append("✓ No issues found")

    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/summarize_manifest.py <manifest.json>")
        print("\nPrints a human/LLM-friendly summary of a geometry manifest.")
        sys.exit(1)

    manifest_path = sys.argv[1]

    if not Path(manifest_path).exists():
        print(f"Error: manifest file not found: {manifest_path}")
        sys.exit(1)

    with open(manifest_path) as f:
        manifest = json.load(f)

    print(summarize_manifest(manifest))


if __name__ == "__main__":
    main()
