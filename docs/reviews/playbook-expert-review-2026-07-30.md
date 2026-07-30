# Expert review — L-kitchen design playbook (trade-practice pass, 2026-07-30)

> Reader: the operator deciding which playbook changes to ratify (the
> playbook is operator-owned; ADR-035 decisions need a superseding decision,
> not a silent edit) | Enables: walking one ratification table and saying
> yes/no per row instead of re-debating trade practice line by line |
> Update-trigger: a finding is ratified into the playbook or explicitly
> refused (mark the row), or the playbook gains/loses a phase this review
> mirrors

**Honesty framing.** The persona behind this review is model-distilled
trade practice — the accumulated defaults, validations and libraries of
PRO100, Polyboard, Winner Flex, TopSolid'Wood and PaletteCAD, plus European
fitting practice — not a certification and not bench time. Where this
review and the operator's own hands disagree, the hands win; where a number
here and the measured room disagree, the room wins. Nothing below is
applied: these are proposals for ratification. Pro-tool references are
cited as evidence that a practice is industry-standard, and flagged where a
tool default is a lowest-common-denominator rather than best practice.

Sources consulted: `docs/l-kitchen-design-playbook.md` (the subject),
`docs/adr/035-playbook-operating-decisions.md` (ratified boundaries),
`kitchen-erp/docs/survey-protocol.md` §6.1 (advisories already surfaced),
bd `kuchnie-uro` (four open trade-practice notes),
`kitchen-erp/docs/specs/height-parameter-set.md`,
`kuchnie-core/docs/specs/l-layout-model.md`, UC-11 in
`docs/specs/use-cases.md`.

---

## §1 Master pipeline (playbook section 1)

### [P-1] KEEP — heights → zones → corner → widths is the correct spine

**Playbook says:** "heights → zones → corner → widths — any process that
starts by placing cabinets is decorating, not designing."

**Trade practice says:** confirmed without reservation. A fitter who has
re-scribed a run because the worktop line was decided after the cabinets
were ordered does not need convincing. The phase order also matches how a
measured room actually constrains a design: heights are body-driven
(fixed earliest), zones are media-driven, the corner consumes width from
both legs (so it must precede widths), and widths are what is left.

**How the pro tools encode it:** PRO100 and Winner Flex set installation
heights (worktop, wall-unit line) at job level before a cabinet is placed;
Polyboard cascades job parameters down to zones and cabinets; PaletteCAD
is room-first by construction. Not one of them treats heights as a
per-cabinet afterthought. This is the strongest confirmation in the review.

### [P-2] TIGHTEN — Phase 1 fixes a LINE; say explicitly that the stack is solved to hit it, in 10 mm steps

**Playbook says:** "worktop = elbow − 100..150 mm, default 850..910 = 720
carcass + 100..150 plinth + 38 top."

**Trade practice says:** two imprecisions, both already flagged elsewhere
(survey-protocol §6.1, bd kuchnie-uro items 1 and 4). First, the arithmetic
bakes in a 38 mm top; compact laminate and thin stone (12–28 mm) are now
common, and with a thin top the plinth (cokół) or leg adjustment absorbs
the difference — the LINE is the decision, the stack is the means. Second,
fitting hardware works in coarse steps: adjustable legs and plinth stock
move in roughly 10 mm increments, so an mm-precise derived height promises
a precision the site cannot deliver. Round the decided line to 10 mm and
say so.

**Proposed text (replace the Phase 1 box):** "Phase 1 — Fix working
heights. Worktop LINE = elbow − 100..150 mm, rounded to 10 mm (legs and
plinth adjust in ~10 mm steps). Default band 850..910. The stack (720
carcass + plinth + top thickness) is then solved to hit the line — a thin
top (12–28 mm) means a taller plinth, not a lower line."

**How the pro tools encode it:** Polyboard and TopSolid'Wood parametrize
plinth height and top thickness independently of the target worktop plane
precisely so the plane survives a material change. PRO100's default 38 mm
top is a legacy laminate assumption — a lowest-common-denominator default,
not a rule.

**Blast radius:** `height-parameter-set.md` stores `derive_worktop_height`
mm-precise with a warning band tied to 850..910 and to the 38 mm
arithmetic; ratifying this touches that spec (add rounding guidance and a
top-thickness note), not just the playbook.

### [P-3] ADD — Phase 1 output should include the wall-unit clearance number, not just "wall-unit line"

**Playbook says:** the Phase 1 artifact is "(worktop, wall-unit line, tall
line)" — the clearance between worktop and wall-unit bottom is never
stated as a number anywhere in the playbook.

**Trade practice says:** bottom of wall units 450–600 mm above the worktop,
500 mm as the default; below 450 the worktop (blat) under the units stops
fitting a kettle or a food processor, above 600 the top shelf leaves a
shorter user's reach. Survey-protocol §6.1 already carries this as an
advisory; it belongs in the phase that fixes the line, with the client's
reach recorded before choosing.

**Proposed text (Phase 1 box, appended):** "wall-unit line = worktop line
+ 450..600 (default 500); record the primary cook's reach before choosing."

**How the pro tools encode it:** Winner Flex and PRO100 both expose the
worktop-to-wall-unit gap as a named job parameter with a 500-class default;
Blum's ergonomic planner (DYNAMIC SPACE) teaches the same band.

### [P-4] KEEP — one worktop line per project is a legitimate simplification

**Playbook says:** one height parameter set per project; Phase 5 demands
"one continuous top line."

**Trade practice says:** correct for a joined laminate worktop and for the
price bracket P1-class projects live in. The AMK/DIN-derived split-height
guidance (sink higher, hob lower — the pot rim adds ~100 mm to the working
plane) is real ergonomics, but split levels cost a worktop joint, break
the L's visual line, and complicate the corner. Keep one line; have the
conversation when a client bakes or cans seriously (survey-protocol §6.1
already says this). No playbook change needed — this row exists so the
simplification is confirmed as chosen, not accidental.

---

## §2 Phase 2 — zones and appliance placement (playbook section 2)

### [P-5] CHANGE — "Dishwasher LEFT of sink" is presented as a hard rule; the trade genuinely disputes it

**Playbook says:** "Cook right- or left-handed? → right: Dishwasher LEFT
of sink / left: Dishwasher RIGHT of sink" and the hard-rules paragraph:
"dishwasher adjacent to sink on the dominant-hand side."

**Trade practice says:** the load-bearing rules are (a) dishwasher
adjacent to the sink cabinet — short plumbing, and scraping/rinsing drips
travel over the sink, not over a drawer bank; (b) the open dishwasher door
must not block the corner or the main traffic path. WHICH side is
disputed: one school says dominant-hand side for loading flow, another
says the side away from the prep zone so an open door doesn't cut the cook
off from the worktop, and observed European installs split close to evenly
depending on where the drain sits. bd kuchnie-uro item 2 flags exactly
this. A hard rule here will be "wrong" for half of clients; a mimed
question is cheap at the survey visit (survey-protocol §4 already makes
the client mime rinsing a plate).

**Proposed text (replace the D branch):** "Dishwasher ADJACENT to the
sink, side decided with the client: have them mime scraping → rinsing →
racking. Default: the side away from the corner. Handedness is the
tie-breaker, not the rule."

**How the pro tools encode it:** none of the five tools enforces a
dishwasher side — PRO100/Winner will happily place it either side and
their validation is silent on it. The absence of a tool rule is itself
evidence this is a preference, not a standard.

### [P-6] KEEP — sink under window, ≥600 prep between sink and hob, hob ≥300 from a side wall

**Playbook says:** sink under the window when one leg has it; "sink-to-hob
>= 600 mm worktop between them; hob >= 300 mm from a side wall."

**Trade practice says:** confirmed, and the numbers are right. The 600
prep stretch between wet and hot zones is the single most-used stretch of
worktop in the kitchen; 300 mm hob-to-wall keeps pan handles off the wall
and lets a wall-side pot actually sit on the back burner (also the
figure most hob sheets state as minimum side clearance to combustible
surfaces). PaletteCAD's and Winner's placement warnings fire on both.

### [P-7] TIGHTEN — the fridge/oven column rule needs hinge side and a hot-to-tall clearance

**Playbook says:** "Fridge + oven column at the OPEN END of the longer leg
— never mid-run, never in the corner" and "fridge with >= 400 mm set-down
beside it."

**Trade practice says:** the open-end rule is right (a tall unit — słupek
— mid-run cuts the worktop in two and murders the work flow). Two cases
are missing. (a) Hinge side: a fridge door hinged against the adjacent
wall opens ~90° and the crisper drawers jam — hinge must swing toward the
room/worktop side; this is the most common fridge complaint fitters hear.
(b) Hob-to-column clearance: a hob placed hard against the tall column
scorches the column's side front and blocks pan handles — keep ≥300 mm
worktop between hob edge and a tall unit (mirror of the wall rule).

**Proposed text (append to F box):** "Fridge hinge swings toward the room,
not into the adjacent wall. Keep ≥300 mm worktop between the hob edge and
the column side."

**How the pro tools encode it:** TopSolid'Wood and Polyboard cabinet
libraries carry handed variants of tall fridge housings for exactly the
hinge reason; hob side-clearance to tall furniture appears in appliance
sheets and in Winner's clearance checks.

### [P-8] KEEP — the 3.6–6.6 m triangle band, knowing it is conservative

**Playbook says:** "Triangle 3.6–6.6 m total? Landings: 400 by hob, 400 by
fridge, 600 by sink?"

**Trade practice says:** NKBA-derived guidance allows up to ~7.9 m;
6.6 m is the stricter European habit. In the small Polish kitchens these
projects will see, the tighter bound costs nothing and catches genuinely
bad layouts. Survey-protocol §6.1 reached the same verdict. Keep as
written; per ADR-035 Decision 3 this stays a human checklist item (G5) and
this review proposes no mechanization.

---

## §3 Phase 3 — the corner (playbook section 3)

This is the phase the repo just built data for (`CornerLink` in
`l-layout-model.md`), so precision here pays twice.

### [P-9] TIGHTEN — choose the mechanism BEFORE fixing the blind-cabinet width; name the 1050 convention

**Playbook says:** "BLIND CORNER 1000–1300 + Magic Corner / LeMans" and
"BLIND CORNER 1000–1300 + plain shelves."

**Trade practice says:** the causality runs mechanism → door opening →
cabinet width, not width first. Kesseböhmer Magic Corner and LeMans
variants are built for specific minimum clear door openings (commonly a
450 or 500 mm door for Magic Corner; LeMans II is sold per door width
450/500/600 and per hinge side); pick the mechanism, read its minimum
opening, then derive the blind width. In Polish practice the workhorse is
the 1050 blind corner (korpus ~1000–1050 + the blind panel/filler), which
yields the ~500 door a Magic Corner wants while consuming a tolerable bite
of the leg; 1200–1300 blinds buy more dead volume, not more access. The
l-layout-model spec already uses "a 1050 corner-blind plus filler" as its
worked example — the playbook band and the repo's example should agree on
naming 1050 as the default.

**Proposed text (replace both BLIND boxes):** "BLIND CORNER — pick the
mechanism first (Magic Corner / LeMans need a stated minimum clear door
opening, and LeMans is handed); derive cabinet width from it. Default
1050 blind (≈500 mm door); widen past 1200 buys dead volume, not access.
Plain-shelf fallback keeps the same 1050 geometry so the mechanism can be
retrofitted."

**How the pro tools encode it:** corner-cabinet libraries in
TopSolid'Wood and Polyboard are parametrized per mechanism (the mechanism
SKU drives the door opening); PRO100's generic blind corner is a plain box
— a lowest-common-denominator default that will not warn about a LeMans
that cannot fit its door. ADR-035 Decision 4 already routes karuzela/cargo
mechanisms to estimate lines, so this changes design guidance, not the
decomposer scope.

### [P-10] TIGHTEN — filler width is collision math, not a 50–100 band; separate the corner filler from the wall filler

**Playbook says:** "MANDATORY in every branch: 50–100 mm filler strip at
the internal corner on BOTH runs — else handles and drawer fronts collide."

**Trade practice says:** mandatory is right; the band is the imprecise
part. The corner filler (blenda) exists to clear the ADJACENT run's front
plus its handle on the opening arc, so its minimum is derived: front
thickness (~19–22 mm) + handle projection (~25–35 mm for a bar handle) +
reveal margin ⇒ ~50–60 mm for door-only meetings, but a DRAWER BANK
meeting the corner needs the full handle projection cleared along the
whole extension travel — with bar handles plan 70–100 mm, with knobs less,
and handleless (gola / TIP-ON) fronts still need ~30–50 mm because the
front corners sweep an arc even without hardware. This is also a different
animal from the wall-end filler of Phase 4, which absorbs wall
irregularity (tolerance-driven, sized at survey); the playbook currently
uses "filler" for both.

**Proposed text (replace FILL box):** "MANDATORY in every branch: corner
filler on BOTH runs, sized by collision math — front thickness + handle
projection + reveal (door meetings ≥50–60; a drawer bank at the corner
≥70–100 with bar handles; handleless still ≥30–50). This corner filler is
separate from the Phase-4 wall-end tolerance filler."

**How the pro tools encode it:** Winner Flex and PRO100 corner assemblies
insert a corner post/filler automatically with a ~60–70 mm default and let
the designer widen it; Polyboard's corner rules take handle projection as
a parameter. Tool defaults near 60 confirm the door-case floor; none of
the defaults knows your handle choice, which is why the math beats the
band.

**Blast radius:** `l-layout-model.md` gives `CornerLink` a scalar "filler
width per leg" — a derived minimum needs handle-projection data the model
does not carry today. Ratifying the math keeps the scalar (the designer
still decides one number); mechanizing the check later (G2/G3) would need
the handle projection recorded per project.

### [P-11] ADD — dishwasher directly beside the blind corner blocks the mechanism

**Playbook says:** "Never in the corner: sink, hob, dishwasher. Never two
appliance doors meeting at the corner." Nothing about the cabinet
IMMEDIATELY beside the corner.

**Trade practice says:** a dishwasher placed as the first unit after the
blind corner has its dropped door lying exactly where you stand to swing a
Magic Corner / LeMans tray out — the two cannot be used in the same
minute, and worse, an open DW door blocks corner access entirely during
loading. Same logic, weaker, for an oven column beside the corner. The
tree's refusal list covers in-corner appliances well (confirmed); it needs
one adjacency line.

**Proposed text (append to X box):** "Avoid a dishwasher as the first
unit after the blind corner — its open door blocks the corner pull-out;
prefer a door or drawer cabinet as the corner's neighbour."

**How the pro tools encode it:** this one is honest terrain — the tools do
NOT check it automatically; it lives in fitter lore and in Kesseböhmer's
planning sheets (access-space diagrams). Evidence grade: manufacturer
planning guidance, not tool validation.

### [P-12] KEEP — corner-before-widths, and the appliance-in-corner refusals

**Playbook says:** "Decided before dimensioning either run, because the
corner consumes width from BOTH legs" plus the X-box refusals.

**Trade practice says:** confirmed on both counts. Sink-in-corner and
hob-in-corner are the two classic regret installs (unreachable bowl,
elbow-in-wall stirring) and the playbook refuses them cleanly; the
both-legs consumption rule is now also invariant 1 of the repo's
l-layout-model. The decision tree covers appliance-in-corner refusal
adequately; P-11 above is the missing adjacent case, not a hole in this
one.

### [P-13] ADD — the corner tree stops at base cabinets; Phase 5 needs a wall-corner decision

**Playbook says:** Phase 5 is "mirror base line, hood on duct route, one
continuous top line" — the wall-unit (górna) corner is never decided
anywhere.

**Trade practice says:** the wall corner has the same three-way choice in
miniature: L-shaped corner wall unit (narożna górna), diagonal wall unit,
or a dead wall corner blanked with a filler — and it interacts with the
hood position on the other leg. Leaving it implicit is how two wall runs
arrive on site with no plan for their meeting.

**Proposed text (Phase 5 box, appended):** "Wall corner decided the same
way as the base corner (L-corner unit / diagonal / dead + filler) —
mirror the base decision unless the hood or a window forbids it."

**How the pro tools encode it:** every corner library in the five tools
ships wall-corner variants alongside base-corner ones; PRO100 places them
as a pair by default.

---

## §4 Phase 4 — drawers vs doors, run composition (playbook section 4)

### [P-14] CHANGE — "one filler per run" contradicts the mandatory corner filler two sections earlier

**Playbook says:** "wall irregularity absorbed by one filler per run at
the wall end, never mid-run" — while section 3 mandates a corner filler
on BOTH runs. Read literally, a corner leg cannot satisfy both lines.

**Trade practice says:** both rules are right; the word "filler" is doing
two jobs. A corner leg in an L normally carries two fillers: the corner
blenda (collision-driven, P-10) and the wall-end tolerance filler
(survey-driven). "Never mid-run" applies to the tolerance filler and is
correct — a mid-run filler breaks the front rhythm and screams
measurement error.

**Proposed text (replace the composition sentence):** "wall irregularity
absorbed by one TOLERANCE filler per run at the wall end, never mid-run —
this is in addition to the Phase-3 corner filler, so a corner leg
normally carries two."

**How the pro tools encode it:** Winner and PRO100 auto-insert both
(corner post + scribe filler at the wall) as distinct catalog items; the
repo's `validate_rows` standard-width advisory would also stop
misreading a two-filler corner leg as an anomaly once the wording is
clear.

### [P-15] TIGHTEN — sink cabinet 800–900 excludes the small-kitchen case

**Playbook says:** "sink → Door cabinet + waste-sorting drawer; carcass
800–900."

**Trade practice says:** 800–900 suits a 1.5-bowl sink with drainer; a
600 sink cabinet under a single bowl is a routine and correct choice in
compact Wrocław flats, and forcing 800 on a 2.4 m leg steals the width
the drawer bank needs. Size the cabinet to the CHOSEN sink (its sheet
states minimum cabinet width) — same defer-to-sheet logic as G4. ADR-035
Decision 4 keeps the sink cabinet an estimate line, so this changes design
guidance without touching decomposer scope.

**Proposed text:** "sink → Door cabinet + waste-sorting drawer; carcass
600–900, minimum per the chosen sink's sheet (single bowl fits 600,
1.5-bowl wants 800+)."

**How the pro tools encode it:** sink libraries in the tools carry the
minimum-cabinet-width attribute per sink model and warn on mismatch —
the sheet, not a band, is the authority.

### [P-16] KEEP — drawer banks in prep/cooking zones from 600 wide; a 900 bank beats two door cabinets

**Playbook says:** the prep/cooking branch prefers "DRAWER BANK —
LEGRABOX or Tandembox; 900 wide with 2 tall + 1 internal beats two door
cabinets," doors for low-use and corner-adjacent modules.

**Trade practice says:** confirmed — this is the single clearest piece of
modern-kitchen consensus. Full-extension drawers give ~30% more usable
retrieval (no kneeling, no dark back half), and the 900 two-tall
composition is the sweet spot of Blum's own DYNAMIC SPACE zone planning.
The corner-adjacent door preference is also right (a drawer bank hard
against the corner is exactly the P-10 collision case). The CHK box
re-checking drawer banks against the corner filler is a genuinely good
gate other playbooks forget.

**How the pro tools encode it:** Blum's planner, Polyboard zone rules and
Winner's zone libraries default prep/cook base units to drawer stacks;
door cabinets survive as the budget branch — exactly the shape of this
tree.

---

## §5 Phase 6 — worktop and services (playbook section 5)

### [P-17] CHANGE — hood heights must defer to the appliance sheet; keep 650/750 as the no-sheet floor

**Playbook says:** "Hood height per its spec: >= 650 mm electric /
>= 750 mm gas above hob" — and gate G7 re-checks "Gas/hood distances
legal?" against these same numbers.

**Trade practice says:** the line already says "per its spec" and then
pins numbers that can contradict the spec: several induction-oriented hood
sheets permit 550–600 mm, while gas minimums are manufacturer-binding and
sometimes HIGHER than 750. The sheet outranks the band in both directions
— exactly how G4 already treats cutouts, and exactly bd kuchnie-uro item
3. Keep the printed numbers as the fallback floor when no sheet is on the
project spine yet (early estimating needs a number).

**Proposed text:** "Hood (okap) height above hob: the manufacturer sheet
is binding, both directions (some induction hoods permit 550–600; some
gas hoods demand more than 750). With no sheet on the spine yet, plan
≥650 electric / ≥750 gas as the floor and mark the value provisional."
And in section 6: G7's hood clause reworded to "hood distance matches the
appliance sheet (fallback floor 650/750 when sheet absent)" — deferring
like G4, per the tracked note in kuchnie-uro.

**How the pro tools encode it:** appliance-library placement in Winner and
PRO100 takes the clearance from the imported appliance record when one
exists and falls back to a generic minimum otherwise — the two-tier rule
proposed here is literally their behaviour.

### [P-18] ADD — plinth ventilation for integrated cold appliances

**Playbook says:** Phase 6 lists cutouts, sockets, lighting, ventilation —
where "ventilation" means the hood duct. Nothing about appliance airflow.

**Trade practice says:** an integrated fridge/freezer column needs a
stated airflow path — typically a vent grille in the plinth (kratka w
cokole) plus a clear duct up the back of the column and an exit above,
per the appliance sheet (commonly a 200 cm²-class cross-section). A
sealed plinth around an integrated fridge means a compressor running hot,
higher bills and early death — and it is invisible at handover, so the
gate is the place that catches it. Also machine-checkable cheaply: fridge
column present in the cabinet list ⇒ vent grille line item present in the
BOM.

**Proposed text (new Phase 6 bullet):** "Integrated fridge/freezer:
plinth vent grille + rear airflow duct per the appliance sheet — the vent
grille is a BOM line, never an on-site improvisation." Gate candidate in
§6 below.

**How the pro tools encode it:** fridge-housing library items in
TopSolid'Wood and Polyboard include the vent cutouts in the part
geometry; PRO100's generic tall housing does not — a known
lowest-common-denominator gap that has burned fitters.

### [P-19] TIGHTEN — socket line: add the height band and the dedicated-circuit list

**Playbook says:** "Sockets every ~900 mm above worktop, none within
600 mm of the sink edge; dedicated circuit for induction; under-cabinet
LED over the full prep run."

**Trade practice says:** right skeleton, three refinements. (a) Height
band: sockets 100–150 mm above the worktop line (bottom of socket), so
they clear the upstand and stay under the wall units. (b) Not above the
hob: the no-socket zone applies to the hob's width as well as the sink's
600 mm radius (a cable draped over a hot pan is the classic finding).
(c) Dedicated circuits: oven and dishwasher normally get their own
circuits in Polish practice, not just the induction — the electrical plan
artifact should list three-plus circuits, decided with the electrician
before the worktop order.

**Proposed text:** "Sockets every ~900 mm along the prep run, 100–150 mm
above the worktop line; a no-socket zone within 600 mm of the sink edge
AND across the hob width. Dedicated circuits: induction, oven,
dishwasher (confirm with the electrician). Under-cabinet LED over the
full prep run."

**How the pro tools encode it:** PaletteCAD and Winner place sockets as
catalog objects snapped to a configurable height band; their reports list
circuits per appliance. The hob no-socket zone appears in their
validation warnings, sink-zone-style.

### [P-20] KEEP — two worktop segments, mason's mitre decided at order time, joint clear of cutouts

**Playbook says:** "two segments joined at the corner; joint type (mason's
mitre for laminate) and grain direction decided with the order, not at
fitting" and "the corner joint must not land on a cutout" with ≥50 mm
web around cutouts.

**Trade practice says:** confirmed, and the "decided with the order"
clause is the valuable part — a mason's mitre cut on site with a router
jig is a different (worse) product than one CNC'd by the supplier, and
grain direction on wood-decor laminate is unfixable after cutting. The
≥50 mm web matches laminate suppliers' order forms. One advisory, no text
change: induction hob sheets sometimes demand a larger rear web or a
cooling gap below — G4's sheet-check already owns that.

---

## §6 Phase 8 — the validation gate list (playbook section 6)

The existing ladder G1–G7 is well-ordered (cheap/structural checks first,
back-references to the phase that owns the fix — the fail-routing is
better than what most commercial tools give you, which is a flat warning
list). Findings: one TIGHTEN on an existing gate, then ADD candidates the
pro tools run automatically that the list lacks. Per ADR-035 Decision 3,
anything needing room geometry (doors, walkways, traffic) belongs on the
G5-style human checklist with a TTL'd attestation, not in code.

### [P-21] TIGHTEN — G3's collision "walk-through" can become machine-checkable at the corner once positions exist

**Playbook says:** "G3: Door/drawer collision walk-through clean at corner
and room door?"

**Trade practice says:** keep the human walk-through for the room door
(room geometry — G5-style per ADR-035), but the CORNER half is opening-arc
math on data the repo now carries (`CornerLink`: runs, turn, filler
widths). Front thickness + handle projection + filler width per leg is a
computable clearance — this is the P-10 math run by machine. Split the
gate's wording so the mechanizable half is named.

**Proposed text:** "G3a (machine-candidate): corner opening-arc clearance
— filler width per leg ≥ front thickness + handle projection + reveal.
G3b (human, G5-style): walk-through at the room door and along the
walkway." Repo home: G-family via `validate_rows` once handle projection
is a recorded parameter; tracked gate work wk-89a668a2 is the natural
carrier.

**How the pro tools encode it:** PRO100 and Winner run door/drawer
opening-collision detection automatically on placement; TopSolid'Wood
checks kinematics of the machining model. The tools treat this as a
machine check, which supports splitting it out of the human list.

### [P-22] ADD — walkway / opposing-fronts clearance: ~1200 mm for a single cook

**Missing from the gate list:** clearance in front of the L when
something faces it (an island later, a wall, a table). Trade floor:
~1200 mm between the front of the run and the opposing obstacle for a
single-cook kitchen (an open dishwasher door ~600 plus a person passing);
1500 for two cooks. The playbook's hard-rules list says "walkway in front
of the L >= 1100 mm" in Phase 2 but the Phase 8 gate never re-checks it
after width changes — and 1100 is the tight end of practice; 1200 is the
safer single-cook floor.

**Testable criterion:** distance from front-of-run to nearest opposing
obstacle ≥1200 mm (single cook) at the narrowest point. **Repo home:**
human checklist (G5-style) — it needs room geometry ADR-009/ADR-035 keep
out of the model; fold it into the G5 plan-sheet walk and its TTL'd
attestation. Also worth harmonizing the Phase-2 number to 1200.

### [P-23] ADD — socket-zone and worktop-overhang checks (human checklist, paired)

Two more checks the tools run that the gate list lacks; both land on the
human checklist today because the repo models neither electrics nor the
worktop order geometry.

(a) **Socket zones vs hob/sink:** no socket within 600 mm of the sink
edge nor across the hob width; height band 100–150 above the worktop
(P-19's rule, re-checked at gate time because Phase 4 width shuffles move
appliances). Testable criterion: overlay the electrical plan on the final
elevation; zero sockets inside either exclusion zone. Repo home: human
checklist until an electrical-plan artifact exists.

(b) **Worktop overhang:** front overhang ~30–50 mm proud of the carcass
front (20 mm door + reveal + drip margin), flush-to-slightly-proud at a
freestanding appliance slot so its door clears. Testable criterion:
worktop depth = carcass depth + front stack + 30–50 mm on the order form.
Repo home: human checklist now; machine-checkable later if the worktop
order (A7 artifact) becomes structured data.

**How the pro tools encode it:** Winner and PaletteCAD generate the
worktop order from the plan with the overhang as a parameter and validate
socket placement against appliance zones; their reports are exactly the
plan-sheet overlay proposed here.

### [P-24] ADD — wall-unit depth vs worktop depth (machine-checkable now)

**Missing from the gate list:** wall units (górne) deeper than ~400 mm
over a 600 worktop put the door edge at forehead height for the working
cook; the standard pairing is 300–350 wall depth over 560–600 base/
650 worktop. Testable criterion: wall-unit depth ≤ 400 whenever the unit
hangs over the worktop line (hood housings exempt, they follow the
sheet). **Repo home:** machine-checkable in the G-family today — cabinet
depth is already a field on the cabinet list; this needs no room
geometry and could join `validate_rows` beside the standard-width
advisory.

**How the pro tools encode it:** the depth pairing is baked into the
tools' wall-unit libraries (300/320/350 defaults); PRO100 warns when a
wall unit's front plane crosses the base unit's working envelope.

---

## §7 Repo mapping (playbook section 7)

### [P-25] KEEP — the no-ledger-ids design and the encoded-vs-tracked honesty

**Playbook says:** the gate numbers "are design-practice values, not
repository facts — they carry no ledger ids by design," with the mapping
table naming what is encoded (G1, G6, standard-width advisory) vs tracked
(G2/G3/G4/G5/G7 under wk-89a668a2).

**Trade practice says:** confirmed — this is the right boundary, and it
is the discipline the commercial tools lack (their defaults and their
validations are indistinguishable, which is how a PRO100 default becomes
someone's "standard"). One forward note, no text change yet: with
`CornerLink` landed, the corner-filler rule is close to crossing the line
from practice value to encoded check (P-10/P-21); when it does, the
playbook's own closing sentence already says what to do — cite the
implementing spec from the playbook. The trigger is about to fire; the
mechanism for it is already written. Good design.

---

## Ratification table

Walk the rows; say yes/no per row. "ADR-035?" marks whether the proposal
touches a ratified ADR-035 decision (needing a superseding decision rather
than a playbook edit alone).

| Id | Severity | One-line proposal | ADR-035? | Suggested disposition |
|---|---|---|---|---|
| P-1 | KEEP | Confirm heights→zones→corner→widths spine | no | ratify now |
| P-2 | TIGHTEN | Phase 1 fixes a LINE (10 mm steps); stack solved to hit it, thin tops via plinth | no (touches height-parameter-set.md) | ratify now |
| P-3 | ADD | Wall-unit clearance 450–600 (default 500) into Phase 1 output | no | ratify now |
| P-4 | KEEP | One worktop line per project stays; split heights remain a client conversation | no | ratify now |
| P-5 | CHANGE | Dishwasher side: adjacent-to-sink rule + mimed client question, not a handedness law | no | ratify now |
| P-6 | KEEP | Confirm sink-under-window, 600 prep stretch, 300 hob-to-wall | no | ratify now |
| P-7 | TIGHTEN | Add fridge hinge-side rule + 300 mm hob-to-column clearance | no | ratify now |
| P-8 | KEEP | Keep conservative 3.6–6.6 triangle band; G5 stays human | yes — consistent with D3 | ratify now |
| P-9 | TIGHTEN | Mechanism-first blind sizing; name 1050 as the default blind | no (D4 unaffected — mechanisms stay estimate lines) | ratify now |
| P-10 | TIGHTEN | Corner filler sized by collision math (front + handle + reveal), not a flat 50–100 | no | ratify now |
| P-11 | ADD | No dishwasher as the blind corner's first neighbour | no | discuss with client data |
| P-12 | KEEP | Confirm corner-before-widths + in-corner appliance refusals | no | ratify now |
| P-13 | ADD | Phase 5 wall-corner decision (L-corner unit / diagonal / dead) | no | ratify now |
| P-14 | CHANGE | Disambiguate tolerance filler vs corner filler ("one filler per run" contradiction) | no | ratify now |
| P-15 | TIGHTEN | Sink cabinet 600–900, minimum per the sink's sheet | no (D4: stays estimate line) | ratify now |
| P-16 | KEEP | Confirm drawer-bank preference + the corner-filler re-check box | no | ratify now |
| P-17 | CHANGE | Hood height defers to appliance sheet both directions; 650/750 only as no-sheet floor; G7 reworded like G4 | no | ratify now |
| P-18 | ADD | Plinth vent grille + airflow path for integrated cold appliances (Phase 6 bullet + BOM-presence gate) | no | ratify now |
| P-19 | TIGHTEN | Socket height band 100–150, hob no-socket zone, dedicated circuits incl. oven + DW | no | ratify now |
| P-20 | KEEP | Confirm worktop segment/joint/order-time discipline | no | ratify now |
| P-21 | TIGHTEN | Split G3 into machine-candidate corner-arc check + human room-door walk | yes — respects D3 boundary; needs wk-89a668a2 scoping | discuss with client data |
| P-22 | ADD | Walkway ≥1200 single-cook re-check at gate time (G5 human checklist item) | yes — extends D3's human checklist | ratify now |
| P-23 | ADD | Socket-zone + worktop-overhang gate checks (human checklist pair) | yes — human-checklist placement per D3 | defer to stage 2 |
| P-24 | ADD | Wall-unit depth ≤400 over worktop — machine-checkable G-family candidate | no | defer to stage 2 |
| P-25 | KEEP | Confirm no-ledger-ids boundary; note corner-filler rule nearing encodement | no | ratify now |

Severity totals: CHANGE 3 · TIGHTEN 8 · KEEP 8 · ADD 6 (25 findings).
