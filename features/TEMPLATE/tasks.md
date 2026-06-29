# F0XX Tasks

> **One file per feature. One source of truth for "what's left."**
>
> Agents: when asked to implement F0XX, pick the next unchecked box in **Implementation**, not "Should" or "Could".

---

## Pre-flight (do before any code)

- [ ] `spec.md` Open Questions all answered.
- [ ] `adr.md` written and `Accepted` (if needed) OR documented as "no ADR needed because: _reason_".
- [ ] Primary bounded context identified (matches `spec.md`).
- [ ] New terms identified for `docs/GLOSSARY.md`.

---

## Implementation — Must (gate-blocking)

> These map 1:1 to the Must items in `spec.md`.

- [ ] _Concrete task 1_ (file: `path/to/file.py`)
- [ ] _Concrete task 2_ (file: `path/to/file.py`)
- [ ] Tests in `tests/<context>/test_<feature>.py`:
  - [ ] _Test case 1_
  - [ ] _Test case 2_

---

## Implementation — Should

> Defer to a follow-up feature if time runs out.

- [ ] _Concrete task_
- [ ] _Concrete task_

---

## Cross-context Impact

> Document-only or thin adapter changes in other contexts. If any of these need real code, you've miscoped — see Change Locality Test.

- [ ] **Context A:** _change_
- [ ] **Context B:** _change_

---

## Documentation

- [ ] `docs/GLOSSARY.md` updated with new terms (must list in `spec.md`).
- [ ] `docs/01_architecture.md` Context Map updated (if relationships changed).
- [ ] `docs/03_implementation_placement.md` updated (if a placement decision changed).
- [ ] `docs/schemas/` updated (if `kitchen_config.yaml` schema bumped).
- [ ] Worked example in `examples/` updated (if format changed).

---

## Validation

- [ ] All Must boxes ticked above.
- [ ] All tests pass: `pytest tests/<context>/`.
- [ ] No `bpy` / `reflex` / `fastapi` imports in `src/kuchnie_core/` (Rule 5 from `00_LLM_NAVIGATION.md`).
- [ ] No regression in prior phases' tests.
- [ ] Round-trip serialization test passes (if model changed).

---

## Close-out

- [ ] `status.md` set to `done` with `completed` date.
- [ ] `features/INDEX.md` row updated to ✅.
- [ ] If phase-completing: relevant phase in `docs/PHASES.md` signed off.
- [ ] Commit message: `feature: close F0XX — <title>`.

---

## Notes / Scratch

> Use this section for in-progress notes, decisions you might promote to the ADR, or lessons that should be captured.

_(free-form)_
