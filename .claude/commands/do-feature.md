---
description: |
  Execute feature with team of agents — waves, reviews, commits.

  Use when: "выполни фичу", "do feature", "execute feature", "запусти фичу"
---

# Do Feature

Execute a full feature using a team of agents.

## Step 1: Load Skill

Invoke Skill tool: `Skill(skill: "feature-execution")`

## Step 2: Find Feature

1. User provides feature path or name
2. Read `work/{feature}/tech-spec.md` — verify exists and approved
3. Read `work/{feature}/tasks/` — verify task files exist
4. If tech-spec or tasks missing → stop, tell user what's needed

## Step 3: Execute

Follow the loaded feature-execution skill workflow.
The skill checks `checkpoint.yml` in Phase 1 and handles resume automatically.

**Blind verification rule (overrides skill defaults):** when spawning any reviewer, auditor, or QA agent — pass specs and git diff only. Never pass executor summaries, decisions.md, or other agents' reports as context: verifiers derive verdicts from the specs and the code tree alone, and executor claims they happen to see are hypotheses to check, not evidence. Pre-deploy QA must run the tech-spec Acceptance Criteria `verify:` commands (receipts) itself rather than trusting task checkboxes.

**Receipt rules (override skill defaults; the lead runs these — they are Bash orchestration, not task work):**

1. **Before every wave** — `python3 .claude/scripts/wave-check.py work/{feature}`. Exit 1 → do not spawn the wave; show the violations to the user (a read/write hit means a task depends on a wave-mate and must move to a later wave). Tasks listed as `skipped_no_owns_paths` run without ownership enforcement — say so explicitly in the execution plan.
2. **Teammate prompt additions** — the teammate sets `start_commit: {git rev-parse HEAD}` in the task frontmatter when it starts, writes only inside `owns_paths`, and on each re-review round hands the reviewer `logs/receipts/task-{N}/FINDINGS.md` (after `findings-sync.py`) so the reviewer returns `closures[]` per fingerprint.
3. **Before marking a task `done` (Phase 3)** — `python3 .claude/scripts/task-accept.py work/{feature} {N}` for every task of the wave. Exit 0 → `done`. Exit 1 → the task stays `in_progress`; spawn an ad-hoc fixer with the printed reasons (never edit `acceptance.json`, never set `done` on `accepted: false`). Three failed receipts → escalate.
4. **Wave commit** includes `work/{feature}/logs/receipts/` — the receipts are the evidence; `logs/working/` is gitignored on purpose.
