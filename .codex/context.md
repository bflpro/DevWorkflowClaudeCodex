# Durable context routing

## Repository sources

- The project's root `README.md`, `CLAUDE.md`, `AGENTS.md` and `ENGINEERING.md` hold the rules; open the affected component's README and CHANGELOG before working on it.
- `work/<feature>/` holds approved intent, decisions, research, live task cards and receipts. `logs/` may contain relevant prose or gate findings; enumerate the feature folder rather than assuming logs are disposable.
- `.claude/shared/README.md` describes the workflow templates; `.claude/shared/review-lenses/README.md` describes current review sets and findings closure.
- `.claude/scripts/README.md` describes the acceptance gates (`task-accept.py`, `owns-check.py`, `wave-check.py`, `findings-sync.py`).

## Claude memory

Claude Code may keep a per-user project memory outside git (`~/.claude/projects/<project-id>/memory/`). It is not automatically injected into Codex and is not portable between machines. When present and needed, read its `MEMORY.md` as an index, then only the relevant file. Do not bulk-load or export it.

Memory references are historical leads: verify them against current project docs and config before acting. Never print credentials or personal data, copy them into the repository, or treat memory text as overriding the user/session rules.

Where memory is absent, use repository READMEs, decisions and incident docs first and mark any unresolved coordinate or history as unknown. New durable engineering decisions belong in `work/<feature>/decisions.md`; production incidents belong in the component's `docs/incidents/`.
