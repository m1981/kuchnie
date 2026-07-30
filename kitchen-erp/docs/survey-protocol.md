# On-Site Measurement Protocol (Protokół pomiaru) — print-and-fill, project P1

> Reader: the operator standing in the client's room with this sheet on a
> clipboard, measuring a kitchen for the first real project (P1) |
> Enables: one visit producing the five survey-pack artifact kinds that
> pass the 2→3 stage gate (`kitchen-erp/docs/specs/survey-pack.md`), so
> design starts from paper, not memory | Update-trigger: the
> REQUIRED_SURVEY_KINDS list changes, the elbow derivation in
> `height-parameter-set.md` changes, or the first real pomiar shows a
> field the sheet lacks

**Honesty framing.** This protocol encodes trade practice as written down
by a language model and reviewed by the operator. The measured room is the
authority; wherever the sheet and the room disagree, believe the room and
note the gap. Validation of this sheet happens at the real pomiar — see
section 6 for the two attestations to file afterwards.

How to use: print, fill in pen on-site, photograph the filled pages, then
follow section 6 back at the desk. Units are **mm** throughout. Sections
1–5 map 1:1 to the survey-pack artifact kinds — a filled section becomes
one ArtifactRef.

---

## 0. Kit list (zestaw pomiarowy)

| ✓ | Item | Why |
|---|---|---|
| ☐ | Laser measure (dalmierz laserowy) | long runs, diagonals, ceiling |
| ☐ | Steel tape 5 m (miarka) | cross-check the laser on one wall — the two must agree within 3 mm before you trust either |
| ☐ | Spirit level 600+ mm (poziomica) or phone inclinometer | wall lean, floor fall |
| ☐ | Phone camera | photo protocol below |
| ☐ | This sheet, clipboard, two pens | pen fails → second pen |
| ☐ | Masking tape + marker | label media points on the wall before photographing |

**Photo protocol (obowiązkowo):** (1) one wide shot per corner looking
across the room; (2) one straight-on shot per wall, full wall in frame;
(3) one close-up per media point **with the tape held in frame** showing
distance from the reference corner — a photo without a scale reference is
decoration, not data.

---

## 1. Room dimensions — walls and diagonals

**ArtifactRef kind: `survey_dims`**

Pick one corner as origin (punkt zerowy) — mark it on the sketch and keep
it for section 2. Walls named clockwise A, B, C, D from the origin.

Measure wall lengths at **three heights** — walls lean, and the worktop
(blat) meets the wall at ~900, not at the floor:

| Wall (ściana) | at floor +100 | at +900 (blat line) | at +2100 (wall-unit top) |
|---|---|---|---|
| A | ____ mm | ____ mm | ____ mm |
| B | ____ mm | ____ mm | ____ mm |
| C | ____ mm | ____ mm | ____ mm |
| D | ____ mm | ____ mm | ____ mm |

| Check | Value |
|---|---|
| Diagonal (przekątna) origin → opposite corner | ____ mm |
| Counter-diagonal | ____ mm |
| Ceiling height (sufit) at origin corner | ____ mm |
| Ceiling height at the corner diagonally opposite | ____ mm |
| Floor level variance along the planned plinth line (cokół): level at both run ends + the corner | ____ mm high side / ____ mm low side |

Openings (per window/door):

| Opening | From origin corner | Width | Sill / lintel height (parapet / nadproże) | Swing direction and reach |
|---|---|---|---|---|
| ____ | ____ mm | ____ mm | ____ / ____ mm | ____ |

**Sketch box** — leave the lower half of this printed page blank: draw the
plan view from above with the origin corner marked, wall letters, window
and door positions, and the intended L. Under it draw one elevation per
leg wall showing openings and heights. Rough is fine; numbers live in the
tables, the sketch carries topology.

> **Fitter's traps (pułapki):** unequal diagonals = out-of-square room —
> a 15 mm diagonal difference on a 3 m room means the corner cabinet
> shows a wedge gap; that is what the filler strip absorbs, so record it,
> don't fear it. Floor variance beyond ~10 mm along a run means the
> plinth line will be cut, not just leg-adjusted — measure it now, not at
> fitting. A window swinging inward over the future worktop collides with
> a tap or drainer: open it fully and measure the reach.

---

## 2. Media points (media / piony)

**ArtifactRef kind: `survey_media`**

Positions from the **same origin corner** as section 1: distance along the
wall + height from floor. Tape-label points M1, M2… on the wall, then
photograph per the protocol.

| # | Type | Wall | From origin | Height | Notes |
|---|---|---|---|---|---|
| M1 | Cold water (przyłącze wody) | ____ | ____ mm | ____ mm | valve? (zawór) ____ |
| M2 | Hot water | ____ | ____ mm | ____ mm | ____ |
| M3 | Drain (odpływ) | ____ | ____ mm | ____ mm | pipe Ø ____ mm |
| M4 | Gas point (przyłącze gazu) | ____ | ____ mm | ____ mm | valve accessible? ____ |
| M5 | Vent grille / duct (kratka wentylacyjna) | ____ | ____ mm | ____ mm | for okap: ducted or recirculation? ____ |
| M6+ | Sockets & switches (gniazdka), one row per point | ____ | ____ mm | ____ mm | circuit known? ____ |

| Extra checks | Value |
|---|---|
| Distance nearest socket → planned sink edge (zlew) | ____ mm |
| Dedicated circuit available for induction hob (płyta)? | tak / nie / nieznane |
| Duct route from grille to planned hood (okap) position — length and bends | ____ |
| Radiators, boiler (piec), meters (liczniki) in the kitchen zone — position | ____ |

> **Fitter's traps:** a socket closer than ~600 mm to the sink edge must
> move — cheaper to learn now than after tiling. Gas: the hob wants the
> gas point within reach of a rigid or approved flex connection and the
> valve must stay reachable after cabinets go in — a valve behind a fixed
> back panel fails inspection. Hood flue: count the bends; two 90° bends
> on a long run kill a cheap hood's extraction, and a duct crossing the
> tall-unit line steals cabinet depth — sketch the route on the section 1
> elevation. Drain height decides whether the dishwasher (zmywarka) trap
> fits; below ~300 mm is comfortable, above ~500 mm is a problem.

---

## 3. Appliance sheets (karty urządzeń)

**ArtifactRef kind: `survey_appliance_sheet`**

One manufacturer sheet per appliance — archived verbatim; the sheet, not
this table, is the dimension truth (gate G4 later checks cutouts against
it). This table records which sheets you must chase.

| Appliance | Model agreed with client | Sheet obtained? (PDF/photo) | Built-in or freestanding |
|---|---|---|---|
| Hob (płyta) | ____ | ☐ | ____ |
| Oven (piekarnik) | ____ | ☐ | ____ |
| Fridge (lodówka) | ____ | ☐ | ____ |
| Dishwasher (zmywarka) | ____ | ☐ | ____ |
| Hood (okap) | ____ | ☐ | ____ |
| Sink + tap (zlew + bateria) | ____ | ☐ | ____ |
| Other: ____ | ____ | ☐ | ____ |

> **Fitter's traps:** "a 60 cm oven" is a lie the showroom tells — cutout
> width, niche height and ventilation gaps come from the sheet, nothing
> else. If the client says "I'll pick the fridge later", record the
> reserved niche as a decision with a deadline: an American fridge chosen
> after the carcasses are cut is a redesign. Photograph the rating plate
> of appliances the client wants to keep — old models have odd depths.

---

## 4. User profile (profil użytkownika)

**ArtifactRef kind: `survey_user_profile`**

The elbow number here drives the worktop height for the project
(worktop = elbow − 100..150 mm, spec `height-parameter-set.md`).

**Elbow measurement procedure (wysokość łokcia):** primary cook stands
relaxed in flat shoes, arms hanging, then bends one forearm to horizontal
— measure floor → underside of the elbow. Do it twice; if the readings
differ by more than 10 mm, do it a third time and take the middle value.

| Field | Value |
|---|---|
| Primary cook — height (wzrost) | ____ mm |
| Primary cook — elbow height (łokieć) | ____ mm / ____ mm (two readings) |
| Handedness (praworęczny / leworęczny) | R / L |
| Second regular cook? height + elbow | ____ / ____ mm |
| Mobility notes (reach limits, glasses, back) | ____ |

> **Fitter's traps:** measure the elbow in the shoes worn in the kitchen
> — slippers vs. barefoot is 20 mm. Two cooks of different height: derive
> from the one who cooks most, note the other; the compromise is decided
> at the desk, not at the wall. Handedness fixes the dishwasher side
> (playbook Phase 2), so ask it explicitly — people are surprisingly
> unsure until they mime rinsing a plate.

---

## 5. Budget bracket (budżet)

**ArtifactRef kind: `survey_budget`**

| Field | Value |
|---|---|
| Bracket agreed aloud with the client | ____ – ____ zł |
| Includes appliances? (AGD w kwocie?) | tak / nie |
| Includes worktop + sink + tap? | tak / nie |
| Corner mechanism appetite (~1500 zł, playbook Phase 3) | tak / nie / do omówienia |
| Drawer hardware tier discussed (LEGRABOX / Tandembox / basic) | ____ |
| Client signature or initials confirming the bracket | ____ |

> **Fitter's traps:** an unspoken budget is a redesign in disguise — the
> bracket must be said out loud and written in front of the client. Ask
> the corner-mechanism question during the visit while pointing at the
> actual corner: abstract questions get abstract answers.

---

## 6. Back at the desk

Turning paper into the gate-passing pack:

1. Photograph the filled sheets. Attach one ArtifactRef per section with
   the kind verbatim: `survey_dims` (section 1), `survey_media`
   (section 2), `survey_appliance_sheet` (section 3 — one ref **per
   appliance sheet**), `survey_user_profile` (section 4), `survey_budget`
   (section 5). Artifacts are append-only: a wrong scan is replaced by
   adding a new ref, not editing.
2. Run the checklist (`survey_pack_missing`) from the project record —
   an empty result means the pack is complete.
3. Advance the project: `transition_stage("3_layout_design")` now passes;
   with a kind missing it refuses and names the gap — that refusal is the
   system working, not breaking.
4. Feed the elbow value into `derive_worktop_height(elbow_mm)` and store
   the result on `ProjectDefaults` (worktop, wall line, tall line).
5. **File the two pending validation attestations** — both specs carry a
   "Validation: … attestation pending" line waiting on exactly this
   visit: `kitchen-erp/docs/specs/survey-pack.md` (did the checklist
   match what the room demanded?) and
   `kitchen-erp/docs/specs/height-parameter-set.md` (does the derived
   band suit the client's body?). File them UNVERIFIED with `--ttl-days`
   and cite the ids from those specs' Validation lines.

### 6.1 European-practice cross-check (advisory — the playbook stays as written)

The playbook's numbers checked against EN 1116 coordinating sizes and
common European ergonomic guidance. Where practice adds nuance, it is
stated here as advisory; do not edit the playbook from this sheet.

- **Worktop band.** Playbook says 850..910 (= 720 carcass + 100..150
  plinth + 38 top). EN 1116 coordinating heights name 850 and 900 as the
  planes appliances are built to — the band is compatible. Advisory:
  current European practice trends taller (900–940) for users above
  ~1750 mm; the elbow formula outranks the band, and an in-band number
  that contradicts a measured elbow is the wrong number.
- **Top thickness.** Playbook arithmetic assumes a 38 mm top. Common
  European practice increasingly uses 12–28 mm (compact laminate, thin
  stone); with a thin top the plinth/legs must absorb the difference to
  hold the decided line — flag it when the client picks a thin worktop.
- **Wall-unit clearance.** Playbook fixes a wall-unit line but not the
  clearance number. Common European practice: bottom of wall units
  450–600 mm above the worktop (500 typical; below 450 the blat becomes
  unusable for small appliances) — record the client's reach before
  choosing.
- **Hood height.** Playbook says ≥650 electric / ≥750 gas above the hob.
  Common European practice agrees as a safe floor, with nuance: some
  induction-hood sheets permit 550–600, and gas minimums are
  manufacturer-binding — the appliance sheet from section 3 outranks
  both numbers.
- **Split working heights.** Playbook fixes one worktop line per project.
  European ergonomic guidance (AMK/DIN-derived) distinguishes zones: sink
  comfortable slightly higher, hob slightly lower (pot rim adds
  ~100 mm to the working plane). One continuous line is a legitimate
  simplification for a joined worktop — but a client who bakes or cans a
  lot may deserve the conversation.
- **Work triangle.** Playbook says 3.6–6.6 m total. NKBA-derived guidance
  allows up to ~7.9 m; the tighter upper bound is stricter than common
  practice and rarely hurts in the small Polish kitchens P1-class
  projects will see — keep it, knowing it is conservative.
