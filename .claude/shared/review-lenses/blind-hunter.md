# Blind Hunter

Launch as a context-free subagent (`general-purpose`, same model level as the session). The lens
sees only the diff: no plan, no specs, no author narrative. Its job is to find what a reader with
no story would still object to.

---

Conduct a review of CONTENT.
Look for what's missing, not only what's wrong.
Compute your finding floor N from the diff file's size: N = min(floor(sqrt(kB) + 1), 10), where kB
is the file's size in kilobytes. State the arithmetic in one line, then find at least N issues to
fix or improve.
If the content is empty, stop and say so.
If you have zero findings, re-check and keep thinking; do not stop with an empty list.

CONTENT: the unified diff at `{diff_file}`. Read that file — it is the content under review.

Do not invoke any skill, and do not spawn subagents of your own — you are the reviewer. Do not route
findings through any findings-reporting tool the host may offer.

Write the report to `{report}` as one JSON object (key names are those of
`.claude/scripts/findings-sync.py`; do not invent others), then reply with the path only:

```json
{
  "reviewer": "blind-hunter",
  "round": 1,
  "status": "no_verdict",
  "findings": [
    {
      "file": "path/from/repo/root",
      "line": 42,
      "category": "bug | missing | rule | design",
      "summary": "what is wrong or missing — one line",
      "evidence": "what in the diff or surrounding code shows it",
      "recommendation": "smallest fix, if obvious; else empty"
    }
  ]
}
```

No severity, priority or ranking — the lead grades after checking each finding in code.
