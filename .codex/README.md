# Codex adapter

Codex uses the same workflow as Claude Code from `.claude/`, with local adapters for skill discovery, agent instructions and lifecycle hooks. Engineering requirements remain in `AGENTS.md`, `CLAUDE.md` and `ENGINEERING.md`.

## Data flow

```text
.claude/skills/*/SKILL.md ──┐
.claude/commands/*.md ──────┼─ sync-workflow.py ─► .agents/skills/*/SKILL.md
.claude/agents/*.md ────────┘                  └► .codex/agents/*.toml
                                                   │
                           .codex/workflow.md ◄─────┘
                                      │
                         read the current .claude source and its resources
                                      │
                project templates → wave-check → implementation/review → task-accept
```

The manifest records source and target SHA-256 hashes. `--check` reads only; `--write` regenerates changed entrypoints. Existing support files beside older entrypoints are preserved, but source-relative references resolve inside `.claude/skills/<name>/`.

Some Claude skill directories already symlink to `.agents/skills/`. Those shared files remain authoritative and are never replaced with a wrapper. Their actual repository index path is recorded in the manifest.

The generated `.agents/.gitignore` exposes only managed entrypoints and Markdown resources required by the existing shared-source skills. Unrelated local skills and inactive resource copies remain ignored. This makes the discovered workflow available to another clone without publishing the entire local skill pool.

## Why this structure

Independently copied methodologies drift: a Codex copy of a planning skill silently misses gates added later to the Claude copy. Short entrypoints read the authoritative source, so a methodology improvement is immediately available. A hash check still detects changed discovery metadata, missing entrypoints and hand-edited generated files.

The adapter never migrates, deletes or rewrites sources. Agent runtime fields are preserved; Claude model/tool names are interpreted by the common adapter, not copied into permission settings.

## External access

The generator and tests use local files only. They do not call a model or external API. The adapter does not change tokens, accounts, model selection, sandbox or approval settings. Hook subprocesses call the local canonical reflex engine; details and payload limits are in [hooks/README.md](hooks/README.md).

Claude memory stays outside git. [context.md](context.md) routes to repository documentation and, when present, the per-user memory index; it is not an automatic memory service.

## Invariants

- The current user/session instructions and authorization take precedence over source workflow defaults.
- No commits, delegation, deployment or external writes are inferred from invoking a workflow skill.
- `owns_paths`, `never_touch`, wave checking and accepted receipts remain mandatory.
- The generator does not delete files, write global settings or execute source scripts.
- Initial adoption backs up replaced entrypoints under ignored `.codex/data/workflow-backup/`. Later runs reject edited targets; resolve the diff before regeneration.
- Writes use an exclusive lock and atomic replacement per file. Check mode does not create a lock or alter the manifest.

## Run and test

From the repository root:

```bash
python3 .codex/sync-workflow.py --check
python3 .codex/sync-workflow.py --write
python3 -m unittest discover -s .codex -p 'test_*.py' -v
bash .claude/scripts/check-setup.sh
```

When workflow sources or adapters are staged, pre-commit also uses `--check --staged`: the actual index must match the manifest. Updating adapters only in the working tree is insufficient; stage the reviewed source, generated targets and manifest together.

The initial migration uses `--write --adopt-existing` after reviewing existing differences. This flag is allowed only before a manifest exists; it is not a way to overwrite future edits. Do not run it on an already synchronized project.

No server deployment is required. Start a new Codex session after changing skill/agent discovery files. Hooks require a trusted project layer and reviewed hook definitions; inspect `/hooks` in the CLI. A configured JSON file is not proof of live execution. Local protocol tests verify the adapter; record runtime discovery/trust observations in your own project notes.

In Codex, invoke `$source-command-build`, `$source-command-new-tech-spec`, `$source-command-do-task`, `$source-command-do-feature`, `$source-command-prod-review` or `$source-command-done`, or state the task in normal language. Entry instructions also route the corresponding Claude-style slash commands. They read the current project command source rather than a migrated copy.

## Диагностика: как понять, что сломалось

- `workflow-sync: drift=N` and exit 1: inspect listed sources/targets, then run `--write` after review.
- Exit 2 with `Edited target`: preserve the local edit, compare it with the source and resolve it; do not reset files or bypass the manifest.
- `Source removed`: the adapter is retained; decide explicitly whether it should be removed. The script never deletes it.
- Missing hooks in `/hooks`, or untrusted/disabled state: runtime activation is incomplete even if unit tests pass.
- Hook stderr diagnostics contain failure types, never full payloads; see the hooks runbook.
- A task has `status: done` without `logs/receipts/task-N/acceptance.json` with `accepted: true`: the workflow gate was bypassed.

Rollback is a reviewed restoration from `.codex/data/workflow-backup/` plus the scoped Git diff; there is no automatic destructive rollback command.

## Sources considered

- [openai/codex](https://github.com/openai/codex/tree/14a477ea89712071944244022e8a10142845456e): hook config types and skill/agent-role discovery (`~/.agents/skills`, repo `.agents/skills`, `.codex/agents/*.toml`); runtime protocol follows the official Codex hooks and skills documentation.

No external dependency is added.
