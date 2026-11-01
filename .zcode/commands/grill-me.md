---
name: grill-me
description: Interview the user relentlessly about a plan or design until reaching shared understanding, resolving each branch of the decision tree. Use when user wants to stress-test a plan, get grilled on their design, or mentions "grill me".
---

Interview me relentlessly about every aspect of this plan until we reach a shared understanding. Walk down each branch of the design tree, resolving dependencies between decisions one-by-one. For each question, provide your recommended answer.

Ask the questions one at a time.

If a question can be answered by exploring the codebase, explore the codebase instead.

When the interview concludes, follow the Grill-log section of the `grilling` skill: write `work/{feature}/grill-log.md` with one entry per resolved branch (challenge → resolution → `Verify:` command for every checkable promise, `**OPEN**` for unresolved ones), and offer to add checkable promises to tech-spec Acceptance Criteria as receipts so `/done` settles them.
