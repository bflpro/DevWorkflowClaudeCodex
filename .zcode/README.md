# ZCode adapter (GLM)

A native ZCode runtime for the shared development workflow, structured after `.claude/`:
ZCode discovers `.zcode/skills/`, `.zcode/commands/` (real slash commands with the same names
as Claude Code) and `.zcode/agents/` (subagents with GLM `model` / `thoughtLevel`) natively
from the project root, so no generator, entrypoints or manifest are used here.

```
.claude/{skills,commands,agents}          methodology source (authoritative)
        scripts/, shared/, reflexes/      gates, templates, reflex engine — shared, not copied
.zcode/workflow.md                        runtime translation, authorization, lifecycle
.zcode/config.json                        hooks (PreToolUse reflexes, SessionStart recovery)
.zcode/hooks/workflow-hooks.py            payload normalizer → shared reflex engine
.zcode/skills|commands|agents/            full adapted copies of .claude/ (see sync rule)
```

## Install

```bash
./install.sh --target /path/to/project --zcode          # Claude + ZCode
./install.sh --target /path/to/project --codex --zcode  # all three runtimes
```

The installer copies the `.zcode/` tree and merges its `hooks` block into an existing
`.zcode/config.json` (your `mcp.servers` and other keys are preserved). `AGENTS.md` — the
instruction file ZCode loads natively — gets a workflow pointer appended when missing.
Then open the project in ZCode and run `/build <task>` or `/new-user-spec`.

## Model tiers

`.claude/shared/workflow-resources/policy.json` maps every role to a tier; the ZCode column:

| Tier | model | thoughtLevel | Roles |
|---|---|---|---|
| routine | `GLM-5.3` | `high` | research, specs, cards, validators, most reviewers |
| critical | `GLM-5.3` | `max` | security-auditor, deploy/QA, adequacy, escalation |
| extraction | `GLM-5.3-Flash` | `low` | workflow-extractor: extraction/summarization only |

Agent frontmatter carries bare model ids. If your account needs a qualified id and the bare one
does not resolve, remove the `model` key (the agent then inherits the session model) rather than
silently switching tiers. Resolve any role explicitly:

```bash
python3 .claude/scripts/workflow-route.py <role> --runtime zcode [--risk <category>]
```

## Sync rule (no drift checker — by design)

`.zcode/skills|commands|agents` are **full adapted copies**, not generated wrappers. When you
change `.claude/skills/`, `.claude/commands/` or `.claude/agents/`, mirror the change into
`.zcode/` **in the same commit**. Gates, templates, reflexes and the policy are shared with
`.claude/` and must never be copied here.

Adaptation checklist applied when copying (re-apply it when mirroring):

- `Task(...)` / `TeamCreate` / «teammate» / `run_in_background` → Agent tool with `subagent_type`.
- `opus` / `sonnet` / `haiku` assignments → policy tiers via
  `workflow-route.py --runtime zcode` (`GLM-5.3`/high, `GLM-5.3`/max, `GLM-5.3-Flash`/low).
- `.claude/settings.json` hook references → `.zcode/config.json`; PostCompact → SessionStart(compact).
- «Claude Code» as the runtime → ZCode; keep «Claude» when it names the source methodology.
- Paths to `.claude/scripts/`, `.claude/shared/`, `ENGINEERING.md` sections — unchanged.

## Diagnostics

- Commands missing in the `/` menu — check `.zcode/commands/*.md` names
  (`^[a-z0-9][a-z0-9_:-]{0,63}$`, no builtin-name collisions) and the discovery order (a
  same-named user-scope command wins).
- Reflexes never fire — `hooks.enabled: true` must stay in `.zcode/config.json`; see
  `.zcode/hooks/README.md`.
- Skills shadowed — a same-named skill in `~/.zcode/skills/` or a nearer root wins; rename it.
- Hooks run but inject nothing — the engine matched no `use-when` trigger, or the reflex already
  fired once this session (by design).

## Tests

```bash
python3 -m unittest discover -s .zcode -p 'test_*.py'
```
