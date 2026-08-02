# Decisions only you can make — the unblock list (2026-08-02)

> Reader: Michał, working through the queue of things an agent must not
> decide | Enables: unblocking five stalled work items and clearing the
> ledger's verdict queue, each with the exact command to run | Update-trigger:
> a question is answered (record the answer in its bead and delete the
> section), or a new owner-gated item appears

Everything here is blocked on a fact or an authority that belongs to you, not
to an agent. Nothing in this list is a matter of opinion about code — those
decisions have all been made and filed as beads.

**Two kinds of item below.** Sections A and B are *questions* — a sentence
from you unblocks work. Section C is *authority* — the ledger physically
refuses agent action and needs your hands on the keyboard.

---

## A. Business numbers — an agent must never invent these

### A1. Service and material rates → unblocks `kuchnie-5q3` (small, immediate)

Four prices are hardcoded in the quoting code with no supplier and no date,
and every quote the software produces today rides on them:

| What | Currently hardcoded | Real rate? | From whom? | As of when? |
|---|---|---|---|---|
| Cutting / nesting (cięcie) | 15.00 PLN/m² | | | |
| Edgebanding PUR (oklejanie) | 4.50 PLN/mb | | | |
| Plinth board (cokół) | 25.00 PLN/mb | | | |
| Plinth seal (uszczelka) | 3.50 PLN/mb | | | |

Same problem, one layer down — these seed the hardware price table:

| What | Currently hardcoded | Real rate? |
|---|---|---|
| Drawer system, priced generically as "Blum/Hettich" | 150.00 PLN/set | |
| Cargo / pull-out mechanism | 600.00 PLN/set | |
| Hinge (zawias) | 15.00 PLN/pc | |
| Handle (uchwyt) | 25.00 PLN/pc | |
| Cabinet leg (nóżka) | 1.50 PLN/pc | |

**Why this is the highest-value answer on the page.** You chose fidelity
first, which means the software will not produce a formatki order for a while
yet. But it *is* producing widełki now, and every one of them is carried by
these numbers. The freshness gate cannot see them, so a quote can be graded
offer-grade while resting entirely on a guess.

**A partial answer is still useful.** If you know the cutting rate and not the
rest, say so — each number can be moved independently. **If any of these are
guesses, say that too**: they will be labelled ASSUMPTION in the code and the
quote will be forced to estimate-grade, which is the honest outcome and better
than the silence we have now.

---

## B. Trade conventions — needed to model the geometry correctly

### B1. Drawer-front division → unblocks `kuchnie-4q8` (medium)

For a drawer base (szafka dolna szufladowa), the code currently computes each
drawer front height as an **equal division** of (carcass height − plinth),
with a **uniform 3 mm gap** above, between, and below every front.

Is that what you actually build? The plausible alternatives:

- equal division, uniform 3 mm gap everywhere — *what the code assumes*
- equal division, but a different reveal at the very top or very bottom
- **fixed** front heights per LEGRABOX height code, with the remainder
  absorbed somewhere specific

Please answer *before* the code moves, not after. The plan is to relocate this
formula out of the translation layer into the construction method; if the
convention is also wrong, I want the move and the correction to be two
separate commits so a later reader can see which was which.

### B2. Default drawer system → narrows `kuchnie-lm8` (medium)

Your fidelity-first decision already answered the big version of this question:
we will model **both** LEGRABOX and TANDEMBOX properly rather than picking one.
What remains is small — when you add a new drawer base, which should the
software default to?

Context: the purchasing side is built around LEGRABOX (it has a LEGRABOX colour
setting and a LEGRABOX accessory parser), while the quoting side currently
hardcodes TANDEMBOX geometry. One of the two is modelling a system you do not
buy, and that is the mismatch this fixes.

Related, same item: should the drawer **NL** (nominal length) be derived
automatically from carcass depth — e.g. 560 mm carcass → NL 500 — or picked
per project? Right now every ERP-derived drawer box is NL 500 regardless of
depth, which is correct for a 560 carcass and wrong for a shallower one.

### B3. kitchen-cam's delivery shape → part of `kuchnie-lh2` (small)

The drilling and DXF code works and is tested, but nothing calls it and there
is no command to run it. Which do you want?

- a library the ERP calls when you press a button (later, once wiring resumes)
- a small command-line tool you run yourself on a project
- leave it parked, explicitly, until the wiring phase

"Leave it parked" is a perfectly good answer — it just needs to be *said*, so
it gets recorded in the allowlist rather than looking like an oversight.

---

## C. Ledger authority — the tool refuses agents by design

Five claims sit in the verdict queue as `diverged`. I resolved what an agent
legitimately can; the rest is gated on you.

**What I already did (no action needed from you):**

- `tr-ff8a5110` (the ADR-015 BOM-fold claim) was diverging for a reason worth
  knowing: **its evidence command is nondeterministic.** It runs `grep -c`
  across three files, and the output line order changes between runs — I
  observed three different orderings in three consecutive runs. That claim
  could never re-verify no matter what the code did. I annotated it as a
  mechanical divergence (ADR-012) and filed a deterministic successor,
  `tr-5f88b6f8`, which pipes the multi-file grep through `sort`. Verified and
  agreed. **The underlying fact was fine all along** — only the ruler was bent.
- The three template-sync claims (`tr-06522739` v0.9.19, `tr-7855c415` v0.9.21,
  `tr-4d916887` v0.9.25) are a superseded chain; the repo now pins **v0.9.26**,
  so all three are genuinely false history. I filed the current successor,
  `tr-d8e5a5ba`, verified and agreed.
- `tr-611a8240` (purchasing order docs) was already superseded by the live
  `tr-6d1f8951` when the LEGRABOX-colour increment raised the test count.

**What needs your hands.** Retraction is human-only — it requires a typed-id
confirmation, and that gate exists precisely so an agent cannot quietly bury a
fact. These four are dead history with live successors and should be
tombstoned:

```bash
TRUTH_HUMAN=1 scripts/truth verdict tr-06522739 retracted --basis "superseded by tr-d8e5a5ba; pin moved to v0.9.26"
TRUTH_HUMAN=1 scripts/truth verdict tr-7855c415 retracted --basis "superseded by tr-d8e5a5ba; pin moved to v0.9.26"
TRUTH_HUMAN=1 scripts/truth verdict tr-4d916887 retracted --basis "superseded by tr-d8e5a5ba; pin moved to v0.9.26"
TRUTH_HUMAN=1 scripts/truth verdict tr-611a8240 retracted --basis "superseded by the live tr-6d1f8951 after the colour-parameter increment"
```

`tr-ff8a5110` is the judgement call. Its successor `tr-5f88b6f8` is live, so
retracting it is defensible — but it is also the only surviving record that a
nondeterministic recipe once slipped through the filing gate. **My
recommendation: retract it, and bank the lesson as a question-bank entry
instead**, where it will actually get asked of future claims:

> **QB-nnn** *<category: evidence-determinism>*
> **Q:** Does this claim's evidence command produce byte-identical output when
> run three times in a row — including multi-file `grep`, directory listings,
> and anything whose ordering the filesystem chooses?
> **Born:** 2026-08-02 — tr-ff8a5110 ran `grep -c` over three files and emitted
> a different line order on each run, so it could never re-verify; it sat
> diverged in the queue while the fact it described was true the whole time.

That is your call to make and your file to append to
(`docs/question-bank.md` grows append-only via `docs/incident-to-gap.md`).

### C1. Two work items are still claimed

`session-close.sh` cannot pass while these are open — they are yours from
earlier sessions, and I did not touch them:

- `wk-593a317b` — Purchasing artifacts: board-order + hardware-order generation
- `wk-59b943b1` — Labor pricing per module type (cennik nakładów)

Either finish them (`scripts/truth done <id> --claim "<what it made true>"`)
or release them (`scripts/truth start --release <id>`) if they are parked. The
matching beads are in progress too, which is what `10-bd-twins.sh` reports.

---

## D. One thing I found and did not fix

`session-close.sh` has been reporting **"WARN 2 claim(s) unverified"
indefinitely, and it is wrong.** Line 54 counts with
`scripts/truth list | grep -c 'unverified'`, which matches the *word* anywhere
in the line — including inside claim text. Two claims happen to describe
session-close itself with the phrase *"warns on unverified claims"*, so the
gate counts them as unverified:

```
scripts/truth list | grep -c 'unverified'             ->  2   (what the gate sees)
scripts/truth list | awk '$2=="unverified"' | wc -l   ->  0   (the truth)
```

The real number is zero. Filed as `kuchnie-c6z`. I deliberately did **not**
fix it in place today: an agent working `kuchnie-lh2` may be editing
`session-close.sh` to register the new reachability gate, and a concurrent
edit to the same file would have caused a merge conflict for no benefit. It
lands right after that merge.

---

## Summary — what each answer buys

| Answer | Unblocks | Size |
|---|---|---|
| A1 rates | `kuchnie-5q3` — every quote stops resting on guesses | S |
| B1 reveal convention | `kuchnie-4q8` — construction math moves home correctly | M |
| B2 drawer default + NL rule | narrows `kuchnie-lm8`, the lead fidelity item | M |
| B3 kitchen-cam shape | `kuchnie-lh2` allowlist entry becomes a decision, not a gap | S |
| C retractions | verdict queue empties; `session-close.sh` gets closer to green | S |
| C1 claimed items | `session-close.sh` can actually pass | S |

If you only have time for one: **A1**. It is the only item on this page that
is silently affecting money today.
