# L-Kitchen Design Playbook — process flow and decision trees

> Reader: designer (human or agent) laying out an L-shaped kitchen from first
> visit to production handoff | Enables: running the same phase sequence with
> the same gates every project, so two designs made months apart come out
> consistent | Update-trigger: a phase, gate number (heights, clearances), or
> decision-tree branch changes in practice

The discipline in one sentence: **heights → zones → corner → widths** — any
process that starts by placing cabinets is decorating, not designing.

---

## 1. Master pipeline

Each phase consumes the artifacts of the previous one. A phase without its
input artifact does not start (Phase 0 rule: missing input = redesign later).

```mermaid
flowchart TD
    classDef artifact fill:#eef,stroke:#88a,stroke-width:1px
    classDef gate fill:#fee,stroke:#a66,stroke-width:2px

    A0[/"IN: room + client + budget"/]:::artifact
    P0["Phase 0 — Discovery<br/>walls, diagonals, media points,<br/>appliance models, user height,<br/>handedness, budget bracket"]
    A1[/"OUT: survey pack<br/>(dims, utilities, appliance sheets)"/]:::artifact

    P1["Phase 1 — Fix working heights<br/>worktop = elbow - 100..150 mm<br/>default 850..910 = 720 carcass<br/>+ 100..150 plinth + 38 top"]
    A2[/"OUT: height parameter set<br/>(worktop, wall-unit line, tall line)"/]:::artifact

    P2["Phase 2 — Zone plan<br/>supplies > cleaning > prep > cooking<br/>sink leg vs hob leg, fridge at end"]
    A3[/"OUT: zone map + appliance positions"/]:::artifact

    P3["Phase 3 — Corner strategy<br/>blind + filler / diagonal / dead<br/>decided BEFORE any widths"]
    A4[/"OUT: corner module + filler spec"/]:::artifact

    P4["Phase 4 — Base run composition<br/>standard widths 300..900,<br/>appliances first, one filler per run<br/>at the wall end"]
    A5[/"OUT: base cabinet list per leg"/]:::artifact

    P5["Phase 5 — Wall + tall units<br/>mirror base line, hood on duct route,<br/>one continuous top line"]
    A6[/"OUT: full cabinet list"/]:::artifact

    P6["Phase 6 — Worktop + services<br/>2 segments + corner joint, cutouts,<br/>sockets, lighting, ventilation"]
    A7[/"OUT: worktop order + electrical plan"/]:::artifact

    P7["Phase 7 — Fronts + decors + gaps<br/>one decor set, 3 mm reveals,<br/>handle system decided globally"]
    A8[/"OUT: decor + hardware selections"/]:::artifact

    P8{"Phase 8 — VALIDATION GATE<br/>see section 6"}:::gate
    A9[/"OUT: approved design"/]:::artifact

    P9["Production handoff<br/>decompose to panels"]
    A10[/"OUT: cut list CSV, edging CSV,<br/>hardware BOM, drilling files DXF"/]:::artifact

    A0 --> P0 --> A1 --> P1 --> A2 --> P2 --> A3 --> P3 --> A4 --> P4 --> A5 --> P5 --> A6 --> P6 --> A7 --> P7 --> A8 --> P8
    P8 -->|pass| A9 --> P9 --> A10
    P8 -->|fail: heights or line broken| P1
    P8 -->|fail: clearance or triangle| P2
    P8 -->|fail: corner collision| P3
    P8 -->|fail: cutout or joint| P6
```

---

## 2. Phase 2 decision tree — zones and appliance placement

```mermaid
flowchart TD
    S{"Window on one leg?"}
    S -->|yes| S1["Sink under the window<br/>(drain usually agrees)"]
    S -->|no| S2["Sink on the leg closest<br/>to the drain stack"]

    S1 --> D{"Cook right- or left-handed?"}
    S2 --> D
    D -->|right| D1["Dishwasher LEFT of sink"]
    D -->|left| D2["Dishwasher RIGHT of sink"]

    D1 --> H{"Gas point / duct location?"}
    D2 --> H
    H -->|fixed| H1["Hob on the other leg,<br/>near duct, min 300 mm to wall"]
    H -->|flexible| H2["Hob on the other leg, positioned<br/>for min 600 mm prep between<br/>sink and hob"]

    H1 --> F["Fridge + oven column at the OPEN END<br/>of the longer leg — never mid-run,<br/>never in the corner"]
    H2 --> F

    F --> V{"Triangle 3.6–6.6 m total?<br/>Landings: 400 by hob,<br/>400 by fridge, 600 by sink?"}
    V -->|yes| OK(["Zone map fixed"])
    V -->|no| R["Shift zones along the legs<br/>and re-check"] --> V
```

**Hard rules encoded above:** sink-to-hob >= 600 mm worktop between them;
hob >= 300 mm from a side wall; dishwasher adjacent to sink on the
dominant-hand side; fridge with >= 400 mm set-down beside it; no traffic
path through the triangle; walkway in front of the L >= 1100 mm.

---

## 3. Phase 3 decision tree — the corner

Decided before dimensioning either run, because the corner consumes width
from **both** legs.

```mermaid
flowchart TD
    C{"Storage in the corner<br/>worth ~1500 zl of mechanism?"}
    C -->|no, tight budget| DEAD["DEAD CORNER<br/>block it off<br/>cost: ~0.8 m2 storage<br/>saving: mechanism + labour"]
    C -->|yes| T{"Floor space generous?<br/>(diagonal eats more floor)"}

    T -->|yes| DIAG["DIAGONAL CORNER + carousel<br/>best access, 45-degree worktop<br/>segment — flag it in the<br/>worktop order NOW"]
    T -->|no| B{"Budget for pull-out<br/>mechanism?"}

    B -->|yes| BLIND1["BLIND CORNER 1000–1300<br/>+ Magic Corner / LeMans"]
    B -->|no| BLIND2["BLIND CORNER 1000–1300<br/>+ plain shelves"]

    DEAD --> FILL
    DIAG --> FILL
    BLIND1 --> FILL
    BLIND2 --> FILL

    FILL["MANDATORY in every branch:<br/>50–100 mm filler strip at the internal<br/>corner on BOTH runs — else handles<br/>and drawer fronts collide"]
    FILL --> X["Never in the corner: sink, hob,<br/>dishwasher. Never two appliance<br/>doors meeting at the corner."]
```

---

## 4. Phase 4 decision tree — drawers vs doors per module

```mermaid
flowchart TD
    M{"Which zone is the module in?"}
    M -->|prep or cooking| W{"Width >= 600?"}
    M -->|sink| SD["Door cabinet + waste-sorting<br/>drawer; carcass 800–900"]
    M -->|low-use / corner-adjacent| DOOR["Door cabinet<br/>(cheapest per m2)"]

    W -->|yes| DR["DRAWER BANK — LEGRABOX or<br/>Tandembox; 900 wide with 2 tall<br/>+ 1 internal beats two door cabinets"]
    W -->|no| B2{"Budget left in bracket?"}
    B2 -->|yes| DR2["Narrow drawer cabinet<br/>(400–500) or cargo pull-out"]
    B2 -->|no| DOOR

    DR --> CHK
    DR2 --> CHK
    SD --> CHK
    DOOR --> CHK
    CHK["Check EVERY drawer bank against the<br/>corner filler: full extension + handle<br/>must clear the perpendicular front"]
```

Composition rules: standard widths only (300/400/450/500/600/800/900);
appliances placed first (they are fixed sizes); wall irregularity absorbed
by **one filler per run at the wall end, never mid-run**.

---

## 5. Phase 6 essentials — worktop and services

- Worktop = **two segments joined at the corner**; joint type (mason's mitre
  for laminate) and grain direction decided with the order, not at fitting.
- Cutouts (sink, hob) with >= 50 mm material web around them; the corner
  joint must not land on a cutout.
- Sockets every ~900 mm above worktop, none within 600 mm of the sink edge;
  dedicated circuit for induction; under-cabinet LED over the full prep run.
- Hood height per its spec: >= 650 mm electric / >= 750 mm gas above hob.

---

## 6. Phase 8 — validation gate (run every item, every time)

```mermaid
flowchart TD
    G1{"Heights consistent<br/>across both legs?"} -->|no| F1["back to Phase 1"]
    G1 -->|yes| G2{"Corner fillers present<br/>on BOTH runs?"}
    G2 -->|no| F2["back to Phase 3"]
    G2 -->|yes| G3{"Door/drawer collision walk-through<br/>clean at corner and room door?"}
    G3 -->|no| F3["back to Phase 3 or 4"]
    G3 -->|yes| G4{"Appliance cutouts match<br/>actual model sheets?"}
    G4 -->|no| F4["back to Phase 0 inputs"]
    G4 -->|yes| G5{"Triangle + landings still legal<br/>after all width changes?"}
    G5 -->|no| F5["back to Phase 2"]
    G5 -->|yes| G6{"Plinth line unbroken?<br/>Top line continuous?"}
    G6 -->|no| F6["back to Phase 4 or 5"]
    G6 -->|yes| G7{"Worktop joint clear of cutouts?<br/>Gas/hood distances legal?"}
    G7 -->|no| F7["back to Phase 6"]
    G7 -->|yes| PASS(["APPROVED —<br/>decompose to production"])
```

---

## 7. Mapping to the pipeline in this repo

| Playbook step | Repo home |
|---|---|
| Phase 0/7 decor selection | `krono-compositor-mvp` (first-visit previews), `catalog` (decors, pairings) |
| Phase 2–5 layout | `home_builder_5` (external Blender addon) → `home-builder-adapter` extraction |
| Phase 8 mechanical checks | `kuchnie_core.validator` / `validate_rows` (candidates to encode the gate) |
| Production handoff | `kuchnie_core.decompose()` → cut list / edging CSV → `kitchen-erp` BOM + cost → `kitchen-cam` drilling DXF |

The gate numbers in this playbook (heights, clearances, filler widths) are
design-practice values, not repository facts — they carry no ledger ids by
design. If any of them become encoded in code (e.g. the validator learns the
corner-filler rule), cite the implementing spec from here.
