> Archived 2026-07-09 — every step referenced docs/archive/rendering-improvements.md, itself already archived; active work is tracked in the truth ledger (scripts/truth ready).

# Roadmap

## Rendering Quality (Remaining)

- [ ] **HDRI Environment for Reflections** — Replace black world background with a studio HDRI or procedural gradient so glossy surfaces show meaningful reflections. ([details](docs/rendering-improvements.md#step-15--hdri-environment-for-reflections))
- [ ] **Base Pass Contrast Enhancement** — Apply gamma/contrast curve to base pass before multiplying textures, deepening AO shadows. ([details](docs/rendering-improvements.md#step-21--base-pass-contrast-enhancement))
- [ ] **Synthetic Edge AO** — Generate artificial contact shadows along cabinet gaps using edge detection on the ID mask. ([details](docs/rendering-improvements.md#step-22--synthetic-edge-ao))

## Production Scaling

- [ ] **RAM Asset Caching** — Load 4K `base_pass.png` and `uv_pass.exr` into a global dict at boot. Expected: ~30–50ms response times.
- [ ] **Database Integration** — Replace `catalog_db.py` with PostgreSQL (SQLAlchemy). Build an admin panel for managing Krono SKUs.
- [ ] **Cloud Storage** — Move `assets/` to S3/R2, stream into OpenCV via `boto3`.
