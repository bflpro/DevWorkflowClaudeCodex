#!/usr/bin/env python3
"""Append the workflow policy link and merge missing runtime defaults without replacing user settings."""

import argparse
import json
import re
from pathlib import Path

import tomllib

SOURCE = Path(__file__).resolve().parents[1]
BLOCK = """
<!-- workflow-resource-policy -->
## Shared workflow resources

Read `.claude/shared/workflow-resources/README.md` before workflow research, specifications,
implementation and review. Resolve the current runtime, role and risk with
`.claude/scripts/workflow-route.py`. Routine roles use Sonnet / Terra medium / GLM-5.3 high;
critical roles use Opus / Sol high / GLM-5.3 max; extraction alone uses Haiku / Luna low /
GLM-5.3-Flash low. Inline phases retain the actual parent model and are self-review. User
authorization still governs delegation. The lead gathers applicable observations once per
phase and gives each role a bounded, current brief; children do not repeat full session-start
scans. Preserve safety checks. Acceptance collects lightweight local metrics; absent
measurements remain unknown.
<!-- /workflow-resource-policy -->
"""

ZCODE_BLOCK = """
<!-- workflow-zcode -->
## Workflow в ZCode

Нативный рантайм ZCode: `.zcode/skills/`, `.zcode/commands/` (slash-команды `/build`, `/done`, …),
`.zcode/agents/` (GLM-модель и thoughtLevel из политики ресурсов). До работы прочти
`.zcode/workflow.md` — перевод инструментов и правила авторизации. Хуки (рефлексы, восстановление
контекста) подключены в `.zcode/config.json` (`hooks.enabled: true`). `.zcode/skills|commands|agents`
— полные адаптированные копии `.claude/`: после правки источников перегенерируй их
`python3 .zcode/adapt-zcode.py --write` тем же коммитом. Запуск скилла сам по себе не разрешает
субагентов, коммит, деплой или запись наружу — без явного разрешения этапы выполняются сам и
называются самопроверкой.
<!-- /workflow-zcode -->
"""


def merge_zcode_hooks(target: Path, dry: bool) -> int:
    """Merge the workflow hooks into an existing .zcode/config.json, preserving the rest."""
    config = target / ".zcode/config.json"
    source = json.loads((SOURCE / ".zcode/config.json").read_text())
    if not config.exists():
        return 0  # installed verbatim by install.sh
    if config.is_symlink() or not config.resolve().is_relative_to(target):
        raise ValueError("ZCode config must be a regular project-local file")
    data = json.loads(config.read_text())
    hooks = data.setdefault("hooks", {})
    hooks["enabled"] = True
    events = hooks.setdefault("events", {})
    added = 0
    for event, groups in source["hooks"]["events"].items():
        present = {
            h.get("command")
            for g in events.get(event, [])
            for h in g.get("hooks", [])
        }
        for group in groups:
            if all(h["command"] not in present for h in group["hooks"]):
                events.setdefault(event, []).append(group)
                added += 1
    if added:
        print(f"  {'[dry-run] ' if dry else ''}merge workflow hooks into .zcode/config.json ({added} group(s))")
        if not dry:
            config.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    return added


def configure(target, codex=False, zcode=False, dry=False):
    target = target.resolve()
    changes = []
    document = target / "CLAUDE.md"
    if document.is_symlink():
        raise ValueError("CLAUDE.md is a symlink; merge the resource policy manually")
    current = document.read_text() if document.exists() else ""
    if ".claude/shared/workflow-resources/README.md" not in current:
        changes.append((document, current.rstrip() + "\n" + BLOCK))
    if zcode:
        agents_doc = target / "AGENTS.md"
        if agents_doc.is_symlink():
            raise ValueError("AGENTS.md is a symlink; merge the ZCode workflow block manually")
        agents_current = agents_doc.read_text() if agents_doc.exists() else ""
        if "<!-- workflow-zcode -->" not in agents_current:
            changes.append((agents_doc, agents_current.rstrip() + "\n" + ZCODE_BLOCK))
        merge_zcode_hooks(target, dry)
    if codex:
        config = target / ".codex/config.toml"
        if config.is_symlink() or not config.resolve().is_relative_to(target):
            raise ValueError("Codex config must be a regular project-local file")
        text = config.read_text() if config.exists() else ""
        data = tomllib.loads(text)
        agents = data.get("agents", {})
        if not isinstance(agents, dict):
            raise ValueError("unsupported agents setting")
        policy = json.loads(
            (SOURCE / ".claude/shared/workflow-resources/policy.json").read_text()
        )
        settings = policy["tiers"][policy["default_tier"]]["codex"]
        defaults = {
            "default_subagent_model": settings["model"],
            "default_subagent_reasoning_effort": settings["model_reasoning_effort"],
        }
        missing = {k: v for k, v in defaults.items() if k not in agents}
        if missing:
            lines = (
                "\n".join(f"{k} = {json.dumps(v)}" for k, v in missing.items()) + "\n"
            )
            header = re.search(r"(?m)^[ \t]*\[agents\][ \t]*(?:#[^\n]*)?$", text)
            if header:
                text = text[: header.end()] + "\n" + lines + text[header.end() :]
            elif "agents" not in data:
                text = text.rstrip() + "\n\n[agents]\n" + lines
            else:
                raise ValueError(
                    "inline agents table: add missing defaults manually before installing"
                )
            tomllib.loads(text)
            changes.append((config, text))
    for path, text in changes:
        print(f"  {'[dry-run] ' if dry else ''}configure {path.relative_to(target)}")
        if not dry:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
    return len(changes)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("target", type=Path)
    ap.add_argument("--codex", action="store_true")
    ap.add_argument("--zcode", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    try:
        configure(args.target, args.codex, args.zcode, args.dry_run)
    except (OSError, ValueError) as error:
        ap.error(str(error))


if __name__ == "__main__":
    main()
