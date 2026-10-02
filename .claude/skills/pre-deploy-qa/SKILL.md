---
name: pre-deploy-qa
description: |
  Pre-deploy acceptance testing methodology: run test suite (unit/integration/E2E),
  verify acceptance criteria from user-spec and tech-spec. Does not require live environment.

  Use when: "приёмочное тестирование", "pre-deploy qa", "проверь перед деплоем",
  "run tests and check AC", "запусти qa", "проверь acceptance criteria",
  "тестирование фичи", "qa", "проверь фичу"
---

# Pre-deploy QA

## Input Requirements

Read before starting:
- `user-spec.md` — acceptance criteria
- `tech-spec.md` — technical acceptance criteria
- `decisions.md` — deviations from plan (if exists)
- Project Knowledge — architecture.md, patterns.md (incl. Testing & Git Workflow sections)

If user-spec or tech-spec missing — request before proceeding.

## Verification Directions

Three verification directions (order doesn't matter):

### Test Suite

Run all tests (unit, integration, E2E). All must pass.

- Identify test runner from project config (package.json, pyproject.toml, Makefile, etc.)
- Run full test suite
- Record: total tests, passed, failed, skipped

### Acceptance Criteria

Check every criterion from user-spec and tech-spec:

- **passed** — criterion met, evidence provided
- **failed** — the feature exists but does not meet the criterion
- **not_verifiable** — cannot be checked without live environment, external service, or MCP tool (scope of post-deploy-qa)

For each criterion — provide evidence (test name, code path, log output).

**Only an event nobody ordered proves the automatic part.** A mechanism can be fully installed and
still never fire, and every one of these reads as done in a report: a timer whose only run came from
`enable --now` (that run is the manual start, not a tick); a manual end-to-end pass along the
production path (proves the path, not the automation, and the team will remember it as "the
automation ran"); a permission created by a migration but held by no role (the question is not
"does the right exist" but "does anyone hold it"); a manual procedure that was *written* rather than
executed; a queue consumer that has processed only records the operator inserted by hand.

Such a criterion is `not_verifiable` — never `passed`. Do not invent a new `status` value for it:
the orchestrator parses that field, `passed` is defined as "zero criticals", and `summary.notVerifiable`
counts it. The distinction lives one level down, in the `deferredToPostDeploy` entry, as
`reasonKind` — and the entry uses the field names the report already has, `reason` and
`verificationCondition`, rather than new ones:

```json
{
  "criterion": "Digest is sent every morning by the timer",
  "reasonKind": "automation-not-observed",
  "reason": "Timer unit installed; the single observed run was started manually via `systemctl enable --now`",
  "verificationCondition": "One run whose timestamp falls on a scheduled tick that nobody triggered, plus its output at the destination",
  "verificationSteps": "After deploy, wait for the next scheduled tick; read the journal for a run with no operator in its provenance, then check the destination"
}
```

`reasonKind` has exactly two values and is mandatory on every deferred entry:

- `needs-live-environment` — the check is impossible here: no live service, no external system, no
  MCP tool. Deploying makes it checkable.
- `automation-not-observed` — the mechanism is fully built and the check is possible, but the one
  observation that would prove it fires has not happened yet. Deploying does not make it checkable;
  **waiting for an unrequested event does.**

The two are not interchangeable, and collapsing them is what lets an installed-but-never-fired
mechanism ship as done: the first is a limitation of the environment, the second is a gap in the
evidence. `verificationCondition` on an `automation-not-observed` entry names that single
unrequested event, and nothing else closes it.

**An acceptance criterion that quotes a command's expected output is verified by comparing that
output**, not by the command's exit code. The two drift, and the exit code is the one that keeps
reporting green.

### Coverage Verification

After test suite passes, verify that tests actually exercise the feature:

- For each file in the feature's scope (from tech-spec "Files to modify"): verify a corresponding test exists. Feature code without any test → severity `critical`
- If project has coverage tooling configured (jest --coverage, pytest --cov, vitest --coverage) — run it. Coverage of feature files dropping below project threshold → severity `critical`
- For each acceptance criterion with status `passed` — verify the linked test actually exercises the relevant code path, not just an import check or mock-only test. Test that doesn't actually test the feature behavior → severity `major`
- Edge cases mentioned in user-spec (error handling, boundary values, empty states) — verify they have corresponding tests. Missing edge case test for M/L features → severity `major`
- **Confirm the runner actually collects each acceptance-critical check.** A check written as a
  standalone script, or living outside the runner's discovery pattern, is invisible to the project's
  test command, so a red criterion reports green forever. The suite reports the tests it *collected*,
  not the tests that *exist* — compare the collected list against the test files on disk, and treat
  any acceptance-critical file missing from the collected list as severity `critical`
- **A check's contract is wider than the field that broke.** When a criterion or a check was written
  from one observed defect, verify it against the whole contract of the thing it guards: every field
  the consumer reads, every path that produces it, and both ends of any name or vocabulary agreement.
  Two documents that name the same verdict field with different vocabularies, or state the same
  report's path differently, each pass their own check and fail together — the consumer can only read
  one of them. Severity `critical` when a consumer reads a path or a value no producer writes
- **Mock-only green says nothing about a live contract.** A required field the real API rejects, and
  a race between two components, are invisible to a mock suite of any size. Criteria whose truth
  depends on a live counterparty are `not_verifiable` here, not `passed`

## Severity Classification

- **critical** — acceptance criterion failed, tests fail, core functionality broken
- **major** — works but with significant issues (edge cases, UX bugs, degraded behavior). Escalate to critical if it affects data integrity or core user workflow.
- **minor** — cosmetic, inaccuracies, improvements

## Output

### JSON report → `logs/working/qa-report.json`

Full report saved to file. Reason: orchestrator parses this to decide pass/fail.

```json
{
  "status": "passed | failed",
  "summary": {
    "totalChecks": 0,
    "passed": 0,
    "failed": 0,
    "notVerifiable": 0,
    "criticals": 0,
    "majors": 0,
    "minors": 0
  },
  "testSuite": {
    "status": "passed | failed",
    "details": "All 42 tests passed"
  },
  "acceptanceCriteria": [
    {
      "criterion": "User can login with email",
      "status": "passed | failed | not_verifiable",
      "evidence": "Test login_test.py::test_email_login passes"
    }
  ],
  "findings": [
    {
      "severity": "critical | major | minor",
      "title": "Login fails for emails with + sign",
      "expected": "Login succeeds",
      "actual": "400 Bad Request",
      "reproduction": "Steps to reproduce..."
    }
  ]
}
```

Status decision: `passed` if zero criticals, `failed` if one or more criticals.

### decisions.md entry — concise summary only

Write a brief entry to decisions.md following the template (`.claude/shared/work-templates/decisions.md.template (fallback: ~/.claude/shared/work-templates/decisions.md.template)`). Link to `logs/working/qa-report.json` for the full report.

Example:
```
## Task 9: Pre-deploy QA

**Status:** Done
**Agent:** qa-runner
**Summary:** QA passed. 391 tests green, 28 acceptance criteria checked (25 passed, 3 not_verifiable). No blockers.
**Deviations:** None.

**Verification:**
- Full report: [logs/working/qa-report.json]
```

## Guidelines

- Work from specs only (user-spec, tech-spec, decisions.md). Task files (tasks/*.md) are already verified by reviewers and are outside QA scope.
- Account for decisions.md — deviations from original plan may be justified.
- Every finding includes concrete reproduction: steps, expected vs actual.
- Criteria requiring live environment or MCP tools — mark as `not_verifiable`, note that post-deploy verification is needed.
- Empty findings array = clean audit.

### Deferred to Post-deploy

If any acceptance criteria are marked `not_verifiable` — add a `deferredToPostDeploy` section to the JSON report. This section is the handoff contract: post-deploy QA reads it and verifies each deferred criterion on live environment.

For each deferred criterion, specify:
- Which criterion (ID and text)
- Why it cannot be verified pre-deploy
- What conditions are needed to verify it (live data, MCP tool, user action)
- Concrete verification steps for post-deploy agent
- **The assumptions the deferral itself rests on.** A deferred criterion usually carries unverified
  prose about production — its data volume, the field names of its API, who holds which right — and
  that prose is the argument for deferring. List each such assumption explicitly as an assumption;
  post-deploy verifies the assumption before it verifies the criterion, because a wrong assumption
  makes the verification steps unrunnable rather than red

Example in JSON report:
```json
"deferredToPostDeploy": [
  {
    "criterion": "US-5: Titles generated with correct declensions",
    "reason": "Requires live LLM call with real data",
    "verificationCondition": "New survey entry processed after deploy",
    "verificationSteps": "Run a survey entry through the bot, check generated title for grammar and naturalness"
  }
]
```

Also mention deferred criteria in the decisions.md entry:
```
**Deferred to post-deploy:** 3 criteria require live verification (US-5, US-8, US-10). See deferredToPostDeploy in qa-report.json.
```
