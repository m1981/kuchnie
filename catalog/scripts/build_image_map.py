"""Build image mapping: match decor business_ids to filesystem image filenames.

Uses deterministic rules (not filesystem scanning):
  1. Exact match:      K8685 → K8685.jpg
  2. Zero-padded:      K110  → K0110.jpg  (K + 4-digit)
  3. Prefix match:     0190  → K0190.jpg  (add K prefix)
  4. Prefix + padded:  190   → K0190.jpg  (add K + zero-pad)
  5. Numeric scan:     K091  → K0091.jpg  (match digits 091 == 0091)

Usage:
    python scripts/build_image_map.py                    # dry-run, print mapping
    python scripts/build_image_map.py --apply            # update YAML files
    python scripts/build_image_map.py --strict           # fail if any decor has no image
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

# Paths relative to catalog/
DATA_DIR = Path(__file__).parent.parent / "data"
PUBLIC_DIR = Path(__file__).parent.parent / "public" / "producers"

# Image directories per producer
IMG_DIRS = {
    "kronospan": PUBLIC_DIR / "kronospan" / "decors",
    "swiss_krono": PUBLIC_DIR / "swiss_krono" / "decors",
    "egger": PUBLIC_DIR / "egger" / "decors",
}

EXTENSIONS = (".jpg", ".png", ".webp")


def _extract_digits(s: str) -> str:
    """Extract digits from a string: 'K091' → '091', '868S' → '868'."""
    return "".join(c for c in s if c.isdigit())


def _find_image(business_id: str, img_dir: Path) -> str | None:
    """Try to find an image file for a decor business_id.

    Returns filename (e.g. 'K0110.jpg') or None.
    """
    if not img_dir.exists():
        return None

    bid = business_id.strip()
    if not bid:
        return None

    # Rule 1: Exact match
    for ext in EXTENSIONS:
        if (img_dir / f"{bid}{ext}").exists():
            return f"{bid}{ext}"

    # Rule 2: Zero-padded (K110 → K0110)
    if bid[0].isalpha() and bid[1:].isdigit():
        letter = bid[0]
        num = int(bid[1:])
        for width in (5, 4, 3):
            padded = f"{letter}{num:0{width}d}"
            for ext in EXTENSIONS:
                if (img_dir / f"{padded}{ext}").exists():
                    return f"{padded}{ext}"

    # Rule 3: Prefix match (0190 → K0190)
    if bid[0].isdigit():
        for prefix in ("K", "D", "U"):
            for ext in EXTENSIONS:
                candidate = f"{prefix}{bid}{ext}"
                if (img_dir / candidate).exists():
                    return candidate
            # Rule 4: Prefix + padded (190 → K0190)
            if bid.isdigit():
                num = int(bid)
                for width in (5, 4, 3):
                    padded = f"{prefix}{num:0{width}d}"
                    for ext in EXTENSIONS:
                        if (img_dir / f"{padded}{ext}").exists():
                            return f"{padded}{ext}"

    # Rule 5: Numeric scan (match digits)
    bid_digits = _extract_digits(bid)
    if bid_digits:
        for f in sorted(img_dir.iterdir()):
            if not f.is_file() or f.suffix.lower() not in EXTENSIONS:
                continue
            file_digits = _extract_digits(f.stem)
            if file_digits and bid_digits == file_digits:
                return f.name

    return None


def _load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def _save_yaml(path: Path, data: dict) -> None:
    with path.open("w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def build_mapping(yaml_path: Path) -> dict[str, str | None]:
    """Build business_id → image_filename mapping for one YAML file.

    Returns dict: {'K8685': 'K8685.jpg', 'K091': 'K0091.jpg', '868S': None}
    """
    data = _load_yaml(yaml_path)
    producer_slug = data["producers"][0]["slug"]
    img_dir = IMG_DIRS.get(producer_slug)
    if not img_dir:
        print(f"WARNING: No image dir for producer '{producer_slug}'")
        return {}

    mapping = {}
    for decor in data.get("decors", []):
        bid = decor["business_id"]
        img = _find_image(bid, img_dir)
        mapping[bid] = img

    return mapping


def apply_mapping(yaml_path: Path, mapping: dict[str, str | None]) -> int:
    """Update YAML file with img fields. Returns count of changes."""
    data = _load_yaml(yaml_path)
    changes = 0

    for decor in data.get("decors", []):
        bid = decor["business_id"]
        img = mapping.get(bid)
        current = decor.get("img")
        if img and current != img:
            decor["img"] = img
            changes += 1
        elif not img and current:
            # Image was set but file doesn't exist — keep it (data > guess)
            pass

    if changes > 0:
        _save_yaml(yaml_path, data)

    return changes


def main() -> None:
    parser = argparse.ArgumentParser(description="Build image mapping for decor business_ids")
    parser.add_argument("--apply", action="store_true", help="Update YAML files with img fields")
    parser.add_argument("--strict", action="store_true", help="Exit 1 if any decor has no image")
    args = parser.parse_args()

    yaml_files = sorted(DATA_DIR.glob("*_full.yaml"))
    if not yaml_files:
        print("ERROR: No *_full.yaml files found in data/")
        sys.exit(1)

    total_matched = 0
    total_unmatched = 0
    all_unmatched: list[tuple[str, str]] = []

    for yaml_path in yaml_files:
        print(f"\n{'='*60}")
        print(f"File: {yaml_path.name}")
        print(f"{'='*60}")

        mapping = build_mapping(yaml_path)
        matched = sum(1 for v in mapping.values() if v)
        unmatched = [(bid, yaml_path.name) for bid, v in mapping.items() if not v]

        total_matched += matched
        total_unmatched += len(unmatched)
        all_unmatched.extend(unmatched)

        print(f"Matched: {matched}/{len(mapping)}")

        # Show matches
        for bid, img in sorted(mapping.items()):
            if img:
                print(f"  ✅ {bid:10s} → {img}")

        # Show unmatched
        if unmatched:
            print(f"\n  ❌ No image ({len(unmatched)}):")
            for bid, _ in unmatched:
                print(f"     {bid}")

        # Apply if requested
        if args.apply:
            changes = apply_mapping(yaml_path, mapping)
            if changes:
                print(f"\n  📝 Updated {changes} decors in {yaml_path.name}")

    # Summary
    print(f"\n{'='*60}")
    print(f"TOTAL: {total_matched} matched, {total_unmatched} unmatched")
    print(f"{'='*60}")

    if all_unmatched:
        print(f"\nAll unmatched decors:")
        for bid, src in all_unmatched:
            print(f"  {bid:10s} ({src})")

    if args.strict and total_unmatched > 0:
        print(f"\nFAILED: {total_unmatched} decors have no image")
        sys.exit(1)


if __name__ == "__main__":
    main()
