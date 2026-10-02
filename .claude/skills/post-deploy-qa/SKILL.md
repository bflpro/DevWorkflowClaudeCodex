---
name: post-deploy-qa
description: |
  Post-deploy verification: execute AVP from tech-spec on live environment,
  verify all acceptance criteria (user-spec + tech-spec), pick up deferred
  criteria from pre-deploy QA report. Uses MCP tools (Telegram MCP, Playwright, curl, bash).

  Use when: "пост-деплой проверка", "post-deploy verification", "проверь после деплоя",
  "MCP verification", "верификация на живом окружении", "проверь деплой",
  "запусти AVP", "agent verification plan"
---

# Post-deploy QA

## Input Requirements

Read before starting:
- `user-spec.md` — acceptance criteria
- `tech-spec.md` — Agent Verification Plan (AVP) section + technical acceptance criteria
- `decisions.md` — deviations from plan (if exists)
- Pre-deploy QA report (`logs/working/qa-report.json`) — check `deferredToPostDeploy` section for criteria that could not be verified pre-deploy
- Confirmation that deploy is complete and environment is live

If tech-spec has no AVP section — still proceed with acceptance criteria verification.

## Verification Methodology

Two verification directions (both required):

### 1. Agent Verification Plan (AVP)

Execute each step from AVP section in tech-spec:

1. Read AVP section — it lists verification steps with expected outcomes and MCP tools to use
2. For each step:
   - Use the specified MCP tool (Telegram MCP, Playwright, curl, bash, etc.)
   - Perform the described action on live environment
   - Compare result with expected outcome
   - Record: tool used, step performed, result
3. If MCP tool is unavailable — mark step as `not_verifiable`, continue with remaining steps
4. **If a step is made safe by a switch — a dry-run flag, a read-only mode, an alternate config or
   profile — find out what else that switch moves before trusting the result.** One env knob
   routinely does two jobs: it isolates the run *and* relocates the feature flags, state files,
   database path or credentials the run exists to verify. The step then passes against a copy and
   says nothing about production. Name, in the step's `details`, the concrete artifacts the run
   actually read (absolute paths, flag source, DB file) and confirm they are the production ones;
   if they are not, the step is `not_verifiable`, not `passed`

**Checkpoint:** All AVP steps executed or marked `not_verifiable`. Proceed to acceptance criteria.

### 2. Acceptance Criteria Verification

Verify all acceptance criteria from user-spec and tech-spec on live environment. This catches criteria that pre-deploy QA could not verify without a live system.

1. Read pre-deploy QA report (`logs/working/qa-report.json`) — check `deferredToPostDeploy` section
2. For each deferred criterion — follow the verification steps specified in the pre-deploy report
3. Also re-check all acceptance criteria from user-spec and tech-spec against live behavior
4. For each criterion:
   - **passed** — verified on live environment, evidence provided
   - **failed** — live behavior does not meet the criterion
   - **blocked** — cannot verify due to external conditions (no data, third-party service down). Provide a concrete manual verification plan for the user: what to check, when, how

A `blocked` criterion requires user follow-up before the feature can count as fully verified.

**Checkpoint:** All acceptance criteria verified, or marked `blocked` with manual verification plan.

## Severity Classification

- **critical** — verification step failed, live functionality broken, data integrity at risk
- **major** — works but with significant issues visible in production
- **minor** — cosmetic, non-functional discrepancies

## Output Format

Return findings as JSON. Reason: orchestrator parses this to decide pass/fail and log findings.

```json
{
  "status": "passed | failed",
  "summary": {
    "totalSteps": 0,
    "passed": 0,
    "failed": 0,
    "blocked": 0,
    "notVerifiable": 0,
    "criticals": 0,
    "majors": 0,
    "minors": 0
  },
  "agentVerification": [
    {
      "step": "Send /start to bot",
      "tool": "telegram_mcp",
      "status": "passed | failed | not_verifiable",
      "details": "Bot responded with welcome message"
    }
  ],
  "acceptanceCriteria": [
    {
      "id": "US-5",
      "criterion": "Titles generated with correct declensions",
      "source": "user-spec | tech-spec | deferred-from-pre-deploy",
      "status": "passed | failed | blocked",
      "evidence": "Checked live output, title 'В компании X работает...' uses correct declension",
      "manualVerificationPlan": "Only if blocked — what the user should check, when, how"
    }
  ],
  "findings": [
    {
      "severity": "critical | major | minor",
      "title": "Bot does not respond to /start",
      "expected": "Welcome message within 3 seconds",
      "actual": "No response after 10 seconds",
      "reproduction": "Steps to reproduce..."
    }
  ]
}
```

Status decision: `passed` if zero criticals, `failed` if one or more criticals.

## Guidelines

- Every finding includes concrete reproduction: steps, expected vs actual, tool output.
- If all MCP tools are unavailable — report that automated verification is not possible, suggest manual steps.
- Empty findings array = clean verification.

## Final Check

Before finishing, verify:
- [ ] All AVP steps executed or marked `not_verifiable`
- [ ] All deferred criteria from pre-deploy QA report addressed
- [ ] All acceptance criteria from user-spec and tech-spec verified on live environment
- [ ] Every `blocked` criterion has a manual verification plan (what to check, when, how)
- [ ] For every capability introduced by a migration or a config change — **a right, a role, a
      queue binding, a schedule** — it was not only created but *assigned and observed in use*.
      "Does the permission exist" is a different question from "does anyone hold it", and granting
      it is a deploy step that has an owner and a place in the runbook, not a side effect of the
      migration. An unassigned right shows up later as an object with no owner, never as an error
- [ ] Every criterion the pre-deploy report marked `automationObserved: false` is closed by the
      unrequested event named in its `closingObservation` — a scheduled tick nobody triggered, a
      delivery at the destination — and not by a manual run repeated on the live system
- [ ] Output JSON is valid, status reflects critical count
