"""CLI: Load YAML data into the SQLite catalog database.

Usage:
    python -m catalog.scripts.seed data/kronospan_sample.yaml
    python -m catalog.scripts.seed data/kronospan_full.yaml data/kronoswiss_full.yaml
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure catalog package is importable
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from catalog.db.engine import get_connection, init_schema
from catalog.scripts.importer import CatalogImporter, load_yaml

DB_PATH = Path(__file__).parent.parent / "db" / "catalog.db"


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python -m catalog.scripts.seed <yaml_file> [yaml_file2 ...]")
        sys.exit(1)

    db = get_connection(str(DB_PATH))
    init_schema(db)
    importer = CatalogImporter(db)

    for yaml_path in sys.argv[1:]:
        path = Path(yaml_path)
        if not path.exists():
            print(f"ERROR: File not found: {path}")
            sys.exit(1)
        print(f"Importing {path.name}...")
        data = load_yaml(path)
        stats = importer.import_all(data)
        print(f"  → {stats}")

    # Final counts
    decors = db.execute("SELECT COUNT(*) FROM decors").fetchone()[0]
    variants = db.execute("SELECT COUNT(*) FROM variants").fetchone()[0]
    print(f"\nDatabase: {DB_PATH}")
    print(f"Total: {decors} decors, {variants} variants")

    db.close()


if __name__ == "__main__":
    main()
