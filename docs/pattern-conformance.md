# Pattern conformance — commercial-CAD patterns vs what's built

> Reader: owner judging how far the codebase implements the five
> commercial-system patterns identified in `docs/vision/01-user-journeys.md`
> | Enables: reading each pattern's real status from live ledger claims
> instead of remembered percentages | Update-trigger: a cited claim dies or
> a pattern's implementation status changes

Facts appear only as ledger ids (spec convention); the id is authoritative,
the hook text is courtesy. Verified 2026-07-12 against source.

| # | Pattern (source system) | Status | Evidence | Gap |
|---|---|---|---|---|
| 1 | Cabinet macros (PRO100) | Delegated to plugin | ADR-009 — hb5 owns parametric cabinets; adapter is the ACL | none (by design) |
| 2 | Construction Method (Polyboard) | Mostly built | tr-56212df8 — first-class registry entity; joinery is one flat string | no per-joint `JoinerySpec` |
| 3 | Sub-product hierarchy (Winner Flex) | Deliberately flatter | tr-0e4f1897 — zero bay/opening/splitter entities; ADR-001 panel-is-atom | intentional; revisit only if openings become first-class |
| 4 | Feature operations (TopSolid) | Mostly built | tr-eaeed5fe — MachiningOp + face/drill_type, cam appliers, runner/confirmat/groove from the legrabox AND corner-blind decomposers | no standalone drill-list export (DXF only) |
| 5 | Object-in-room (PaletteCAD) | Delegated to plugin | ADR-009 — placement/room stays in hb5 | none (by design) |
| 6 | Panel formula engine | Built, unwired | tr-fc74bc2e — `recipe.py` has no decomposer consumer; erp runs its own JSON recipes | wire decomposers or retire one engine |
| 7 | Material ≠ Construction | Clean | tr-9b296c35 — construction.py material-free; MaterialCatalog Protocol | none |
| 8 | Validation gates | Built 2026-07-16 | tr-65aa5969 — `buildability.evaluate_buildability` runs the scattered checks (premise tr-00421995) as ordered gates M1–M5 + FIT/WSTD/G1/G6, parked gates explicit skips | emission not gated on the verdict yet (wk-cb6a17c8); parked gates need model support |
| 9 | File structure | Flat, pragmatic | directly observable: `kuchnie_core/` flat modules + `export/`, `materials/` subpackages | none worth acting on |
| 10 | Plugin extension IO | Extraction only | tr-50c8f148 — no writer back into hb5 scenes | bidirectional IO is a scope decision (L1 Q10) |

Rows 6 and 10 are the actionable ones; 6 is engineering debt, 10 is the
Stage-2 investment fork already posed in the L1 questionnaire. Row 8
closed 2026-07-16 with the buildability gate runner (residual wiring:
wk-cb6a17c8).

## Re-running this review (the signature exercise)

The 2026-07-16 review that closed row 8 and found the antipattern set
(the import cycle — fixed 2026-07-17, tr-cad8d45a; the stringly gate
protocol — fixed 2026-07-17 by 872547f, finding superseded by
tr-cb1dec8a; tr-847d40f8 triple BOM fold) ran on a signature summary,
not full source. The review
lives at three regime layers:

1. **Findings are path-watched claims** — each antipattern claim watches
   its offending files, so the commit that fixes (or worsens) it stales
   the claim and the verdict queue re-opens exactly that question.
2. **Mechanical smells run at session close** —
   `scripts/session-gates.d/60-arch-smells.sh` (WARN-only) detects ten
   smell classes: import cycles (deferred included), cross-module
   `_underscore` imports, repeated deferred imports, dormant classes
   (≥3 methods, zero production references repo-wide), god classes
   (≥25 methods), duplicate module-level def names (ADR-006 dual-source
   risk), dimension parameters without a unit suffix (kuchnie_core only
   — unit ambiguity is scrap risk), param bloat (≥8 parameters;
   TYPE_CHECKING-guarded imports are exempt from cycle detection — they
   are the sanctioned idiom),
   SQLModel entities importing sibling services inside methods
   (active-record leak), layer rules (kuchnie_core never imports
   reflex/sqlmodel/sqlalchemy/kitchen_erp; kitchen_erp core/ never
   imports reflex or ui), and stringly-enum (distinctive enum values
   used as raw literals by modules that never reference the enum).
   Deliberate deferrals live in `docs/arch-smells-baseline.txt` (each
   annotated with its work item); the gate WARNs only on NEW findings
   and notes when baseline entries get fixed — regenerate with
   `--write-baseline` as part of the fixing commit.
   Vocabulary DRIFT has its own gate:
   `scripts/session-gates.d/62-vocab-drift.sh` warns when a new
   identifier-like literal starts being shared across ≥3 modules,
   against the committed `docs/shared-literals-baseline.txt`
   (regenerate deliberately with `scripts/shared-literals.py --write`).
3. **The judgment pass is TRIGGERED mechanically, performed by an
   architect.** `scripts/session-gates.d/61-signature-drift.sh` diffs
   the live surface (`scripts/signature-summary.py`, stdlib-ast,
   deterministic) against the committed baseline
   `docs/architecture-signatures.txt`. Drift → WARN naming the changed
   modules and demanding the review. The re-committed baseline is the
   RECEIPT that the review happened — same discipline as
   exercise-gate baselines. Run the review with:

```bash
find kuchnie-core/src kitchen-erp/kitchen_erp/ -type f -name "*.py" \
    ! -name "test*.py" | pysum --pipe
```

Feed the summary to an architect (human or agent) against the table
above; new findings become claims (layer 1) and, when grep-able,
detectors (layer 2). `pysum` is a user-local tool
(`~/.local/bin/pysum`) — the gate layer deliberately does not depend
on it.
