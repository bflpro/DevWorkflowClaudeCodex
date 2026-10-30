# Workflow resources: Claude and Codex

This policy governs resource selection, bounded context and local feedback for the shared development workflow. Criteria, task ownership and acceptance remain in their existing sources. Model assignments are a pilot based on the October audit, not a claim of measured quality equivalence.

## Why this design

Explicit role tiers prevent expensive parent-model inheritance. A dedicated escalation profile handles Codex custom-role precedence. Receipt-based collection reuses existing evidence and avoids a new model call or full transcript scan after every task. A native session-analysis CLI would add dependencies without solving task attribution.

## External access

The resolver and collector use local files only; they need no token, account, scope, network connection or server process. They touch the shared policy, task receipts/working evidence and ignored `.claude/state/workflow-metrics/`. Agent execution still uses the already selected client's provider and authorization; these scripts do not call that provider themselves.

## Invariants

Collection never changes an acceptance verdict, canonical finding or workflow setting. Unknown measurements remain null. The same task/run updates its existing snapshot; raw finding/customer text is excluded. Unmarked Codex runtime overrides survive sync, and an edited managed target blocks overwrite. Retention limits apply when collection runs; no background cleanup service is installed.

## Resolve before work

Run from the repository root before dispatch or the start of an inline phase:

```bash
python3 .claude/scripts/workflow-route.py task-creator --runtime codex
python3 .claude/scripts/workflow-route.py code-reviewer --runtime codex --risk money
python3 .claude/scripts/workflow-route.py implementation --runtime claude
```

`policy.json` is the shared assignment source. Routine research, specification drafts, cards and semantic validators use Terra/medium in Codex, Sonnet in Claude. Security, deployment/QA and adequacy roles use Sol/high or Opus. Architecture, money, data loss, concurrency and recovery strengthen otherwise routine work. Mechanical checks use existing scripts. Luna/low or Haiku is limited to extraction/summarization, never semantic approval, security review, finding closure or acceptance. Do not introduce an LLM classifier before every operation.

The resolver returns **requested** settings, never evidence of the model that ran. For an unknown role or risk it fails instead of silently downgrading. A failed or contradictory routine result gets one bounded investigation; unresolved invariants or demonstrated capability gaps use the critical profile, with the reason recorded. Repeated escalation is a signal for the periodic report, not an automatic full pipeline restart. Do not silently fall back to an unavailable model or effort: record the limitation and use a supported, explicit assignment; never describe unavailable checks as passed.

If a newly added custom profile is not exposed by the current tool, reload the session. A runtime that supports explicit model/effort on a generic agent may instead use that supported mechanism with the original source path and the same restrictions. Do not invent an unavailable agent type or dispatch another fixed role whose settings would ignore the requested override.

For Codex custom roles the generated TOML settings take precedence over spawn overrides. Use the returned `workflow-escalation` agent type, supply the original role/lens source path and exact output schema, rather than trying to override a fixed Terra role. Routine generic lenses use the returned requested settings. Security/prod-readiness use critical resources. Never change the `reviewer` identity or findings schema merely because the execution profile changes. Marked generated model fields track policy; unmarked local overrides are preserved by sync. To retain a reviewed local override, remove the managed marker, set the fields, then run sync check/write and inspect the diff.

Claude uses explicit `model` in role frontmatter and the resolver's model for generic agents. Existing `executor` metadata is not a provider switch: a Codex session resolves a Codex model, a Claude session resolves a Claude model. Preserve an explicitly approved stronger assignment; remove blanket Opus launches for routine work. Legacy executor hints never authorize invoking another provider or external service. Effort names from Codex are not copied to Claude.

**Authorization:** only delegate when the user has authorized it. Otherwise execute inline with the selected session model, record the requested/actual mismatch and call the check self-review. Custom-agent files do not switch the parent session model. Select a new parent model through the client's supported controls at a phase boundary; never claim to have changed it via text. Restart the client/session to reload discovery settings when required.

## Context and review

Give each role its question, card/spec/diff paths, relevant source ranges, invariants, output schema/path and verification target. Build one relevant observations/knowledge brief per phase and update it only when the task or sources change. Do not repeat whole-session history or full private-memory/observer scans per child. A current mandatory safety check still runs; this rule is not permission to bypass one. Initial discovery enumerates the feature folder; subsequent readers load the relevant artifacts.

Use a fresh bounded context when the runtime supports it (`fork_turns: none` in the current Codex tool when independently dispatched). If isolation cannot be ensured, record that limitation rather than claiming blind review. Reviewers receive original requirements and code evidence, not the executor narrative or a previous solution. Give a soft checkpoint after 20–30 reviewer tool/model steps or a materially expanded input scope: return evidence and remaining work, not a false approval. These are pilot checkpoints, not enforced runtime quotas.

Apply `.claude/shared/review-lenses/triage.md`: group by demonstrated root cause, retain every fingerprint, verify the patch and adjacent invariants, rerun required tests. Do not rerun every lens after each patch. Reopen accepted residual risk only when code, requirements or evidence changes. A new high/medium defect remains a blocker even when a cycle budget is exhausted. Record an unfinished check explicitly.

At the boundary between planning and implementation, or after a long implementation wave, persist the current commit, task/contract, owned paths, receipt and finding paths, unresolved questions and next action. Resume from this brief and files; do not load all other active features. Avoid starting a fresh session while authorized child work is still unaccounted for.

## Lightweight evidence and report

`task-accept.py` automatically collects receipt/finding aggregates after **each** attempt, including rejection. It does not call a model or scan session transcripts. Optional resource counters come from one file per actual execution, written by the lead/launcher from tool metadata when available:

`work/<feature>/logs/working/task-N/evidence-workflow-run-<unique-run-id>.json`

```json
{
  "role": "code-reviewer",
  "runtime": "codex",
  "mode": "delegated",
  "requested": {"model": "gpt-6.1-terra", "effort": "medium"},
  "actual": {"model": null, "effort": null},
  "usage": {"input_uncached": null, "cache_read": null, "cache_write": null, "output": null},
  "elapsed_seconds": null,
  "waiting_seconds": null,
  "escalated": false
}
```

Update the same file for the same execution; do not copy its cumulative usage into another run. Retries in a new agent/session get a new ID. Separate agents and task executions must not share cumulative counters. Requested fields come from resolver settings (its `model_reasoning_effort` maps to evidence `effort`); actual fields come from observed runtime metadata. Do not ask every child for an extra narrative report. Without observed task-scoped usage keep null; never substitute a session total, estimate cache from context length, or infer actual resources from configuration. This version exposes missing coverage; it does not promise automatic capture of all provider counters or all agent executions.

Future structured triage can add `triage.route` (`patch`, `false`, `defer`, `ask`, `duplicate`) to canonical finding metadata. Legacy evidence is classified conservatively by closure text; ambiguous text is unknown. This is a count of records, not unique bugs or a severity assessment. The collector does not mutate findings or receipts.

Runtime files: ignored `.claude/state/workflow-metrics/{state.json,lock,report.md}`. Keep at most 500 task contracts, 90 days, 100 run records per task and 1 MiB per input JSON. Stored data is an allowlist of counters/resources, hashed feature identity and contract; no finding text, prompts, commands, customer documents, full paths or exception contents. Retrying acceptance updates the snapshot, not summed usage. A lock and atomic replacement serialize concurrent writers; contention/failure warns and leaves acceptance unchanged.

The saved report refreshes after 10 newly accepted contracts or after seven days with new accepted data. This happens on the next acceptance invocation, not via a cron/model loop. Inspect any time:

```bash
python3 .claude/scripts/workflow-metrics.py report
python3 .claude/scripts/workflow-metrics.py collect work/<feature> N
```

The report flags high false-finding share, many escalations or unusually high numeric closure rounds with explicit sample limits. It never equates closure rounds with repeated audits, missing usage with zero, or an automatic signal with proof that a model should be downgraded. Use the report periodically with selected anonymized examples for a human-requested analysis. Proposed changes include evidence, expected effect, quality check and rollback; the collector never edits policy automatically.

## Run, tests and troubleshooting

```bash
python3 .claude/scripts/tests/test_workflow_metrics.py
python3 -m unittest discover -s .codex -p 'test_*.py'
python3 .codex/sync-workflow.py --check
```

Warnings from `workflow-metrics` mean collection was incomplete/unavailable, not acceptance failure. Corrupt state is retained for inspection; never silently reset it. Unknown actual models or token counters are expected until the launcher/client exposes them. A passing sync proves file consistency, not live model routing or comparable quality; record runtime observations separately on subsequent authorized tasks.

## Sources

Local receipt and sync tooling is reused. Inspected ccusage @ `71e022a8edf98b41b5715b77b17b3ea5a166498b` (MIT), its package build hooks and Codex parser/tests; no code copied, dependencies installed or external code run. A full session CLI is unnecessary for bounded task summaries. Configuration semantics checked against https://learn.chatgpt.com/docs/agent-configuration/subagents.
