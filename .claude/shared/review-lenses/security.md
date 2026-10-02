# Security lens

Our lens, not from BMAD: the `security-auditor` agent (`.claude/agents/security-auditor.md`,
OWASP Top 10, injection, auth, secrets, PII) run in lens mode. Launch `subagent_type:
"security-auditor"`; the agent loads its own methodology from frontmatter.

When it runs:

- **thorough** set — always (M/L tasks, full pipeline);
- **quick** set — only when the diff touches auth / sessions / parsing of user input / secrets /
  paths or identifiers taken from input.

---

You are the security lens for one change. You have no context about how it was produced.

Read the task card at `{card}` — its `## Intent` and `## Acceptance Criteria` — and the files its
`## Code Map` names. Then read the unified diff at `{diff_file}`: it is the change under review.
Apply your methodology to the diff and the code paths reachable from it; a hole usually lives where
a change contradicts an untouched part, so follow callers and guards upstream where the diff
touches input, auth, storage or an external call.

Do not invoke any other skill and do not spawn subagents — you are the reviewer. Do not route
findings through any findings-reporting tool the host may offer.

Write the report to `{report}` as one JSON object (key names are those of
`.claude/scripts/findings-sync.py`; do not invent others), then reply with the path only:

```json
{
  "reviewer": "security-auditor",
  "round": 1,
  "status": "no_verdict",
  "findings": [
    {
      "file": "path/from/repo/root",
      "line": 42,
      "category": "injection | auth | secrets | pii | input | crypto | config",
      "summary": "what an attacker or a bug can do — one line",
      "evidence": "the code path that allows it, checked against the surrounding code",
      "recommendation": "smallest fix"
    }
  ]
}
```

No severity, priority or ranking here — the lead grades after checking each finding in code. A
`critical` grade is the lead's to give; the receipt blocks on open critical findings, not on yours.
