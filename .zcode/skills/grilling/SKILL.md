---
name: grilling
description: Interview the user relentlessly about a plan or design. Use when the user wants to stress-test a plan before building, or uses any 'grill' trigger phrases.
---

Interview me relentlessly about every aspect of this plan until we reach a shared understanding. Walk down each branch of the design tree, resolving dependencies between decisions one-by-one. For each question, provide your recommended answer.

Ask the questions one at a time, waiting for feedback on each question before continuing. Asking multiple questions at once is bewildering.

If a question can be answered by exploring the codebase, explore the codebase instead.

## Grill-log: the interview leaves a trace

A grill that ends as a conversation is forgotten by the next session. When the interview concludes, write the outcome down:

1. Write `work/{feature}/grill-log.md` (if the plan belongs to a feature folder; otherwise ask where to put it, defaulting to next to the plan document). One entry per resolved branch:

   ```markdown
   ## G-1: {challenge, one line}
   - **Resolution:** {what was decided and why}
   - **Verify:** `{command}` → {expected} — how we'll know the resolution holds
   ```

   `Verify` is required whenever the resolution makes a checkable promise ("this won't slow down the endpoint", "the migration is reversible"). If a resolution is genuinely unverifiable by command, write `Verify: manual — {what to watch for}`.

2. If the feature has a `tech-spec.md` with Acceptance Criteria — offer to add the checkable promises as additional AC receipts there (`- [ ] G-1: ... / verify: ...`), so `/done` settles them automatically.

3. Unresolved branches (user deferred, or no agreement reached) get an entry marked `**OPEN**` — the next grill or `/done` surfaces them instead of silently dropping them.
