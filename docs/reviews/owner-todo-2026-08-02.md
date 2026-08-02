# Your paste-ready to-do (2026-08-02)

> Reader: Michał, at a terminal in the repo root | Enables: clearing
> everything still blocked on you, by copy-paste, in roughly ten minutes |
> Update-trigger: an item is done (delete its section) or a new owner-gated
> item appears

Four questions were answered on 2026-08-02 and are already recorded in their
beads — **nothing below repeats them.** What remains is three things only you
can do. Run from the repo root: `cd ~/PycharmProjects/kuchnie`.

---

## 1. Two ledger retractions (2 min)

Retraction is human-only by design — the gate exists so an agent cannot
quietly bury a fact. Both of these are claims **this review filed** that its
own repairs then made false, which is the ledger working correctly:

```bash
TRUTH_HUMAN=1 scripts/truth verdict tr-4476e4d8 retracted \
  --basis "superseded by tr-ce5c7845; Material gained structure and thickness_mm in kuchnie-h45 step 1"

TRUTH_HUMAN=1 scripts/truth verdict tr-0151520f retracted \
  --basis "superseded by tr-7f0c23cd; the DrawerSystem ABC gained runner_y_mm via DrawerBoxSpec in kuchnie-27b"
```

Each will ask you to type the id back to confirm. Both successors are already
filed, verified and premise-linked, so `scripts/truth ready` is correct with
or without this — the retraction is tombstoning, not unblocking.

*(The five retractions listed in the earlier unblock doc are already done —
they were retracted at 15:01 today. Nothing to do there.)*

---

## 2. Two claimed work items (1 min)

`session-close.sh` cannot pass while these are open. They are yours from
earlier sessions and I did not touch them.

```bash
scripts/truth issues | grep claimed
```

For each, either finish it:

```bash
scripts/truth done wk-593a317b --claim "<what the finished work made true>"
scripts/truth done wk-59b943b1 --claim "<what the finished work made true>"
```

…or release it back to the pool if it is parked:

```bash
scripts/truth start --release wk-593a317b
scripts/truth start --release wk-59b943b1
```

- `wk-593a317b` — purchasing artifacts (board + hardware order generation).
  Twin bead `kuchnie-ubc`, in progress.
- `wk-59b943b1` — labor pricing per module type (cennik nakładów). Twin bead
  `kuchnie-60t`, in progress.

**Note:** `truth done --claim` files the completion claim *unverified* and
without an evidence command. If you use it, follow with a manual check and
`scripts/truth verdict <new-id> agree --basis "<what you checked>"`, or it
will sit in the queue.

---

## 3. The prices — the one that costs you money today (5 min)

**This is the only item on this page that is silently affecting real
quotes.** Every widełka the software produces right now rests on hardcoded
numbers with no supplier and no date, and the freshness gate cannot see them,
so a quote can be graded offer-grade while resting entirely on a guess.

### The proper route: a landing CSV

`price_import` accepts a **semicolon-separated** CSV with this exact header.
Save as `prices-2026-08.csv` anywhere and fill in what you know:

```csv
supplier;item_code;description;unit;price_net;currency;valid_from;source_ref
Cutting service;USL-CIECIE;Ciecie i nesting;m2;;PLN;2026-08-02;
Cutting service;USL-OKLEJANIE;Oklejanie PUR;lm;;PLN;2026-08-02;
Plinth supplier;COKOL-PVC;Cokol PVC;lm;;PLN;2026-08-02;
Plinth supplier;COKOL-USZCZ;Uszczelka cokolu;lm;;PLN;2026-08-02;
Blum dealer;BLUM-LEGRA-SET;Legrabox zestaw;sets;;PLN;2026-08-02;
Blum dealer;BLUM-ZAWIAS;Zawias;pcs;;PLN;2026-08-02;
GTV;UCHWYT;Uchwyt;pcs;;PLN;2026-08-02;
GTV;NOZKA;Nozka regulowana 100;pcs;;PLN;2026-08-02;
GTV;CARGO;Cargo / mechanizm wysuwny;sets;;PLN;2026-08-02;
```

Rules the importer enforces, so you do not fight it:

- `unit` must be one of `m2 lm mb pcs szt sets kpl`
- `valid_from` is the date the price is *good from*, not today's date if
  they differ — it drives freshness grading
- a price more than **50 %** away from the last known price for the same
  `item_code` is **refused** for your eyeballs, not silently accepted
- leave `source_ref` empty; the importer stamps the archived source path
- **delete any row you do not know.** A missing row is honest; a guessed row
  is the exact problem this fixes

### The fast route, if a CSV is a faff

Just reply with the numbers and who they came from, in any format — even
"cutting is 18 zł/m² at Drewpol since June, the rest I don't know". I will
build the CSV and run the import. Partial is genuinely useful: each number
moves independently.

### If a number is a guess

**Say so.** It gets labelled ASSUMPTION in code and the quote is forced to
estimate-grade. That is the honest outcome and strictly better than the
silence we have now.

### Current hardcoded values, for reference

| What | Hardcoded now | Where |
|---|---|---|
| Cutting / nesting (cięcie) | 15.00 PLN/m² | `bom_generator.py` |
| Edgebanding PUR (oklejanie) | 4.50 PLN/lm | `bom_generator.py` |
| Plinth board (cokół) | 25.00 PLN/lm | `bom_generator.py` |
| Plinth seal (uszczelka) | 3.50 PLN/lm | `bom_generator.py` |
| Drawer system "Blum/Hettich" | 150.00 PLN/set | `rules_engine.py` |
| Cargo / pull-out | 600.00 PLN/set | `rules_engine.py` |
| Hinge (zawias) | 15.00 PLN/pc | `rules_engine.py` |
| Handle (uchwyt) | 25.00 PLN/pc | `rules_engine.py` |
| Leg (nóżka) | 1.50 PLN/pc | `rules_engine.py` |

---

## 4. One follow-up question from your NL answer

You chose **derive NL from carcass depth**, and confirmed **560 → NL 500**.
The rest of the table is not confirmed and I will not invent it — drawer
runner lengths are a manufacturer fact, not a preference.

Fill in whichever rows you actually build:

| Carcass depth | NL | Confirmed? |
|---|---|---|
| 560 mm | 500 | ✅ you confirmed |
| 500 mm | ? | |
| 450 mm | ? | |
| 350 mm | ? | |

If you only ever build 560-deep base cabinets, say so — then the rule is
"NL 500, and the buildability gate refuses any other depth loudly", which is
simpler and equally correct for your shop.

---

## What happens once these are done

| You do | Unblocks |
|---|---|
| §1 retractions | verdict queue empties |
| §2 claimed items | `session-close.sh` can finally pass green |
| §3 prices | `kuchnie-5q3` — every quote stops resting on guesses |
| §4 NL table | the last gate on `kuchnie-lm8`, the lead fidelity item |

Already unblocked by today's answers and needing nothing further from you:
`kuchnie-4q8` (drawer-front move is now a pure move), `kuchnie-lh2`
(kitchen-cam parked explicitly), and `kuchnie-h45` steps 2–5 (the identity
shape was already confirmed on 2026-08-01).
