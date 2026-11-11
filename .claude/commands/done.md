---
description: |
  Finalize a completed feature: trace original requirements to verified receipts,
  check declared footprint against git actuals, update current business scenarios and project knowledge,
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

**Completeness check:** Record incomplete work as specific gaps for Step 4. Task checkboxes and implementer reports are not evidence; a general approval to finalize does not accept individual gaps.

**Task receipts check:** for every `work/{feature}/tasks/*.md` with `status: done`, `work/{feature}/logs/receipts/task-{N}/acceptance.json` must exist with `accepted: true` and `task_sha256` equal to the current hash of the task body (`python3 .claude/scripts/task-accept.py` recomputes it; a mismatch means the task text changed after acceptance). Missing or `accepted: false` → list those tasks verbatim; they were marked done outside the flow. The user may accept them explicitly (record `task N: done without receipt (accepted by user: {reason})` in receipts.md) — never silently. Features whose tasks predate `owns_paths` (no receipts dir at all) get one note "feature predates task receipts" and are not blocked.

## Step 4: Run Receipts

"Done" is a re-runnable command, not a sentence. Settle every acceptance criterion with observed evidence, preferably a repeatable check, not with the implementer's word.

Before running checks, read the existing `receipts.md`, if present. Map every requirement, constraint and acceptance scenario in `user-spec.md` to the acceptance criteria in `tech-spec.md`; split compound requirements into separate assertions. Use existing IDs, or a section reference and short quote when IDs are absent; do not rewrite specs to assign IDs. Apply only explicitly approved requirement changes, with their approval references. Never adjust requirements to match the implementation.

1. Inspect current implementation in the feature's scope against this mapping. Preserve all technical acceptance criteria, even those without a direct user requirement (label their source `technical`); a missing mapping must remain visible. For each criterion with a `verify:` command — run the command via Bash (from the repo root) and compare the actual result against the expected outcome. Record `hit` or `miss`. Do not skip a command because the code "obviously works". Commands remain subject to existing authorization and safety rules; an unauthorized or unavailable check is `unverified`, not permission to execute it.
2. If `work/{feature}/grill-log.md` exists — its entries are receipts too: run every `Verify:` command the same way and include the results in the ledger (prefix `G-N`). Entries marked `**OPEN**` are surfaced to the user as unresolved grill branches — finalizing with open branches requires explicit user acknowledgment.
3. Criteria marked `verify: manual — ...` — record observed evidence or the user's explicit confirmation of the specific check and its result. Without that evidence, mark `unverified` and state what must be checked; never infer a pass from approval to close the feature.
4. Write the ledger to `work/{feature}/receipts.md`:

   ```markdown
   # Receipts — {feature}
   Run: {YYYY-MM-DD}, commit {short-sha}

   | Source requirement / assertion | AC | Check | Expected | Actual / evidence | Verdict |
   |--------------------------------|----|-------|----------|-------------------|---------|
   | US-1 / valid login | AC-1 | targeted login test | login succeeds | observed successful login | hit |
   | US-2 / expired session | — | no matching criterion | session rejected | no evidence | missing |
   | technical | AC-3 | manual — user checks UI | no overflow | not checked | unverified |
   ```

5. **Any gap blocks finalization and archiving:** `missing` criterion/implementation, `partial` coverage, `contradicts` the approved requirement, `miss` check, or `unverified` evidence (including manual checks). Show each gap with its source and sanitized evidence. Fix and re-run, or obtain explicit user acceptance of that specific gap with a reason; record the original verdict plus `accepted by user`, reason and approval reference. Accepted exceptions are not passes. An OPEN grill branch still requires explicit acknowledgment.
6. Old specs without `verify:` lines: use available targeted tests, inspection or manual checks and record the method, expected result and actual evidence. Note the legacy format; age alone never waives a gap. If `user-spec.md` or another required spec is absent, record the unavailable comparison as `unverified` and require explicit acceptance of that limitation; do not invent requirements from code or silently treat tech-spec as the original intent.
7. On re-run, update results and retain the history of accepted exceptions in the same `receipts.md`. Record the requirement/assertion text and specific gap with each exception; it applies only while both are unchanged. Changed requirements or gaps require renewed acceptance. Recheck previously accepted items and mark resolved gaps as resolved, without deleting the approval history.

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

## Step 6: Update Current Business Scenarios and Project Knowledge

Always read each affected project's existing README and linked domain documents. Reconcile added, changed and removed business scenarios against the approved requirements and evidence from Step 4, including their constraints and exceptions. Update the existing authoritative description and remove rules made false by the change; check surrounding sections for contradictions. If no scenario description exists, add a compact section to the existing README. Do not create a new document or duplicate rules across README and project knowledge.

Record a short scenario-update summary in `receipts.md`: added/changed/removed scenarios and links to their current documentation sections. Keep links valid after the feature is archived. If business behavior did not change, record that verdict and why. Resolve documentation contradictions before archiving; unverified behavior must remain explicitly unverified, even when the user accepted the verification gap. If no existing documentation destination is available, report the blocker instead of silently skipping or creating a new document.

If `.claude/skills/project-knowledge/references/` is absent or empty, report that project knowledge is not initialized; skip only the PK updates below, never the scenario update above. Otherwise, read current PK files and update only those affected by the feature, linking to the authoritative scenario description instead of duplicating it:
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
   - Requirement coverage and receipts verdict: verified assertions, gaps by type, and explicitly accepted exceptions (never counted as passes)
   - Footprint verdict: declared vs actual (ok / scope creep / under)
   - Business scenarios updated and links to their current descriptions (or why unchanged); PK files updated, or PK not initialized
   - Feature archived to `work/completed/{feature}/`

## Self-Verification

- [ ] Documentation-writing skill loaded
- [ ] Feature artifacts read and understood
- [ ] Every original requirement, constraint and scenario assertion mapped; only approved deviations applied
- [ ] Receipts recorded — each `verify:` command ran or its unverified gap was explicitly accepted; actual results remain distinct from exceptions
- [ ] No unaccepted gaps, including missing criteria and unverified manual checks; exception history preserved and applicability rechecked
- [ ] Footprint compared against `git diff --numstat` (or skip noted for pre-footprint specs)
- [ ] Current business scenarios reconciled in existing docs, false rules removed, receipt links valid after archive (or no behavior change justified)
- [ ] PK files updated where initialized; absence did not skip scenario documentation
- [ ] Feature archived to work/completed/ (receipts.md included)
- [ ] Changes committed
- [ ] Report delivered to user
