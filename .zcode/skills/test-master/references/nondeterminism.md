# Nondeterminism

How to test properties whose observation is a draw rather than a value: races, locks,
retries under contention, timeouts, throughput, anything keyed on the clock, and anything
whose result depends on state the test did not set.

The single idea: **a check whose outcome is a random variable reports the draw, not the
distribution — and a deterministic check and a one-draw sample look identical at the call
site.** Both are a command with an exit code. Every mechanism around them — an acceptance
checkbox, a verification step, a reviewer reading a report — treats them the same way.

## Table of contents

- [1. Sample size belongs in the criterion](#1-sample-size-belongs-in-the-criterion)
- [2. Repetition belongs inside the detector](#2-repetition-belongs-inside-the-detector)
- [3. Scope: which layer serialises the callers](#3-scope-which-layer-serialises-the-callers)
- [4. Nested and layered guards](#4-nested-and-layered-guards)
- [5. Clocks, zones and any moving zero](#5-clocks-zones-and-any-moving-zero)
- [6. Fixture and resource scopes](#6-fixture-and-resource-scopes)
- [7. Performance assertions have three parts](#7-performance-assertions-have-three-parts)
- [8. Sample size as resolving power](#8-sample-size-as-resolving-power)

---

## 1. Sample size belongs in the criterion

**Rule: any acceptance criterion whose subject is nondeterministic states its repetition
count; otherwise the default sample size is one, chosen by nobody, and the artefact
records the luckiest draw.**

Write `probe --concurrent 2 passes 20 consecutive runs`, never `probe --concurrent 2
passes`. The criterion is what the implementer and every later reviewer read, and "ran it
once and it printed OK" is not something anyone can re-check.

The criterion also names the **environment**, because the verdict is a function of ambient
machine load. The same probe has produced 1 pass in 5 on a busy machine and 75 in 75 on an
idle one, with no change to the code. A developer laptop is the idle case; a server running
a dozen processes on one disk is the loaded case — so a criterion verified where it is least
able to falsify itself is discharged by the quietest machine in the pipeline, which is the
one where the race cannot occur.

Inverse rule for reviewers: **a concurrency finding is neither accepted nor dismissed on one
run.** Re-run several times and state the run count in the finding.

---

## 2. Repetition belongs inside the detector

**Rule: the probe takes a repetition count, defaults it above one, and reports the failure
**rate**, not a boolean.** A probe that can only answer yes/no on one draw is
under-specified, and leaving the repetition to whoever runs it means it is not repeated.

And: **the detector lives inside the command the suite actually runs.** A probe sitting
beside the test suite is not covered by "all tests pass", so its red state can coexist
indefinitely with a green suite.

---

## 3. Scope: which layer serialises the callers

**Rule: before writing a concurrency test, name the scope the guard defends — threads in one
process / processes on one host / hosts on one datastore — and write the test at THAT scope.**

A test can only observe contention its own callers are able to create. Any serialising layer
between the test and the property converts the test into a measurement of that layer. If the
method under test takes a process-local lock around its whole body, an in-process test of
that method's atomicity is a test of the lock, and the datastore-level guarantee needs
callers the lock does not span.

The mismatch is systematic, not occasional, because the **cost gradient guarantees it**:
threads are the cheap concurrency (same interpreter, shared objects, an assertion collected
in a list), processes need a spawned script, a synchronised start and result marshalling. The
cheaper scope is always the inner one, and the guard that matters in production is always the
outer one, because production is where the extra processes live.

- Name the scope **in the test's name** — `..._across_processes`, not `..._is_atomic`. A name
  that asserts the property rather than the scope is what makes the gap invisible afterwards.
- Let the deployment shape decide: if the process manager can ever run two instances at once
  — a restart overlap counts — the cross-process scope *is* the production scope, and a
  thread-only suite verifies a configuration that never runs.
- Settle the question by mutation: remove the wide-scope guard and re-run. If the suite stays
  green, the guarantee is untested however real the concurrency in the test looks.

---

## 4. Nested and layered guards

Redundancy and testability pull in opposite directions on the same assertion. Every layer
added to make the outcome robust makes the outcome less informative about any one layer — so
an end-state assertion over a redundant control approaches zero diagnostic value exactly as
the control approaches its design goal, and it keeps returning green while layers die one by
one, until the last one dies loudly and the incident report says the control was tested.

**Rule: each layer needs a test that exercises the hazard with the other layers disabled or
absent, so the pass is attributable to that layer alone.**

- Keep the all-layers-on test as an integration check, labelled as such, and never as the only
  test.
- Where a layer's job is to *attach* something (a filter, a hook, a middleware), the cheapest
  per-layer test asserts the **attachment** directly — the filter is present on the handler
  after the call — rather than the downstream effect any layer could have produced.
- **Nested** guards are worse than peer guards: the inner one is present in every test the
  author will naturally write. Disable it for the test, or drive the outer scope directly.
- Review-side rule: when a test is offered as evidence that a control works, check whether its
  pass is **attributable**. A control described as layered whose only test enables every layer
  is untested per layer — that is the finding, not "the control is covered".

(Attribution answers "which layer produced this pass"; it says nothing about "does this layer
ever run with these inputs". Both questions must be asked — see
[proving-a-check.md](proving-a-check.md) §5 on setup and entry-point fidelity.)

---

## 5. Clocks, zones and any moving zero

**Rule: a test that pins a moment must pin it for BOTH sides — the data and the code under
test.**

If the fixture seeds relative to a literal `NOW` while the code reads the system clock —
through a subprocess, an HTTP call, a SQL `now()` — the two agree on the day the test is
written and diverge silently afterwards. The break arrives with a delay, and it lands on
whichever test was added most recently, which is typically the guard added in response to an
audit finding, i.e. the load-bearing one. A permanently red suite then devalues every other
test in it ("oh, that's the known failure"), and on a red suite a mutant is indistinguishable
from the base state — so the guard that was the last line of defence stops defending at
exactly the moment it starts failing.

- The code under test must receive that same moment through an explicit channel: a function
  argument, a `--now` flag, an injectable clock.
- Run the suite once with the system date shifted (or schedule a nightly run) — that is the
  only cheap way to find date dependence at the author rather than a day later.
- The same applies to every moving zero the code can reach behind the test's back: clock, time
  zone, locale, today's date, an exchange rate, a default that resolves at call time. A green
  run under any of them is a statement about the day it ran.
- A guard added because of a finding is now load-bearing code and gets the same robustness
  scrutiny as production code.

**Do not make a clock-based guard vacuous in order to run fast** — move the boundary rather
than deleting it. See [proving-a-check.md](proving-a-check.md) §2.

---

## 6. Fixture and resource scopes

**Rule: for any resource whose lifetime is wider than one test — a module-level cache, a
singleton connection, a registry, an environment variable, a temp directory at a fixed path —
exactly one initialiser may exist; everyone else takes it as a dependency.**

Setup code is written and read one fixture at a time but executes in combinations. Two sibling
fixtures that each "reset to a known state" the same process-global destroy each other's
handles, and only when both are requested — a combination nobody tried. Each participant is
individually correct: cleaning up after yourself is the rule, and it is precisely that
diligence that invalidates the other's still-live handle.

- Review prompt when adding a fixture: does any existing fixture already touch this global? If
  so, depend, do not duplicate.
- Debugging prompt: an error about a closed or invalid handle inside a test body, where the
  same test passes with one fixture removed, is a fixture-ownership conflict, not an
  arrangement bug — look at what else resets that resource before investigating the resource.
- Inherited process state (environment variables, cwd, umask, module globals, on-disk caches)
  is a source the test did not declare. A guard asserting that a component *adds* one of them
  must first clear every other source of it.

---

## 7. Performance assertions have three parts

**Rule: a performance assertion consists of a measured quantity, a workload and a ceiling, and
all three must be consistent with each other.**

A ceiling derived honestly from the operational cycle (a timer every five minutes, a known
incident at 281 seconds → a 30-second budget) and a workload derived from whatever the test can
build in a second come from different worlds. Their product is a margin inside which the defect
is invisible: a mutation removing a time window or an index-narrowing predicate stayed inside
the budget by a factor of 200–600, so the budget test passes on exactly the code the criterion
feared. Tightening the ceiling until it is sensitive does not fix it — that turns the test into
an assertion about the speed of the machine.

- Before treating a time budget as closing a criterion, **run a mutation that makes the work
  demonstrably more expensive and look at the margin.** More than ~10× margin means time is not
  the instrument.
- Then measure the **work**, not its consequence: engine step counters, a query plan, rows
  read, number of requests, call counts. A work counter is deterministic, independent of
  hardware, and therefore admits a tight ceiling.
- Keep both assertions side by side and label which question each answers ("it finishes in
  time" vs "it does the work the right way").
- Beware inert performance mutants: an optimiser may undo the change (a correlated subquery
  rewritten back into a join), so the mutant survives and falsely accuses the test. Prove
  non-inertness in the work counter, not in the wall clock.
- Do not phrase an acceptance criterion as "fits within the time budget" when the implementer
  chooses the fixture size — it is then satisfied by any implementation.

---

## 8. Sample size as resolving power

**Rule: a property about *when* something happens inside a repetition needs an input of at
least two elements, and an assertion that distinguishes the timing.**

"Do this after **each** element", "flush at least every N", "stop at the first divergence",
"do not exceed this rate" — these are statements about a moment inside a loop, and a moment
does not exist in a sample of one. On one element, "check after each" and "check once at the
end" are byte-identical results, so the mutant moving the check to the end survives the whole
suite.

The trap is reinforced by convenience: `--only`, `--first`, `--limit 1` make a test fast,
deterministic and readable — which is what good engineering looks like — while collapsing the
loop into a single iteration and, with it, every property about order and periodicity.

The distinguishing assertion is about the **second** element: that it was not processed, or was
processed later, or at a different rate. Concretely — a processed counter in the artefact
(`checked: 1` with two supplied) for early exit, a record count on the medium for flushing,
timestamps for rate limiting.

**Deduplication and idempotency windows have two axes, and coverage needs both.** A dedup
suite naturally varies only the number of times the trigger fired; the defect lives in
*differences*. Required trio: (1) one event, N firings → one record; (2) **two distinct events
inside the window → two records**; (3) both sides of the window boundary (T−ε and T+ε), not
only the outer one. A set that varies only multiplicity proves suppression of repeats and says
nothing about what counts as a repeat. Reading tell: if the collapse discriminator is the row's
*insertion* time while the thing to distinguish is events, and the event carries its own
timestamp, key on that instead. And when a window is borrowed from an existing constant to
"avoid introducing a third notion of time", ask what question that constant answered before —
a borrowed constant silently carries its old definition of sameness into the new place.
