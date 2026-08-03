# Attested claims triage — the command-less residue (2026-08-04)

> Reader: whoever decides authoring policy for the truth ledger — what may be
> filed as a claim at all | Enables: deciding whether command-less claims get a
> mandatory TTL, get restated with a command, or are accepted as named
> permanent debt — and knowing which individual ids each choice touches |
> Update-trigger: the evidence allowlist admits a test runner, an intake gate
> constrains command-less claims, or the ledger is re-measured after any of the
> levers below is pulled

> **STATUS: MEASUREMENT + PROPOSAL.** Every number below carries the command
> that produces it. The taxonomy in §3 is my reading of 42 claim texts read
> unfiltered; the per-claim metrics under it are mechanical. Nothing here has
> been filed, committed, or applied — this document is the argument, not the
> change.

---

## TL;DR

1. **42 claims carry no evidence command** — exactly the 41 `UNVERIFIED` plus
   the 1 `INFERRED` claim. Every one of the 177 `VERIFIED` claims has a
   command, because the schema forces it. "Command-less" and "not VERIFIED"
   are the same set, not two overlapping ones.
2. **They are now the *majority* of the remaining human upkeep.** All-time they
   account for 100 of 293 human re-checks (34%). But since `reaffirm` landed
   (first mechanical verdict `2026-07-23T20:30:38`), they account for **61 of
   70 — 87%**. Reaffirm cleared the command-carrying half and left this residue
   standing alone.
3. **Every one of those 100 re-checks came from a path watch. Zero came from a
   TTL.** Of 128 invalidations on the 42: 124 `evidence paths changed`, 4
   `anchor unreachable`, 0 TTL. The 11 command-less claims that carry *no*
   `evidence_paths` have cost **zero** invalidations and **zero** human
   re-checks across the whole ledger.
4. So the lever is not "give them a TTL". A TTL does not suppress the path
   check — `INVALIDATORS` runs `_ttl_expired` first and `_evidence_paths_touched`
   anyway. The lever is **`evidence_paths` must not appear on a claim that has
   no command.**

---

## 1. How the 42 were identified

`.truth/claims.jsonl` is folded with the repo's own kernel (no reimplementation),
first-claim-wins per ADR-006, and a claim is *command-less* when
`payload.evidence.command` is absent or empty.

```bash
python3 - <<'PY'
import json, sys, collections
sys.path.insert(0, '.')
from truthlib.kernel import fold
EV = [json.loads(l) for l in open('.truth/claims.jsonl') if l.strip()]
folded, _ = fold(list(enumerate(EV)))
nc = [(c, e) for c, e in folded.items()
      if not (e["claim"]["payload"].get("evidence") or {}).get("command")]
print("command-less:", len(nc), "of", len(folded))
print("by class:",  collections.Counter(e["claim"]["payload"]["evidence_class"] for _, e in nc))
print("by status:", collections.Counter(e["status"] for _, e in nc))
print("by tier:",   collections.Counter(e["claim"]["payload"]["cost_tier"] for _, e in nc))
print("carries a TTL:",   collections.Counter(bool(e["claim"]["payload"].get("ttl_days")) for _, e in nc))
print("carries paths:",   collections.Counter(bool(e["claim"]["payload"].get("evidence_paths")) for _, e in nc))
print("POSITIVE CONTROL — claims WITH a command:",
      sum(1 for e in folded.values() if (e["claim"]["payload"].get("evidence") or {}).get("command")))
PY
```

```
command-less: 42 of 219
by class:  {'UNVERIFIED': 41, 'INFERRED': 1}
by status: {'live': 22, 'retracted': 12, 'stale': 6, 'cannot_verify': 2}
by tier:   {'P2': 37, 'P1': 5}
carries a TTL:   {False: 41, True: 1}
carries paths:   {True: 31, False: 11}
POSITIVE CONTROL — claims WITH a command: 177        # 177 + 42 = 219 ✓
```

The positive control is the sum check demanded by QB-013: the two branches
partition the fold exactly, so "42" is not a filtered read that missed a shape.
A second, independent control over the raw file (field-anchored on `kind`, not
a substring) reports the same 219 distinct ids / 177 / 42 and confirms there
are no duplicate claim ids to fold away.

**Finding 1.** Command-less ≡ non-VERIFIED. The schema's VERIFIED branch
requires `evidence`, so there is no third category of "VERIFIED but the command
went missing". Any policy about command-less claims is a policy about the
`--class UNVERIFIED` filing verb, and nothing else.

---

## 2. What they cost

### 2.1 Reproducing the staling ledger

A *resolved staling* is an invalidation on a claim followed, in fold order, by
a verdict on that claim. A *false alarm* is one resolved by `agree`. It is
*mechanical* when the verdict's basis is exactly ADR-030's fixed string
`reaffirm: hash-match, no judgment re-run`; otherwise a human read the fact and
agreed.

```bash
python3 - <<'PY'
import json, sys, collections
sys.path.insert(0, '.')
from truthlib.kernel import fold_key
from truthlib.registry import VERDICT_STATUS
from truthlib.evidence import screen_evidence_command
def lst(p):
    return [l.strip() for l in open(p) if l.strip() and not l.startswith('#')]
ALLOW, DENY = lst('.truth/evidence-allow'), lst('.truth/evidence-deny')
EV = [json.loads(l) for l in open('.truth/claims.jsonl') if l.strip()]
ordered = [e for _, e in sorted(enumerate(EV), key=fold_key)]
REAFFIRM = "reaffirm: hash-match, no judgment re-run"
claims, status, open_st, agreed, out = {}, {}, {}, set(), []
def why(cid, inv):
    p = claims[cid]["payload"]; ev = p.get("evidence") or {}
    if (inv or {}).get("payload", {}).get("reason_code") == "ttl": return "ttl"
    if not ev.get("command"):        return "no-command"
    if ev.get("screened") is False:  return "unscreened"
    if screen_evidence_command(ev["command"], ALLOW, denylist=DENY): return "screen-refuses"
    return "runnable" if cid in agreed else "never-agreed"
for e in ordered:
    k, p = e["kind"], e.get("payload", {})
    if k == "claim":
        if e["id"] in claims: continue
        claims[e["id"]] = e; status[e["id"]] = "unverified"
    elif k == "invalidation" and p.get("claim") in claims:
        c = p["claim"]
        if status[c] == "retracted": continue
        status[c] = "stale"; open_st[c] = e
    elif k == "verdict" and p.get("claim") in claims:
        c = p["claim"]
        if status[c] == "retracted": continue
        status[c] = VERDICT_STATUS[p["verdict"]]
        if c in open_st:
            out.append(dict(claim=c, verdict=p["verdict"], ts=e["ts"],
                            mech=p.get("basis", "") == REAFFIRM, why=why(c, open_st.pop(c))))
        if p["verdict"] == "agree": agreed.add(c)
a = [r for r in out if r["verdict"] == "agree"]
h = [r for r in a if not r["mech"]]
print("resolved stalings:", len(out), "| by verdict:", dict(collections.Counter(r["verdict"] for r in out)))
print("false alarms (agree):", len(a), "| mechanical:", len(a) - len(h), "| HUMAN:", len(h))
print("human re-checks by why the machine could not help:",
      dict(collections.Counter(r["why"] for r in h)))
json.dump(out, open('/tmp/resolved.json', 'w'))
PY
```

```
resolved stalings: 630 | by verdict: {'agree': 555, 'diverge': 69, 'retracted': 4, 'cannot_verify': 2}
false alarms (agree): 555 | mechanical: 262 | HUMAN: 293
human re-checks by why the machine could not help:
  {'runnable': 172, 'no-command': 100, 'never-agreed': 15, 'screen-refuses': 6}
```

**Note on the brief's figures.** The task set this up as 608 resolved stalings
/ 530 false alarms / 288 human, split 188 / 95 / 5. My reproduction gives
630 / 555 / 293, split 172 + 15 / 100 / 6. The *shape* is identical (over-sensitive
recipes ≈ 2/3, command-less ≈ 1/3, screen refusals ≈ 2%) and the residual is
small, but the definitions are not byte-identical — the brief's measurement is
not in the repo and I could not re-run it (`grep -rn "608" docs/` and a repo-wide
search for "530" return nothing on this subject). Where the two disagree I use
mine, because mine is reproducible from the command above. Treat "95" and "100"
as the same finding.

**Finding 2.** 100 of 293 all-time human re-checks (34%) come from the 42
command-less claims.

### 2.2 The number that actually matters: the post-`reaffirm` era

```bash
python3 -c "
import json, collections
res  = json.load(open('/tmp/resolved.json'))
rows = json.load(open('/tmp/rows.json'))           # see §2.3
NC   = {r['id'] for r in rows}
cut  = min(r['ts'] for r in res if r['mech'])
print('first mechanical reaffirm verdict:', cut)
for lab, pred in (('PRE ', lambda t: t < cut), ('POST', lambda t: t >= cut)):
    h  = [r for r in res if r['verdict']=='agree' and not r['mech'] and pred(r['ts'])]
    m  = [r for r in res if r['verdict']=='agree' and     r['mech'] and pred(r['ts'])]
    hn = [r for r in h if r['claim'] in NC]
    print(f'{lab}: agree-stalings={len(h)+len(m)} mechanical={len(m)} human={len(h)} '
          f'human-on-command-less={len(hn)} ({100*len(hn)/max(1,len(h)):.0f}% of human)')
"
```

```
first mechanical reaffirm verdict: 2026-07-23T20:30:38.852512+00:00
PRE : agree-stalings=223 mechanical=0   human=223 human-on-command-less=39 (17% of human)
POST: agree-stalings=332 mechanical=262 human=70  human-on-command-less=61 (87% of human)
```

**Finding 3 (the surprise).** Before reaffirm, command-less claims were 17% of
human upkeep and easy to ignore. After reaffirm they are **87%**. The
automation did not reduce this class at all — it removed everything *around* it.
Over the 12 days 2026-07-23 → 2026-08-03 the residual human load is ≈5 re-checks
per day, and nearly all of it is this residue. This is the number that turns an
academic taxonomy question into an operating cost.

### 2.3 Per-claim detail, and where the mass sits

```bash
python3 - <<'PY'
import json, sys, collections
sys.path.insert(0, '.')
from truthlib.kernel import fold
EV = [json.loads(l) for l in open('.truth/claims.jsonl') if l.strip()]
folded, _ = fold(list(enumerate(EV)))
res = json.load(open('/tmp/resolved.json'))
human = collections.Counter(r["claim"] for r in res if r["verdict"] == "agree" and not r["mech"])
inval = collections.Counter(e["payload"]["claim"] for e in EV if e["kind"] == "invalidation")
verd  = collections.Counter(e["payload"]["claim"] for e in EV if e["kind"] == "verdict")
rows = []
for cid, e in folded.items():
    p = e["claim"]["payload"]
    if (p.get("evidence") or {}).get("command"): continue
    rows.append(dict(id=cid, status=e["status"], tier=p["cost_tier"], ttl=p.get("ttl_days"),
                     paths=len(p.get("evidence_paths") or []), inval=inval[cid],
                     verd=verd[cid], human=human[cid], text=p["text"]))
rows.sort(key=lambda r: (-r["human"], -r["inval"]))
json.dump(rows, open('/tmp/rows.json', 'w'))
for r in rows:
    print(f"{r['id']} {r['status']:<13} {r['tier']} ttl={str(r['ttl']):<4} "
          f"paths={r['paths']:<2} inv={r['inval']:<3} vd={r['verd']:<3} hum={r['human']:<3} {r['text'][:70]}")
print("TOTALS  claims", len(rows), "invalidations", sum(r['inval'] for r in rows),
      "verdicts", sum(r['verd'] for r in rows), "human", sum(r['human'] for r in rows))
PY
```

Abridged (full ordering is the command's output; totals are exact):

| id | status | tier | ttl | #paths | #inval | #verdicts | **human re-checks** | about |
|---|---|---|---|---|---|---|---|---|
| `tr-b2e3dbff` | live | P2 | — | 1 | 11 | 13 | **10** | `decompose_dolna_legrabox` emits TOP + PLINTH panels |
| `tr-3ef7b607` | live | P2 | — | 1 | 11 | 13 | **10** | confirmat drills + HDF grooves on legrabox sides |
| `tr-6692cbe7` | live | P1 | — | 3 | 10 | 15 | **10** | ERP Variants re-derive rozrys/CNC/BOM; *pinned by test* |
| `tr-19a7f6b3` | stale | P2 | — | 1 | 12 | 11 | **9** | UC-1 fully dressed in `docs/specs/use-cases.md` |
| `tr-0e13ba64` | live | P2 | — | 5 | 10 | 12 | **9** | drawer-box PanelRoles bucket into `drawer_box_m2` |
| `tr-e51ef4fd` | live | P1 | — | 2 | 9 | 13 | **9** | ERP `Project` spine fields + `transition_stage` |
| `tr-c87a68f9` | live | P2 | — | 3 | 6 | 9 | **6** | Offers/ACCEPT lock variants; *pinned by test* |
| `tr-ee15599a` | stale | P2 | — | 3 | 7 | 7 | **5** | LEGRABOX runner screw ops single-sourced |
| `tr-6ccd4a63` | cannot_verify | P1 | — | 1 | 7 | 7 | **5** | UC-2 dressed, backlog confined to 2a/8a |
| `tr-4afef6fb` | live | P2 | — | 4 | 5 | 8 | **5** | quote header estimate-grade badge; *pinned by test* |
| … 11 more with 1–4 each … | | | | | | | **21** | |
| **21 claims with 0 human re-checks** | | | | | | | **0** | |
| **TOTAL (42 claims)** | | | | **31 watched** | **128** | **213** | **100** | |

Concentration:

```bash
python3 -c "
import json; rows=json.load(open('/tmp/rows.json'))
h=sorted((r['human'] for r in rows), reverse=True); t=sum(h); c=0
for i,n in enumerate(h,1):
    c+=n
    if i in (1,3,5,6,10,12,21): print(f'top-{i:2d} claims -> {c:3d}/{t} ({100*c/t:.0f}%)')"
```

```
top- 1 ->  10/100 (10%)      top- 6 ->  57/100 (57%)
top- 3 ->  30/100 (30%)      top-10 ->  78/100 (78%)
top- 5 ->  48/100 (48%)      top-12 ->  86/100 (86%)
                             top-21 -> 100/100 (100%)
```

**Finding 4.** Half the load is six claims. All of the load is twenty-one
claims. The other twenty-one command-less claims have never cost a human
anything. This is not a class-wide problem; it is a short, named list.

### 2.4 What actually stales them — and why a TTL would not have helped

```bash
python3 -c "
import json, collections
NC={r['id'] for r in json.load(open('/tmp/rows.json'))}
c=collections.Counter()
for l in open('.truth/claims.jsonl'):
    e=json.loads(l)
    if e['kind']=='invalidation' and e['payload']['claim'] in NC:
        p=e['payload']; c[p.get('reason_code') or p.get('reason','')[:30]]+=1
print(dict(c))"
```

```
{'evidence paths changed': 124, 'anchor unreachable (history re': 4}
```

Zero TTL invalidations, because only one of the 42 carries a TTL at all
(`tr-57bd65bb`, `ttl_days: 365`, filed 2026-07-12 — not yet expired, 0
invalidations, 0 human re-checks).

And the two mechanisms do not substitute for one another. In
`truthlib/policy.py`:

```python
INVALIDATORS = (_ttl_expired, _anchor_unreachable, _evidence_paths_touched)
```

`decide_invalidation` returns the *first* hit, so on a claim that carries both,
TTL wins only in the window after expiry; before that, every touch of a watched
path still fires `_evidence_paths_touched`. Ledger-wide, 17 of the 20 TTL'd
claims also carry `evidence_paths` — coexistence is the norm, not the exception:

```bash
python3 -c "
import json,sys; sys.path.insert(0,'.')
from truthlib.kernel import fold
EV=[json.loads(l) for l in open('.truth/claims.jsonl') if l.strip()]
f,_=fold(list(enumerate(EV)))
t=[e for e in f.values() if e['claim']['payload'].get('ttl_days')]
print('claims with a TTL:', len(t), 'of', len(f),
      '| of those, also path-watched:', sum(1 for e in t if e['claim']['payload'].get('evidence_paths')))"
```

```
claims with a TTL: 20 of 219 | of those, also path-watched: 17
```

**Finding 5.** The upkeep driver is `evidence_paths`, not the missing command.
The 11 command-less claims *without* paths have produced 0 invalidations and 0
human re-checks; the 31 *with* paths have produced 128 and 100. The missing
command is why nothing can heal the staling; the watch is why the staling
happens at all.

### 2.5 They are load-bearing, so retirement is not free

```bash
python3 -c "
import json, collections
EV=[json.loads(l) for l in open('.truth/claims.jsonl') if l.strip()]
rows={r['id']:r for r in json.load(open('/tmp/rows.json'))}
live20={i for i,r in rows.items() if r['status']!='retracted' and r['paths']>0}
edges=set()
for e in EV:
    if e['kind']=='premise': edges.add((e['payload']['claim'], e['payload']['issue']))
    if e['kind']=='issue':
        for c in e['payload'].get('premises') or []: edges.add((c, e['id']))
print('command-less claims cited as a premise:', len({c for c,_ in edges if c in rows}), 'of', len(rows))
sub={x for x in edges if x[0] in live20}
print('still-watching command-less claims:', len(live20))
print('premise edges to redirect if all 20 retire:', len(sub), 'across', len({i for _,i in sub}), 'issues')"
```

```
command-less claims cited as a premise: 17 of 42
still-watching command-less claims: 20
premise edges to redirect if all 20 retire: 24 across 22 issues
```

They also hold work *today*. Three of the four open/claimed issues with a broken
premise are broken by a command-less claim nobody can mechanically revive
(`wk-a898481e`, `wk-b669f4f5` on `tr-87282b5d` + `tr-89acfc89`; `wk-b29f670a`
on `tr-eb6f5ec7`) — verified by joining `fold_issues` against `premise_check`
over every non-closed, non-cancelled issue.

And they are cited in prose across 15 live documents (`docs/specs/use-cases.md`,
`docs/specs/purchasing-variants.md`, `docs/specs/process-coverage.md`,
`docs/specs/conformance-join.md`, `docs/specs/walking-skeleton-d60.md`,
`docs/pattern-conformance.md`, `docs/adr/014`, `docs/adr/034`, `STATUS.md`,
`CHANGELOG.md`, three kitchen-erp specs, `kuchnie-core/docs/specs/l-layout-model.md`,
and this review's siblings) — so a bare retraction trips the ADR-036 tombstone
citation gate. Retirement must go through ADR-049 `--cause restated --successor`
and ADR-013 premise supersede, never `retract` alone.

---

## 3. The taxonomy — five kinds, assigned by reading all 42 texts

The 42 texts were read in full (unfiltered dump of every `text` field), not
sampled. Assignment is my judgment; the metrics per kind are mechanical. The
id lists are exhaustive and disjoint — the script below asserts 42 assigned,
0 missing, 0 duplicated, and regenerates the table (run after §2.3):

```bash
python3 - <<'PY'
import json
rows = {r['id']: r for r in json.load(open('/tmp/rows.json'))}
K = {
"K1 greppable structure, command never written":
 ["tr-19a7f6b3","tr-6ccd4a63","tr-c440ff7a","tr-c413667b","tr-e51ef4fd","tr-eb6f5ec7"],
"K2 behavioural, honest oracle is a test run":
 ["tr-b2e3dbff","tr-3ef7b607","tr-6692cbe7","tr-0e13ba64","tr-c87a68f9","tr-ee15599a",
  "tr-4afef6fb","tr-76d6de33","tr-3bb325f8","tr-167da3d5","tr-b538d31a","tr-65aa5969","tr-a081d9c9"],
"K3 self-obsoleting snapshot / defect description":
 ["tr-eaeed5fe","tr-88fb2941","tr-a6c202c2","tr-3a97dc10","tr-847d40f8","tr-72b4e836",
  "tr-a21ce0b0","tr-12d9a3a6","tr-a8777c48","tr-89acfc89","tr-87282b5d","tr-d0610cb4","tr-747adf10"],
"K4 episodic completion attestation (unwatched)":
 ["tr-544e72ca","tr-08ad27d2","tr-09ed38fd","tr-cad8d45a","tr-d4c30969","tr-d20f7370",
  "tr-277c9b54","tr-9e27d225"],
"K5 outside-world testimony": ["tr-57bd65bb","tr-09ea12aa"],
}
seen = set()
for k, v in K.items():
    seen |= set(v)
    print(f"{k:50} n={len(v):2} watched={sum(1 for i in v if rows[i]['paths']>0):2} "
          f"non-retracted={sum(1 for i in v if rows[i]['status']!='retracted'):2} "
          f"inval={sum(rows[i]['inval'] for i in v):3} human={sum(rows[i]['human'] for i in v):3}")
assert len(seen) == len(rows) == 42 and not set(rows) - seen
assert len([i for v in K.values() for i in v]) == len(seen)   # disjoint
print("42 assigned, 0 missing, 0 duplicated | TOTAL human:", sum(r['human'] for r in rows.values()))
PY
```

| Kind | n | watched | non-retracted | invalidations | **human re-checks** |
|---|---|---|---|---|---|
| **K1** greppable structure, command simply never written | 6 | 6 | 5 | 40 | **31** |
| **K2** behavioural property whose honest oracle is a *test run* | 13 | 11 | 13 | 65 | **59** |
| **K3** self-obsoleting snapshot / defect description | 13 | 13 | 3 | 22 | **9** |
| **K4** episodic completion attestation, unwatched | 8 | 0 | 7 | 0 | **0** |
| **K5** outside-world testimony | 2 | 1 | 2 | 1 | **1** |
| | **42** | **31** | **30** | **128** | **100** |

**K1 — the command was simply never written.** `tr-19a7f6b3`, `tr-6ccd4a63`,
`tr-c440ff7a`, `tr-c413667b`, `tr-e51ef4fd`, `tr-eb6f5ec7`. Each asserts a
structure a `grep`/`ls` on its own watched paths would decide: "UC-1 is fully
dressed in `docs/specs/use-cases.md`", "`exercises/walking-skeleton-d60/`
contains the hand reference", "ERP's `Project` model has stage/contact/lifecycle
fields". Nothing prevented a command. These are the honest targets of
"retire and re-file with a command".

**K2 — the oracle is a test, and the evidence screen deliberately refuses to
run tests.** `tr-b2e3dbff`, `tr-3ef7b607`, `tr-6692cbe7`, `tr-0e13ba64`,
`tr-c87a68f9`, `tr-ee15599a`, `tr-4afef6fb`, `tr-76d6de33`, `tr-3bb325f8`,
`tr-167da3d5`, `tr-b538d31a`, `tr-65aa5969`, `tr-a081d9c9`. Nine of these say
so in their own text ("pinned by test", "pinned by tests in
`kuchnie-core/tests/test_buildability.py`"). This is a *structural* gap, not
laziness:

```bash
grep -v '^#' .truth/evidence-allow | grep -v '^$' | tr '\n' ' '   # no runner
grep -v '^#' .truth/accept-allow  | grep -v '^$' | tr '\n' ' '    # bash python3 .venv/bin/python …
```

`.truth/evidence-allow` ships no test runner *on purpose* ("a test runner
executes repository code, which is exactly the arbitrary-execution channel being
screened"), and `bash` is on the ADR-022 deny baseline. `.truth/accept-allow`
ships `bash`, `python3`, `.venv/bin/python` — so an ADR-014 **acceptance oracle
on a `wk-` issue** may run the suite, but a **claim** may never cite it. A
behavioural fact therefore cannot carry honest evidence in this system. K2 is
59 of the 100 re-checks — the largest bucket, and the one no amount of authoring
care fixes.

**K3 — facts engineered to become false.** `tr-eaeed5fe`, `tr-88fb2941`,
`tr-a6c202c2`, `tr-3a97dc10`, `tr-847d40f8`, `tr-72b4e836`, `tr-a21ce0b0`,
`tr-12d9a3a6`, `tr-a8777c48`, `tr-89acfc89`, `tr-87282b5d`, `tr-d0610cb4`,
`tr-747adf10`. Five of them are the same sentence re-filed as a counter moved
— "the signature review has a mechanical tripwire: 60-arch-smells (**six**
detectors … 8 true findings at baseline)" → eight/15 → ten/17 → eleven/19 →
eleven, baseline-diffed. Others describe a defect the author was about to fix
("kitchen-erp core has a model-service import cycle"). **AGENTS.md already
forbids this**: *"Do NOT file a fact that describes a defect you are about to
fix."* The data shows the rule violated 13 times and then working — 10 of the 13
are already retracted, at a cost of 22 invalidations, 9 human re-checks and 13
tombstones. No new machinery is owed here; the existing rule needs enforcement,
not extension.

**K4 — episodic completion attestations.** `tr-544e72ca`, `tr-08ad27d2`,
`tr-09ed38fd`, `tr-cad8d45a`, `tr-d4c30969`, `tr-d20f7370`, `tr-277c9b54`,
`tr-9e27d225`. "Dark-triage executed 2026-07-16", "the ruff correctness baseline
is burned down to zero findings", "the CabinetGeometry delete-or-wire decision is
executed as delete". All eight carry **no paths and no TTL**, so they have cost
exactly zero upkeep — and will never be questioned again. They are the mirror
image of the problem: not expensive, but permanently unfalsifiable. "The ruff
baseline is at zero findings" is a claim about *today* that the ledger will keep
asserting in 2027.

**K5 — outside-world testimony, the shape the doctrine actually prescribes.**
`tr-57bd65bb` (the Nero Computing System / e-rozkroj column-mapping import
format — a third-party product's behaviour, `INFERRED`, `ttl_days: 365`, no
paths, 0 invalidations, 0 re-checks) and the hybrid `tr-09ea12aa` ("the drafts
are posted upstream" — a GitHub state no path can watch, bolted onto a
repo-watchable clause, 1 re-check).

**Finding 6 (the second surprise).** AGENTS.md's rule for command-less claims is
*"Do file facts about the world outside the repo … Use `--ttl-days N` instead of
`--paths`."* Exactly **one** of the 42 obeys it — and it is the only one that has
cost nothing. The other 41 are repo-internal facts wearing testimony's record
type. The class is not "human attestation"; it is **VERIFIED claims filed
without doing the verification work**, plus a small tail of genuine testimony.

---

## 4. Levers

### Rejected: "give command-less claims a mandatory TTL" (as stated)

**Rejected on §2.4.** 0 of 128 invalidations on this class were TTL-driven; 100
of 100 human re-checks came from `evidence_paths`. Because `INVALIDATORS`
evaluates TTL and the path watch independently, stamping a TTL on the current 20
still-watching claims changes *nothing* about their staling rate — it only adds a
re-file obligation on top (ADR-019's amendment is explicit: an expired claim is
**re-filed, not re-verified**, because a re-agree is re-staled by the next scan
forever). Cost: 20 claims × one re-file per TTL period, plus 24 premise-edge
redirects each cycle. Buys: 0 of the 100. This lever is a strict loss as worded.

### Accepted: "no command ⇒ no `evidence_paths`, and a TTL is mandatory"

The same lever, inverted. A claim filed without an evidence command may not
carry `evidence_paths`; it must carry `ttl_days` instead. That is precisely
AGENTS.md's existing rule, promoted from prose to a gate.

- **Buys:** all 100 human re-checks, all 128 invalidations, and the 24
  premise-edge churn — because the entire cost is path-driven. Direct evidence:
  the 11 command-less claims already in this shape have cost 0 and 0.
- **Costs:** the fact stops being watched, so a genuine change goes unnoticed
  until expiry. That is a real loss of coverage and should be stated plainly —
  but note what is being given up: the watch on a command-less claim never
  *detected* anything either. It fired 128 times and a human agreed the fact
  still held 100 of those times; it produced zero mechanical detections, because
  there is nothing to compare against.
- **Where to put it:** one `pre-execution` row in `INTAKE_GATES`
  (ADR-034 — "a later gate ADR adds a row, not a paragraph"), reusing ADR-032's
  existing default-TTL machinery verbatim (`DEFAULT_OVERRIDE_TTL_DAYS = 30`,
  `ttl_default: true`, one advisory line in the CC-1 block). No schema change,
  no fold change, no new record kind.
- **Side benefit:** it fixes K4. The eight unwatched attestations currently
  never decay; a mandatory TTL converts "the ruff baseline is at zero findings,
  forever" into a dated assertion that expires and is re-asked. **This is the
  only place the TTL half of the lever buys anything on its own.**

### Accepted, narrowly: "retire by re-filing with a command" — for K1 only

- **Applies to:** K1's 5 still-live ids (`tr-19a7f6b3`, `tr-6ccd4a63`,
  `tr-c413667b`, `tr-e51ef4fd`, `tr-eb6f5ec7`) — 31 of the 100 re-checks.
- **Costs:** 5 evidence commands that must survive the ADR-035 exit gate and
  the G6 double-run; 5 `verdict --retract --cause restated --successor` records;
  11 premise edges to redirect (ADR-013). Perhaps a day.
- **Buys:** those claims stop needing a human — `reaffirm` picks them up.
- **Rejected for K2** (13 claims, 59 re-checks): the honest command is
  `pytest`, and admitting a runner to `.truth/evidence-allow` would convert the
  read-only evidence screen into arbitrary execution in verifier sessions — the
  exact thing ADR-009/021/022/029 exist to prevent, and the file says so in its
  own header comment. A `grep` proxy for "the decomposer emits a PLINTH panel"
  is a weaker oracle *presented as* verification, which is worse than an honest
  UNVERIFIED. **Do not pull this lever for K2.**

### Accepted: "named permanent attested debt" — for K5, and for K2 reshaped

- **K5** (`tr-57bd65bb`, `tr-09ea12aa`): already costs 1 re-check total. Accept
  as-is; split `tr-09ea12aa`'s repo-watchable clause from its GitHub clause if it
  ever becomes annoying.
- **K2**: the correct move is not a command and not a TTL-with-paths — it is to
  stop caching the fact. AGENTS.md: *"Never write a separate doc that restates
  what the code does. If the code is clear and tested, it IS the documentation."*
  A behavioural fact already pinned by a passing test is a **cache of that
  test**, and every one of its 65 invalidations is that cache going stale. Nine
  of the 13 say "pinned by test" in their own text — they name their own
  redundancy. Retire them to testimony shape (no paths, TTL), or, where the test
  is the whole content, retract with `--cause restated` pointing at the test
  rather than at another claim.

### Rejected: any new machinery

The doctrine's own open question (`docs/reviews/agentic-verification-doctrine-2026-08-03.md`
§7) says that if auto-reaffirm does not flatten the curve, the answer is **fewer
claims, not more machinery**. §2.2 shows reaffirm *did* flatten its half — 262
mechanical agrees, human load down from 223 to 70 — and that what remains is a
class automation cannot touch by construction. There is no third automation to
build. Every lever above is a subtraction: one intake refusal, and a shorter
ledger.

---

## 5. Proposed policy, in one paragraph

**A claim filed without an evidence command is testimony, and testimony has a
shape: no `evidence_paths`, a mandatory `ttl_days`.** Add it as one
`pre-execution` row in the ADR-034 gate table, refusing `--paths` on a
command-less filing and defaulting `ttl_days` to 30 with `ttl_default: true`
exactly as ADR-032 already does for scope overrides; no schema, fold, or status
change. Then work the existing 20 still-watching claims by kind, not in bulk:
re-file K1's five with a real `grep` command (ADR-049 `--cause restated
--successor`, 11 premise edges to redirect); re-shape K2's eleven watched ones
as TTL'd testimony *without* admitting a test runner to `.truth/evidence-allow`
— a behavioural fact whose only honest oracle is `pytest` belongs in the test
suite and in an ADR-014 acceptance oracle, not in a claim; let K3's three
survivors die on their own beads and enforce the AGENTS.md rule that forbade
them; accept K4 and K5 as permanent attested debt, now dated by the mandatory
TTL so they expire instead of asserting 2026-07-16's world forever. Expected
effect, measured against §2: the 100 human re-checks go to ~0 and the current
≈5/day residual load — 87% of everything left after reaffirm — disappears, at
the price of losing a path watch that has never once detected anything on this
class.

---

## 6. What I could not determine

- **The brief's 608 / 530 / 288 / 188-95-5 figures.** Not reproducible: the
  measurement is not committed anywhere in the repo (searched repo-wide for the
  literals, and `docs/reviews/` for the subject). My §2.1 reproduction gives
  630 / 555 / 293 / 172+15-100-6 — same shape, different definition. If the
  original definition matters, it needs to be recorded next to the number.
- **Whether a K1/K2 claim's grep command would actually *fail* when the sentence
  is false.** Deciding that requires writing all five commands and mutation-testing
  them (the `truth mutate` harness the doctrine lists as item 5, unbuilt). Until
  then, "K1 could trivially have had a command" is my reading of the sentences,
  not a demonstrated fact — treat it as INFERRED.
- **Retraction cause for this class.** All 12 retractions of command-less claims
  predate ADR-049 and record no `cause`, so I cannot say whether they died
  `fixed`, `wrong`, or `expired`. Ledger-wide only 2 of 77 retractions carry a
  cause. The recent kuchnie-m0m mortality measurement bears on the K3 question
  and was not re-derived here.
- **Whether the 42's watched paths are hot for structural reasons or because of
  one busy fortnight.** Invalidation counts (11–12 on `catalog.py` and
  `use-cases.md`) are all inside a 26-day ledger; a longer window might rank
  them differently.

---

## 7. One question for the owner

Behavioural facts pinned by tests (K2 — 13 claims, 59 of 100 re-checks) cannot
carry honest evidence while the evidence screen refuses test runners, and the
screen refuses them for a good reason. Should such facts be **allowed in the
ledger at all**, or should the rule become "if a test pins it, the test is the
record and no claim is filed"? Everything else in §5 follows from that answer.
