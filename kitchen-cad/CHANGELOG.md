# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added

- Documentation restructuring (2026-06-23)
    - Created ROADMAP.md at root
    - Created CHANGELOG.md at root
    - Consolidated architecture documentation
    - Removed stale test counts from docs

### Changed

- `corpus_type` field changed from `str` to `CorpusType` enum (backward-compatible — Pydantic coerces strings)
- `drill_engine.apply_*` functions are now **pure** — return new panel lists, originals are never mutated
- Shared `SYSTEM32_OFFSET` / `SYSTEM32_SPACING` constants extracted to `models.py`

### Fixed

- Magic number `37` in `panel_calculator._shelf_panels()` replaced with shared `SYSTEM32_OFFSET` constant
- Mutation/return ambiguity in `drill_engine` — functions now deep-copy before modifying

---

## [0.2.0] — 2026-06-23

### Added

- Validator module — geometry checks for drill points (out of bounds, depth, overlaps)
- Mirror functionality — X/Y reflection for drill points and edges
- Grooving module — back panel groove calculation
- Edge drilling — holes in panel edges (side drilling)
- Flip-up fronts support — AVENTOS-style hinges
- Handle configuration — multiple handle types (relingowe, gałka)
- Hinge configuration — multiple hinge specs
- Materials catalog — material validation
- Test suite expanded to 277 tests

### Changed

- Test structure reorganized into unit/, integration/, e2e/

---

## [0.1.0] — 2026-06-17

### Added

- Initial release — Phase 1 Core Engine
- Pydantic models (CorpusSpec, Panel, DrillPoint, HingeSpec, HandleSpec)
- Panel calculator (base, drawer, wall, 2-door cabinet types)
- System 32 drill engine — shelf pin positions
- Blum CLIP 35mm drill engine — hinge cup drilling
- Handle drilling — relingowe handles
- CSV cutting list generator
- CSV edge banding generator
- Comparison tools (CSV + DXF validation)
- Shelf pin drilling from Corpus .cmk reference
- Example generator script
- LEGRABOX technical specification documentation
- Comprehensive design documentation (DESIGN.md)
- Test plan documentation

### Technical

- Python 3.12 + Pydantic v2
- ezdxf for DXF generation
- pytest for testing
- TDD approach from start

---

## Types of Changes

- **Added** for new features
- **Changed** for changes in existing functionality
- **Deprecated** for soon-to-be removed features
- **Removed** for now removed features
- **Fixed** for any bug fixes
- **Security** in case of vulnerabilities

---

_See [ROADMAP.md](ROADMAP.md) for planned features._
