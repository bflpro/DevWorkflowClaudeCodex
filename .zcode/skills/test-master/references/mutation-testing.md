# Mutation Testing

The executable procedure behind the question in
[proving-a-check.md](proving-a-check.md): break the code on purpose and see whether the
suite notices. Everything here is tool-independent — it is a procedure, not a product.
If a mutation runner exists in the project, it must satisfy the same obligations; if it
does not, the procedure runs by hand with a text editor and a test command.

Two verdicts, checked differently:

| Verdict | Who audits it | Consequence of being wrong |
|---|---|---|
| `survived` — a finding | Someone investigates it | Wasted work, a test written for a risk that never existed, a false accusation against the author |
| `killed` — closure | **Nobody** | The suite is scored strong when it is blind; the receipt becomes the evidence |

**The reassuring verdict is the one that needs proof.** The verdict that generates work
gets a natural audit; the verdict that closes the question is simply accepted. Every rule
below exists because one of the two verdicts can be produced without the suite having
answered anything.

## Table of contents

- [Procedure](#procedure)
- [Harness trustworthiness checklist](#harness-trustworthiness-checklist)
- [Deriving the mutant set](#deriving-the-mutant-set)
- [Reading the result](#reading-the-result)
- [Reporting](#reporting)
- [If you are the reviewer prescribing the fix](#if-you-are-the-reviewer-prescribing-the-fix)

---

## Procedure

### 0. Isolate the tree

Never mutate a working tree anyone else can write to. A shared tree can only convert
`survived` into `killed` — foreign breakage adds failures and never removes them — so
every corruption pushes the verdict toward "the tests are good", which is the answer that
ends the investigation. A flaky-looking baseline gets noticed; a uniform green-to-red flip
gets congratulated.

Create a checkout pinned to the revision under review (a detached worktree, a clone, an
export). Then:

- **Scope follows the verification COMMAND, not the subject of the review.** If the command
  is "run the whole suite", the copy must feed the whole suite — not only the module being
  examined. Deriving scope from what you are studying is the standard way to spend three
  rounds on the copy.
- **Reproduce the path relative to the repository root**, not only the directory itself.
  Suites anchor external oracles by counting levels up (`parents[4]`) and read neighbouring
  projects; a flat copy breaks every such anchor, and that anchoring lives exactly where a
  suite compares itself against an external reference.
- **Symlinks isolate reads and do not isolate writes.** A copy assembled from links inherits
  the original's *permissions* along with its contents. Name the direction of the isolation
  you need. If the invariant is "the working tree is not modified", it needs its own oracle:
  snapshot the original's state before and after (`git status --porcelain`, a tree hash) and
  fail on any difference. A green suite inside the copy is evidence about reads only.
- **A symlinked directory is the whole directory.** Build the substitution list from what the
  suite actually *reads*, down to individual files where a file suffices, and widen it only
  under a test that reddens without the path. Otherwise a throwaway tree ends up holding live
  tokens, `.env` files and neighbouring services' data directories — and no test fails because
  of surplus access, only because of missing access.
- **Apply the secret filter to the whole composition, including link targets**, and verify it
  with a positive test: no path in the built copy matches the deny patterns.
- **Record the scope in the report** (which paths were exported, which were linked), or the
  next round repeats the same three attempts.

### 1. Control run — before the first mutation, with numbers

Run the verification command on the **unmutated** copy and record **three numbers: passed,
failed, skipped**, each compared against the same revision in the live tree and against what
the author reported.

- **Red control is by default a defect of the copy, not a finding about the delivery.** An
  incomplete copy does not announce itself with silence: it produces a detailed, plausible red
  that reads exactly like the best finding a reviewer can bring, and it needs no further
  checking to feel confirmed. Before calling it a finding, run the same command in the live
  tree at the same revision.
- **Green with unexplained skips is not a control.** Missing inputs that raise produce a red
  that gets investigated; missing inputs that `skip` produce a green that gets banked, and a
  well-written skip message is what converts a broken environment into a passing one. A skip
  count that differs from the baseline is a copy defect exactly as a failure is. Enumerate
  which tests skipped and why before accepting the baseline.
- **Control per killing test.** For each mutant, the test designated to kill it must be green
  *before* the mutation. Without that, "the test failed on the mutant" and "the test always
  fails" are the same observable, and the one that requires nothing is chosen. A red killing
  test is its own outcome (`control_red`), never `killed`.
- A control run certifies the run, **not the base**. An inert contaminant is green by
  definition. See the identity check in §3.

### 2. Apply a mutation — provably

- **Address by a unique text anchor, never by a line number.** The applying step asserts the
  anchor occurs exactly once and refuses otherwise. A mutation that cannot be uniquely
  addressed needs a longer anchor, not a coordinate. Line numbers come from a *different* read
  of the file than the edit, and a mis-addressed edit produces a no-op whose evidence is a
  green run — byte-identical to the finding.
- **Prove application by construction, not by grepping afterwards.** The single-site assertion
  firing, or the diff hunk, is the proof. A substring-absence check after the fact gives false
  failures for insertions and says nothing about whether the right site was hit.
- **Prove non-inertness, and prove it in the right currency.** "The bytes changed" proves the
  text was applied, not that behaviour differs.
  - For value/branch mutations: show the mutated code behaves differently on at least one
    input; for ordering mutations, build them by moving the statement programmatically and
    diff the compiled form, since a textual substitution silently no-ops when the anchor
    carries more text than behaviour.
  - For **scope** mutations (an allow-list, a filter, a traversal depth, a glob), measure the
    thing the mutant controls — the number of reachable paths, the size of the set, the length
    of the list — before and after, and show it moved.
  - For guards over a **collapsed or normalised key space** (JSON paths with `[]`, globs,
    canonicalised identifiers), the mutation must act in the space the guard observes. Moving
    a datum between instances that collapse to one symbol changes nothing the guard can see.
    Print the guard's observed set before and after: byte-identical means inert.
- **A non-compiling mutation is discarded explicitly** and excluded from the score, never
  counted as a survivor and never quietly dropped.

### 3. Restore — from an immutable source

- **Never restore from a sidecar the harness itself writes.** A backup written by the mutating
  step stops being the original on the second edit to the same file: the second `apply` copies
  the already-mutated file over the backup, and the restore then returns mutant #1 and calls it
  clean. The contamination can be inert under the current configuration, so the next control
  run is green — and the defect finally surfaces as *your* hashes disagreeing with the author's
  receipt, i.e. as an accusation against the person under review, which is the direction of
  error least likely to be challenged.
- Re-materialise each target from the revision (`git show <rev>:<path>`) or from a read-only
  pristine copy made once.
- **Verify the base by identity, not by outcome:** before each mutation, assert the target's
  hash equals the revision's. A green run is not evidence that the base is clean.
- **Re-establish the base at every phase change.** A review campaign alternates between two
  kinds of edit to the same files — "break it with a mutant, to measure the tests" and "apply
  my prescribed fix, to show it red on my mutant". A base captured during the *fixing* phase
  turns the whole next campaign into a test of the recipe against itself, and the first symptom
  is an anchor that no longer matches, whose cheapest explanation ("stale anchor") points away
  from the cause. Any procedure that perturbs one object in two different ways for two different
  purposes needs its reference point outside the object.
- When several mutants touch one file, state in the report how the base was re-established for
  each — that is the case a harness is most likely to get wrong.

### 4. Pair the mutant with a killing test — and verify the pairing

The mapping "mutant → killing test" is an assertion about a **fixture**, not about code
location. Code location matches almost always, which is why the mapping looks plausible and is
checked in a second by eye; whether the named test's fixture *distinguishes* the two behaviours
is checked by nobody.

- Pick the test by reading its **arrangement**, not its name. A test named for the property the
  mutant attacks is the most persuasive wrong choice available.
- Record a third column: **the distinguishing input** — which field of *this test's* fixture
  differs between original and mutant. An empty cell means there is no killing test, not that
  someone forgot to name one.
- Mechanical pre-check: write down the axis the mutant varies (boundary / composition / source /
  filter / timing) and the axis the named test varies. Axes must match.
- For a mutant expressing the feature's **central decision**, the killing test must be **new and
  built from the mutant**, not found among the existing ones. That is exactly where an
  approximately-right test will be found and where its fixture most often fails to separate the
  two formulas.
- **Verify which assertion inside the node reddens.** A pinned size literal (`len(LIST) == 25`,
  "exactly three entries") dies first in almost any composition mutant and systematically steals
  attribution from the substantive guard — while being the first thing a routine edit to that
  same list updates. Control check: weaken the pinned literal (or mentally apply the standard
  edit instruction for that list) and see whether the node is still red. Still red → the pairing
  is right. Green → the receipt certifies a one-day guard, and you need either a different node
  or a second mutant "weaken and adjust the literal". For receipts that grant access or close a
  security finding, this step is mandatory.

---

## Harness trustworthiness checklist

Before any verdict from a harness — yours, the project's, or a third party's — is read:

- [ ] Control run on the unmutated tree is green, with **passed / failed / skipped** all
      matching the baseline.
- [ ] The killing test for each mutant is green before its mutation (`control_red` is a
      separate outcome with a non-zero exit).
- [ ] Mutation is addressed by unique anchor; occurrence count asserted.
- [ ] Application is proven by construction; non-inertness proven in the mutant's own
      currency.
- [ ] Base restored from an immutable source; base hash asserted before each mutation.
- [ ] Isolation direction named, and the non-write invariant has its own oracle.
- [ ] Copy scope derived from the verification command; scope recorded.
- [ ] At least one mutant per batch whose kill was **predicted in advance** — a positive
      control. A batch in which nothing is killed is a broken harness until proven otherwise.
- [ ] The harness distinguishes a **collection error** from a test failure, and treats the
      former as VOID rather than `killed`. Only a named failing test attributable to the
      mutated module is evidence.
- [ ] Four outcomes are reported, not two: `killed` / `survived` / `inert` / `control_red`
      (plus `not-exercised`, §"Reading the result"). The first two are claims about the tests,
      the rest are claims about the run, and they are repaired differently.
- [ ] A claim about what a tool does is verified by **reading the tool**, not by its being a
      reasonable expectation. ("Mutation runs in a copy of the tree, that is already
      implemented" — while the code writes into the working tree and restores in a `finally`.)

**When a one-off practice moves into code, its acceptance changes.** A hand-built copy is
repaired in the same session by the red run that exposed it; a copy built by a tool freezes the
same defect in source, where it becomes a permanent property of every future run, and several
registry entries become permanently unverifiable. Worse, good new diagnostics added alongside
will give the defect a plausible name from their own vocabulary (`control_red` → "look for a
broken test") and lead the investigation away from the real cause. So a tool that automates a
manual procedure is accepted against the procedure it replaces — a full-suite comparison of the
copy against the working tree, both numbers — not against one green run.

---

## Deriving the mutant set

**The set is a sample, and the sampler is the same mind that wrote or just reviewed the
tests.** Left to itself it draws exactly the defects the tests were written against, which
makes a perfect score the expected result of a worthless sample.

1. **Enumerate mechanically from the code, then sample.** Walk the module and list every
   comparison operator, every boundary constant, every boolean connective, every early return,
   every declared-contract constant, every branch whose guard has two clauses. The set derived
   this way contains the defects nobody has thought of, which is the only population worth
   measuring.
2. **Define the enumeration unit explicitly.** A regex, a format string, a SQL predicate, a
   schema literal is not an atom — list its parts (each anchor, each quantifier bound, each
   character class, each alternation branch) exactly as clauses of a boolean guard are listed.
   An enumeration coarser than the smallest independently breakable decision looks exhaustive
   and silently samples.
3. **Exclude the previous round's findings from the suite-strength count.** Verifying a fix by
   mutation is correct and necessary, but it belongs in the fix-verification section. Mixing
   the two lets closure evidence be read as coverage evidence.
4. **For each newly introduced formula, list its terms** and mutate them one at a time
   ("remove one term", "swap a term for a plausible sibling"). Boundary cases vary the *result*;
   the composition of the inputs is an orthogonal axis, and a trio of boundary cases leaves it
   entirely open while reading as complete precisely because the boundaries are all named. A
   term that is zero (or the operation's neutral element) in every fixture can be deleted from
   the formula with impunity.
5. **Mutate the constant AND its use.** A constant extracted as part of a fix has two
   independent failure surfaces: what is in it, and who reads it. A guard pinning its contents
   reads as closing both, while one line at the call site reverts the whole fix with the suite
   green and the extracted function still sitting unused in the file. Phrase it as: *unwire the
   call, do not only corrupt the value*.
6. **Mutate the test's own literals, not only production code.** A closed list fixed by a
   decision is behavioural and belongs in the registry, with "delete an entry (adjusting any
   counts that mechanically follow)" as a named mutant. Expect it to survive, and treat the
   survivor as the finding rather than as proof the list is fine.
7. **Prefer branches the fixture corpus does not reach** — a one-line scan establishes which.
   That is where the corpus's silence and the unit tests' gaps coincide.
8. **Cover the scope class explicitly**: guards whose subject is reachability, an allow-list, a
   filter, a traversal depth, or coverage of a declared surface. These are the ones a trimmed
   test bench cannot measure (see below).
9. **Use sibling asymmetry as a free candidate list.** Whatever one implementation of a guard
   asserts and its twin does not is a mutant to run, not a stylistic note.
10. **A mutant set is a snapshot of a specific design, not a property of the feature.** While
    review rounds keep reworking the design, the snapshot ages at exactly the rate the review
    works well. Give the list an **owner and an expiry**: "immutable for the implementer,
    reissued by the reviewer at every rework of the design". Each round, run two reconciliations
    — every killing-test name against the current test names, every file against the files the
    feature still touches — and the reverse one that matters most: **every new decision must
    have at least one mutant**, because a design that appeared in round two is by default
    uncovered. Do not hard-code the list's length into an acceptance criterion a second time;
    have the criterion read the count from the file itself.

---

## Reading the result

**`survived` is a hypothesis about the instrument before it is a finding about the tests.**
There are four distinct routes to a survivor line, and the report renders them identically:

| Route | Tell | Correct verdict |
|---|---|---|
| The tests are genuinely blind | Mutation applied, non-inertness proven, the killing test's fixture supplies data on both sides | `survived` — a finding |
| The mutation never applied | Anchor mismatched; the printed target line does not contain the replaced text | Broken harness — re-address |
| The mutation is semantically inert | Behaviour-preserving substitution; or a scope mutant on a trimmed bench where there was nothing to widen; or an instance-level edit against a shape-level guard | `inert` — a finding about the mutation |
| The mutation is real but **not exercised** | The named test's arrangement puts no row / value / branch input into the mutated construct: the query returns zero rows with and without the filter | `not-exercised` — a finding about the **test**, not about the code |

The last two are the expensive ones, because they accuse the suite of a hole it does not have,
and the natural response — writing another test — produces a test asserting something that was
never at risk.

Distinguishing inert from not-exercised: an inert-by-text mutation cannot change behaviour on
**any** input; a not-exercised mutation changes behaviour on some input, just not the one the
chosen test constructs. The difference lives in the fixture, which the runner never reads.

**A trimmed bench is only representative along the axes it did not trim.** Before running a
batch, name the axes on which the bench differs from production (volume, composition, path
depth, permissions, clock), and for each mutant check whether its subject lies on one of them.
A mutant about **scope** on a trimmed bench is invalid by default and must be re-run in the real
tree. Every economy in a fixture is a narrowing of the set of hypotheses the fixture can
distinguish, and the narrowing is invisible from inside the run: after the fact it looks like a
finding about the subject rather than about the instrument.

**`killed` is a hypothesis too.** It is only evidence if the control run was green, the killing
test was green before the mutation, and the assertion that reddened is the one the mutant was
written to challenge (§4).

**When replaying someone else's receipt, a disagreement is a defect of your replayer until
shown otherwise.** A parser asks the format questions it never promised to answer — one code
block equals the whole patch, one file equals the whole mutant — and each assumption comes back
as a discrepancy shaped exactly like a caught falsification. A parser error that lands on
*seventeen* mutants is obviously yours; one that lands on exactly *one* is plausible, sounds
like an accusation, and requires no further checking to feel confirmed. **Suspicion of your own
tooling must rise as the discrepancy becomes more targeted.** Practically: open the raw text of
that receipt section by eye before calling it a finding; collect **all** file+hash pairs in a
section and apply them together; assert the number of applied edits equals the number of declared
hashes; print "N of M sections parsed" so a full parse is distinguishable from a silently
skipped one; and check your own base file's hash against the revision before anything else.

---

## Reporting

- **Report survivors, not kills.** "Five mutations, five kills" is unreportable as evidence;
  "28 mutations from a mechanical enumeration, 11 survivors, here they are" is. A report with a
  100% kill rate is a statement about the sampling, not about the suite — make that an explicit
  criterion for whoever reads it.
- **Print the enumeration itself** — the list of units, each marked "mutated" or "deliberately
  skipped + reason". A completeness claim written as a sentence cannot be audited, and a gap
  should show up as a missing row rather than as a reviewer's lucky guess.
- Record next to each survivor **the evidence that the mutation applied and was non-inert**.
  "Survived" without that line is an unverified claim.
- Record the revision, the copy's scope, the control run's three numbers, and the base hash per
  mutant.
- Record the **expected** outcome per mutant before the run. A mismatch between expectation and
  outcome is a reason to stop, not a row in a table.
- Record the control outcome as its own column. A receipt without one is indistinguishable from
  a receipt with a red control, and those are opposite documents.
- Distinguish, in the report, the "as delivered" scenario from any scenario in which your own
  prescribed fix was applied.

---

## If you are the reviewer prescribing the fix

A reviewer who demands proof by mutation ships two artefacts with no proof of their own — the
prescribed recipe and the demonstrating mutant — and both fail **silently and in the direction
that confirms the reviewer**: a useless recipe reads as a working guard, a confounded mutant
reads as a caught hole.

- **Run the recipe against the mutant before issuing it.** Apply both in your copy and show the
  red. If you have not run it, issue a *requirement on behaviour* ("the guard must redden on
  mutant X") and leave the form to the implementer. A requirement without a form is more honest
  than an unverified form. The cost of getting this wrong is higher than an ordinary review
  error: an implementer who faithfully adopts the recipe gets a correctly-named guard that
  misses the finding, and the finding is then closed formally with nobody left to reopen it.
- **The recipe must intercept the same execution path as the mutant.** Cheap check: name the
  function the mutant edits and the function the guard calls. Not the same → the guard misses.
- **Check the mutant can die for the reason you allege.** Before presenting a green run as
  blindness, ask whether this subject is *capable* of dying from the mechanism you are accusing,
  or whether its green is an already-accepted limit of the method (for example a field rendered
  twice, which no differential mutation can kill). Pick a subject with no second carrier.
- **When the implementer declares a survivor "a limit of the method", they have named a class,
  not a case.** Enumerate the whole class: a limit of the method and a hole in the suite look
  identical from outside, and they differ only by the presence of a compensating check at each
  specific site.
- **Resolve an objection by reproduction, not by persuasion.** Run both variants, record the
  outcome, and if the implementer was right, say so in plain words rather than dissolving it
  into "closed differently".
