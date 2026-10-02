---
name: feature-execution
description: |
  Orchestrate feature delivery as team lead: spawn agents by wave,
  run review lenses and triage findings (max 2 patch cycles), commit per wave.

  Use when: "выполни фичу", "do feature", "execute feature", "запусти фичу",
  "выполни все задачи", "execute all tasks"
---

# Feature Execution

## Role Boundary

You are a dispatcher, not a doer. Your job: spawn agents, wait for results, update status, commit orchestration changes, communicate with user.

Allowed actions:
- Read specs and task frontmatter (for planning)
- Spawn teammates and review lenses (Agent tool)
- Send/receive messages (SendMessage)
- Update frontmatter status fields and checkpoint.yml (Edit)
- Write execution-plan.md (Write)
- Git commits for status/orchestration changes (Bash)

Forbidden actions:
- Writing or editing source code, tests, configs, prompts
- Running tests, builds, linters, deploys
- Calling MCP tools for task work (Telegram, browsers, APIs)
- Debugging errors or "quickly fixing" anything
- Reading full task content during execution (frontmatter only)

Reason: when the lead does task work, it pollutes context with implementation details, loses orchestration state, and breaks the parallel execution model. Every task — no matter how trivial — gets a spawned teammate.

## Phase 1: Initialization

0. Check `work/{feature}/logs/checkpoint.yml`:
   - `last_completed_wave > 0` → this is a resume after context compaction.
     Read checkpoint, then read `work/{feature}/decisions/` (per-task files) and `work/{feature}/decisions.md`
     (the merged file, if the feature predates the split) to confirm what was actually completed.
     For tasks in the resumed wave: if a task has a `decisions/task-{N}.md` file (or a decisions.md entry),
     it completed — update its frontmatter to `done` and skip it. Only re-execute tasks without one.
     Check if `~/.claude/teams/{team_name}/config.json` exists: if yes, team is alive; if no,
     recreate via TeamCreate. Skip to Phase 2 starting from `next_wave`.
     Report to user: "Resuming from wave {N}. Waves 1-{N-1} completed."
   - `last_completed_wave: 0` → fresh start, proceed below.

1. Read `work/{feature}/tech-spec.md` and `work/{feature}/user-spec.md`
2. Read frontmatter of all task files in `work/{feature}/tasks/` — extract fields:

   | Field | Purpose |
   |-------|---------|
   | `status` | planned → in_progress → done |
   | `wave` | Parallel execution group number |
   | `depends_on` | Task numbers that must be done first |
   | `skills` | Skills the teammate loads |
   | `reviewers` | Reviewer agents to spawn (source of truth) |
   | `teammate_name` | Agent name for team spawning (optional) |
   | `verify` | Verification types: [smoke], [user], [smoke, user], or [] (optional) |

   Build waves: group tasks by `wave` field. Within a wave, all tasks run in parallel.

3. Build execution plan following template at `.claude/shared/work-templates/execution-plan.md.template (fallback: ~/.claude/shared/work-templates/execution-plan.md.template)`
4. Save to `work/{feature}/logs/execution-plan.md`
5. Show plan to user, wait for approval
6. Create team via TeamCreate
7. Update `work/{feature}/logs/checkpoint.yml`: set `total_waves` from the execution plan.

**Checkpoint:** execution plan approved, team created, checkpoint initialized.

## Phase 2: Execute Wave

1. Find tasks for current wave: `status: planned`, all `depends_on` tasks are `done`
2. Update frontmatter: `status: planned` → `status: in_progress`. Read only frontmatter (`limit=15`), then Edit the status field. Do not read full task content.
3. For each task, spawn a **teammate** (review lenses are launched by the lead after the teammate commits — see "Lead-run review" below):

   Use `teammate_name` from task frontmatter as the agent name. If not set — pick a descriptive name based on the task.

   **A spawn briefing is context and priorities, never the assignment.** Whatever you write into a
   prompt is a summary of the task card, and summarising drops the enumerated, mechanical parts
   first — the list of verbatim commands, the readiness table, the per-row checks. That is exactly
   where the verification lives, and the executor cannot see the gap, because a coherent brief has
   no holes in it. So every prompt you send must carry the authority pointer in its own words —
   "the task card is authoritative; this message adds context" — and must never be phrased so that
   an executor could treat it as the complete scope.

   **Field names in a structured artefact are quoted from the consumer, never from memory.** When
   you tell an agent to emit JSON that a script will parse (review verdicts, findings, receipts),
   open the parser — or the schema it documents — in the same turn you write the prompt, and copy
   the key names out of it. An LLM producer will conform to whatever keys it is given and a
   consumer skips unrecognised keys by design, so the mismatch never raises an error: it produces a
   well-formed file and a plausible wrong number. After the first such artefact lands, run the
   consumer once and confirm it *matched* the entries before acting on the aggregate — a sync step
   must report how many entries it matched alongside how many it found, so "0 matched of 7" is
   loud.

   **Each spawned agent gets its own scratchpad subdirectory**, named after task and role
   (`<scratchpad>/task-{N}-exec/`, `<scratchpad>/task-{N}-{reviewer}/`), handed to it explicitly in
   the prompt. A scratchpad is isolated from the project, not from the other agents of the same
   session: two agents writing generically named files (`run.py`, `out.json`) to the scratchpad root
   is a race whose losing side executes someone else's code under its own arguments.

   **Teammate** — `subagent_type: "general-purpose"`, `model: "opus"`, `team_name: "{team}"`

   Prompt template:

   ```
   You are "{name}" executing task {N}.

   Read task: {feature_dir}/tasks/{N}.md
   Load skills listed in task frontmatter. If skills listed — follow the loaded skill workflow.
   If no skills listed — follow the task instructions directly (the task file contains detailed steps).

   If the task requires user actions — send the instruction to team lead via SendMessage.
   Team lead will forward to user and return confirmation.

   {reviewers_block}

   The task card ({feature_dir}/tasks/{N}.md) is authoritative; this message adds context and
   priorities only. Read the card before acting on anything written here. If the card requires work
   this message did not mention, do the card's version, and say in your final report which
   requirements came only from the card. If the two actually conflict, surface the conflict — do
   not silently pick one.

   Your scratchpad subdirectory is {scratchpad}/task-{N}-exec/. Write every temporary file there,
   never to the scratchpad root, and never under a generic name. Before executing a scratch script
   you wrote earlier in the session, re-check that its content is still yours (header line or hash).

   After task complete:
   - Write your entry to {feature_dir}/decisions/task-{N}.md (follow template at
     .claude/shared/work-templates/decisions.md.template (fallback: ~/.claude/shared/work-templates/decisions.md.template)). One file per task — do NOT append to a
     shared decisions.md: a pathspec names a file, not your contribution to it, and committing a
     shared file carries your neighbour's uncommitted paragraph under your message. The lead merges
     the per-task files.
   - Message team lead: "Task {N} complete. decisions/task-{N}.md written."

   Feature dir: {feature_dir}
   ```

   **{reviewers_block}** — include only when task has reviewers (not `reviewers: [none]`):

   ```
   Review is run by the team lead, not by you: after your implementation commit the lead builds the
   diff from your `start_commit`, launches review lenses and triages their findings. You will receive
   at most ONE message per patch cycle (max 2 cycles) listing findings to fix, each as
   `<file> — <what is wrong> — <what the smallest fix must do>`. Fix each with the smallest change
   that does the job, run only the tests covering the files you edit, commit the same way as below
   (`fix: address review cycle {M} for task {N}`), and reply with what you changed. Do not re-run
   reviews yourself and do not widen scope because of a finding — if a finding needs a decision the
   card does not settle, say so in the reply instead of guessing.
   ```

   Commit flow:
   1. After implementation complete (tests pass): commit with ONE command that stages and commits your
      own paths together — `git commit -m "feat|fix: task {N} — {brief description}" -- <your paths>`.
      Never a separate `git add` followed by a later `git commit`: the index is one shared state per
      worktree, and in the window between the two a parallel session's commit takes your staged files
      into ITS commit under ITS message.
   2. If `git commit` answers "no changes added to commit" after you just saw your files staged, do
      NOT re-add and do NOT `git add -A`. That message is the same for "I did nothing" and "a
      neighbour's commit took my files". Check the content of recent commits for your paths —
      `git log --stat -3`, and search your own text in `git show HEAD:<path>` — before doing anything
      else.
   3. Report the commit hash you verified by FINDING YOUR OWN CHANGE INSIDE IT, not the hash a
      successful command printed: under parallel work the hash may belong to someone else's commit.
   4. Report "Task {N} complete" with the verified hash — the lead runs the review from here.
   5. After each patch cycle the lead sends (tests pass): commit the same way, `fix: address review cycle {M} for task {N}`.
   6. Receipts and findings are committed by the lead in Phase 3, not by you.
   ```

   If task has `reviewers: [none]` — no lenses run. The teammate works independently, commits code with message `feat|fix: task {N} — {brief description}` (tests pass), and reports completion directly to team lead.

   Every task gets a spawned teammate — even tasks with no skills and no reviewers (operational tasks, MCP interactions, benchmarks, manual steps). The lead never executes task work directly.

   **Lead-run review** — after a teammate reports "Task {N} complete" with a verified commit hash,
   and only for tasks whose `reviewers` is not `[none]`:

   1. Resolve the lens set: `reviewers: [quick]` → quick; `[thorough]` or `[]` → thorough (`prod-readiness` only when the tech-spec `level` is L1+); a legacy
      explicit list (`code-reviewer`, `security-auditor`, `test-reviewer`, …) → thorough. Catalog and
      prompts: `.claude/shared/review-lenses/README.md`.
   2. Write the unified diff from the card's `start_commit` over the task's `owns_paths` (tracked and
      untracked) to `{scratchpad}/task-{N}-review/diff.patch`. The diff goes to lenses as a path, never
      inline.
   3. Launch every lens of the set **in one turn** as context-free subagents (`general-purpose`,
      `model: "sonnet"`; `security` → `subagent_type: "security-auditor"`), `run_in_background: false`,
      prompt = the lens file with `{diff_file}`, `{card}`, `{report}`
      (`{feature_dir}/logs/working/task-{N}/{lens}-1.json`) and, for `intent-alignment`,
      `{verbatim_intent}` substituted. Key names in the envelope are quoted from
      `.claude/scripts/taskflow.py` — say so in the prompt and do not paraphrase them. Read no report
      before all lenses are launched. Each lens gets its own scratchpad subdirectory
      `{scratchpad}/task-{N}-{lens}/`.
   4. Triage by `.claude/shared/review-lenses/triage.md`: verify every finding in code yourself,
      grade it (`high / medium / low / false / maybe-false`) with evidence, log every one in the
      card's `## Review Triage Log`, group by root cause, route `patch / ask / defer`. Lens
      severities are not read.
   5. `patch` → one SendMessage to the SAME teammate (by its name — a fresh spawn is not
      re-engagement) with the finding list in the format its prompt announced. When it replies, re-run
      the card's `## Verification Steps` yourself and rewrite `diff.patch`. Max **2 patch cycles**;
      a third → Escalation. `ask` → stop the task, put the question to the user in one message.
      `defer` → `{feature_dir}/deferred-work.md` (`- source: tasks/{N}.md / summary / evidence`).
   6. Close in the findings mechanism without touching scripts: run
      `python3 .claude/scripts/findings-sync.py work/{feature} {N}`, then write
      `{feature_dir}/logs/working/task-{N}/{lens}-2.json` per lens —
      `{"reviewer":"{lens}","round":2,"status":"triaged","findings":[],"closures":[…]}`, one closure
      per fingerprint from `logs/receipts/task-{N}/FINDINGS.md`: `verdict: closed` for patched,
      `false`, rejected `low` and `defer` (evidence = triage verdict + proof), `open` only for `ask`
      awaiting the user. Run `findings-sync.py` again and confirm it matched every closure
      (a sync that matched 0 of 7 is loud only if you look).
   7. `logs/working/` is gitignored; the durable record is `logs/receipts/task-{N}/` (findings +
      `FINDINGS.md`), committed by the receipt step in Phase 3. Confirm with `git check-ignore -v`.

   Blind review holds: a lens receives the diff, the card and the specs by path — never the
   teammate's report, `decisions/task-{N}.md` or earlier lens reports.

4. All teammates of the wave work in parallel. Lead waits for each to report "Task complete", then runs the review lenses for that task (above) while the others continue.

### Audit Wave tasks

Audit Wave is conditional (tech-spec-planning step 5: level ≥ L1 and an external write, a server unit or ≥ 4 code tasks); a tech-spec without it carries a one-line skip reason — check the reason against the tasks before accepting the plan, and add the wave if the reason is false. When present, its tasks (Code Audit, Security Audit, Test Audit) have `reviewers: [none]` — each auditor teammate IS the review. Spawn them as standard teammates (general-purpose, opus), each loads its methodology skill.

Each auditor:
- Reads decisions.md to understand what was done in each task
- Reads all source files listed in tech-spec "Files to modify" across all implementation tasks
- Reviews the final state of code holistically (full files, not diffs)
- Writes report to `{feature_dir}/logs/working/audit/{auditor-name}.json`
- Writes decisions.md entry, reports to lead

After all 3 reports:
- All clean → proceed to Final Wave
- Issues found → spawn a fixer teammate (ad-hoc, code-writing skill); the lead reviews its commit with the **thorough** lens set and triages (max 2 patch cycles). After closure → proceed to Final Wave. Unresolved → escalate (see Escalation).

### Ad-hoc agents

When lead spawns an agent outside the original execution plan (to fix audit findings, handle escalations, complete missing work):

1. Lead assigns a skill and reviewers matching the type of work:
   - Code changes → skill: `code-writing`, reviewers: `[thorough]` (`[quick]` when the fix is ≤100 lines in ≤5 files and touches no external write)
   - Prompt changes → skill: `prompt-master`, reviewers: prompt-reviewer (role reviewer, run as a lens with its own agent)
   - Skill changes → skill: `skill-master`, reviewers: skill-checker
   - Deploy/CI changes → skill: `deploy-pipeline`, reviewers: deploy-reviewer
   - Infrastructure changes → skill: `infrastructure-setup`, reviewers: infrastructure-reviewer + `security` lens
   - Other tasks (research, config, manual steps) → no skill, no reviewers. Agent follows lead's instructions directly.
2. The ad-hoc agent writes a decisions.md entry (same template as planned tasks)
3. Standard review protocol: agent commits → lead runs lenses and triages → patch message → max 2 cycles
4. Lead verifies decisions.md entry exists before considering ad-hoc work complete

**Checkpoint:** all teammates reported "Task complete", decisions.md entries written.

## Parallel writers in one shared worktree

Waves exist to run several executors at once, so parallel writing is the normal mode, not a
malfunction. Splitting the work by paths does not split the tools the work is committed with.

- **The index is shared state, not the property of whoever wrote into it.** `git add` creates no
  ownership: between "staged" and "committed" the contents belong to everyone, and any neighbour
  committing "everything staged" takes your files along with theirs. Hence the one-command
  stage-and-commit rule in the executor prompt, and hence "no changes added to commit" must be read
  as a possible signal that a neighbour's commit carried your files away.
- **A pathspec names a file, not a writer's contribution to it.** Any file several executors append
  to is a shared mutable resource, and committing it by name commits the neighbour's half-finished
  hunk under your message. Prefer one file per writer (`decisions/task-{N}.md`, merged by the lead).
  Where a shared file is unavoidable, the writer runs `git diff` on that path immediately before the
  commit and aborts if the diff contains lines outside its own section; at minimum it compares the
  path's diffstat against the size of the edit it just made.
- **A control run must name and pin its version.** See the reviewer prompt: HEAD and
  `git status --short` before and after, clean checkout of the reviewed SHA on any divergence.
 
- **An ownership check built on a commit range measures something other than what it names.**
  "What changed since commit X" and "what this executor changed" coincide only until the first
  parallel writer. A file that appears in the range but in none of the task's own commits is
  **foreign**, not a violation: it is reported with the name of the commit that introduced it, and it
  does not fail the receipt. Tell executors explicitly: *a file outside your `owns_paths` that you did
  not change is a process finding you report — never something you "fix" by widening `owns_paths` or
  moving `start_commit`.* Both of those repairs are cheaper than an investigation, look identical to
  honest work, and switch off exactly the signal the check exists to raise — leaving the honest
  executor blocked and the careless one holding a green receipt.
- **Each agent writes only inside its own scratchpad subdirectory** (see Phase 2).

## Phase 3: Wave Transition

1. If task had Smoke/User verification steps — confirm teammate reported verification results. Missing results without explanation → ask user whether to proceed.

0a. **Count outputs against inputs; do not accept a prose summary as a completion report.** For any
   task that was a bulk job over a set (N files converted, N records processed, N documents written),
   independently compare the actual output count in the target scope against the actual input count
   before treating the task as complete. A dispatched agent can end its turn — and be marked
   "completed" by the harness — while shell work it backgrounded is still running or already killed,
   and a partial run and a complete run produce similarly worded success messages. Hedging language in
   an agent's own final message ("is running", "will check back", "in the background") is a signal to
   re-verify, not to accept. The same applies to the lead's own long-running steps: a recent progress
   line is evidence of progress, never of completion — look for the terminal marker the job emits
   deliberately at the end.

0b. **After a context compaction, reconcile from disk before believing anything.** First step on
   resume is `ListAgents` plus a comparison of `logs/working/findings/` and `logs/receipts/` against
   `git status` — not waiting for a notification from an agent that no longer exists. Open findings
   that survive only in a compaction summary are open findings you are about to commit as reviewed.
1a. **Task receipts (only if the repo has `.claude/scripts/task-accept.py`; other repos keep the original flow):** run `python3 .claude/scripts/task-accept.py work/{feature} {N}` for each task of the wave. Exit 0 → proceed. Exit 1 → the task stays `in_progress`: spawn an ad-hoc fixer with the printed reasons, then re-run. The receipt — not the teammate's "Task complete" — is the definition of done. In the same repos also run `python3 .claude/scripts/wave-check.py work/{feature}` before spawning any wave in Phase 2 and refuse to spawn on exit 1.
2. Update task frontmatter: `status: in_progress` → `status: done`. Read only frontmatter (`limit=15`), then Edit the status field. Do not read full task content.
3. Git commit: `chore: complete wave {N} — update task statuses and decisions` (include `work/{feature}/logs/receipts/` when present). Code is already committed by teammates.
4. Update `work/{feature}/logs/checkpoint.yml`: set `last_completed_wave`, update task statuses, set `next_wave`.
5. Next wave → Phase 2

**Checkpoint:** all wave tasks done, committed, checkpoint updated.

## Phase 4: User Review

All waves done including Final Wave (QA, deploy if applicable, post-deploy verification if applicable).

1. Show results: what was built, key decisions, QA report summary
2. Describe what to check manually (from execution plan "user checks" section)
3. Issues found → spawn ad-hoc agent to fix (see "Ad-hoc agents" in Phase 2) → lenses + triage → commit (max 2 patch cycles). If unresolved → escalate (see Escalation).
4. All ok → finalize, shutdown team, delete `work/{feature}/logs/checkpoint.yml`

## Escalation

Call user when:
- 2 patch cycles exhausted with `high`/`medium` findings still open, or a finding routed `ask`
- Teammate reports blocker or ambiguous requirement
- Task depends on unavailable MCP tool or external service

When escalating:
1. Stop all work on the blocked task/wave
2. Report to user: what failed, what was tried (every cycle), what remains unresolved
3. Write decisions.md entry: summary of attempts + unresolved findings
4. Git commit: `chore: escalate task {N} — unresolved after review triage`
5. Wait for user decision before continuing

## Self-Verification

- [ ] Execution plan created and approved
- [ ] All tasks executed, reviewed by lenses where applicable (max 2 patch cycles each, every finding in the Triage Log), `decisions/task-{N}.md` written for every task
- [ ] Every spawn prompt said the task card is authoritative, and named the agent's own scratchpad subdirectory
- [ ] Field names in every script-parsed artefact were quoted from the consuming parser, and the consumer's match count was checked once
- [ ] For every bulk task: output count compared against input count, not taken from the agent's summary
- [ ] Review evidence derived into a tracked path (`logs/receipts/`), verified with `git check-ignore`
- [ ] Each executor's reported commit hash was verified by finding its own change inside that commit
- [ ] All waves committed (including Final Wave)
- [ ] User reviewed and approved
