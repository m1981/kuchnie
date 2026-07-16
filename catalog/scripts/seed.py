"""CLI: Load YAML data into the SQLite catalog database.

Usage:
    python -m catalog.scripts.seed data/kronospan_sample.yaml
    python -m catalog.scripts.seed data/kronospan_full.yaml data/kronoswiss_full.yaml
    python -m catalog.scripts.seed --db /tmp/rebuild.db data/kronospan_full.yaml

--db targets a different database file (rebuild verification, scratch
environments) without touching the canonical catalog/db/catalog.db.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure catalog package is importable
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from catalog.db.engine import get_connection, init_schema
from catalog.scripts.importer import CatalogImporter, load_yaml

DB_PATH = Path(__file__).parent.parent / "db" / "catalog.db"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("yamls", nargs="+", help="YAML data files to import")
    parser.add_argument("--db", default=str(DB_PATH),
                        help="target database path (default: the canonical catalog.db)")
    args = parser.parse_args()

    db = get_connection(args.db)
    init_schema(db)
    importer = CatalogImporter(db)

    for yaml_path in args.yamls:
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
    print(f"\nDatabase: {args.db}")
    print(f"Total: {decors} decors, {variants} variants")

    db.close()


if __name__ == "__main__":
    main()
