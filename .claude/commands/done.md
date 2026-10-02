---
description: |
  Finalize a completed feature: run acceptance-criteria receipts (re-runnable verify commands),
  check declared footprint against git actuals, update project knowledge files,
  archive feature directory to work/completed/.

  Use when: "фича готова", "заверши фичу", "done", "финализация", "закрой фичу", "перенеси в completed"
---

# Done — Finalize Feature

## Step 1: Load Documentation Skill

Use Skill tool: `documentation-writing`

## Step 2: Identify Feature

User typically provides feature directory with the command (e.g., `/done work/my-feature`).
- If provided → use it
- If not → ask: "Which feature to finalize? Provide path to work/{feature}/ directory."

## Step 3: Read Feature Artifacts

Read these files from the feature directory:
1. `user-spec.md` — what was planned
2. `tech-spec.md` — how it was implemented
3. `decisions.md` — what decisions were made during implementation

If `decisions.md` is missing or sparse, use `git log --oneline` for feature-related commits to understand what changed.

**Completeness check:** If the feature looks incomplete (tasks not marked done in tech-spec, missing implementation, failing tests) — warn the user: "Feature appears incomplete: {reason}. Continue with finalization anyway?"

**Task receipts check:** for every `work/{feature}/tasks/*.md` with `status: done`, `work/{feature}/logs/receipts/task-{N}/acceptance.json` must exist with `accepted: true` and `task_sha256` equal to the current hash of the task body (`python3 .claude/scripts/task-accept.py` recomputes it; a mismatch means the task text changed after acceptance). Missing or `accepted: false` → list those tasks verbatim; they were marked done outside the flow. The user may accept them explicitly (record `task N: done without receipt (accepted by user: {reason})` in receipts.md) — never silently. Features whose tasks predate `owns_paths` (no receipts dir at all) get one note "feature predates task receipts" and are not blocked.

## Step 4: Run Receipts

"Done" is a re-runnable command, not a sentence. Settle every acceptance criterion with a script, not with the implementer's word.

1. Parse `## Acceptance Criteria` from tech-spec.md. For each criterion with a `verify:` command — run the command via Bash (from the repo root) and compare the actual result against the expected outcome. Record `hit` or `miss`. Do not skip a command because the code "obviously works".
2. If `work/{feature}/grill-log.md` exists — its entries are receipts too: run every `Verify:` command the same way and include the results in the ledger (prefix `G-N`). Entries marked `**OPEN**` are surfaced to the user as unresolved grill branches — finalizing with open branches requires explicit user acknowledgment.
3. Criteria marked `verify: manual — ...` — list them for the user as UNVERIFIED with what they need to check by hand.
4. Write the ledger to `work/{feature}/receipts.md`:

   ```markdown
   # Receipts — {feature}
   Run: {YYYY-MM-DD}, commit {short-sha}

   | AC | Command | Expected | Actual | Verdict |
   |----|---------|----------|--------|---------|
   | AC-1 | `npm test` | exit 0 | exit 0 | hit |
   | AC-2 | `curl ...` | 200 | 500 | **miss** |
   | AC-3 | manual — user checks UI | — | — | unverified |
   ```

5. **Any miss blocks finalization.** Stop and show the user the failing receipts verbatim (command + actual output). Options: fix now and re-run receipts, or the user explicitly accepts the miss — record `miss (accepted by user: {reason})` in receipts.md. Never silently downgrade a miss.
6. Old specs without `verify:` lines: fall back to the plain checklist, note in the report that the feature predates receipts.

## Step 5: Footprint Check

Compare the declared change size against what git actually recorded.

1. Read `footprint` and `start_commit` from tech-spec frontmatter. If either is missing (spec predates the footprint field) — skip with a note in the report.
2. Compute actuals:
   ```bash
   git diff --numstat {start_commit}..HEAD -- . ':(exclude)work/' | awk '{add+=$1; files+=1} END {print files " files, +" add " lines"}'
   ```
3. Compare with the declaration (`files_modified + files_new`, `loc_estimate`):
   - Actual > 2x declared → warn: possible scope creep — list the biggest unplanned files from numstat.
   - Actual < 0.5x declared → warn: feature may be incomplete.
4. New dependencies: check package.json / requirements.txt changes in the diff against declared `new_deps`. An undeclared new dependency → warn explicitly.
5. Append the footprint verdict (declared vs actual, ok / creep / under) to `work/{feature}/receipts.md`. Footprint mismatches warn but do not block — the user decides.

## Step 6: Update Project Knowledge

If `.claude/skills/project-knowledge/references/` does not exist or is empty — skip this step, inform the user that project knowledge has not been initialized.

Otherwise, read current PK files and update only those affected by the feature:
- `architecture.md` — new components, changed structure, data model / schema changes
- `patterns.md` — new project-specific patterns, testing approaches, business rules
- `deployment.md` — deployment or monitoring changes
- If the project has a backlog file, note any status updates for the user

Apply quality principles from documentation-writing skill: no code examples, no obvious content, only project-specific information.

## Step 7: Archive

Move `work/{feature}/` → `work/completed/{feature}/` (create `work/completed/` if it doesn't exist). `receipts.md` travels with the feature — it is the permanent evidence of what was verified.

## Step 8: Commit & Report

1. Commit PK file changes and feature archive move.
   ```
   docs: update project knowledge after {feature-name}
   ```

2. Report to user:
   - What was done (brief summary from specs)
   - Receipts verdict: N hits / N misses (accepted) / N unverified-manual
   - Footprint verdict: declared vs actual (ok / scope creep / under)
   - What PK files were updated and what changed
   - Feature archived to `work/completed/{feature}/`

## Self-Verification

- [ ] Documentation-writing skill loaded
- [ ] Feature artifacts read and understood
- [ ] Completeness assessed (user warned if incomplete)
- [ ] Receipts executed — every `verify:` command actually ran; results in receipts.md
- [ ] No unresolved misses (fixed, or explicitly accepted by user with reason recorded)
- [ ] Footprint compared against `git diff --numstat` (or skip noted for pre-footprint specs)
- [ ] PK files updated (only affected ones)
- [ ] Feature archived to work/completed/ (receipts.md included)
- [ ] Changes committed
- [ ] Report delivered to user
