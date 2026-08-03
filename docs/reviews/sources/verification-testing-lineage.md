# The verification and testing lineage — sources behind the doctrine (2026-08-03)

> Reader: anyone about to build, defend or dispute the verification machinery
> described in `../agentic-verification-doctrine-2026-08-03.md` and
> `../verification-system-scratch-design-2026-08-03.md` | Enables: reading the
> primary sources those documents cite, seeing what their authors actually
> argued and what happened to each proposal, and finding the four places where
> the literature contradicts our reading | Update-trigger: a source in the
> "still unread" list is obtained, a citation label changes, or the doctrine
> adds a claim that rests on a source not catalogued here

**What this is.** The doctrine document maps our failure modes onto named
prior art. It cites; it does not explain. This document supplies the
substance: for each source, the problem its author faced, the evidence they
had, the reasoning, the proposal, what became of it, and what it means for us.

**Citation labels.** Every source carries one:

- **VERIFIED** — I retrieved the source itself, or an authoritative registry
  record (Crossref, dblp), and confirmed title, authors, venue, year. Where I
  read the full text I say so; where I confirmed only metadata I say that too.
- **ATTRIBUTED** — consistently attributed across independent sources, no
  primary reached.
- **UNCERTAIN** — a lead to check, not a fact.

**Quotation rule.** Every passage in quotation marks below was retrieved from
a document I actually read. Nothing is quoted from memory. Where I could not
read a source, I paraphrase and say so, and no page number, DOI or ISBN
appears that I did not see in a record or on the page.

---

## 1. Dijkstra, 1969 — the sentence everyone truncates

**Source.** E. W. Dijkstra, "Notes on Structured Programming" (EWD 249),
August 1969; second edition April 1970. **VERIFIED** — full transcription read
at the E.W. Dijkstra Archive, University of Texas at Austin
(`cs.utexas.edu/~EWD/transcriptions/EWD02xx/EWD249/EWD249.html`).

**Source, published form.** J. N. Buxton and B. Randell (eds.), *Software
Engineering Techniques: Report on a conference sponsored by the NATO Science
Committee, Rome, Italy, 27th to 31st October 1969*, NATO Science Committee,
April 1970. **VERIFIED** — full report read (Randell's scanned-and-OCR'd
edition, via the Internet Archive).

**The problem.** Dijkstra was trying to answer whether programming ability
could be raised by an order of magnitude, and had concluded that the binding
constraint was confidence in correctness. His own framing in the NATO report
is a reliability-of-composition argument: if a program is composed of N
components each correct with probability p, the whole is correct with
probability no better than p^N, so for large N, p must be "practically equal
to one".

**The evidence.** A counting argument, not data. In EWD 249 he takes a 27-bit
multiplier: exhaustive testing means 2^54 multiplications, and "although a
single multiplication took only some tens of microseconds, the total time
needed for this finite set of multiplications would add up to more than
10 000 years!"

**The reasoning.** Sampling cannot establish a universally quantified claim
over an astronomically large input space. Therefore confidence must come from
the program text, not from its behaviour on samples.

**What he actually wrote, in full.** From §7.4 "Structured Programming" of the
NATO 1969 report (on original page 85 of the printed edition, per the page
markers in Randell's scan):

> "The number of different inputs, i.e. the number of different computations
> for which the assertions claim to hold is so fantastically high that
> demonstration of correctness by sampling is completely out of the question.
> Program testing can be used to show the presence of bugs, but never to show
> their absence! Therefore, proof of program correctness should depend only
> upon the program text."

And immediately after — this is the part that is always cut:

> "Therefore, I have not focused my attention on the question 'how do we prove
> the correctness of a given program?' but on the questions 'for what program
> structures can we give correctness proofs without undue labour, even if the
> programs get large?' and, as a sequel, 'how do we make, for a given task,
> such a well-structured program?'."

The famous short form is a *different* utterance: it is a one-line floor remark
in §3.1 "Correctness" of the same report, verbatim
"**Dijkstra: Testing shows the presence, not the absence of bugs.**" It was a
reply to Alan Perlis, who had just said that "a number of test cases properly
studied will exhaust the testing problem". Both forms are in the same
document, and that is why both circulate.

Two further remarks in that discussion are worth having, because they are
better than the slogan. Hoare, immediately above Dijkstra:

> "The role of testing, in theory, is to establish the base propositions of an
> inductive proof."

And Lucas of the IBM Vienna Laboratory, immediately below, on a proof that
found a PL/I compiler defect:

> "The error was not found by the compiler writers; it was not found by product
> test and it would not easily have been found by any random tests."

**What happened to it.** The argument won structurally and lost economically.
Structured programming, invariants and assertions became universal; whole-program
proof did not. The slogan detached from the argument and became a rhetorical
flourish used to dismiss testing — a use Dijkstra's own sentence does not
support, since his point was *design for cheap proof*, not *stop testing*.

**Relevance to us.** Confirms what we already concluded, and sharpens it. The
truth ledger's evidence commands are sampling instruments; Dijkstra's argument
says a passing sample is worth nothing unless the sample could have failed. But
his positive proposal — restructure the thing so that checking it is cheap — is
exactly the scratch design's move from stored claims to computed invariants.
The doctrine cites Popper for falsifiability; Dijkstra is the closer and more
domain-specific ancestor, and he is already in our own corpus's reach.

---

## 2. DeMillo, Lipton & Sayward, 1978 — mutation testing

**Source.** R. A. DeMillo, R. J. Lipton, F. G. Sayward, "Hints on Test Data
Selection: Help for the Practicing Programmer", *Computer* (IEEE), vol. 11,
no. 4, April 1978, pp. 34–41. **VERIFIED** — full text read (PDF, retrieved
from a university course mirror; page numbers, the IEEE copyright line
`0018-9162/78/0400-0034$00.75 © 1978 IEEE` and the April 1978 running heads
are on the pages).

**The problem.** Not correctness in the abstract — *budget*. Their opening is
an economics argument: "It is an economic and political requirement in most
production programming shops that programmers shall spend as little time as
possible in testing." They set out to give practitioners something that works
inside that constraint.

**The evidence they had.** Three kinds, and it is worth being precise, because
this paper is usually described as pure conjecture:

1. **Diminishing returns data.** Their Figure 1 comes from A. E. Tucker,
   "The Correlation of Computer Program Quality with Testing Effort", System
   Development Corporation TM 2219/000/00, January 1965: in the first half of
   the test cycle 1.54 % of errors are found per unit of effort; in the second
   half, 0.4 %.
2. **A fault-frequency distribution.** E. A. Youngs, *Error-Proneness in
   Programming*, PhD thesis, University of North Carolina, 1971 — 1258 errors
   in Fortran, Cobol, PL/I and Basic programs, tabulated by type. Assignment
   or computation errors 0.27, allocation 0.15, unknown/multiple 0.11,
   unsuccessful iteration 0.09, and so on down. The distribution is dominated
   by *small* errors.
3. **Worked experiments.** A Fortran `MAX` subroutine, a triangle-classifier
   taken from Ramamoorthy et al., Hoare's `FIND`, and tables comparing live
   mutant counts under randomly generated test vectors drawn from different
   ranges.

**The two load-bearing assumptions.**

*The "competent programmer" premise.* Note carefully: **the 1978 paper does
not contain the phrase "competent programmer hypothesis".** It states the idea
informally, and twice, as a pull-quote: "Programmers have one great advantage
that is almost never exploited: they create programs that are close to being
correct!" and, in the body, "Programmers do not create programs at random;
competent programmers, in their many iterations through the design process,
are constantly whittling away the distance between what their programs look
like now and what they are intended to look like." The named hypothesis is a
later formalisation. Anyone citing "DeMillo et al. 1978" for a formal statement
of the competent programmer hypothesis is citing the wrong page.

*The coupling effect*, which **is** stated formally and set off in the text:

> "The coupling effect: Test data that distinguishes all programs differing
> from a correct one by only simple errors is so sensitive that it also
> implicitly distinguishes more complex errors."

And, three sentences later, the honesty that makes the paper good:

> "There is, of course, no hope of 'proving' the coupling effect; it is an
> empirical principle."

**The proposal.** Program mutation. Generate variants P1…Pk of program P
differing by a single simple error (their example: `B.LE.C` becomes `B.EQ.C`).
Run the test data. A mutant on which P and Pi differ is **dead**. A mutant that
survives is **live**, for one of exactly two reasons: the test data is not
sensitive enough, or Pi is genuinely equivalent to P and no data can
distinguish them. Test data that leaves only equivalent live mutants is
*adequate*. They describe an interactive Fortran system built at Yale and
Georgia Tech, and — a point our doctrine should steal — they frame the output
socially: a surviving mutant is "a 'hard question' concerning his program
(e.g. 'The test data you've given me says it doesn't matter whether or not this
test is for equality or inequality; why is that?')".

They are explicit that this is *not* path coverage. Their `MAX` example shows
data that exercises every path while failing to distinguish `.GT.` from `.GE.`,
and their triangle example shows a test suite covering all paths of a program
whose compound Boolean conditions are never actually tested.

**Hamlet's independent work.** R. G. Hamlet, "Testing Programs with the Aid of
a Compiler", *IEEE Transactions on Software Engineering*, vol. SE-3, no. 4,
July 1977, pp. 279–290, DOI 10.1109/tse.1977.231145. **VERIFIED
bibliographically (Crossref registry record); content NOT read** — it is behind
IEEE paywall and no open copy was reachable. That it is an independent
contemporaneous formulation of the same idea is **ATTRIBUTED**: it is
universally cited that way in the mutation-testing literature, and Marick's
1991 paper cites `[Hamlet77]` alongside `[Howden82]` as the origin of *weak*
mutation specifically. I did not confirm it from the paper itself. See
"Sources still unread" below.

**What happened to it.** This is the interesting part, and it is a 40-year arc.

- **1992 — the coupling effect gets tested.** A. J. Offutt, "Investigations of
  the software testing coupling effect", *ACM Transactions on Software
  Engineering and Methodology*, vol. 1, no. 1, 1992, pp. 5–20, DOI
  10.1145/125489.125473. **VERIFIED bibliographically (Crossref); not read.**
- **2014 — the coupling effect gets measured against real faults.** René Just,
  Darioush Jalali, Laura Inozemtseva, Michael D. Ernst, Reid Holmes, Gordon
  Fraser, "Are mutants a valid substitute for real faults in software testing?",
  *FSE 2014*, pp. 654–665, DOI 10.1145/2635868.2635929. **VERIFIED — full text
  read.** 357 developer-fixed, manually-verified real faults across 5
  open-source Java programs (321,000 LOC), 230,000 mutants. Findings, in their
  words: "The results show the existence of a coupling effect for 73% of real
  faults"; "10% of real faults require a new or stronger mutation operator";
  "17% of real faults are not coupled to mutants". And mutant detection
  correlates with real-fault detection more strongly than statement coverage
  does, independently of coverage. So: DeMillo's 1978 conjecture is *mostly*
  true, with a measured 17 % residual that no mutation operator reaches.
- **2018–2022 — it ships, but only after being throttled.** Goran Petrović,
  Marko Ivanković, Gordon Fraser, René Just, "Practical Mutation Testing at
  Scale: A view from Google", *IEEE Transactions on Software Engineering*,
  vol. 48, no. 10, 2022, pp. 3900–3912, DOI 10.1109/tse.2021.3107634.
  **VERIFIED — full text read.** (Earlier: Petrović & Ivanković, "State of
  mutation testing at Google", *ICSE-SEIP 2018*, pp. 163–171, DOI
  10.1145/3183519.3183521 — **VERIFIED bibliographically; not read**.)

  The Google numbers are the most useful thing in this whole document for us:

  - Scale: "Google has a codebase of two billion lines of code and more than
    150,000,000 tests are executed on a daily basis."
  - The motivation is precisely our F2/F4: "code coverage alone is
    insufficient and may give a false sense of efficacy, in particular if
    program statements are covered but their expected outcome is not asserted
    upon".
  - **The killer number: "developers at Google initially classified 85% of
    reported mutants as unproductive."** An unproductive mutant is trivially
    equivalent, or detectable but not worth a test.
  - The fix is suppression, not more mutants. They label "arid nodes" in the
    AST — sites whose mutation yields unproductive mutants — *before*
    generating anything, and report at most one mutant per changed, covered
    line. Median mutants per changelist: **820 traditional → 77 one-per-line →
    7 with arid-node suppression.** Two orders of magnitude.
  - Over six years, productive-mutant ratio went "from 15% to 80%" and then to
    89 %.
  - Their explicit design principle, which is our §4.11 restated by someone
    with 24,000 developers: "preventing non-actionable findings is more
    important than reporting all actionable findings."

**Relevance to us.** Confirms the doctrine's ranking of `truth mutate` as the
highest-value item, and **contradicts its cost estimate**. The doctrine
describes mutation of evidence recipes as a matter of "perturb a watched path,
re-run the recipe, assert the output changes". Google's experience says the
mechanism is the easy 15 %; the work is the suppression rules that stop it
producing 85 % noise, and that took six years of feedback to build. For a
one-person shop the implication is stark: a `truth mutate` sweep that reports
everything will be switched off within a week. It must report *one* finding
per claim and must have a suppression list from day one.

---

## 3. Weyuker, 1982 — the oracle problem

**Source.** Elaine J. Weyuker, "On Testing Non-testable Programs", *The
Computer Journal*, vol. 25, no. 4, November 1982, pp. 465–470 (Wiley Heyden
Ltd; received November 1981). **VERIFIED — full text read** (page scan from a
University of Washington course page; page numbers, journal running heads and
copyright line visible).

**The problem.** Almost the entire testing literature assumes an oracle. She
names the assumption and attacks it.

> "The mechanism which checks this correctness is known as an *oracle*, and the
> belief that the tester is routinely able to determine whether or not the test
> output is correct is the *oracle assumption*."

**What counts as non-testable.** Her definition has two limbs, and the second
is the practical one:

> "if either of the following two conditions occur, a program should be
> considered *non-testable*: (1) there does not exist an oracle; (2) it is
> theoretically possible, but practically too difficult to determine the
> correct output."

She then names three classes of non-testable program:

1. **Programs written to determine the answer** — "If the correct answer were
   known, there would have been no need to write the program."
2. **Programs producing so much output that verifying it is impractical.**
3. **Programs for which the tester has a misconception** — the vicious case.
   "the tester believes that there is an oracle, i.e. he believes he knows or
   can ascertain the correct answers." She notes the consequence directly:
   the tester will "believe that the program contains an error and will
   therefore attempt to debug it", or worse, will "modify the correct program
   in order to 'fix' it and thereby makes it incorrect."

Her evidence is anecdotal but well chosen: a company comptroller reporting
that a long-running assets program had "suddenly gone crazy" because it stated
total assets of $300 — a case of detecting an incorrect result without knowing
the correct one. She generalises this to the *partial oracle*: knowing a result
is wrong without knowing what is right.

**What she proposed.** Four things, in descending order of rigour:

- **Pseudo-oracles / dual coding.** "an independently written program intended
  to fulfill the same specification as the original program." Two programs,
  same inputs, compare. She is candid about cost — "At least two programs must
  be written" — and about the failure mode: it works only if the two teams do
  not share a misconception.
- **Simplified data.** Run on inputs whose answers are known, extrapolate. She
  immediately warns why this is weak: "Experience tells us that it is
  frequently the 'complicated' cases that are most error-prone. It is common
  for central cases to work perfectly whereas boundary cases cause errors."
- **Plausibility, narrowed.** Her sin(42°) worked example: known values at 30°
  and 45°, monotonicity, and convexity give a straight-line lower bound, so
  0.6657 < sin 42° < 0.7071 without knowing the answer.
- **Theory-derived invariants.** "The theory might tell us that some
  conservation laws should remain invariant, or that certain properties should
  hold... These should be checked repeatedly throughout the computation."

**The sentence our whole project should have on the wall.** Immediately after
proposing invariants, she supplies the trap:

> "We know when calculating values of the sine and cosine, for example, that
> sin²(x) + cos²(x) = 1. Care should be taken to see that this check is really
> being performed at each stage. If the cosine is calculated by finding the
> square root of (1 − sin²(x)), checking for this invariant cannot be expected
> to be revealing."

That is a 1982 statement of *evidence that cannot fail*, in the exact form we
hit on 2026-08-02: a check derived from the thing it is supposed to check.

**Her conclusion.** She proposes five items as "an absolute minimal standard
part of documentation": the criteria used to select test data; the degree to
which they were fulfilled; the test data; the output for each datum; and —
item (5) — "How the test results were determined to be correct or acceptable."
She also anticipates the coverage critique by four years:

> "We are able to make statements such as 'all but three of the branches of the
> program have been traversed'... Implicit in such statements is the assumption
> that the branches have been traversed *and yielded the correct results*. But
> as we have argued, this cannot in general be determined."

**What happened to it.** The paper defined a research area that is still open.
"Non-testable" became the standard term; the oracle problem is now a named
subfield with its own surveys. Pseudo-oracles survive as *differential testing*
(and, in a mutated form, as N-version programming, which she carefully
distinguishes from her proposal). Her invariant-checking suggestion is the
direct ancestor of metamorphic testing (§4) and of property-based testing (§5),
both of which cite her.

**Relevance to us.** Contradicts nothing, but reframes the scratch design. Her
item (5) — record *how* you decided the output was right — is precisely what a
truth-ledger record is for, and it is the part the scratch design proposes to
delete for computable facts. That deletion is probably still correct (a
predicate *is* the answer to item 5), but the sin²+cos² warning says the
predicate must be shown to be independent of what it checks, which is exactly
why the scratch design makes `mutation:` a required field. Weyuker gives that
field a 44-year pedigree.

---

## 4. Chen, Cheung & Yiu, 1998 — metamorphic testing

**Source.** T. Y. Chen, S. C. Cheung, S. M. Yiu, "Metamorphic Testing: A New
Approach for Generating Next Test Cases", Technical Report HKUST-CS98-01,
Department of Computer Science, The Hong Kong University of Science and
Technology, 1998. **VERIFIED — full text read** (the report is hosted on
S. C. Cheung's own HKUST faculty page; the header line
"Published as Technical Report HKUST-CS98-01" is on page 1).

**The problem.** Three observations, in their words: successful (non-failing)
test cases are discarded unexamined; errors survive into production where
outputs are never verified; and, citing Weyuker directly, "the availability of
test oracles is pragmatically unattainable in most situations."

**The evidence.** None empirical. This is a proposal paper with worked
examples — binary search, k-th occurrence in an unsorted array, shortest path
in an undirected graph, Gaussian elimination — each with a seeded defect and a
derived follow-up test that catches it.

**The reasoning.** If you cannot check *one* output, check a *relationship
between several*. From a successful input-output pair (x₀, P(x₀)), construct
x₁…x_k whose outputs must stand in a known relation to P(x₀). You never need to
know the right answer; you only need to know a property that must hold across
runs.

**Concretely, what a metamorphic relation looks like.** Their shortest-path
example is the clearest:

> "Given a weighted graph G, a source node x, and the destination node y... the
> problem is to output the shortest path and the shortest distance from x to y.
> ... This output is difficult to check even in the testing phase if the input
> graph G is non-trivial... In this case, a practically feasible test oracle
> does not exist."

The relation: run it again as `⟨y, x, G⟩`. For an undirected graph, the
distance must be the same p. They note the constraint explicitly — "These test
cases are not applicable if G is a directed graph" — which is a declared blind
spot, in 1998, in a footnote.

Their binary-search example yields a small family of relations: if the search
returned position k with A[k] = x, then re-searching for A[k−1] must return
k−1; searching for any y strictly between A[k−1] and A[k+1] with y ≠ x must
return −1; searching for a randomly chosen A[p] must return p. Each targets a
specific suspected fault class (overwriting, splitting error, false
non-existence). They demonstrate this catching a real off-by-one in a recursive
binary search (`BinSearch(x,A,mid+2,j)` where `mid+1` was correct).

They are also careful about cost, borrowing Blum's constraint on program
checkers: "The time for the construction of each new test case and the checking
on the corresponding output are assumed to be strictly less than the execution
time of the program."

**Terminology caution.** The 1998 report **never uses the phrase "metamorphic
relation"**. It calls the technique metamorphic testing and constructs
relations ad hoc. The term is a later crystallisation. Their own conclusion
admits the gap: "a methodology supporting such an approach has yet been fully
developed."

**The later canonical definition** — T. Y. Chen, Fei-Ching Kuo, Huai Liu,
Pak-Lok Poon, Dave Towey, T. H. Tse, Zhi Quan Zhou, "Metamorphic Testing: A
Review of Challenges and Opportunities", *ACM Computing Surveys*, vol. 51,
no. 1, 2018, article 4. **VERIFIED bibliographically (dblp) and abstract read**
(via the Semantic Scholar record):

> "Metamorphic testing is an approach to both test case generation and test
> result verification. A central element is a set of metamorphic relations,
> which are necessary properties of the target function or algorithm in
> relation to multiple inputs and their expected outputs."

**What happened to it.** It worked, and it is now the standard answer to the
oracle problem in domains where there is no oracle:

- **Compilers.** Vu Le, Mehrdad Afshari, Zhendong Su, "Compiler Validation via
  Equivalence Modulo Inputs", *PLDI 2014*, pp. 216–226, DOI
  10.1145/2594291.2594334. **VERIFIED — abstract and body read.** The
  metamorphic relation is: a program and a variant with unexecuted code
  stochastically pruned must compile to code that behaves identically on the
  profiling inputs. Their result: "Our extensive testing in eleven months has
  led to 147 confirmed, unique bug reports for GCC and LLVM alone. The majority
  of those bugs are miscompilations, and more than 100 have already been
  fixed."
- **Autonomous vehicles.** Zhi Quan Zhou, Liqun Sun, "Metamorphic testing of
  driverless cars", *Communications of the ACM*, vol. 62, no. 3, 2019,
  pp. 61–67, DOI 10.1145/3241979. **VERIFIED bibliographically (Crossref) and
  abstract read; full text NOT read** — CACM blocked retrieval. The abstract:
  "Metamorphic testing can test untestable software, detecting fatal errors in
  autonomous vehicles' onboard computer systems." I am not going to characterise
  which systems or which defects, because I did not read the paper.

**Relevance to us.** This is a genuine gap in the doctrine, and it is
actionable. Several of our claims are non-testable in Weyuker's sense — a
cutting-list output, a nesting layout, a drilling pattern — where nobody can
say "this is the right answer" but everybody can say "these two runs must
agree". Metamorphic relations are the cheap form of that: reorder the input
panels and the total board consumption must not change; mirror a cabinet and
the drilling pattern must mirror; re-run the same project and the BOM must be
byte-identical. That last one we already do (the exercise gate). We have been
using metamorphic testing without naming it, and naming it would let us
generate more relations deliberately instead of by accident.

---

## 5. Claessen & Hughes, 2000 — property-based testing

**Source.** Koen Claessen, John Hughes, "QuickCheck: a lightweight tool for
random testing of Haskell programs", *ICFP '00* (Proceedings of the Fifth ACM
SIGPLAN International Conference on Functional Programming), Montreal,
pp. 268–279, DOI 10.1145/351240.351266. **VERIFIED — full text read** (PDF from
a university course mirror; ACM copyright block for ICFP '00 on page 1).

**The problem.** Cost. "Testing is by far the most commonly used approach to
ensuring software quality. It is also very labour intensive, accounting for up
to 50% of the cost of software development."

**The proposal.** Properties written as Haskell functions, checked on
automatically generated random input; type-directed default generators;
combinators for custom generators; conditional properties; and — the part most
tools drop — *monitors* that report the distribution of the test data actually
generated.

**How it differs from mutation and metamorphic testing.** Precisely stated,
because they state it themselves in §6.2, "Correctness Criteria":

> "The problem of determining whether a test is passed or not is known as the
> oracle problem."

- **Mutation testing** judges a *test suite* by seeding faults in the program.
  The artefact under evaluation is the tests.
- **Metamorphic testing** judges an *output* by relating it to other outputs of
  the same program. No oracle needed, no property of a single run asserted.
- **Property-based testing** asserts a universally quantified property of a
  single run (or of a generated sequence of calls), and attacks the *input*
  side by generating many. QuickCheck properties subsume result checkers — they
  say so — but go further: "the property that an operator is associative, for
  example, cannot really be said to check the result of any individual use of
  the operator, but still expresses a useful 'global' property".

**What it assumes.** Two things, both admitted in the paper.

First, **that fine-grained pure functions exist to state properties about.**
"When a function is built from separately tested components, then random
testing suffices to obtain good coverage of the definition under test." They
explicitly decline to adopt any adequacy criterion, citing Duran & Ntafos
("An Evaluation of Random Testing", *IEEE TSE*, SE-10(4), 1984, pp. 438–444 —
**VERIFIED bibliographically via Crossref; not read**) and Hamlet's survey,
quoting: "By taking 20% more points in a random test, any advantage a partition
test might have had is wiped out."

Second, **that the generator's distribution is watched by a human.** This is
the honest limitation and the paper leads with it:

> "The major limitation of QuickCheck is that there is no measurement of test
> coverage: it is up to the user to investigate the distribution of test data
> and decide whether sufficiently many tests have been run... A programmer who
> does not risks gaining a false sense of security from a large number of
> inadequate tests."

Their §5.1.4 is literally titled "A False Sense of Security" and reports it
happening to them, in the unification case study:

> "we found that over 95% of test cases had this property. Although QuickCheck
> succeeded in 'verifying' every property, we can hardly consider that they were
> thoroughly tested."

**The finding that matters most to us.** From §6.6, "Some Reflections":

> "We have observed that the errors we find are divided roughly evenly between
> errors in test data generators, errors in the specification, and errors in
> the program."

Two thirds of what a verification apparatus catches are defects *in the
apparatus*, not in the system under test.

**What happened to it.** It escaped its language and became industrial.
John Hughes, "Experiences with QuickCheck: Testing the Hard Stuff and Staying
Sane", *Lecture Notes in Computer Science*, Springer, 2016, pp. 169–186, DOI
10.1007/978-3-319-30936-1_9. **VERIFIED — full text read.** Quviq founded 2006;
the largest project was AUTOSAR acceptance testing for Volvo Cars:

> "For this project we read around 3,000 pages of PDFs (the standards
> documents). We formalized the specification in 20,000 lines of QuickCheck
> code. We used it to test a million lines of C code in total, from 6 different
> suppliers, finding more than 200 problems—of which well over 100 were
> ambiguities or inconsistencies in the standard itself!"

Note that number again: over half the defects found were in the *specification*,
not the code. It corroborates the 2000 paper's one-third estimate and pushes it
higher. The paper also documents the stateful extension — a model with
`_pre`, `_next` and `_post` functions per API call — which is Design by Contract
(§8) relocated from the implementation into the test harness.

**Relevance to us.** Contradicts our reading in one specific and uncomfortable
way. The doctrine treats the ledger's 2,100 records and 35 % claim mortality as
a maintenance-cost problem on the FIT curve. Claessen & Hughes and Hughes 2016
suggest a different diagnosis: a large fraction of what a verification
apparatus produces is *supposed* to be defects in the apparatus and the
specification, and that is the apparatus working, not failing. The question is
not "why do so many claims die" but "when a claim dies, was the fault in the
code, in the claim's wording, or in the evidence recipe?" We do not currently
record which. If we did, and the split were roughly even, that would be
Claessen & Hughes' number and evidence of health.

---

## 6. Coverage criteria and their limits

### 6.1 Marick — coverage as clue, not command

**Source.** Brian Marick, "How to Misuse Code Coverage", Testing Foundations.
Copyright line: "Copyright © 1997 Brian Marick, 1999 Reliable Software
Technologies"; Version 1.1; PDF produced March 2000. Presented at Testing
Computer Software '99. **VERIFIED — full text read** (13 pages including
references, via the Internet Archive capture of
`exampler.com/testing-com/writings/coverage.pdf`).

> **Note for future readers.** The copy currently served from exampler.com is
> **truncated at 6 pages**, cutting off mid-sentence in the numbered
> recommendation procedure. The 2018 Wayback capture is complete. If you fetch
> this paper and it ends at "…usually means a small amount of code, not
> something", you have the broken copy.

**Credibility.** He built the tools. From his own tools page: "As someone who's
written four coverage tools, I rather like them. However, they're often
misused." GCT (Generic Coverage Tool) was his third.

**The evidence.** Not opinion — a measured study eight years earlier: Brian
Marick, "Experience with the Cost of Different Coverage Goals for Testing",
*Pacific Northwest Software Quality Conference*, 1991. **VERIFIED — read by a
research subagent.** Seven units tested with extended black-box technique;
black-box design alone consumed ~53 % of total effort and already delivered
~95 % branch coverage; pushing to 100 % feasible branch/loop/multi-condition
coverage cost a few percent more. Weak mutation was the expensive one, and most
of that cost went to *proving conditions infeasible*, not writing tests. Its
conclusion contains the seed of the 1999 argument: "A low initial coverage
signals a problem in the testing process."

**The argument.** The pivot is a worked example where `perform_operation`
returns three status codes and the code handles two. A test written to satisfy
the coverage tool passes; the bug survives.

> "the coverage tool didn't tell me to write the needed tests. It can't. It can
> only tell me how the code that exists has been exercised. It can't tell me
> how code that **ought** to exist **would have been** exercised."

> "This is a fundamental problem for all code coverage tools... They all have
> to work on the code they're given."

**The proposal**, and it is not abolition:

> "It would be a mistake to abandon coverage tools."

> "My approach is based on this key observation: If a part of your test suite
> is weak in a way that coverage can detect, it's likely also weak in a way
> coverage can't detect."

The procedure: for each missed condition, identify the *feature* it corresponds
to; redesign the test for that feature while deliberately not thinking about
the condition; re-run and expect the condition to close as a side effect. If it
does not, you erred again in test design.

> "coverage tools don't give commands ('make that evaluate true'), they give
> clues ('you made some mistakes somewhere around there'). If you treat their
> clues as commands, you'll end up in the fable of the Sorcerer's Apprentice."

**On targets.** His section "Managers make mistakes, too" is the best empirical
statement of Goodhart's law in software testing I have read, and it is
observational, not theoretical:

> "when I talk about coverage to organizations that use 85%, say, as a shipping
> gate, I sometimes ask how many people have gotten substantially higher,
> perhaps 90%. There's usually a few who have, but everyone else is clustered
> right around 85%."

> "Coverage numbers (like many numbers) are dangerous because they're objective
> but incomplete."

And on where 85 % came from, in a footnote: one company adopted it because
another respectable company used it, and — "I have the horrible feeling that,
if I traced it all the way back to the Dawn of Time, I'd find someone who
pulled 85% out of a hat."

He also warns about the *other* failure: "inflated hopes get attached to
coverage… But a year passes and the coverage tool does not bring Utopia.
Therefore, it must be useless. And the testing organization lurches wildly in
yet another direction."

**What happened to it.** Absorbed into the context-driven testing curriculum
(it is a required reading in the BBST Foundations course) rather than into
tooling. Marick went on to co-author the Agile Manifesto and, with Bach and
Kaner, "A Manager's Guide to Evaluating Test Suites" (Quality Week 2000),
arguing that objective test-suite metrics are not sufficient at all. The 85 %
gate, meanwhile, is still everywhere.

### 6.2 The hierarchy, and why DO-178B mandates MC/DC

**Primary tutorial source.** Kelly J. Hayhurst (NASA Langley), Dan S. Veerhusen
(Rockwell Collins), John J. Chilenski (Boeing), Leanna K. Rierson (FAA), "A
Practical Tutorial on Modified Condition/Decision Coverage",
NASA/TM-2001-210876, NASA Langley Research Center, May 2001, 85 pp.
**VERIFIED — full text read by a research subagent** (hosted openly at
`shemesh.larc.nasa.gov`). Note the author list: the criterion's co-inventor,
an avionics supplier, an airframer and the regulator, in one document.

**The hierarchy**, in the tutorial's ordering: "The structural coverage
measures in Table 1 range in order from the weakest, statement coverage, to the
strongest, multiple condition coverage" — statement, decision, condition,
condition/decision, MC/DC, multiple condition.

The two traps, quoted from the tutorial:

- Statement coverage is nearly worthless: citing Myers, "statement-coverage
  criterion is so weak that it is generally considered useless."
- **Condition coverage does not subsume decision coverage.** "for the decision
  (A or B) test cases (TF) and (FT) meet the coverage criterion, but do not
  cause the decision to take on all possible outcomes."
- Condition/decision coverage still cannot tell `(A or B)` from `A`: "these two
  tests do not distinguish the correct expression (A or B) from the expression
  A or from the expression B or from the expression (A and B)."

**MC/DC's definition**, quoted in the tutorial from the DO-178B glossary:
every entry and exit point invoked; every condition has taken all outcomes;
every decision has taken all outcomes; "and each condition in a decision has
been shown to independently affect that decision's outcome. A condition is
shown to independently affect a decision's outcome by varying just that
condition while holding fixed all other possible conditions."

**Origin.** John Joseph Chilenski, Steven P. Miller, "Applicability of modified
condition/decision coverage to software testing", *Software Engineering
Journal*, vol. 9, no. 5, 1994, pp. 193–200, DOI 10.1049/sej.1994.0025.
**VERIFIED bibliographically (Crossref registry: SEJ vol 9, issue 5, 1994,
start page 193); full text NOT read** — IET paywalled. Note: the NASA tutorial's
own reference list cites this as "Vol. 7"; Crossref and dblp both say volume 9,
and volume 9 is right on chronology. The tutorial quotes Chilenski & Miller
directly on their motive:

> "The modified condition/decision coverage criterion was developed to achieve
> many of the benefits of multiple-condition testing while retaining the linear
> growth in required test cases of condition/decision testing."

**Why DO-178B mandates it specifically.** RTCA/DO-178B, "Software
Considerations in Airborne Systems and Equipment Certification", RTCA Inc.,
December 1992 (EUROCAE ED-12B in Europe). The tutorial states the placement:
objective 7 (statement coverage) applies to levels A–C, objective 6 (decision
coverage) to levels A–B, objective 5 (MC/DC) to **level A only**.

The cost argument is arithmetic: MC/DC needs "a minimum of n+1 test cases for a
decision with n inputs" where multiple-condition coverage needs 2^n. The
tutorial makes it empirical with Chilenski's survey of all logic expressions in
the airborne Ada software of five line-replaceable units from two aircraft
models (1995). Distribution by condition count n: n=1 → 16,491 expressions;
n=2 → 2,262; n=3 → 685; n=4 → 391; n=5 → 131; n=6–10 → 219; n=11–15 → 35;
n=16–20 → 36; n=21–35 → 4; n=36–76 → 2. "As Chilenski's data shows, actual code
has been written with more than 36 conditions. Clearly, multiple condition
coverage is impractical for systems such as these."

**Why structural coverage at all** — the tutorial quotes RTCA/DO-248A FAQ #43:

> "it was realized that requirements-based testing cannot completely provide
> this kind of evidence with respect to unintended functions. Code that is
> implemented without being linked to requirements may not be exercised by
> requirements-based tests."

And the discipline that goes with it, from FAQ #44: if coverage analysis finds
untested code, "If any additional testing is required, it should be
requirements-based testing." You never write a test against the code to close a
coverage gap. That is Marick's argument, arrived at independently from the
regulated side, and made mandatory.

The tutorial also insists: "Coverage is a measure, not a method or a test. Thus,
phrases such as 'MC/DC testing' can do more harm than good."

**Does MC/DC actually find faults?** Two studies, pointing different ways.

- **For.** Arnaud Dupuy, Nancy Leveson, "An Empirical Evaluation of the MC/DC
  Coverage Criterion on the HETE-2 Satellite Software", DASC, Philadelphia,
  October 2000. **VERIFIED — full text read by a research subagent.** ~6000
  lines of C, functional testing first, then MC/DC gap-filling. "the test cases
  generated to satisfy the MC/DC coverage requirement detected important errors
  not detectable by functional testing... it was not significantly more
  difficult than satisfying condition/decision coverage". The mechanism: the
  uncovered code "primarily involved error-handling". They also credit it with
  finding *specification* gaps: "the whitebox testing process served as a
  verification of the completeness of the specification was very useful." Their
  own caveat: only 11 % of decisions had Boolean operators at all, so MC/DC and
  decision coverage were equivalent for the rest, which is why it was cheap.
- **Against.** Ajitha Rajan, Michael W. Whalen, Mats P. E. Heimdahl, "The effect
  of program and model structure on MC/DC test adequacy coverage", *ICSE 2008*,
  pp. 161–170, DOI 10.1145/1368088.1368111. **VERIFIED via institutional
  repository record; full text not read.** From the abstract: test suites
  satisfying MC/DC on a non-inlined implementation, re-run against the inlined
  version of the same logic, "yield an average reduction of 29.5% in MC/DC
  achieved". **100 % MC/DC is not a property of the test suite. It is a property
  of the test suite plus how the developer chose to write the Boolean
  expressions.**

**Relevance to us.** Confirms the doctrine's §4.3 refusal of coverage targets
with better evidence than the doctrine cites, and adds one thing the doctrine
misses. Marick's positive procedure — treat a gate finding as a *clue pointing
to a feature*, redesign the test for the feature, and expect the finding to
close as a side effect — is a usable rule for our gates, and the opposite of
what we did on 2026-08-02 when a claim was patched to make a command exit 0.
The DO-248A rule ("close a coverage gap with requirements-based tests, never
code-shaped ones") is the enforceable form.

---

## 7. Boehm, 1979 — verification versus validation

**Source.** Barry W. Boehm, "Guidelines for Verifying and Validating Software
Requirements and Design Specifications", TRW, Redondo Beach, CA. Presented at
Euro IFIP 79. **VERIFIED — full text read by a research subagent**, from a
re-typeset reproduction (body re-keyed, figures original scans). The
reproduction carries no venue or date line; internal evidence dates it to 1979
(latest reference April 1979). **Pagination ("pp. 711–719, North Holland")
UNCERTAIN — not confirmed.**

**The finding that matters.** The pithy formulation is **Boehm's own words**,
and it is in the **1979** paper — not first in the 1984 IEEE Software paper that
Wikipedia and most textbooks cite:

> "Verification - to establish the truth of the correspondence between a
> software product and its specification. (Note: This definition is derived
> from the Latin word for 'truth,' veritas...)
>
> Validation - to establish the fitness or worth of a software product for its
> operational mission...
>
> Informally, we might define these terms via the following questions:
>
> Verification: 'Am I building the product right?'
> Validation: 'Am I building the right product?'"

Note "**Am I**", first person singular. The circulating "Are we building…" is a
later paraphrase.

**The problem and the evidence.** Cost of late defect discovery. His Figure 1
("REQUIREMENTS ERRORS MUST BE CAUGHT EARLY") plots relative cost to fix against
the phase of detection, log scale 1 → 1000, with four plotted sources named in
the legend: IBM-SSD, GTE, SAFEGUARD, and a TRW survey median with 20th/80th
percentile whiskers. It is sourced to his own earlier paper (Boehm, "Software
Engineering", *IEEE Trans. Computers*, Dec. 1976) — **so the famous cost curve
is not original to the V&V paper**; the V&V paper reuses it as motivation.
Retrieved quote: "It shows that savings of up to 100:1 are possible by finding
and fixing problems early rather than late in the life-cycle."

**The part that got lost.** The slogan is not an aphorism; it does structural
work. Boehm draws a horizontal line across a V-chart and says the line is the
**requirements baseline**:

> "From the V-chart, it is clear that the key artifact that distinguishes
> verification activities from validation activities is the software
> requirements baseline."

Verification failures are fixed *below* the baseline. Validation failures
*force a change to the baseline itself*. That is the operational content, and
it is sharper and more useful than the slogan.

He also gives four criteria for a satisfactory specification — completeness,
consistency, feasibility, testability — and splits completeness into properties
that "can be verified by mechanical means" (no TBDs; no references to
nonexistent functions, inputs or outputs) versus those that "generally require
some human intuition to verify or validate" (missing spec items, missing
functions, missing products). His Section III then rates twelve techniques on
economics for small and large systems: reading and manual cross-referencing win
on economics; mathematical proofs score well on rigour and badly on cost.

**What happened to it.** Drift. The Wikipedia rendering attributes the questions
to Boehm 1984 and silently converts "Am I" to "Are we". More consequentially,
the standards drifted: IEEE-610's *validation* is evaluation against "specified
requirements", which is Boehm's *verification*. The later ISO/IEC/IEEE
formulation ("fulfils requirements for a specific intended use") pulls back
toward him. **IEEE 1012 and ISO/IEC 12207 exact wording: NOT VERIFIED** — three
retrieval attempts failed and nothing is quoted from them here.

**Relevance to us.** Contradicts our framing, mildly but usefully. The truth
ledger is entirely a *verification* instrument in Boehm's sense: it checks
correspondence between statements and the code below the baseline. It has no
validation apparatus at all — nothing in it can tell us we are building the
wrong kitchen software. The scratch design's "testimony" layer (owner rates,
supplier geometry, standards) is the closest thing we have to a requirements
baseline, and Boehm's rule says that when testimony is superseded, the
consequence is not "recheck the code" but "the baseline moved, and everything
descending from it must be re-argued". That is a stronger claim than the
scratch design's `bead --stands-on--> testimony` edge currently makes.

---

## 8. Meyer, 1992 — Design by Contract

**Source.** Bertrand Meyer, "Applying 'Design by Contract'", *Computer* (IEEE),
vol. 25, no. 10, October 1992, pp. 40–51, DOI 10.1109/2.161279. **VERIFIED —
full text read** (PDF from Meyer's own ETH Zurich publications page; Crossref
registry confirms volume/issue/pages/DOI).

**Provenance note.** Meyer states in the article that most concepts "were
previewed in the book *Object-Oriented Software Construction*" (1988) and that
the article is adapted from a later book chapter. The earlier 1986 technical
report often cited as the term's origin is **ATTRIBUTED** — I did not reach it.

**The problem.** Reusable components. "For reusable components, which may be
used in thousands of different applications, the potential consequences of
incorrect behavior are even more serious than for application-specific
developments."

**The reasoning, and what he was arguing against.** Defensive programming.

> "Adding possibly redundant code 'just in case' only contributes to the
> software's complexity - the single worst obstacle to software quality... The
> result of such blind checking is simply to introduce more software, hence more
> sources of things that could go wrong at execution time, hence the need for
> more checks, and so on ad infinitum."

The alternative is to *assign responsibility explicitly*. Each routine is a
contract between a client and a supplier, with obligations and benefits on both
sides, and — critically — the **No Hidden Clauses rule**: "no requirement other
than the contract's official obligations may be imposed on the client as a
condition for obtaining the contract's official benefits." An obligation entry
is simultaneously a benefit, because it states that the listed constraints are
the *only* ones.

**What Eiffel actually did.**

- **Preconditions** (`require`), checked on routine entry; **postconditions**
  (`ensure`), checked on exit, with `Old x` denoting the entry value;
  **class invariants**, checked on both entry and exit of every exported
  routine.
- **Monitoring is a per-class compile-time option**: none, preconditions only
  (**the default**), preconditions and postconditions, plus invariants, or all
  assertions. Violation raises an exception. Meyer's rationale for the default
  is worth quoting because it is an argument about *where* trust is cheap: a
  mature released library cluster probably needs no postcondition monitoring,
  but its clients are young and buggy, and their bugs "may show up as erroneous
  arguments in calls to routines" of the library — so check preconditions.
- **Contracts as documentation.** The `short` command strips bodies and keeps
  pre/postconditions. "software documentation is not treated as a product to be
  developed and maintained separately from the actual code; instead, it is the
  more abstract part of that code and can be extracted by computer tools."
- **Inheritance as subcontracting.** A redeclaration may **not** strengthen the
  precondition nor weaken the postcondition; it **may** weaken the precondition
  or strengthen the postcondition, because "the subcontractor does a better job
  than the original contractor". Eiffel enforces this syntactically: a
  redeclaration may not use bare `require`/`ensure`.

**The sentence to steal.**

> "Assertion monitoring, then, is a way to call the developer's bluff by
> checking what the software does against what its author thinks it does."

**Its ancestor.** Hoare, 1969 (see §9) already proposed exactly this as the
right form of subroutine documentation: "The most rigorous method of
formulating the purpose of a subroutine, as well as the conditions of its
proper use, is to make assertions about the values of variables before and
after its execution."

**What happened to it.** The idea won; the mechanism lost.

- **Taken:** the vocabulary (precondition/postcondition/invariant) is now
  universal; the Liskov-style substitution rule for contracts under inheritance
  is standard; assertion statements are in every mainstream language; the
  "contracts as extracted documentation" idea is in every doc generator; and
  QuickCheck's stateful model (§5) is literally `_pre`, `_next`, `_post` per
  API call — Design by Contract relocated into a test harness.
- **Refused:** always-on runtime contract checking outside Eiffel. Java's JML,
  .NET Code Contracts, Spec# and similar research/industrial systems did not
  become defaults. **Why they were refused is a question I did not establish
  from sources** — the research pass that was to cover it failed. I am not going
  to supply a plausible-sounding explanation I cannot cite. See "Sources still
  unread".

**Relevance to us.** Directly load-bearing for the scratch design's invariant
layer, and it supplies two design decisions we have not made:

1. **Monitoring level is a setting, not a constant.** Meyer's default —
   preconditions on, postconditions off for mature code — is the fast/slow
   split the scratch design §7 flags as "obvious but unspecified". The rule is
   not fast/slow, it is *whose bug is this likely to be*: check the inputs
   coming into stable components, not the outputs of stable components.
2. **No Hidden Clauses.** An invariant's declared `blind_spots` field is the
   negative half of the same rule. Meyer's version is stronger: it says the
   declared constraints are the *complete* set, so anything not declared is a
   promise. That is a much heavier obligation than "list what you don't catch",
   and it is the honest reading of what a GREEN invariant asserts.

---

## 9. Checking the checker — what else bears on our problem

The doctrine asks "how do you know a check is actually checking". Four sources
below genuinely bear on it. I researched fewer topics here than planned, and
have listed the rest as leads rather than write thin entries.

### 9.1 Hoare, 1969 — the axiomatic basis, and what he wanted it *for*

**Source.** C. A. R. Hoare, "An Axiomatic Basis for Computer Programming",
*Communications of the ACM*, vol. 12, no. 10, October 1969, pp. 576–580 and
583. **VERIFIED — page scan read** (title, abstract, notation and concluding
sections; journal running heads and page numbers visible).

The notation, in his words:

> "To state the required connection between a precondition (P), a program (Q)
> and a description of the result of its execution (R), we introduce a new
> notation: P {Q} R. This may be interpreted 'If the assertion P is true before
> initiation of a program Q, then the assertion R will be true on its
> completion.'"

What is usually missed is the *purpose* section. Hoare's stated payoff is not
proof for its own sake; it is three practical things, and two of them are ours:

> "the practice of proving programs would seem to lead to solution of three of
> the most pressing problems in software and programming, namely, reliability,
> documentation, and compatibility."

On documentation — the passage that becomes Design by Contract 23 years later:

> "The most rigorous method of formulating the purpose of a subroutine, as well
> as the conditions of its proper use, is to make assertions about the values of
> variables before and after its execution."

And the concession that should be printed on the front of our doctrine:

> "As in other areas, reliability can be purchased only at the price of
> simplicity."

**Relevance to us.** Confirms and predates the scratch design's central move.
Hoare's argument is that an assertion is simultaneously a check, a
specification and the documentation, and that the value of maintaining one
artefact instead of three is what pays for the effort. That is the exact
argument for collapsing claims-plus-evidence-plus-prose into a single invariant
record.

### 9.2 Schuler & Zeller, 2011 — checked coverage, and mutating the checks

**Source.** David Schuler, Andreas Zeller, "Assessing Oracle Quality with
Checked Coverage", *ICST 2011*, pp. 90–99, DOI 10.1109/icst.2011.32.
**VERIFIED — full text read.** (Journal extension: *STVR* 23(7), 2013,
pp. 531–551, DOI 10.1002/stvr.1497 — **VERIFIED bibliographically; not read**.)

**The problem, in their words:** "A known problem of traditional coverage
metrics is that they do not assess oracle quality—that is, whether the
computation result is actually checked against expectations."

**The proposal.** *Checked coverage*: "the dynamic slice of covered statements
that actually influence an oracle". Slice backwards from the assertions; only
statements that feed an assertion count.

**The experiment, which is the meta-test our doctrine §5.3 asks for.** They
introduce **oracle decay** — "oracle quality artificially reduced by removing
checks" — deleting 25 %, 50 %, 75 % of the assert statements from seven
open-source projects' test suites and measuring which metric notices.

Results: "For statement coverage, the decrease values are the lowest for all
projects… it is the least sensitive metric to missing assert-statements." And
"when 75% of the tests are removed, checked coverage decreases by 23%, whereas
the mutation testing score only decreases by 14%." Conclusion: "Checked
coverage is more sensitive to missing assertions than statement coverage and
mutation testing."

**The finding that qualifies mutation testing.** They observe that "test suites
with no assertions still detect a significant fraction of the mutations" —
because crashes, exceptions and timeouts kill mutants without any assertion
being involved. **Mutation score is contaminated by implicit checks.**

**Relevance to us, and it is a correction.** The scratch design makes
`mutation:` a required field: an invariant must ship a perturbation that turns
it RED. Schuler & Zeller say that is necessary but not sufficient — a
perturbation that makes the predicate *crash* proves nothing about whether the
predicate checks the right property. The requirement should be stronger: the
mutation must make the invariant report RED **for the stated reason**, not
merely exit non-zero. And their oracle-decay design is a ready-made,
cheap-to-run form of the doctrine's canary sweep: delete half our gates'
assertions and see which gates still pass.

### 9.3 Newcombe et al., 2014/2015 — formal specification that survived contact

**Sources.** Chris Newcombe, Tim Rath, Fan Zhang, Bogdan Munteanu, Marc
Brooker, Michael Deardeuff, "Use of Formal Methods at Amazon Web Services",
Amazon.com, 29 September 2014. **VERIFIED — full text read** (hosted on Leslie
Lamport's site). Journal version: "How Amazon web services uses formal
methods", *Communications of the ACM*, vol. 58, no. 4, 2015, pp. 66–73, DOI
10.1145/2699417. **VERIFIED bibliographically (Crossref); the CACM version not
read separately.**

**The problem.** "we still find that subtle bugs can hide in complex concurrent
fault-tolerant systems… human intuition is poor at estimating the true
probability of supposedly 'extremely rare' combinations of events". And the
decisive limitation: "We have found that testing the code is inadequate as a
method to find subtle errors in design, as the number of reachable states of
the code is astronomical."

**The proposal.** TLA+/PlusCal specifications of core algorithms, exhaustively
model-checked with TLC. They pitch it internally as "**Exhaustively testable
pseudo-code**", and deliberately avoid the words "formal", "verification" and
"proof".

**The evidence — their own results table**, which is unusually honest:

| System | Component | Lines | Benefit |
|---|---|---|---|
| S3 | Fault-tolerant low-level network algorithm | 804 PlusCal | Found 2 bugs; further bugs in proposed optimizations |
| S3 | Background redistribution of data | 645 PlusCal | Found 1 bug, and a bug in the first proposed fix |
| DynamoDB | Replication & group-membership system | 939 TLA+ | Found 3 bugs, some requiring traces of 35 steps |
| EBS | Volume management | 102 PlusCal | Found 3 bugs |
| Internal lock manager | Lock-free data structure | 223 PlusCal | "Improved confidence. Failed to find a liveness bug as we did not check liveness." |
| Internal lock manager | Fault-tolerant replication and reconfiguration | 318 TLA+ | Found 1 bug. Verified an aggressive optimization |

The fifth row is the most valuable line in the paper: a **declared blind spot
published in the results table**, admitting that the check passed something it
was not looking for. That is our L2 "declared unsoundness" requirement, in
production, by a team with everything to lose by admitting it.

**The lasting benefit they report is not bug-finding.** It is change safety:

> "a major benefit of having a precise, testable model of the core system is
> that we can rapidly verify that even deep changes are safe, or learn that they
> are unsafe without doing any harm."

and documentation: "a precise, testable, well commented description of a design
is an excellent form of documentation… a formal specification is precise,
short, and can be explored and experimented upon with tools."

They also publish what it does *not* do: it handles "bugs and operator errors
that cause a departure from the logical intent", but not "surprising 'sustained
emergent performance degradation' of complex systems that inevitably contain
feedback loops. … We don't yet know of a feasible way to model a real system
that would enable tools to predict such emergent behavior."

**Relevance to us.** Contradicts the doctrine's §4.10 blanket refusal of formal
methods — not on the merits, but on the reasoning. The doctrine refuses formal
methods as over-engineering. AWS's argument for adopting them is the *opposite*
of over-engineering: a few hundred lines of specification, sold internally as
pseudo-code, whose payoff is "is this change safe?" answered in minutes. That
is exactly the L5 blast-radius question the doctrine says we cannot answer, and
it is exactly what bit us when `/admin` broke. Our refusal is probably still
right at our scale, but §4.10 should say "not worth it *here*", not "refuted".

### 9.4 Goodenough & Gerhart, 1975 — the criterion both DeMillo and Weyuker were answering

**Source.** John B. Goodenough, Susan L. Gerhart, "Toward a theory of test data
selection", *Proceedings of the International Conference on Reliable Software*,
1975, pp. 493–510 (also *ACM SIGPLAN Notices* 10(6) and *IEEE TSE* SE-1(2),
pp. 156–173). **VERIFIED bibliographically (Crossref, three concurrent
records); full text NOT read.**

Included because it is the paper both DeMillo et al. and Weyuker cite as the
thing they are responding to: it introduced the notions of *reliable* and
*valid* test criteria and the taxonomy of error classes DeMillo reproduces
(implementation error; specification not representing the design; failure to
understand a requirement; failure to satisfy a requirement). DeMillo's
observation that these are "global concerns" while real errors show up as
"missing control paths, inappropriate path selection, or inappropriate or
missing actions" is a direct reply to it.

**Relevance to us.** Bibliographic only, until someone reads it. The
error taxonomy is nevertheless immediately usable: our claim-death post-mortem
should classify each retraction into those four buckets, which would answer the
question §5 of this document says we cannot currently answer.

---

## What this lineage says we got wrong or missed

Directly, and in order of how much it should change what we do.

**1. We priced `truth mutate` as a mechanism. It is a suppression problem.**
The doctrine ranks "mutate the evidence" as the single highest-value item and
budgets it as medium effort. Google ran this exact experiment at scale and
found that **85 % of raw mutation findings were unproductive**, that fixing that
took six years of accumulated heuristics, and that the deliverable is *one*
mutant per changed line, not all of them. Median mutants per change went from
820 to 7. If we build `truth mutate` and let it report everything, it will
become the thing we switch off — and by §4.11 our own doctrine says a gate that
warns forever is worse than no gate. **The suppression list is not a later
refinement; it is the feature.**

**2. Our mutation requirement is too weak, and Schuler & Zeller show why.**
The scratch design requires each invariant to carry a perturbation that turns it
RED. But a perturbation that makes the predicate crash, error, or exit non-zero
for an unrelated reason satisfies that requirement while proving nothing. The
requirement should be: the mutation must produce the *specific* RED the
invariant's statement describes. Schuler & Zeller measured this directly —
test suites with every assertion deleted still killed a significant fraction of
mutants, purely through crashes. **Mutation without checking why it failed is
itself evidence that cannot fail.**

**3. We have no validation layer, and Boehm's distinction says that is a real
gap, not a scope choice.** Everything in the ledger is verification: does the
statement correspond to the code. Nothing in it can tell us the code is solving
the wrong problem. Boehm's operational rule — verification failures are fixed
below the requirements baseline, validation failures force a change *to* the
baseline — maps onto the scratch design's testimony layer, but the design's
`stands-on` edge is too weak for it. When owner testimony is superseded, the
consequence should not be "recheck dependent work"; it should be "the baseline
moved, and every design decision descending from it is now unargued." That is a
much louder signal than a HELD flag.

**4. Two thirds of what a verification apparatus finds is supposed to be
defects in the apparatus. We treat that as failure.** Claessen & Hughes: errors
divide "roughly evenly between errors in test data generators, errors in the
specification, and errors in the program". Hughes 2016 on the Volvo project:
over half of 200+ findings were ambiguities in the *standard*, not bugs in the
code. Our 35 % claim mortality is currently read as a maintenance-cost symptom
on the FIT curve. It might instead be the apparatus working exactly as
designed. **We cannot tell, because we do not record whether a dead claim died
from a code change, a mis-worded statement, or a broken recipe.** Adding that
one field to a retraction is the cheapest high-value change in this whole
document, and it converts an anxiety into a measurement.

**5. Metamorphic testing is missing from the doctrine and it is the right tool
for our hardest claims.** Several things this system produces have no oracle in
Weyuker's sense — a nesting layout, a cutting list, a drilling pattern. We have
been coping by freezing golden outputs, which is a *relation between one run and
one past run*. Chen et al. give the general form: relations between runs of the
same program on related inputs. Mirror a cabinet and the drilling pattern must
mirror; permute the panel order and total board consumption must not change;
scale every dimension and the edge-banding length must scale. These are cheap,
they need no golden file, and they do not rot when a legitimate change lands —
which is precisely the failure mode of golden files. **This is the most
actionable omission in the doctrine.**

**6. Our §4.10 refusal of formal methods is right for the wrong reason.** AWS
adopted TLA+ *because* it was cheap: a few hundred lines, sold as "exhaustively
testable pseudo-code", answering "is this change safe?" That is our L5
blast-radius problem, and it is the one that broke `/admin`. The refusal should
be scoped honestly — "not at our size, not yet" — rather than stated as if the
technique were refuted.

**7. Two attributions in the doctrine are imprecise enough to matter.**
- The doctrine dates mutation testing to 1978 and credits DeMillo et al. with
  the *competent programmer hypothesis*. The 1978 paper does not name that
  hypothesis; it states the idea informally. It does formally state the
  coupling effect, and it explicitly says the coupling effect cannot be proved.
  When we cite it as our foundation, we should cite what it actually claims —
  and we should cite Just et al. 2014, which measured it: true for 73 % of real
  faults, with 17 % reachable by no mutation operator at all.
- Marick's "How to Misuse Code Coverage" is dated "late 1990s" in the doctrine.
  Written 1997, presented 1999. More importantly, the doctrine uses him only
  negatively (coverage tells you what you did not test). His *positive*
  procedure — a gate finding is a clue pointing at an under-tested feature;
  redesign the test for the feature and expect the finding to close as a side
  effect — is the rule we violated on 2026-08-02 and is worth adopting
  verbatim.

**8. What I could not establish.** Runtime verification as a field, model
checking's adoption history, the empirical assertion-density literature, and
the specific reasons industry refused always-on contract checking. The research
pass covering those failed and I did not substitute guesses. They remain open.

---

## Sources still unread (worth obtaining)

Each row states what we would gain that open sources could not give.

| Source | Where | Cost | What we would gain |
|---|---|---|---|
| R. G. Hamlet, "Testing Programs with the Aid of a Compiler", *IEEE TSE* SE-3(4), 1977, pp. 279–290 | IEEE Xplore | ~USD 33 article purchase | Whether the independent 1977 formulation really is mutation testing, and what his compiler-integrated design was. Our doctrine credits Hamlet in one clause; nobody here has read him. Also settles the weak-mutation origin, which Marick attributes to `[Hamlet77]`. |
| J. J. Chilenski, S. P. Miller, "Applicability of modified condition/decision coverage to software testing", *Software Engineering Journal* 9(5), 1994 | IET Digital Library | ~USD 40 | The original cost/benefit argument for MC/DC in the authors' own words, rather than at one remove through the NASA tutorial. Low priority — the tutorial quotes the key passage. |
| RTCA/DO-178C (and DO-248) | RTCA | ~USD 800 | The normative text of the MC/DC objective and, specifically, whether DO-178C still places it at Level A only. We currently cannot confirm this from any source actually read. **Not worth buying** — the claim should simply be stated as DO-178B, which is verified. |
| C. A. R. Hoare, "How Did Software Get So Reliable Without Proof?", *Lecture Notes in Computer Science*, Springer, 1996, pp. 1–17, DOI 10.1007/3-540-60973-3_77 (**VERIFIED bibliographically via Crossref; content not read**) | SpringerLink | ~USD 30 chapter | This is Hoare conceding, in print, that testing and engineering process delivered reliability his proofs did not. It is the single best counterweight to our own tendency toward more machinery, and it is by the person with the most to lose by writing it. **Highest value on this list.** |
| B. W. Boehm, *Software Engineering Economics*, Prentice-Hall, 1981 | used market | ~USD 30–60 | Whether the question form appears there as well as in 1979, and the full defect-cost dataset behind the 100:1 figure. Low priority; the 1979 paper covers what we need. |
| B. Meyer, *Object-Oriented Software Construction*, 2nd ed., 1997 | new/used | ~USD 60–90 | The full treatment of contracts under inheritance and the "class invariant" semantics, and Meyer's own retrospective on why runtime contract checking did not spread. The 1992 article covers the mechanism; the book covers the argument. |
| E. J. Weyuker's cited pseudo-oracle paper: M. Davis, E. Weyuker, "Pseudo-oracles for non-testable programs", *Proceedings of ACM '81 Conference*, 1981 | ACM DL | possibly open | The pseudo-oracle proposal in full. Weyuker's 1982 paper summarises it adequately; check the DL first, much of the older backfile is now open. |

---

## Method note

Sources I read in full: Dijkstra EWD 249 (transcription) and the NATO 1969
report; DeMillo, Lipton & Sayward 1978; Weyuker 1982; Chen, Cheung & Yiu 1998;
Claessen & Hughes 2000; Hughes 2016; Marick 1999 (complete Wayback copy);
Hoare 1969 (page scan); Meyer 1992; Schuler & Zeller 2011; Just et al. 2014;
Petrović et al. 2022; Le, Afshari & Su 2014; Newcombe et al. 2014. Read by a
research subagent and reported with retrieved quotes: Boehm 1979; Marick 1991;
Hayhurst et al. 2001; Dupuy & Leveson 2000. Verified from registry metadata
only, and labelled as such above: Hamlet 1977; Goodenough & Gerhart 1975;
Duran & Ntafos 1984; Offutt 1992; Chilenski & Miller 1994; Rajan et al. 2008;
Zhou & Sun 2019; Chen et al. 2018; Petrović & Ivanković 2018; Newcombe et al.
2015; Hoare 1996.

Registry lookups used Crossref and dblp APIs directly. No source was obtained
from a shadow library.
