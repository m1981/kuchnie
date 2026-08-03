# Question Bank — incidents made permanent probes

> Reader: any agent authoring a spec, drafting a red-team brief, or running the monthly audit (the operator's R11 routine) | Enables: probing a new feature or claim batch with the class of gap behind past incidents, before the next incident finds it | Update-trigger: a new incident births a question (append-only), or a written rejection note retires one

Grown by the ritual in [docs/incident-to-gap.md](incident-to-gap.md).
The bank grows monotonically: entries are appended, never deleted; a
question is retired only by a written rejection note inside its entry.
Category tags are short kebab slugs; rejections and deferrals for the
birthing incident are recorded inline in the entry.

## QB-001 <category: procedure-order>
**Q:** For any documented multi-step procedure, which step creates data a later step consumes — and is the required order stated and tested?
**Born:** 2026-07-27 — "extras in any order" in catalog-service.md was false: seed_curated_kitchens creates style_tags that seed_decor_style_tags links to; wrong order seeded 0 associations silently.
**Gap closed by:** doc correction + rebuild re-verification tr-0dda200b.

## QB-002 <category: companion-data>
**Q:** For each catalog entity, is the manufacturer's companion data (edges, profiles, formats) present, or only the primary rows — and does a test assert it?
**Born:** 2026-07-27 — the DB's 19 PF-U-600 worktop variants carried zero variant_edges rows while the manufacturer table lists an HPL edge per decor; the assertion "catalog entities carry their manufacturer companion data" had never been written.
**Gap closed by:** seed_worktop_uu materialising 18 HPL edges + the SC-wtuu-005 test.

## QB-003 <category: derived-attributes>
**Q:** When a seeder derives rows from existing rows, which inherited attributes were verified against the manufacturer source, and which merely copied?
**Born:** 2026-07-27 — kronospan_full.yaml hardcodes structure RS on PF-U-600 variants where the manufacturer table says UE/PE/GG/PN for ten decors; the U-U seeding amplified the error into 36 more rows.
**Tracked as:** wk-4fc28a19.

## QB-004 <category: read-surface-parity>
**Q:** When data is added, do the DIFFERENT read surfaces (endpoints, views, fallbacks) that could serve it actually agree on exposing it?
**Born:** 2026-07-27 — the 36 U-U variants are offered by the configurator's role fallback yet hidden by the worktops endpoint, which requires worktop_specs rows they lack.
**Tracked as:** wk-bca0a74b.

## QB-005 <category: claim-hygiene>
**Q:** Do batch-filed claim texts vary beyond their distinguishing token?
**Born:** 2026-07-27 — nine symbol-pin claim texts sharing a boilerplate tail collided at jaccard 0.617 (door_width × drawer_front_width); ADR-018 would have refused mid-batch.
**Gap closed by:** the tail-variation rule, recorded in
`docs/truth-ledger-machinery.md` § Life of a fact (Filing hygiene).

## QB-006 <category: extraction-shape>
**Q:** For any extraction recipe, what input SHAPE makes it return a truncated-but-nonempty result, and is that shape tested?
**Born:** 2026-07-27 — the symbol-tracing method-pin regex silently dropped the body (~50 lines) of the 62-line decompose_drawer_box definition when its multi-line signature closes at 4-space indent, extracting the 12 signature lines alone.
**Gap closed by:** recipe amendment A4.

## QB-007 <category: data-provenance>
**Q:** Which production tables hold rows no committed script can regenerate, and is each disclosed?
**Born:** 2026-07-27 — production carries 6 decor_style_tags rows (0514/0515 × modern/stone/matte) no committed script regenerates — found only because a scratch rebuild was diffed against production.
**Rejection-with-reason (incident, not the question):** accepted as hand-era residue; disclosed in catalog-service.md's roughness note; pinned counts exclude that table. The question stays live.

## QB-008 <category: retraction-hygiene>
**Q:** Before a retraction is recommended or executed, was the id's citation set swept corpus-wide (specs, docs, use-cases) — not just the file that prompted the check?
**Born:** 2026-07-28 — the tr-44356ef4 retraction was recommended as "trips nothing" after checking only catalog-service.md; the id was also cited in use-cases.md and purchasing-variants.md, and spec-health went red until both citations were swapped to the live successor tr-0dda200b.
**Gap closed by:** citation swaps in both files (this commit); the recommending agent's own sweep habit corrected.

## QB-009 <category: namespace-ownership>
**Q:** For artifacts a template ships into a consumer repo, who owns the number/name space they land in — and is the boundary tested before the two series collide?
**Born:** 2026-07-29 — the truth-ledger template ships its 33 machinery ADRs into the consumer's shared `docs/adr/`, overlapping kuchnie's domain series (~15 duplicate numbers; "ADR-009" ambiguous between evidence-screen and a rename decision; the next meta ADR number would collide with kuchnie's fresh ADR-034).
**Gap closed by:** template release v0.9.18 — machinery ADRs move to the `docs/adr/truth/` namespace; interim rule: cite machinery ADRs by full title, never bare number.

## QB-010 <category: lesson-routing>
**Q:** Where does a cross-cutting, project-agnostic lesson go — agent session memory, the consumer's question bank, or the template harness — and what forces that routing decision to be made?
**Born:** 2026-07-29 — the operator noticed a session-compaction brief carrying seven agent-agnostic rules (retraction citation sweep, doc↔claim two-commit dance, mechanical pre-scan of claim batches, version-pin divergences are genuine, copier-managed-file upstreaming, argv-array drivers, post-merge reaffirm commits) that lived ONLY in one agent's session memory and would die with it.
**Gap closed by:** the seven rules promoted into the template harness (machinery.md "Filing hygiene & aftermath" + a verifier-prompt line) in v0.9.18; this question stands as the standing router for the next lesson.

## QB-011 <category: intake-warnings>
**Q:** When a CLI verb prints a warning above its final output line (evidence exit-1, unprotected premise, screen notes), did the operator or agent actually read it — or did a `tail -1` style capture swallow it?
**Born:** 2026-07-29 — the v0.9.19 consume claim tr-0e884e02 was filed with its evidence chain already failing (returncode 1: the machinery.md authoring-loop section never landed after a botched stash-pop conflict resolution took the pre-copier HEAD version); the intake warning was piped away by tail -1 and the hollow claim died only at its independent verification.
**Gap closed by:** machinery.md restored from the template, successor claim filed with passing evidence; batch drivers now surface full CLI output on nonzero-warning paths.

## QB-012 <category: adequacy>
**Q:** Why is this the RIGHT set of statements, rather than merely a set of true ones? For any spec, gate suite or claim batch: what would be missing if every statement in it were true and the system still failed the user?
**Born:** 2026-08-03 — the source-lineage research (`docs/reviews/sources/knowledge-architecture-lineage.md`) established that this project's invariant/testimony split reproduces Zave & Jackson's K (domain knowledge) but not their S, and that the missing third of their distinction is R (requirements) — carrying the adequacy obligation `S, K ⊢ R`. Every mechanism here is verification ("am I building it right"); nothing is validation ("am I building the right thing"). Boehm named that split in 1979 and this repo has only ever built one half of it.
**Tracked as:** open. No design in the surveyed lineage closes it, and this is deliberately a standing probe rather than a bead: the answer is a judgment made per spec, not a check that can be automated. The owner questions in `docs/reviews/owner-todo-2026-08-02.md` are the de-facto validation layer today, and they live in prose.

## QB-013 <category: bounded-reads>
**Q:** Does this conclusion assert something UNBOUNDED ("never runs", "does not exist", "is empty", "all of them") while resting on a BOUNDED read — `tail -n`, `head -n`, `grep -A/-B/-m`, a truncated pager, or a filter that matched the wrong field?
**Born:** 2026-08-03 — three instances in one session, all by the same agent. (a) `bd close A B` piped through `tail -1` showed only the second confirmation; the first bead silently failed to close and left the P1 lead item blocked by finished work. (b) `grep -A 4 "^on:"` truncated a workflow's trigger block, producing a published finding that `truth-gate.yml` "fires only on pull_request and has never run" — it carries both triggers and `gh run list` shows it completing on push. (c) `grep -c 'unverified'` matched the word inside claim TEXT rather than the status column, so `session-close.sh` reported two unverified claims where the true count was zero.
**Generalises:** QB-011, which asked the same question for the narrower case of a warning line swallowed by `tail -1`. **QB-011 was banked on 2026-07-29 and the failure recurred on 2026-08-03 anyway** — so the gap is not a missing question but a question that never reached the point of use. A bank entry is read when someone opens the bank; the failure happens mid-command.
**Gap closed by:** delivery rather than documentation — the rule is stored via `bd remember` (key `bounded-reads`), which the `SessionStart` hook injects through `bd prime` into every session's context without anyone opening a file. Prose mirrors live in AGENTS.md and CLAUDE.md.

