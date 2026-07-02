> Type: A | Status: frozen 2026-07 (see /MIGRATION-STATUS.md) | Role: Domain hub — Kitchen, Panel, decomposition, BOM, standards, validator | ADRs: 001, 002, 003

# kuchnie-core

Kitchen cabinet decomposition engine. Takes YAML cabinet definitions,
produces physical panels with dimensions, edge banding, and machining
operations. Outputs: BOM, cut list CSV, intermediate JSON.

See [`/AGENTS.md`](../AGENTS.md) for architecture rules and file map.
