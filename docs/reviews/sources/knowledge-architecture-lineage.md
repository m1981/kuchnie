# Knowledge architecture — the source lineage (2026-08-03)

> Reader: anyone about to extend, re-partition, or defend the truth ledger,
> and anyone checking whether the claims in the 2026-08-03 doctrine and
> scratch-design documents survive contact with the primary literature |
> Enables: citing the real ancestors of each mechanism, dropping the ones
> that turn out to be false analogies, and knowing which historical failure
> we are actually at risk of | Update-trigger: a source here is read in full
> and contradicts the summary, a `VERIFIED` label is downgraded, or the
> ledger's mechanism changes in a way that alters §16's two answers

**What this is.** A source document for `agentic-verification-doctrine-2026-08-03.md`
and `verification-system-scratch-design-2026-08-03.md`. Those two documents make
historical claims. This one checks them against the primary literature and,
where the check fails, says so.

**It fails in three places that matter**, all in §16 and §17:

1. **The truth ledger is not a Truth Maintenance System.** The analogy is loose
   in a way that misdirects future work. The real ancestor is `make`.
2. **The FIT diagnosis is wrong in its causal order**, and its quantitative
   clause is unsourced. The best-evidenced account puts a different failure
   first, and the successor technology reproduced it.
3. **The invariant/testimony split is half a rediscovery of Zave & Jackson**,
   and the half it is missing is the half that does the work.

Two claims survive intact and are strengthened: the refusal of ATMS (§2, for a
different reason than the doctrine gives), and the primacy of independence as a
control (§14, on much better evidence than Fagan).

---

## How to read the citations

Every bibliographic record carries one of three labels.

- **VERIFIED** — the source itself, or an authoritative registry record
  (Crossref, DBLP, OpenAlex, a publisher's own page), was fetched and the
  title / author / year / venue confirmed. Where a quotation appears under a
  VERIFIED record, the quoted text was read.
- **ATTRIBUTED** — consistent across the sources actually fetched, but the
  primary was not reached. Content claims under an ATTRIBUTED label are
  second-hand.
- **UNCERTAIN** — a lead. Do not build on it.

**No page number, DOI, ISBN, or quotation in this document was invented.**
Where a figure could not be obtained it is marked as such rather than
estimated. Where a scan was too poor to transcribe with confidence the text is
paraphrased and labelled as paraphrase. §18 lists everything that could not be
verified; §19 lists what would have to be bought.

Two sources were read first-hand for this document, page by page, because the
whole argument turns on them: Doyle 1979 (via the 1987 Ginsberg reprint) and
Zave & Jackson 1997. Their quotations are the most reliable material here.

---

## 1. Doyle, "A Truth Maintenance System" (1979)

**Record — VERIFIED.** Jon Doyle, "A Truth Maintenance System," *Artificial
Intelligence* 12(3):231–272, November 1979. DOI `10.1016/0004-3702(79)90008-0`.
MIT Artificial Intelligence Laboratory; the paper's dedication reads "In memory
of John Sheridan Mac Nerney." A free tech-report predecessor exists as **MIT AI
Memo 521**, June 1979, at `https://dspace.mit.edu/handle/1721.1/5733` (an
earlier AITR-419, 1978, is at handle `1721.1/6926`). Reprinted as chapter 4 of
Matthew L. Ginsberg (ed.), *Readings in Nonmonotonic Reasoning*, Morgan
Kaufmann, 1987, pp. 259–300 — **this reprint is what was read for this
document**, and page numbers below are the reprint's printed numbers.

### Problem

Not "how do we store facts." The problem is that classical inference is
*monotonic* and the world is not. Doyle states it directly (p. 259):

> "Briefly put, the problems with the conventional view of reasoning stem from
> the monotonicity of the sequence of states of the reasoner's beliefs: his
> beliefs are true, and truths never change, so the only action of reasoning is
> to augment the current set of beliefs with more beliefs. This monotonicity
> leads to three closely related problems involving commonsense reasoning, the
> frame problem, and control."

He names the update cost explicitly on the same page: "The problem of describing
and performing this updating efficiently is sometimes called the frame problem."

A problem solver that makes assumptions in order to act must be able to
*withdraw* them when a discovery contradicts them, and must not have to
re-derive everything else from scratch when it does.

### Evidence they had

Working systems, not measurements. Doyle's setting is the mid-1970s MIT problem
solvers — the paper's dependency-directed backtracking is credited in the text to
Stallman and Sussman's circuit analyser — plus the general observation that
programs that "recompute everything" are unusable and programs that "keep
everything" become inconsistent. There is no empirical evaluation in the paper.
This matters when judging the pedigree: TMS was validated by construction and by
adoption, never by experiment.

### Reasoning

Record *why* each belief is held, and make belief membership a computed function
of those reasons rather than a stored flag. Then withdrawal is not a special
operation — it is a recomputation.

### Proposed solution, in enough detail to judge our own mechanism

**Nodes and justifications.** Each potential belief is a *node*. Each node
carries a *justification-set* — several independent reasons to believe it. Two
justification forms:

- **SL (support-list)**, written `(SL <inlist> <outlist>)`. It is valid if and
  only if every node in its inlist is `IN` and every node in its outlist is
  `OUT`. A justification with empty inlist and empty outlist is a *premise*
  justification and is always valid. An SL-justification with a nonempty inlist
  and an **empty outlist** is an ordinary monotonic deduction.
- **CP (conditional-proof)**, `(CP <consequent> <inhypotheses> <outhypotheses>)`,
  which justifies a node by the validity of a hypothetical argument and
  discharges its hypotheses.

**Assumptions are defined by the outlist.** A node whose supporting justification
has a **nonempty outlist** is an *assumption* — it is believed *because* something
else is not believed. This is the non-monotonic justification, and it is Doyle's
actual novelty. Nothing in the ledger has this shape.

**IN and OUT are not truth values.** A node is `IN` if it has at least one valid
justification and `OUT` if it has none — either because it has no justifications
at all, or because all of them are invalid. Doyle is emphatic that this is not
negation (p. 262, transcribed from the reprint scan):

> "The former classification refers to current possession of valid reasons for
> belief. True and false, on the other hand, classify statements according to
> truth value independent of any reasons for belief."

and on the asymmetry (p. 260):

> "These states are not symmetric, for while reasons can be constructed to make
> P in, no reason can make P out. (At most, it can make ¬P in as well.)"

**Well-founded support.** The TMS singles out one justification per `IN` node as
its *supporting-justification*, and requires the resulting support graph to be
non-circular. From this it derives *antecedents*, *foundations* (the transitive
closure of antecedents), *consequences*, *affected-consequences* and
*repercussions*. Truth maintenance is then: when a node's status changes,
recompute the labels of its believed-repercussions. Circular support is
forbidden — a belief may not be its own reason.

**Dependency-directed backtracking.** A node may be marked a *contradiction*,
representing the inconsistency of any set of beliefs entering into an argument
for it. When one becomes `IN`, the system walks the well-founded argument to find
the *assumptions* it rests on (nodes with non-empty outlists), and retracts one by
constructing a **new justification** that makes it `OUT`. That summary of the
inconsistent assumption set is a **nogood**. Chronological backtracking undoes the
most recent choice; dependency-directed backtracking undoes a *relevant* choice
and leaves a permanent record forbidding that combination.

### What happened to it

Enormously influential and, as an artifact, superseded. OpenAlex records ~1,785
citations (**ATTRIBUTED**). "Truth maintenance" was largely renamed "reason
maintenance," including by Doyle. But Ginsberg's 1987 editorial introduction to
the reprint — read first-hand, p. 257 — is the sharpest contemporary verdict:

> "In spite of this, work on truth maintenance appears to have become
> disconnected from progress on default reasoning. The reason appears to be that
> Doyle's paper presents an algorithm, as opposed to a declarative description of
> nonmonotonic reasoning. He goes to great efforts to present a detailed
> description of the workings of a TMS, but nowhere is there a satisfactory
> explanation of the semantics of the approach."

The mechanism lives on in constraint and SAT solving as solving-under-assumptions
and unsatisfiable-core extraction. **The frequently-made claim that
dependency-directed backtracking is the direct ancestor of CDCL clause learning
is plausible and widely repeated but was not verified for this document — treat
it as UNCERTAIN and do not assert it.**

### Relevance to us

Decisive, and negative. See §16, question 1. The short form: the ledger has no
outlists, no propagation, no well-founded support requirement, and no
dependency-directed backtracking. What it has is one hop of a monotonic
SL-justification with an empty outlist. That is a join, not a maintenance system.

The two things worth stealing are real, though:

- **IN/OUT is not true/false.** The ledger already honours this — `live`,
  `stale`, `diverged`, `cannot_verify` are epistemic states, not truth values —
  and Doyle is the citation for why that distinction must be maintained rather
  than collapsed into a boolean.
- **Well-founded support forbids cycles.** `docs/adr/truth/013-premise-supersede.md`
  permits redirect cycles and resolves them by a deterministic-but-arbitrary rule
  ("resolves to that first-repeated value"). Doyle forbids the situation outright.
  Ours is defensible for a depth-1 graph; it would not be at depth 3, and that is
  worth knowing before anyone adds claim-on-claim edges.

---

## 2. de Kleer, "An Assumption-Based TMS" (1986)

**Records — VERIFIED.** The trilogy occupies one issue, consecutively:

- Johan de Kleer, "An Assumption-based TMS," *Artificial Intelligence*
  28(2):127–162, 1986. DOI `10.1016/0004-3702(86)90080-9`.
- "Extending the ATMS," same issue, pp. 163–196. DOI `10.1016/0004-3702(86)90081-0`.
- "Problem Solving with the ATMS," same issue, pp. 197–224. DOI `10.1016/0004-3702(86)90082-2`.

Xerox PARC, Intelligent Systems Laboratory. Preliminary version: de Kleer,
"Choices Without Backtracking," *Proc. AAAI-84*, pp. 79–85, free at
`https://cdn.aaai.org/AAAI/1984/AAAI84-013.pdf`. de Kleer self-archived scanned
reprints of papers 1 and 3 at PARC; they survive in the Internet Archive.
**"Extending the ATMS" has no free copy anywhere** — see §19.

Flagship application — **VERIFIED**: de Kleer & Williams, "Diagnosing Multiple
Faults," *Artificial Intelligence* 32(1):97–130, 1987, DOI
`10.1016/0004-3702(87)90063-4` (the GDE paper; Reiter's "A theory of diagnosis
from first principles" is the immediately preceding article in the same issue).

### Problem

The JTMS holds exactly **one** belief set at a time. de Kleer's 1984 opening is
unusually candid: "The results of this paper are born out of frustration...
they are intrinsically incapable of working with multiple contradictory choices
at once... Timing analysis shows that the reasoner spends the majority of its
time in the backtracking algorithms."

He names the failure mode in the 1986 paper (p. 138):

> "**The single-state problem.** Given a set of assumptions which admits multiple
> solutions, the TMS algorithms only allow one solution to be considered at a
> time. This makes it extremely difficult to compare two equally plausible
> solutions... However, this is often exactly what one wants to do in problem
> solving—differential diagnosis to determine the best solution."

### Evidence they had

Named, failing systems of his own — LOCAL, ENVISION, QP — running out of memory
on Symbolics hardware, with profiling that put the time in backtracking.
Engineering evidence, not experiment.

### Reasoning

Invert the association. From the 1986 paper (p. 144):

> "The ATMS constructs this data structure by associating descriptions of
> contexts with data, instead of the usual association of data with contexts.
> The ATMS associates with every datum a parsimonious description of every
> context in which the datum holds."

### Proposed solution

An **environment** is a set of assumptions (logically, their conjunction). A node
*holds* in environment E if it is derivable from E and the current justifications.
An environment is **nogood** if false is derivable from it. A **context** is a
consistent environment plus everything derivable from it. A node's **label** is a
set of environments — every minimal environment in which the node holds.

The label is required to be **sound, consistent, complete and minimal**. Those
four names are de Kleer's own (1986 p. 144; restated as a numbered list in
"A General Labeling Algorithm for Assumption-Based Truth Maintenance," AAAI-88,
p. 188 — **VERIFIED**, free at `https://cdn.aaai.org/AAAI/1988/AAAI88-034.pdf`).
The payoff: asking whether a node holds in an environment becomes a subset test
against its label. All contexts are available at once, so context switching is
free.

### The cost — and it is de Kleer who states it

This is the part the doctrine's refusal needed and did not have. All verbatim:

*"Problem Solving with the ATMS," §6.1 (p. 215):*

> "If there are an exponential number of solutions and only one is required, then
> node labels may become excessively large. Although the label-update algorithms
> are efficient, at some point they will consume too many resources."

and, in the same section, the comparison against a JTMS on single-solution
problems: "If there is none, then the ATMS is slower due to its inherent overhead
on database accesses." §3 of the same paper: "**The ATMS is not a panacea and is
not suited to all tasks.**"

*AAAI-88, p. 190:*

> "For many problems the expense of ensuring label consistency is too high"

and

> "As ensuring label completeness is so computationally expensive, the ATMS
> computes the complete label for a node only upon request."

**The architectural cost is separate and larger.** "Problem Solving with the ATMS"
§3 defines a *consumer architecture* and imposes on the problem solver that a
consumer "should only examine the data of nodes," that its justifications "must
include all the consumer's antecedents, no more and no less," and that "the
consumer may not have any internal state." That is a monotonic, stateless,
non-retracting problem solver — a rewrite of the caller, not a library swap.

Forbus & de Kleer, "Focusing the ATMS," AAAI-88 (**VERIFIED**, free at
`https://cdn.aaai.org/AAAI/1988/AAAI88-035.pdf`) is the admission that this failed
in practice: "existing ATMS techniques generally perform badly on them" and
"current ATMS/inference-engine interfaces are oriented towards finding all (or
many) solutions, making them unsuitable for such problems."

Modern independent confirmation — Dev Gupta, Genc & O'Sullivan, "Explanation in
Constraint Satisfaction: A Survey," IJCAI-21, DOI `10.24963/ijcai.2021/601`
(**VERIFIED**, free):

> "Nevertheless, these capabilities may be costly in space and time as the nogood
> database, as well as the labels, may be exponential in size... in general a
> focusing mechanism is necessary to make an ATMS work in practice."

The theoretical floor: an ATMS label is exactly the set of subset-minimal
abductive explanations, and Eiter & Gottlob, "The complexity of logic-based
abduction," *JACM* 42(1):3–42, 1995 (**VERIFIED**) put those problems at the
second level of the polynomial hierarchy.

### The decision criterion — verbatim, and it settles our question

*1984 paper, criterion (b):* "the user is interested in many or all of the
solutions which achieve the goal (**if one is only interested in a single
solution, a standard TMS is probably better**)."

*1986 paper, §3 (p. 137) — the cleanest statement:*

> "Conventional TMSs are oriented to finding one solution, and extra cost is
> incurred to control the TMS to find many solutions. The ATMS is oriented to
> finding all solutions, and extra cost is incurred to control the ATMS to find
> fewer solutions."

### What happened to it

Widely used in the late 1980s and early 1990s — qualitative reasoning, model-based
diagnosis, scene interpretation, several commercial expert-system shells — then
declined sharply as an artifact while its problem survived. Citations to the 1986
paper by year (OpenAlex, **ATTRIBUTED**): 24 in 2013, 16 in 2019, 3 in 2023, 2 in
2025. The best-sourced explanation is the IJCAI-21 survey's: truth maintenance
"limits the scope of applicability... there was an interest in solver-agnostic
methods that could work for arbitrary constraint solvers." The instrumentation
contract killed it. Modern practice extracts unsat cores from an off-the-shelf
solver instead.

The clinching datum: de Kleer's own ISCAS-85 diagnosis benchmarks were finally
solved not by an ATMS but by SAT — Metodi, Stern, Kalech & Codish, "A Novel
SAT-Based Approach to Model Based Diagnosis," *JAIR* 51:377–411, 2014, DOI
`10.1613/jair.4503` (**VERIFIED**, open access): "we can determine, for the first
time, minimal cardinality diagnoses for the entire standard ISCAS-85 and 74XXX
benchmarks."

### Relevance to us

**The refusal in doctrine §4.6 is correct. Its stated reason is not.**

The doctrine refuses ATMS because it is "a research-grade mechanism whose cost
would land squarely on the FIT curve." That is an argument from expense. de
Kleer's own criterion is an argument from *fit*: you need an ATMS when you must
hold and compare several candidate worlds simultaneously — differential
diagnosis. We never do. There is exactly one current belief set about this
codebase, and the ledger contains **zero `contradicts` records**, meaning the one
multi-world verb we already have has never been used in 2,133 records.

Replace the rationale. "Too expensive" invites someone to re-open it when
compute gets cheap. "We do not have the problem it solves" does not.

One nuance worth carrying: the ATMS does not eliminate backtracking. The 1986
abstract says "**most** backtracking (and all retraction) is avoided," and within
a year de Kleer & Williams published "Back to Backtracking: Controlling the ATMS"
(AAAI-86, pp. 910–917, **VERIFIED**, free at
`https://cdn.aaai.org/AAAI/1986/AAAI86-151.pdf`), whose abstract concedes that
"for some applications this ATMS capability is more of a hindrance than a help
and some form of backtracking is necessary."

---

## 3. AGM belief revision (1985)

**Record — VERIFIED.** Carlos E. Alchourrón, Peter Gärdenfors & David Makinson,
"On the Logic of Theory Change: Partial Meet Contraction and Revision Functions,"
*The Journal of Symbolic Logic* 50(2):510–530, June 1985. DOI `10.2307/2274239`.
A free copy is on Makinson's own homepage, linked from
`https://sites.google.com/site/davidcmakinson/`.

**Origin — VERIFIED, and it is not an AI origin.** Alchourrón took a law degree
at the University of Buenos Aires in 1957 and a doctorate in 1967 on "Logical
clarification of some juridical concepts." Makinson's obituary of him — "In
memoriam Carlos Eduardo Alchourrón," *Nordic Journal of Philosophical Logic*
1(1):3–10, 1996 — says verbatim: "In the late 1970's, Carlos began a close
collaboration with David Makinson on the fine logical structure of derogation in
legal codes, which soon expanded into a more general investigation of the logic
of the contraction and revision of theories." Makinson's own retrospective ("Ways
of Doing Logic: What was Different about AGM 1985?", *J. Logic and Computation*
13:3–13, 2003) adds: "Alchourrón and I came to belief change from a problem in
the philosophy of law, of determining the result of abrogating an item from a
legal code."

### Problem

Given a set of beliefs closed under logical consequence, and a reason to stop
believing one of them, what is the resulting belief set? Not "how do I compute
it" — *what constraints must any rational answer satisfy*.

### Evidence they had

None empirical. AGM is a normative theory. This is the single most important
thing to know about it before importing anything.

### Reasoning

Represent a belief state as a **belief set** — a set closed under consequence,
`A = Cn(A)`. Three operations: **expansion** `K+p = Cn(K ∪ {p})`; **contraction**
`K÷p`, a subset of K not implying p; **revision** `K*p`, adding p while restoring
consistency. The two bridges (both **VERIFIED**):

- **Levi identity**: `K*p = (K÷¬p)+p`
- **Harper identity**: `K÷p = K ∩ K*¬p`

(The Harper identity is verified from Booth & Chandler, arXiv:1604.05419; it does
*not* appear in the current Stanford Encyclopedia of Philosophy entry. Its dating
— Harper 1976 vs a PSA-1976 volume published 1977 — is **UNCERTAIN**.)

### Proposed solution — the postulates

Six basic postulates for contraction, names **VERIFIED** against SEP and against
Fermé & Hansson's Table 1: **Closure**, **Success**, **Inclusion**, **Vacuity**,
**Extensionality**, **Recovery** (`K ⊆ (K÷p)+p`). Two supplementary:
**Conjunctive inclusion** and **Conjunctive overlap**. (The alternative names
"intersection" and "conjunction" could not be found in any source — do not use
them.) Revision has a parallel eight, though their naming is *not* stable across
sources: SEP's own two entries disagree on whether `*4` is Vacuity or
Preservation.

### What the postulates say about dependent beliefs — the question that matters

Three findings, in order of importance to us.

**(a) The result must still be closed.** The Closure postulate. You cannot retract
a belief and leave its consequences dangling.

**(b) The postulates constrain but do not determine.** This is the load-bearing
result. SEP, verbatim:

> "The central problem of belief revision is that deductive logic alone cannot
> tell you which of your beliefs to give up–this has to be decided by some other
> means."

The construction is **partial meet contraction**: take the *remainder set* `K⊥p`
(the inclusion-maximal subsets of K not implying p), apply a **selection
function** γ picking the "best" of them, and intersect. SEP: "However, the
definition of a selection function is very general, and allows for quite
disorderly selection patterns." The representation theorem is what proves
non-uniqueness — the six postulates characterise the *entire family* of partial
meet operations for *any* selection function whatever, not one member of it.

**Epistemic entrenchment** (Gärdenfors & Makinson, "Revisions of Knowledge Systems
Using Epistemic Entrenchment," TARK 1988, pp. 83–95 — **VERIFIED**) supplies the
missing ordering, and entrenchment-based contraction coincides exactly with
transitively relational partial meet contraction. But the ordering is an input,
not a theorem.

**(c) Foundational vs coherentist — and Doyle's own verdict, which is not what
you would expect.** AGM is coherentist: belief sets are closed under consequence
and there is *no* explicit justification structure. SEP, verbatim: "The structure
of the agent's reasons is *not* explicitly represented: you cannot tell of any two
α,β ∈ B whether one is a reason for the other." And: "In artificial intelligence,
Doyle's (1979) reason maintenance system is taken to exemplify the foundations
approach."

The standard objection to the coherentist side, from Fermé & Hansson (2011):

> "In the AGM framework, however, 'merely derived' beliefs such as p∨q have the
> same status as independently justified beliefs such as p."

Doyle's own paper on the split — "Reason Maintenance and Belief Revision:
Foundations vs. Coherence Theories," in Gärdenfors (ed.), *Belief Revision*,
Cambridge Tracts in Theoretical Computer Science 29, CUP, 1992, pp. 29–51, DOI
`10.1017/CBO9780511526664.002` (**VERIFIED**; free PostScript from his MIT page
at `https://groups.csail.mit.edu/medg/people/doyle/publications/cf92.ps`) —
does **not** concede. Verbatim from his abstract:

> "We argue that the coherence and foundations approaches differ less than has
> been supposed... We also argue that the foundations approach represents the
> most direct way of mechanizing the coherence approach. Moreover, the
> computational costs of revisions based on epistemic entrenchment appear to
> equal or exceed those of revisions based on reasons... we conclude that while
> the coherence approach offers a valuable perspective on belief revision, it
> does not yet provide an adequate theoretical or practical basis for
> characterizing or mechanizing belief revision."

**Recovery** is the most attacked postulate (Fermé & Hansson: "By far the most
criticized"). Hansson's Cleopatra counterexample — *Studia Logica* 50(2):251–260,
1991, **VERIFIED** — is the standard one. **Correction to a common shorthand:
Makinson is not straightforwardly a critic.** His 1987 *JPL* paper coins
"withdrawal" for operations dropping Recovery, and his 1997 paper is a *defence*.
Attributing the critique to Levi or Fuhrmann could not be verified at all.

### What happened to it

Enormous and continuing uptake as a normative theory — OpenAlex totals ~3,236
citations, still running 70–90 per year (**ATTRIBUTED**). Iterated revision was
the major gap: AGM outputs a belief set but not a new entrenchment ordering, so
subsequent revisions are underdetermined. Darwiche & Pearl, "On the Logic of
Iterated Belief Revision," *Artificial Intelligence* 89(1–2):1–29, 1997, DOI
`10.1016/S0004-3702(96)00038-0` (**VERIFIED**; free preprint at
`https://ftp.cs.ucla.edu/pub/stat_ser/R202.pdf`) supplied postulates DP1–DP4.

**It never produced deployed systems.** Fermé & Hansson's 25-year retrospective
("AGM 25 Years," *J. Philosophical Logic* 40(2):295–331, 2011, **VERIFIED**, free
CC-BY at the University of Madeira repository) is blunt: "Belief revision has
usually been studied from the viewpoint of ideal agents... From a theoretical
point of view the computational tractability of the proposed algorithms is a
major challenge," and quotes Nebel: "The general revision problem for
propositional logic appears to be hopelessly infeasible from a computational
point of view." The only named implementation in the whole retrospective is a
1988 research system. Where AGM machinery did find applied traction is ontology
debugging and description-logic repair.

### Relevance to us

Three things, one of which is a direct diagnosis of a mechanism we ship.

**1. `--supersedes` is a hand-executed selection function.** AGM's central
negative result is that the postulates do not tell you what to give up; something
outside the logic must choose. `truth premise <issue> <new-tr> --supersedes
<old-tr>` is exactly that "something outside the logic," performed by a human,
per issue, with the choice recorded. ADR-013's insistence that the redirect is
"not history editing" and that "the old premise link, the redirect, and the
replacement are three permanent records" is, in AGM terms, *recording the
selection function's output as evidence*. That is a defensible design and AGM is
the right citation for why it cannot be automated away.

**2. We are foundational, and should say so.** Our claims have named supports
(evidence commands, watched paths) and named dependents (issues). We are not
running a coherentist belief set and we should stop reaching for AGM as a
theoretical warrant. Doyle 1992 is the citation that makes this comfortable: he
argues the foundations approach *is* the practical mechanisation of coherence,
and that entrenchment buys no computational saving.

**3. The complexity symmetry is worth knowing.** ATMS label computation sits at
the second level of the polynomial hierarchy (via abduction); general AGM
revision sits at the second level of the polynomial hierarchy (via Nebel). Both
the foundational and the coherentist theory of belief change hit the same wall
from opposite directions. Any future proposal to "properly formalise" the ledger
should be read against that.

**What does not transfer.** Closure under consequence. Our claims are not closed
under anything — they are 217 unrelated sentences. Recovery, Vacuity and
Extensionality have no meaning over a set with no consequence relation. Citing
"the AGM postulates" as backing for the ledger, as doctrine §2.1 does in passing,
is decorative.

---

## 4. Zave & Jackson, "Four Dark Corners of Requirements Engineering" (1997)

**This is the sharpest test of our design, so it was read first-hand.** Every
quotation below was transcribed from the article itself.

**Record — VERIFIED.** Pamela Zave & Michael Jackson, "Four Dark Corners of
Requirements Engineering," *ACM Transactions on Software Engineering and
Methodology* 6(1):1–30, January 1997. DOI `10.1145/237432.237434`. Zave at AT&T
Research; Jackson at AT&T Research and MAJ Consulting Limited, London. The full
ACM-typeset article circulates freely at
`https://www.fceia.unr.edu.ar/asist/zave00.pdf`.

**Companion records — VERIFIED.** Michael Jackson, "The World and the Machine,"
*Proc. 17th ICSE*, Seattle, 1995, pp. 283–292, DOI `10.1145/225014.225041` (the
word "keynote" could not be confirmed — **UNCERTAIN**). Michael Jackson,
*Problem Frames: Analysing and Structuring Software Development Problems*,
Addison-Wesley / ACM Press, 2000 or 2001 depending on the catalogue (DBLP says
2000; the ACM series listing says 2001), ISBN 0-201-59627-X. Michael Jackson,
*Software Requirements & Specifications: A Lexicon of Practice, Principles and
Prejudices*, Addison-Wesley, 1995, ISBN 0-201-87712-0. Michael Jackson, "Problem
frames and software engineering," *Information and Software Technology*
47(13):903–912, 2005, DOI `10.1016/j.infsof.2005.08.004` — **the best freely
available primary source for the problem-frames framework**, and the one used
here in place of the book, which was not obtained.

### Problem

Requirements engineering had terminology, methods and tools but no foundation.
Nobody could say precisely what a *requirement* is as distinct from a
*specification*; "implementation bias" made practitioners afraid to use state;
languages routinely failed to record who controls what; and "domain knowledge"
was fashionable with no agreed job to do.

**A correction worth making, because the phrase invites it:** the four dark
corners are **not** requirements / specifications / domain properties / machine.
They are four areas of inquiry, corresponding to §2 *Grounding Formal
Representations in Reality*, §3 *Implementation Bias*, §4 *Control of Actions*,
§5 *The Role of Domain Knowledge*, and stated in the introduction as four
conclusions. The fourth is the one we care about (p. 2):

> "(4) The primary role of domain knowledge in requirements engineering is in
> supporting refinement of requirements to implementable specifications. Correct
> specifications, in conjunction with appropriate domain knowledge, imply the
> satisfaction of the requirements."

### Evidence they had

Worked examples and a case study — a zoo turnstile, a lift controller, a
one-customer bank, a warehouse — plus a full treatment in Jackson & Zave,
"Deriving Specifications from Requirements: An Example," *17th ICSE*, 1995. No
empirical study. It is a conceptual paper and says so: "This work is limited to
the formal aspects of requirements engineering."

### Reasoning — the epistemology, which is the part that bears on us

Everything in requirements engineering is a statement about **the environment**,
never about the machine. Two grammatical moods separate the kinds (p. 7):

> "The primary distinction necessary for requirements engineering is captured by
> two grammatical moods. Statements in the 'indicative' mood describe the
> environment as it is in the absence of the machine or regardless of the actions
> of the machine; these statements are often called 'assumptions' or 'domain
> knowledge.' Statements in the 'optative' mood describe the environment as we
> would like it to be and as we hope it will be when the machine is connected to
> the environment. Optative statements are commonly called 'requirements.' The
> ability to describe the environment in the optative mood makes it unnecessary
> to describe the machine."

They claim the move as novel (p. 9): "To the best of our knowledge, we are the
first to propose that requirements should contain nothing but information about
the environment."

**The falsifiability asymmetry, in miniature.** §2 distinguishes an *assertion*
from a *definition* (p. 4):

> "The assertion constrains the real world by expressing a relationship between
> two real-world phenomena. It might be true or false and should be validated
> before it is used. The definition ... precludes a designation of *student*. It
> extends the formal vocabulary without constraining the real world in any way.
> It might be useless or misleading, but it cannot be false."

That sentence pair — *can be false and must be validated* versus *cannot be
false* — is the distinction our scratch design is reaching for, drawn thirty
years earlier and drawn more precisely.

**Designations.** The grounding obligation (p. 3): "This explanation must be
clear and precise; it must be written down; and it must be maintained as an
essential part of the requirements documentation." And a limit that matters to
us: "components of the machine state cannot be designated. Designations refer to
the real world, and the machine state may have no direct correspondence to the
real world."

**Mood is relative.** From ICSE'95 (**VERIFIED** by the researching agent from
the paper at `https://users.ece.utexas.edu/~perry/education/SE-Intro/jackson-icse95.pdf`):
"when the system is successfully installed and operating, the requirement becomes
a reality, what we desired to be true becomes true; and the optative becomes
indicative. So mood is relative to the progress of the development." That is the
mechanism by which today's requirement silently becomes tomorrow's assumption.

### Proposed solution — the entailment and the completion criteria

§5 introduces the relation and §6.3 states it formally. Verbatim from p. 27:

> "If the five following criteria are satisfied, then requirements engineering,
> in the strongest sense, is complete...
> (1) There is a set R of requirements. Each member of R has been validated
> (checked informally) as acceptable to the customer...
> (2) There is a set K of statements of domain knowledge. Each member of K has
> been validated (checked informally) as true of the environment.
> (3) There is a set S of specifications. The members of S do not constrain the
> environment; they are not stated in terms of any unshared actions or state
> components; and they do not refer to the future.
> (4) A proof shows that
>
> **S, K ⊢ R.**
>
> This proof ensures that an implementation of S will satisfy the requirements.
> (5) There is a proof that S and K are consistent."

And, as a notation *rule* binding on any requirements language (p. 26, rule 4):

> "Each property or assertion must be identified as a requirement, statement of
> domain knowledge, or specification."

Jackson's later work writes the same relation with `W` for world properties:
`S, W ⊢ R` (2005 paper, §3).

### Did they solve "the domain assumption goes stale"? No — and they say so

This was checked deliberately rather than inferred.

**The entire validation mechanism for K is completion criterion (2): "validated
(checked informally) as true of the environment."** One human, informally, once,
at requirements time. The two *proofs* (criteria 4 and 5) take K as a premise;
criterion 5 will catch a K that contradicts itself or contradicts S, and will
never catch a K that is coherent and simply untrue.

They acknowledge fallibility twice and decline to offer detection both times.
§3.3, on the warehouse: "the imitation is usually imperfect, however, because
there may be delay, errors, and factors in the real world that the machine does
not know about." And, closest to our question, §5.4 on "soft" requirements
(p. 24):

> "Requirements are also characterized as 'soft' if the domain knowledge that
> supports their satisfaction is not absolutely reliable. For example, the lift
> requirement that a waiting group is eventually served (L2) is satisfiable
> partly because (L3) someone in the waiting group pushes the request button. But
> L3 is a highly probable *assumption* rather than an unalterable fact. In those
> rare cases where the assumption is not true, the requirement will not be
> satisfied, even if the lift controller is perfect."

That is the whole statement of the problem, and the paper moves straight on.
There is no monitoring, no re-validation protocol, no expiry, no obligation to
re-check K when the world changes, and no link from a changed world back to the
proofs that stood on it.

**Jackson's best illustration of the consequence** is in ICSE'95 — the reverse-
thrust interlock, quoted by the researching agent from the paper:

> REQ: `can_rev ↔ on_runway` · WORLD1: `pulsing ↔ rotating` ·
> WORLD2: `rotating ↔ on_runway` · SPEC: `can_rev ↔ pulsing`
>
> "They prove their specification correct by showing that WORLD1, WORLD2, SPEC ⊢
> REQ. Unfortunately, property WORLD2 does not in fact hold in the world. On one
> occasion a plane landed in heavy rain on a runway covered with water. The
> wheels were aquaplaning, not turning. The pilot was prevented from engaging
> reverse thrust, and the plane ran off the end of the runway."

A valid proof, a correct implementation, and a runway excursion, because one
indicative premise was false.

In the 2005 paper Jackson escalates this to a named engineering concern —
**Reliability**: "A causal problem domain typically satisfies its properties
description with high—but never with perfect—reliability. If the reliability is
too low in relation to the criticality of the system it is necessary to detect,
or even to anticipate, failures and to prevent, mitigate or compensate their
effects." A duty to detect, with no notation, artifact, or process for doing so.

Detection became the *next* generation's research programme — requirements
monitoring (Fickas & Feather, RE'95) and obstacle analysis in the KAOS tradition
(van Lamsweerde & Letier). Both are **UNCERTAIN** here; neither primary was
reached. Their existence is itself the evidence that the founders left the gap
open.

### What happened to it

Foundational. Semantic Scholar reports 859 citations, 67 influential
(**ATTRIBUTED**). The 1995 companion case study won the ICSE Ten-Year Most
Influential Paper Award in 2005; the condensed restatement — Gunter, Gunter,
Jackson & Zave, "A Reference Model for Requirements and Specifications," *IEEE
Software* 17(3):37–43, 2000 — won the RE Ten-Year award in 2010 (**VERIFIED** via
Zave's own page, `https://www.pamelazave.com/fre.html`).

The formal successor, **WRSPM** (ICRE 2000, fetched by the researching agent at
`http://egunter.cs.illinois.edu/papers/ICRE2000.pdf`), generalises `S, K ⊢ R`
into five artifacts W/R/S/P/M with explicit HOL proof obligations. **Note what
did not change: even in the fully formalised version, W is a premise.**
Formalisation sharpened the entailment and added consistency obligations; it
added no means of noticing that W had stopped being true.

The vocabulary is standard in requirements-engineering research, in safety-
critical practice, and in the assurance-case literature. It did not penetrate
mainstream commercial tooling: no widely used tracker has a first-class notion of
a domain assumption, and the indicative/optative distinction has no
representation in user stories. Problem frames fared worse — a dedicated workshop
series (IWAAPF at ICSE 2004, 2006, 2008), sustained academic work at the Open
University and Duisburg-Essen, and essentially zero industrial adoption. Jackson's
own explanation is that it is deliberately "not a development method... rather, a
perspective and a conceptual framework," and industry adopts methods.

### Relevance to us

See §16, question 2, for the full answer. In brief: the *testimony* half of our
split is an exact rediscovery of K, including its epistemology. The *invariant*
half is not S. And the thing they built that we have not is the entailment — the
only mechanism in this whole document that answers "is this set of statements the
right set?"

---

## 5. Parnas & Clements, "A Rational Design Process: How and Why to Fake It" (1985/86)

**Records — VERIFIED, and the conference version is the earlier one.**

- Conference: David L. Parnas & Paul C. Clements, "A rational design process:
  How and why to fake it," in *Mathematical Foundations of Software Development*
  (TAPSOFT '85, Berlin, 25–29 March 1985), Volume 2: Colloquium on Software
  Engineering, LNCS 186, Springer, 1985, pp. 80–100. DOI `10.1007/3-540-15199-0_6`.
- Journal: same title, *IEEE Transactions on Software Engineering* SE-12(2):251–257,
  February 1986. DOI `10.1109/TSE.1986.6312940`. Manuscript received 18 March 1985
  — one week before TAPSOFT.

**Watch the citation.** An ACM DL listing giving "Vol 12, No 1" is wrong; the
journal page header reads No. 2. And a widely mirrored re-typeset PDF (on course
pages at UT Austin, Tufts and elsewhere) is textually near-identical but **not**
page-identical to TSE — its reference list cites a paper from August 1985,
postdating the TSE submission. Do not take page numbers from it.

### Problem

> "Ideally, we would like to derive our programs from a statement of requirements
> in the same sense that theorems are derived from axioms in a published proof...
> The bad news is that, in our opinion, we will never find the philosopher's
> stone. We will never find a process that allows us to design software in a
> perfectly rational way. The good news is that we can fake it."

### Evidence they had — the seven reasons, verbatim from the TSE scan

Section II, "Why Will a Software Design 'Process' Always Be an Idealisation?":

1. "the people who commission the building of a software system **do not know
   exactly what they want and are unable to tell us all that they know**."
2. "Many of the details only become known to us as we progress in the
   implementation. Some of the things that we learn invalidate our design and we
   must backtrack."
3. "human beings are unable to comprehend fully the plethora of details that must
   be taken into account... until we have separated the concerns, we are bound to
   make errors."
4. "all but the most trivial projects are subject to change for external reasons.
   Some of those changes may invalidate previous design decisions."
5. "**Human errors can only be avoided if one can avoid the use of humans.**"
6. "We are often burdened by preconceived design ideas."
7. "Often we are encouraged, for economic reasons, to use software that was
   developed for some other project."

Note reason 7 precisely: the economic pressure named is *component reuse*, not
generic schedule pressure. And the closing observation:

> "Even the small program developments shown in textbooks and papers are unreal.
> They have been revised and polished until the author has shown us what he
> wishes he had done, not what actually did happen."

### Reasoning — why documentation diverges, and it is structural, not moral

Section VI.A is the most directly useful passage in this whole literature for
"why do our docs rot":

> "Most programmers regard documentation as a necessary evil, written as an
> afterthought only because some bureaucrat requires it. They don't expect it to
> be useful. This is a self-fulfilling prophecy; documentation that has not been
> used before it is published, documentation that is not important to its author,
> will always be poor documentation. Most of that documentation is incomplete and
> inaccurate **but those are not the main problems**."

The main problem is **organisation**:

> "The problem with both of these documentation styles is that subsequent readers
> cannot find the information that they seek. It will therefore not be easy to
> determine that facts are missing, or to correct them when they are wrong. **It
> will not be easy to find all the parts of the document that should be changed
> when the software is changed.** The documentation will be expensive to maintain
> and, in most cases, will not be maintained."

Plus boring prose ("Lots of words are used to say what could be said by a single
programming language statement, a formula or a diagram... it leads to inattentive
reading and undiscovered errors"), inconsistent terminology, and myopia
(documents written at project end by people who take the major decisions for
granted).

### Proposed solution

Produce the documents the rational process *would* have produced, in the order it
would have produced them, and treat them as the design medium:

> "The documentation in this design process **is not an afterthought; it is
> viewed as one of the primary products of the project.**"

> "Each document is designed by stating the questions that it must answer and
> refining the questions until each defines the content of an individual section.
> **There must be one, and only one, place for every fact that will be in the
> document.**"

> "**The documentation is our medium of design and no design decisions are
> considered to be made until their incorporation into the documents.**"

And the anti-rot clause, Section V.G:

> "Maintenance is just redesign and redevelopment. The policies recommended here
> for design must be continued after delivery or the 'fake' rationality will
> disappear. **If a change is made, all documentation that is invalidated must be
> changed.**"

**The mechanism nobody remembers, and the only detection mechanism anywhere in
§4–§5 of this document** — typed brackets around every defined term, with a
separate dictionary per type:

> "The special bracketing symbols make it easy to institute **mechanical checks
> for terms that have been introduced but not defined or defined but never
> used.**"

That is a dangling-reference and orphan-reference checker over documentation.
Narrow — it checks *coherence*, never *truth* — but it is more than either
requirements paper offers.

They also deliberately deviate from the mathematics analogy in one place: "We
make a policy of recording all of the design alternatives that we considered and
rejected. For each, we explain why it was considered and why it was finally
rejected." That is an Architecture Decision Record, 1985.

### Evidence that it works — the A-7E

One project, Section VII:

> "Usually, a requirements document is produced before coding starts and is never
> used again. However, that has not been the case for [9]... The organisation
> that has to test the software uses our document extensively to choose the tests
> that they do. When new changes are needed, the requirements document is used in
> describing what must be changed and what cannot be changed."

Reference [9] is Heninger, Kallander, Parnas & Shore, *Software Requirements for
the A-7E Aircraft*, NRL Memorandum Report 3876, 27 November 1978 (**VERIFIED**
from the paper's own reference list, along with the rest of the SCR corpus).
Independently corroborated: Zave & Jackson cite "the A-7 method [Heninger 1980;
Parnas and Clements 1986]" as the notable exception among requirements methods
that enforce designations.

### What happened to it

**The slogan won; the practice did not.** "Fake it" is a standard graduate-course
reading and its descendants are visible — Clements went on to co-author the SEI's
*Documenting Software Architectures*, and the modern ADR practice is Parnas's
"record the rejected alternatives" as a lightweight artifact. But the prescribed
practice — seven formal work products, tabular mathematical requirements, typed
terminology dictionaries with mechanical checks, mandatory re-faking of every
invalidated document on every change — was never mainstream. Agile's "working
software over comprehensive documentation" is the direct negation of "no design
decisions are considered to be made until their incorporation into the
documents."

SCR-style documentation survived where certification demands it (NRL's SCR*
toolset; Lockheed's CoRE variant on the C-130J; Ontario Hydro/AECL's tabular
specifications for the Darlington shutdown systems) — all **ATTRIBUTED**, none of
the primary reports reached. Reported line counts for the C-130J application vary
between sources; do not cite one.

Parnas returned to the problem: **"Software Aging," ICSE 1994, pp. 279–287**
(**ATTRIBUTED**; three fetch attempts 404'd, content from secondary summaries
only — its two named causes, "lack of movement" and "ignorant surgery," should
not be quoted as his words without the paper). And "Precise Documentation: The
Key to Better Software," in Nanz (ed.), *The Future of Software Engineering*,
Springer, 2011, pp. 125–148, DOI `10.1007/978-3-642-15187-3_8` (**VERIFIED**
bibliographically, content not obtained).

### Relevance to us

**1. The diagnosis of doc rot is structural, and we should adopt it.** Docs rot
because there is no unique home for each fact, so you cannot detect absence,
cannot detect error, and cannot find everything a change invalidates. Every
mechanism in this repo that gives a fact a unique id and a unique location — the
ledger, `docs/spec-convention.md`, the ADR series — implements "one, and only
one, place for every fact." That is a better-fitting lineage for those mechanisms
than TMS.

**2. `doc-health.sh` is Parnas's bracket checker.** Its broken-link check is
exactly "terms that have been introduced but not defined." Its forbidden-name
check is the terminology-consistency half. Both are 1985 mechanisms, and both
check coherence, not truth — which is precisely their known limit and should be
stated as their declared blind spot.

**3. The honest warning.** "Fake it" is the closest historical precedent for
"maintain a documentation artifact whose accuracy is a standing obligation," and
it did not take. The cost came from the completeness that made it valuable.
Parnas was explicit that the maintenance clause is what makes the whole thing
work; that is the clause the world declined to pay for.

---

## 6. Knuth, literate programming (1984)

**Records — VERIFIED.** Donald E. Knuth, "Literate Programming," *The Computer
Journal* 27(2):97–111, 1984. DOI `10.1093/comjnl/27.2.97`. Quotations below are
from the preprint typescript (footer: "submitted to THE COMPUTER JOURNAL")
fetched at `https://www.cs.tufts.edu/~nr/cs257/archive/literate-programming/01-knuth-lp.pdf`.
Book: Knuth, *Literate Programming*, CSLI Lecture Notes 27, CSLI Publications,
Stanford, 1992, xvi+368 pp., ISBN 0-937073-80-6. *TeX: The Program* =
*Computers & Typesetting* Volume B, Addison-Wesley, 1986, ISBN 0-201-13437-3.
The Stanford report *The WEB System of Structured Documentation*, CS-TR 980,
1983, is **ATTRIBUTED** (never reached; do not cite a page count for it).

### Problem

Not "programs are under-commented." Knuth's target is that the compiler's
required order of presentation is the wrong order for a human, and that
documentation-as-afterthought is a consequence of that constraint.

> "I believe that the time is ripe for significantly better documentation of
> programs, and that we can best achieve this by considering programs to be works
> of literature."

> "Let us change our traditional attitude to the construction of programs:
> Instead of imagining that our main task is to instruct a computer what to do,
> let us concentrate rather on explaining to human beings what we want a computer
> to do."

> "the programmer's task is to state those parts and those relationships, in
> whatever order is best for human comprehension—not in some rigidly determined
> order like top-down or bottom-up."

### Evidence he had

Personal, self-reported, single-author, and he says so: "Programming is a very
personal activity, so I can't be certain that what has worked for me will work
for everybody," and "discount much of what I shall say as the ravings of a
fanatic who thinks he has just seen a great light."

His strongest quality claim is an *equal-time, better-output* claim, not a
measured defect reduction:

> "the total time of writing and debugging a WEB program is no greater than the
> total time of writing and debugging an ALGOL or PASCAL program, even though my
> WEB programs are much better, and even though I am putting substantially more
> documentation into the programs."

> "In retrospect, the fact that a 'literate' program takes much less time to
> debug is not surprising, because the WEB language encourages a discipline that I
> was previously unwilling to impose on myself."

The external artifacts are TeX and METAFONT in WEB, and *TeX: The Program* as
published proof.

### Reasoning and proposed solution

WEB is bilingual (TeX + Pascal) with two processors: TANGLE emits compilable
source, WEAVE emits typeset documentation. "The process of 'compile, load, and
go' has been slightly lengthened to 'tangle, compile, load, and go.'" He is
explicit that the language pair is incidental: "the same principles would apply
equally well if other languages were substituted."

### What happened to it — including a correction

**The McIlroy exchange is routinely misreported, and if we retell it we should
get it right.** Bentley's May 1986 *Programming Pearls* column introduced
literate programming; the June 1986 column — Bentley, Knuth & McIlroy,
"Programming pearls: a literate program," *CACM* 29(6):471–483, DOI
`10.1145/5948.315654` (**VERIFIED**, full text fetched) — printed Knuth's WEB
program for the "K most common words" problem **plus a commissioned review by
Doug McIlroy**.

McIlroy's review is overwhelmingly positive about literate programming and
negative about the engineering choice:

> "I found Don Knuth's program convincing as a demonstration of WEB and
> fascinating for its data structure, but I disagree with it on engineering
> grounds."

> "because an explanation in WEB is intimately combined with the hard reality of
> implementation, it is qualitatively different from, and far more useful than, an
> ordinary 'specification' or 'design' document. It can't gloss over the tough
> places."

> "Perhaps the greatest strength of WEB is that it allows almost any sensible
> order of presentation. Even if you did not intend to include any documentation,
> and even if you had an ordinary cross-referencer at your disposal, it would make
> sense to program in WEB simply to circumvent the unnatural order forced by the
> syntax of Pascal."

His criticism is that the problem was solved from scratch rather than by
composing existing parts — "A wise engineering solution would produce—or better,
exploit—reusable parts" — followed by a six-stage shell pipeline (`tr` / `tr` /
`sort` / `uniq -c` / `sort -rn` / `sed`) written "on the spot" that "worked on
the first try." And the famous close: "Knuth has shown us here how to program
intelligibly, but not wisely. I buy the discipline. I do not buy the result."

**Bentley took the blame himself, in the same column**: "That is, of course, my
responsibility as problem assigner; Knuth solved the problem he was given."

So "McIlroy demolished literate programming with a six-line shell script" is
false. He endorsed the discipline in print, at length, twice.

**Why it did not take hold — the honest account.** The strongest contemporary,
named evidence is Christopher van Wyk closing his own CACM literate-programming
column in March 1990 (*CACM* 33(3):361, 365, DOI `10.1145/77481.316051`,
**VERIFIED** bibliographically; the quoted text is **ATTRIBUTED**) after a year of
soliciting contributions:

> "Unfortunately, no one has yet volunteered to write a program using another's
> system for literate programming. A fair conclusion from my mail would be that
> one must write one's own system before one can write a literate program, and
> that makes me wonder how widespread literate programming is or will ever
> become."

That is a tooling-burden diagnosis from a Bell Labs researcher who mostly
received new *tools* instead of programs. Knuth's own retrospective (2008
InformIT interview with Andrew Binstock, **ATTRIBUTED** — the live page could not
be re-fetched):

> "Literate programming is a very personal thing. I think it's terrific, but that
> might well be because I'm a very strange person. It has tens of thousands of
> fans, but not millions."

> "Jon Bentley probably hit the nail on the head when he once was asked why
> literate programming hasn't taken the whole world by storm. He observed that a
> small percentage of the world's population is good at programming, and a small
> percentage is good at writing; apparently I am asking everybody to be in both
> subsets."

**What could NOT be verified, and we should stop repeating:** there is
essentially *no* empirical literature on literate-programming adoption. Experience
reports exist — Thimbleby, *Computer Journal* 29(3):201–211, 1986; Ramsey &
Marceau, "Literate programming on a team project," *SP&E* 21(7):677–683, 1991
(both **VERIFIED** bibliographically, neither read) — but no controlled study or
adoption survey was found. The specific folklore (tangling breaks debuggers and
stack traces, woven documents merge badly, IDEs cannot cope) has **no primary
source located**. And "no large multi-developer codebase uses WEB" is
**UNCERTAIN** — the TeX Live toolchain still ships WEB/CWEB sources.

**The descendants, with the lineages kept straight:**

| Tool | Descends from WEB? | Basis |
|---|---|---|
| noweb → Sweave → knitr / R Markdown | Yes, documented | The Sweave manual states R code is embedded "using the noweb syntax... which is usually used for literate programming (Knuth, 1984)" (**VERIFIED**) |
| Org-mode Babel | Yes, explicitly | Schulte, Davison, Dye & Dominik, *JSS* 46(3), 2012, DOI `10.18637/jss.v046.i03`, opens by quoting Knuth 1984 verbatim (**VERIFIED**) |
| Javadoc / Doxygen | **No — different lineage** | The same JSS paper classifies them as "Simple comment extraction engines" with only *partial* LP support, because "they do not recognize named code blocks or reorganize code" (**VERIFIED**) |
| Jupyter / IPython | **Unverified** | No evidence found that IPython claims WEB descent; Mathematica notebooks (1988) predate it (**UNCERTAIN**) |
| doctests / Rust doc tests | **Unverified** — likely independent. Do not claim lineage. |

**The sharpest sourced conclusion**, from the JSS 2012 authors: "Sweave and its
descendants do not support code block re-organization during tangling and thus
only partially support literate programming."

What survived is *interleaving*. What died is *reordering* — the part Knuth
called "perhaps the greatest lesson I have learned."

### Relevance to us

Doctrine §4.1 refuses "literate programming at scale" and gives the reason as
"never survives maintenance." The better-evidenced reason is **tooling burden and
the two-subsets problem**, and the better-evidenced conclusion is subtler: the
interleaving half of the idea won completely and universally, and only the
reordering half died. That matters, because our design is not proposing
reordering at all. §4.1's refusal is therefore aimed at something we were never
going to build, and the live question it should be asking instead is §15.5's:
whether a claim should live *next to* the thing it describes rather than in a
separate ledger.

---

## 7. Cunningham's Fit and FitNesse (2001–2008) — **the doctrine's diagnosis is wrong**

Doctrine §2.3 says: *"FIT did not die because the idea was wrong. It died from
maintenance cost. Specifications went brittle on every code change; teams spent
more effort repairing executable documents than doing the work those documents
described."* Our entire risk analysis rests on that sentence. It was checked
clause by clause.

**Clause 1 survives. Clause 2 is half-right and misordered. Clause 3 is
unsourced, and the only controlled experiments point the other way.**

### Records

- **Fit** = Framework for Integrated Test, created by Ward Cunningham. The 2002
  date is **ATTRIBUTED** (Wikipedia/HandWiki); `http://fit.c2.com/` carries
  "copyright 2002, Cunningham & Cunningham, Inc." (**VERIFIED**). Style note from
  Wikipedia: "'Fit' and '_Fit_' are appropriate usage, but 'FIT' is not."
- **FitNesse — correct our date.** FitNesse's own User Guide says: "FitNesse
  started as an HTML and wiki 'front-end' to FIT ... back in **2001**"
  (**VERIFIED**), not 2003. Credited authors on that page: "Robert C. Martin,
  Micah D. Martin, Patrick Wilson-Welsh & FitNesse contributors."
- **SLIM** = Simple List Invocation Method, described by fitnesse.org as "an
  alternative to Fit," released **November 2008** in build 20081115 (**VERIFIED**
  via a dated post by Eric Lefevre-Ardant). **Correction to a common claim:** no
  source states SLIM became the configured *default*. What is verifiable is that
  it displaced Fit in practice — FitNesse's release notes contain 54 mentions of
  Slim against 2 of Fit, both old. Say "superseded," not "became the default."
- **Book — VERIFIED**: Rick Mugridge & Ward Cunningham, *Fit for Developing
  Software: Framework for Integrated Tests*, Prentice Hall PTR (Robert C. Martin
  Series), 2005. ISBN-13 978-0-321-26934-8, LCCN 2005005894, published 29 June
  2005. Page count conflicts between catalogues (355 vs 384) — cite neither, or
  cite the source.

### Problem and design

Executable documents: business rules stated as HTML/wiki tables, with **fixtures**
in code binding columns to system calls, and the table itself recoloured cell by
cell — green, red, yellow — when the suite runs. Ward's own fixture taxonomy,
from Phil Windley's contemporaneous notes on a Cunningham/Ingerson talk of
**9 July 2003** (**VERIFIED**): "Column fixtures are for logic, action fixtures
are for interaction (buttons on the rows) and row fixtures are for databases.
Fixtures are responsible for type conversion." Independently confirmed by
fitnesse.org's own guide.

### Why it faded — the evidence, in the order the evidence supports

**(1) The collaboration premise failed. This came first.**

The most authoritative practitioner source is **James Shore — who was Fit's
project coordinator.** That is not folklore: `http://fit.c2.com/` itself says "It
was created by WardCunningham and the project is coordinated by JamesShore."

Shore, "The Problems With Acceptance Testing," 26 February 2010
(`https://www.jamesshore.com/v2/blog/2010/the-problems-with-acceptance-testing`,
**VERIFIED**), gives two problems, **in this order**:

1. Customers "weren't interested in doing that" and "often couldn't understand
   and didn't trust tests that were written by others." Responsibility "gets
   handed off to testers, which defeats the whole point."
2. *Then* the cost: acceptance-testing tools "are almost invariably used to create
   end-to-end integration tests, which are slow and brittle"; "tools like Fit
   don't work with refactoring tools. Once you have a lot of tests, they become a
   real maintenance burden."

His conclusion: "acceptance testing isn't worth the cost. I no longer use it or
recommend it."

InfoQ's roundup (Mike Bria, 8 April 2010, **VERIFIED**) states the causal
structure explicitly: "The real planned benefit of an automated acceptance tool,
like Fit, was that the business folks ('customers') would write executable
examples themselves. History has shown that **very** rarely occurs."

Gojko Adzic — who interviewed dozens of teams — leads the same way. His "Top 10
reasons why teams fail with Acceptance Testing," 24 September 2009
(**VERIFIED**), has **"No collaboration" at #1**; "Focusing on tools" is #5 and
"'Test code' not maintained with love" is #7.

**Without the benefit, the cost was unpayable. That is the correct causal order,
and it inverts the doctrine's.**

**(2) The strategy/tool mismatch — Shore diagnosed it in 2007, three years before
he quit.** "Five Ways to Misuse Fit," 7 October 2007 (**VERIFIED**), misuse #1 is
"Use Fit for Test Automation":

> "Fit is actually a fairly weak test automation tool."
> "Fit's strength--the one thing it does better than any other tool I know--is
> that customers are comfortable providing examples in tables."
> "Use Fit for communication. Need a comprehensive regression suite? Use xUnit
> and test-driven development instead."

The one-line version, quoted by InfoQ in November 2007: **"Fit is good for
communication, weak for test automation. People mostly use Fit for test
automation, less for communication."** Much of the brittleness attributed to
executable specification was the brittleness of end-to-end integration testing,
for which Fit was the vehicle.

**(3) Tooling: tests in a wiki, outside refactoring. Strongly supported, three
named dated sources.**

- Mike Roberts, 30 December 2005: "One problem with Wiki's though are that they
  typically sit outside of a team's source control environment." He built a
  CruiseControl.NET rig to version them.
- Johannes Link, 5 March 2008: "Doing 'refactoring' in large FitNesse test
  collections is a real pain in the neck," and "I haven't seen - and could not
  find - a tool for FitNesse that tries to tackle these problems." Users were left
  with "some regex-based search and replace mechanism."
- Shore, 2010: "tools like Fit don't work with refactoring tools."

FitNesse pages *are* files on disk and *could* be versioned. The evidence is that
the default workflow did not, which is why 2005–2006 produced a small genre of
"how to get FitNesse into source control" posts.

**(4) The maintenance-cost claim was contested at the time, by name.** Adzic,
"Mind your boomerangs," 5 April 2010 (**VERIFIED**), argues the friction is real
but front-loaded — "There is a point during the implementation of acceptance
testing where it is enough to give you some value, but there is still a lot of
friction with the tools" — and that the benefits are invisible (bugs that stop
recurring), so teams under-count them. Ron Jeffries, 5 March 2010, concedes the
pain but reads Shore's position as safe only for high-discipline teams.

**(5) The academic evidence exists, it is thin, and it points the OTHER WAY.**

The relevant studies are real and **VERIFIED** bibliographically: Melnik, Read &
Maurer (XP/Agile Universe 2004); Read, Melnik & Maurer (XP 2005); Ricca et al.,
"Talking tests" (IWPSE 2007) and "Are fit tables really talking?" (ICSE 2008,
pp. 361–370, DOI `10.1145/1368088.1368138`); Ricca, Di Penta & Torchiano,
"Guidelines on the use of Fit tables in software maintenance tasks: Lessons
learned from 8 experiments" (ICSM 2008); Haugset & Hanssen (Agile 2008, Agile
2011); Haugset & Stålhane (HICSS 2012).

The one finding retrieved in the authors' own words, from the open-access
companion (Ricca, Torchiano, Di Penta, Ceccato & Tonella, *ECEASST* vol. 8, 2008,
**VERIFIED**):

> "FIT tables help students to correctly perform the maintenance/evolution tasks
> with no significant impact on time."

Students, small tasks — a real limitation. But it is the **only controlled
evidence there is, and its sign is opposite to our draft's third clause.**

**No rigorous industry measurement of Fit/FitNesse maintenance cost was found.**
The maintenance-cost story rests entirely on practitioner testimony — excellent
testimony, named and dated, from the tool's own coordinator — but testimony, and
publicly contested when it was made. **"Teams spent more effort repairing
executable documents than doing the work" is not measured anywhere. Attribute it
to Shore as opinion or drop the quantification.**

**(6) The successor reproduced the failure. This is the most important finding
in this section.**

Irshad, Britto & Petersen, "Adapting Behavior Driven Development (BDD) for
large-scale software systems," *Journal of Systems and Software* 177:110944, 2021,
DOI `10.1016/j.jss.2021.110944` (**VERIFIED**, CC-BY full text retrieved).
Workshops plus industrial evaluation at Ericsson. Practitioner-identified
challenges, verbatim:

> "Practitioners identified the following challenges: specification and ownership
> of behaviors, adoption of new tools, the software projects' scale, and
> **versioning of behaviors**."

> "The practitioner also believed that **BDD is an expensive process to
> follow**... **maintenance of BDD scenarios can be challenging because of the
> textual nature of scenarios**... the **Versioning Control of BDD artifacts** is
> also considered as a challenge in a large-scale context."

Twelve years later, different syntax, same four failure modes: ownership,
maintenance, versioning, cost. Corroborated by Adzic's 2020 ten-years-later survey
(**VERIFIED**): 57% now treat the task tracker as the primary source of truth for
requirements — directly contradicting the living-documentation promise — and 29%
of teams using examples do not automate them at all. And by Aslak Hellesøy in
2018: "most people who use Cucumber don't use it for BDD. They use it for
testing, writing their tests afterwards" — the identical misuse Shore diagnosed
for Fit in 2007.

### Current status — VERIFIED, and the contrast is stark

**Fit is dead.** `http://fit.c2.com/` front page: "Last edited October 13, 2007."
Its download page (last edited 14 October 2009) still points at SourceForge,
Yahoo Groups and RubyForge, and says "A few language implementations were started
but now appear to be abandoned."

**FitNesse is alive** — 2,133 stars, latest release v20251025, commits into March
2026 — but as a *Slim* product, not a Fit one.

**Cucumber is healthy** (`cucumber/cucumber-jvm`, 2,831 stars, pushed August
2026). Concordion exists as a design critique of Fit's table format. And Gherkin
beat Fit tables on *authoring effort only*: dos Santos & Vilain, XP 2018, DOI
`10.1007/978-3-319-91602-6_7` (**VERIFIED**) found "no sufficient evidence to
affirm that one technique is easier to specify test scenarios or better to
communicate software requirements," but "the mean time to specify test scenarios
using Gherkin language is lower than Fit tables."

### Relevance to us — rewrite the risk analysis

**Replace doctrine §2.3's sentence.** A defensible version, every clause sourced
above:

> Fit did not die because the idea was wrong. It died because the benefit that
> was supposed to pay for it never arrived: business people did not write or read
> the tables, so the tests fell to developers and testers — and once that
> happened, the tool was being used for something its own coordinator said it was
> bad at. Only then did the cost become unpayable: slow, brittle end-to-end tests
> living in a wiki that refactoring tools could not reach. The successor did not
> fix this; practitioners on large BDD projects report the same maintenance,
> ownership and versioning problems in 2021. No rigorous industry measurement of
> the maintenance cost exists, and the only controlled experiments found that Fit
> tables *helped* maintenance tasks.

**What this changes about our risk model.** Three things.

1. **The collaboration premise is not our failure mode.** There is no business
   stakeholder who was supposed to read our claims and didn't. Owner testimony
   enters as testimony, not as an executable table. **The single biggest
   documented cause of Fit's death does not apply to us**, which means the FIT
   analogy is weaker evidence against our design than the doctrine treats it as.
2. **The tooling cause does apply, exactly.** "Executable specifications that
   refactoring tools cannot reach" is our 25 `grep -n` claims verbatim. That is
   the part of the FIT story to keep, and it is an argument *for* doctrine L0
   (AST-based evidence), on much better evidence than the doctrine gave.
3. **The successor's failure is the real warning.** Ownership, maintenance,
   versioning, cost — those recurred with a completely different syntax. So they
   are properties of *decoupled executable specification as a category*, not of
   Fit's table format. Doctrine §4.2's lesson ("few and load-bearing") survives
   and is strengthened; its causal story does not.

---

## 8. Architectural fitness functions (2017), ArchUnit, and the older conformance line

**Records — VERIFIED.** Neal Ford, Rebecca Parsons & Patrick Kua, *Building
Evolutionary Architectures: Support Constant Change*, O'Reilly, October 2017,
ISBN 978-1-491-98636-3 (copyright page read directly from a Thoughtworks-hosted
excerpt). 2nd edition: *Building Evolutionary Architectures: Automated Software
Governance*, with Pramod Sadalage, O'Reilly, released December 2022 / copyright
2023, ISBN 978-1-492-09754-9 — **author order is UNCERTAIN**, Thoughtworks and
O'Reilly list it differently; cite "Ford et al."

ArchUnit — **VERIFIED** via the GitHub API: repository `TNG/ArchUnit` created
2017-04-21, first release v0.4.0 on 2017-04-23, v1.0.0 on 2022-10-03,
Apache-2.0, actively maintained. TNG Technology Consulting's own announcement
credits **Peter Gafert**, who presented "ArchUnit — How to keep your architecture
alive" in May 2017.

### The definition

> "An architectural fitness function provides an objective integrity assessment
> of some architectural characteristic(s)."

The provenance is evolutionary computing, in the authors' own house wording via
the Thoughtworks Technology Radar (**VERIFIED**): "Borrowed from evolutionary
computing, a fitness function is used to summarize how close a given design
solution is to achieving the set aims." The blip first appeared in the "Trial"
ring in November 2017 — the term entered practitioner circulation with the book,
from the same organisation.

Note how *broad* the definition is. From the 1st-edition excerpt (p. 10): "**Any
tool that helps assess some architectural characteristic qualifies as a fitness
function.**" There is no membership criterion, no determinism requirement, and no
requirement that the function itself be testable.

### The taxonomy — VERIFIED as an exact list, nothing invented

Chapter 2's categories, in order: **Atomic vs. Holistic**; **Triggered vs.
Continual**; **Static vs. Dynamic**; **Automated vs. Manual**; **Temporal**;
**Intentional Over Emergent** (a preference, not a dichotomy); **Domain-specific**.
Four named combinations: atomic+triggered = unit tests; holistic+triggered =
integration tests; atomic+continual; holistic+continual = Chaos Monkey.

### How do they handle a fitness function that is itself wrong? Almost not at all

This was the question, and the answer is a genuine gap. The complete set of
material found:

**Ownership** — one sentence, from the excerpt (p. 10), **VERIFIED**: "In general,
the definition and maintenance of fitness functions is a shared responsibility
between architects, developers, and any other role concerned with maintaining
architectural integrity."

**A named section, "Review Fitness Functions"** (**ATTRIBUTED** — the section
exists and was reached via a reproducing site plus three independent sets of
practitioner reading notes, not the book): "Review your fitness functions at
least once a year," in a meeting with business and technical stakeholders,
covering "checking the relevancy of the current fitness functions," changes in
scale or magnitude, better measurement approaches, and new functions needed.
Will Larson's notes record the annual cadence and add, in his own words, that
"the author notes this seems infrequent."

**What is absent.** No discussion of false positives as a category. No discussion
of a fitness function encoding an obsolete decision. **No retirement or deletion
procedure.** No testing, validating, or meta-checking of the functions themselves.
No exemption/waiver mechanism. The one adjacent thing handled is *conflict*
between functions (p. 19: "Conflicting goals are inevitable. However, discovering
and quantifying those conflicts early allows architects to make better informed
decisions") — a different problem.

The downstream practitioner literature is equally silent: Martin Fowler's site
(Kiran Prakash, "Governing data products using fitness functions," 2024) and
Thoughtworks' own "Fitness function-driven development" (2019) were both fetched
and neither addresses wrongness.

### Where the honest answer actually exists: in the tools

Two shipped mechanisms address "the rule is wrong or stale," and neither comes
from the fitness-function literature.

**ArchUnit's `FreezingArchRule`** — **VERIFIED**, introduced in v0.11.0, released
2019-07-30. The motivation, from the user guide: "When rules are introduced in
grown projects, there are often hundreds or even thousands of violations, way too
many to fix immediately." It wraps any rule, records existing violations in a
`ViolationStore`, fails only on *new* ones, and updates the store when a violation
is fixed so it cannot regress. By default it **ignores line numbers** — "if a
violation is just shifted to a different line, it will still count as previously
recorded." Then, tellingly, v0.12.0 (2019-11-03) added a mode "to forbid updates
of the `ViolationStore` or the creation of a new `ViolationStore`. This can be
valuable in CI environments" — because the default behaviour lets CI silently
absorb new violations.

**import-linter's stale-exemption detector.** This is the single most useful
finding in this section for us. The option `unmatched_ignore_imports_alerting`
is "the alerting level for handling expressions supplied in `ignore_imports` that
do not match any imports in the graph," with values `error` (**the default**),
`warn`, `none` (**VERIFIED** from the project's own docs). **By default, an
exemption that no longer corresponds to any real import fails the build.** That
is doctrine §4.11 — "a gate that warns forever" — solved mechanically, in a
Python tool, today.

Baselines in sibling tools: dependency-cruiser has `--ignore-known` with a
generated known-violations file (**VERIFIED**); NDepend has "code diff since
baseline" queried in CQLinq (**VERIFIED**); Deptrac's baseline is **UNCERTAIN**;
Structure101 is **dead** — its site now redirects to Sonar, which states plainly
that the products are no longer available for sale (**VERIFIED**).

### The older lineage, which the doctrine skipped entirely

**Perry & Wolf, "Foundations for the Study of Software Architecture," *ACM SIGSOFT
Software Engineering Notes* 17(4):40–52, October 1992, DOI `10.1145/141874.141884`
— VERIFIED and read.** It introduces both terms (p. 43):

> "Architectural erosion is due to violations of the architecture... Architectural
> drift is due to insensitivity about the architecture."

And, on p. 45, what is effectively the fitness-function thesis stated twenty-five
years early:

> "style embodies those decisions that suffer erosion and drift. An emphasis on
> style as a constraint on the architecture provides a **visibility** to certain
> aspects of the architecture so that violations of those aspects and
> insensitivity to them will be more obvious."

**Murphy, Notkin & Sullivan, "Software Reflexion Models: Bridging the Gap Between
Source and High-Level Models," *FSE '95*, pp. 18–28, DOI `10.1145/222124.222136`
— VERIFIED bibliographically; content ATTRIBUTED.** Journal version: *IEEE TSE*
27(4):364–380, 2001, DOI `10.1109/32.917525`. An engineer writes down a high-level
model of what the structure is *supposed* to be, plus a **declared mapping** to
source entities; a tool computes **convergences, divergences and absences**.

Also **VERIFIED** bibliographically: de Silva & Balasubramaniam, "Controlling
software architecture erosion: A survey," *JSS* 85(1):132–151, 2012.

### What happened to it

Fitness functions are mainstream practitioner vocabulary. **No peer-reviewed
empirical study of their adoption or effectiveness was found**, under substantial
search (DBLP's publication search was down and Semantic Scholar rate-limited, so
read this as "not found," not "does not exist"). The two closest hits are both
2025 proposals rather than evaluations. That is a striking asymmetry for a
technique nine years into adoption.

### Relevance to us

**1. Doctrine §2.2 is right that our gates are fitness functions, and the
literature has nothing to teach us about the thing we most need.** Ford et al.
treat a fitness function as an oracle. The doctrine's F9 ("the measuring
instrument itself is wrong") is genuinely unaddressed in the source. Our L2 plan
— a declared blind spot per gate, pinned by a test that fails if someone fixes the
blind spot — is **stronger than anything in the fitness-function literature**, and
we should say so rather than presenting it as adoption.

**2. Adopt import-linter this week.** It is BSD-2, maintained (latest 2.13, July
2026), Python-native, has five contract types (Forbidden, Protected, Layers,
Independence, Acyclic siblings), exits non-zero on violation, and its default
stale-exemption behaviour is exactly the §4.11 rule we currently enforce by
memory. It is a re-runnable falsifiable claim with a built-in answer to "has my
own governance rule gone stale."

**3. Steal reflexion models' outcome vocabulary.** Convergence / divergence /
**absence** is better than our binary. The ledger currently cannot express
absence — "a claim that ought to exist for this part of the system and does not."
That is precisely the blind spot the scratch design's §7 worries about under a
different name.

**4. Perry & Wolf, not Doyle, is the honest 'why this repo has gates' citation.**
Erosion and drift, and visibility as the remedy.

---

## 9. Livshits et al., "In Defense of Soundiness: A Manifesto" (2015)

**Record — VERIFIED, author order confirmed twice (DBLP and Semantic Scholar).**
Benjamin Livshits, Manu Sridharan, Yannis Smaragdakis, Ondřej Lhoták, J. Nelson
Amaral, Bor-Yuh Evan Chang, Samuel Z. Guyer, Uday P. Khedker, Anders Møller,
Dimitrios Vardoulakis, "In defense of soundiness: a manifesto," *Communications of
the ACM* 58(2):44–46, February 2015. DOI `10.1145/2644805`. The authors' preprint
— the file linked from soundiness.org — is at
`https://yanniss.github.io/Soundiness-CACM.pdf` and was read in full.

### Problem

> "Soundness would seem essential for any kind of static program analysis...
> Yet, in practice, soundness is commonly eschewed: **we are not aware of a
> single realistic whole-program analysis tool** ... **that does not purposely
> make unsound choices.**"

The paradox they name: "on the one hand we have the ubiquity of unsoundness in
any practical whole-program analysis tool that has a claim to precision and
scalability; on the other, we have a research community that, outside a small
group of experts, is oblivious to any unsoundness."

### Evidence they had — and they are candid that it is thin

Two things only: named industrial tools whose unsoundness they assert as common
knowledge ("Coverity, Fortify, GrammaTech, IBM"), and a *negative* result from
their own poll:

> "an informal email and in-person poll of recognized experts in static and
> runtime analysis failed to pinpoint a single reliable survey of the use of
> so-called dangerous features (pointer arithmetic, unsafe type casts, etc.) in C
> and C++."

The honest heart of the paper is that the field does not know how bad the problem
is, and they could not find out either.

### Reasoning

"sound modeling of all language features usually destroys the precision of the
analysis... Imprecision, in turn, often destroys scalability." And: "the dominant
practice is one of treating soundness as an engineering choice."

### Proposed solution — the term, and the exact ask

> "We introduce the term **soundy** for such analyses... A soundy analysis aims to
> be as sound as possible without excessively compromising precision and/or
> scalability."

> "We draw a distinction between analyses that are soundy — mostly sound, with
> specific, well-identified unsound choices — and analyses that do not concern
> themselves with soundness."

The asks, verbatim from "Moving Forward":

- "**Soundy is the new sound;** de facto, given the research literature of the
  past decades."
- "**Papers involving soundy analyses should both explain the general
  implications of their unsoundness and evaluate the implications for the
  benchmarks being analyzed.**"
- "As a community, we should provide guidelines on how to write papers involving
  soundy analysis... emphasizing which features to consider handling — or not
  handling."
- "at the least, some effort should be made in experimental evaluations to
  **compare results of an unsound analysis with observable dynamic behaviors of
  the program**."

**The ask is stronger than the doctrine records it.** It is not merely "declare
your gaps." It is *also* "argue that the excluded features do not matter for the
corpus you actually evaluated on." Their own sharpest sentence:

> "**It really does not help the reader for the analysis' author to declare that
> their analysis is sound modulo features X and Y, only to discover that these
> features are present in just about every real-life program!**"

And they shipped a fill-in-the-blank **Soundiness Statement Generator** on
`http://soundiness.org/`, whose boilerplate ends "To the best of our knowledge,
our analysis has a sound handling of all language features other than those
listed above."

The commonly-ignored-feature list in the paper is segregated by language
(C/C++: `setjmp`/`longjmp`, pointer arithmetic, manufactured pointers; Java/C#:
reflection, JNI, dynamic loading, native code; JavaScript: `eval`, dynamic
loading, DOM data flow, `with`, dynamically-computed properties). **The better
list is embedded in the site's own generator JavaScript**, and it includes, in
*all three* language lists, "exceptions and flow related to that," plus integer
overflow in two. Those are not exotic dynamic features; they are ordinary control
flow, routinely dropped.

**The Dagstuhl/workshop origin the doctrine implies could not be verified.**
soundiness.org mentions no workshop, no seminar, and no meeting; the preprint has
no acknowledgements naming a venue. Do not assert it.

### What happened to it

**It largely failed as a norm, and the numbers are small enough to state.** 154
citations, 7 influential (**ATTRIBUTED**, Semantic Scholar) — respectable for a
three-page Viewpoint. A DBLP title search for "soundy" returns, in the entire
computer-science corpus, exactly two relevant papers: Machiry et al., "DR. CHECKER:
A Soundy Analysis for Linux Kernel Drivers" (USENIX Security 2017) and Mondal,
Silva & d'Amorim, "Soundy Automated Parallelization of Test Execution" (ICSME
2021). Both **VERIFIED**. The curated bibliography on soundiness.org has no entry
later than 2015, and the site's HTTPS is broken. **Nobody attaches the generated
statement.**

### Relevance to us

**1. Doctrine §4.5 and L2 are correctly grounded.** F4 is a textbook soundy
analysis with an undeclared blind spot, and Livshits et al. is the exact match.

**2. But the adoption record is evidence about our own plan.** A manifesto with
ten prominent signatories and a fill-in-the-blank form produced two paper titles
in eleven years. **A declaration nobody is forced to make does not get made.**
That is the argument for making `blind_spots` a *required field* refused at
authoring time (scratch design §3.1) rather than a convention — and it means the
scratch design's choice is better-founded than the manifesto it descends from.

**3. Adopt the stronger half of the ask.** Our L2 plan stops at "declare what the
gate does not catch." Livshits et al. also demand you argue the gap does not
matter *for the corpus you ran on*. For `64-reachability.sh` that would read:
"does not see `__init__` re-export laundering; there are N such re-exports in this
repo and here is why they are or are not load-bearing." That second sentence is
what would have prevented the false `recipe.py` conclusion — the declaration
alone would not have.

---

## 10. Program slicing (1981) and change impact analysis (1993/96)

### Records

- **Mark Weiser, "Program Slicing," *Proc. 5th ICSE*, San Diego, March 1981,
  pp. 439–449** — **VERIFIED** (start page read off the PDF; end page from
  DBLP/ACM, **ATTRIBUTED**). Journal version: *IEEE TSE* SE-10(4):352–357, July
  1984, DOI `10.1109/TSE.1984.5010248` — **VERIFIED**, header and footer read.
  The 1979 Michigan PhD is **VERIFIED via Weiser's own reference list**: "Program
  slices: Formal, psychological, and practical investigations of an automatic
  program abstraction method," University of Michigan, 1979. Also his "Programmers
  use slices when debugging," *CACM* 25(7):446–452, July 1982.
- **Robert S. Arnold & Shawn A. Bohner, "Impact Analysis — Towards A Framework
  for Comparison," *Proc. Conference on Software Maintenance (ICSM 1993)*,
  Montréal, pp. 292–301, DOI `10.1109/ICSM.1993.366933`** — **VERIFIED, full text
  read.** Note the author order flips relative to the book.
- Bohner & Arnold, *Software Change Impact Analysis*, IEEE Computer Society Press,
  1996, xiii+376 pp., ISBN 0-8186-7384-2 — **VERIFIED** as to publisher, year,
  ISBN and extent. **Whether it is an edited tutorial anthology could NOT be
  verified**; catalogue records name them as authors, but a separately-indexed
  preface and externally-cited chapters point the other way. Describe it
  cautiously.

### What slicing is, and Weiser's own undecidability theorem

TSE 1984, p. 353, verbatim:

> "*Definition:* A **slicing criterion** of a program *P* is a tuple ⟨*i*, *V*⟩,
> where *i* is a statement in *P* and *V* is a subset of the variables in *P*."

> "*Definition:* A **slice** *S* of a program *P* on a slicing criterion *C* is
> any **executable program** with the following two properties. 1) *S* can be
> obtained from *P* by deleting zero or more statements from *P*. 2) Whenever *P*
> halts on an input *I* with state trajectory *T*, then *S* also halts on input
> *I* with state trajectory *T'*..."

> "**Theorem: There does not exist an algorithm to find statement-minimal slices
> for arbitrary programs.**"

**The computability wall shaped the founding definition, in the founding paper.**
ICSE 1981, p. 441:

> "Unfortunately this condition is too strong, because it implies the
> unsolvability of finding slices."
> "**To fix this problem, the requirement of equivalent projected behaviors can be
> weakened to be: projected behaviors must be equivalent whenever the original
> program terminates.**"
> "no algorithm can always find the slice with the minimum number of statements,
> because of **the impossibility of evaluating the functional equivalence of two
> different pieces of code**."

And on conservatism, TSE p. 353: "Data flow analysis can be used to construct
**conservative** slices, guaranteed to have the slice properties but with possibly
too many statements." Weiser already knew about aliasing ("arrays and pointer
variables usually require worst-case assumptions") and about unknown callees
(TSE p. 355: "calls on external routines must be assumed to both reference and
change any external variable") — which is the 1984 form of today's reflection and
dynamic-dispatch problem.

### The human-factors evidence is weaker than its reputation

Weiser did run a study (ICSE 1981, pp. 444–445): 21 experienced programmers, three
programs of 75/121/150 lines of ALGOL W, bugs "deliberately kept simple." But it
was a **recognition-memory test after debugging**, not observation of debugging.
His own result statement: "In all three programs, the slice relevant to the bug
was remembered as having been used or probably used in almost half of the 63
cases. This was not significantly worse than how well the two adjacent code
segments were remembered." A null result plus a descriptive contrast (adjacent 38
and 36; slice 36; non-adjacent 17 and 12, out of 63).

**Do not use** the widely-repeated "programmers using slicing took only 58% of the
control group's time." It is not in Weiser's paper and no primary source was
found.

### The real numbers on slice size

- Weiser's own 1981 table: 26–37% for programs of 60–380 lines, but 100% for a
  matrix-multiply routine, whose "single-mindedness of its mathematical code made
  it difficult to slice."
- **Weiser's TSE 1984 "44%" figure is routinely mis-cited.** His own key reads
  "**% Size: Size of cluster** as a percentage of total program size" — a cluster,
  not a slice. Do not say "Weiser found slices averaged 44%."
- **Binkley & Harman, ICSM 2003** (**VERIFIED** via the King's College repository):
  43 C programs, just over 1 million lines, 2,353,598 slices, "**an average slice
  size being just under 30% of the original program**." Ignoring calling context:
  +50%.
- **Binkley, Gold & Harman, *ACM TOSEM* 16(2), Article 8, 2007** (**VERIFIED** via
  Crossref's publisher abstract): for the most precise slicer, "the average slice
  contains just under one-third of the program."
- **Why**: Harman, Binkley, Gallagher, Gold & Krinke, "Dependence Clusters in
  Source Code," *ACM TOPLAS*, 2009 (**VERIFIED** as author preprint; exact
  volume/pages **UNCERTAIN**): "large dependence clusters are surprisingly
  commonplace. Most of the 45 programs studied have clusters of dependence that
  consume more than 10% of the whole program. Some even have clusters consuming
  80% or more."

Slicing did not die; it *migrated*. The dependence-graph machinery became
CFL-reachability and the standard framework for interprocedural analysis; it
shipped commercially as CodeSurfer; and dynamic slicing survives in fault
localisation. But note the retreat Horwitz, Reps & Binkley acknowledge in their own
retrospective: their PLDI 1988 work "did not solve... that of producing a slice
that is an **executable projection** of the original program." A slice became a
*set of statements* — strictly weaker than Weiser's definition.

### Impact analysis: SIS / EIS / AIS are genuinely theirs, and from 1993

Arnold & Bohner, §3.4.1, p. 296, verbatim:

> "the ***starting impact set* (SIS#)** is the set of objects that are thought to
> be initially affected by a change. The ***estimated impact set* (EIS#)** is the
> set of objects estimated to be affected by the IA approach... The ***actual
> impact set* (AIS)** is the set of objects... actually modified as the result of
> performing the change... **The AIS is normally not unique, since a change can be
> implemented in several ways.**"

Their own definition of the activity (§2.1): "Impact analysis (IA) is the activity
of identifying what to modify to accomplish a change, or of identifying the
potential consequences of a change." They cite **program slicing explicitly** as
an IA technique — the two literatures are joined in the primary source.

**Ripple effect is NOT theirs**, and they say so: they credit it to Stevens (1974)
and stability to Yau (1980).

**And the framework shipped with no empirical calibration, in a footnote:** "(The
percentages in this column are **suggested starting points**. They may be tuned as
desired.)"

### What is not computable — with real precision and recall

1. **Semantic impact is program equivalence**, which is Weiser's undecidability
   result. Any tool claiming behavioural impact is approximating.
2. **The ground truth is not well-defined** — "The AIS is normally not unique."
3. **Impact through data, configuration, documentation and human process is
   outside the model by construction.** Arnold & Bohner's own Table 3-1 rates
   "Interpretation — How much effort by the user is needed to interpret the
   results (i.e., derive true impacts from IA)?"

**The numbers.** Zimmermann, Weißgerber, Diehl & Zeller, "Mining Version Histories
to Guide Software Changes," *ICSE 2004*, pp. 563–572, DOI
`10.1109/ICSE.2004.1317478` (**VERIFIED**, full text read; extended in *IEEE TSE*
31(6):429–445, 2005). 10,761 transactions across eight open-source projects. At
entity granularity in the navigation scenario, averaged: **recall 0.15, precision
0.26**, with the correct location in the top three 64% of the time. Their own
gloss (p. 7): "The programmer has to check about four suggestions in order to find
a correct one." And the boxed conclusion:

> "**One can either have precise suggestions or many suggestions, but not both.**"

**But** — and this is the part that should change our plan — the *same* machinery
in the **error-prevention** scenario (warning at commit time that something looks
missing) had average recall around 4% and **average precision above 50%**, and in
the closure scenario precision around 0.98: "Only 2% of all transactions cause a
false alarm."

### Relevance to us

**1. Doctrine L5 is aimed at the wrong output.** It asks for "an explicit
dependents check" — an impact *set*. Impact sets are 26% precise. What actually
works, on this evidence, is a **conservative commit-time warning**: high
precision, low recall, cheap to ignore correctly. That is the shape L5 should
take, and Zimmermann et al. is the citation.

**2. The undecidability is not a detail.** Weiser weakened his own definition to
escape it, and static slices still average a third of the program. Any future
proposal to compute "everything affected by changing `Material`" should be read
against that. Our practical form — a checklist item plus a targeted regression
test — is the right size, and the literature supports it rather than embarrassing
it.

**3. The AIS non-uniqueness point is worth internalising.** There is no ground
truth for "what a change should have touched," so a blast-radius gate cannot be
scored for accuracy even in principle. `blast_forecast` (ADR-039) is correctly
framed as an *upper bound*, not a prediction, and that framing is the one the 1993
paper would endorse.

---

## 11. Code as a queryable database — CodeQL, Glean, Kythe, and the Datalog line

### The lineage — all VERIFIED

- **Whaley & Lam, "Cloning-based context-sensitive pointer alias analysis using
  binary decision diagrams," *PLDI 2004*, pp. 131–144, DOI `10.1145/996841.996859`.**
  Full text read. The founding statement of the whole cluster: "Instead of writing
  our program analyses directly in terms of BDD operations, we store all program
  information and results as relations and express our analyses in **Datalog**, a
  logic programming language used in deductive databases." Payoff: "Datalog
  programs are **orders-of-magnitude easier to write**." The tool, `bddbddb`, now
  has 11 stars and a last push in 2016.
- **Lam, Whaley, Livshits, Martin, Avots, Carbin & Unkel, "Context-sensitive
  program analysis as database queries," *PODS 2005*, pp. 1–12, DOI
  `10.1145/1065167.1065169`.** Full text read. Motivation: "it is important to
  **empower programmers to write their own analyses**." Historical framing:
  "The concept of formulating data-flow analysis in compilers as a database query
  was first proposed by Ullman... In 1994, Reps investigated the use of deductive
  database queries."
- **Bravenboer & Smaragdakis, "Strictly declarative specification of sophisticated
  points-to analyses," *OOPSLA 2009*, pp. 243–262, DOI `10.1145/1640089.1640108`**
  — the DOOP framework, whose complaint about `bddbddb` is that it was "a **hybrid**
  between imperative code and a logical specification." `plast-lab/doop` is alive
  (216 stars, pushed 2026-08-01).
- **Jordan, Scholz & Subotić, "Soufflé: On Synthesis of Program Analyzers," *CAV
  2016*** (volume/pages **ATTRIBUTED**). Oracle Labs connection confirmed from the
  paper's own footnote. **Note the fork**: `oracle/souffle` is archived and
  literally described as "DEPRECATED"; `souffle-lang/souffle` is alive under
  UPL-1.0 but low-velocity.
- **The portability tax, which is the honest counterweight to "it's just
  declarative Datalog":** Antoniadis, Triantafyllou & Smaragdakis, "Porting Doop
  to Soufflé," *SOAP'17*, DOI `10.1145/3088515.3088522` — "a roughly **10-person-
  month effort**" for up-to-4x speedups.
- **Hajiyev, Verbaere & de Moor, "codeQuest: Scalable Source Code Queries with
  Datalog," *ECOOP 2006*, pp. 2–27, DOI `10.1007/11785477_2`** (note the
  lowercase `c`), preceded by an OOPSLA 2005 Companion poster that also lists
  Kris De Volder.

### The Oxford → Semmle → GitHub line, and the fork that explains it

Primary source: the **University of Oxford REF2021 Impact Case Study**, "Improving
Software Security via Variant Analysis" (**VERIFIED**, fetched). Verbatim:

> "a number of other research groups, including Laurie Hendren's at McGill and
> **Monica Lam's at Stanford**, had also started using Datalog... At Oxford, de
> Moor's group also provided a Datalog implementation for experimentation using
> **traditional database technology instead of binary decision diagrams**,
> building on previous work by **Thomas Reps** at Wisconsin."

Stanford went BDD; Oxford went relational. That choice is why CodeQL exists
commercially and `bddbddb` does not.

> "**Semmle was founded in 2006** to create the novel technology that realises
> the potential of Datalog for software analysis demonstrated in the Oxford team's
> research."

And the cleanest one-paragraph statement of the thesis:

> "By treating source code as a relational database, and analysis problems as
> queries against a database, deep semantic analyses can be expressed as concise
> queries in an object-oriented query language."

Acquisition — **VERIFIED with primary source**: Nat Friedman, "GitHub welcomes
Semmle," The GitHub Blog, 18 September 2019. The frequently quoted ~$410M sale
price is **ATTRIBUTED to PitchBook**; Oxford's own case study says the real figure
is confidential.

QL itself: Avgustinov, de Moor, Peyton Jones & Schäfer, "QL: Object-oriented
Queries on Relational Data," *ECOOP 2016*, LIPIcs 56, pp. 2:1–2:25 (**VERIFIED**):
"QL compiles to Datalog and runs on a standard relational database... **classes
are logical properties describing sets of values, subclassing is implication, and
virtual calls are dispatched dynamically**."

### The industrial code-fact databases — and a damning pattern

- **Meta's Glean** — open-sourced August 2021 (**VERIFIED** from Meta's own
  engineering post), Haskell server over RocksDB, schema-defined facts, its own
  logic query language **Angle**, Python support, incrementality by "stacking
  immutable databases on top of each other." **Active** (1,377 stars, pushed
  2026-08-03). But it is a *server* built for a monorepo.
- **Google's Kythe** — open-sourced January 2015 (**VERIFIED**), Apache-2.0,
  "language-agnostic graph structure." **Effectively dormant**: ~1.5 commits per
  month for two years against 274 open issues, and after eleven years it has never
  reached version 0.1. Its historic top three contributors have zero commits in
  the last twelve months. (The frequently repeated "successor to Grok" and
  "protobuf-based schema" claims are **UNCERTAIN** — neither appears on any
  kythe.io page fetched.)
- **GitHub's `semantic`** — **archived**, README: "This repository is no longer
  supported or updated by GitHub."
- **GitHub's `stack-graphs`** — `semantic`'s intended successor for precise code
  navigation — **also archived**, last push 2025-09-09.

**The pattern belongs in our document.** GitHub built `semantic` and abandoned it,
built `stack-graphs` to replace it and archived that too. **CodeQL is the only
code-as-database system GitHub still funds, and it is the proprietary one.**

Alive and healthy in the same space: **tree-sitter** (MIT, 26,525 stars, created
2013-11-06 by Max Brunsfeld — his authorship is **VERIFIED** from commit history;
the "at GitHub" attribution is **ATTRIBUTED**) and **SCIP**, which in January 2026
moved out of Sourcegraph into an independent `scip-code` org with its own
governance (**VERIFIED**; the reason for the move could not be established).

### The cost that decides it for us: CodeQL's licence

CodeQL is **split-licensed**, and the split is the whole story.

- **Queries and standard library: MIT.** `github/codeql`, SPDX MIT, active.
- **The engine/CLI: proprietary, and restricted to open-source codebases.** From
  the GitHub CodeQL Terms and Conditions (**VERIFIED**, fetched from
  `https://raw.githubusercontent.com/github/codeql-cli-binaries/main/LICENSE.md`),
  under what you may *not* do:

  > "To otherwise or in any other context use the Software in connection with any
  > codebase that is not an Open Source Codebase (e.g., code in a private repo in
  > GitHub)."

  The paid escape hatch: "if your use of the Software is under a paid customer
  license for GitHub Advanced Security, the restrictions ... do not apply."
  (The EULA still says "Advanced Security" while the docs say "Code Security" —
  a live inconsistency. The commonly quoted per-committer price is **UNCERTAIN**;
  no pricing page was fetched.)

### The other costs, measured against this repo

This repo was measured, not guessed: **250 Python files, 52,969 Python LOC; 300
markdown files, 64,229 lines; 27 shell scripts.** More markdown than code.

- **No build needed for Python** (**VERIFIED** from GitHub's docs) — the one
  favourable fact. But that is also why import resolution is fragile: the
  extractor's virtualenv discovery is a ~30-line script that tries `import pip`
  and otherwise scans `sys.path` for a `site-packages` substring. And since
  CodeQL Action 3.25.0/2.25.0 it **no longer installs Python dependencies** — you
  create the venv or cross-module reasoning silently degrades.
- **A three-year-old open defect** on relative imports (`github/codeql` #13051,
  opened 2023-05-05, still open) emits `[WARN] Failed to find .xxx, no parent
  package of Python module`.
- **The closest public scale data point maps almost exactly onto us.**
  `github/codeql` issue #19928, opened 2025-06-30, still open: **263 Python files,
  ~88,981 lines**, and "The analysis **never finishes, even after more than 2
  hours**." GitHub's response was that this is the cost model, not a bug, and that
  source/sink definitions "need to be specialized."
- **CodeQL's Python semantics are mid-rewrite right now** — the Semmle-era
  points-to engine is being replaced by API graphs and shared CFG/SSA, with PRs
  still open through mid-2026, including one titled "Move `ControlFlowNode`,
  `Expr`, and `Module` points-to to legacy" and one reverting a change "for
  performance reasons." To make a *reproducible* claim you must pin the standard
  library — which pins you into the middle of an unfinished rewrite.
- Every substantial public CodeQL success story found is C/C++/Java security
  research at a security firm or browser vendor. No credible "CodeQL transformed
  my small Python project" report was located.

### Relevance to us — this closes doctrine §7's open question

Doctrine §7 asks: "Should evidence commands move to a real query engine
(CodeQL/Glean) rather than a local AST helper?" **The answer is no, and it can be
closed.** Three reasons, descending:

1. **Licensing disqualifies it before any technical argument.** The terms forbid
   using the engine "in connection with any codebase that is not an Open Source
   Codebase." Building a *falsifiability* discipline on a licence violation is
   self-defeating.
2. **The scale economics are inverted.** CodeQL is engineered so that a 1.4M-variable
   OpenJDK points-to analysis terminates. We have 53k lines we wrote, and the
   closest public data point at our scale never finished in two hours.
3. **Its Python semantics are under reconstruction**, so a pinned claim means
   freezing on a mid-rewrite snapshot.

**What to do instead**, in order:

1. **`import-linter`** for structural claims (§8).
2. **A ~100-line `ast`-based fact extractor of our own**, emitting one row per
   (module, def, call, import, decorator) into SQLite or JSONL, run from a script
   and diffed in CI. That is the PODS 2005 idea at the scale it is warranted:
   real SQL over our code, zero licence exposure, sub-second runtime, and a schema
   *we* control — so the claim is exactly as falsifiable as we make it. **This,
   not CodeQL, is our "code as a queryable database."** `grimp` (BSD-2, the import
   graph engine under import-linter, usable standalone) is a ready building block.
3. **Semgrep CE** (LGPL-2.1 engine; note only CE is LGPL and the registry rules
   are under a separate licence "available only for internal business use") for
   pattern-level claims, with our own rules.
4. **Keep ripgrep** for genuinely textual facts.

The honest finding, and it should temper doctrine L0's ambition: for a
53k-line single-author repo the gap between "structured queries plus tests" and
"a code database" is much narrower than the literature implies — and the systems
that tried to close that gap for everyone (`semantic`, `stack-graphs`, Kythe,
`bddbddb`) are archived, dormant or dead. **The one that survived commercially
survived by not being open.**

---

## 12. What we missed, part 1 — the mechanism we actually built

### 12.1 Feldman's `make` (1978/79) — the real ancestor

**Records — VERIFIED.** Stuart I. Feldman, "Make — A Program for Maintaining
Computer Programs," *Software: Practice and Experience* 9(4):255–265, 1979, DOI
`10.1002/spe.4380090402`. The technical-report version was read: the 7th Edition
UNIX manual Volume 2 printing, byline "S. I. Feldman / Bell Laboratories / Murray
Hill," **printed date 15 August 1978**. (A Bell Labs CSTR #57, 1977, is
**ATTRIBUTED**.)

**Problem.** Feldman's opening paragraph is our ledger's problem statement,
written in 1978:

> "Unfortunately, it is very easy for a programmer to forget which files depend on
> which others, which files have been modified recently, and the exact sequence of
> operations needed to make or exercise a new version of the program. After a long
> editing session, one may easily lose track of which files have been changed and
> which object modules are still valid, since **a change to a declaration can
> obsolete a dozen other files**. Forgetting to compile a routine that has been
> changed or that uses changed declarations will result in a program that will not
> work, and a bug that can be very hard to track down. On the other hand,
> **recompiling everything in sight just to be safe is very wasteful**."

That last sentence is the precision/soundness trade-off, named in the first
paragraph of the original paper. It is *exactly* the trade-off `invalidate-scan`
makes.

**Solution.** A declared dependency manifest plus file modification times.
Verbatim from the abstract: "The basic operation of Make is to find the name of a
needed target in the description, ensure that all of the files on which it depends
exist and are up to date, and then create the target if it has not been modified
since its generators were." And: "The operation of the command depends on the
ability to find the date and time that a file was last modified."

**Evidence he had.** None empirical. A tool paper with a workflow argument, and
candid about scope: "Make is most useful for medium-sized programming projects."

**What happened.** Universal adoption; its failure modes became a research agenda.

### 12.2 Mokhov, Mitchell & Peyton Jones, "Build Systems à la Carte" (2018)

**Record — VERIFIED.** *Proceedings of the ACM on Programming Languages*
2(ICFP), Article 79, September 2018, DOI `10.1145/3236774`. Read in full.

**The contribution is a coordinate system.** Every build system decomposes into a
**scheduler** (what order to rebuild in) and a **rebuilder** (how to decide
something needs rebuilding), and "we can combine any scheduler with any rebuilder,
and obtain a correct build system." Table 2, verbatim:

| Rebuilding strategy | Topological | Restarting | Suspending |
|---|---|---|---|
| Dirty bit | **Make** | Excel | — |
| Verifying traces | Ninja | — | Shake |
| Constructive traces | CloudBuild | Bazel | — |
| Deep constructive traces | Buck | — | Nix |

**Their correctness definition, which is the gift here:**

> "We can now say what it means for a build system to be correct, something that
> is seldom stated formally. Our intuition is this: when the build system
> completes, the target key, and all its dependencies, should be up to date. What
> does 'up to date' mean? It means that if we recompute the value of the key
> (using the task description, and the final store), we should get exactly the same
> value as we see in the final store."

**The known failure modes of the `make` cell**, verbatim:
- Timestamps are unsound: "Technically, you can fool Make by altering the
  modification time of a file without changing its content."
- Under-declared dependencies: "**Untracked dependencies** Some tasks depend on
  untracked values — for example C compilation will explicitly list the source.c
  file as a dependency, but it may not record that the version of gcc is also a
  dependency."
- Hermeticity has a floor: "Systems like Bazel use various sandboxing techniques
  to guard against missing dependencies, but none are likely to capture all
  dependencies right down to the CPU model and microcode version."
- Volatility is a third category: tasks defined to change every build "are best
  modelled as depending on a special key RealWorld whose value is changed in every
  build."
- **Early cutoff** is the property `make` lacks: "When it executes a task and the
  result is unchanged from the previous build, it is unnecessary to execute the
  dependent tasks... Make and Excel do not [support it], whereas Shake and Bazel
  do."

### 12.3 STRIPS (1971) — the same idea, eight years before either

**Records — VERIFIED, both read.** Richard E. Fikes & Nils J. Nilsson, "STRIPS: A
New Approach to the Application of Theorem Proving to Problem Solving,"
*Artificial Intelligence* 2(3–4):189–208, 1971; and their retrospective, "STRIPS,
a retrospective," *Artificial Intelligence* 59:227–232, 1993. Context: McCarthy &
Hayes, "Some Philosophical Problems from the Standpoint of Artificial
Intelligence," *Machine Intelligence 4*, 1969, pp. 463–502 (**VERIFIED**, full text
at `http://www-formal.stanford.edu/jmc/mcchay69/`), which names the frame problem
and its cost — "with *n* actions and *m* fluents we might have to write down *mn*
such conditions."

**This is the finding a naive survey misses.** STRIPS did not stop at "unmentioned
facts persist." It explicitly handled *derived* facts whose support an operator
could destroy, and its solution is a hand-declared dependency list. Verbatim:

> "it may be the case that a world model contains clauses that are derived from
> other clauses in the model... Now, if one of the clauses on which the derived
> clause depends is deleted, then the derived clause must also be deleted."
>
> "We deal with this problem by defining a set of primitive predicates... and we
> require that **any nonprimitive clause in the world model have associated with it
> those primitive clauses on which its validity depends**."

That is `evidence_paths`, written in 1971.

**And the authors' own verdict on it, 1993:**

> "Also, the STRIPS 'solution' to the frame problem was vague and flawed. It was
> many years before the ideas were made precise and a satisfactory formal
> semantics developed."

with a footnote conceding the mechanism's unsoundness: "the technique for finding
relevant operators of matching goals to add lists is only a heuristic since the
delete lists of operators are ignored."

The **"STRIPS assumption"** is their own term for the persistence rule: "a plan
operator affects only those aspects of the world explicitly mentioned in the
operator's deletions and additions lists." The **"sleeping dog strategy"** is
McDermott's (1987), per the Stanford Encyclopedia — not Fikes & Nilsson's; don't
misattribute it.

The **Yale shooting problem** (Hanks & McDermott, *Artificial Intelligence*
33(3):379–412, 1987 — **VERIFIED** bibliographically, text not read) showed that
*minimising change* is not the same as *reasoning correctly about persistence*.

### Relevance to us — this is the most consequential correction in the document

**The ledger's actual mechanism is `make`, not Doyle.** Measured against
`.truth/claims.jsonl` on 2026-08-03: **656 invalidation records against 42
premise records**, and **204 of 217 claims carry `evidence_paths`** (187
paths-only, 17 paths+TTL; only 3 are TTL-only). Belief death in this ledger comes
overwhelmingly from *a commit touching a watched path* — a declared manifest plus
a change signal. That is Feldman 1978. The TMS lineage accounts for 42 edges;
the build-system lineage accounts for 656.

Both `make` and Doyle's TMS were published in 1979. **We cited the wrong one.**

Three consequences, all cheap and all concrete:

1. **We are in the weakest cell of Table 2 — dirty bit × topological.** We store
   *paths*, not content hashes, so a whitespace or comment commit invalidates. The
   Ninja/Shake row is one field away: **store a content hash of each watched path
   alongside the last verified anchor, and skip staling when the hash is
   unchanged.** This is nearly free in git and kills a large class of false
   staleness — the exact cost curve the doctrine fears.
2. **We have no early cutoff.** When a stale claim is re-verified and its verdict
   is unchanged, nothing stops there; the staleness has already propagated. Adding
   cutoff at re-verification is the second cheap win.
3. **We have no `RealWorld` category.** Business-domain claims depend on nothing
   in the repo, so a path-based trigger can never fire for them. The build-systems
   answer is to model them as *always volatile* — which is what a TTL is. That
   validates the TTL mechanism and says why it must not be conflated with path
   watching: **they are two different rebuilders, not two configurations of one.**

And two warnings from the same lineage:

- **The dependency manifest is an under-approximation, and always will be.**
  `make`'s untracked-dependency problem is our under-declared `evidence_paths`
  problem, and Bazel-style hermeticity has a floor even with a sandbox. Fikes &
  Nilsson called their version "vague and flawed" *in retrospect, having invented
  it*. That is the honest ceiling on what path-watching can promise, and it should
  be a declared blind spot of the whole ledger, not just of individual gates.
- **Adopt their correctness definition as a periodic audit.** "If we recompute the
  value of the key, we should get exactly the same value as we see in the final
  store" transposes to: *the ledger is correct if re-running every claim's command
  against the current tree reproduces every stored verdict.* At 217 claims that is
  a brute-force run, and it is the only ground truth no amount of incremental
  staleness bookkeeping can substitute for.

---

## 13. What we missed, part 2 — executable documentation that actually worked

### 13.1 iComment (2007) — the closest existing artifact to a claim ledger

**Record — VERIFIED and read.** Lin Tan, Ding Yuan, Gopal Krishna & Yuanyuan Zhou,
"/*iComment: Bugs or Bad Comments?*/", *SOSP '07*, pp. 145–158, DOI
`10.1145/1294261.1294276`.

**Problem**, verbatim from §1.1 — and it is our premise, published in 2007:

> "It is common for developers to change code without updating comments
> accordingly as developers may not be motivated, may not have time or simply
> forget to do so. Furthermore, as opposed to source code that always goes through
> a series of software testing before release, **comments cannot be tested to see
> if they are still valid.**"

**The two-sided failure**, verbatim from the abstract:

> "As software evolves, they can easily grow out-of-sync, indicating two problems:
> (1) bugs — the source code does not follow the assumptions and requirements
> specified by correct program comments; (2) bad comments — comments that are
> inconsistent with correct code."

**Yield**, verbatim: "iComment automatically extracts **1832 rules** from comments
with **90.8-100% accuracy** and detects **60 comment-code inconsistencies, 33 new
bugs and 27 bad comments**, in the latest versions of the four programs [Linux,
Mozilla, Wine, Apache]. **Nineteen of them (12 bugs and 7 bad comments) have
already been confirmed** by the corresponding developers."

**Relevance.** Two things transfer hard.

- **The disambiguation is irreducibly human.** A mismatch is *either* a bug *or* a
  bad comment, and nothing in the tool can tell you which. That is exactly our
  `diverged` state, and ADR-012's `--mechanical` subtype is our (correct)
  attempt to record which side moved. iComment is the citation for why that
  distinction has to exist.
- **The yield is a realistic prior.** 1,832 machine-extracted rules over four of
  the most-reviewed codebases in existence produced 60 inconsistencies, 19
  developer-confirmed. Value in this kind of system is *concentrated*: a handful of
  claims will earn the whole apparatus and most will be overhead. Identifying
  which is the actual design problem, and it is the same problem doctrine §4.2
  ("few and load-bearing") names without a mechanism.

### 13.2 Doctests — the only form that achieved universal adoption

**Record — VERIFIED** from the Rust documentation:

> "`rustdoc` supports executing your documentation examples as tests. **This makes
> sure that examples within your documentation are up to date and working.**"

The lineage runs back through Python's `doctest`.

**Relevance, and it is uncomfortable.** This is the only mechanism in the whole
history surveyed here that achieved *universal* adoption for "keep written
statements about a system true as the system changes." It won for one reason:
**the claim and its check are the same text.** No watched-path list, no staleness
state machine, no ledger — the statement *is* the check.

Every design in this document that *separated* the claim from its verifier —
Fit tables in a wiki, Code Contracts, JML, Spec#, PEP 316, traceability links,
TSQL2's hidden attributes — died or stalled. The one that fused them is in every
Rust and Python project on earth.

That is the strongest empirical argument bearing on our architecture, and **it
points against the decoupling.** The honest counter is that domain claims
("the supplier ships 18 mm only") have no code site to live at — but that is an
argument for *two* mechanisms, not for putting code-facts in a ledger. It is the
same conclusion the scratch design reaches from a different direction, and it is
worth noticing that doctrine §2.2 already lists doctests as "the successful,
surviving version" and then does not act on the implication.

---

## 14. What we missed, part 3 — the reliability argument is refuted

**Record — VERIFIED bibliographically.** John C. Knight & Nancy G. Leveson, "An
experimental evaluation of the assumption of independence in multiversion
programming," *IEEE TSE* SE-12(1):96–109, 1986, DOI `10.1109/TSE.1986.6312924`.
The controversy it caused is documented: same authors, "A reply to the criticisms
of the Knight & Leveson experiment," *ACM SIGSOFT SEN* 15(1):24–35, 1990, DOI
`10.1145/382294.382710`.

**Sourcing caveat.** The paper itself could not be fetched. The abstract below is
verified via a faithful verbatim reproduction in a KTH seminar document; the
design details (27 students, Pascal, an anti-missile specification, 551 coincident
failures on the most common case, independence rejected at α = 0.01) are
**ATTRIBUTED** to that summary, not to the paper.

**Abstract:**

> "In all, **27 versions of a program were prepared independently from the same
> specification at two universities** and then subjected to **one million tests**.
> The results of the tests revealed that the programs were individually
> **extremely reliable** but that **the number of tests in which more than one
> program failed was substantially more than expected**."

**What happened to it.** Bitterly contested — hence the 1990 reply — and it won.
The consensus explanation is that independently-built components fail together
because they share the *specification*, the problem's *difficulty structure*, and
human *cognitive biases*. **The hard cases are hard for everyone.**

### Relevance to us

**This refutes an argument the doctrine makes implicitly and never states.** The
ledger's reliability story is a voting story: 217 independently re-checkable
claims, so the chance our self-picture is systematically wrong is small. Knight &
Leveson kills that inference. Our claims are not independent, and they are
non-independent in every way the experiment identified — written against a shared
understanding of the domain, many authored by the same agent lineage with the same
blind spots, and, **worse than N-version programming, the verification command was
usually written by whoever wrote the claim.** In N-version at least the *oracle*
was independent.

The sharp version: **a claim that is subtly wrong is likely to have a subtly wrong
command, because both are hard for the same reason.** That is not a hypothesis —
it is what happened to `tr-ce5c7845`, whose sentence was about a mapping in one
file while its command counted substrings in two others.

Two consequences:

1. **"217 claims, all green" carries far less information than 217 × "one claim,
   green."** Any future dashboard that totals green claims is measuring
   correlation, not correctness (and doctrine §4.8 already forbids the count as a
   target for a different reason).
2. **This is a much stronger argument for ADR-010 (session separation) than Fagan
   is.** Fagan 1976 says independent review catches things. Knight & Leveson says
   *why*, and says that the residual correlated failures are exactly the ones you
   care about. The concrete implication we are not yet acting on: **have a
   different author write the verification command than wrote the claim**, and
   treat a claim whose command was written by its own author as carrying materially
   less evidential weight. That is a cheap, mechanical change to the authoring loop
   in `docs/truth-ledger-machinery.md`.

---

## 15. What we missed, part 4 — shorter entries that still change something

Each of these is verified and load-bearing, but does not need a full section.

### 15.1 Naur, "Programming as Theory Building" (1985) — the strongest argument *against* this whole project

**Record — VERIFIED.** Peter Naur, "Programming as theory building,"
*Microprocessing and Microprogramming* 15(5):253–261, 1985, DOI
`10.1016/0165-6074(85)90032-8`. Reprinted in *Computing: A Human Activity*, ACM
Press / Addison-Wesley, 1992, ISBN 0-201-58069-1. Full text read.

His thesis is not "documentation gets stale." It is stronger and it deserves a
fair hearing:

> "programming in this sense primarily must be the programmers' building up
> knowledge of a certain kind, knowledge taken to be basically the programmers'
> immediate possession, **any documentation being an auxiliary, secondary
> product**."

The load-bearing step is a claim about the *kind* of knowledge:

> "The dependence of a theory on a grasp of certain kinds of similarity between
> situations and events of the real world gives the reason why the knowledge held
> by someone who has the theory **could not, in principle, be expressed in terms
> of rules**. In fact, the similarities in question are not, and cannot be,
> expressed in terms of criteria, no more than the similarities of many other
> kinds of objects, such as human faces, tunes, or tastes of wine, can be thus
> expressed."

And the sharp edge of his evidence — case 1, the compiler handover — is that group
B **had the documentation, had read it, and still got it wrong**: "In several major
cases it turned out that the solutions suggested by group B were found by group A
to make no use of the facilities that were not only inherent in the structure of
the existing compiler but were **discussed at length in its documentation**."

His conclusion is radical: "program revival, that is reestablishing the theory of a
program merely from the documentation, is strictly impossible," and it is better to
discard the program text and start again.

**Relevance.** Do not strawman this in the doctrine — engage it. Two honest
counter-arguments and one concession:

- Naur's transmission mechanism is "work in close contact with the programmers who
  already possess the theory." That is unavailable to an agent starting cold every
  session. If the alternative to a lossy written theory is *no* theory, a lossy
  shadow is an improvement, not a category error. Naur never considered a reader
  with perfect recall of text and zero continuity of practice.
- An executable claim is a proposition that fights back — it can be falsified by
  the machine without a human noticing. That does not rescue the theory; it does
  rescue a subset of the facts.
- **But his deepest point survives.** The knowledge that decides *which claims are
  worth having* is exactly the residue he says cannot be written down. The ledger's
  coverage question is not answerable by the ledger. That is the same gap the
  Zave–Jackson entailment names (§4), the same gap QuickCheck names (§15.7), and
  the same gap the scratch design's §7 admits. Three independent literatures
  converging on one hole is the most interesting structural fact in this document.

### 15.2 Lehman's laws (1980) — with a correction

**Record — VERIFIED, full scan read.** M. M. Lehman, "Programs, Life Cycles, and
Laws of Software Evolution," *Proceedings of the IEEE* 68(9):1060–1076, September
1980, DOI `10.1109/PROC.1980.11805`.

**Correction to a common citation: the 1980 paper has FIVE laws, not seven.** The
paper says so — "it led to a set of five laws." Law VII (Declining Quality) and
Law VI (Continuing Growth) come later; VI is dated 1991 and VII/VIII to 1996/97,
published in Lehman, Ramil, Wernick, Perry & Turski, "Metrics and Laws of Software
Evolution — The Nineties View," IEEE METRICS 1997, DOI `10.1109/METRIC.1997.637156`
(**VERIFIED** as a record; the law dating is **ATTRIBUTED**). Do not cite Proc.
IEEE 1980 for Declining Quality. Note also that the modern one-line renderings of
laws I and II are the post-1996 revisions, not the 1980 wording.

**The part that matters to us is the E-type classification**, and it is genuinely
Lehman's, in this paper:

> "The third class, E-programs, are inherently even more change prone. They are
> programs that mechanize a human or societal activity."
> "**The program has become a part of the world it models, it is embedded in it.**"

and, on why correctness is the wrong frame:

> "For an E-program as an entity on the other hand, validity depends on human
> assessment of its effectiveness in the intended application. Correctness and
> proof of correctness of the program as a whole are, in general, irrelevant."

**Relevance.** This is the correct opening paragraph for "why domain facts expire":
not carelessness, but a property of E-type systems embedded in a world that changes
underneath them. Use it as the premise. Do **not** try to derive a design from it —
Lehman's laws are statistical regularities over large multi-team industrial systems,
and he names his own threshold: "They have no meaning until a system, a project and
the organizational metasystem are well established."

### 15.3 Bitemporal data — "retraction" is the wrong verb

**Record — VERIFIED, full text read.** Richard T. Snodgrass & Ilsoo Ahn, "Temporal
Databases," *IEEE Computer* 19(9):35–42, September 1986, DOI
`10.1109/MC.1986.1663327`. Definitions verbatim: "**transaction time, the time the
information was stored in the database**" versus "**valid time, the time when the
relationship in the enterprise being modeled was valid**." And the reason they must
be separated: "One limitation of supporting transaction time is that the history of
database activities, rather than the history of the real world, is recorded."

His book — *Developing Time-Oriented Database Applications in SQL*, Morgan
Kaufmann, 1999 (copyright page says 2000), ISBN 1-55860-436-7 — is **free from the
author's own site** and states: "**A transaction-time table is append-only.**"

**What happened.** TSQL2 was submitted to ISO in 1995, generated "considerable
controversy," and **the project was cancelled in 2001** (Kulkarni & Michels,
"Temporal features in SQL:2011," *SIGMOD Record* 41(3):34–43, 2012 — **VERIFIED**,
read). Date & Darwen's critique is that "TSQL2 involves 'hidden attributes'" and is
therefore "certainly not relational." SQL:2011 shipped a different design with
different vocabulary (system-versioned tables; application-time periods), and
Kulkarni & Michels note in 2012 that they were aware of exactly **one** commercial
implementation. Martin Fowler's practitioner take (2021, **VERIFIED**): "If we can
avoid using bitemporal history, then that's usually preferable as it does complicate
a system quite significantly."

**Relevance — a precise diagnosis.** The ledger as built is a **pure transaction-time
system**: an append-only log of *check events* ("on this date we ran this command and
it passed"). It has no valid-time axis — no way to assert "claim C held over commits
[A, B)" as a fact about the code, independent of when anyone ran the checker. That
gap is why "retraction" feels wrong for `tr-4476e4d8`. **Retraction is a
transaction-time operation — "we were mistaken." What actually happened was a
valid-time event — "the world changed."** Conflating them is the taxonomy defect the
scratch design §1 identifies, named correctly.

The cheap version: git already supplies the valid-time axis for free, because commit
order *is* the timeline of the modelled world. And the repo has already half-found
the standard temporal representation by instinct — claims are rolled to successor ids
rather than mutated. Adding an explicit `valid_from_commit` / `valid_to_commit` to
the existing successor chain gets most of the benefit at a fraction of SQL:2011's
cost. **Do not import the full machinery**; the standards record is a warning.

### 15.4 Incremental view maintenance and DRed — a better-engineered answer to a smaller problem

**Records — VERIFIED.** Gupta, Mumick & Subrahmanian, "Maintaining Views
Incrementally," *SIGMOD 1993*, pp. 157–166, DOI `10.1145/170035.170066`. The best
free citation is Gupta & Mumick, "Maintenance of Materialized Views: Problems,
Techniques, and Applications," *IEEE Data Engineering Bulletin* 18(2):3–18, 1995
(read in full). Book: *Materialized Views: Techniques, Implementations, and
Applications*, MIT Press, ISBN 0-262-57122-6 (year listed as 1998 or 1999 depending
on catalogue — **UNCERTAIN**). Also Blakeley, Larson & Tompa, "Efficiently Updating
Materialized Views," *SIGMOD 1986*, pp. 61–71 (**VERIFIED** bibliographically, text
not reached).

**DRed**, in the authors' own words:

> "The DRed algorithm computes changes to the view relations in three steps. First,
> the algorithm computes an **overestimate of the deleted derived tuples**... Second,
> this overestimate is **pruned** by removing those tuples that have alternative
> derivations in the new database... Finally, the new tuples that need to be inserted
> are computed."

Its known pathology, from Motik, Nenov, Piro & Horrocks (**VERIFIED**, read):
"Overdeletion can thus be very inefficient when facts are derived more than once,
and when facts contribute to many proofs of other facts."

**And the concept that names our `evidence_paths` exactly**: the 1995 survey calls
it the "query independent of update" or "**irrelevant update**" problem — deciding
when a modification leaves a view unchanged.

**Relevance — three honest limits, and one transferable idea.**

IVM is far more mature than any TMS: optimality results, complexity bounds,
thirty-five years of production deployment. But it buys that with assumptions we
cannot make. (a) It *symbolically differentiates a view definition*; you cannot
differentiate `pytest -q`. Every IVM optimisation evaporates when support is a
black-box exit code — including the counting algorithm, whose precondition is
knowing how many ways a fact is supported. (b) Its dependency graph is **derived**
from the query and therefore sound by construction; ours is hand-declared and can
be an *under*-approximation. **IVM's guarantees do not transfer, because they rest
on a derived dependency graph we do not have.** (c) Everything relevant must live in
the database; "our supplier ships 18 mm only" has no `Q`.

The transferable idea is Motik et al.'s: **before cascading staleness to dependents,
check whether the claim itself still holds.** Exploring *support* beats exploring
*consequences* when proof trees are shallow — and at depth 1, ours are as shallow as
they get. That is the same recommendation §12.3 reaches from the build-systems side,
arrived at independently, which is a good sign.

### 15.5 Design by Contract, and the study that should most change our staleness rule

**Records — VERIFIED.** Bertrand Meyer, "Applying 'Design by Contract'," *Computer*
(IEEE) 25(10):40–51, October 1992 (full scan read). **Correction to a common
citation:** Meyer's "Eiffel: programming for reusability and extendibility" is a
*SIGPLAN Notices* 22(2):85–94 (February 1987) article, **not** an OOPSLA paper. The
origin is Meyer, "Design by Contract," in Mandrioli & Meyer (eds.), *Advances in
Object-Oriented Software Engineering*, Prentice Hall, 1991, pp. 1–50 — the 1992
IEEE piece is the popularisation.

Meyer's frame is an attack on defensive programming, and his contract is a
**division of labour**: "what is an obligation for one party is usually a benefit
for the other," with the pragmatic rule that "the best solution is the one that
achieves the simplest architecture."

**What happened.** Every attempt to put full DbC into a mainstream language ended in
deprecation, deferral, or a rounding-error user base, while bare `assert` survived
everywhere. Eiffel's `EiffelStudio` has 54 GitHub stars. Python's PEP 316,
"Programming by Contract for Python" (created 2 May 2003), is **still "Deferred"**
twenty-three years later. And the clearest death certificate: **Microsoft's
CodeContracts repository was archived on 15 July 2023**, and Microsoft Learn says
"Code contracts aren't supported in .NET 5+... **Consider using Nullable reference
types instead.**"

**That replacement is the real lesson.** The industry's answer to "how do we state
and enforce a precondition" turned out to be *push the checkable part into the type
system* — nullable reference types, Option/Result, sum types — and let the rest be
prose. Note also that in Eiffel, Ada 2012 and D alike, **contract checking is off or
partial by default**.

**The study that matters most to us — VERIFIED, extended version read.** Estler,
Furia, Nordio, Piccioni & Meyer, "Contracts in Practice," *FM 2014*, pp. 230–246,
DOI `10.1007/978-3-319-06410-9_17`. Corpus: "**21 contract-equipped Eiffel, C#, and
Java projects totaling more than 260 million lines of code over 7700 revisions**."

Findings, verbatim from the boxed results:

- "The **implementation** of an average routine changes much more frequently than
  its **specification**." Wilcoxon signed-rank *V* = 0, *p* = 9.54·10⁻⁷, **Cohen's
  *d* > 0.99**.
- "The overwhelming majority of contracts involves **Void/null** checks. In
  contrast, quantifiers appear very rarely."
- "Qualitative trends of measures involving contracts do **not** change significantly
  whether we consider or ignore **inherited** contracts." Meyer's most distinctive
  mechanism turned out empirically to be inert.

And their §5.5 explanation of *why* contracts stay aligned:

> "Contracts are *executable* specifications... **Therefore, their contracts cannot
> become grossly misaligned with the implementation: inconsistencies quickly
> generate runtime errors, which can only be fixed by reconciling implementations
> with their specifications.**"

**Relevance, and it is a warning with a number attached.** Our per-claim evidence
command is an attempt to buy exactly that mechanism for non-executable statements,
and that instinct is right. But note what Estler measures: in a corpus where specs
*are* executable, **specifications change roughly an order of magnitude less often
than implementations**. Our "watched path touched → STALE" rule assumes the
opposite — that code churn is evidence a claim needs re-checking. **Expect a high
false-stale rate by construction, and expect the human cost of that to be what kills
the ledger** — which is the same shape as their observed "specification fatigue,"
where contract density gracefully decreases as a project grows. This is the FIT
curve made measurable, and §12.3's content-hash fix is the direct countermeasure.

A companion result worth carrying: Casalnuovo, Devanbu, Oliveira, Filkov & Ray,
"Assert Use in GitHub Projects," *ICSE 2015*, pp. 755–766 (**VERIFIED**, read). 69
projects, 35,262 KLOC. Two findings: **"64.59% of total added assertions are deleted
or modified"** — machine-checkable statements really do rot — and, less comfortably,
"adding the first assert to a file has a significant and sizable effect on bugs, but
after the first, on average for all developers, **adding additional asserts has no
appreciable difference**," with the benefit concentrated where *many* developers
touch a method and null where few do. **We are a one-owner repo.** The counter —
and it is a real one, but it must be argued rather than assumed — is that our
"developers" include agents, and every agent session is a low-ownership,
low-continuity contributor, which is precisely the regime where they found asserts
help most.

### 15.6 Traceability — the field that already lived our problem for thirty years

**Record — VERIFIED and read.** Cleland-Huang, Gotel, Huffman Hayes, Mäder & Zisman,
"Software traceability: trends and future directions," *FOSE at ICSE '14*, pp. 55–69,
DOI `10.1145/2593882.2593891`.

The failure mode is not decay-to-absence. It is decay-to-plausible-wrongness, plus a
governance pathology, verbatim:

> "A recent analysis of the traceability documents submitted to the FDA... revealed
> numerous problems related to the overall completeness and correctness of the trace
> data. Not only was traceability data **incomplete, incorrect, and conflicting** in
> many cases, there were clear indications that **trace links had been created at the
> very end of the process in many projects, specifically for certification
> purposes**."

Their own field's neglect: "10% of papers mapped to planning topics, **44% mapped to
creating, 15% to maintaining**, and 31% to usage." Their stated grand challenge is
traceability "established and sustained with **near zero effort**," and their process
model — Creating → Using → Maintaining, with transitions "Trace maintenance required
[elements change]" and "Trace retired" — is structurally our ledger.

**The counterweight, and it is the honest case *for* us — VERIFIED**: Mäder & Egyed,
"Do developers benefit from requirements traceability when evolving and maintaining a
software system?", *Empirical Software Engineering* 20(2):413–441, 2015, DOI
`10.1007/s10664-014-9314-z`. A controlled experiment with **71 subjects** re-performing
real maintenance tasks: subjects with traceability "performed on average **24% faster**
on a given task" and "created on average **50% more correct solutions**."

**Relevance.** A trace link *is* a claim plus its watched paths, and this is arguably
a closer structural match than Design by Contract. Two things to take: the FDA
finding is our cautionary tale — **a ledger maintained by an agent at session close
to make `truth ready` go green is at acute risk of retroactive creation for
compliance**, which is exactly the pathology that discredited traceability. And the
Mäder–Egyed numbers are the best available evidence that when the links are present
and correct the benefit is large.

### 15.7 QuickCheck (2000) and Hughes' industrial retrospective (2016)

**Records — VERIFIED.** Koen Claessen & John Hughes, "QuickCheck: A Lightweight Tool
for Random Testing of Haskell Programs," *ICFP 2000*, pp. 268–279, DOI
`10.1145/351240.351266` (read). John Hughes, "Experiences with QuickCheck: Testing
the Hard Stuff and Staying Sane," in *A List of Successes That Can Change the World*,
2016, pp. 169–186, DOI `10.1007/978-3-319-30936-1_9` (read; its own abstract notes
"This is not a typical scientific paper").

The oracle move, from the 2000 paper: "A testing tool must be able to determine
whether a test is passed or failed; the human tester must supply an automatically
checkable criterion of doing so. We have chosen to use formal specifications for this
purpose." Hughes' 2016 statement of why a property beats an expected value: "This test
has thirty possible correct outcomes!... The only practical way to decide if a test
such as this has passed or failed, is via a property that distinguishes correct from
wrong results."

**Two findings transfer with unusual precision.**

*The adequacy admission* (2000, §6.6) is our problem stated twenty-six years earlier
and never solved by them:

> "The major limitation of QuickCheck is that there is no measurement of test
> coverage: it is up to the user to investigate the distribution of test data and
> decide whether sufficiently many tests have been run... **A programmer who does not
> risks gaining a false sense of security from a large number of inadequate tests.**"

*The error distribution*, same section: "We have observed that the errors we find are
divided roughly evenly between errors in test data generators, errors in the
specification, and errors in the program." Hughes 2016 escalates it: "Errors are
often in the model, rather than the code. **Calling something a specification does not
make it right!**"

And the industrial anchor, from the Volvo/AUTOSAR work: "We formalized the
specification in 20,000 lines of QuickCheck code. We used it to test a million lines
of C code in total, from 6 different suppliers, finding more than 200 problems—of
which **well over 100 were ambiguities or inconsistencies in the standard itself!**"

**Relevance.** If we cite one thing for "a claim ledger's real yield is disagreements
between two independent descriptions," cite Hughes 2016 — it is the only source found
where someone confronted all three of our problems at industrial scale at once. And
act on the error distribution: **roughly a third of the ledger's future red lights
will be the claim being wrong, not the code**, so the re-verification workflow must be
able to express that as a first-class outcome. (It already can — `diverge --mechanical`
per ADR-012 — which the literature retrospectively validates.) *Caveat:* QuickCheck
properties are universally quantified over generated inputs; our claims are single
assertions about a codebase's current state. **Do not describe the ledger as
"property-based testing" without that qualifier.**

### 15.8 Bornholt et al., ShardStore (2021) — the closest published thing to what we are building

**Record — VERIFIED, read.** James Bornholt, Rajeev Joshi, Vytautas Astrauskas,
Brendan Cully, Bernhard Kragl, Seth Markle, Kyle Sauri, Drew Schleit, Grant Slatton,
Serdar Tasiran, Jacob Van Geffen & Andrew Warfield, "Using Lightweight Formal Methods
to Validate a Key-Value Storage Node in Amazon S3," *SOSP 2021*, pp. 836–850, DOI
`10.1145/3477132.3483540`.

Abstract, verbatim:

> "We do not aim to achieve full formal verification, but instead emphasize
> automation, usability, and **the ability to continually ensure correctness as both
> software and its specification evolve over time**... Our work has prevented **16
> issues** from reaching production."

Cost anchors: 40,000+ lines of frequently-changing code; reference models "1% of the
implementation code"; total validation apparatus "only 13% of the total code base...
an overhead that compares favorably to formal verification approaches that report
3–10× overhead"; built by "two formal methods experts working full-time for nine
months and a third expert who joined for three months." Handover: "18% of the lines
of code in the test harnesses were last edited by a non-formal-methods expert... **the
need for such harnesses is now a standard question during code review.**"

**Their staleness mechanism, §4.2 "Coverage metrics":**

> "As the code evolves over time, new functionality may be added that is not reachable
> by the existing property-based test harness... Both types of changes risk **eroding
> the coverage** of property-based tests... To mitigate these risks, our test harnesses
> generate code coverage metrics for the implementation code to help us identify blind
> spots that are not sufficiently checked, including newly added functionality that
> the reference model may not know about."

**And their honest failure, §8.3:** a bug their validation should have caught but did
not, found in manual code review instead, because "the cache size was configured to be
very large in all tests" so the cache-miss path was unreachable. Plus a warning worth
pinning up: "biasing introduces the risk of baking our assumptions into our tests,
when our goal in adopting formal methods is to invalidate exactly such assumptions."

**Relevance.** Cite this first, ahead of AWS's TLA+ paper, for "how does a real team
keep machine-checked statements true as the system changes." Their answer to the
drift problem is structurally ours with a different proxy: **they detect drift by
measuring what the checks can still reach; we detect it by watching file paths.** Both
are proxies for the same question, and their §8.3 story is the honest demonstration
that the proxy can be silently wrong. One more thing worth copying: their validation
lives in the repo as ordinary unit tests, "distinguished from other tests only by
naming conventions and module hierarchy" — the doctests lesson (§13.2) again, from a
production system.

For contrast, the AWS TLA+ paper — Newcombe, Rath, Zhang, Munteanu, Brooker & Deardeuff,
"How Amazon web services uses formal methods," *CACM* 58(4):66–73, 2015, DOI
`10.1145/2699417` (**VERIFIED** as a record; quotations below are from the AWS-authored
preprint "Use of Formal Methods at Amazon Web Services," 29 September 2014, hosted on
Lamport's site — **do not attribute these strings to the CACM version without
re-checking**). Its most transferable line is the limit, not the success:

> "On learning about TLA+, engineers usually ask, 'How do we know that the executable
> code correctly implements the verified design?' **The answer is that we don't.**"

That is the boundary our ledger sits on — better off than they were (our commands touch
the real repo, not a model) and worse off (no state-space exploration, so a 35-step
interleaving bug is invisible to us). Also free from that paper: the vocabulary
discipline. They "initially avoid the words 'formal', 'verification', and 'proof', due
to the widespread view that formal methods are impractical," and pitched it internally
as "exhaustively testable pseudo-code."

### 15.9 Leads not pursued

Verified enough to name, not enough to build on. Listed so nobody re-derives them.

- **Daikon** — Ernst, Cockrell, Griswold & Notkin, "Dynamically discovering likely
  program invariants **to support program evolution**," *IEEE TSE* 27(2):99–123, 2001,
  DOI `10.1109/32.908957` (**VERIFIED** bibliographically). The genuine *alternative
  architecture*: infer invariants from executions rather than write them, so staleness
  is impossible because nothing is persisted. Counter-evidence (**ATTRIBUTED**):
  Polikarpova et al. found Daikon could not recreate all developer-written assertions
  and about a third of generated assertions were incorrect or irrelevant. The
  architectural question — persist claims and manage staleness, versus regenerate and
  have none — is worth posing explicitly, because our design answers it silently.
- **Metamorphic testing** — Chen, Cheung & Yiu, HKUST-CS98-01, re-issued as
  arXiv:2002.12543 (**VERIFIED** as to the report number; the 1998 date is
  **ATTRIBUTED**). Real industrial teeth in compiler testing (Le, Afshari & Su, PLDI
  2014: "147 confirmed, unique bug reports for GCC and LLVM"; Yang, Chen, Eide &
  Regehr, PLDI 2011: "more than 325 previously unknown bugs"). But both operate on a
  cheap, infinitely-generatable input space. A few of our claims have metamorphic
  shape; most do not. **Do not claim the ledger "is" metamorphic testing.**
- **Alloy and the small scope hypothesis** — Daniel Jackson & Vaziri, "Finding Bugs
  with a Constraint Solver," *ISSTA 2000*, pp. 14–25 (**VERIFIED**), where the
  hypothesis is stated by name. *(Daniel Jackson of MIT is a different person from
  Michael Jackson of §4; they share a surname and once co-authored a 2006 chapter.)*
  The portable idea is the licence for many cheap bounded checks over few expensive
  proofs. **The much more actionable relative is Marinov, Andoni, Daniliuc, Khurshid &
  Rinard, "An Evaluation of Exhaustive Testing for Data Structures," MIT CSAIL, 2003
  (an unrefereed technical report — not in DBLP or Crossref).** It makes "is my checking
  adequate?" operational, and its answer is mutation: "**mutation adequacy is a
  stronger criterion than code coverage**." Translated: the way to know whether 217
  claims are enough is not to count them or watch them all pass, but to make deliberate
  wrong changes and count how many go red. That is doctrine L1's `truth mutate`, with
  an empirical warrant. **The commonly circulated citation "Andoni, Daniel, Khurshid,
  Marinov — Evaluating the small scope hypothesis" is garbled: "Daniel" is a truncation
  of Dumitru Daniliuc, and no such published paper was found.**
- **Provenance** — Buneman, Khanna & Tan, "Why and Where: A Characterization of Data
  Provenance," *ICDT 2001*; Green, Karvounarakis & Tannen, "Provenance semirings,"
  *PODS 2007*; W3C PROV-DM and PROV-O, both W3C Recommendations of 30 April 2013 (all
  **VERIFIED**). The field's own negative result is the useful part: *where*-provenance
  is the weakest of the three. `evidence_paths` is where-provenance and can only answer
  "did something near this move," never "would this still hold." **The theoretically
  correct reframing is that the evidence command *is* the provenance and the path list
  is a derived index of it** — which, if adopted, makes the content-hash fix in §12.3
  the obvious next step rather than an optimisation.
- **Self-admitted technical debt** — Potdar & Shihab, "An Exploratory Study on
  Self-Admitted Technical Debt," *ICSME 2014* (**VERIFIED**, read): SATD in 2.4%–31% of
  files, and "**only between 26.3% - 63.5%** of self-admitted technical debt gets
  removed from projects after introduction." The transferable point is the base rate for
  *flag disposition*: a system that converts commits into STALE flags is a flag-generation
  machine, and most flags historically stay put. Note the counter-finding they themselves
  cite: Fluri et al. found "**97% of comment changes are done in the same revision as the
  code**," which does not support the strong "documentation always drifts" folk theorem.
  Bavota & Russo's larger MSR 2016 study is **VERIFIED** bibliographically but its
  survival-time result could not be obtained — **do not fill that number in from memory.**
- **Runtime verification** — Leucker & Schallhart, "A brief account of runtime
  verification," *JLAP* 78(5):293–303, 2009 (**VERIFIED**, not read). Mostly a forced
  fit: RV monitors an execution trace, we check a repository state. One idea is worth a
  sentence — RV's finite-trace semantics requires a *third* truth value meaning "not yet
  determined," and our `stale` is arguably that value rather than a failure.
- **The 2020 expert survey on formal methods** — Garavel, ter Beek & van de Pol, *FMICS
  2020*, LNCS 12327, pp. 3–69 (**VERIFIED**, read). Read the methodology before citing
  any number: it is a hand-picked panel of 130 formal-methods insiders, not a sample of
  industry. Its one durable finding is that the ranked limiting factors are
  overwhelmingly human — training, tooling maintenance, lifecycle integration, learning
  curve — and the authors' summary is that "obstacles arising from human factors
  predominate." Its companion finding matters more for us: **every documented success is
  at a large organisation with a specialist team attached.** The evidence that lightweight
  formal methods work in a one-person shop is thin to nonexistent.

---

## 16. The two direct questions

### Question 1 — is the truth ledger really a TMS, or is that analogy loose?

**It is loose, and it is loose in the direction that costs us something.**

The evidence is structural and was measured against `.truth/claims.jsonl` on
2026-08-03, not argued from the prose.

**(a) There is no belief network to maintain.** The `premise` record is
schema-constrained: `payload` requires exactly `issue` (any string) and `claim`
(matching `^tr-[0-9a-f]{8}$`). **No record kind can make a claim depend on a
claim.** All 42 premise records in the ledger carry an `issue` field pointing at a
work item (`wk-` or `kuchnie-`). The dependency graph is therefore bipartite,
depth 1, and acyclic *by construction* — claims at the bottom, work items on top,
one hop between them. Doyle's TMS *is* the propagation algorithm over a network of
arbitrary depth. **There is nothing here to propagate.** A depth-1 dependency
lookup is a join.

**(b) None of the mechanisms that define a TMS are present.**

| Doyle 1979 | Truth ledger |
|---|---|
| SL justification with an **outlist** — belief supported by the *absence* of another belief | No outlist. No claim is believed because another is not. This is the paper's central novelty and we have zero of it. |
| **Well-founded support**, circular support forbidden | Cycles are permitted; ADR-013 resolves a redirect cycle to "that first-repeated value" — deterministic but arbitrary. Different in kind. |
| **Label propagation** through believed-repercussions | One hop, evaluated on read. |
| **Dependency-directed backtracking**: on contradiction, walk the argument, find the culprit assumption, justify it OUT, record a **nogood** | Absent. `contradicts` marks both sides `disputed` and stops. It is a nogood of size 2 — and there are **zero `contradicts` records in the ledger**. |
| A node is OUT because its support became invalid | A claim goes stale because **a commit touched a watched path** |

**(c) The mechanism that actually kills beliefs here is not a TMS mechanism at
all.** 656 invalidation records against 42 premise records. 204 of 217 claims
carry `evidence_paths`; only 3 are TTL-only. Belief death in this ledger is
**~94% path-triggered and ~0% support-triggered.** That is a declared dependency
manifest plus a change signal — Feldman's `make`, published the same year as
Doyle's paper (§12). Our own doctrine's L3 heading, "the TMS you already have,"
attaches a 1979 pedigree to 42 edges and leaves the 656 unexplained.

**(d) `--supersedes` is not a TMS operation.** In a TMS you never redirect a
justification; you add one and the label recomputes. `truth premise --supersedes`
is a manual, per-issue rewrite of a dependency edge, performed by a human, with
the choice recorded. In AGM terms that is a **selection function executed by
hand** — precisely the thing AGM proves the postulates cannot determine (§3).
That is a *good* design and it has a real citation. It is just not Doyle's.

**What is genuinely TMS-shaped**, and it is worth keeping the name for: the single
premise edge is exactly a monotonic SL-justification with an empty outlist, and
HELD is the work-item analogue of going OUT. ADR-001's matrix — `live` passes,
`unverified` warns, `cannot_verify` blocks only P0, `stale`/`diverged`/`retracted`/
missing always block — is a graded IN/OUT labelling, and Doyle's insistence that
IN/OUT are *not* truth values is the right warrant for keeping those states
distinct rather than collapsing them to a boolean.

**So: the ledger contains the simplest possible fragment of a JTMS, embedded in a
build system.** Calling the whole thing a TMS is an overstatement, and it has two
concrete costs. It borrows credibility the design does not inherit — TMS is a
1979-pedigreed mechanism and ours is a 1979-pedigreed *different* mechanism. And
it points future work at the wrong shelf: doctrine §7 asks whether to extend
toward ATMS and whether TMS-over-code-facts is novel, when the productive
questions are the ones the build-systems literature answers in a table (§12.3) —
content-hash verifying traces, early cutoff, and a volatile category — all three
of which are cheap, and all three of which directly attack the false-stale rate
that §15.5 says will be our actual killer.

**The corollary on ATMS: the refusal is right, the reason is wrong.** Doctrine
§4.6 refuses ATMS as "research-grade" and too expensive. de Kleer's own criterion
is about fit, not cost: "Conventional TMSs are oriented to finding one solution...
The ATMS is oriented to finding all solutions." We have one belief set about this
codebase and zero uses of our one multi-world verb. Refuse ATMS because **we do
not have the problem it solves** — an argument that does not expire when compute
gets cheaper.

**And on novelty (doctrine §7's third open question): no, and it should be
dropped.** TMS-over-code-facts is unusual, but "machine-checkable statements about
a system, with a declared mapping to source, re-checked as the system changes" has
prior art in at least four places: software reflexion models (1995, §8), iComment
(2007, §13.1), the traceability field (thirty years, §15.6), and Daikon (2001,
§15.9). None is TMS-shaped. All are the same problem.

### Question 2 — is invariant-vs-testimony a rediscovery of Zave–Jackson?

**Half of it is an exact rediscovery. The other half is not, and the half we are
missing is the half that does the work.**

**Testimony ≈ K, and the match is precise, down to the epistemology.** The scratch
design's testimony layer — not computable, needs a source and a date and an actor,
immutable, superseded rather than retracted, never re-verified because there is
nothing to re-run — is Zave & Jackson's *statement of domain knowledge*: "an
indicative property intended to be relevant to the software development project."
The mood distinction is the same distinction: indicative statements "describe the
environment as it is in the absence of the machine," they are *elicited* rather
than chosen, and — as §2 of their paper puts it about assertions generally — one
"might be true or false and should be validated before it is used." The scratch
design's `confidence: confirmed | assumption | hearsay` is a coarser version of the
same idea, and Jackson's L3 lift assumption ("a highly probable *assumption* rather
than an unalterable fact") is exactly what `confidence: assumption` is for.
**Rediscovery: confirmed.**

**Invariant ≠ S, and this is where the mapping breaks.** A Zave–Jackson
specification is an *optative property of the environment*, stated only in shared
phenomena, directly implementable, not referring to the future. Our invariants —
"no first-party module is unreachable without a declaration," "the BOM quantity
fold is single-source" — are constraints on the **machine's internal structure**.
Zave & Jackson put that outside their vocabulary deliberately: "components of the
machine state cannot be designated. Designations refer to the real world, and the
machine state may have no direct correspondence to the real world." Our invariants
are *design* constraints, and their real home is the architecture-conformance
lineage — Perry & Wolf's erosion and drift, Murphy's reflexion models, fitness
functions (§8) — not requirements engineering.

**So the split is a two-way rediscovery of a three-way distinction, and the missing
third is R.** Their notation rule (p. 26, rule 4) is binding: "Each property or
assertion must be identified as a requirement, statement of domain knowledge, or
specification." We have testimony (K) and something that is neither S nor K, and we
have no requirements at all.

**What they already solved that we have not: the adequacy obligation.**

`S, K ⊢ R`, plus the five completion criteria, is a *definition of done* for a body
of statements. It answers the question our design cannot: **why is this the right
set of statements?** The scratch design proposes 15–25 invariants and 20–40
testimony records and offers no answer to "why these?" — and its §4 admits as much,
conceding that no design solves F9 because "a wrong invariant reports GREEN exactly
as confidently as a right one."

That concession is exactly the gap the entailment closes, and closing it costs
nothing mechanical. It costs writing down R. An invariant that no requirement
depends on is either unnecessary or documents an unstated requirement; a
requirement no invariant and no testimony supports is unguarded. **That check is
free, it is a fitness function over the ledger itself, and it is the single most
valuable idea in this document that we are not already doing.**

Three smaller things they solved that we have not:

- **Designations.** Every atomic term must have a written, maintained, informal
  explanation of its real-world meaning. `docs/GLOSSARY.md` is a designation list;
  Zave & Jackson would make it an enforced obligation ("maintained as an essential
  part of the requirements documentation") rather than a convention.
- **Assertion versus definition.** An assertion "might be true or false and should
  be validated"; a definition "might be useless or misleading, but it cannot be
  false." A ledger claim that is really a definition is unfalsifiable by
  construction — which is doctrine F2 ("evidence that cannot fail") arriving from
  logic instead of from mutation testing, and a cheaper screen than a mutation run.
- **Consistency as a separate obligation.** Their criterion (5) requires a proof
  that S and K are consistent. We have `contradicts` and have never used it. A flat
  set of 217 claims has no composition rule and nothing prevents two from being
  jointly unsatisfiable.

**What they did NOT solve, and neither will we.** Keeping K true as the world
changes. Completion criterion (2) is the whole mechanism: "validated (checked
informally) as true of the environment." One human, informally, once. Jackson's
aquaplaning aircraft is what that costs when it fails, and his later work escalates
it only to a *duty* to "detect, or even to anticipate, failures" with no notation
for doing so. Even WRSPM, the fully formalised 2000 successor, keeps W as a bare
premise.

**So we should stop claiming the split and start claiming the small thing we
actually added.** A TTL on a testimony record — "re-ask the owner about the
cutting rate in 180 days" — is a scheduled re-validation of a domain assumption.
It is crude, it is a timer rather than a monitor, and it is nonetheless more than
the 1997 framework, the 2000 formalisation, or the problem-frames book offer. That
is a modest, defensible, *true* novelty claim, and it is worth more than an
overstated one.

---

## 17. What this lineage says we got wrong or missed

Ordered by how much it should change what we do next. Each item names the section
with the evidence.

**Wrong**

1. **The FIT diagnosis is misordered, and its quantitative clause is unsourced
   (§7).** The best-evidenced account — from Fit's own project coordinator — puts
   the *failed collaboration premise* first and cost second. "Teams spent more
   effort repairing executable documents than doing the work" is measured nowhere;
   the only controlled experiments found Fit tables *helped* maintenance tasks with
   no significant time cost. And BDD reproduced the same four failure modes in
   2021. The lesson survives; the causal story must be rewritten. **This matters
   most because the collaboration premise is the part that does not apply to us —
   which makes FIT weaker evidence against our design than the doctrine treats it
   as, and makes the tooling cause (executable specs that refactoring cannot reach
   — our 25 `grep -n` claims) the part to take seriously.**

2. **We cited the wrong 1979 paper (§12, §16 Q1).** 656 invalidation records
   against 42 premise edges. The ledger's dominant mechanism is a declared
   dependency manifest plus a change signal — Feldman's `make` — and calling the
   whole thing a TMS misdirects future work toward ATMS and away from the three
   cheap upgrades the build-systems literature hands us in a table.

3. **The ATMS refusal has the wrong rationale (§2, §16 Q1).** Refuse it because we
   have one belief set and zero `contradicts` records, not because it is expensive.

4. **The novelty claim should be dropped (§16 Q1).** Doctrine §7 asks whether
   TMS-over-code-facts has prior art. The answer is that the *problem* has plenty —
   reflexion models, iComment, traceability, Daikon — none of it TMS-shaped.

5. **The Knuth refusal is aimed at something we were never going to build (§6).**
   Only the *reordering* half of literate programming died; the interleaving half
   won universally. And if we ever retell the McIlroy story, it is misreported: he
   endorsed the discipline in print, twice, at length, and Bentley took the blame
   for the problem statement.

6. **"Retraction" is the wrong verb (§15.3).** Retraction is a transaction-time
   operation ("we were mistaken"). What killed `tr-4476e4d8` was a valid-time event
   ("the world changed"). The scratch design calls this a taxonomy defect and is
   right; Snodgrass & Ahn 1986 is the vocabulary for fixing it, and git already
   supplies the missing axis for free.

7. **Three smaller citation errors to fix if these ever appear in our prose:**
   Lehman's 1980 paper has **five** laws, not seven — Declining Quality is from
   1996/97 (§15.2). Meyer's 1987 Eiffel paper is *SIGPLAN Notices* 22(2), not
   OOPSLA (§15.5). And the Soundiness Manifesto's Dagstuhl origin could not be
   verified anywhere (§9).

**Missed**

8. **Software reflexion models (Murphy, Notkin & Sullivan, 1995) — the closest
   structural ancestor, and we never cited it (§8).** A human-authored model of what
   the structure should be, a declared mapping to source, and a mechanical
   re-check. It also hands us a better outcome vocabulary: convergence /
   divergence / **absence**. The ledger cannot currently express absence — "a claim
   that ought to exist for this part of the system and does not" — which is exactly
   the blind spot the scratch design's §7 worries about under a different name.

9. **The adequacy obligation (§4, §16 Q2).** `S, K ⊢ R` is the only mechanism in
   this entire lineage that answers "is this the right set of statements?" It is
   free to adopt, it is a fitness function over the ledger itself, and it is what
   doctrine F9 concedes no design solves.

10. **Doctests are the only universally adopted form, and they won by fusing the
    claim with its check (§13.2).** Every decoupled design in this document died or
    stalled. Doctrine §2.2 already notices this and does not act on it. The live
    question is not "AST helper or CodeQL" but "should a code-fact live next to the
    code rather than in a ledger at all?"

11. **Knight & Leveson refutes our unstated reliability argument (§14).** 217
    claims are not 217 independent checks — and we are worse off than N-version
    programming, because the claim and its command usually share an author. This is
    a stronger warrant for ADR-010 than Fagan, and it implies a cheap change to the
    authoring loop: **different author for the claim and for its command.**

12. **Estler et al. measures the assumption our staleness rule is built on, and
    finds the opposite (§15.5).** In a corpus of 260M lines where specifications
    *are* executable, specifications change roughly an order of magnitude less often
    than implementations (Cohen's *d* > 0.99). "Watched path touched → STALE"
    assumes code churn implies a claim needs re-checking. **Expect a high
    false-stale rate by construction.** That is the FIT curve made measurable, and
    §12.3's content-hash fix is the direct countermeasure.

13. **`import-linter`'s stale-exemption detector already solves doctrine §4.11
    (§8).** `unmatched_ignore_imports_alerting` defaults to `error`: an exemption
    that no longer matches any real import fails the build. It is Python, BSD-2,
    maintained, and adoptable this week. ArchUnit's `FreezingArchRule` is the same
    idea for baselines — including the v0.12.0 lockdown mode added because the
    default let CI silently absorb new violations.

14. **The impact-analysis plan targets the wrong output (§10).** Impact *sets* run
    at 26% precision. The same machinery as a **conservative commit-time warning**
    hit above 50% precision with 2% false alarms. That is the shape L5 should take.

15. **Doctrine §7's CodeQL question can be closed: no (§11).** The licence forbids
    the engine on a private commercial repo without paid Code Security; the closest
    public data point at our scale never finished in two hours; and its Python
    semantics are mid-rewrite. Do `import-linter` plus a ~100-line `ast` fact
    extractor into SQLite instead — that *is* the PODS 2005 idea at the scale it is
    warranted.

16. **The fitness-function literature has no answer to "what if the function is
    wrong," and ours is better than the source (§8).** Ford et al. offer shared
    ownership and an annual review meeting. Our L2 plan — declared blind spot per
    gate, pinned by a test that fails when someone fixes the blind spot — exceeds
    it. Say so rather than presenting it as adoption. And adopt the *stronger* half
    of the soundiness ask (§9): not just "declare the gap" but "argue the gap does
    not matter for the corpus you actually ran on."

17. **Naur deserves an answer, not omission (§15.1).** "Programming as Theory
    Building" is the strongest argument against this entire project, and it is a
    better argument than the doctrine's refusal list contains. The honest reply is
    that his transmission mechanism — apprenticeship with people who hold the theory
    — is unavailable to an agent that starts cold every session, so a lossy written
    shadow is an improvement over nothing rather than a category error. That reply
    should be written down, because it is also the strongest *justification* the
    ledger has.

18. **The traceability field's governance pathology is our acute risk (§15.6).**
    FDA submissions were found to contain trace links "created at the very end of
    the process... specifically for certification purposes." **A ledger healed by an
    agent at session close to make `truth ready` go green is the same failure.**
    That risk is not on the doctrine's list and should be.

19. **Casalnuovo's null result deserves an explicit answer (§15.5).** The measured
    benefit of assertions was concentrated where many developers touch the same
    code and null where few do. We are a one-owner repo. The counter — that agent
    sessions *are* the many low-continuity contributors — is probably right, but it
    is currently assumed rather than argued, and it is the load-bearing
    justification for the whole apparatus.

**One thing we got right that deserves better evidence than it has**

20. **Independence (doctrine F6, ADR-010).** The doctrine grounds it in Fagan 1976
    and IEEE 1012. Knight & Leveson is the stronger citation, because it explains
    *why* — correlated failure through shared specification and shared cognitive
    bias — and predicts precisely which residual errors survive independent review.

---

## 18. What could not be verified

Listed so nobody fills these in from memory. Anything here that appears in our
prose must carry its label or be removed.

| Claim | Status |
|---|---|
| Dependency-directed backtracking as the direct ancestor of CDCL clause learning | **UNCERTAIN** — plausible, widely repeated, not checked |
| Soundiness Manifesto's Dagstuhl / workshop origin | **COULD NOT VERIFY** — absent from soundiness.org and the preprint |
| "Building Evolutionary Architectures" 2nd-edition author order | **UNCERTAIN** — publishers disagree; cite "Ford et al." |
| BEA's "Review Fitness Functions" section text, incl. the annual cadence | **ATTRIBUTED** — reproducing site plus three sets of reading notes; book not reached |
| Whether the BEA 2nd edition addresses the "wrong fitness function" question | **NOT ASSESSED** — 2nd-ed chapters unreachable |
| That no empirical study of fitness-function adoption exists | **"NOT FOUND under substantial search"** — DBLP search was down, Semantic Scholar rate-limited |
| Bohner & Arnold 1996 as an edited tutorial anthology | **COULD NOT VERIFY** — catalogues name them as authors; all ToC sources blocked |
| Weiser ICSE 1981 end page 449; CACM 1982 issue number 7 | **ATTRIBUTED** — from registries, not the page |
| "Slicing cut debug time to 58%" | **DO NOT USE** — no primary source; not in Weiser 1981 |
| Weiser TSE 1984 "44%" as *slice* size | **MIS-CITATION** — his own key says *cluster* size |
| "28.1% / 26.3%" backward/forward slice split | **DO NOT USE** — authors' own words are "just under 30%" |
| Harman et al. dependence clusters, final TOPLAS volume/pages | **UNCERTAIN** — author preprint only |
| Knight & Leveson 1986 full text | **ATTRIBUTED** — abstract verified via a faithful verbatim reproduction; design details second-hand |
| Parnas "Software Aging" content, incl. "lack of movement" / "ignorant surgery" | **ATTRIBUTED** — three fetch attempts 404'd |
| Parnas "Precise Documentation" content | **NOT OBTAINED** — record only |
| SCR industrial applications (C-130J, Darlington) and any line count | **ATTRIBUTED**; sources disagree on the line count — cite none |
| van Wyk's 1990 CACM assessment text; Knuth's 2008 InformIT interview | **ATTRIBUTED** — files carry their source URLs but could not be re-fetched live |
| Folklore that tangling breaks debuggers / woven docs merge badly | **NO PRIMARY SOURCE FOUND** — drop or label as folklore |
| "No large multi-developer codebase uses WEB" | **UNCERTAIN** — TeX Live still ships WEB/CWEB sources |
| Fit's 2002 creation date | **ATTRIBUTED** — c2.com's copyright line says 2002; no primary statement |
| That SLIM became FitNesse's configured *default* | **PROBABLY WRONG** — say "superseded in practice" |
| *Fit for Developing Software* page count | **CONFLICTING** — 355 vs 384 |
| Semmle founded 28 Dec 2006 by de Moor, Avgustinov & Tibble | **ATTRIBUTED** — Oxford confirms only "2006"/"December 2006" and de Moor |
| Semmle sale price ~$410M | **ATTRIBUTED to PitchBook** — Oxford says the real figure is confidential |
| Kythe as successor to Google's "Grok"; Kythe's schema being protobuf-based | **COULD NOT VERIFY** / **ATTRIBUTED** |
| tree-sitter created "at GitHub" | **ATTRIBUTED** — Brunsfeld's authorship is verified, the employment link is not |
| GitHub Code Security per-committer price | **UNCERTAIN** — no pricing page fetched |
| Why SCIP left Sourcegraph | **COULD NOT VERIFY** |
| Gärdenfors 1990, *Revue Internationale de Philosophie* 172:24–46 | **ATTRIBUTED** — sole source is Doyle's own bibliography; prefer the 1992 CUP reprint |
| Harper identity dating (1976 vs 1977) | **UNCERTAIN** |
| "Intersection" / "conjunction" as alternative names for the supplementary contraction postulates | **NOT FOUND** — do not use |
| Levi and Fuhrmann as Recovery critics | **UNSUPPORTED** by anything retrieved |
| Darwiche & Pearl's own wording | **ATTRIBUTED** — record verified, preprint fonts defeated extraction |
| de Kleer "Extending the ATMS" contents | **NOT OBTAINED** — no free copy exists |
| Which commercial expert-system shells embedded an ATMS | **COULD NOT VERIFY** — the reference numerals are OCR-garbled in the scan |
| Fickas & Feather RE'95 and van Lamsweerde & Letier obstacle analysis | **UNCERTAIN** — neither primary reached |
| Michael Jackson's *Problem Frames* year (2000 vs 2001) and whether the title includes "and Methods" | **UNCERTAIN** — catalogues disagree |
| "The World and the Machine" as a formal *keynote* | **UNCERTAIN** — venue/year/pages verified, keynote status not |
| Bavota & Russo (MSR 2016) SATD survival time | **NOT OBTAINED** — the one number that could not be reached at all |
| "Evaluating the small scope hypothesis" as a retrievable paper | **UNCERTAIN** — absent from DBLP and Crossref; the circulating author list is garbled |
| Woodcock et al.'s "62 industrial projects" figure | **UNVERIFIED** — do not state it |
| Any quantitative claim about bitemporal-adoption regret rates | **NO STUDY FOUND** |
| Any published study of TLA+ or Alloy adoption outside large companies | **NONE FOUND** — a literature gap, not evidence of absence |
| Any Eiffel market-share or user-count figure | **NOT OBTAINABLE** — only proxy signals |
| Published rebuttals of the Four Dark Corners framework | **NOT FOUND** — absence of evidence, not evidence of absence |
| Parnas & Clements citation count | **NOT OBTAINED** — Semantic Scholar 429, ACM DL 403 |

**Environment notes for anyone continuing this.** ACM DL, IEEE Xplore,
ScienceDirect, Springer, Wiley, O'Reilly, JSTOR, PhilPapers, MIT Press,
ResearchGate and Academia.edu all returned 403 or 418. `dblp.org` refuses
connections but `dblp.uni-trier.de` serves identical data. Snodgrass's Arizona
page hosts a free full-text book and the 1986 *IEEE Computer* paper behind an
expired TLS certificate. soundiness.org must be fetched over plain HTTP. Crossref,
OpenAlex, OpenLibrary, HathiTrust, the AAAI and IJCAI proceedings CDNs, MIT
DSpace, arXiv, W3C, PyPI and the GitHub REST API were all reliable.

---

## 19. Sources requiring purchase

Nothing in this document was obtained from a pirate source. The following could
not be reached legitimately, and each line states what we would actually gain.

| Item | Where | What we gain |
|---|---|---|
| **de Kleer, "Extending the ATMS," *AI* 28(2):163–196, 1986** — Elsevier, DOI `10.1016/0004-3702(86)90081-0` | ScienceDirect, single-article purchase | The only trilogy member with no free copy. First-hand account of the general-clause extension and its cost. **Only worth buying if we ever seriously reconsider §4.6.** Low priority — the refusal is already settled on better grounds. |
| **de Kleer, "A Perspective on Assumption-Based Truth Maintenance," *AI* 59(1–2):63–67, 1993** — DOI `10.1016/0004-3702(93)90171-7` | Elsevier | Five pages; his own seven-years-on retrospective, likely his frankest cost assessment. Cheap. Same low priority. |
| **Ford, Parsons, Kua & Sadalage, *Building Evolutionary Architectures*, 2nd ed. (2022)** — O'Reilly, ISBN 978-1-492-09754-9 | O'Reilly / booksellers | **The one genuinely worth buying.** The 1st edition demonstrably has no answer to "what if a fitness function is wrong"; the 2nd edition's own marketing says it deepens exactly the "Fitness Functions" and "Impact" material. If it *does* address retirement, false positives, or meta-validation, that changes §8 and our L2 plan. If it does not, that negative result is worth having on record. |
| **Michael Jackson, *Problem Frames*, Addison-Wesley, ISBN 0-201-59627-X** | Secondhand | Would settle the 2000-vs-2001 date and the frame-concern definitions first-hand. **Not needed for §16 Q2** — the 2005 IST paper is free and carries the framework. Buy only for completeness. |
| **Forbus & de Kleer, *Building Problem Solvers*, MIT Press, 1993, ISBN 978-0-262-06157-5** | MIT Press / secondhand | The canonical side-by-side JTMS-vs-ATMS treatment with working code. The Lisp source is free (archived); the text is not. Superseded for our purposes by de Kleer's own papers. Skip. |
| **Gärdenfors (ed.), *Belief Revision*, CUP 1992, ISBN 9780521545648** | Cambridge Core | Doyle's chapter — the one we actually needed — **is free from his MIT page**. Buy only for Gärdenfors's introduction. Skip. |
| **Hansson, "Belief contraction without recovery," *Studia Logica* 50(2):251–260, 1991** — DOI `10.1007/BF00370186` | Springer | The Recovery critique first-hand. Decorative for us. Skip. |
| **Provan, "The Computational Complexity of Multiple-Context TMSs," ECAI-90** | Out of print; library only | Formal worst-case bounds on ATMS labels. Not needed — de Kleer's own admissions are stronger evidence and are free. Skip. |

**Recommendation: buy one.** The 2nd edition of *Building Evolutionary
Architectures*, because §8's central finding is a *negative* one about the
literature, and a negative finding is only as good as the edition it was checked
against.








