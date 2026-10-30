#!/usr/bin/env python3
"""Append the workflow policy link and merge missing Codex defaults without replacing user settings."""

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
`.claude/scripts/workflow-route.py`. Routine roles use Sonnet / Terra medium; critical
roles use Opus / Sol high; extraction alone uses Haiku / Luna low. Inline phases retain
the actual parent model and are self-review. User authorization still governs delegation.
The lead gathers applicable observations once per phase and gives each role a bounded,
current brief; children do not repeat full session-start scans. Preserve safety checks.
Acceptance collects lightweight local metrics; absent measurements remain unknown.
<!-- /workflow-resource-policy -->
"""


def configure(target, codex=False, dry=False):
    target = target.resolve()
    changes = []
    document = target / "CLAUDE.md"
    if document.is_symlink():
        raise ValueError("CLAUDE.md is a symlink; merge the resource policy manually")
    current = document.read_text() if document.exists() else ""
    if ".claude/shared/workflow-resources/README.md" not in current:
        changes.append((document, current.rstrip() + "\n" + BLOCK))
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
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    try:
        configure(args.target, args.codex, args.dry_run)
    except (OSError, ValueError) as error:
        ap.error(str(error))


if __name__ == "__main__":
    main()
