---
name: tech-spec-planning
description: |
  Creates tech-spec.md with architecture, decisions, testing strategy, and implementation plan.

  Use when: "сделай техспек", "составь техспек", "техническая спецификация",
  "tech spec", "создай тз", "составь тз", "new-tech-spec", "/new-tech-spec"

  Requires existing user-spec.md as input (create with user-spec-planning skill first if missing).
---

# Tech Spec Planning

Create technical specification through code research, adaptive clarification, and multi-validator review.

**Input:** `work/{feature}/user-spec.md` + Project Knowledge
**Output:** `work/{feature}/tech-spec.md` (approved)
**Language:** Technical documentation in English, communication in Russian

## Phase 1: Load Context

1. Ask user for feature name if not provided. Check `work/{feature}/` exists, create if needed.

2. Read `work/{feature}/user-spec.md`. If missing — ask user to describe the task or create user-spec first.
   Extract `size: S|M|L` from user-spec frontmatter — it determines testing strategy depth in tech-spec.

3. Read all files in `.claude/skills/project-knowledge/references/` (project.md, architecture.md, patterns.md, deployment.md, ux-guidelines.md, and any custom domain files). Missing files are fine — not all projects have all guides.

4. user-spec.md is the single input source — all information from interview.yml and code research is already consolidated there.

**Checkpoint:**
- [ ] Feature folder exists
- [ ] user-spec.md read, size extracted
- [ ] Project Knowledge read

## Phase 2: Code Research

Launch `code-researcher` subagent (Task tool, opus) with feature path and user-spec path. The agent reads existing `code-research.md` (from user-spec phase if available) and deepens analysis for implementation.

After subagent completes — read `{feature_path}/code-research.md`. Use in Phase 3 clarification and Phase 4 spec writing.

If during later phases a gap is discovered — launch `code-researcher` again with the specific question.

**Build the reading list by enumerating the folder, not from memory:** `ls -R work/{feature}`. Anything under `logs/` that is prose about the system — a prior round's findings, a gate report with reasoning in it — is an input to this phase, not exhaust. A directory named `logs/` makes the strongest possible claim that nothing inside it is content; the claim is true ninety-nine times and catastrophically wrong once, and nothing distinguishes the cases from outside.

**Research verdict → criterion: a crossing table with no empty cells.** A research conclusion and an acceptance criterion are different genres, and a conclusion lost in the move between them leaves no empty space behind it — the spec reads complete. So the transfer is checked against the source, never by reading the result. Before writing the spec:

1. Give every research conclusion marked blocking or mandatory an id.
2. Carry them into the spec as a table `research conclusion → the acceptance criterion that closes it`, or an explicit row `closed by a decision not to do it, reason: …`.
3. An empty cell is a lost conclusion and blocks approval.

The same applies to any persisted gate output in the feature's `logs/` — a completeness or coverage gate that returned a numbered gap list. For each numbered gap report exactly one of: **closed** (content present in the final artefact), **consciously deferred** (written into the artefact as an accepted limitation), **dropped** (neither). A dropped critical or major gap is a finding of the same weight as any other critical finding — it must never depend on someone noticing the leftover gate file while reading the folder for something else.

**Checkpoint:**
- [ ] code-research.md created/updated with implementation-level analysis
- [ ] Research file read by orchestrator
- [ ] Feature folder enumerated (`ls -R`), prose artefacts under `logs/` read
- [ ] Crossing table built: every blocking research conclusion and every persisted gate gap has a named destination (criterion / deferred / reason not to do it)

## Phase 3: Clarification (Adaptive)

Analyze if additional information is needed based on user-spec and code research.

- Ask technical questions if gaps exist. No limit on question count — ask as many as needed.
- Focus: technical constraints, integration points, data sources, external dependencies.
- If gaps found in user-spec requirements — discuss with user and update user-spec too (via subagent or directly).
- If requirements are fundamentally unclear — suggest creating user-spec first.

### Premises are not requirements — separate them and check them

A brief is two genres in one text. A **requirement** states what must become true; it cannot be falsified, only met or not met. A **premise** states what is already true — "the webhook is already configured", "that field is already filled", "it will be picked up automatically", "this is deployed". A premise can be false, and a false premise silently invalidates every requirement resting on it, without leaving any mark on the spec.

1. Extract every statement about the current state of the system from the brief and from the user's own wording into one short written list. On paper, not from memory.
2. Verify each against code and config, and mark it: **confirmed** (`file:line`), **refuted**, or **not checkable** (say why — e.g. server access not granted). "Not checkable" is a result and is written down as one: a spec must never present an unverified premise as a verified one, even when the check was forbidden by the terms of the task.
3. A refuted premise is never routed around in silence. The requirement standing on it either changes, or gains a task that makes the premise true — and either way it becomes a User-Spec Deviations entry marked "the brief assumed otherwise".
4. **An exemplar reference is a premise.** "Like X does", "same as already built", "by analogy with" — resolve each to `file:line` and write out WHAT the exemplar actually does, before writing Decisions. Record either "exemplar confirmed, `file:line`" or a Deviations entry "the exemplar does something else; this mechanism is introduced here for the first time, definition in Decision N". An exemplar reference can never stand in for a definition in the tech-spec: the executor reads the task card, not the brief, and every later reader sees a reference that resolves and none of them sees the divergence.
5. **A premise that arrives after research is still a premise.** When a review round or a user decision introduces a new external dependency — an account, channel, number, endpoint, identifier, service — diff the external addresses against the previous version of the spec and run every new one through the sources research would have used (project reference memory, neighbouring services' code, past incidents) before the spec goes back for re-review. A user decision settles "whether to do it"; it creates no facts about the world. It arrives precisely when the fact-checking phase is formally over and carries the status "decided, do not argue", so a new dependency enters through the one gap where the control has already been lifted, with maximum trust and minimum checking at the same time.

**Checkpoint:**
- [ ] All technical gaps clarified (or none existed)
- [ ] Premises from the brief listed and each marked confirmed / refuted / not checkable
- [ ] Every exemplar reference ("like X") resolved to `file:line` or turned into a Deviations entry
- [ ] External dependencies added after research were researched before re-review

## Phase 4: Create tech-spec

1. Copy template to feature folder. Prefer the project template (synced via git), fall back to the user-level copy:
   ```bash
   cp .claude/shared/work-templates/tech-spec.md.template work/{feature}/tech-spec.md \
     || cp ~/.claude/shared/work-templates/tech-spec.md.template work/{feature}/tech-spec.md
   ```
   If both copies exist and differ — stop and show the diff instead of silently taking either one. Record which copy this spec was built from in frontmatter as `template_source: project|user`. Without that line, "the section is absent" is indistinguishable from "the section never arrived", and a gap caused by a stale fallback copy is only ever found by an outside reviewer who happened to hold the right copy. (The precedence rule itself — project copy wins over the personal one — lives in the project `CLAUDE.md`, which cannot be shadowed; a precedence rule written only in the copy that loses cannot be read without having already picked a winner.)

   Then edit sections one by one using Edit tool. This keeps template structure and examples visible while you work.

2. Fill frontmatter:
   - `created`: today's date
   - `status`: draft
   - `size`: copy from user-spec (S|M|L)
   - `branch`: `dev`
   - `level`: уровень зрелости по `ENGINEERING.md` §0 (L0 прототип / L1 прод — default / L2 нагрузка). Если пользователь не назвал — L1. L2 требует явного обоснования в Decisions.
   - `start_commit`: leave empty at draft (filled at approval, Phase 6)
   - `footprint`: declare the expected change size up front — `files_modified` (existing files to touch), `files_new` (files to create), `loc_estimate` (rough lines added+changed), `new_deps` (new packages, `[]` if none). Derive the numbers from the Implementation Tasks "Files to modify" lists and the Dependencies section — they must agree. /done compares this declaration against `git diff --numstat` actuals; a large mismatch flags scope creep or incomplete work.

3. Fill all template sections. The template defines section structure — follow it directly.
   In Architecture → Shared Resources: list heavy resources (ML models, DB pools, browser instances, API clients) shared across components. Specify owner (who creates), consumers, instance count. If none — write "None".

   **An enumerated set is a forecast until the code is read back.** Where a task's description
   or a Data Models / API-contract table lists a fixed, countable set the task will add — fields,
   columns, event types, constants — that task's Acceptance Criteria carry a **cardinality**
   assertion, not only per-name presence: `count(actual) - baseline == N`, with N the literal
   the prose claims. Presence checks are structurally blind in one direction: every name the
   spec listed is there, so every "field X exists" assertion passes while the code quietly
   ships a superset, and the task's own spec-derived tests agree with its own spec and are
   wrong together. A missing promise is at least searchable by name; an unnamed extra is
   invisible to any check phrased as "is Y present".

   **Acceptance Criteria = receipts.** Every criterion in `## Acceptance Criteria` must carry a `verify:` line — a concrete runnable command with an expected outcome (exit code, HTTP status, output substring). "Done" is a re-runnable command, not a sentence: /done re-runs every verify command and records hit/miss; a miss blocks finalization. A criterion that genuinely cannot be checked by a command gets `verify: manual — <what the user checks>` — use sparingly. Abstract checks ("works correctly", "no errors") are not receipts — rewrite them as commands.

   **A decision that changes a contract version between services is not closed by citing the deploy procedure.** Write a separate Decision point that walks the rollout step by step in time and names the state of the system at each step — "reader deployed, writer still old: what does the user see". A procedural rule that has never actually been executed is a hypothesis, and its status is said out loud. Two rules that are each correct and each covered by tests can be unexecutable together; the seam where that shows up is the window between the two deploys, and every service must be rollback-able on its own or the rollback plan is listing services it cannot separate.

   **User-spec anchoring:** Every decision in the Decisions section must reference a user-spec requirement it serves (e.g., "Supports US-3: push notifications"). If a decision is purely technical (not derived from any user-spec requirement) — mark it `[TECHNICAL]` with justification. If a decision contradicts or changes a user-spec requirement — document it in the User-Spec Deviations section and mark as `[PENDING USER APPROVAL]`. All deviations must be documented explicitly — this preserves the user's original intent for review.

4. Fill Implementation Tasks by waves. For each task provide: Description, Skill, Reviewers, Verify-smoke (optional), Verify-user (optional), Files to modify, Files to read. Select skill and reviewers from [skills-and-reviewers.md](references/skills-and-reviewers.md) (execution skills catalog, reviewer agents, default mappings).

   For each task, write `Verify-smoke:` when the task involves:
   - External API integration → curl/httpie command to real endpoint with expected response
   - Library/model initialization → `python -c` or import check that verifies setup
   - Docker/infrastructure → `docker compose build`, `docker run` commands
   - LLM/prompt work → spawn agent with prompt + test question, check response
   - External service API (OpenRouter, Stripe, etc.) → test API call with expected response
   - MCP-verifiable UI/frontend → use Playwright MCP or similar to check rendered page
   Write `Verify-user:` when user should check something: UI on localhost, behavior, UX.
   Omit both if task is purely internal logic covered by unit tests.

   #### A verify command is a contract, not a description

   `Verify-smoke:` here and `verify:` in Acceptance Criteria are both replayed by a machine
   (`.claude/scripts/task-accept.py`, `/done`): ONE shell command per bullet, run from the
   task's `verify_cwd`, judged by its exit code. A line written in any other shape fails the
   receipt for a reason that has nothing to do with the code under test — and it fails at the
   last stage, where the only remaining fix is invention by someone who never saw what the
   check was supposed to prove. Four axes, each cheap, each checkable at authoring time:

   1. **The verdict travels on the channel the acceptor reads — the exit code.** A verify line
      has two readers: the human, who reads the expected output, and the machine, which reads
      only the exit status, and they can disagree in both directions. `→ expected output`
      notation is forbidden unless it is wrapped (`test`, `!`, `&&`). An absence check is
      `! grep -q <pattern>`, never `grep -c … → 0` — `grep -c` prints `0` and exits 1, so the
      passing state is scored as a failure. Anchor an absence pattern to its syntactic position
      (a directive at line start), never a bare token, or the cheapest route to green is
      deleting the rationale comment the task was required to keep.
   2. **The interpreter resolves in the environment of EXECUTION, not of authorship.** Take the
      runner invocation from the project's own README "how to run tests" block, or from an
      existing task card of the same component — never from habit — and state once, above the
      task table, which invocation the spec assumes. `python` vs `python3.11` vs
      `./venv/bin/python` is the first token of the line: it looks like boilerplate, it is the
      part most likely to differ between the machine that writes the command and the machine
      that runs it, and it is therefore the part least likely to be examined.
   3. **The command's write-set lies inside the executing task's `owns_paths`.** A command that
      writes a file (`--report`, `--out`, a redirection) may be run only by the task that owns
      that path. Where a later task must confirm the same fact, its verify is a **read** of the
      artefact (`grep -q 'survived: 0' <receipt>`), not a re-run — and the criterion names the
      producing task. A verify command asserts two things at once, what it proves and who may
      run it where, and the two are indistinguishable on the page.
   4. **Repo-local or environment-dependent.** Lexical detector, applied to every command:
      `ssh`, an absolute runtime path, `systemctl`, `docker compose`, `pm2`. Any of these means
      the command is asserting that a deploy has already happened. Such a command goes to the
      post-deploy criterion list, or gets an explicit repo-local equivalent; it may not sit in a
      wave that precedes the deploy task. Wave ordering is enforced over repository paths, so a
      dependency expressed as *deployed state* is invisible to it, and the failure then surfaces
      as a QA status (`not_verifiable`) rather than a spec defect — routing the correction to
      the party least able to make it. The same directional check applies to a deploy or
      verification task's own step list: resolve every symbol, file, endpoint and binary a step
      names against the state of the target **at that step**, not against the end state of the
      feature. Anything the feature itself creates must be introduced by an earlier step than
      the one consuming it.

   Mechanics that follow from the same contract: no ellipsis in a command, no prose connectives
   ("локально", "затем", "повтор"), at most one backtick span per bullet. A check needing a
   running process, a seeded database or a secret IS the one command that provides them — a
   wrapper script named in that task's Files to modify, or an `env … sh -c '…'` one-liner.
   A selector-bearing command (`-k`, `-t`, a path substring, a tag filter) is smoke-run at
   authoring time and records what it selected beside it — `→ exit 0, 3 selected`; a check whose
   test does not exist yet is written `0 selected (test written in Task N)`, which keeps the debt
   visible in the spec instead of disguising it as a check. Select tests by file path, never by
   name filter: a name filter that matches nothing exits 0 under some runners and is then
   literally indistinguishable from a pass.

   **Whether a check is able to go red at all** is a separate question with one canonical
   procedure: `.claude/skills/test-master/references/proving-a-check.md` (fallback: `~/.claude/skills/test-master/references/proving-a-check.md`). The spec author's
   part is small and fixed — for each verify line, probe BOTH polarities against the acceptor's
   contract (the passing case and the no-subject case), and record the two exit codes next to
   the command. Do not restate the procedure here; follow it there.

   #### The form of the check follows the artefact, not the kind of work

   The bullet list above names types of *work* (API, Docker, LLM, UI), which is why a task
   producing no code tends to get an empty verification field — not by decision, but because the
   question was never asked. The right question is **"does this artefact have a machine-readable
   form?"**. When it does, the field is never left blank: either a command, or one line saying
   why no command exists.

   | Artefact the task produces | Form the check takes |
   |---|---|
   | Schema (JSON Schema, OpenAPI, DDL, migration) | it parses; a known-good and a known-bad instance validate as expected |
   | Fixture / golden sample | it parses; required keys present; the invariant stated in prose holds ON the artefact |
   | Document **plus** its own sample (contract + fixture) | the two are checked against each other — their divergence is what every consumer inherits |
   | Config / env declaration | every key the code reads resolves; every key declared is read by something |
   | Contract between components | the consumer's parser accepts the producer's sample, run as one command |
   | Receipt / report of fixed shape | structural parse (row count, closed token set, non-empty columns), not a `grep` for two substrings |
   | Prose / an agreement with a human | one line stating why no command exists |

   An empty field looks identical for a task nothing can check and for a task checkable by one
   line of `python -c`; the line of prose is the only thing that separates them, and a reviewer
   reads both as "no automation here".

   Two traps specific to the case where the spec defines **both** an artefact's shape and the
   command that checks that shape — both halves written by one author in one edit:
   - The checking half is never run against a correct instance. Manufacture one instance exactly
     as the spec describes it and run the command on it. A broken checking half usually fails
     *safe* — permanently red — which looks harmless and is not: an executor stuck on an
     unreachable criterion fixes the artefact to fit the command, so the closed form the rule
     existed to enforce gets rewritten by the party it was meant to constrain.
   - When a verify greps a document for literal text, check that text against the nearest
     existing sibling artefact of the same kind in the repo (`logs/receipts/*`, or the artefact's
     own path pattern). If the precedent does not already satisfy the new grep, either match the
     precedent's shape or state in the criterion why this artefact must diverge from it —
     otherwise a task-creator who used the sibling as its formatting reference, which is the
     reasonable thing to do, produces something the criterion rejects.

   **Do not "green" a wave by moving a shared artefact earlier** (a contract, fixture, schema,
   key set). First enumerate everyone who checks that artefact against the PRODUCT of code
   rather than against itself: shape equality, key-set comparison, a self-check spawned as a
   subprocess. If any exist, moving the artefact does not produce a green wave — it converts a
   hidden intermediate red into a blocking one, and a Verify-smoke widened to the full set
   becomes the mechanism that presents it. In that case name the expected-red nodes explicitly
   in the task card and leave Verify-smoke on the set that is obliged to be green. "Make the
   wave green" and "make the red visible" are different goals with different means.

   **Task brevity rules:**
   - Tasks are brief scope descriptions (2-3 sentences). Detailed steps, AC, and TDD anchors are created during task-decomposition phase.
   - Task Description answers WHAT and WHY, not HOW. No step-by-step instructions, no line numbers, no implementation details.
   - All technical decisions belong in the Decisions section, not in task descriptions. If you're writing a decision rationale inside a task — move it to Decisions.

5. **Audit Wave and Final Wave — conditional (since 2026-09-30).** They are the most expensive part of
   the pipeline, so they run only where they can catch something the per-task lenses cannot:

   Include **Audit Wave** (3 parallel tasks, `reviewers: [none]`: Code Audit `code-reviewing`,
   Security Audit `security-auditor`, Test Audit `test-master`) when `level` ≥ L1 **and** at least one
   of: the feature writes outward (CRM record or task, message to a client, payment, external API write);
   it adds or changes a server unit (process manager, systemd, cron, container); it has ≥ 4 code tasks.
   Otherwise omit it and write under Implementation Tasks one line:
   `**Audit Wave:** пропущена — <which condition fails>`. Auditors read all source files of the
   feature and write reports (analysis only); if issues are found the feature-execution lead spawns
   a fixer and reviews it with the thorough lens set.

   **Final Wave:**
   - **QA** (skill: `pre-deploy-qa`) — present whenever Audit Wave is present, or whenever the
     feature has acceptance criteria that no task's own verification exercises end to end. Otherwise
     omit with a one-line reason next to the Audit Wave line.
   - **Deploy** (skill: `deploy-pipeline`) — only if deploy is needed for this feature.
   - **Post-deploy verification** (skill: `post-deploy-qa`) — only if live-environment checks are needed (MCP tools listed in Agent Verification Plan → Tools required).

   L0 features never carry Audit or Final waves. The skip line is a claim the validators check
   against the tasks: a feature with an external write and no Audit Wave is a critical finding.

6. Fill Risks → Prod-readiness table (for level L1+). Each row is either "как сделано" or "не применимо, потому что". Source of rules — `ENGINEERING.md` §2 and `.claude/skills/prod-review/production-checklist.md` (read only the blocks triggered by this feature). Never leave a row empty; an empty row means the question was not asked.

   Two rules make the rows load-bearing instead of decorative:

   - **Every mitigation carries an executable owner** — a test node id, an acceptance-criterion number, a mutant id, or the address of the task that implements it. A prose pointer ("see Decision N") does not close a row. A mitigation that exists only in prose is a description of an intention, indistinguishable from its own absence by any run; and the more often a decision is restated in the document, the more readily it is taken for covered — frequency of mention and existence of a check are independent quantities.
   - **A row naming a framework-specific mechanism** (a config flag, a middleware, a decorator) is cross-checked against Dependencies → New packages. If that framework is not in the approved list, the spec holds an unresolved choice, not a settled one: either add the package with its own line in New packages, or restate the row framework-agnostically. The same seam applies wherever a Files-to-read example is borrowed from a sibling service — the example's stack is verified against what THIS feature's Dependencies approved, not adopted because the response shape is a good model.
   - **Every file path named in Dependencies or Prod-readiness prose as the mechanism for a requirement must appear in the Files-to-read or Files-to-modify list of the task that owns that requirement.** Mechanical: extract the paths, intersect with the task lists, and the difference must be empty. A requirement stated once in a cross-cutting section and never restated per task is inherited silently by a task-creator, because the missing file was never in either list to begin with.

7. Fill User-Spec Deviations section. For each element in tech-spec that changes, extends, or contradicts user-spec — add an entry with the requirement ID, what user-spec says, what tech-spec does differently, and why. Mark each entry `[PENDING USER APPROVAL]`. If no deviations — write "None".

8. Task Count Check: if >15 tasks — propose splitting into MVP + Extension phases. Wait for user decision.

9. Git commit: `draft(techspec): create tech-spec for {feature}`

**Checkpoint:**
- [ ] tech-spec.md created in work/{feature}/ with all sections
- [ ] Frontmatter has `level` set (L1 by default; L2 justified in Decisions)
- [ ] Risks → Prod-readiness table filled for L1+ (no empty rows)
- [ ] Frontmatter has `footprint` filled, consistent with task file lists and Dependencies
- [ ] Every Acceptance Criteria item has a `verify:` command with expected outcome (or explicit `verify: manual`)
- [ ] Every verify / Verify-smoke line: verdict carried by exit code; interpreter taken from the project's own run instructions; write-set inside the executing task's `owns_paths`; environment-dependent commands (`ssh`, absolute runtime path, `systemctl`, `docker compose`, `pm2`) routed post-deploy
- [ ] Both polarities probed and the two exit codes recorded; selector-bearing commands carry their selected count
- [ ] Every task producing a machine-readable artefact (schema, fixture, config, contract, receipt) has a check or one line saying why none exists
- [ ] Frontmatter records `template_source`
- [ ] Implementation Tasks include Description (2-3 sentences), skill, reviewers for each task
- [ ] No AC or TDD anchors in tasks (those come from task-decomposition phase)
- [ ] Technical decisions are in Decisions section, not in task descriptions
- [ ] Every Decision references a user-spec requirement or is marked `[TECHNICAL]`
- [ ] User-Spec Deviations section filled (or "None")
- [ ] Audit Wave and Final Wave present when the conditions of step 5 hold, or the one-line skip reason is written and true
- [ ] Task count ≤15 (or user approved larger scope)

## Phase 5: Validation

### Run 5 validators in parallel

Launch all as subagents, each writes JSON report to `logs/techspec/{name}-review.json`:

| Validator | Agent | Checks |
|-----------|-------|--------|
| Mirage detector | `skeptic` | Non-existent files, APIs, functions, dependencies |
| Completeness + adequacy | `completeness-validator` | Bidirectional traceability, scope creep, overengineering, underengineering, solution depth |
| Security | `security-auditor` | OWASP, input validation, auth, sensitive data |
| Testing strategy | `test-reviewer` | Test plan adequacy for feature size S/M/L |
| Template + wave conflicts | `tech-spec-validator` | All sections filled, frontmatter, format, skills/reviewers, wave conflict detection |

Pass to each validator: `work/{feature}/tech-spec.md` + `work/{feature}/user-spec.md`.

### Process findings

Read all 5 reports. Read each finding's **whole body**, never its title: a reporter often
includes the correct fix, and dismissal is the one outcome with no downstream checkpoint — a
finding that is closed or cited gets looked at again, a dismissed one silently disappears.

**Split every finding into diagnosis and cure; they are not equally reliable.** The diagnosis
rests on what the reviewer actually read and is usually right. The cure rests on what the
reviewer did NOT read — another service, a neighbouring feature, a second consumer of the same
number, an external contract — and is bounded by the frame of its own artefact, while reading
exactly as confidently, because it is internally consistent and often comes with a test. Take
the diagnosis; derive the cure again yourself. Where the finding concerns a value that someone
else also reads, writes or duplicates, the correct cure follows from the invariant BETWEEN the
consumers, and that invariant is visible from neither of them alone.

Then close each finding in four passes. Passes 2–4 are the difference between closing a defect
and closing a class, and they are exactly where a second review round systematically fails —
because the author's work subjectively ends where the finding's text ends.

**Pass 1 — answer the finding.** Apply the fix at the address the finding names. Reject with
reasoning where you disagree — only for findings unrelated to user-spec alignment.

**Pass 2 — recompute what the fix invalidated.** A fix leaves everything downstream of it
wearing the confident, self-justifying phrasing it was born with:
- Any number sitting below a newly added derivation is **stale until recomputed from the new
  figures**. Practical detector: a carried-over number cannot be produced by any arithmetic over
  the new table. Trust in a section must FALL when a new derivation appears in it, and rise only
  as each dependent number is recomputed — a correct calculation standing next to an old number
  reads as agreement and protects it better than it was protected before.
- A fix that relaxes a limit, threshold, pause or timeout is never a standalone decision: it is
  the pair "limiter + the demand it was relaxed for", and only the pair is valid. The limiter's
  justification must cite a figure computed AFTER all of this edit's changes. Any fix moving more
  than one quantity lists which quantities moved and re-derives each remaining number from the
  right one — each individual number stays correct, and what breaks is the link between a number
  and its justification, which is written down nowhere.
- Amending a decision's **default value, precondition or failure mode** obliges a grep of the
  whole document for procedures that cite that decision, each re-read against the new form —
  asking not "does this step still make sense" (it will) but "what was this step protecting
  against, and does that hazard still exist". Record the answer as a line in the amendment:
  `steps elsewhere that assumed the old form: <list, or 'checked, none'>`.

**Pass 3 — apply the new rule to everything, starting with this round's own additions.** Every
closed finding leaves a rule behind: the rule the document was missing. A review finds
instances, not classes, and a fix inherits the finding's address. So write the rule out in one
sentence, enumerate the places it could apply, and record a verdict per place —
**applies and applied** / **applies and not applied** / **does not apply, because …**. An empty
cell means the question was never asked; the enumeration is recorded next to the fix, not
implied. **First in the enumeration come the elements this round itself added** (new decisions,
fields, criteria, tiles, mutants): no finding can exist about them, the author has just seen the
principle written down and counts the matter closed, so the freshest part of the document is
systematically the least checked part. Three shapes recur often enough to name:
- **A paragraph explaining why one field is exempt** from a narrowed scope (a stage list, a time
  window, an entity population) is not evidence of diligence — it is a pointer to a class. The
  obligatory next question is "who else is in that scope", answered by enumerating every field of
  the data model inside it, not by reasoning about the ones the rationale mentions. Two figures
  about one subject with different domains of definition, displayed side by side, is a `major`.
- **A fix shaped "if A is unavailable, take B, else C"** reinstates rejected semantics under the
  name of a fallback path. Write out each rung's semantics separately and compare with the top
  rung: a rung that reproduces rejected semantics is either re-justified as a decision in its own
  right with its own cost, or removed. Values from different rungs are different *kinds* of
  value — they do not compare equal, do not enter the same aggregates, do not displace the main
  branch on conflict, and the level marker ("known" / "unknown") survives to the point of
  comparison. A fallback threshold is its OWN constant, derived from the data it exists for;
  a borrowed constant imports someone else's definition of sameness and is usually orders of
  magnitude too wide. And the fallback's population is measured by a reading probe BEFORE it is
  switched on — it exists for data that in normal operation will not be there.
- **A decision added by this round has no mutant and no test by default**, because the set was
  assembled before it existed. Every new decision gets at least one.
- If the document instructs an audit to hunt a class of defect ("a second definition of a term"),
  check the document against itself: did this same edit introduce an instance?

**Pass 4 — status is binary.** "Partially closed" is not a terminal status. A finding is
**closed** (its original question has an answer checkable against the text) or **open**. The
remainder of a partial close is re-filed as the SAME finding, at the SAME severity, with an added
line "what has already been done" — never as a fresh finding at a lower level. Severity is a
property of the question, not of the volume of work left, and may fall only together with an
answer. A status between closed and open works as a drain: it takes the pressure off a finding
without deciding anything, and does so the more reliably the more honestly the remainder is
phrased. At the end of every round, list separately the findings open for more than one round —
otherwise a long-running finding dissolves into the totals and convergence ends up measuring how
fast findings are rephrased rather than what changed in the subject.

**User-spec alignment findings require user decision.** When completeness-validator reports `gap`, `scope_creep`, `overengineering`, or `shallow_solution` — present each finding to the user with your recommendation (fix / keep / adjust). Reason: these findings mean the tech-spec may contradict what the user asked for — only the user can decide whether the deviation is acceptable.

### Iterate if needed (one full round; critical-only re-run)

If fixes were made:
1. Apply targeted fixes directly in `work/{feature}/tech-spec.md`.
2. Git commit: `chore(techspec): validation round {N} — {summary of fixes}`
3. Re-run **only the validators that reported a `critical` finding**, scoped to the sections the
   fix touched. `major` and `minor` fixes are applied and not re-validated — the Prod-readiness
   check and the decomposition validators see the document again anyway. Max 2 rounds in total
   (since 2026-09-30; before — up to 3 full passes, most of the third rephrasing the second).

If critical findings remain after round 2 — show user: "Validation didn't pass in 2 rounds. Here's what remains — let's resolve together."

**Checkpoint:**
- [ ] All 5 validators ran
- [ ] Findings processed (fixed / rejected / discussed)
- [ ] For each closed finding: the rule it leaves behind written out, and applied across the document — this round's own additions enumerated first
- [ ] Numbers below any new derivation recomputed; amended decisions carry their "steps elsewhere" line
- [ ] No finding carries a "partially closed" status; findings open more than one round listed separately
- [ ] Final tech-spec.md placed in work/{feature}/

## Phase 6: User Approval

1. Show user the full tech-spec.md.
2. Show validation summary: iterations count, issues found and resolved.
3. Wait for explicit approval.
4. If user has comments — fix, re-validate, show again.
5. After approval: update `status: draft` → `status: approved` in tech-spec frontmatter, and set `start_commit` to the current HEAD (`git rev-parse HEAD`) — this is the baseline /done uses for the footprint check.
6. Git commit: `chore(techspec): approve tech-spec for {feature}`
7. Tell user next step: run `/decompose-tech-spec` to create task files.

**Checkpoint:**
- [ ] User explicitly approved tech-spec
- [ ] status = approved

## Final Check

- [ ] tech-spec.md created with all sections (Implementation Tasks are brief scope descriptions)
- [ ] Validation passed (5 validators)
- [ ] User approved tech-spec
- [ ] status = approved in frontmatter
