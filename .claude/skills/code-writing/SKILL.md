---
name: code-writing
description: |
  Universal quality coding process: plan, TDD, reviews.
  Use whenever code needs to be written — ad-hoc or as part of a task.

  Use when: "напиши код", "закодь", "реализуй", "write code", "implement"

  Do NOT use for pure layout from Figma, Claude Design, screenshots, or an existing visual
  style ("сверстай", "подвинь блок", responsive) — use layout-writing instead.
  Direct mixed layout + business-logic work uses both layout-writing and code-writing.

  For planning tasks → tech-spec-planning skill. For specs → user-spec-planning skill.
---

# Code Writing

## Phase 1: Preparation

1. **Parse Requirements**
   - Extract what needs to be built from user message or passed acceptance criteria
   - Clarify ambiguities — ask user if unclear
   - Formulate acceptance criteria (what "done" looks like)
   - **Substitute the task's own constants into the task's own constraint, before planning.**
     An input that states both a rule and the values it governs contains a checkable claim, and
     that claim is false more often than it looks — the author holds the rule in words and the
     constant in code. One minute now; after the check is written and tested it becomes a choice
     between building something unworkable and deviating from the brief silently
   - **A literal carried over from a spec brings the semantics of whatever language it lands in**
     (glob, regex, SQL, shell, a separator inside a composite key). The crossing is a conversion
     with its own correctness question — escape it in code, not in your head. And a separator is
     an unwritten claim about the alphabet of the parts: verify it against a value from the real
     producer, not against a literal from the same head that wrote the template

2. **Read Project Context (Graceful)**

   **Working on a task?** Read all files listed in the task's "Context" section — it already specifies everything needed.

   **Standalone (no task file)?** Read (skip if missing):
   - `.claude/skills/project-knowledge/references/project.md` — project overview
   - `.claude/skills/project-knowledge/references/architecture.md` — system structure
   - `.claude/skills/project-knowledge/references/patterns.md` — project conventions

   Then read `.claude/skills/project-knowledge/SKILL.md` (if exists).
   Consider which domain-specific guides are relevant to your task and read those
   (e.g., `architecture.md` Data Model section for DB work, `ux-guidelines.md` for UI tasks).

   **No project patterns?** Apply baseline from [universal-patterns.md](references/universal-patterns.md) — naming, error handling, structure.

3. **Analyze & Review Approach**

   Before coding, output your findings:
   - Grep for usages of code to be modified
   - **The other direction: whose default am I inheriting?** For every limit, timeout, page size,
     retry count or constant you take without passing it, find where it was defined and for whom.
     A loop bound answering "when to stop searching" is not a product limit; the next caller
     inherits that wrong answer invisibly, because an argument not passed leaves no trace in the
     diff, and a truncated list is indistinguishable from a short one
   - **If the code filters by a set of values** (whitelist, status enum, allowed types, a sweep's
     "what belongs here") — grep every writer of that field and list them. The set alone is a claim
     about intent; only its intersection with the writers is a claim about behaviour. Adding a new
     writer to a shared store is always two changes: the write, and registering its shape with
     whoever cleans the store up
   - **For every field crossing a module boundary, pin both axes: form and reference frame.** Form
     is type, shape and units; reference frame is timezone, currency, base, origin, encoding. A
     contract that fixes only the form leaves both sides formally correct with different meanings,
     and a fixture where every value shares one reference frame proves self-consistency, never
     agreement. Put at least one example with a different reference frame into the corpus
   - Read all files that will be changed
   - Verify solution follows project patterns (or universal patterns)
   - Identify existing code that can be reused
   - If modifying existing code, run existing tests for the area to establish baseline
   - **Editing by text anchor?** The anchor names a line; the thing you intend to act on is a unit,
     and a unit's boundary usually sits above its most distinctive line (docblock, decorator,
     annotation). Where the two disagree the edit lands inside another construct and everything
     mechanical still passes — check that the seam reads correctly, not just that the edit applied

   If concerns → discuss with user before proceeding.

**Checkpoint:** List completed preparation steps before moving to implementation.

## Phase 2: Implementation (TDD)

1. **Write Tests First**

   **Before writing tests**, read [testing-guide.md](references/testing-guide.md) — when to write which test type, test structure.

   - Write tests for: business logic, validations, transforms, error handling. Skip trivial code without logic (simple getters, one-liners, configs)
   - Write tests for requirements and edge cases
   - Tests should fail initially (no implementation yet)
   - One test = one scenario, test behavior not implementation
   - If mocking >3 dependencies → wrong test type, use integration test

2. **Critique Tests** (before writing code)

   Spawn a fresh `test-reviewer` in `design` mode. No implementation exists yet, so it
   attacks test design (behavior-not-implementation, edge/error coverage, meaningful
   assertions, right test type) rather than the litmus test, which needs running code.
   Pass: paths to the test files you wrote + acceptance criteria.
   Report path: `logs/working/task-{N}/test-reviewer-design-{round}.json`
   (`{N}` = task number, `"standalone"` if no task file). This phase's 2-round cap is
   independent of the Phase 3 code-review cap — each critic phase gets its own two rounds.

   Process findings by the Phase 3 "Process Findings" rules (in-scope fix / disagree →
   discuss / out-of-scope → surface to user). Strengthen the tests, then spawn a **new**
   `test-reviewer` for the next round — a fresh instance, not the same one.
   Limit: 2 rounds. If in-scope findings remain after round 2 → ask the user before
   writing code. Reason: catching a hollow test now is cheaper than discovering after
   the code is built that the tests never protected it.

3. **Write Code**
   - Implement to pass tests
   - Follow project patterns (from Phase 1) or apply baseline from [universal-patterns.md](references/universal-patterns.md)
   - Use env vars for secrets, validate inputs at boundaries
   - Handle edge cases, comment WHY not WHAT

4. **Run Tests**
   - All new tests pass
   - Fix any failures

**Checkpoint:** List implemented functionality and test results.

## Phase 3: Post-work

1. **Run Lint/Format**
   - Run project's linter and formatter before reviews

2. **Run Relevant Tests**
   - Tests for files changed
   - Tests mentioned in task (if applicable)
   - Save full test suite for end of feature

3. **Smoke Verification** (if task has Verification Steps → Smoke or User)

   Execute each command from the Smoke section. Record results in decisions.md Verification section.
   If a check fails — fix the code before proceeding to reviews.
   If the task has User checks — ask the user to verify, wait for confirmation.

   Smoke catches integration bugs that mocked tests miss:
   real API responses, library initialization, config validity.

   **Measure the outcome, not the nearest link.** The fix lands in one link of the chain while the
   promise is about the end result, and the link nearest the change always improves more than the
   outcome does. Replay real cases end to end and count how many still reproduce; name the remainder
   out loud — it is the honest boundary of the fix, and unnamed it makes the next occurrence read as
   a regression of an already "closed" class. Two numbers side by side (a total and its breakdown)
   assert a third thing nobody checked — that the second explains the first: verify they are computed
   over the same population.

4. **Prod Gate** (level L1+ only; skip for L0 prototypes)

   Before spawning reviewers, self-check the change against `ENGINEERING.md` §2 and the
   triggered blocks of `.claude/skills/prod-review/production-checklist.md` (read only the
   blocks the diff triggers, never the whole file). Minimum:
   - external calls have timeouts; retries bounded, with backoff+jitter, only on network/5xx/429
   - any write with a side effect (CRM record or task, message to a client, payment) is idempotent —
     a repeat run creates no duplicate
   - webhook handlers dedupe by event id; cron/loops hold a lock against parallel runs
   - transition state lives in DB/file, not in process memory
   - no secrets or PII in logs; no empty `except: pass`
   - answered: which metric/log/alert shows this feature broke, before the user notices

   Fix gaps now — a reviewer finding is more expensive than a self-check. If a gap is deliberate,
   record it in the "Отложено" line of the closing block below.

5. **Run Review Lenses** (launch all in one turn)

   Lens set — the size rule of `ENGINEERING.md` §1a, not the reviewer's role:
   - Working on a task file → `reviewers` of the card: `[quick]` → quick; `[thorough]`, `[]` or a
     legacy role list → thorough; `[none]` → no review.
   - Standalone (no task file) → quick when the change is ≤100 lines in ≤5 files with no external
     write, else thorough. When in doubt — thorough.

   Catalog, prompts and envelope: `.claude/shared/review-lenses/README.md`. Protocol:
   1. Write the unified diff of this change (from the card's `start_commit`, or from the first edit
      when standalone; untracked files included) to `<scratchpad>/review-{N}/diff.patch`. Lenses read
      it by path; the diff is never pasted into a prompt.
   2. Launch every lens of the set as a context-free subagent (`general-purpose`, `model: "sonnet"`;
      `security` → `subagent_type: "security-auditor"`) in the same turn, `run_in_background: false`,
      with `{diff_file}`, `{card}`, `{report}` = `logs/working/task-{N}/{lens}-1.json`
      (`{N}` = task number, `"standalone"` without a task file) and, for `intent-alignment`, the
      verbatim `## Intent`. Key names in the envelope are quoted from `.claude/scripts/taskflow.py`;
      do not paraphrase them. Read no report before all lenses are launched.
   3. **Record the state that was reviewed**: the commit sha, or a hash per file for an uncommitted
      tree. A review is a statement about a specific state of an artefact, and every tool a reviewer
      uses reports the *current* state while none reports *which* state — so the identity of what was
      judged is the one input to the verdict that is otherwise never written down. **Invalidate on the
      reviewed paths, not on HEAD.**

   Blind review: a lens gets the diff, the card and the specs by path — never your implementation
   narrative, decisions.md or an earlier report.

6. **Triage Findings**

   By `.claude/shared/review-lenses/triage.md`: verify every finding in code yourself, grade it
   (`high / medium / low / false / maybe-false`) with evidence, group by root cause, route
   `patch / ask / defer`. Lens severities are not read — severity is yours to give after checking.
   Every finding gets a row in the card's `## Review Triage Log` (standalone: in your reply):

   | # | Lens | file:line | Verdict | Evidence | Scope measured | Route |

   **Scope measured** is the region the fix actually reaches, obtained by enumeration, not intent.
   A fix has two scopes — the mechanism it changes and the instances that motivated it — and they
   coincide only by accident: you reason from the instances, because those are what the investigation
   surfaced, while the mechanism's reach is a question nobody asked. Write the enumeration (sites
   found, branches of the classifier covered, carriers the pattern can inhabit) or write literally
   "N not measured". Never pair a verb of widening ("hardened all callers", "applied everywhere")
   with the small count of motivating examples — each half is correct alone and the reader cannot
   see that they disagree. Check too that any proof obligation attached to the fix is not also a
   filter that silently excludes part of the finding.

   `patch` → fix now, re-run tests and the card's verification. `ask` → one message to the user
   with the question and options; do not guess. `defer` → `deferred-work.md` next to the card
   (standalone: name it in the closing block). Limit: **2 patch cycles**; a lens is not re-run
   after a patch — you verified the finding and the fix yourself, and the verification commands
   ran again. Then close in the findings mechanism: `findings-sync.py`, `{lens}-2.json` with
   `closures[]` per fingerprint (`closed` with evidence; `open` only for `ask`), `findings-sync.py`
   again — see the README's "Закрытие лидом".

7. **Closing Block** (level L1+)

   End the task with exactly three lines (`ENGINEERING.md` §6.5):

   ```
   Риски: <что сломается под нагрузкой или при частичном отказе внешнего API>
   Отложено: <что осознанно не сделано и на каком уровне понадобится>
   Наблюдаемость: <какая метрика / лог / алерт покажет поломку>
   ```

   No risks — say so explicitly. More than three lines — trim.

**Checkpoint:** List post-work steps completed.

## Self-Verification

Verify each item before marking complete. If any item fails, return to the relevant phase.

- [ ] All phases completed (Preparation, Implementation, Post-work)
- [ ] Tests pass
- [ ] Smoke verification executed (if task had Smoke/User checks)
- [ ] Prod Gate self-check done (L1+)
- [ ] Closing block «Риски / Отложено / Наблюдаемость» written (L1+)
- [ ] Every lens finding verified in code, graded and logged in the Triage Log
- [ ] Findings log table produced, with the measured scope of each fix (or "N not measured")
- [ ] Reviewed artefact state recorded, and re-checked on the reviewed paths before accepting a verdict
- [ ] Review JSON reports saved to `logs/working/task-{N}/`

