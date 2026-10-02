---
description: |
  Execute task from tasks/*.md with quality gates.

  Use when: "выполни задачу", "сделай таску", "do task", "execute task", "запусти задачу"
---

# Do Task

Execute a spec-driven task with validation and status tracking.

## Step 1: Read Task

1. Read task file (user provides path or task number)
   - If user didn't specify → ask: "Which task to execute?"
2. Derive feature directory from task path: `work/{feature}/tasks/N.md` → `work/{feature}/`
   All `logs/` paths in the task (Reviewers section, What to do, Acceptance Criteria) are relative to this feature directory. Resolve them as `{feature_dir}/logs/...` when creating files.
3. Verify task status is `planned` (if not → ask user before proceeding)
4. Update task frontmatter: `status: planned` → `status: in_progress`, and set `start_commit: {git rev-parse HEAD}`.
   The commit is the baseline for `owns-check.py` and the acceptance receipt — without it neither can run.
   Frontmatter `owns_paths` is the only place you may write (plus `work/{feature}/`); `never_touch` wins over
   everything. A build error in a file outside `owns_paths` is not yours to fix — report it, do not "helpfully" edit.
5. Read every file listed in the task's "Context Files" section

## Step 2: Execute

1. Load each skill listed in the task (frontmatter `skills: [...]` and "Required Skills" section)
   - If a skill is not found → warn user, continue with remaining skills
   - If task has no skill (frontmatter `skills: []` or absent) → read the task, execute "What to do" and "Verification Steps" directly. For tasks with user instructions → show the instruction to user, wait for confirmation.
2. Follow loaded skill workflow
3. Git commit implementation (code + tests pass): `feat|fix|refactor: task {N} — {brief description}`
4. Review — by lenses, not role reviewers (`.claude/shared/review-lenses/README.md`):
   1. Lens set from frontmatter `reviewers`: `[quick]` → quick; `[thorough]`, `[]` or a legacy role list → thorough; `[none]` → skip to Step 3.
   2. Write the unified diff from `start_commit` over `owns_paths` (untracked included) to `<scratchpad>/task-{N}-review/diff.patch`.
   3. **Blind review rule:** launch every lens of the set in one turn as context-free subagents with `{diff_file}`, the task card and the specs by path — never your implementation summary, decisions.md or earlier reports. Reports go to `{feature_dir}/logs/working/task-{N}/{lens}-1.json` in the envelope the README quotes from `taskflow.py`.
   4. Triage by `.claude/shared/review-lenses/triage.md`: verify each finding in code, grade it, log it in the card's `## Review Triage Log`, route `patch / ask / defer`. `patch` → fix, re-run tests, git commit: `fix: address review cycle {M} for task {N}`; max 2 cycles. `ask` → stop and ask the user. `defer` → `{feature_dir}/deferred-work.md`.
   5. Close: `python3 .claude/scripts/findings-sync.py work/{feature} {N}`, then `{lens}-2.json` with `closures[]` per fingerprint from `logs/receipts/task-{N}/FINDINGS.md` (`closed` + evidence; `open` only for `ask`), run the sync again and confirm every closure matched.

## Step 3: Verify

1. Check each acceptance criterion from task file
2. If task has "Verification Steps → Smoke" → execute each smoke command, record results in decisions.md Verification section
3. If task has "Verification Steps → User" → ask user to verify, wait for confirmation
4. If any verification fails → fix → re-run tests → re-run the lens set on the new diff → re-verify
   - After 2 failed cycles → stop, report failures to user, keep status `in_progress`
   - Tool unavailable → document, suggest manual check

## Step 4: Complete

0. **Receipt first.** Run `python3 .claude/scripts/task-accept.py work/{feature} {N}`. It re-runs every Automated/Smoke
   verification command itself, runs `owns-check.py`, syncs reviewer findings into `logs/receipts/task-{N}/findings/`
   and writes `logs/receipts/task-{N}/acceptance.json`. Exit 0 = `accepted: true`.
   Exit 1 → read the printed reasons (failed command, leak outside `owns_paths`, `changes_required`, open critical
   finding), fix, go back to Step 2/3 (new review cycle if code changed), re-run. After 3 failed attempts → stop,
   keep `in_progress`, report to user. Never set `done` on a task whose receipt says `accepted: false` and never
   edit `acceptance.json` by hand — a hand-edited receipt is worse than none.
1. Read template `.claude/shared/work-templates/decisions.md.template (fallback: ~/.claude/shared/work-templates/decisions.md.template)` and write a concise execution report to `work/{feature}/decisions.md`. Follow template format strictly — no extra sections.
2. Update task frontmatter: `status: in_progress` → `status: done` (only with `accepted: true`)
3. Update tech-spec: `- [ ] Task N` → `- [x] Task N`
4. Git commit: `chore: complete task {N} — update status and decisions`

## Self-Verification

- [ ] Task status is `done`
- [ ] Tech-spec checkbox updated
- [ ] decisions.md entry written with reviews and verification results
- [ ] Git commit created with task reference
- [ ] Every acceptance criterion from task file is met
