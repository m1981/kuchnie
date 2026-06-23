# Documentation Guidelines

> **Purpose:** Rules for maintaining documentation structure and freshness.
> **Last updated:** 2026-06-23

---

## Three-Tier Hierarchy

Every piece of content has exactly one home. Never duplicate information across files.

| Tier                  | What lives here                          | Update frequency       | Location                            |
| --------------------- | ---------------------------------------- | ---------------------- | ----------------------------------- |
| **Tier 1: Code**      | Source, schemas, tests                   | Every feature          | `src/`, `tests/`                    |
| **Tier 2: Contracts** | Architecture, domain rules, format specs | When structure changes | `docs/`                             |
| **Tier 3: Plans**     | Roadmap, changelog, intent               | When priorities change | Root (`ROADMAP.md`, `CHANGELOG.md`) |

---

## Where Does Content Go?

| Content                  | Home   | File                      |
| ------------------------ | ------ | ------------------------- |
| Architecture diagrams    | Tier 2 | `docs/architecture.md`    |
| Domain specifications    | Tier 2 | `docs/<domain>-spec.md`   |
| API / format reference   | Tier 2 | `docs/config-syntax.md`   |
| Feature spec             | Tier 3 | `docs/specs/<feature>.md` |
| What we're building next | Tier 3 | `ROADMAP.md` (root)       |
| What changed             | Tier 3 | `CHANGELOG.md` (root)     |
| Quick-start / usage      | Tier 2 | `README.md`               |

---

## Anti-Staleness Rules

### Rule 1: Never put counts in docs

❌ **Wrong:**

```markdown
We have 277 tests passing across 20 test files.
```

✅ **Correct:**

```markdown
Run `make test` to verify all tests pass.
```

**Why:** Test counts change with every commit. Docs should describe behavior, not numbers.

### Rule 2: Never copy-paste between docs

❌ **Wrong:** Same table in 3 files.

✅ **Correct:**

```markdown
See [architecture.md](architecture.md) for layer definitions.
```

**Why:** If two files say the same thing, one is already stale.

### Rule 3: Docs describe stable things, plans describe volatile things

❌ **Wrong:** Roadmap items in `architecture.md`

✅ **Correct:** Roadmap items in `ROADMAP.md`

**Why:** Architecture changes rarely. Plans change often. Don't mix them.

### Rule 4: Root files get read first

| File           | Why root                               |
| -------------- | -------------------------------------- |
| `ROADMAP.md`   | GitHub renders it on repo landing page |
| `CHANGELOG.md` | Standard convention, tools expect it   |
| `README.md`    | Entry point for every reader           |

**Never bury these in `docs/`.**

---

## Doc Freshness Gate

Before marking a feature as done, verify:

- [ ] If architecture changed → `docs/architecture.md` updated
- [ ] If config format changed → `docs/config-syntax.md` + schema version bumped
- [ ] If feature completed → `ROADMAP.md` marked ✅
- [ ] If breaking change → `CHANGELOG.md` entry added
- [ ] No counts, no copy-paste, no stale references

---

## Current Documentation Structure

```
kitchen-cad/
├── README.md                          # Quick-start, usage examples
├── ROADMAP.md                         # What we're building next
├── CHANGELOG.md                       # What changed
│
└── docs/
    ├── architecture.md                # Authoritative architecture doc
    ├── DESIGN.md                      # Project design (references architecture.md)
    ├── LEGRABOX_SPEC.md               # LEGRABOX domain specification
    ├── poradnik-kompleksowy.md        # Comprehensive furniture guide
    ├── analiza_konfiguratora_formatek.md  # Panel configurator analysis
    ├── test-plan.md                   # Test strategy and cases
    ├── PROJECT_LOG.md                 # Project journal
    ├── DOCUMENTATION_GUIDELINES.md    # This file
    │
    ├── specs/
    │   └── 01-overview.md             # User context
    │
    └── sessions/
        └── SESSION_2026-06-17.md      # Session logs (optional)
```

---

## Maintenance Checklist

### Weekly

- [ ] Check for stale test counts in docs
- [ ] Verify ROADMAP.md reflects current priorities

### Per Feature

- [ ] Update architecture.md if structure changed
- [ ] Update ROADMAP.md to mark completed items
- [ ] Add CHANGELOG.md entry for breaking changes

### Monthly

- [ ] Review for copy-paste duplication
- [ ] Verify all links work
- [ ] Check that specs match implementation

---

## Common Mistakes

### ❌ Mistake 1: Putting session logs in docs/

**Problem:** Session logs are volatile and date-specific.

**Solution:** Move to `docs/sessions/` or keep in git history.

### ❌ Mistake 2: Duplicating specs across files

**Problem:** System 32 spec in README.md, DESIGN.md, and poradnik.md.

**Solution:** Single source of truth (e.g., `poradnik-kompleksowy.md`), reference elsewhere.

### ❌ Mistake 3: Embedding roadmap in design docs

**Problem:** DESIGN.md §10 contains roadmap.

**Solution:** Roadmap goes in `ROADMAP.md` at root. DESIGN.md references it.

### ❌ Mistake 4: Hardcoding test counts

**Problem:** "75 tests, 96% coverage" becomes stale immediately.

**Solution:** "Run `make test` to see current count."

---

## Adding New Documentation

1. **Determine the tier** (Code, Contracts, Plans)
2. **Check if content belongs in existing file** (avoid duplication)
3. **Place in correct location** (see hierarchy above)
4. **Add pointers** instead of copying content
5. **Remove counts** — use commands instead

---

## References

- [doc-structure skill](../../.pi/agent/skills/doc-structure/SKILL.md) — Documentation structure rules
- [CHANGELOG.md](../CHANGELOG.md) — Change history
- [ROADMAP.md](../ROADMAP.md) — Current priorities

---

_This document follows the anti-staleness rules it describes._
