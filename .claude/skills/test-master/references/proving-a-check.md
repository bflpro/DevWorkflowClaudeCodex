# Proving a Check

Canonical reference for one question:

> **What proves that this check is capable of going red?**

A check here is anything offered as evidence that code behaves correctly: a test,
an assertion, a guard, a grep-based acceptance criterion, a schema comparison, a
parity run, a verification command in a task or spec. The question is not "does a
check exist" and not "does it pass" — it is whether the check can distinguish the
correct system from a wrong one.

Passing tells you nothing on its own. A check that cannot fail passes for the same
reason a correct system passes, and the two are byte-identical in the run output.
Worse than absent: an empty check consumes the attention that would have noticed
the absence.

Other skills reference this file rather than restating it: code review, production
review, pre-deploy acceptance and security audit all need the same question, phrased
the same way.

## Table of contents

- [1. Where the expected value comes from](#1-where-the-expected-value-comes-from)
- [2. Anti-vacuity: the mandatory red run](#2-anti-vacuity-the-mandatory-red-run)
- [3. Non-empty input and the traversal domain](#3-non-empty-input-and-the-traversal-domain)
- [4. Differential oracles: name what is observed](#4-differential-oracles-name-what-is-observed)
- [5. The double and the fixture are part of the oracle](#5-the-double-and-the-fixture-are-part-of-the-oracle)
- [6. Completeness is derived from the artefact, never from memory](#6-completeness-is-derived-from-the-artefact-never-from-memory)
- [Review checklist](#review-checklist)

---

## 1. Where the expected value comes from

**Rule: for every literal a check asserts against, name its source — and that source
must not move when the code under test moves.**

An assertion is a comparison between what the code produced and something else. If
the something else is derived from the code, the comparison is between the code and
itself: it proves internal consistency and calls it correctness. The defect is
invisible in review, because a literal looks equally authoritative whichever
document it was retyped from.

Four recurring shapes:

| Shape | What happens | The fix |
|---|---|---|
| Expectation imported from the subject | `from module import MAX_ATTEMPTS` then asserting a loop ran `MAX_ATTEMPTS` times. Changing the constant to any value keeps the suite green — the one thing in dispute (the value) is structurally unpinnable. | Where a requirement names a number, one test restates that number as a literal taken from the requirement (`assert MAX_ATTEMPTS == 5`), separately from the behavioural tests that scale with it. The duplication *is* the oracle; DRY is correct for production code and inverted on the assertion side. |
| A machine-readable spec artefact retyped instead of executed | A spec contains runnable DDL / a JSON schema / an OpenAPI document / a config sample, and the conformance test transcribes its contents as literals. Both versions pass on day one; afterwards spec and code drift with nothing comparing them. | Execute or parse the normative artefact in the test and diff it against what the code produces. The cheapest correct oracle is already written. |
| Equivalence asserted with no runnable reference | A port/migration/rewrite claims "same behaviour as the old implementation", and the expected side is a human-assigned label in a fixture. A hand-set label is a validity check on the logic, never an equivalence check on the port. | Name the mechanism that produces the reference output and check that the reference is runnable — a runnable reference converts equivalence from opinion into an exact assertion. Compare the widest structure the code returns, not a summary field: equivalence asserted on a summary passes for every divergence the summary absorbs. |
| Both sides of a cross-module claim taken from one side | A translation table / status map / registry is tested by asserting its keys equal an expected set written in the same module. Two modules can only diverge if each value came from its own side. | The key set must come from running the real writer, or from reading the writer's own artefact (its declared list of supported types, its exported surface). A fixture that builds a record "the way the other module writes it" must take the value from that module's output — a literal there is a hypothesis about a neighbour, not a requirement. Review tell: the test mentions one module, its name claims a link between two. |

**Two kinds of literal, opposite rules.** A literal that *is* the requirement (a
timeout of 1440 minutes, a message text, a status code) must be restated verbatim
and must never be imported from the code. A literal that *describes an absence* (an
identifier not in a registry, a key not in a dictionary, a path not on disk) must be
*derived at run time* — `next(x for x in candidates if x not in configured)` — because
the set of "what does not exist" is owned by the system and changes as the system
grows legitimately. Control question: **can the system acquire, by design and on plan,
the thing whose absence this check asserts?** If yes, the subject of the negation must
be computed. A pinned absent value breaks exactly when development goes as intended,
and its failure is indistinguishable from a regression.

**Compute-it-two-ways is a rule about provenance, not arithmetic.** A degeneracy or
minimum-size guard whose two counts resolve to the same artefact (same directory
listing, same query, same in-memory collection) is one measurement wearing two hats,
however differently the two expressions read. At least one count must come from an
artefact written by a *different* step — a capture manifest, a committed expected
count, a checksum file. The review question is never "are these computed
differently?" but "**what would have to be true for these two to disagree?**"

---

## 2. Anti-vacuity: the mandatory red run

**Rule: a check is not delivered until it has been observed red. Deliver the red
observation, not a description of it.**

Green is the state a vacuous check and a correct system share. The only evidence that
separates them is a run in which the check failed for the reason it exists.

**Executable form** — for each check, before calling it done:

1. State the failure it is supposed to catch, in one sentence.
2. Produce that failure: break the code, plant the forbidden value, feed the
   adversarial input, run the criterion on the revision *before* the work.
3. Observe the check red, and confirm the failure message names the right subject.
4. Restore, and observe it green.

If step 3 cannot be produced, the check is not a check yet. For breaking the code
systematically, see [mutation-testing.md](mutation-testing.md) — that file is the
procedure; this section is the obligation.

**Acceptance criteria are checks too.** A grep-shaped criterion must be **red on the
starting revision and green after the work**. Running it only after the work confirms
nothing: the cheapest positive condition to add is one that is already true (a date
already present in a changelog, a name already imported, a file that already exists),
and it turns a conjunction into a tautology while keeping the correct form. A criterion
never observed red is indistinguishable from a commented-out one.

**Recurring vacuity patterns:**

- **Negation swallows instrument failure.** `! grep PATTERN path` exits 0 when grep
  errors (bad path, unreadable file) exactly as when the pattern is absent. Every
  absence check ships with an existence anchor on the same subject (`test -f X && ! grep ...`,
  or a positive grep of a line known to be there), and the anchor must read the same
  subject. A recipe that is safe as a pair stops being safe the moment one half is
  reused alone. Run the recipe once against a deliberately wrong path before
  prescribing it.
- **Conditional skip.** A test that skips when its oracle, fixture or dependency is
  missing goes silent in the state most correlated with the defect — the oracle breaks
  while the oracle is being changed. Treat a conditional skip as an empty test unless
  the condition is proven unreachable in the environments the suite runs in. Separate
  "legitimately absent here" (skip, counted and printed) from "present and broken"
  (failure, never a skip). A suite whose external oracle is mandatory must **fail**
  when it is absent. Add a guard asserting the oracle actually loaded, so a fully
  skipped block fails loudly instead of disappearing into the skip count — nobody
  reads the skip count.
- **A guard neutralised in the arrange step.** To stay fast, tests write the sentinel
  value that makes a clock-based guard vacuous (`SET next_attempt_at = NULL` against
  `WHERE next_attempt_at IS NULL OR next_attempt_at <= now`). Every test that could
  exercise the constraint first disables it. Move the boundary instead of deleting it:
  set the timestamp into the past, or inject the clock. Add one test for the negative
  direction (timestamp in the future → not returned). Review tell: an arrange line that
  writes a null or a sentinel into the exact column a `WHERE` clause tests.
- **An ordering assertion standing in for a formula.** `d[0] < d[1] < d[2]` is true of
  every retry policy anyone would write, including the ones the exponential formula
  exists to avoid. An assertion admits every implementation it cannot distinguish; the
  question is how large that set is. Assert the values against the specification, or
  the ratio between consecutive terms. Give any cap its own test that drives the input
  past the bound — and check arithmetically that the bound is reachable at all: a cap
  first binding at attempt 7 under a limit of 5 attempts is dead code that reads as
  defence in depth.
- **A check discharged in prose.** A verification recorded as a sentence in a completion
  report ("checked at capture time: no empty titles") is, downstream, indistinguishable
  from a check that runs, and strictly more dangerous than an absent one. Extract every
  check a spec or a decision mandates and locate each one in the suite by name; "the
  producing task verified it manually" is a missing test, not coverage. The sharper a
  decision's diagnosis of why the normal oracle cannot see a failure, the more
  convincingly its prescribed remedy reads as already implemented — diagnosis and remedy
  are separate deliverables and only one leaves a running artefact behind.
- **A claim about a runtime, unchecked against the harness.** "This check is executable
  locally" is a claim about the runtime, not about the text of the check. A layout
  assertion in a DOM emulator that does not compute layout compares two zeros and goes
  green on every implementation, including a broken one. Every strategy item that names
  a test file must be checked for compatibility of the required API with that file's
  runtime (test environment from the config, dependency list, availability of layout,
  network, filesystem). And one check lives in one place: a duplicate in the weaker
  runtime will be presented as coverage.
- **A negative probe that never arrived.** Before reading the behaviour of a bad
  configuration, prove the bad configuration took effect: print the resolved value the
  system actually uses (the effective temp dir, the resolved path, the actual URL, the
  actual timeout). Between "I set the value" and "the system is running on that value"
  sits a normalisation layer that only shows itself in the unsuccessful path — which is
  where negative probes live entirely. An ignored setting produces a result identical in
  shape to the finding "the guard does not fire", i.e. exactly the finding a reviewer is
  hunting for and most willing to believe. Also: the bad configuration must be bad in
  exactly the **one** respect the guard checks, not in a second respect the library
  reacts to first.
- **Inherited state supplying the observed value.** A guard asserting that a component
  *adds* something (an environment variable for a child process, a header, a default)
  must first remove every other source of it, or it measures a union and attributes it
  to one term. Most dangerous when the second source is brought by the person testing:
  the environment of the run is part of the test and is invisible in the test's text, so
  it is green for the author and the reviewer and red only for the one participant who
  never had it.
- **An unfalsifiable absence test over clean-by-construction input.** "No personal data
  reaches the response", run over the canonical clean fixture, asserts a property of the
  fixture. When such a test turns out to be unfalsifiable, first ask whether the control
  it claims exists at all. If it does — feed it adversarial input and keep it. If it does
  **not**, do not invent the control to make the test meaningful: split it into (a) a
  canary honestly named as a property of the sample and (b) a test that *measures* the
  actual pass-through, green today and red the day someone adds filtering at this layer.
  Write the "who owns this guarantee" conclusion into the file the tests live in. A test
  that cannot fail carries information about the system, not about the property it names:
  very often the control was never built, and the test is the only place anyone recorded
  that it should have been.
- **A compensating measure with no oracle of its own.** When a known limitation is
  accepted and closed by a mitigation (a warning on every loss of signal, a fallback, a
  reconciliation pass), the mitigation is ordinary code and is the code least likely to
  have a guard — it is written while attention is on justifying the limitation. Review it
  as a function, not as a fact of presence, with an oracle per question: what
  distinguishes "fired for a real case" from "fired vacuously", and is that distinction
  pinned by a test (mutate the condition away); how many times will it fire over the life
  of one case (measure, do not estimate) and is there a ceiling; does it *restore* the
  loss or only report it — if only report, the artefact must be a monitored counter, not
  a log line, because logs are read after the incident.

---

## 3. Non-empty input and the traversal domain

**Rule: a check that walks something proves nothing about what the walk never reached.
State the domain, and prove the walk covered it.**

- **Non-empty input is a precondition, not a detail.** A query predicate, a filter, a
  comparison or a branch can only be observed with data on both sides of it. A test whose
  fixture inserts no rows returns the same result with and without the filter. Where a
  check's subject is a predicate, show that the arrangement supplies at least one value on
  each side; otherwise the honest verdict is "not exercised" — a finding about the test.
- **A declared set and a traversed set are two different sets.** A guard of the form "walk
  the produced artefact and check each element against a declared allow-list" is only as
  wide as their intersection. Close the loop in the other direction: **every declared entry
  must have been reached at least once by this run**, failing with the list of entries that
  were not. Paths produced only when the fixture contains an error row, an empty state, a
  second page, are declared and guarded by nothing. Free bonus: the reverse assertion also
  detects fixture drift.
- **Traverse the way the consumer traverses.** An "artefact contains no X" guard inherits
  the boundary of whatever walker it uses, and library authors place that boundary where
  cycles are cheapest to avoid, not where meaning ends. A standard recursive glob does not
  descend into symlinked directories; the consumer of the artefact (a subprocess, an image
  build, an archiver, a sync tool) does. So the guard is systematically blind to the exact
  construct through which foreign content arrives. Either walk with your own traversal that
  follows links (with a visited set of resolved paths), or forbid such links outright and
  make the prohibition the asserted property. A fast green over a large tree is evidence the
  tree was not walked.
- **Branches the corpus cannot reach.** For any fixture- or corpus-backed suite, enumerate
  the branches of the code under test and mark each "the corpus reaches this" or "the corpus
  does not". An error / miss / empty-value branch reached by no fixture is a finding, not a
  coverage gap — divergence between two implementations is cheapest exactly there, and a
  corpus captured from a working system never contains it, because the working system does
  not go there. Report the count: "0 of 36 fixtures reach this input" is a one-line scan and
  a finding.
- **Exemptions are a transfer of coverage.** Every declared comparison exemption
  (whitelisted path, order-insensitive key, tolerance window, "known-different" field) needs
  four answers: what remains verifiable about the field from a source the suite carries
  (usually recomputation from the test's own *input*, which is exact); whether the
  compensating oracle actually ships with the suite or lives behind an absolute path,
  a credential or a neighbouring checkout; an expiry that flips to a failure the day the
  cause is fixed; and a count of the strong contour's runs, not only the weak one's. An
  exemption written while the compensating oracle is demonstrably present is written at the
  moment its absence is hardest to imagine, and it converts somebody else's unfixed data
  defect into a green run — removing the only pressure that would have fixed it.

---

## 4. Differential oracles: name what is observed

A differential check asserts "change the input, and the output must change" (or the
inverse). It is powerful because it needs no knowledge of the implementation — and for
the same reason it is easy to satisfy by accident.

**Rule: the observed channel is named as a closed, justified list, and the consumer
decides which channel it is.**

- **Observe what the consumer consumes.** When a fact leaves a process by several channels
  — exit code, a line in a receipt file, a JSON field, a metric, a log — the test naturally
  attaches to the one that feels like the "real" result, while the automation that matters
  reads another. If the acceptance criterion is `grep -q "^survived: 0$" receipt`, then the
  test must assert that line, with the criterion's own regex copied, not paraphrased. Two
  independent expressions of the same predicate in one module is itself a finding: fix by
  collapsing them into one function, which makes the mutant impossible rather than merely
  detectable.
- **Assert the effect, not the text of the generated artefact.** For properties the output
  does not carry — query cost, cache use, batching, connection reuse — a substring assertion
  on the generated SQL is maximally sensitive to harmless renames and blind to the one edit
  that undoes the fix (`started_at >= ?` survives inside `(started_at >= ? OR 1=1)`). Find
  the layer that *consumes* the artefact — the planner, the scheduler, the cache — and read
  its interpretation; and capture the artefact from the real run, never retype it in the
  test body. Two review prompts: could this assertion be satisfied by a change that keeps
  the behaviour? Could it be defeated by a change that keeps the text? A text assertion
  answers yes to both.
- **Test hooks are not output.** An oracle comparing rendered markup measures the whole
  output, including traces of the test itself. `data-testid`, `class` and other
  instrumentation attributes never count as rendering: a test that credits them proves its
  own existence. An attribute counts as a carrier only with independent evidence that it
  does something (a style selector, verified separately). Otherwise the cheapest repair
  available to an executor seeing red is to add a carrier rather than the rendering.
- **When a leaf is credited, verify *what* moved.** The observed change may come from a
  sibling's fallback branch, from sorting, from a key, from a badge. Remove the presumed
  carrier and confirm the check reddens on *that* leaf. A field rendered twice cannot be
  killed by a differential mutation at all — the second site keeps moving.
- **A discriminator field with a closed value set is structurally invisible.** If the
  mutator produces a value outside the domain (appending a suffix to a string), and the
  consumer is a branch with a default case, the out-of-domain value lands in the default and
  the output is byte-identical. For a leaf carrying a closed token set, "a different value of
  the same type" must mean **a different member of the set**, and the mutator enumerates the
  domain. Symmetrically, a discriminator whose consumer has a default branch needs a separate
  test per domain value: the differential oracle cannot cover it by construction. Declare
  the class in the oracle rather than meeting instances one at a time and appending each to
  the exception list.
- **Structural comparison: union, and empty means silence.** A container's shape is the
  **union** over its elements, never one representative element; an empty container
  contributes only its own path, and is not a conflicting shape. Compare key paths plus
  container kind rather than scalar types wherever the contract permits nullable or widened
  values. Otherwise the guard's first failure is on a legitimate sparse sibling, it is
  indistinguishable from the drift the guard exists to catch, and the author loosens the
  guard instead of the sampling. Carry a positive control on the enumeration itself (the
  walk returned more than N paths) — a walker that silently returns nothing agrees with
  everything.
- **An exception list is enforced only where editing it changes an observable.** Adding a
  bogus exception moves the pinned counts; *removing* a legitimate one is a null edit by
  construction — the entry exists precisely because the property is absent there. So each
  exception needs a **carrier-free positive witness**: construct the arrangement in which
  every known alternative carrier is absent, perturb the excepted value, and assert the
  visible output is byte-identical. That test is green exactly while the exemption is true
  and turns red the day the field starts being rendered. Per entry, record *why* it is
  exempt and what observable would change if it stopped being exempt.

---

## 5. The double and the fixture are part of the oracle

**Rule: everything the test brings — doubles, fakes, fixtures, arrange steps, the entry
point it calls — is part of the oracle, and each carries assumptions nobody stated.**

- **A double must import, never retype, any parameter the subject also declares.** A fake
  written by reading the real thing and reproducing its parameters as literals makes the
  subject's declaration inert: the suite measures the fake's copy, the constant the reader
  would edit does nothing, and nothing distinguishes them. `FakeClient(page_size=module.PAGE_SIZE)`,
  not `FakeClient(page_size=50)`. Corollary sweep: mutate every module-level constant and
  confirm something fails — survivors are either dead code or unpinned policy, and both are
  findings even when today's behaviour is correct.
- **Do not arrange through the subject's own API when the production scenario is external
  mutation.** A test that changes the world by calling the subject's helper gives the subject
  the chance to stay consistent with itself, so caching, staleness and missed-invalidation
  defects are invisible by construction. Where production's story is "an operator touches a
  file", "another service writes a row", "a deploy replaces a config", "the clock advances",
  mutate by that same outside route — a separate process, a separate connection, the
  filesystem directly. Tell: arrange calls a method of the module under test and assert calls
  another method of the same module — that verifies internal consistency only.
- **Read the arrange block before the assertions, and ask of each line: does production reach
  this call with this already true?** An assertion and its setup carry opposite biases —
  strengthening the assertion makes the test more diagnostic about the thing asserted, while
  the setup required to make that assertion possible quietly substitutes the world in which
  the code already works. For any function whose job is to decorate, wire up or extend things
  that already exist, the setup must fabricate exactly the state whose absence is the failure
  mode. Any line that manufactures a precondition needs a sibling test that runs the call with
  that precondition absent.
- **Enter through the entry point production uses.** A test can be faithful about the world
  and unfaithful about the caller, and these feel like one axis. Effort spent making the
  environment honest (a subprocess, a cleared registry, a real socket) generates a strong
  intuition of completeness while the cheapest substitution remains: production never calls the
  function under test, it calls the thing that calls it. For anything whose job is to be
  *invoked at startup*, the wiring is the artefact and the function is the detail. Cheap
  universal backstop, no subprocess needed: one wiring test per entry point asserting the
  documented installers ran, so unwiring turns the suite red.
- **A transformation applied to test data for reasons outside testing is a change to every
  test's input.** Anonymisation, truncation, licence-scrubbing, size reduction: evaluate it
  against what the code *reads*, not against what the field is called. Identify the properties
  the logic keys on — counts of distinct values, lengths, prefixes, ordering, injectivity —
  and confirm the transformation preserves each. Two individually correct requirements can be
  jointly destructive, and they escape review precisely because they are owned by different
  reviewers, neither of whose checklists contains the other's concern. State the order
  explicitly (reference output derived from the transformed fixture, not before it), and add a
  self-check asserting every derived counter is equal over raw and transformed input.
- **An oracle and its input are two projections of one value.** If the input is transformed,
  the transformation must be applied to the pair, not to each side independently. A
  transformation that selects by *field name* commutes with a computation only while the
  computation does not rename, merge, sort or truncate — that is, never, if the computation
  does anything. The comparison report shows values, not their provenance, so a divergence
  caused by asymmetric preparation is indistinguishable from a real defect, and hypothesis-
  driven debugging goes looking for a bug the code does not contain. What separates the two
  classes in one step is a **second oracle run on the same transformed input**: if the
  reference implementation, fed the same input as the port, agrees with the port, the
  divergence was in the preparation.
- **Fixtures own resources wider than themselves — exactly one owner.** Two sibling fixtures
  that each "reset to a known state" a process-level cache, a singleton connection, a registry,
  an env var, or a fixed-path temp dir destroy each other's handles, and only when both run.
  Each one, read alone, does the correct and conventional thing. Make one the owner and have
  the other take it as a dependency. Debugging prompt: an error about a closed or invalid
  handle inside a test body, where the same test passes with one fixture removed, is a
  fixture-ownership conflict, not an arrangement bug.
- **A comparator written by the suite is untested code every assertion depends on.** A
  hand-rolled deep differ whose leaf branch is `if expected != actual` accepts `30` vs `30.0`
  and `0` vs `False` in languages where those compare equal — in the one comparison the whole
  acceptance criterion rests on. Reviewer attention flows to the structural traversal, where
  the visible effort is, and away from the leaf, where the decision happens. Check the type
  first (identity of type, not an `isinstance` that a bool-subclasses-int rule defeats), and
  give the comparator its own positive **and negative** cases: feed it a known difference and
  require that it reports one. Any helper a suite uses to decide whether two things are the
  same must be shown to report a difference it was given, not merely to stay silent on data
  that agrees.

---

## 6. Completeness is derived from the artefact, never from memory

**Rule: any check claiming to cover a whole surface derives the list of what it covers
from the artefact, programmatically, and asserts that the covered set equals it.**

A list written from recall inherits the author's model of the system, so its coverage is
**anti-correlated with risk**: what is easy to enumerate and easy to parametrise gets
covered, and what needs a fixture — the stateful, the wired-up, the rare — is quietly left
out. Then the guard is presented as full coverage of the deviation it justifies.

- **Derive the surface.** For a parity or vendoring guard, take the module's public surface
  programmatically (`__all__`, exported names, the route table, the schema's field list), and
  assert the covered set equals it. Deliberate exclusions go in an explicit skip list with a
  reason, so an exclusion is *visible* instead of absent. Make the surface-equality assertion
  itself a test: adding a function without a comparison then fails the suite.
- **Coverage of a lookup table is measured per row.** A parametrize list of three cases under
  a name that quantifies over the table ("expires by action type") pins the rows it names and
  nothing else, and the gap widens on its own as the table grows. Parametrize over the table
  itself with an assertion derived from each row's own value, or state which rows are
  deliberately unpinned. **False-completeness signature:** a programmatic test that every key
  exists, paired with a hand-written test of two keys' values — the first is what makes the
  second look exhaustive, because completeness of the *keys* is routinely mistaken for
  completeness of the *values*.
- **Size is the proxy; composition is the property.** A corpus guard that counts fixtures
  (even from three independent sources) still passes a corpus of N identical copies of one
  record. Assert the *shape* the capture step recorded — the per-category breakdown — plus
  behavioural floors ("at least N fixtures reach branch X") measured from the current corpus
  with margin. Ask which corpus events the guard distinguishes: deletion-after-capture leaves
  counts inconsistent and is caught; re-capture-with-different-selection keeps every count
  consistent by construction and is the event that actually happens. Where the producing step
  records structure the guard does not read, that is itself the finding.
- **Enumerate at the granularity of the smallest independently breakable decision.** A regex,
  a format string, a SQL predicate, a schema literal is not an atom: it is a small program
  whose anchors, quantifier bounds, character classes and alternation branches are independent
  decisions. An enumeration whose unit is coarser than that looks exhaustive and silently
  samples. Publish the walked list — each unit marked "covered" or "deliberately skipped +
  reason" — rather than a sentence claiming completeness; a completeness claim without the
  list cannot be audited, and a gap should appear as a missing row, not as a reviewer's lucky
  guess.
- **Sibling asymmetry is a free, pre-computed list of gaps.** Where a codebase implements the
  same kind of check more than once, whatever one sibling asserts and another does not is a
  candidate gap — visible from test names alone, cheaper than re-deriving the risk model, and
  not inheriting the blind spot that produced the omission. Concretely for numeric thresholds:
  a comparison is pinned only when **both** sides are asserted (the value exactly on the
  allowed edge passes, the next value is rejected); asserting only the rejecting side leaves
  the comparison's direction free.
- **A stated scope boundary is checked against the artefact, not against its rationale.**
  When a receipt or a test declares a class of checks out of scope, the cheapest check is
  whether the artefact's own tests already close that class somewhere. A class closed in one
  place and open in its twin is not out of scope — it is unevenly covered, and the limitations
  section is describing something other than what the code does.

---

## Review checklist

For each check offered as evidence:

1. **Provenance.** Where did the expected value come from, and does that source move when
   the code moves? (§1)
2. **Red run.** Has it been observed red for the reason it exists? Is the criterion red on
   the starting revision? (§2)
3. **Instrument failure.** Does any failure of the tooling (bad path, missing oracle,
   skipped test, absent fixture row, empty walk) render as a pass? (§2, §3)
4. **Domain.** What does the check traverse, what does it declare, and is the declared set
   proven to be reached? (§3)
5. **Channel.** Is the observed channel the one a consumer actually reads, and is the set of
   accepted carriers a closed, justified list? (§4)
6. **The test's own contributions.** Doubles, fixtures, arrange steps, the entry point,
   comparators — which of them supplies the value being asserted? (§5)
7. **Completeness.** Is the covered list derived from the artefact or from memory, and at
   what granularity? (§6)

A finding names which of the seven failed and includes the concrete replacement, not a
description of the problem.
