---
name: task-decomposition
description: |
  Decompose approved tech-spec into atomic task files with parallel creation and validation.

  Use when: "разбей на задачи", "декомпозиция", "decompose tech-spec",
  "создай задачи из техспека", "/decompose-tech-spec"
---

# Task Decomposition

Decompose tech-spec Implementation Tasks into individual task files with parallel creation and validation.

**Input:** `work/{feature}/tech-spec.md` (status: approved)
**Output:** `work/{feature}/tasks/*.md` (validated)
**Language:** Task files in English, communication in Russian

## Claims discipline

Applies to every phase, every agent and this orchestrator itself.

**A number derived from an earlier task's output is recomputed at drafting time, never copied
from the tech-spec.** When a card's arithmetic takes a count produced by an earlier task
("19 existing + N new = 22"), state the formula and its inputs symbolically in the card, and
re-derive the total from that task's *actual code* before any literal is written into a
command. A tech-spec section is a forecast of what the earlier task would build, not a record
of what it built, and the gap is silent: the wrong total gets baked into a new executable
oracle — a smoke-test literal — which then looks like a rigorous check while asserting against
a wrong constant. Telling the card's own executor to "recount from the source before writing"
does not help, because the wrong number has already reached the card's literal by then; the
re-derivation belongs to whoever drafts the card.

A task card states facts about the world: a file path, a line number, a test node id, a
function signature, a task number, what a sibling card owns, what a script does in its edge
case, "nobody else touches this file". **Every such claim is verified against the primary
source at the moment it is written, and re-verified at the moment it is handed over** — a
brief, a validator finding, a fix-mode instruction and an earlier measurement of your own are
all retellings, not sources. Three shapes that look verified and are not:

- a negative existence claim ("no other task creates this") — self-confirming, refuted only by
  a `grep` across all sibling cards, never by the tech-spec field the cards are known to extend;
- a claim you were told not to touch ("already fixed in both") — the one instruction exempt from
  the checking that carrying out an instruction would otherwise give it; honour the "don't
  touch", verify and report the "it is already like this" separately;
- a rationale that argues against its own source ("the spec says X, we do Y because…") — a fix to
  the source falsifies it while leaving the conclusion correct, so no correctness check catches it.

A claim that cannot be re-verified at handoff time is phrased with the time of observation
attached. Mechanics for the authoring agent: `task-creator.md` → "Claims discipline".

## Phase 1: Create Tasks

1. Ask user for feature name if not provided.

2. Read `work/{feature}/tech-spec.md`. Check frontmatter `status: approved`.
   If not approved — tell user: "tech-spec не утверждён. Сначала запусти `/new-tech-spec` и доведи до approved." Stop.

3. Read `work/{feature}/user-spec.md`.

4. Note the task template path: `.claude/shared/work-templates/tasks/task.md.template (fallback: ~/.claude/shared/work-templates/tasks/task.md.template)`

5. Read skills/reviewers catalog from [skills-and-reviewers.md](.claude/skills/tech-spec-planning/references/skills-and-reviewers.md) (fallback: `~/.claude/skills/tech-spec-planning/references/skills-and-reviewers.md`) — for passing correct skills/reviewers to task-creators.

5a. **Assign executor for each task** using the Executor Assignment rules in skills-and-reviewers.md.
    For each task determine `executor` (opus | sonnet | codex | antigravity) based on:
    - skill type (prompt-master → opus, code-writing S → codex, etc.)
    - files count (10+ files → antigravity)
    - task complexity (L + design-heavy → opus)
    Present the assignment table to the user before creating tasks:

    ```
    Task 1: Create DB schema          skill=code-writing S  → codex
    Task 2: Implement API endpoints   skill=code-writing M  → sonnet
    Task 3: Write system prompt       skill=prompt-master   → opus
    Task 4: Migrate 15 config files   10+ files             → antigravity
    ```

    Ask user to confirm or adjust. User may override any assignment.

5b. **Skill-copy drift check (once per skill per batch, not once per card).** For every skill
    that will appear in any task's `skills`, compare the personal copy `~/.claude/skills/<name>/`
    with the project copy `.claude/skills/<name>/` (`diff -rq`, or `.claude/scripts/check-setup.sh`).
    The personal copy is what actually loads and silently overrides the project one — an executor
    opening one card cannot tell a shorter version was substituted. Differences: state them to the
    user and put the resolved path into every card of the batch. Applying this per card produces
    cards that disagree about the same risk, which is indistinguishable downstream from no card
    catching it.

6. For each task in Implementation Tasks — launch [`task-creator`](.claude/agents/task-creator.md) (fallback: `~/.claude/agents/task-creator.md`) subagent in parallel.
   Pass each task-creator:
   - feature_path, task_number, task_name
   - template_path: `.claude/shared/work-templates/tasks/task.md.template (fallback: ~/.claude/shared/work-templates/tasks/task.md.template)`
   - files_to_modify, files_to_read (from tech-spec) — they become frontmatter `owns_paths` / `reads` verbatim; the executor may write only inside `owns_paths`
   - depends_on, wave, skills, reviewers, verify (from tech-spec)
   - executor (determined in step 5a)
   - teammate_name (if specified in tech-spec, optional)
   Each task-creator copies the template to `tasks/{N}.md` first, then edits each section in place. This ensures no sections are skipped.

   **`owns_paths` is derived from consequences, not from intent.** The tech-spec's Files-to-modify
   is the author's statement of what they mean to edit; what breaks is whatever stops being true.
   Before freezing a task's `owns_paths`, extend it by four traversals — each one grep, each one
   cheap at this point and expensive at the first red run:
   - every caller of a signature the task changes (`grep` the symbol repo-wide);
   - every closed list that enumerates the task's output (schema, enum, allow-list, status set,
     fixture registry) — owning the producer and not its gatekeeper is a two-place edit split in one;
   - test scaffolding of anything moved: fixtures and conftest are invisible in the production
     import graph and are what reattaches moved code to the place it was leaving;
   - the task's **declared non-happy path**: what it is told to do when its own check fails. A
     verifying task owns the instrument, not the subject — if the spec tells it to fix the subject,
     that is a contradiction inside one card, resolved by ownership or by wave, never by prose.
   A narrowing of a shared contract (removing a field, a status, a parameter) is global by
   construction: the task must own every consumer of the removed thing, or the removal moves to a
   later wave. Task that narrows + promises compatibility + does not own the data = contradiction.

   **When the task's only deliverable is a report, `owns_paths` is legitimately empty and
   `produces:` is not.** The artefact's address is then fully determined by the executing skill's
   own convention — resolve it and write it down; a consumer card must cite it by path, never by
   description. The producer's declaration is the authoritative source of that name; a convention
   is a fallback only while the producer's card does not yet exist.

   **Prod-readiness rows need a named owner.** Traverse the tech-spec's Prod-readiness table (not
   the task list) and name, for each row, the task that discharges it. Rows about the running
   system — rollback plan, kill switch, state preservation, alert wiring — have no code artefact
   and are therefore invisible to every traversal that starts from tasks; a producer/consumer pair
   split across two cards satisfies neither card's own checklist. A row with no owner is a finding.

7. Confirm each task-creator returned a file path. Skip reading task content — preserve context
   budget for validation phase. **Recorded trade-off (do not re-litigate):** the executable checks
   on a card's own verification commands (`bash -n`, unresolved `{placeholders}`, scope inside
   `owns_paths`) belong to the card's author and run inside `task-creator` at authoring time, not
   here. The author has the card open anyway; the orchestrator would have to re-read every file.
   Mirror of this note: `task-creator.md` → "Verification Steps are executable code".

7a. **Wave collision check runs here, not only at the end of Phase 2.** Run
    `python3 .claude/scripts/wave-check.py work/{feature}` yourself (Bash) as soon as the cards
    exist: a same-wave collision is cheapest to fix before validation spends three rounds on cards
    that will be re-cut anyway, and per-card authoring is structurally the wrong altitude to see it.
    The write-set it must be checked against is wider than `owns_paths`:
    - what a card's **verification commands execute** (a test run that rewrites a shared fixture, a
      build that regenerates a lockfile) — isolation proven for files is not isolation for processes;
    - a file that a card's prose claims to modify while `owns_paths` omits it — a collision that
      lives only in the prose is invisible to the script by construction, so grep the prose too.
    Tasks reported as `skipped_no_owns_paths` are not "ok". Exit 1 → fix mode, re-run until exit 0.

7b. **Acceptance criteria rules** — apply to every card before the draft commit:
    - criterion about an EFFECT checkable now, never about an ACT ("the rule was added", "the
      commit came first"): an act is unverifiable once the artefact exists, and it fails in the
      harmless case, which is why review never notices;
    - scope of measurement ≤ scope of ownership. An aggregate criterion over a shared artefact
      ("the whole suite is green", `git diff HEAD` is empty) inherits other people's work: it goes
      red from their unfinished work and green from their finished work, and the second half is
      silent. Such a criterion belongs to whoever owns the whole scope;
    - a criterion naming an internal state produced by another task carries that task's number —
      a predecessor's merge can make it unreachable, and a test written to it then passes by
      asserting nothing;
    - a criterion of the form "this task did not modify X" is a claim about the delta from the
      start of the work, which `git diff HEAD` cannot express. Such process-level criteria belong
      to the mechanism that holds the baseline; the card keeps criteria about its result.

8. Git commit: `draft(tasks): create {N} tasks from tech-spec for {feature}`

**Checkpoint:**
- [ ] All `tasks/*.md` files created
- [ ] Each task-creator returned file path
- [ ] Skill-copy drift checked once per skill (step 5b)
- [ ] `wave-check.py` exits 0, no `skipped_no_owns_paths`
- [ ] Every Prod-readiness row has a named owner task
- [ ] Draft committed

## Phase 2: Validation (one full round; critical-only re-run)

Tech-spec was already validated by 5 validators. This phase checks only: (1) task-creator correctly expanded tasks by template, (2) no mismatches with real code appeared during detailing.

### Validators

Launch both in parallel:

[`task-validator`](.claude/agents/task-validator.md) (fallback: `~/.claude/agents/task-validator.md`) (sonnet) — Template Compliance + AC/TDD carry-forward:
- Batch: 5 tasks per call
- Pass: feature_path, task_numbers array, batch_number, iteration
- Report: `logs/tasks/template-batch{N}-review.json`

[`reality-checker`](.claude/agents/reality-checker.md) (fallback: `~/.claude/agents/reality-checker.md`) (sonnet) — Reality & Adequacy:
- Batch: 3 tasks per call
- Pass: feature_path, task_numbers array, batch_number, iteration
- Report: `logs/tasks/reality-batch{N}-review.json`

### Process

1. Launch both validators in parallel (task-validator in batches of 5, reality-checker in batches of 3).
2. Read JSON reports, collect findings.
3. If issues found — for each task with issues, launch [`task-creator`](.claude/agents/task-creator.md) (fallback: `~/.claude/agents/task-creator.md`) in fix mode:
   - Pass: same inputs as creation + `mode: fix` + `findings` from validators
   - task-creator reads existing task, applies fixes, overwrites file
   - after the fixes land, run the **Propagation sweep** below over ALL cards — a fix round is
     an edit like any other, and its brief's file list is not the boundary of the correction
4. After each validation round, git commit: `chore(tasks): validation round {N} — {summary}`
5. Re-validate **only the tasks that had a `critical` finding**, with the validator that reported it. `major`/`minor` fixes are applied and not re-validated (since 2026-09-30). Maximum 2 rounds in total.
6. If critical findings remain after round 2 — show user: "Вот что осталось — давай решим вместе."

### Propagation sweep

**Runs after ANY edit — a fix round, a tech-spec correction, a split, a hand edit — and before
the cross-task check. Never scoped to the files the fix named.** Work is scoped by file; a fact
is not. The fix's own description names the destination of a change and almost never its source,
so the half that must give something up is the half nobody opens.

Drive the sweep from the fact, three passes, all batch-level (a per-card pass cannot see any of them):

1. **Contradiction pass** — `grep -l '<the changed name>' tasks/*.md` and read every hit: any card
   asserting a wave, an independence relation, an ownership claim or a format about the changed
   thing is asserting something only the owning card's frontmatter can settle. Resolve each against
   that frontmatter. Two claimants for one file is a reassignment that half landed; a sibling
   repeating the same dead premise looks like corroboration, not staleness.
2. **Absence pass** — a correction that ADDS a fact leaves no token to search for: the card that
   most needs editing is the one where the new name never appears. So this pass is driven from the
   ownership table, not from the corrected text: for each unit, compare what it is now supposed to
   contain with what it does contain. Same for centralisation — when a spec finally mints an owner
   for something several cards each improvised, search for the **workaround**, never for the
   decision's vocabulary; the improvised copies read as finished work.
3. **Stale-rationale pass** — cards that were RIGHT are not reopened, and they are the second class
   of victim: a deviation rationale, a diagnosis of a spec defect, a "still open question", a
   documented "this file does not exist yet" are present-tense claims about a document that just
   changed. Scope by "which cards talk about this fact", never by "which cards got it wrong".

Also: when a shared citation is corrected in one card (an external line number, a signature, a
constant, a verify command's literal flags), grep the literal wrong string across **all** cards of
the feature, including batches already validated — batching by task-number range has no reason to
re-surface a fact that is not task-scoped.

A validator's prescribed `fix` is advice with no expiry stamp: the observation of the defect
usually stays true, the remedy is a design decision made against a snapshot. Re-derive any remedy
that says "keep" or "build" against the current tech-spec before applying it; remedies that say
"delete" or "correct this false statement" rarely invert.

### Re-assignment / split checklist

Splitting a task, extracting a subtask or moving work between cards has **three** downstream
classes, and the change itself names only two of them (the donor and the recipient):

- [ ] the **donor** card actually gave the work up — an extraction that leaves it in place produces
      a duplicate that looks more finished than the new card;
- [ ] every **by-number reference** to the donor (`Task N`, `задача N`, `depends_on`, decision ids)
      re-resolved: the plan's cross-references are keyed on an identifier the plan just re-partitioned;
- [ ] every **consumer of the moved artefact** — named nowhere, needing no edit of its own, and
      correct only because of a wave number whose meaning the split silently rewrote. Re-derive the
      ordering from artefact paths (`wave-check.py`), never assume bucket numbers still mean what
      they meant. This class is why a split always ends with a wave-check re-run.
- [ ] any reference leaving the feature folder is qualified with the feature name — `Task 4` is
      unique only inside one `tasks/` directory, and the next feature reuses the number.

### Cross-card findings

A card's author is often the only party positioned to see a defect in a sibling, and is exactly the
party that may not edit it (`owns_paths`). Without a channel, that author does the one thing
available — writes an explanation to whoever comes next — and the pipeline scores it as diligence.

- A card may only resolve questions its own execution answers. A question about a card that runs
  **earlier** is escalated out of the file to this orchestrator, which is the only layer that sees
  the ordering. Recording a discrepancy is what you do after someone owns it, not instead.
- Route: the finding goes into the validation round's finding list with the sibling's task number,
  and this orchestrator launches `task-creator` in fix mode on the sibling. A card whose text
  instructs its executor to *inform* someone about a problem elsewhere is a finding, not a fix —
  treat that phrasing as the tell.
- An obligation written in the delegating card ("task N will call this") is recorded, not assigned:
  the party that must act reads a different file. Require the named party's own card to state it.
- A gate that counts findings in an artefact the gated task does not own needs a stated closure
  path: who re-issues the report after the fix, and how. Signature to check mechanically — an
  acceptance command whose input path is outside the task's `owns_paths` and whose failure
  condition is a property of that file's contents. Without a re-issue step that is a trap, not a
  gate: the only reachable action is editing someone else's file.

### Cross-Task Integration Check

After individual validation passes, run a final cross-task check:

0. Run `python3 .claude/scripts/wave-check.py work/{feature}` yourself (Bash) — it is the only step that
   sees every task's `owns_paths` / `reads` / `depends_on` side by side (a per-task pass structurally cannot).
   Exit 1 → each violation goes to `task-creator` in fix mode: move the reading task to a later wave and add
   `depends_on`, or split the overlapping ownership. Re-run until exit 0. Tasks reported as
   `skipped_no_owns_paths` are not "ok" — a code task without `owns_paths` cannot be enforced.

1. Launch both validators on ALL tasks in a single batch (not split into smaller batches):
   - `task-validator` — focus: shared resource ownership (one owner, consumers depend_on owner), no competing instances in same wave
   - `reality-checker` — focus: duplicate heavy resource init, hidden dependencies, inconsistent approaches across tasks

2. If issues found → launch `task-creator` in fix mode for affected tasks. Re-validate fixed tasks.

3. One round for the cross-task check; a second only for `critical` findings.

**Checkpoint:**
- [ ] Both validators: status=approved OR user resolved remaining issues
- [ ] Propagation sweep run after the last edit (contradiction / absence / stale-rationale)
- [ ] Cross-task integration check: no cross-task conflicts
- [ ] Cross-card findings routed to their owning card, none left as prose instructions

## Phase 3: Present to User

1. Summary: task count, waves, dependencies, validation results (iterations, issues found/fixed).
2. Wait for user approval.
3. Git commit: `chore(tasks): task decomposition approved for {feature}`
4. Suggest next step: `/do-task` for individual tasks.

**Checkpoint:**
- [ ] Summary presented to user
- [ ] User approved task decomposition
- [ ] Approval committed

## Final Check

- [ ] All phases completed (tasks created, validation passed)
- [ ] All tasks match template (frontmatter: status, depends_on, wave, skills, reviewers, teammate_name)
- [ ] Validation: both validators passed or user confirmed remaining issues
