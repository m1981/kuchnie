# Machinery atlas — the whole apparatus, from six angles (2026-08-04)

> Reader: Michał, or anyone who must understand what runs this repo before
> changing it | Enables: seeing the system's layers, triggers, state machines
> and human seams without reverse-engineering them from scripts a second time
> | Update-trigger: a gate, hook, workflow, verb or status is added, removed
> or repositioned
>
> **STATUS: ATLAS.** Part I is a reusable prompt carrying the vocabulary;
> Part II is the diagram set. Every diagram carries an evidence anchor and an
> `OBSERVED` / `INFERRED` label. Nothing here rests on recollection — the
> facts were re-read from disk on 2026-08-03/04, mostly while wiring the very
> gates being drawn.

---

# Part I — The prompt

Use this to regenerate, extend or audit the atlas in a fresh session. It is
written to be pasted whole. Its job is to install the vocabulary first,
because most misdrawings of this system come from using ordinary words
("check", "task", "done") where the system has precise ones.

## Role

> You are documenting a **self-governing repository**: a codebase that
> carries machinery for deciding whether its own recorded knowledge is still
> true. Two apparatuses coexist. A **truth ledger** governs *facts*, and an
> **issue tracker** governs *intentions*. They are linked, and the link is
> what makes work refusable when the ground under it has moved.
>
> Your task is to draw how it is wired: layers, triggers, state machines,
> dependencies, and — most importantly — the seams where the machine stops
> and requires a human.

## Vocabulary — use these words, not synonyms

**Ledger side.**

| Term | Meaning |
|---|---|
| **claim** (`tr-…`) | one recorded fact, with an evidence command and watched paths |
| **evidence command** | a re-runnable, read-only command whose *output hash* is the proof; screened by an allowlist (ADR-009/029/040/041) |
| **verdict** | an independent judgment on a claim: `agree`, `diverge`, `cannot_verify`, `retracted` |
| **invalidation** | a *mechanical* demotion, filed when a watched path changes — no judgment involved |
| **reaffirm** | mechanical re-confirmation when the evidence hash still matches after a staling commit (ADR-030) |
| **retraction** | the only way a fact leaves; carries a **cause** (`restated` / `expired` / `wrong`) and, for `restated`, a **successor** (ADR-049) |
| **premise** | a link from an *issue* to a *claim*: "this work stands on this fact" |
| **issue / work item** (`wk-…`) | the ledger's **native work kernel** (ADR-002), independent of any tracker |
| **bead** (`kuchnie-…`) | the same intention in the `bd` tracker; a **twin** of a `wk-` item across the **adapter seam** (ADR-004) |
| **status registry** | the authoritative status vocabulary, read at runtime via `truth vocab` — never hand-copied (ADR-043) |
| **HELD** | `truth ready`'s refusal: an issue whose premises are no longer valid |

**Gate side.**

| Term | Meaning |
|---|---|
| **gate** | a check that can refuse |
| **arm** | one independent check inside a gate script |
| **posture** | `blocking` or `advisory` — whether an arm's finding stops the boundary |
| **dark arm** | an arm that examined nothing; must be a FAILURE, never a pass |
| **root** | a scheduled invoker (hook, workflow, cron). A check no root reaches **is prose** (ADR-048) |
| **canary** | the seeded-fault suite: deliberately broken inputs that every arm must CATCH; it tests the *checkers*, not the code |
| **fault arm** | one seeded fault in the canary, named e.g. `FAULT SC`, `FAULT LK` |
| **tier** | A/B/C: what ships to consumers vs what stays in the meta-repo (ADR-046) |
| **whisper budget** | the deliberate cap on advisory output; noise trains bypass (ADR-005) |
| **adoption metric** | the measurement a blocking gate owes before it may block (ADR-047) |

**Failure vocabulary** — the named ways this system has actually failed:

- **dead sensor / F1 rule** — a checker that cannot run must *scream*, never
  read as zero. A `2>/dev/null | grep -c` turns a crashed tool into "all clear".
- **bounded read** (QB-013) — never let a bounded read support an unbounded
  claim. `tail -1`, `grep -A 4`, an unanchored substring: each has published a
  false finding here.
- **evidence that cannot fail** — a proof whose command would print the same
  thing whether or not the claim held.
- **gate that refuses legitimate work** — teaches its own bypass (ADR-014).
- **normalisation of deviance** — an advisory nobody acts on becomes furniture.

## Invariants to respect while drawing

1. **INV-A**: the ledger is strictly append-only. Status changes are *new
   records*, never edits. Any diagram showing a claim "being updated" is wrong.
2. **Fold, not database**: statuses are *derived* by a pure confluent fold over
   the record stream. Two machines folding the same file agree.
3. **Author ≠ verifier** (ADR-010), and it is **asymmetric**: self-`diverge`
   and self-`cannot_verify` are allowed because they run against interest;
   only self-`agree` is refused.
4. **Terminal acts need a human** (ADR-011), gated on `stdin.isatty()`.
5. **The template ships artifacts; it cannot ship habits.** Anything the
   consumer must *remember* is, in practice, not enforced.

## What to produce

Diagrams at these angles, each with a caption naming its evidence and an
`OBSERVED` / `INFERRED` label:

1. **Provenance** — meta-repo → template → consumer; what deliberately does
   not ship.
2. **Trigger topology** — every automatic root and its reach; what is prose.
3. **Claim lifecycle** — the status state machine and the verbs that move it.
4. **Work kernel lifecycle** — issue states, premise links, `ready` gating.
5. **Twin coupling** — ledger work kernel ↔ tracker across the adapter seam.
6. **Gate anatomy** — posture taxonomy, dark-arm rule, reachability.
7. **Human seams** — every place the machine stops and asks.
8. **Defence map** — failure family → the mechanism that catches it.
9. **Sequences** — a claim's life; a session's shape.

## Rules of the drawing

- **Cite, don't recall.** Every arrow traces to a file line, a trigger block
  or a verb. If you cannot cite it, label the node `INFERRED`.
- **Never let a bounded read support an unbounded claim.** Before writing
  "nothing invokes X", grep unfiltered *and run a positive control*.
- **Verify by re-query.** Do not conclude from a command's own output.
- **Draw the holes.** A diagram that shows only what works is marketing.

---

# Part II — The atlas

## 1. Provenance: what is inherited, and what is deliberately withheld

```mermaid
flowchart TB
    subgraph META ["META-REPO m1981/truth-ledger"]
        direction TB
        TPL["template/ — Tier A<br/>shipped to every consumer"]
        INST["instruments/ + meta gates — Tier C<br/>META-REPO ONLY, ADR-003 rule 2"]
    end

    subgraph SHIPPED ["what arrives here via copier"]
        S1["truthlib/ — kernel, policy, registry, cli, advisory"]
        S2["scripts/truth · check-truth.sh · truth-canary.sh"]
        S3["scripts/spec-health.sh · doc-health.sh · session-close.sh"]
        S4[".githooks/ pre-commit · post-commit · post-merge"]
        S5[".github/workflows/ truth-gate · truth-scan · truth-canary"]
        S6["docs/adr/truth/001..049"]
    end

    subgraph WITHHELD ["what never ships"]
        W1["gate-reachability.sh — the check that finds unreachable checks"]
        W2["release-battery.sh"]
        W3["separation-report · retraction-causes · override-velocity"]
    end

    TPL --> SHIPPED
    INST --> WITHHELD
    SHIPPED --> KU["kuchnie — consumer<br/>.copier-answers pins _commit: v0.9.34"]
    WITHHELD -.->|"enumeration encodes<br/>the meta-repo's own wiring"| X(("consumer inherits<br/>the LAW, not the<br/>ENFORCEMENT"))

    KU --> LOCAL["locally authored, template-invisible:<br/>scripts/session-gates.d/ ·<br/>scripts/pre-push-checks.sh ·<br/>.beads/hooks/*"]

    style X fill:#fdd,stroke:#c00
    style WITHHELD fill:#fff4f4
```

*`OBSERVED`. Ship list from `template/` at tag v0.9.34; withheld scripts carry
an explicit META-REPO ONLY banner. The consumer receives ADR-048 — "a check no
scheduled root invokes is prose" — and no script that enforces it. This is the
single most load-bearing asymmetry in the whole system: it is why the local
`gate-reconcile` arm had to be written by hand here.*

## 2. Trigger topology: what fires without anyone remembering

```mermaid
flowchart LR
    subgraph ROOTS ["scheduled roots"]
        C(["git commit"])
        M(["git merge"])
        P(["git push"])
        CR(["cron Mon 06:17 UTC"])
        H(["a human deciding to"])
    end

    C --> PC["pre-commit"]
    PC --> G1["check-governance.sh<br/>BLOCKS"]
    PC --> G2["check-truth.sh<br/>BLOCKS · INV-A"]
    C --> POC["post-commit → invalidate-scan"]

    M --> PMC["pre-merge-commit<br/>check-truth.sh · BLOCKS<br/>ADR-045 · wired 2026-08-04"]
    M --> POM["post-merge → invalidate-scan"]

    P --> PP["pre-push → pre-push-checks.sh"]
    PP --> B1["10 BLOCKING arms<br/>spec-health · doc-health · exercise-gate ·<br/>4 test suites 1434 tests ·<br/>test-health · reachability · gate-reconcile"]
    PP --> B2["8 ADVISORY arms<br/>bd-twins · dashboard-fresh · new-dark ·<br/>arch-smells · signature/vocab/glossary-drift · ruff"]
    PP --> B3["human-queue note<br/>printed, never blocks"]

    P --> WF1["truth-scan.yml<br/>scan → commit demotions → death report"]
    P --> WF2["truth-gate.yml<br/>INV-A/INV-B in CI · catches --no-verify"]
    CR --> WF3["truth-canary.yml<br/>261 seeded faults"]

    H -.->|"prose only"| SC["session-close.sh<br/>dirty tree · claimed items ·<br/>all 11 gates"]

    style SC fill:#fff4f4,stroke:#c60
```

*`OBSERVED`. Hook contents read in full from `.beads/hooks/` (core.hooksPath
points there); workflow triggers read as whole blocks, not `grep -A n` — an
earlier truncation of exactly this kind produced a published false finding.
`session-close.sh` remains reachable only by prose; the push boundary now
duplicates its gate coverage, not its session-scoped checks.*

## 3. Claim lifecycle: statuses are derived, never assigned

```mermaid
stateDiagram-v2
    [*] --> unverified: truth claim
    unverified --> live: verdict agree — different session, ADR-010
    unverified --> diverged: verdict diverge
    unverified --> cannot_verify: verdict cannot_verify

    live --> stale: invalidation — watched path changed, mechanical
    stale --> live: reaffirm — evidence hash still matches, ADR-030
    stale --> diverged: recheck hash mismatch
    live --> disputed: contradicts

    diverged --> live: new verdict agree
    cannot_verify --> live: verdict agree

    live --> retracted: verdict retracted --cause
    stale --> retracted: verdict retracted --cause
    diverged --> retracted: verdict retracted --cause
    retracted --> [*]

    note right of retracted
        ADR-049: the cause is recorded
        restated → successor REQUIRED
        expired  → successor optional
        wrong    → successor optional
        ADR-011: human, isatty-gated
    end note

    note left of stale
        Nothing is edited. Every arrow
        is a NEW appended record; the
        status is a fold over them.
    end note
```

*`OBSERVED`. Statuses and verdict mapping read from `truth vocab` at runtime,
which is the registry itself (ADR-043) rather than a copy: `verdicts:
agree->live, diverge->diverged, cannot_verify->cannot_verify,
retracted->retracted`. The `--cause` arm was exercised for the first time in
this repo on 2026-08-04, retiring two claims that asserted a superseded
template pin.*

## 4. Work kernel: how a fact can refuse a task

```mermaid
flowchart TB
    subgraph K ["native work kernel — ADR-002"]
        I["issue wk-…"]
        I --> ST{"folded status<br/>ADR-028"}
        ST --> O["open"]
        ST --> CL["claimed"]
        ST --> RE["released"]
        ST --> DO["closed"]
        ST --> CA["cancelled — terminal"]
    end

    I -->|"truth premise"| CLM["claim tr-…"]

    CLM --> V{"premise validity<br/>ADR-001 · registry-driven"}
    V -->|"live"| READY["READY — surfaces in truth ready"]
    V -->|"unverified · cannot_verify"| WARN["READY but WARNED"]
    V -->|"stale · diverged · retracted<br/>disputed · cannot_verify"| HELD["HELD — refused"]

    READY --> WORK["an agent may take it"]
    HELD -.-> RENEG["renegotiate the fact first"]

    ADAPT["scripts/truth-bd-adapter.sh<br/>| scripts/truth ready --stdin"] --> V

    style HELD fill:#fdd,stroke:#c00
    style READY fill:#efe
```

*`OBSERVED`. `premise_blocking: stale,diverged,cannot_verify,retracted,disputed`
and `premise_warn: unverified,cannot_verify` come from `truth vocab`. This is
the mechanism the whole apparatus exists for: **work standing on a dead fact is
not offered**. It is also why `bd ready` alone is the wrong verb here — it sees
intentions but not the ground they stand on.*

## 5. Twin coupling: two trackers, one intention

```mermaid
flowchart LR
    subgraph LEDGER ["truth ledger — facts and intentions"]
        WK["wk-59b943b1<br/>claimed → released"]
        TR["tr-6692cbe7<br/>premise"]
        WK -->|premise| TR
    end

    subgraph BD ["bd — embedded Dolt, refs/dolt/data"]
        BE["kuchnie-60t<br/>in_progress → open"]
        MEM["bd remember<br/>13 memories, injected at session start"]
    end

    WK <-->|"adapter seam<br/>ADR-004 · twin ids"| BE
    BE --> GATE["10-bd-twins.sh<br/>no in_progress may survive a session"]
    MEM --> PRIME["bd prime via SessionStart hook<br/>— the ONLY mechanically<br/>delivered rule channel"]

    JSONL[".beads/issues.jsonl<br/>PASSIVE export — never the source"] -.-> BD

    style PRIME fill:#efe
    style JSONL fill:#f6f6f6
```

*`OBSERVED`. The A/B trial is deliberate: the ledger has a native work kernel
and `bd` runs beside it. `bd remember` is the load-bearing detail — QB-011 sat
in the question bank for five days and the failure it describes recurred
anyway, because a bank entry is read when someone opens the bank. The same
rule delivered through `bd prime` arrives unasked. **The gap was delivery, not
documentation.**

## 6. Gate anatomy: posture, darkness, reachability

```mermaid
flowchart TB
    GATE["an arm runs"] --> OUT{"did it report<br/>what it examined?"}
    OUT -->|"no output"| DARK["FAIL — dark arm<br/>examined nothing ≠ clean"]
    OUT -->|"counts present"| RC{"posture"}

    RC -->|blocking| RCB{"exit code"}
    RCB -->|"0"| OK1["pass"]
    RCB -->|"non-zero"| FAILB["BLOCK the boundary"]

    RC -->|advisory| ADV["print one summary line<br/>never blocks"]
    ADV --> METRIC["accumulates the ADR-047<br/>adoption metric"]
    METRIC -.->|"owner decides,<br/>with a review date"| RCB

    ALL["scripts/session-gates.d/*.sh"] --> RECON{"gate-reconcile:<br/>is every gate<br/>named by a root?"}
    RECON -->|"no"| FAILR["FAIL — ADR-048<br/>a check no root invokes is prose"]
    RECON -->|"yes"| OK2["pass"]

    SENSOR{"could the checker<br/>itself have crashed?"} -->|"unchecked"| F1["dead sensor — F1<br/>a crash reads as 'all clear'"]
    SENSOR -->|"exit code read first"| SCREAM["SENSOR FAILED · loud"]

    style DARK fill:#fdd,stroke:#c00
    style F1 fill:#fdd,stroke:#c00
    style FAILR fill:#fdd,stroke:#c00
```

*`OBSERVED`, and earned. The dark-arm rule caught three of my own bugs within
24 hours: a test-count parser that reported two live suites as dark, a probe
harness, and `10-bd-twins.sh`, which printed nothing when it was happy and so
blocked a push on its own silence. Posture is not uniform by taste: six gates
declare in their own headers "WARN-only by design … promoting this to FAIL is
Michał's call", and two carry session semantics that would refuse legitimate
mid-work pushes.*

## 7. Human seams: where the machine stops on purpose

```mermaid
flowchart TB
    subgraph AUTO ["the machine decides"]
        A1["INV-A append-only"]
        A2["invalidation on path change"]
        A3["reaffirm on hash match"]
        A4["fold → status"]
        A5["premise validity → HELD"]
    end

    subgraph HUMAN ["a human must decide"]
        H1["retraction<br/>ADR-011 · stdin.isatty · TRUTH_HUMAN_ACK names the exact id"]
        H2["verdict on a claim your own session filed<br/>ADR-010 · asymmetric: only agree is refused"]
        H3["promoting an advisory arm to blocking<br/>ADR-047 · needs a metric and a review date"]
        H4["quantifier scope<br/>ADR-007 · --scope-ok, expires by default ADR-032"]
        H5["accepting a baseline<br/>drift gates: --write then commit"]
        H6["facts only the owner holds<br/>rates, depth→NL table"]
    end

    AUTO --> SURFACE["surfaced at the push boundary,<br/>printed and never blocking:<br/>'needs your judgment: N claims, M beads'"]
    SURFACE --> HUMAN

    H2 --> DISP["scripts/truth dispatch tr-…<br/>emits a verifier prompt with an<br/>integrity hash and END-OF-DISPATCH terminator"]

    style HUMAN fill:#fffbe6
    style SURFACE fill:#efe
```

*`OBSERVED`. The interactive guard is `sys.stdin.isatty()` in
`truthlib/shellio.py:154`; the independence seam is `truthlib/cli.py:313`, and
it inspects the **session**, not the actor — so the same person in a different
terminal passes it, which makes it a structural seam rather than an identity
check. `TRUTH_HUMAN_ACK` must name the exact id it kills, so a forgotten
`export` cannot authorise future tombstones.*

## 8. Defence map: failure family → the mechanism that catches it

```mermaid
flowchart LR
    F1["a checker crashes<br/>and reads as zero"] --> D1["read the exit code FIRST;<br/>scream, never degrade"]
    F2["a gate examines nothing<br/>but reports clean"] --> D2["dark-arm rule:<br/>report what you examined"]
    F3["a bounded read supports<br/>an unbounded claim"] --> D3["QB-013 · bd remember;<br/>re-query, whole block,<br/>anchored grep + positive control"]
    F4["evidence that cannot fail"] --> D4["determinism double-run;<br/>negative control before filing"]
    F5["a fact quietly goes stale"] --> D5["invalidate-scan at commit,<br/>merge and push"]
    F6["an author blesses<br/>their own work"] --> D6["ADR-010 independence seam"]
    F7["a fact vanishes<br/>without a reason"] --> D7["ADR-049 cause + successor"]
    F8["a check exists but<br/>nothing runs it"] --> D8["ADR-048 reachability;<br/>local gate-reconcile arm"]
    F9["a gate refuses<br/>legitimate work"] --> D9["ADR-014; posture chosen<br/>per gate, not per taste"]
    F10["advisories become<br/>furniture"] --> D10["ADR-005 whisper budget;<br/>ADR-047 adoption metric"]
    F11["the checkers themselves rot"] --> D11["weekly canary:<br/>261 seeded faults, 0 missed"]

    style D11 fill:#efe
```

*`INFERRED` as a grouping; each right-hand mechanism is individually
`OBSERVED`. The bottom row is the one that makes the rest trustworthy: without
a canary, every mechanism above is a claim about itself.*

## 9. Sequences

### 9a. A claim's whole life

```mermaid
sequenceDiagram
    autonumber
    participant A as authoring session
    participant L as ledger (append-only)
    participant H as post-commit hook
    participant V as verifier session
    participant M as Michał (TTY)

    A->>L: truth claim --evidence-cmd --paths
    Note over L: status = unverified
    A->>A: determinism double-run + negative control
    V->>L: verdict agree (different session)
    Note over L: status = live
    H->>L: invalidation — a watched path changed
    Note over L: status = stale
    V->>L: reaffirm — evidence hash still matches
    Note over L: status = live again
    H->>L: invalidation — the fact really moved
    V->>L: verdict diverge
    Note over L: status = diverged, sits in the queue
    A->>L: file the successor claim
    A--xL: retraction REFUSED — no TTY (ADR-011)
    M->>L: verdict retracted --cause expired --successor
    Note over L: status = retracted; the why is readable
```

*`OBSERVED` — this is literally the path `tr-d8e5a5ba` took, ending
2026-08-04. Step 11 is not decoration: the agent-side refusal happened twice
and wrote nothing.*

### 9b. The shape of a session

```mermaid
sequenceDiagram
    autonumber
    participant S as SessionStart hook
    participant Ag as agent
    participant R as truth ready
    participant G as pre-push-checks
    participant Q as human queue

    S->>Ag: bd prime — 13 memories, incl. bounded-reads
    Ag->>Ag: STATUS.md (§3 names the next work)
    Ag->>R: truth-bd-adapter.sh | truth ready --stdin
    R-->>Ag: READY items only; dead-premise items HELD
    Ag->>Ag: work; commit (pre-commit BLOCKS on governance + INV-A)
    Ag->>G: git push
    G-->>Ag: 10 blocking arms + 8 advisory + queue note
    G->>Q: "needs your judgment: N claims, M beads"
    Note over Ag,Q: session-close.sh is the fuller gate —<br/>and nothing invokes it
```

*`OBSERVED`. Step 3 is the load-bearing one and the easiest to get wrong: the
adapter form, not bare `bd ready`.*

---

## What the atlas shows that no single script does

**The system's competence is lopsided by construction.** Ledger integrity is a
property of one file, checkable in milliseconds, so it lives on the commit
boundary and blocks. Code health costs tens of seconds and ~1,400 tests, so it
was moved off that boundary — and until 2026-08-03 was never given another one.
The fix was not new machinery; it was wiring existing checks to an existing
boundary.

**Every enforcement layer here was bought with an incident.** The dark-arm rule
exists because two upstream gates reported "clean" for weeks while examining
zero files. ADR-011 exists because an agent could otherwise launder a human
confirmation. QB-013 exists because three bounded reads published three false
findings in one day. The atlas is, read one way, an incident history with
arrows.

**The remaining hole is delivery, not design.** `session-close.sh` — the
fullest gate in the repo — is still invoked by nothing but prose, and prose is
the same mechanism as remembering.
