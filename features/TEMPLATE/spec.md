# F0XX — <Feature Title>

> **HOW TO USE THIS TEMPLATE**
>
> 1. Copy the parent folder: `cp -r features/TEMPLATE features/F0XX-<slug>`
> 2. Replace `F0XX` and `<Feature Title>` everywhere.
> 3. Fill in every section. Empty sections = drift later.
> 4. If a section truly doesn't apply, write `N/A — <reason>` rather than deleting it.

---

## Job Story

> Format: *When I am [situation], I want to [motivation], so I can [outcome].*

**When** I am _______________,
**I want to** _______________,
**So I can** _______________.

> Why Job Story over User Story: it captures the outcome ("so I can") which prevents scope creep into UI artifacts.

---

## Bounded Context

- **Primary (the one that OWNS this):** `<Catalog | Core | CAD | Web | Render>`
- **Touched (consumers, must have explicit reason):**
  - `<context>`: _why it touches_
  - `<context>`: _why it touches_

> If `Touched` has more than 1 entry, run the Change Locality Test below. If it fails, split this into two features.

---

## Subdomain Classification

Pick one:

- [ ] **Core** — competitive advantage. Invest engineering time, write thorough tests.
- [ ] **Supporting** — necessary but commoditized. Use a framework, ship pragmatic.
- [ ] **Generic** — buy / use existing / skip.

**Reasoning:** _why this classification_

---

## Data Ownership

- **Canonical writes happen in:** `<context>` — `<file/class>`
- **Read-only consumers:**
  - `<context>` reads via `<projection / API / file>`

> Anti-pattern check: if two contexts write the same data, you have a shared-database-as-integration smell. Re-scope.

---

## Scope — MoSCoW

### Must (do not ship without)
- [ ] _Specific outcome 1_
- [ ] _Specific outcome 2_

### Should (do if time permits, defer to follow-up otherwise)
- [ ] _Specific outcome 1_

### Could (nice to have, almost certainly defer)
- [ ] _Specific outcome 1_

### Won't (this iteration — explicit cuts to prevent drift)
- _Thing that an LLM might propose but we are explicitly NOT doing here._
- _Thing that belongs in a future feature, named explicitly._

---

## Change Locality Test

> Solo dev's friend. If this test fails, the scope is wrong.

- [ ] Editing **one bounded context's** code only (or one + thin adapter).
- [ ] At most **one published contract change** (schema version bump, new field, new API endpoint).
- [ ] If both fail → **STOP**. Re-scope or split into two features.

---

## Glossary Impact

New terms introduced (must be added to `docs/GLOSSARY.md` in the implementation commit):

- `<NewTerm1>` — _short hint_
- `<NewTerm2>` — _short hint_

Existing terms refined or contradicted:

- `<ExistingTerm>` — _what changes_

> If you can't list any new or refined terms, this feature is probably not a real feature — it might be a bugfix or refactor.

---

## Acceptance Criteria

The feature is **done** when:

- [ ] Code committed to primary context.
- [ ] Tests in `tests/<context>/test_<feature>.py` covering Must items.
- [ ] `docs/GLOSSARY.md` updated with new terms.
- [ ] ADR written (see `adr.md`) if the decision is architectural.
- [ ] `docs/01_architecture.md` Context Map updated if relationships changed.
- [ ] Phase gate criteria in `docs/PHASES.md` checked off (if phase-completing).
- [ ] `status.md` set to `done`.
- [ ] `features/INDEX.md` updated.

---

## Out of Scope (anti-drift section)

Explicit list of things this feature does NOT do. Prevents the next LLM session from "helpfully" expanding scope.

- _Thing 1 — out of scope because [reason]_
- _Thing 2 — out of scope because [reason]_

---

## References

- **Pattern source:** `docs/02_pattern_analysis.md` § _section_
- **Placement decision:** `docs/03_implementation_placement.md` § _section_
- **Process rules:** `docs/04_solo_dev_process.md`
- **Related ADRs:** F0XX, F0XX
- **Related features:**
  - **Depends on:** F0XX (must be done first)
  - **Enables:** F0XX (will consume this feature's output)
  - **Conflicts with:** _none, or list_

---

## Open Questions

> Things the developer must answer before starting. Each becomes a decision (in ADR) or a scope cut.

- [ ] _Question 1_
- [ ] _Question 2_

> When all open questions have answers, this spec is "ready". Until then, do not start coding.
