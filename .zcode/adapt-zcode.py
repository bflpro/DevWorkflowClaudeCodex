#!/usr/bin/env python3
"""Generate the .zcode/ runtime from .claude/ sources — full adapted copies, no wrappers.

Usage: adapt-zcode.py [--check] [--quiet]

.zcode/skills|commands|agents are full copies of the .claude/ methodology adapted to the
ZCode runtime by the rule tables below (see .zcode/README.md for the sync rule). Gates,
templates, reflexes and the resource policy stay in .claude/ and are never copied.

--check verifies the working tree matches regeneration and exits 1 on drift.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POLICY = ROOT / ".claude/shared/workflow-resources/policy.json"

# Model tier per role comes from policy.json; the source `model:` line is the fallback
# for roles missing from the policy.
SOURCE_MODEL_TIER = {"opus": "critical", "sonnet": "routine", "haiku": "extraction"}

# --- body transformations applied to every generated .md (order matters) --------
GLOBAL_RULES: list[tuple[str, str]] = [
    (r"\bteam lead\b", "lead"),
    (r"\bTeam lead\b", "Lead"),
    (r"\bTeammates\b", "Subagents"),
    (r"\bTeammate\b", "Subagent"),
    (r"\bteammates\b", "subagents"),
    (r"\bteammate\b", "subagent"),
    (r"\bTask tool\b", "Agent tool"),
    (r"Sonnet / Codex Terra medium", "GLM-5.3/high in ZCode"),
    (r"Sonnet / Terra medium", "GLM-5.3/high in ZCode"),
    (r"Opus / Sol high", "GLM-5.3/max in ZCode"),
    (r"Luna/low or Haiku", "GLM-5.3-Flash/low"),
]

# --- per-file transformations (keys are .claude-relative paths) -----------------
FILE_RULES: dict[str, list[tuple[str, str]]] = {
    "skills/feature-execution/SKILL.md": [
        (
            "     Check if `~/.claude/teams/{team_name}/config.json` exists: if yes, team is alive; if no,\n     recreate via TeamCreate. Skip to Phase 2 starting from `next_wave`.",
            "     Executors spawned before the compaction may be gone: check the session's task list\n     (`/tasks`) for still-running agents; a missing executor is re-spawned fresh with the\n     same card (its `start_commit` keeps ownership verifiable). Skip to Phase 2 starting\n     from `next_wave`.",
        ),
        ("6. Create team via TeamCreate",
         "6. Note the dispatch convention: one background subagent per task (Agent tool,\n   `run_in_background: true`); keep every spawn result's agent id for SendMessage"),
        ("**Checkpoint:** execution plan approved, team created, checkpoint initialized.",
         "**Checkpoint:** execution plan approved, dispatch convention set, checkpoint initialized."),
        (
            '   **Teammate** — `subagent_type: "general-purpose"`, `model: <resolved Claude model>`, `team_name: "{team}"`; resolve implementation/skill and risk through the resource policy. Codex uses its adapter and resolved model/effort.',
            "   **Subagent** — Agent tool, `subagent_type: \"general-purpose\"`, `run_in_background: true`,\n   model/thoughtLevel from the card's `executor` resolved via\n   `workflow-route.py --runtime zcode` (glm-max → GLM-5.3/max, glm-high → GLM-5.3/high,\n   glm-flash → GLM-5.3-Flash/low); resolve skill and risk through the resource policy.",
        ),
        (
            "   If the task requires user actions — send the instruction to lead via SendMessage.\n   Lead will forward to user and return confirmation.",
            "   If the task requires user actions — include the instruction request in your completion\n   report; the lead forwards it to the user and returns the confirmation by SendMessage to\n   your agent id.",
        ),
        ("- Message lead: \"Task {N} complete. decisions/task-{N}.md written.\"",
         "- Completion report: \"Task {N} complete. decisions/task-{N}.md written.\""),
        (
            "   3. Launch every lens of the set **in one turn** as context-free subagents (`general-purpose`,\n      `model: <resolved lens model>`; `security` → `subagent_type: \"security-auditor\"`; Codex uses the resolved profile/model/effort), `run_in_background: false`,",
            "   3. Launch every lens of the set **in one turn** as context-free subagents (Agent tool,\n      `subagent_type: \"general-purpose\"` with the lens tier resolved via\n      `workflow-route.py --runtime zcode`; `security` → `subagent_type: \"security-auditor\"`),\n      `run_in_background: false`,",
        ),
        ("(by its name — a fresh spawn is not\n      re-engagement)",
         "(by its agent id from the spawn result —\n      a fresh spawn is not re-engagement)"),
        ("4. All ok → finalize, shutdown team, delete `work/{feature}/logs/checkpoint.yml`",
         "4. All ok → finalize, stop any remaining background subagents (TaskStop), delete `work/{feature}/logs/checkpoint.yml`"),
    ],
    "skills/methodology/SKILL.md": [
        ("All tasks via agent teams. Lead orchestrates waves of parallel work.",
         "All tasks via parallel subagents. The lead orchestrates waves of parallel work."),
        ("- Creates team via TeamCreate",
         "- Dispatches one background subagent per task (Agent tool)"),
    ],
    "skills/skill-tester/SKILL.md": [
        ('3. TeamCreate(team_name="skill-test-{skill-name}")',
         '3. Label the run "skill-test-{skill-name}" (runners are background subagents spawned below)'),
    ],
    "skills/task-decomposition/SKILL.md": [
        ("For each task determine `executor` (opus | sonnet | codex | antigravity) based on:",
         "For each task determine `executor` (glm-max | glm-high | glm-flash) based on:"),
        ("(prompt-master → opus, code-writing S → codex, etc.)",
         "(prompt-master → glm-max, code-writing S → glm-high, etc.)"),
        ("(L + design-heavy → opus)", "(L + design-heavy → glm-max)"),
        ("→ sonnet", "→ glm-high"),
        ("→ opus", "→ glm-max"),
        ("(sonnet)", "(glm-high)"),
        ("(opus)", "(glm-max)"),
    ],
    "skills/user-spec-planning/SKILL.md": [
        ("subagent (opus)", "subagent (glm-max: GLM-5.3/max)"),
        ("(Task tool, sonnet)", "(Agent tool, glm-high)"),
        ("(sonnet)", "(glm-high)"),
        ("(opus)", "(glm-max)"),
    ],
    "skills/project-planning/SKILL.md": [
        ("(Task tool, sonnet)", "(Agent tool, glm-high)"),
    ],
    "skills/code-writing/SKILL.md": [
        ("routine lenses use GLM-5.3/high in ZCode, security/prod-readiness use GLM-5.3/max in ZCode (`general-purpose`;",
         "routine lenses use GLM-5.3/high, security/prod-readiness use GLM-5.3/max, resolved via\n      `workflow-route.py --runtime zcode` (`general-purpose`;"),
    ],
    "skills/prod-review/porting-to-other-repos.md": [
        (".claude/settings.json", ".zcode/config.json"),
    ],
    "skills/skill-tester/references/test-design-guide.md": [
        ("vibe-coding через Claude Code", "vibe-coding через Claude Code или ZCode"),
        ('"model": "opus"', '"model": "glm-max"'),
    ],
    "skills/skill-tester/references/grading-guide.md": [
        ("a test run of a Claude Code skill", "a test run of a ZCode skill"),
    ],
    "skills/skill-master/references/agents.md": [
        ("Subagents cannot call other subagents — Claude Code supports only one level of orchestration.",
         "Subagents cannot call other subagents — ZCode supports only one level of orchestration."),
        ("Agent files use YAML frontmatter + Markdown body. Store in `~/.claude/agents/{name}.md`.",
         "Agent files use YAML frontmatter + Markdown body. Store in `.zcode/agents/{name}.md`\n(project scope; ZCode discovers them natively)."),
        ("| `model` | `inherit` | Always use `inherit` to match orchestrator's model |",
         "| `model` | policy tier | Bare model id (`GLM-5.3`, `GLM-5.3-Flash`) from the resource policy |\n| `thoughtLevel` | tier | `low` / `high` / `max` — reasoning effort of the subagent's model |"),
        ("- [Create custom subagents - Claude Code Docs](https://code.claude.com/docs/en/sub-agents)",
         "- Project agents live in `.zcode/agents/*.md` (frontmatter: `name`, `description`, `model`,\n  `thoughtLevel`, `tools`, `color`); see `.zcode/README.md`."),
    ],
    "skills/infrastructure-setup/SKILL.md": [
        ("If sync reports a conflict, stop and report it. Include the generated Codex entrypoints and the\nmanifest in the same commit as the `.claude/**` source change (details: `.codex/README.md`).",
         "If sync reports a conflict, stop and report it. Include the generated Codex entrypoints and the\nmanifest in the same commit as the `.claude/**` source change (details: `.codex/README.md`).\n\nZCode-side `.zcode/skills|commands|agents/**` are full adapted copies — regenerate them with\n`python3 .zcode/adapt-zcode.py --write` in the same commit as the `.claude/**` source change\n(`--check` reports drift; details: `.zcode/README.md`)."),
    ],
    "skills/skill-master/references/frontmatter-options.md": [
        ("| `model` | `inherit` | Override model: `sonnet`, `opus`, `haiku`, `inherit` |",
         "| `model` | `inherit` | Override model: `GLM-5.3`, `GLM-5.3-Flash`, `inherit` |"),
        ("model: haiku", "model: GLM-5.3-Flash"),
        ("- `sonnet` — fast, good for most tasks\n- `opus` — best quality, use for complex reasoning\n- `haiku` — fastest, use for simple lookups",
         "- `GLM-5.3` — standard work (routine tier)\n- `GLM-5.3-Flash` — fastest, use for simple lookups"),
        ("only Claude can invoke", "only the model can invoke"),
    ],
    "commands/init-project.md": [
        ("(добавить --codex для Codex)", "(добавить --codex/--zcode для Codex/ZCode)"),
    ],
    "agents/task-creator.md": [
        ("[quick] when executor is codex — see skills-and-reviewers.md",
         "[quick] for S-size mechanical tasks — see skills-and-reviewers.md"),
    ],
    "agents/task-validator.md": [
        ("`[quick]` only with `executor: codex`",
         "`[quick]` only for S-size mechanical tasks (`executor: glm-high`)"),
    ],
}

ZCODE_EXECUTOR_CATALOG = """### Executors

| Executor | Resources | Best for |
|----------|-----------|----------|
| `glm-max` | GLM-5.3 / thoughtLevel max | Complex reasoning: prompt-master, architecture design, L-size tasks with non-obvious decisions |
| `glm-high` | GLM-5.3 / high (default) | Standard work: code-writing S/M/L, reviews, QA, documentation, infrastructure-setup, deploy-pipeline, mechanical and large-scale refactoring |
| `glm-flash` | GLM-5.3-Flash / low | Extraction/summarization only — never semantic approval, review, security or acceptance |

### Assignment rules

**Use `glm-max` when:**
- skill = `prompt-master`
- Task requires architectural decisions with multiple trade-offs (L-size + design-heavy)
- No clear single right answer — task needs deep reasoning

**Use `glm-high` (default) when:**
- Any code-writing size, review, QA, documentation, infrastructure or deploy task
- Mechanical changes (add field, rename, boilerplate) and large-scale refactoring/migrations
- Anything not covered by the glm-max rules

**Use `glm-flash` only for extraction** — fetching facts, counting, summarizing existing
material. It never approves, reviews or closes findings.

### Skill → Executor default

| Skill | Default executor |
|-------|-----------------|
| `prompt-master` | `glm-max` |
| `code-writing` (S/M/L) | `glm-high` |
| `code-reviewing` | `glm-high` |
| `security-auditor` | `glm-max` (critical tier) |
| `test-master` | `glm-high` |
| `infrastructure-setup` | `glm-high` |
| `deploy-pipeline` | `glm-high` |
| `documentation-writing` | `glm-high` |
| `skill-master` | `glm-high` |
| `pre-deploy-qa` | `glm-max` (critical tier) |
| `post-deploy-qa` | `glm-max` (critical tier) |
| large-scale refactoring / 10+ files | `glm-high` |

"""


def apply_rules(text: str, rel: str) -> tuple[str, list[str]]:
    """Apply FILE_RULES then GLOBAL_RULES; report patterns that did not match."""
    missed = []
    for pattern, repl in FILE_RULES.get(rel, []):
        if pattern not in text:
            missed.append(pattern)
        text = text.replace(pattern, repl)
    for pattern, repl in GLOBAL_RULES:
        text = re.sub(pattern, repl, text)
    return text, missed


def transform_skills_and_commands(src: str, rel: str) -> str:
    if rel.startswith("skills/tech-spec-planning/references/skills-and-reviewers.md"):
        src = re.sub(r"### Tools available.*?(?=## Examples)", ZCODE_EXECUTOR_CATALOG, src, flags=re.DOTALL)
    src, _ = apply_rules(src, rel)
    return src


def flatten_command_frontmatter(text: str) -> str:
    """ZCode parses command frontmatter flat: single-line values, inline lists."""
    m = re.match(r"\A---\r?\n(.*?)\r?\n---\r?\n?(.*)\Z", text, re.DOTALL)
    if not m:
        return text
    fm, body = m.groups()
    out = []
    lines = fm.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        dm = re.match(r"^description:\s*\|", line)
        am = re.match(r"^allowed-tools:\s*$", line)
        if dm or am:
            key = "description" if dm else "allowed-tools"
            i += 1
            cont = []
            while i < len(lines) and (lines[i].startswith((" ", "\t")) or lines[i] == ""):
                if lines[i].strip():
                    item = lines[i].strip()
                    cont.append(item.removeprefix("-").strip())
                i += 1
            if key == "description":
                out.append("description: " + " ".join(cont))
            else:
                out.append("allowed-tools: " + ", ".join(cont))
            continue
        out.append(line)
        i += 1
    return "---\n" + "\n".join(out) + "\n---\n" + body


AGENT_PREAMBLE = """<!-- ZCode runtime adapter: read .zcode/workflow.md first. Load every skill listed in
     `skills` below via the Skill tool (or read .zcode/skills/<name>/SKILL.md) before starting.
     Resources for this role: python3 .claude/scripts/workflow-route.py {name} --runtime zcode -->
"""


def parse_agent_frontmatter(text: str) -> tuple[dict, str] | None:
    m = re.match(r"\A---\r?\n(.*?)\r?\n---\r?\n?(.*)\Z", text, re.DOTALL)
    if not m:
        return None
    fm_text, body = m.groups()
    fields: dict[str, object] = {}
    lines = fm_text.split("\n")
    i = 0
    while i < len(lines):
        km = re.match(r"^([A-Za-z-]+):\s*(.*)$", lines[i])
        if not km:
            i += 1
            continue
        key, value = km.groups()
        if value.strip() in ("|", ">", "|-", ">-"):
            i += 1
            cont = []
            while i < len(lines) and (lines[i].startswith((" ", "\t")) or lines[i] == ""):
                cont.append(lines[i])
                i += 1
            fields[key] = "\n".join(c.strip() for c in cont).strip()
            continue
        elif value.strip() == "":
            i += 1
            items = []
            while i < len(lines) and re.match(r"^\s+-\s+", lines[i]):
                items.append(re.sub(r"^\s+-\s+", "", lines[i]).strip())
                i += 1
            if items:
                fields[key] = items
            else:
                fields[key] = ""
            continue
        else:
            fields[key] = value.strip()
        i += 1
    return fields, body


def transform_agent(src_text: str, rel: str, policy: dict) -> str:
    parsed = parse_agent_frontmatter(src_text)
    if parsed is None:
        raise ValueError(f"agent frontmatter unreadable: {rel}")
    fields, body = parsed
    name = str(fields.get("name") or Path(rel).stem)
    description = " ".join(str(fields.get("description", "")).split())
    source_model = str(fields.get("model", "sonnet")).lower()
    roles = {**policy.get("roles", {}), **policy.get("lenses", {})}
    tier = roles.get(name) or SOURCE_MODEL_TIER.get(source_model, policy["default_tier"])
    zsettings = policy["tiers"][tier]["zcode"]
    color = fields.get("color", "blue")
    skills = fields.get("skills", [])
    if isinstance(skills, str):
        skills = [s.strip() for s in skills.split(",") if s.strip()]
    tools = fields.get("allowed-tools", fields.get("tools", []))
    if isinstance(tools, str):
        tools = [t.strip() for t in tools.split(",") if t.strip()]
    desc_escaped = description.replace("\\", "\\\\").replace('"', '\\"')
    fm = (
        "---\n"
        f'name: {name}\n'
        f'description: "{desc_escaped}"\n'
        f'model: {zsettings["model"]}\n'
        f'thoughtLevel: {zsettings["thoughtLevel"]}\n'
        f"color: {color}\n"
        f"skills: [{', '.join(skills)}]\n"
        + (f"tools: [{', '.join(tools)}]\n" if tools else "")
        + "---\n"
    )
    body, missed = apply_rules(body.strip("\n"), rel)
    for pattern in missed:
        print(f"  warn: {rel}: file rule did not match: {pattern[:70]!r}", file=sys.stderr)
    return fm + "\n" + AGENT_PREAMBLE.format(name=name) + body.rstrip("\n") + "\n"


def generate(root: Path) -> dict[str, bytes]:
    policy = json.loads((root / ".claude/shared/workflow-resources/policy.json").read_text())
    out: dict[str, bytes] = {}

    for source in sorted((root / ".claude/skills").glob("*/**/*")):
        if not source.is_file() or "__pycache__" in source.parts:
            continue
        rel = source.relative_to(root / ".claude").as_posix()
        target = ".zcode/" + rel
        if source.suffix == ".md":
            text = transform_skills_and_commands(source.read_text(), rel)
            data = text.encode()
        else:
            data = source.read_bytes()
        out[target] = data

    for source in sorted((root / ".claude/commands").glob("*.md")):
        rel = source.relative_to(root / ".claude").as_posix()
        text = transform_skills_and_commands(source.read_text(), rel)
        out[".zcode/" + rel] = flatten_command_frontmatter(text).encode()

    for source in sorted((root / ".claude/agents").glob("*.md")):
        rel = source.relative_to(root / ".claude").as_posix()
        out[".zcode/" + rel] = transform_agent(source.read_text(), rel, policy).encode()

    for target in sorted(out):
        if "/__pycache__/" in target:
            del out[target]
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true", help="regenerate the .zcode tree (default)")
    mode.add_argument("--check", action="store_true", help="verify the tree matches; exit 1 on drift")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    generated = generate(ROOT)
    stale = []
    for kind in ("skills", "commands", "agents"):
        base = ROOT / ".zcode" / kind
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            if path.is_file() and "__pycache__" not in path.parts:
                rel = path.relative_to(ROOT).as_posix()
                if rel not in generated:
                    stale.append(rel)
    drift = []
    written = 0
    for target, data in sorted(generated.items()):
        path = ROOT / target
        current = path.read_bytes() if path.exists() else None
        if current != data:
            drift.append(target)
            if not args.check:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
                written += 1
    for target in stale:
        print(f"zcode-adapt: stale generated file left in place: {target}", file=sys.stderr)
    if args.check:
        if drift:
            print(f"zcode-adapt: drift={len(drift)}")
            for target in drift:
                print(f"  {target}")
            return 1
        print("zcode-adapt: in sync" + (f" ({len(generated)} files)" if not args.quiet else ""))
        return 0
    print(f"zcode-adapt: written={written}, unchanged={len(generated) - written}, stale={len(stale)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
