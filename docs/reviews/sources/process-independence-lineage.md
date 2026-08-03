# Process, independence, and why measurement corrupts — a source lineage (2026-08-03)

> Reader: whoever is deciding how much verification machinery this repo
> carries, and anyone who wants to check the historical claims in the doctrine
> and scratch-design documents against what the sources actually say |
> Enables: citing this literature without re-deriving it, seeing which of our
> controls are validated and which are folk memory, and buying the four books
> that would close the remaining gaps | Update-trigger: a source in §13 moves
> from ATTRIBUTED to VERIFIED (or is refuted), a purchase in §12 is made and
> read, or a finding in §11 is acted on or overturned

Companions: [`../agentic-verification-doctrine-2026-08-03.md`](../agentic-verification-doctrine-2026-08-03.md)
(the historical mapping and adoption plan) and
[`../verification-system-scratch-design-2026-08-03.md`](../verification-system-scratch-design-2026-08-03.md)
(the target design). Those two documents *name* this literature. This one
reads it. Where they disagree with the sources, §11 says so.

---

## 0. How to read the citation labels

The whole point of this project is evidence that cannot lie, so the
bibliography is held to the same standard as a truth-ledger claim.

- **VERIFIED** — I retrieved the source text itself (or a page of it) in this
  session and read the passage being cited. Quotations marked VERIFIED are
  transcribed from that retrieved text.
- **ATTRIBUTED** — consistently and widely reported, but I did not reach the
  primary. Wording may be a secondary source's paraphrase. No quotation is
  presented as verbatim unless it came from text I actually retrieved.
- **UNCERTAIN** — a lead worth checking, recorded so it is not lost. Not a
  fact.

No page number, DOI, ISBN or quotation in this document was reconstructed from
memory. Where a page range is conventional rather than confirmed, it says so.
Where a date could not be pinned, it says "circa" and gives the reason.

Sources reached in full text: Fagan 1976; Bacchelli & Bird 2013; Sadowski et
al. 2018; Clark & Wilson 1987; Campbell 1976; CAIB 2003 p. 191; Feynman 1986;
Austin 1996 (front matter, contents, chapters 1–3); Wagner (circa 2006); Cook
(1998–2000). Sources reached only through reliable secondary material:
Gilb & Graham 1993; IEEE 1012; Vaughan 1996; Goodhart 1975; Perrow 1984;
Weick & Sutcliffe 2001. §12 lists what buying would buy us.

---

## 1. Fagan (1976) — the control that worked on 2026-08-02

**VERIFIED.** M. E. Fagan, "Design and code inspections to reduce errors in
program development", *IBM Systems Journal*, Vol. 15, No. 3, 1976,
pp. 182–211. DOI `10.1147/sj.153.0182` (per the ACM Digital Library listing;
the page header "182 FAGAN IBM SYST J" is visible in the retrieved scan).
Full text retrieved and read.

### Problem

Programming had no measurable checkpoints. Fagan's framing sentence is
managerial, not technical: "Successful management of any process requires
planning, measurement, and control. In programming development, these
requirements translate into defining the programming process in terms of a
series of operations, each operation having its own exit criteria." Without
that, error rework lands late, where it is expensive, and nobody can say how
complete the product is at any point.

### Evidence they had

Two studies, and they are different studies reporting different things. The
doctrine document, and most citations of Fagan generally, blur them.

**Study A — coding productivity, systems programming.** A piece of the design
of a large operating system component, structured, "judged to be of moderate
complexity", designed by three programmers and coded by thirteen, in PL/S.
Inspected at I₁ (design-complete, 100 %), I₂ (code at first clean compilation,
100 %) and I₃ (unit-test inspection). Result: "This net saving translated
into a **23 percent increase in the productivity of the coding operation
alone**." A control sample was drawn at random *after* I₁ and I₂ had become
routine, explicitly "to normalize for Hawthorne effect". Component figures
from the same study: net savings in programmer-hours per K.LOC of I₁: 94,
I₂: 51, I₃: −20; rework of I₁: 78, I₂: 36. Quality: "AN INSPECTION SAMPLE HAD
**38 % FEWER ERRORS/K LOC** THAN A WALK-THROUGH SAMPLE DURING EQUIVALENT
TESTING BETWEEN POST UNIT TEST AND SYSTEM TEST IN THIS STUDY."

**Study B — Aetna, applications programming.** An eight-module COBOL program,
**4,439 non-commentary source statements**, written by two programmers at
Aetna Life and Casualty, Hartford, June 1975, with three to five inspection
participants. The only process change was adding I₁ and I₂. An automated
estimator predicted 62 programmer-days; actual was 46.5 including inspection
meeting time — "The resulting saving in programmer resources was 25 percent."
Table 1 ("Error detection efficiency") reports errors found per K.NCSS:
design I₁ + code I₂ inspections **38 per K.NCSS = 82 % of total errors found**;
unit test and preparation for acceptance test 8 per K.NCSS = 18 %; acceptance
test 0; actual usage over six months 0; total 46 per K.NCSS.

**The famous 82 % is Study B**, and Fagan says so directly: "The inspections
were obviously very thorough when judged by the inspection error detection
efficiency of 82 percent". For systems programming he reports a materially
lower number: "approximately two thirds of all errors reported during
development are found by I₁ and I₂ inspections prior to machine testing", and
then, pointedly, "The error detection efficiencies of the I₁ and I₂
inspections separately are, of course, less than 66 percent."

Three caveats that citations routinely drop. The 25 % saving is measured
against an *estimate*, not a control group. The 82 % is a share of *errors
found* within six months, not of errors existing. And both studies are single
projects, one of them under 4,500 statements.

### Reasoning

Rework cost rises with lateness — Fagan's repeated figure is that rework at
inspection time is "10 to 100 times less expensive than if it is done in the
last half of the process". So the return does not come from finding *more*
errors; it comes from finding them *earlier* and in *batches*, which shortens
total rework even inside the coding operation.

Independence is engineered in, not hoped for. The moderator "must be a
competent programmer but need not be a technical expert on the program being
inspected. **To preserve objectivity and to increase the integrity of the
inspection, it is usually advantageous to use a moderator from an unrelated
project.**" And the author-exclusion rule is explicit: "If the coder of a
piece of code also designed it, he will function in the designer role for the
inspection process; a coder from some related or similar program will perform
the role of the coder. If the same person designs, codes, and tests the
product code, the coder role should be filled as described above, and another
coder — preferably with testing experience — should fill the role of tester."

The team is deliberately small: "Four people constitute a good-sized
inspection team… The team size should not be artificially increased over
four."

### Proposed solution

Four roles — **moderator, designer, coder/implementor, tester** — and five
operations: **overview, preparation, inspection, rework, follow-up**.

Entry criteria are concrete: I₁ enters when the design meets "Design Level 4
exit criteria (a level of detail of design at which one design statement would
ultimately appear as three to 10 code instructions)"; I₂ enters when the code
reaches "the first clean compilation".

Exit is equally concrete: "rework of all known errors up to a particular point
must be complete before the associated checkpoint can be claimed to be met for
any piece of code." And follow-up has a re-inspection trigger: "If more than
five percent of the material has been reworked, the team should reconvene and
carry out a 100 percent reinspection."

The rate limits are the part everyone forgets. Table 3, systems programming,
lines of code per hour: overview 500 (design only); preparation 100 (I₁) /
125 (I₂); **inspection 130 (I₁) / 150 (I₂)**; rework 20 (I₁) / 16 (I₂)
hours per K.NCSS. Applications rates (Table 2, NCSS/hour) are "four to six
times faster": preparation 898/709, inspection 652/539. Total effort for one
I₁ or I₂ with four people in systems programming is "about 90 to 100
people-hours". And there is a fatigue limit: "the error detection efficiency
of most inspection teams tends to dwindle after two hours of inspection…
it is advisable to schedule inspection sessions of no more than two hours at
a time. Two two-hour sessions per day are acceptable."

One objective at a time: "no specific solution hunting is to take place during
inspection. (The inspection is *not* intended to redesign, evaluate alternate
design solutions, or to find solutions to errors; it is intended just to find
errors!) A team is most effective if it operates with only one objective at a
time." The moderator reports in writing "within one day".

And — this is the passage that matters most for our F1 problem, written a year
before Goodhart's paper was widely read and in the same document as the
method — Fagan forbids using the data to appraise people:

> "feedback of results from inspections must be counted for the programmer's
> use and benefit: they should not under any circumstances be used for
> programmer performance appraisal."

His defence against the obvious objection is purely anecdotal, and he says so:
three years, "hundreds of experienced programmers and tens of managers, and so
far he has found no case in which inspection results have been used negatively
against programmers. Evidently no manager has tried to 'kill the goose that
lays the golden eggs.'"

### What happened to it

Formal inspection became the standard reference method and the ancestor of
every later review practice, but its measured effectiveness did not hold at
Fagan's headline level once the field pooled results. Wagner's literature
survey (§2) puts inspection effectiveness at **mean 34.14 %, median 30 %,
range 8.5 %–92.7 %** across studies. Full Fagan inspection is now rare in
industry; what survived is the lightweight, asynchronous, tool-mediated
descendant measured by Bacchelli & Bird and Sadowski et al. (§3).

### Relevance to us

The doctrine calls F6 "the oldest and best-validated control in the whole
catalogue" and it is right about the *practice*. But we inherited only the
one rule we already liked (author ≠ inspector) and none of the machinery that
Fagan's numbers actually depend on: entry criteria, a bounded checking rate,
a session-length limit, a single objective, a re-inspection threshold, and a
one-day written report. See §11.4 and §11.11.

---

## 2. Gilb & Graham (1993) — what they added, and what the field then measured

**VERIFIED (bibliography).** Tom Gilb and Dorothy Graham, *Software
Inspection*, Addison-Wesley, 1993, ISBN 0-201-63181-4. Confirmed via multiple
independent bookseller and library records and a 1995 review in the *Journal
of Software Maintenance: Research and Practice*.
**ATTRIBUTED (contents).** I did not reach the book. Everything below about
its internals is either from a peer-reviewed paper that cites it directly, or
labelled as second-hand.

### Problem

Fagan's inspection worked but was expensive, inconsistently applied, and
positioned as a defect-*removal* activity. Seventeen years on, the open
questions were: how do you make it repeatable, how do you make it cheaper by
inspecting less, and how do you make the defects you find feed back into the
process that produced them?

### Evidence they had

**ATTRIBUTED.** Roughly two decades of industrial inspection data from IBM and
from Gilb's consulting practice across European organisations. I could not
verify which case studies the book reports or their numbers, so none are
quoted here.

### Reasoning

**ATTRIBUTED.** Two arguments. First, inspection is a *measurement* instrument
for document quality, not only a defect filter: if you can estimate defect
density per page, you can decide whether a document is fit to leave its stage
at all, and you can do that from a **sample** rather than a full read.
Second, finding the same defect class repeatedly is a process signal, so
inspection should include a step that attacks the cause rather than the
instance.

### Proposed solution

**ATTRIBUTED.** A more granular process than Fagan's five operations —
commonly reported as *entry, planning, kickoff, individual checking, logging
meeting, process brainstorming, edit, follow-up, exit* — with entry and exit
promoted to explicit, gated steps, and a process-improvement step separated
from defect logging.

**VERIFIED (via a citing paper).** The concrete measured parameter they are
best known for is the **optimum checking rate**. Wagner's survey states: "in
[8] the optimal bandwidth of the inspection rate is 1 ± 0.8 pages per hour
where one page contains 300 words", where [8] is Gilb and Graham, *Software
Inspection*, Addison-Wesley, 1993. Wagner adds: "As other authors give
similar figures, we can summarise this easily with saying that the optimal
inspection rate lies about one page per hour. However, the effect of deviation
from this optimum is not well understood."

### What happened to it

**VERIFIED.** The best available synthesis of what inspection is worth is
Stefan Wagner, "A Literature Survey of the Quality Economics of
Defect-Detection Techniques" (arXiv:1612.04590; Institut für Informatik, TU
München — circa 2006, dated from its citation of the author's own 2006
technical report TUM-I0614 and 2006 ISSTA paper; the venue line was not
present in the retrieved copy). Retrieved and read. Its pooled figures for
inspection:

| Measure | Lowest | Mean | Median | Highest |
|---|---|---|---|---|
| Effectiveness (% of defects found) | 8.5 | 34.14 | 30 | 92.7 |
| Efficiency (defects per staff-hour) | 0.16 | 1.87 | 1.18 | 6 |
| Removal cost (staff-hours per defect) | 0.05 | 1.91 | 1.2 | 7.5 |

Wagner's own comment on the spread: "We observe a quite stable mean value that
is close to the median with about 30 %. However, the range of values is huge.
This suggests that an inspection is dependent on other factors to be
effective."

Inspection also has an uneven defect profile. Wagner reports per-type
difficulty for inspections (higher = harder to find): initialisation 35.4,
computation 29.1, control 57.2, interface 53.3, data 79.3, cosmetic 83.3 —
and notes that inspections and tests are hard in *different* places, with
tests averaging about 0.45 difficulty against inspections' 0.65.

The rate discipline survived better than the ceremony. Checking rate is one of
the few inspection parameters that repeatedly shows up as effectiveness-
determining, and it is the one thing Gilb & Graham quantified that later
authors independently corroborated.

### Relevance to us

Two things. The pooled 30 % median is the honest prior for what an
independent verifier finds — not Fagan's 82 %, and not our 4-of-4. And the
one control the field agrees on is a **rate limit**, which we have no analogue
of: an agent verifier reads an arbitrarily large diff in one pass. §11.4.

---

## 3. Modern code review — what it actually catches versus what people believe

This is the most load-bearing section in the document, because it is the only
place where the literature directly contradicts a belief this project is
operating on.

### 3a. Bacchelli & Bird (2013)

**VERIFIED.** Alberto Bacchelli and Christian Bird, "Expectations, Outcomes,
and Challenges of Modern Code Review", *Proceedings of the 35th International
Conference on Software Engineering (ICSE 2013)*, pp. 712–721 (page range per
the ACM Digital Library listing). Full text retrieved from Microsoft Research
and read.

**Problem.** Tool-mediated, lightweight, asynchronous code review had replaced
formal inspection everywhere, on the assumption that it delivers inspection's
benefits more cheaply. Nobody had checked whether it does.

**Evidence they had.** A mixed-method study at Microsoft around the CodeFlow
review tool: structured interviews (30–50 minutes) with 23 people in different
roles conducted by an external vendor; observations and interviews with
developers, 40–60 minutes each, continued to saturation; a card sort;
**manual inspection and classification of 570 review comments** drawn from
"dozens of independent projects"; and surveys of **165 managers and 873
programmers**.

**Reasoning and findings.** Expectations first. "Almost all the managers
included 'finding defects' as one of the reasons for doing code reviews; for
44 % of the managers, it is the top reason." For developers and testers,
"'finding defects' is the first motivation for code review for 383 of the
programmers (44 %), second motivation for 204 (23 %), and third for 96
(11 %)." The paper then notes, correctly, "This is in-line with the reason why
code inspections were devised in the first place."

Outcomes second. Of the 570 classified comments:

| Category | Count | Share |
|---|---|---|
| Code improvements (readability, unused code, better practices) | 165 | 29 % |
| **Defects** (4th of 9 categories) | **78** | **14 %** |
| Knowledge transfer (explicit) | 12 | ~2 % |

Within the 78 defect comments: "65 are on logical issues (e.g., a wrong
expression in an if clause), 6 on high-level issues, 5 on security, and 3 on
wrong exception handling."

The authors tested and rejected the obvious explanations — sample too small,
changes unusually clean, misclassification — by triangulating against the
interviews and surveys, and then stated the finding plainly:

> "the outcome of code review does not match the main expectation of both
> programmers and managers — finding defects. Review comments about defects
> are few, comprising one-eighth of the total in our sample, and mostly
> address 'micro' level and superficial concerns; while programmers and
> managers would expect more insightful remarks on conceptual and design level
> issues."

**Their explanation, which is the useful part.** The bottleneck is not
attention or diligence — it is **context**. "Many interviewees eventually
acknowledged that understanding is their main challenge when doing code
reviews." A senior developer: "the most difficult thing when doing a code
review is understanding the reason of the change." A tester: "the biggest
information need in code review: what instigated the change." And developers
"confirm that 'not knowing files (or [dealing with] new ones) is a major
reason for not understanding a change.'" The paper reports that when they
asked how much understanding each outcome required, "the outcome that stands
out from an understanding perspective is 'finding defects,' immediately
followed by 'alternative solutions.'"

So: **defect-finding is the outcome that requires the most context, and
reviewers are the participants with the least.** That is the mechanism.

**What happened to it.** It became the standard citation for what modern code
review is for, and it shifted the field's stated justification from defect
detection toward knowledge transfer, shared ownership and maintainability.

### 3b. Sadowski et al. (2018) — the follow-up, at scale

**VERIFIED.** Caitlin Sadowski, Emma Söderberg, Luke Church, Michal Sipko,
Alberto Bacchelli, "Modern Code Review: A Case Study at Google",
*ICSE-SEIP '18*, May 27 – June 3 2018, Gothenburg, Sweden. Full text
retrieved and read.

**Evidence.** 12 semi-structured interviews; an internal survey with **44
valid responses (45 % response rate)**; and analysis of review logs covering
approximately **9 million reviewed changes over two years**.

**Findings, verbatim where numeric.** Change size: "over 35 % of the changes
under consideration modify only a single file and about 90 % modify fewer than
10 files. Over 10 % of changes modify only a single line of code, and **the
median number of lines modified is 24**." Reviewer count: "fewer than 25 % of
changes have more than one reviewer, and over 99 % have at most five reviewers
with **a median reviewer count of 1**. … even very large changes on average
require fewer than two reviewers." Latency: median under an hour for small
changes, about five hours for very large ones. Reviewer load: "developers
spend an average of 3.2 (median 2.6 hours a week) reviewing changes."

And the sentence that should be read next to Bacchelli & Bird's 14 %: of the
44 survey respondents, "**Only 2 respondents said the comments had found a
bug.**"

**What they conclude the process is for.** The paper's stated themes for
review at Google are "education, maintaining norms, gatekeeping, and accident
prevention", and the focus "is on education as well as code maintainability".
Defect-finding is not the primary claim.

**On reviewer count** the paper quotes the prior result it is contrasting
with: Rigby and Bird "found this number to be two, remarkably regardless of
whether the reviewers were explicitly invited… and concluded that two
reviewers find an optimal number of defects." (Peter C. Rigby and Christian
Bird, "Convergent contemporary software peer review practices", ESEC/FSE 2013
— **ATTRIBUTED**, reached only through Sadowski's citation of it.) Google, by
contrast, converged on one reviewer plus small changes plus fast turnaround.

### Relevance to us

Directly, and uncomfortably. The doctrine's §5.2 proposes measuring "how many
findings the verifier caught that the filer missed", records that it was 4 of
4 on 2026-08-02, and offers two interpretations if the number falls: the work
got better, or the verifiers stopped being independent. **The literature
supplies a third and far more likely one — reversion to the field's normal
rate**, which is a minority of issues, mostly shallow ones. See §11.2.

More usefully: if the binding constraint on defect-finding is *understanding*,
then independence and effectiveness trade off against each other, because
independence is precisely the removal of context. §11.3.

---

## 4. IEEE 1012 and IV&V — what "independence" formally means

**ATTRIBUTED (the standard).** IEEE Std 1012, *IEEE Standard for System,
Software, and Hardware Verification and Validation* (editions include 1998,
2004, 2012 and 2016; NASA and California state guidance in circulation cites
the 2012 edition). The standard itself is paywalled and I did not reach it.
The three-parameter framing and the substance of the definitions below are
consistently reported by NASA, the SEI, and US federal IV&V guidance.

**VERIFIED (NASA's own statements).** From the NASA IV&V programme's public
overview page:

- Purpose, the two questions: verification — "Are we building the product
  right?"; validation — "Are we building the right product?"
- What IV&V is: "Software IV&V is a systems engineering process employing
  rigorous methodologies for evaluating the correctness and quality of the
  software product throughout the SDLC."
- **Managerial independence**: "responsibility for the IV&V effort to be
  vested in an organization separate from the organization responsible for
  performing the system implementation."
- **Financial independence**: "the IV&V budget be vested in an organization
  independent from the development organization." NASA implements this
  literally — its IV&V programme is funded from the Mission Support
  Directorate, not from the projects it audits.
- **Technical independence**: NASA's page paraphrases it as practitioners who
  "assess development processes using expertise independent of developers".

**ATTRIBUTED (the fuller rationale).** The reasoning attached to each
parameter in IEEE 1012's independence annex, as reported by federal IV&V
guidance and the SEI:

- *Technical* — the IV&V team must form its **own** understanding of the
  problem and of how the system solves it, rather than accepting the
  developer's. The stated purpose is a "fresh viewpoint", on the grounds that
  subtle errors are precisely the ones invisible to people too close to the
  solution.
- *Managerial* — the independent organisation chooses **what** to analyse,
  **which** techniques to use, **when**, and **which** findings to pursue, and
  reports results without prior approval from the development group. Without
  this, the audited party controls the audit's scope.
- *Financial* — control of the IV&V budget sits outside the development
  organisation, so that IV&V work cannot be curtailed, delayed or defunded by
  diverting money under project schedule pressure.

**VERIFIED (when it is required).** NASA's Software Engineering Handbook
(SWE-141) requires IV&V for Category 1 projects per NPR 7120.5, Category 2
projects with Class A or Class B payload risk classification per NPR 8705.4,
and projects explicitly selected by the Mission Directorate Associate
Administrator.

### Why anyone thought all three were necessary

Because each defeats a different attack on the finding, and each is
individually insufficient:

- Technical independence alone → an outsider who forms their own view, but
  whose manager is the project manager. Findings get softened before they
  leave the room.
- Technical + managerial → findings leave the room intact, but the work stops
  when the budget is reallocated in the month before a milestone.
- Financial alone → funded, but the scope of what gets looked at is chosen by
  the party being examined.

The three parameters are not three flavours of the same thing; they are three
distinct control points — *what you look at*, *what you may say*, and
*whether you get to finish*.

### Relevance to us

Our `filer ≠ verifier` rule is **technical independence only**. The other two
have no analogue and, in a one-person shop with agents, mostly cannot have
one: the same person defines the verifier's task (managerial) and pays for
its tokens and time (financial). That is worth naming honestly rather than
implying that "independent verification" here means what it means in IEEE
1012. The practical residue of managerial independence that *is* available:
the verifier, not the filer, should choose what to examine. Today the filer's
hand-off usually scopes it. §11.7.

---

## 5. Clark & Wilson (1987) — separation of duty as a security mechanism

**VERIFIED.** David D. Clark (Senior Research Scientist, MIT Laboratory for
Computer Science) and David R. Wilson (Director, Information Security
Services, Ernst & Whinney), "A Comparison of Commercial and Military Computer
Security Policies", *Proceedings of the 1987 IEEE Symposium on Security and
Privacy*, Oakland, California. Conventionally cited as pp. 184–194; p. 186 is
visible in the retrieved scan. Full text retrieved and read.

### Problem

Computer security research had been built around the military problem —
preventing **disclosure** of classified information, formalised as a lattice
model. The authors' opening argument is that this is the wrong model for the
commercial world: "for that core of data processing concerned with business
operation and control of assets, the primary security concern is data
integrity." A bank does not primarily fear that you read the ledger; it fears
that you change it.

### Evidence they had

Centuries of accounting practice, and Wilson's professional vantage point
inside a Big Eight audit firm. Notably, they also had a concrete failure of
the military framing applied to commercial products: they note that RACF,
ACF/2 and CA-TopSecret had been evaluated against the Orange Book and "The C
ratings that these security packages received would indicate that they did not
meet the mandatory requirements of the security model as described in the
Orange Book" — the model mis-scored real commercial integrity controls.

### Reasoning

This is the part that turns out to matter most for us. They split integrity
into two kinds, and the split is about *what a computer can check*:

- **Internal consistency** — enforced by *well-formed transactions*, of which
  double-entry bookkeeping is the archetype: "any modification of the books
  comprises two parts, which account for or balance each other… If an entry is
  not performed properly, so that the parts do not match, this can be detected
  by an independent test (balancing the books)."
- **External consistency** — "the correspondence between the data object and
  the real world object it represents." And then the decisive sentence:
  **"Because computers do not normally have direct sensors to monitor the real
  world, computers cannot verify external consistency directly."**

Separation of duty exists because of that second gap. Since the machine cannot
check correspondence with reality, you get it indirectly: "the correspondence
is ensured indirectly by separating all operations into several subparts and
requiring that each subpart be executed by a different person." Their worked
example is purchasing: authorise the purchase order, record arrival of the
item, record arrival of the invoice, authorise payment. "If one person can
execute all of these steps, then a simple form of fraud is possible, in which
an order is placed and payment made to a fictitious company without any actual
delivery of items. In this case, the books appear to balance; the error is in
the correspondence between real and recorded inventory."

Note what that says: **internal consistency can be perfect while the whole
thing is a lie.** The books balance. The gate is green.

### Proposed solution

Their most basic rule, verbatim:

> "Perhaps the most basic separation of duty rule is that any person permitted
> to create or certify a well-formed transaction may not be permitted to
> execute it (at least against production data). This rule ensures that at
> least two people are required to cause a change in the set of well-formed
> transactions."

And the limit of the mechanism, also verbatim, which they state rather than
hide:

> "The separation of duty method is effective except in the case of collusion
> among employees. For this reason, a standard auditing disclaimer is that the
> system is certified correct under the assumption that there has been no
> collusion. While this might seem a risky assumption, the method has proved
> very effective in practical control of fraud."

Their hardening measure against collusion is randomisation: "Separation of
duty can be made very powerful by thoughtful application of the technique,
such as random selection of the sets of people to perform some operation, so
any proposed collusion is only safe by chance."

### What happened to it

The Clark-Wilson model became one of the two canonical integrity models and
the theoretical basis for separation-of-duty requirements in commercial
security, audit standards and later in role-based access control.

### Relevance to us

Two findings, one supporting and one alarming.

Supporting: the scratch design's **invariant / testimony** split is
Clark & Wilson's **internal / external consistency** split, rediscovered from
churn statistics in 2026 rather than from fraud control in 1987. "Computers do
not have sensors on the real world" is the exact justification for why
testimony records cannot have evidence commands. That is a strong independent
confirmation that the partition is the right one — worth saying, because the
scratch design lists "whether this is novel" as an open question.

Alarming: the whole control **rests on an explicit non-collusion assumption**,
and two agent verifiers running the same model on the same prompt with the
same context are the software equivalent of collusion. §11.7.

Also: their basic rule is *create/certify ≠ execute*, which is stronger than
our filer ≠ verifier. The agent that writes a claim's evidence recipe should
not be the agent that runs it and records the verdict.

---

## 6. Goodhart (1975) and Campbell (1976) — read, not quoted

Both are cited far more than read, and both original formulations are narrower
and more careful than the slogans. Campbell I reached; Goodhart I did not.

### 6a. Goodhart

**ATTRIBUTED.** C. A. E. Goodhart, "Problems of Monetary Management: The U.K.
Experience", in *Papers in Monetary Economics*, Volume I, Reserve Bank of
Australia, 1975. Reported wording, consistent across sources:

> "Any observed statistical regularity will tend to collapse once pressure is
> placed upon it for control purposes."

I did not reach the RBA volume. The bridge used here is the Chrystal & Mizen
line of secondary work on the law's origins, plus consistent encyclopaedic
reporting — sufficient for ATTRIBUTED, not for VERIFIED.

**Problem.** UK monetary policy in the 1970s targeted monetary aggregates
selected because they had historically correlated with nominal income. The
correlations broke down as soon as they were targeted.

**Reasoning.** The claim is about *statistical regularities*, not about
metrics generally. A historical correlation between two variables is evidence
about the world **as it was being generated** — including as it was being
generated by agents who were not optimising against that correlation. Start
controlling one variable and you change the generating process; the regularity
was never a law. It is the same year and the same intellectual moment as the
Lucas critique (1976), and the two are usually read together.

**What happened to it.** Keith Hoskin (1996) and the anthropologist Marilyn
Strathern generalised it out of monetary economics. The slogan everyone quotes
—

> "When a measure becomes a target, it ceases to be a good measure"

— is **Strathern's**, from "'Improving ratings': audit in the British
University system", *European Review*, 1997 (**ATTRIBUTED**). It is not
Goodhart's sentence, and it is a broader claim than his.

**Relevance to us.** The narrow original is arguably *more* applicable to us
than the slogan, not less. "Ledger claims verified per session" is exactly an
observed statistical regularity; the moment it is used to steer, the process
that generated it changes. But the narrow reading also tells us where the law
does *not* bite: an invariant that is a direct, complete test of the property
it names is not a proxy regularity, and targeting it is fine. Goodhart's law
is an argument against **surrogate** measures specifically. That distinction
is what makes the scratch design's invariants defensible.

### 6b. Campbell

**VERIFIED.** Donald T. Campbell, "Assessing the Impact of Planned Social
Change", Paper #8, Occasional Paper Series, Public Affairs Center, Dartmouth
College, December 1976. Full text retrieved and read; the passage below is
from the section headed "Corrupting Effect of Quantitative Indicators",
pp. 49–52 of that paper. (Also published in *Evaluation and Program Planning*
2(1), 1979, pp. 67–90 — **ATTRIBUTED**.)

**Problem.** Social programmes were being evaluated by quantitative
indicators, and Campbell — the field's leading methodologist, arguing *for*
quantitative evaluation — needed to state the failure mode of his own
programme.

**Evidence he had.** Explicitly weak evidence, and he says so: "Let me
illustrate these two laws with some evidence which I take seriously, although
it is **predominantly anecdotal**."

The examples are worth having, because they are more specific than the slogan:

- **Chicago voting versus census.** Voting has elaborate anti-fraud
  machinery, the census almost none — yet voting statistics are distrusted and
  census statistics trusted. His explanation: votes "have had real
  implications as far as jobs, money, and power are concerned — and have
  therefore been under great pressure from efforts to corrupt", while census
  data were not used for political decision-making.
- **Police clearance rates** (citing Skolnick 1966). Two corruptions: not
  recording complaints, or postponing recording them until solved — "simple
  evasions which are hard to check, since there is no independent record of
  the complaints"; and a plea-bargaining interaction in which "a burglar who
  is caught in the act can end up getting a lighter sentence the more prior
  unsolved burglaries he is willing to confess to", sometimes to crimes he did
  not commit.
- **Nixon's crackdown on crime** — "had as its main effect the corruption of
  crime-rate indicators… achieved through underrecording and by downgrading
  the crimes to less serious classifications."
- **Blau (1963), employment offices.** "evaluating staff members by the number
  of cases handled led to quick, ineffective interviews and placements. Rating
  the staff by the number of persons placed led to concentration of efforts on
  the easiest cases, neglecting those most needing the service, in a tactic
  known as 'creaming'."
- **Texarkana performance contracting** (citing Stake 1971). Contractors paid
  on pupils' test-score gains "were teaching the answers to specific test
  items that were to be used on the final play-off testing", and defended
  themselves "with a logical-positivist, operational-definitionalist argument
  that their agreed-upon goal was defined as improving scores on that one
  test."

**The actual formulation.** Verbatim, and note the plural:

> "I come to the following pessimistic **laws** (at least for the U.S. scene):
> The more any quantitative social indicator is used for social
> decision-making, the more subject it will be to corruption pressures and the
> more apt it will be to distort and corrupt the social processes it is
> intended to monitor."

Two distinct claims are packed into that sentence, and the slogan version
usually keeps only the first:

1. **The indicator degrades** — the number stops describing what it described.
2. **The measured process degrades** — the underlying activity gets worse.

Campbell hedged twice in one sentence ("pessimistic", "at least for the U.S.
scene") and then again on the evidence. The people who cite him rarely do.

**What happened to it.** It became "Campbell's law", and it is invoked most
often about standardised testing in education — which is, fairly, one of his
own examples.

**Relevance to us.** The second law is the one that applies to us and the one
we do not usually think about. If we start counting verifier findings, the
first effect is that the count stops meaning what it meant. The second effect
is that **verification itself gets worse** — verifiers optimised for
find-count produce many shallow findings, which is precisely the failure shape
Bacchelli & Bird measured in human reviewers (29 % cosmetic improvements,
14 % defects, mostly micro-level). Those two findings reinforce each other and
that is not a coincidence: Campbell cites Ridgway (1956) and Blau (1963), and
so does Austin.

**VERIFIED (bibliographically, via Austin's permissions page).** V. F.
Ridgway, "Dysfunctional Consequences of Performance Measurements",
*Administrative Science Quarterly*, Vol. 1, No. 2 (September 1956) — the
earliest statement of the whole idea, twenty years before Campbell. Austin
reprints from pp. 243 and 247.
**VERIFIED (partially).** Steven Kerr, "On the folly of rewarding A, while
hoping for B" — the retrieved scan's own header confirms the reprint in *The
Academy of Management Executive*, February 1995, 9(1), p. 7. The original,
*Academy of Management Journal* 1975, 18(4), pp. 769–783, is **ATTRIBUTED**;
the scan was image-only and I could not read the body text, so nothing is
quoted from it.

---

## 7. Austin (1996) — full versus partial supervision

**VERIFIED (front matter, contents, chapters 1–3).** Robert D. Austin,
*Measuring and Managing Performance in Organizations*, Dorset House
Publishing, New York, 1996, ISBN 0-932633-36-6, foreword by Tom DeMarco and
Timothy Lister. Based on Austin's PhD thesis at Carnegie Mellon. The
publisher's sample was retrieved and read in full; it covers the permissions
page, the complete table of contents, the foreword, and chapters one to three.
Chapters 4–19 — which contain the model — are **ATTRIBUTED**, and §12 argues
for buying the book.

### Problem

Organisations measure knowledge work in order to manage it, and the
measurement makes the work worse. Austin wanted to know why — not
anecdotally, but from a model that says under exactly what conditions it
happens and under what conditions it does not.

### Evidence he had

The dysfunction literature back to Ridgway (1956) and Blau's *The Dynamics of
Bureaucracy* (University of Chicago Press, 1955/1963), which he quotes
extensively; the contemporary management-measurement boom, which he documents
with hard numbers (a 1988 Peat Marwick report showing 87 % of surveyed
financial firms had executive incentive plans, 98 % of banks; Hewitt Associates
data showing US companies offering variable pay to all salaried employees
rising from 47 % in 1988 to 68 % in 1993); and — chapter sixteen — his own
interviews with software measurement experts.

### Reasoning

**VERIFIED.** He starts by partitioning *intent*:

> "**Motivational** measurements are explicitly intended to affect the people
> who are being measured, to provoke greater expenditure of effort in pursuit
> of organizational goals."
>
> "**Informational** measurements are valued primarily for the logistical,
> status, and research information they convey…"

And immediately notes the tension: "informational measurement should be
careful not to change the actions of the people being measured, because the
information conveyed by measures is likely to be most representative of actual
events when people being measured behave as if the measurement system did not
exist."

Then his definition of the failure, verbatim:

> "Dysfunction occurs when the validity of information delivered by a system
> of measurement is compromised by the unintended reactions of those being
> measured. **Unintended reactions become possible whenever measures are
> imperfect.**"

And the conclusion of chapter three, which is the sentence that makes this the
deepest treatment of our F1:

> "Unless the latitude to subvert measures can be eliminated (that is, unless
> measures can be made perfect) — a special case — or some means can be
> established for preventing certain kinds of information use (for example, if
> it could be made unthinkable within an organization's culture to use
> measurement to evaluate people), dysfunction seems destined to accompany
> organizational measurement."

DeMarco and Lister's foreword states the shape compactly (VERIFIED): you
"measure `<parameter>` in the hopes of improving `<goal>`", and "When
dysfunction occurs, the values of `<parameter>` go up comfortingly, but the
values of `<goal>` get worse." Their assessment: "dysfunction is not an
exception to the rule; it is the rule."

### Proposed solution — the model

**VERIFIED (structure, from the book's own contents page).** Chapter Seven is
titled "Three Ways of Supervising the Agent" with sections *No Supervision*
(p. 58), *Full Supervision* (p. 60), *Partial Supervision* (p. 62). Chapter
Ten covers "Internal versus External Motivation" and "Delegatory Management";
Chapter Eleven compares delegatory and measurement-based management; Chapter
Twelve handles the case where neither is recommended; Chapter Fourteen is "How
Dysfunction Arises and Persists" and Fifteen "The Cynical Explanation of
Dysfunction".

**ATTRIBUTED (mechanism).** The model has three parties — a **principal**
(manager), an **agent** (worker) and a **customer**. The agent divides effort
across two activities; the customer's satisfaction depends on getting a
particular *mix* of the two. The three regimes:

- **No supervision (delegation).** The principal measures neither activity and
  relies on the agent's internal motivation and knowledge of the customer.
  The agent allocates effort to the mix they believe the customer wants. This
  can be *optimal*.
- **Full supervision.** The principal measures both activities. Incentives can
  be set to produce the customer's preferred mix. Measurement works.
- **Partial supervision.** The principal measures **one** of the two
  activities. The agent, behaving rationally, shifts effort toward the
  measured one. Effort may even go *up*. The customer's outcome goes *down*.

The load-bearing result is that partial supervision can be **worse than no
supervision at all** — that is, worse than not measuring. Dysfunction is
therefore not a property of measurement in general; it is a property of
**incomplete** measurement in the presence of an actor who responds to it.
Austin's recommended alternative where full measurement is impossible is
delegatory management resting on internal motivation, which is why chapters
ten to twelve are about motivation rather than metrics.

His parallel diagnosis of the industry, chapter seventeen ("The Measurement
Disease"), examines the Malcolm Baldrige Quality Award, ISO 9000 certification
and Software Capability Evaluation as instances of the same pattern.

### What happened to it

It is the standard citation in software engineering for why measurement
programmes backfire, largely through DeMarco and Lister's advocacy. It did not
stop the industry measuring; the modern DORA/SPACE line of work is in part a
response to exactly this critique.

### Relevance to us

This is the sharpest tool in the document for our problem, and it reframes F1
usefully. The doctrine calls F1 "accepting a proxy for the property" and marks
it "named, not preventable". Austin's model says it is *conditionally*
preventable, and tells you which condition: **make the measurement complete
for a narrowly-scoped property, or do not measure and delegate — but never sit
in between.**

The truth ledger currently sits in between. It measures the *mechanically
checkable* dimension of a claim — does the recipe run, does the output hash
match — and cannot measure the *load-bearing* dimension — does the sentence
mean what it says, and does it still matter. That is partial supervision in
Austin's precise sense, and the failures of 2026-08-02 are the predicted
consequence: recipes that ran green while the sentence above them was about
something else.

The scratch design's invariant/testimony split is, without knowing it,
Austin's full-supervision/delegation split. An **invariant** is a property
scoped narrowly enough that the measurement is complete for it — full
supervision. **Testimony** is a statement no measurement can reach, recorded
with a source and a date and then trusted — delegation. Austin's model says
that is the right structure and that the danger is anything left in the middle.
§11.6.

---

## 8. Vaughan (1996) — the actual mechanism of normalisation of deviance

**ATTRIBUTED (the book).** Diane Vaughan, *The Challenger Launch Decision:
Risky Technology, Culture, and Deviance at NASA*, University of Chicago Press,
1996 (enlarged edition 2016). Not reached; §12 argues for buying it.
**VERIFIED (the secondary source).** Ronald C. Kramer, "Vaughan, Diane: The
Normalization of Deviance", in Francis T. Cullen and Pamela Wilcox (eds.),
*Encyclopedia of Criminological Theory*, SAGE Publications, 2010, print
pp. 976–980, DOI `10.4135/9781412959193.n269`. Retrieved and read; the Vaughan
quotations below are as given there, with Kramer's own page citations.

### Problem

The Rogers Commission's account of Challenger was that NASA managers, under
schedule and budget pressure, violated safety rules and launched against
engineering advice. Vaughan set out to test that account against the full
archival record and found it did not survive contact with the documents.

### Evidence she had

Primarily archival — NASA's own Flight Readiness Review records, Solid Rocket
Booster work-group documentation, and the Presidential Commission's evidence
volumes — plus targeted interviews. The book is the product of nine years of
work on that corpus.

### Reasoning — and why it is subtler than "people got sloppy"

The conventional reading, and the one our own refusal list gestures at, is
that standards erode because people become lax. Vaughan's finding is close to
the opposite. From Kramer's account:

> "A number of narratives emerged that depicted the NASA managers responsible
> for the launch as **amoral calculators** who had engaged in a variety of
> safety rule violations… But Vaughan's exhaustive research contradicted the
> conventional explanation of calculated managerial wrongdoing."

Vaughan, quoted at 1996, p. 410:

> "No fundamental decision was made at NASA to do evil; rather, a series of
> seemingly harmless decisions were made that incrementally moved the space
> agency toward a catastrophic outcome."

And Kramer's summary of the thesis: "According to Vaughan, it was **not
deviance per se, but conformity** that was responsible for the Challenger
disaster."

The mechanism, as Kramer states it: "over time the work group culture at NASA,
in the context of institutional pressures and aerospace industry norms, began
to **normalize signals of danger** and technical deviations in its official
risk assessments. Since the space shuttle was an experimental technology it
was normal to have technical problems at the agency. **Small changes that were
slight deviations from the normal work process gradually became the norm and
provided the basis for further deviations over time.**" The result was "an
incremental descent into poor judgment" ending in "a cultural belief that it
was safe to fly the shuttle".

Vaughan's own generalisation, quoted at 2007, p. 11:

> "in some social settings deviance becomes normal and acceptable; it is not a
> calculated decision where the costs and benefits of doing wrong are weighed
> because **the definitions of what is deviant and what is normative have been
> redefined within that setting**."

**ATTRIBUTED (the decision sequence).** The repeating five-step pattern
Vaughan identifies is widely reported as: (1) signals of potential danger;
(2) an official act acknowledging escalated risk; (3) review of the evidence;
(4) an official act indicating the normalization of deviance — accepting the
risk; (5) proceed. I did not verify this against the book, and the exact
wording of steps may differ.

Two of her supporting concepts, **structural secrecy** (organisational
structure itself segments and dilutes information so that no one holds the
whole picture) and **culture of production** (the work group's own
professional norms about what counts as an acceptable anomaly), are
**ATTRIBUTED**.

The critical structural point: step 4 is an **official act**. The deviation
does not slip through unnoticed. It is examined, discussed, and formally
accepted — and the acceptance is *recorded*, which is what makes it the new
baseline against which the next deviation is judged.

### What happened to it

"Normalization of deviance" entered general use in safety-critical fields —
aviation, medicine, offshore drilling, and software operations. Vaughan's own
verdict on whether the lesson took: the Columbia Accident Investigation Board
found, seventeen years later, that "NASA had once again normalized a technical
anomaly with catastrophic consequences" (Kramer's summary).

### Relevance to us

The doctrine's refusal 4.11 says a permanently-warning gate trains people to
ignore it, and prescribes: "Either accept the finding into a baseline *with
the reason recorded*, or fix it." Read against Vaughan, **that prescription is
step 4 of her sequence.** Recording a reason is exactly the official act that
converts a deviation into the new normal. The recording is not the safeguard;
it is the mechanism. §11.8.

---

## 9. Columbia (CAIB, 2003), Tufte, and Feynman's precursor

### 9a. The CAIB sidebar

**VERIFIED.** *Columbia Accident Investigation Board Report*, Volume I,
August 2003, **p. 191**, full-page sidebar titled "Engineering by Viewgraphs".
The page was retrieved and read in full, including the reproduced slide and
Tufte's marginal annotations. Tufte's own book — Edward R. Tufte, *The
Cognitive Style of PowerPoint*, Graphics Press, 2003 (2nd edition 2006) — is
**ATTRIBUTED**; the analysis quoted below is as it appears in the CAIB report.

**Problem.** During Columbia's flight, the Debris Assessment Team analysed
whether foam strike damage threatened the orbiter, and presented its
conclusion to the Mission Evaluation Room using Boeing PowerPoint slides.
Management concluded there was no danger. There was.

**The mechanism, precisely.** Not "summaries lose detail". Three specific
things, all verifiable on the reproduced slide:

1. **The title asserts reassurance; the disqualifying fact sits at maximum
   indentation depth.** The slide is headed "Review Of Test Data Indicates
   Conservatism for Tile Penetration". CAIB: "The slide created **six levels
   of hierarchy**, signified by the title and the symbols to the left of each
   line. These levels prioritized information that was already contained in 11
   simple sentences." The caveat that invalidates the whole analysis —
   "Flight condition is significantly outside of test database / Volume of
   ramp is 1920cu in vs 3 cu in for test" — is at the bottom.
2. **The title's subject is not what a reader assumes.** CAIB: "Tufte also
   notes that the title is confusing. 'Review of Test Data Indicates
   Conservatism' refers **not to the predicted tile damage, but to the choice
   of test models used to predict the damage**." Tufte's proposed honest
   headline: "Review of Test Data Indicates **Irrelevance** of Two Models."
3. **A key word carries several incompatible meanings in one document.**
   Tufte, quoted verbatim in the report: "The vaguely quantitative words
   'significant' and 'significantly' are used 5 times on this slide, with de
   facto meanings ranging from 'detectable in largely irrelevant calibration
   case study' to 'an amount of damage so that everyone dies' to 'a difference
   of 640-fold.'"

CAIB's own statement of the scale problem: "Only at the bottom of the slide do
engineers state a key piece of information: that one estimate of the debris
that struck Columbia was **640 times larger** than the data used to calibrate
the model on which engineers based their damage assessments. (Later analysis
showed that the debris object was actually **400 times larger**)."

And the general finding, verbatim:

> "As information gets passed up an organization hierarchy, from people who do
> analysis to mid-level managers to high-level leadership, key explanations and
> supporting information is filtered out. In this context, it is easy to
> understand how a senior manager might read this PowerPoint slide and not
> realize that it addresses a life-threatening situation."

Plus the Board's own experience of the same substitution: "At many points
during its investigation, the Board was surprised to receive similar
presentation slides from NASA officials **in place of technical reports**."

**Relevance to us.** Our agents' reports fail in exactly this shape: a
confident headline verdict, with the qualifier that would change the verdict
placed below it and subordinate to it. The mechanism gives a mechanical test
— see §11.9 — and Tufte's "significant" observation maps directly onto our
reports' unqualified use of *verified*, *confirmed*, and *passes*.

### 9b. Feynman (1986) — the precursor nobody in our documents cites

**VERIFIED.** Richard P. Feynman, "Appendix F: Personal Observations on the
Reliability of the Shuttle", in the *Report of the Presidential Commission on
the Space Shuttle Challenger Accident* (Rogers Commission), 1986. Full text
retrieved and read.

Three passages, all directly applicable to a system built on gates and
evidence.

On the gap between assessed and actual confidence:

> "It appears that there are enormous differences of opinion as to the
> probability of a failure with loss of vehicle and of human life. The
> estimates range from roughly **1 in 100 to 1 in 100,000**. The higher figures
> come from the working engineers, and the very low figures from management…
> we could properly ask 'What is the cause of management's fantastic faith in
> the machinery?'"

On how a passing record becomes evidence of safety — the mechanism Vaughan
later modelled sociologically:

> "We have also found that certification criteria used in Flight Readiness
> Reviews often develop a **gradually decreasing strictness**. The argument
> that the same risk was flown before without failure is often accepted as an
> argument for the safety of accepting it again. Because of this, obvious
> weaknesses are accepted again and again."

And the sentence that ought to be pinned above every green gate:

> "The acceptance and success of these flights is taken as evidence of safety.
> But erosion and blow-by are not what the design expected. They are warnings
> that something is wrong… **Erosion was not something from which safety can
> be inferred.**"

His dissection of the "safety factor of three" argument — that erosion to
one-third of the O-ring radius left "a safety factor of three" — is the
cleanest available account of a measurement being reinterpreted into its own
opposite: "If now the expected load comes on to the new bridge and a crack
appears in a beam, this is a failure of the design. There was no safety factor
at all."

Closing line of the appendix:

> "For a successful technology, reality must take precedence over public
> relations, for nature cannot be fooled."

---

## 10. Why organisations stop believing their own reports — the wider literature

Four strands from 1984 onward that genuinely bear on agent supervision. Kept
short deliberately: each is included because it changes a decision, not
because it is famous.

### 10a. Perrow, *Normal Accidents* (1984)

**ATTRIBUTED.** Charles Perrow, *Normal Accidents: Living with High-Risk
Technologies*, Basic Books, 1984 (Princeton University Press edition 1999).
Reached through encyclopaedic secondary material.

Systems that are both **interactively complex** (components interact in
unplanned, non-obvious ways) and **tightly coupled** (failures propagate
faster than anyone can intervene) will produce accidents that are "normal" —
not in the sense of frequent, but in the sense of *inherent to the design*.
Three Mile Island is the canonical case: individually trivial faults
cascading incomprehensibly.

The finding that matters for us is Perrow's argument that **redundancy
backfires**, by three routes: redundant devices make the system more complex
and so generate new failure modes; responsibility diffuses among more actors;
and the presence of safety measures licenses greater production pressure, so
the system is run faster and closer to its limits.

**Relevance.** Every verification layer in the doctrine's adoption plan is
complexity added to a system that already has gates, a ledger, a tracker and a
spec corpus. The doctrine's risk register names maintenance cost (the FIT
curve). Perrow adds two risks it does not name: diffusion of responsibility
across a growing set of automated checks, and the licence effect — "we have
independent verifiers" is a reason to move faster. §11.13.

### 10b. High Reliability Organization theory / Weick & Sutcliffe

**ATTRIBUTED.** The Berkeley group — Todd LaPorte, Gene Rochlin and Karlene
Roberts — studied US nuclear aircraft carriers, FAA air traffic control and
the Diablo Canyon nuclear plant, and argued the opposite of Perrow: hazardous,
complex organisations *can* operate safely. Karl E. Weick and Kathleen M.
Sutcliffe, *Managing the Unexpected: Assuring High Performance in an Age of
Complexity*, Jossey-Bass, 2001, distilled this into five principles of
"mindful organizing":

1. **Preoccupation with failure** — treat every anomaly as a system-level
   symptom, not a local nuisance.
2. **Reluctance to simplify interpretations** — resist the tidy explanation;
   look across boundaries; value dissenting readings.
3. **Sensitivity to operations** — maintain continuous awareness of what is
   actually happening at the sharp end, not what the plan says.
4. **Commitment to resilience** — build the capacity to detect, contain and
   recover, rather than assuming prevention.
5. **Deference to expertise** — in a crisis, authority migrates to whoever
   knows most, regardless of rank.

**Relevance.** Principle 2 is the direct antidote to the CAIB failure and to
our agents' confident summaries: the summary *is* the simplification. Principle
1 argues against the "accept into a baseline" habit. Principle 5 has an odd but
real reading for us: the agent with the most context on a change is usually the
filer, and our process systematically defers to the verifier instead — which is
correct for independence and wrong for expertise. That tension is real and
unresolved.

### 10c. Cook, "How Complex Systems Fail" (1998–2000)

**VERIFIED.** Richard I. Cook, MD, *How Complex Systems Fail (Being a Short
Treatise on the Nature of Failure; How Failure is Evaluated; How Failure is
Attributed to Proximate Cause; and the Resulting New Understanding of Patient
Safety)*, Cognitive Technologies Laboratory, University of Chicago, copyright
1998–2000. Retrieved and read.

The theses that bear on us, quoted:

- **3.** "Catastrophe requires multiple failures – single point failures are
  not enough." — "Overt catastrophic failure occurs when small, apparently
  innocuous failures join to create opportunity for a systemic accident."
- **5.** "Complex systems run in degraded mode." — "complex systems run as
  broken systems. The system continues to function because it contains so many
  redundancies and because people can make it function, despite the presence of
  many flaws."
- **7.** "Post-accident attribution to a 'root cause' is fundamentally wrong."
  — "there is no isolated 'cause' of an accident. There are multiple
  contributors to accidents."
- **8.** "Hindsight biases post-accident assessments of human performance." —
  "Hindsight bias remains the primary obstacle to accident investigation."
- **9.** "Human operators have dual roles: as producers & as defenders against
  failure."

**Relevance.** Thesis 5 is the honest description of this repo: 131 live
claims, 75 retracted, gates with undeclared blind spots, and it works anyway.
Thesis 7 and 8 qualify the 2026-08-02 post-mortem directly — "four defects,
all caused by self-assessment" is a root-cause story told with hindsight. The
useful reframing from thesis 9: an agent is simultaneously the producer of
work and a defender against failure, and the two roles compete for the same
context window.

### 10d. Blameless post-mortems

**ATTRIBUTED.** John Allspaw, "Blameless PostMortems and a Just Culture", Etsy
*Code as Craft* engineering blog, May 2012 (the post is well known and
consistently attributed; I could not retrieve it in this session, so the exact
date is unconfirmed). Its intellectual sources are Sidney Dekker's work on just
culture and the "second story", and Cook and Woods on complexity in safety.

The argument: an engineer who expects sanction for an error reports less of it,
and reports it later and less accurately. Since the organisation's only access
to what actually happened runs through that person's account, punishing the
account destroys the data. The remedy is to make the account safe — ask what
made the action reasonable *at the time*, with the information then available.

**Relevance.** The agent-supervision analogue is not about feelings; it is
about the report. If an agent's output is graded on whether it found the
"right" answer, the incentive is to produce a confident answer. If it is
graded on whether its account of what it checked, what it could not check, and
what it assumed is accurate, the incentive points the other way. This is the
practical bridge between Austin (§7) and the report-shape problem (§9). See
§11.10.

### 10e. Leads not followed

- **UNCERTAIN.** McIntosh, Kamei, Adams and Hassan, "The impact of code review
  coverage and code review participation on software quality" (MSR 2014).
  Reported to find that review *coverage* alone is a weak predictor of
  post-release defects and that *participation* matters more. Both candidate
  URLs 404'd; the finding is not confirmed and should not be cited until it is.
- **UNCERTAIN.** Chrystal & Mizen, "Goodhart's Law: Its Origins, Meaning and
  Implications for Monetary Policy" (circa 2001–2003, prepared for a
  Festschrift for Charles Goodhart). Would settle §6a properly. Not retrieved.
- **UNCERTAIN.** Nancy Leveson's STAMP/STPA line of work as a systems-theoretic
  alternative to both Perrow and HRO. Plausibly relevant to gate design; not
  investigated here.

---

## 11. What this lineage says we got wrong or missed

Ordered by how much it should change what we do. Items 1–4 are the ones worth
acting on.

### 11.1 The headline number we are implicitly relying on does not exist

The doctrine calls F6 "the oldest and **best-validated** control in the whole
catalogue" and cites Fagan. The *practice* is well validated. The
*effectiveness* is not. Fagan's 82 % comes from one 4,439-statement COBOL
program written by two people; his systems-programming figure in the same paper
is "approximately two thirds", and he explicitly says the individual
inspections are below 66 %. The pooled literature (Wagner) gives **mean 34 %,
median 30 %, range 8.5–92.7 %**. Any planning that assumes independent
verification catches most defects is assuming the top decile of a very wide
distribution.

### 11.2 Our 4-of-4 is a small sample, and the literature predicts it will fall

Doctrine §5.2 records that on 2026-08-02 the verifiers found 4 of 4 defects,
and offers two readings if the number declines: the work improved, or the
verifiers stopped being independent. The literature supplies a third and more
probable one: **regression to the field's normal rate**. Bacchelli & Bird found
14 % of review comments concerned defects, "mostly address 'micro' level and
superficial concerns". Sadowski found that of 44 surveyed Google developers,
"Only 2 respondents said the comments had found a bug." One session with two
adversarially-tasked verifiers on a known-suspect body of work is a favourable
special case, not a rate. Treat 4-of-4 as an existence proof that the control
*can* fire, not as a baseline.

### 11.3 Independence and effectiveness trade off, and we optimised the wrong one

This is the most valuable finding in the document and it undercuts our own
conclusion. Bacchelli & Bird's explanation for why review finds so few real
defects is **not** insufficient independence — it is insufficient
**understanding**. "understanding is their main challenge when doing code
reviews"; the outcome requiring the most understanding is, precisely, finding
defects; and unfamiliarity with the files is "a major reason for not
understanding a change".

Independence is the *deliberate removal of context*. So every increment of
independence costs effectiveness on exactly the axis we care about. Fagan knew
this and paid for it: the **overview** step exists to transfer context to the
inspectors, the **reader** paraphrases the design aloud so misunderstanding
surfaces, and **checklists** of historically frequent error types tell
inspectors where to look. We adopted the independence and none of the context
transfer. Our verifier agents start cold with a diff.

**Actionable:** spend on the verifier's briefing, not on more verifiers. A
verifier prompt should carry the change's *intent*, the acceptance criteria,
the known blind spots of the gates involved, and a checklist derived from the
nine failure modes — Fagan's overview, reader and checklist steps, adapted.
This is cheap and is not in the adoption plan.

### 11.4 We copied one Fagan rule and skipped the ones his numbers depend on

Adopted: author ≠ inspector. Not adopted, and all present in the 1976 paper:

| Fagan control | Our analogue |
|---|---|
| Entry criteria before inspection starts (clean compilation; design level 4) | none — verifiers are launched at whatever state the work is in |
| Bounded checking rate (130–150 loc/hr systems; Gilb & Graham ~1 page/hr) | none — a verifier reads an arbitrarily large diff in one pass |
| Session limit (2 hours; efficiency "dwindles after two hours") | none |
| One objective: find errors, do not design solutions | none — our verifiers routinely propose fixes |
| Re-inspect if >5 % of material reworked | none |
| Written report within one day; moderator confirms every issue resolved | partial — reports exist; resolution confirmation is manual |
| Team of four, "should not be artificially increased over four" | we scaled by adding verifiers |

The rate limit is the single control the empirical literature most consistently
associates with inspection effectiveness, and it is the cheapest of these to
implement: cap the diff size handed to one verifier pass, and split larger
changes. Sadowski's Google data agrees from the other direction — median change
24 lines, median one reviewer, and change size treated as the primary quality
lever ("developers are strongly encouraged to make small, incremental
changes").

### 11.5 We are about to do the thing Fagan forbade, with the mitigation Austin says fails

Fagan, 1976: inspection results "should not under any circumstances be used for
programmer performance appraisal". Doctrine §5.2 proposes recording verifier
find-counts per audit and mitigates with "Do not turn this into a target"
(§4.8).

Austin's chapter three closes off exactly that mitigation: motivational and
informational uses of a measurement **cannot be segregated by intent** once the
number exists and is visible, and "dysfunction seems destined to accompany
organizational measurement" unless the measure can be made perfect or the
motivational use can be made *unthinkable*. Fagan's own defence was anecdotal —
three years, no observed misuse, "no manager has tried to kill the goose".

And Campbell's formulation is **two** laws, not one. The first (the count stops
meaning anything) is the one we guarded against. The second — "the more apt it
will be to **distort and corrupt the social processes it is intended to
monitor**" — is the dangerous one: verifiers optimised toward a find-count
produce many shallow findings, which is precisely the 29 %-cosmetic /
14 %-defect distribution Bacchelli & Bird measured.

**Actionable:** do not persist a per-verifier or per-session find-count at all.
If the retrospective is worth doing, record the *findings* and read them; do
not record the *number*. A number that exists will eventually be compared.

### 11.6 Austin reframes F1 from "unpreventable" to "conditionally preventable"

The doctrine marks F1 "named, not preventable". Austin's model is more useful
than that: dysfunction is a property of **partial** supervision, not of
measurement. Full supervision (measure every dimension that matters, which is
achievable only for a narrowly-scoped property) works. No supervision
(delegate, and trust internal motivation and context) works. **Only the middle
is dysfunctional, and the middle can be worse than not measuring at all.**

The ledger currently occupies the middle: it measures whether a recipe runs and
whether an output hash is stable, and cannot measure whether the sentence above
means what it says or still matters. That is the exact generator of
`tr-ce5c7845`.

Supporting news: the scratch design's invariant/testimony split *is* Austin's
full-supervision/delegation split, arrived at independently. An invariant is a
property scoped narrowly enough that measurement is complete. Testimony is a
statement no measurement can reach, delegated to a dated source. The design's
implicit rule — nothing may sit between the two — is Austin's result, and it is
worth stating that way in the design, because it converts a taxonomy preference
into an argument.

### 11.7 The independence we have is one third of the definition, and it assumes non-collusion

Two gaps, both from §4 and §5.

**Scope.** IEEE 1012 independence has three parameters. `filer ≠ verifier` is
*technical* independence only. Managerial independence (the verifier decides
what to look at) and financial independence (the verification cannot be cut
short under delivery pressure) have no analogue here, and in a one-person shop
mostly cannot. The realistic residue is managerial: today the filer's hand-off
scopes the verifier's attention. Letting the verifier choose its own targets
from the change set — including targets the filer did not mention — is the
cheap approximation, and we do not do it.

**Correlation.** Clark & Wilson state the assumption their whole mechanism
rests on: "the system is certified correct under the assumption that there has
been **no collusion**." Two verifier agents running the same model, on the same
prompt template, with the same context, are correlated in exactly the way
collusion describes — they share blind spots by construction. Clark & Wilson's
own hardening is randomisation: "random selection of the sets of people to
perform some operation, so any proposed collusion is only safe by chance." The
analogue is to vary something real between verifiers — model, prompt framing,
or the *order and slice* of material each one sees. Two identical verifiers are
closer to one verifier than to two.

Also, their basic rule is stronger than ours: *create or certify* ≠ *execute*.
Applied here, the agent that authors a claim's evidence recipe should not be the
agent that runs it and records the verdict.

### 11.8 "Accept into a baseline with the reason recorded" is Vaughan's step 4

Refusal 4.11 says: a gate that warns forever trains people to ignore it, so
"either accept the finding into a baseline *with the reason recorded*, or fix
it", and correctly names this as normalisation of deviance in miniature.

Read against Vaughan, the prescription is the disease. Her sequence is signal →
official acknowledgement → review → **official act of acceptance** → proceed.
Step 4 is not sloppiness; it is a documented, reasoned, formally recorded
acceptance. That is precisely what "accept into a baseline with the reason
recorded" is. And what makes it corrosive is that the accepted state becomes
the baseline against which the *next* deviation is judged, so the standard
moves without anyone deciding to move it. Feynman saw the same thing from the
inside: certification criteria "often develop a gradually decreasing
strictness", because "the same risk was flown before without failure".

**Actionable, and cheap:** a baseline entry must carry (a) the *original*
standard it departs from, so the comparison is always against the original and
never against the last accepted state, and (b) an expiry, after which it
returns as a finding. Recording the reason is necessary and nowhere near
sufficient.

### 11.9 The report-shape failure has a precise test we can apply

CAIB p. 191 gives the mechanism exactly: the title asserted reassurance, the
title's actual subject was not what a reader assumes ("Conservatism" referred
to the choice of test models, not to the predicted damage), and the fact that
invalidated everything sat at the deepest of six indentation levels. Tufte's
proposed honest headline — "Review of Test Data Indicates **Irrelevance** of
Two Models" — is the same content with the load-bearing fact promoted to the
title.

Our agents' reports fail identically: confident verdict at the top, the
qualifier that would change the verdict nested below it.

**Actionable:** a report whose conclusion is positive must restate its
strongest limitation **at the same level as the conclusion**, not below it —
and if the limitation would change the verdict, the verdict must be restated in
its terms. Tufte's "significant" observation gives a second, mechanical check:
grep our reports for *verified*, *confirmed*, *passes*, *validated* used without
a scope, since those are our "significant".

CAIB's other line applies to us verbatim: "the Board was surprised to receive
similar presentation slides from NASA officials **in place of technical
reports**." An agent's summary is arriving in place of the evidence, and the
truth ledger's whole point is that the evidence should be re-runnable rather
than reported.

### 11.10 Grade the account, not the answer

From §10d and Austin combined. If verifier output is judged on whether it found
the right answer, the pressure is toward a confident answer. If it is judged on
the accuracy of its account — what was checked, what could not be checked, what
was assumed — the pressure is toward calibration. This is also the only version
of a verifier metric that survives §11.5, because an accurate account of
limitations is not a count and cannot be gamed upward by producing more of it.

### 11.11 The missing control the whole lineage points at: an entry criterion

Fagan's framing sentence is about operations "each having its own exit
criteria"; his inspections have hard entry gates; Gilb & Graham promoted entry
and exit to first-class steps. We have no entry criterion for verification at
all. A verifier is launched whenever the filer is finished, on whatever state
exists. The obvious cheap form: verification does not start until the change
compiles, the relevant suites run, and the acceptance criteria are written down
in a form the verifier can quote back line by line — which is doctrine §3 L4
Adopt 2, currently framed as a *close* control rather than an *entry* control.
It is worth more as an entry control.

### 11.12 A green gate is not evidence of correctness — Feynman's sentence

"Erosion was not something from which safety can be inferred." Our gates report
the absence of a specific signal. The doctrine's F2 (evidence that cannot fail)
and F4 (undeclared blind spots) are two special cases of this general one, and
Feynman's formulation is better than either because it is about *inference
direction*: a passing check licenses no positive claim, only the narrower
statement that this particular check did not fire. The scratch design's
required `blind_spots` field is the right structural answer; the sentence is
worth carrying next to it.

### 11.13 Perrow's warning applies to the adoption plan itself

Redundancy adds complexity, diffuses responsibility, and licenses faster
operation. The doctrine tracks the first (as maintenance cost, the FIT curve)
and neither of the other two. The licence effect is the one to watch here:
"we have independent verifiers" is a reason to ship with less care, and it is
invisible until something gets through. The doctrine's own §7 answer — "the
correct response is fewer claims, not more machinery" — is the right instinct,
and Perrow is the argument for extending it to controls as well as claims.

### 11.14 What we got right, stated plainly

So the section is not read as uniformly negative:

- The invariant/testimony split independently reproduces Clark & Wilson's
  internal/external consistency partition (1987) and Austin's
  full-supervision/delegation partition (1996). Two unrelated literatures
  arriving at the same boundary is strong evidence the boundary is real.
- Refusal 4.8 (do not target claim counts) is correct and is Goodhart read
  narrowly, which is the right reading.
- Refusal 4.4 (LLM-as-judge is self-assessment, never the control) is exactly
  what the IV&V literature says about technical independence.
- The required `mutation:` field is a stronger control than anything in the
  inspection literature, which has no equivalent of proving that a check can
  fail. That one is genuinely ahead of the sources.

---

## 12. Sources requiring purchase

Four items would materially change what this document can say. Prices are
indicative and were not verified in this session; nothing here was obtained
from a pirate source and none should be.

| Source | Why buy it | Priority |
|---|---|---|
| **Robert D. Austin, *Measuring and Managing Performance in Organizations*** (Dorset House, 1996, ISBN 0-932633-36-6; also available as a Pearson/Addison-Wesley reissue). New or used, typically the price of a technical book. | I read only chapters 1–3 from the publisher's sample. **The model is chapters 5–12** — the principal/agent/customer setup, the three supervision regimes, the incentive design chapter, and the comparison of delegatory versus measurement-based management. §11.6 rests on a secondary summary of exactly those chapters. This is the deepest treatment of our F1 failure mode and the one place we are reasoning from a paraphrase. | **1 — highest** |
| **Diane Vaughan, *The Challenger Launch Decision*** (University of Chicago Press, 1996; enlarged edition 2016). Paperback. | §11.8 makes a strong claim — that our baseline-acceptance rule *is* her step 4 — on the basis of an encyclopaedia entry. The five-step sequence, "structural secrecy", and the "culture of production" are all ATTRIBUTED. If the claim is right it should change how baselines work, so it deserves the primary. | **2** |
| **Tom Gilb & Dorothy Graham, *Software Inspection*** (Addison-Wesley, 1993, ISBN 0-201-63181-4). Used copies only; long out of print. | §2 is the weakest section here. What survives verification is one parameter (checking rate ≈ 1 page/hour) obtained via a citing paper. The book's measured case data, the sampling argument, and the process-improvement step are all second-hand. Buy only if we decide to implement a rate limit and want the underlying data. | 3 |
| **IEEE Std 1012** (current edition; IEEE Standards Store, typically a few hundred USD for a single-user copy). | Would convert §4's three definitions and their rationales from ATTRIBUTED to VERIFIED. Honestly: **low value for money here.** NASA's public material gives us the substance, and the standard's cost model assumes a certification budget we do not have — which is the doctrine's own refusal 4.7 argument. Recommend **not** buying unless a definition is ever load-bearing in a decision. | 4 — recommend skipping |

Free but not reached, worth a further attempt before buying anything:
Goodhart's original 1975 RBA paper (§6a) and the Chrystal & Mizen commentary;
the McIntosh et al. MSR 2014 paper (§10e); Allspaw's post (§10d).

---

## 13. Source list with labels

**VERIFIED — full or partial primary text retrieved and read in this session**

1. M. E. Fagan, "Design and code inspections to reduce errors in program
   development", *IBM Systems Journal* 15(3), 1976, pp. 182–211.
   DOI `10.1147/sj.153.0182` (DOI per ACM listing).
2. Alberto Bacchelli, Christian Bird, "Expectations, Outcomes, and Challenges
   of Modern Code Review", *ICSE 2013*, pp. 712–721 (page range per ACM
   listing).
3. Caitlin Sadowski, Emma Söderberg, Luke Church, Michal Sipko, Alberto
   Bacchelli, "Modern Code Review: A Case Study at Google", *ICSE-SEIP '18*,
   Gothenburg, May–June 2018.
4. David D. Clark, David R. Wilson, "A Comparison of Commercial and Military
   Computer Security Policies", *Proc. 1987 IEEE Symposium on Security and
   Privacy*, Oakland CA. Conventionally pp. 184–194; p. 186 confirmed in scan.
5. Donald T. Campbell, "Assessing the Impact of Planned Social Change",
   Paper #8, Occasional Paper Series, Public Affairs Center, Dartmouth College,
   December 1976 — quoted passage at pp. 49–52.
6. *Columbia Accident Investigation Board Report*, Volume I, August 2003,
   p. 191, sidebar "Engineering by Viewgraphs".
7. Richard P. Feynman, "Appendix F: Personal Observations on the Reliability of
   the Shuttle", Rogers Commission report, 1986.
8. Robert D. Austin, *Measuring and Managing Performance in Organizations*,
   Dorset House, 1996, ISBN 0-932633-36-6 — front matter, contents, foreword
   and chapters 1–3 only.
9. Stefan Wagner, "A Literature Survey of the Quality Economics of
   Defect-Detection Techniques", TU München, circa 2006 (dated from its own
   citations; arXiv:1612.04590).
10. Richard I. Cook, "How Complex Systems Fail", Cognitive Technologies
    Laboratory, University of Chicago, 1998–2000.
11. Ronald C. Kramer, "Vaughan, Diane: The Normalization of Deviance", in
    Cullen & Wilcox (eds.), *Encyclopedia of Criminological Theory*, SAGE,
    2010, pp. 976–980, DOI `10.4135/9781412959193.n269` — a secondary source,
    but retrieved and read in full.
12. NASA IV&V programme overview page and NASA Software Engineering Handbook
    SWE-141 (Version C) — for §4's verbatim NASA statements.
13. V. F. Ridgway, "Dysfunctional Consequences of Performance Measurements",
    *Administrative Science Quarterly* 1(2), September 1956 — citation
    verified via Austin's permissions page; the article itself not read.
14. Steven Kerr, "On the folly of rewarding A, while hoping for B" — reprint
    header verified: *The Academy of Management Executive*, Feb 1995, 9(1),
    p. 7. Body text not readable; nothing quoted.

**ATTRIBUTED — widely and consistently reported, primary not reached**

15. Tom Gilb, Dorothy Graham, *Software Inspection*, Addison-Wesley, 1993,
    ISBN 0-201-63181-4 (bibliography verified; contents attributed).
16. IEEE Std 1012, *IEEE Standard for System, Software, and Hardware
    Verification and Validation* — three independence parameters and their
    rationales.
17. C. A. E. Goodhart, "Problems of Monetary Management: The U.K. Experience",
    *Papers in Monetary Economics* Vol. I, Reserve Bank of Australia, 1975.
18. Marilyn Strathern, "'Improving ratings': audit in the British University
    system", *European Review*, 1997 — source of the popular slogan.
19. Diane Vaughan, *The Challenger Launch Decision: Risky Technology, Culture,
    and Deviance at NASA*, University of Chicago Press, 1996 (enlarged edition
    2016) — including the five-step decision sequence, "structural secrecy" and
    "culture of production".
20. Edward R. Tufte, *The Cognitive Style of PowerPoint*, Graphics Press, 2003
    (2nd ed. 2006). The specific analysis used here is quoted from CAIB, not
    from the book.
21. Charles Perrow, *Normal Accidents: Living with High-Risk Technologies*,
    Basic Books, 1984 (Princeton UP edition 1999).
22. Karl E. Weick, Kathleen M. Sutcliffe, *Managing the Unexpected*,
    Jossey-Bass, 2001; and the Berkeley HRO group (LaPorte, Roberts, Rochlin).
23. Peter C. Rigby, Christian Bird, "Convergent contemporary software peer
    review practices", ESEC/FSE 2013 — reached only via Sadowski's citation.
24. John Allspaw, "Blameless PostMortems and a Just Culture", Etsy *Code as
    Craft*, May 2012 — date unconfirmed.
25. Peter M. Blau, *The Dynamics of Bureaucracy*, University of Chicago Press,
    1955/1963 — the employment-agency dysfunction example, cited by both
    Campbell and Austin.
26. Steven Kerr, "On the folly of rewarding A, while hoping for B", *Academy of
    Management Journal* 18(4), 1975, pp. 769–783 — the original venue.

**UNCERTAIN — leads, not facts**

27. McIntosh, Kamei, Adams, Hassan, "The impact of code review coverage and
    code review participation on software quality", MSR 2014.
28. Chrystal & Mizen, "Goodhart's Law: Its Origins, Meaning and Implications
    for Monetary Policy", circa 2001–2003.
29. Nancy Leveson's STAMP/STPA work as a third position between Perrow and HRO.
