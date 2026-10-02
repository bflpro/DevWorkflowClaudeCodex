# DevWorkflowClaudeCodex

**English** · [Русский](README.ru.md)

A development workflow for Claude Code and Codex that you install into any repository: from an
idea through specifications and tasks to code, review and acceptance. Every step is closed by a
check that a script runs, not by the model's word: a task is done only with a receipt, an
executor cannot touch files outside its ownership, and reviewers never see the executor's own
story of how well it went.

> The skills, commands and templates are written mostly in Russian; the methodology files of
> the original skills are in English. Models read both without trouble.

## Flow

```
/build <task> ── code reconnaissance ── threshold (ENGINEERING.md §1a)
   │                                         │
   │ ≤100 lines, ≤5 files,                   │ otherwise
   │ no external writes, level ≤ L1          ▼
   ▼                         /new-user-spec   interview → work/<feature>/user-spec.md
 oneshot: task card,         /new-tech-spec   architecture, decisions, criteria with verify commands
 code, one review lens,      /decompose-tech-spec  task cards: owns_paths, reads, TDD Anchor
 receipt                     /do-feature      agent waves:
                                                wave-check.py   tasks in a wave do not overlap
                                                code + tests (TDD)
                                                review lenses, findings triage
                                                task-accept.py  re-runs verify, owns-check,
                                                                open findings → receipt
                             /done            spec criteria re-run as receipts,
                                              footprint checked against git diff, docs updated
```

Alongside the flow:

- **reflexes** — a `PreToolUse` hook injects a lesson right before a risky command (staging
  runtime data, a mass operation, a cron job without a lock);
- **`/prod-review`** — a production-readiness checklist (blocks A–J: timeouts, idempotency,
  webhooks, locks, data growth, LLM features);
- **documentation skills** — `technical-writing` and its siblings (design docs, runbooks, ADRs,
  postmortems), `/prose-review`, `/ground-docs`.

## Install

Requires `git`, `python3` ≥ 3.11 with PyYAML (`python3 -m pip install pyyaml`, used by the task gates) and `node` (for reflex hooks).

```bash
git clone https://github.com/bflpro/DevWorkflowClaudeCodex.git
cd DevWorkflowClaudeCodex
./install.sh --target /path/to/project            # Claude Code
./install.sh --target /path/to/project --codex    # + Codex
```

`--dry-run` prints what would happen without changing anything; `--force` replaces files you
have modified (originals go to `.workflow-backup/<timestamp>/`).

Then open the project in Claude Code and run `/build <task>` or `/new-user-spec`. In Codex:
start a new session, trust the project, check `/hooks`, and invoke `$source-command-build`.

## What gets installed

| Path | What it is |
|---|---|
| `.claude/skills/` | methodologies: planning, specs, decomposition, feature execution, coding, review, testing, QA, prod-review, documentation |
| `.claude/agents/` | subagents: spec and task validators, code/test/security reviewers, QA |
| `.claude/commands/` | slash commands (table in `templates/CLAUDE.md`) |
| `.claude/shared/` | feature artifact templates, interview templates, review lenses, feature-folder script |
| `.claude/scripts/` | gates: `task-accept.py`, `owns-check.py`, `wave-check.py`, `findings-sync.py`, `check-readme.py`, `check-techspec-readiness.py`, the reflex engine |
| `.claude/reflexes/` | reflexes — short lessons with a trigger condition |
| `.claude/settings.json` | two hooks (reflexes, context restore after compaction); merged into an existing file |
| `CLAUDE.md`, `AGENTS.md`, `ENGINEERING.md` | project rules — only when absent |
| `.codex/`, `.agents/skills/` | with `--codex`: the adapter and generated entrypoints |
| `.gitignore` | `work/*/logs/working/`, `.codex/data/`, `.workflow-backup/` |

`ENGINEERING.md` has "fill in" sections (stack, deploy). Fill them for your project; skills
refer to the other sections by number, so keep the numbering.

## Why it is built this way

- **Installed per project, not into `~/.claude`.** Skills and gates call `.claude/scripts/…` and
  `.claude/shared/…` from the project root, and the methodology travels with the repository: a
  teammate gets the same process after `git clone`.
- **One methodology for two tools.** Codex does not get a copy of the skills:
  `.codex/sync-workflow.py` writes short entrypoints that read the original from `.claude/`.
  Copies drift; references do not. Manifest hashes catch hand edits and staleness.
- **Done means a receipt.** An executor's report and a green exit code are not evidence;
  `task-accept.py` re-runs the checks itself and writes `acceptance.json`.
- **Re-installing is safe.** "Overwrite everything" was rejected: it would erase your edits.

## Invariants

- `install.sh` never replaces a file you modified without `--force`, and backs it up first when
  forced; it never touches an existing `CLAUDE.md`, `AGENTS.md` or `ENGINEERING.md`.
- Re-running with no upstream changes reports `added 0` and changes nothing.
- The Codex generator never deletes files and refuses to overwrite hand-edited entrypoints.
- Nothing goes over the network: installer, gates and hooks work on local files only.

## Updating

```bash
cd DevWorkflowClaudeCodex && git pull
./install.sh --target /path/to/project [--codex]
```

Files you did not change are updated; changed ones stay yours and are listed so you can merge
(or use `--force`). With `--codex`, entrypoints are regenerated.

## Checking and troubleshooting

```bash
bash .claude/scripts/check-setup.sh            # hooks, interpreters, scripts in place
python3 .codex/sync-workflow.py --check        # Codex entrypoints match .claude/
```

- `/new-user-spec` says `template not found` — `.claude/shared/` is incomplete; reinstall.
- Reflexes never fire — `node` is missing or the hooks are not in `.claude/settings.json`.
- `workflow-sync: drift=N` — `.claude/` changed but entrypoints were not regenerated:
  `python3 .codex/sync-workflow.py --write`. `Edited target` — an entrypoint was edited by hand.
- A task has `status: done` but no `logs/receipts/task-N/acceptance.json` — the gate was bypassed.

## Developing the workflow itself

```bash
bash tools/check-clean.sh                                              # leak guard
python3 -m unittest discover -s .claude/scripts/tests -t .claude/scripts/tests
python3 -m unittest discover -s .codex -p 'test_*.py'
python3 .codex/sync-workflow.py --check
```

CI (`.github/workflows/check.yml`) runs the same plus an install smoke test into an empty
repository. When you change a skill, command or agent, regenerate the Codex entrypoints
(`--write`) in the same commit.

## Third-party material

`technical-writing` and its sibling skills come from
[riekelt/technical-writer](https://github.com/riekelt/technical-writer) (MIT; license text in
`.claude/skills/technical-writing/LICENSE`). The size-based routing rule is adapted from
`bmad-build` in [BMAD-METHOD](https://github.com/bmad-code-org/BMAD-METHOD) (MIT).

## License

MIT — see [LICENSE](LICENSE).
