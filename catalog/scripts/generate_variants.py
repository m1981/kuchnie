"""Generate chipboard variants for Global Collection decors missing variants.

Reads structure info from global-collection-decory.yaml and adds
chipboard 18mm variants to kronospan_full.yaml.
"""

from __future__ import annotations

from pathlib import Path

import yaml

DATA_DIR = Path(__file__).parent.parent / "data"
DOCS_DIR = Path(__file__).parent.parent / "docs" / "materials" / "Kronospan"


def main() -> None:
    # Load full decor list (has structure info)
    with open(DOCS_DIR / "global-collection-decory.yaml", encoding="utf-8") as f:
        full_data = yaml.safe_load(f)
    full_map = {str(d["dekor"]): d for d in full_data["dekory"]}

    # Load existing YAML
    yaml_path = DATA_DIR / "kronospan_full.yaml"
    with open(yaml_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    existing_variant_codes = {v["decor_code"] for v in data.get("variants", [])}
    existing_structures = set()

    # Check which structures exist in the YAML
    for s in data.get("structures", []):
        existing_structures.add(s["code"])

    added = 0
    missing_structures = set()

    for decor in data.get("decors", []):
        bid = decor["business_id"]
        if bid in existing_variant_codes:
            continue

        full_decor = full_map.get(bid)
        if not full_decor:
            continue

        struct_str = str(full_decor.get("struktura", ""))
        parts = [s.strip() for s in struct_str.split("/")]
        primary = parts[0]
        multi = ", ".join(parts[1:]) if len(parts) > 1 else None

        # Check if primary structure exists
        if primary not in existing_structures:
            missing_structures.add(primary)

        # Build variant
        variant = {
            "business_id": f"{bid}-CH-18-{primary}",
            "decor_code": bid,
            "material_slug": "kronospan-chipboard-global",
            "structure_code": primary,
            "thickness_mm": 18.0,
            "sheet_format_slug": "2800x2070",
            "roles": ["front", "carcass"],
            "hpl_available": True,
        }

        if multi:
            variant["multi_structures"] = multi

        # Express availability
        ex = []
        if full_decor.get("ex_12"):
            ex.append(12)
        if full_decor.get("ex_16"):
            ex.append(16)
        if full_decor.get("ex_18"):
            ex.append(18)
        if ex:
            variant["express"] = ex

        data.setdefault("variants", []).append(variant)
        existing_variant_codes.add(bid)
        added += 1
        print(f"  ✅ {bid:10s} → {variant['business_id']:20s}  struct={primary}  multi={multi or '-'}")

    # Save
    if added > 0:
        with open(yaml_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        print(f"\nSaved {yaml_path.name}")

    print(f"\nSummary:")
    print(f"  Variants added: {added}")
    print(f"  Total variants: {len(data.get('variants', []))}")
    if missing_structures:
        print(f"  ⚠️  Missing structures: {missing_structures}")


if __name__ == "__main__":
    main()
