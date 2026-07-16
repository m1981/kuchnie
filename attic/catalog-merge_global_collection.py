# TOMBSTONE (2026-07-16): atticized by owner dark-triage decision. One-shot
# generator/migration whose output is already committed (catalog/data/*.yaml,
# schema 1.5.0). The living data pipeline is documented in
# docs/specs/catalog-service.md; rebuild = catalog.scripts.seed + seed_* extras.
"""Merge Global Collection decors into kronospan_full.yaml.

Reads the full 174-decor list from global-collection-decory.yaml,
matches images from public/producers/kronospan/decors/, and adds
missing decors to kronospan_full.yaml with img fields.
"""

from __future__ import annotations

from pathlib import Path

import yaml

DATA_DIR = Path(__file__).parent.parent / "data"
DOCS_DIR = Path(__file__).parent.parent / "docs" / "materials" / "Kronospan"
IMG_DIR = Path(__file__).parent.parent / "public" / "producers" / "kronospan" / "decors"

EXTENSIONS = (".jpg", ".png", ".webp")


def _find_image(business_id: str) -> str | None:
    """Find image file for a decor business_id."""
    bid = business_id.strip()
    if not bid:
        return None

    # Exact match
    for ext in EXTENSIONS:
        if (IMG_DIR / f"{bid}{ext}").exists():
            return f"{bid}{ext}"

    # Zero-padded (K110 → K0110)
    if bid[0].isalpha() and bid[1:].isdigit():
        letter = bid[0]
        num = int(bid[1:])
        for width in (5, 4, 3):
            padded = f"{letter}{num:0{width}d}"
            for ext in EXTENSIONS:
                if (IMG_DIR / f"{padded}{ext}").exists():
                    return f"{padded}{ext}"

    # Prefix match (0190 → K0190)
    if bid[0].isdigit():
        for prefix in ("K", "D", "U"):
            for ext in EXTENSIONS:
                if (IMG_DIR / f"{prefix}{bid}{ext}").exists():
                    return f"{prefix}{bid}{ext}"

    return None


def _group_to_color_family(group: str) -> str | None:
    """Map group name to color_family slug."""
    group_lower = group.lower()
    if "white" in group_lower:
        return "bialy"
    if "color" in group_lower and ("basic" in group_lower or "special" in group_lower):
        return "szary"  # generic, override per-decor
    if "wood" in group_lower:
        return "dab"
    if "contempo" in group_lower:
        return "szary"
    if "harmony" in group_lower:
        return "szary"
    return None


# Color family overrides based on decor name keywords
_COLOR_KEYWORDS = {
    "biał": "bialy", "white": "bialy", "alpejsk": "bialy",
    "czarn": "czarny", "black": "czarny",
    "szar": "szary", "gray": "szary", "grey": "szary", "grafit": "szary",
    "dąb": "dab", "oak": "dab", "dab ": "dab",
    "orzech": "orzech", "walnut": "orzech",
    "jesion": "jesion", "ash": "jesion",
    "buk": "buk", "beech": "buk",
    "brąz": "brazowy", "brown": "brazowy",
    "beż": "bezowy", "beige": "bezowy", "krem": "kremowy",
    "marmur": "marmur", "marble": "marmur",
    "beton": "beton", "concrete": "beton",
    "łupek": "lupek", "slate": "lupek",
    "kamień": "lupek", "stone": "lupek",
    "niebies": "niebieski", "blue": "niebieski",
    "ziel": "zielony", "green": "zielony",
    "czerwon": "czerwony", "red": "czerwony",
    "złot": "zloty", "gold": "zloty",
    "srebrn": "srebrny", "silver": "srebrny",
}


def _infer_color_family(name: str, group: str) -> str | None:
    """Infer color_family from decor name."""
    name_lower = name.lower()
    for keyword, family in _COLOR_KEYWORDS.items():
        if keyword in name_lower:
            return family
    return _group_to_color_family(group)


def main() -> None:
    # Load full decor list
    with open(DOCS_DIR / "global-collection-decory.yaml", encoding="utf-8") as f:
        full_data = yaml.safe_load(f)
    full_decors = full_data["dekory"]

    # Load existing YAML
    yaml_path = DATA_DIR / "kronospan_full.yaml"
    with open(yaml_path, encoding="utf-8") as f:
        existing_data = yaml.safe_load(f)

    existing_ids = {d["business_id"] for d in existing_data.get("decors", [])}
    print(f"Existing decors in YAML: {len(existing_ids)}")

    # Find decors to add (have images, not in YAML)
    added = 0
    skipped_no_img = 0
    skipped_exists = 0

    for decor in full_decors:
        bid = str(decor["dekor"])

        if bid in existing_ids:
            skipped_exists += 1
            continue

        img = _find_image(bid)
        if not img:
            skipped_no_img += 1
            continue

        # Build new decor entry
        name = decor["nazwa"]
        group = decor.get("grupa", "")
        # Extract group name without number prefix
        group_name = group.split(" ", 1)[1] if " " in group else group

        new_decor = {
            "business_id": bid,
            "name": name,
            "group_name": group_name,
            "producer_slug": "kronospan",
            "img": img,
        }

        # Add name_en if available
        if "nazwa_en" in decor:
            new_decor["name_en"] = decor["nazwa_en"]

        # Add color_family
        color = _infer_color_family(name, group)
        if color:
            new_decor["color_family_slug"] = color

        # Add reference colors from uwagi
        uwagi = decor.get("uwagi", "")
        if "NCS" in uwagi:
            for part in uwagi.split(","):
                part = part.strip()
                if part.startswith("NCS"):
                    new_decor["ncs"] = part.replace("NCS ", "").strip()
                elif part.startswith("RAL"):
                    new_decor["ral"] = part.replace("RAL ", "").strip()
                elif part.startswith("Pantone"):
                    pass  # skip for now

        existing_data.setdefault("decors", []).append(new_decor)
        existing_ids.add(bid)
        added += 1
        print(f"  ✅ Added {bid:10s} {name:30s} → {img}")

    # Save
    if added > 0:
        with open(yaml_path, "w", encoding="utf-8") as f:
            yaml.dump(existing_data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        print(f"\nSaved {yaml_path.name}")

    print(f"\nSummary:")
    print(f"  Added:          {added}")
    print(f"  Already exists: {skipped_exists}")
    print(f"  No image:       {skipped_no_img}")
    print(f"  Total in YAML:  {len(existing_ids)}")


if __name__ == "__main__":
    main()
