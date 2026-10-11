#!/usr/bin/env python3
"""check-refs.py — ссылки на скиллы, агентов, линзы и команды резолвятся в файлы репозитория.

Что проверяет:
  - `.claude/agents/*.md`            → frontmatter `skills:` → `.claude/skills/<name>/SKILL.md`
  - `work/*/tasks/*.md` (не `done`)  → `skills:` → скилл; `reviewers:` → набор линз
                                        (`quick` / `thorough` / `none`), файл линзы или агент (легаси)
  - `CLAUDE.md`                      → каждая `/команда` → `.claude/commands/<name>.md`
                                        или `.claude/skills/<name>/`

Ссылка, которая резолвится только в `~/.claude/` (личная копия), — WARN: на другой машине
её нет. Ссылка, которой нет нигде, — ERROR.

Запуск:  python3 .claude/scripts/check-refs.py [--root <репо>] [--include-done]
Коды:    0 — всё резолвится; 1 — есть ERROR или не разобрался frontmatter; 2 — нечего проверять.

Почему отдельный скрипт: `task-validator` смотрит карточки глазами при декомпозиции, а скилл
или агент могут быть переименованы позже; CLAUDE.md перечисляет команды, часть которых жила
только в `~/.claude/`. Идея — `scripts/check-runbooks.sh` из `msitarzewski/agency-agents`
@ `f99f6aa` (MIT): «каждый слаг ростера резолвится в файл». Код свой.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

import yaml

BUILTIN_COMMANDS = {"clear", "compact", "context", "help", "mcp", "config", "model", "fast"}
REVIEWER_SETS = {"quick", "thorough", "none"}


def read_frontmatter(path: Path) -> dict | None:
    """Вернуть frontmatter как dict; None — если его нет или YAML не разобрался."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end < 0:
        return None
    try:
        data = yaml.safe_load(text[3:end])
    except yaml.YAMLError:
        return None
    return data if isinstance(data, dict) else None


def as_list(value) -> list[str]:
    """`[a, b]` → [a, b]; голый скаляр `none` → ['none']; пусто → []."""
    if value is None:
        return []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return []


class Resolver:
    def __init__(self, root: Path, personal: Path | None):
        self.root = root
        self.personal = personal

    def _personal(self, rel: str) -> str | None:
        """'personal', если файл есть только в ~/.claude; иначе None."""
        return "personal" if self.personal and (self.personal / rel).exists() else None

    def skill(self, name: str) -> str | None:
        if (self.root / ".claude/skills" / name / "SKILL.md").exists():
            return "project"
        return self._personal(f"skills/{name}/SKILL.md")

    def agent(self, name: str) -> str | None:
        if (self.root / ".claude/agents" / f"{name}.md").exists():
            return "project"
        return self._personal(f"agents/{name}.md")

    def command(self, name: str) -> str | None:
        if (self.root / ".claude/commands" / f"{name}.md").exists() or \
           (self.root / ".claude/skills" / name / "SKILL.md").exists():
            return "project"
        return self._personal(f"commands/{name}.md") or self._personal(f"skills/{name}/SKILL.md")

    def reviewer(self, name: str) -> str | None:
        if name in REVIEWER_SETS:
            return "project"
        if (self.root / ".claude/shared/review-lenses" / f"{name}.md").exists():
            return "project"
        return self.agent(name)


def check(root: Path, personal: Path | None, include_done: bool = False) -> tuple[list[str], list[str], int]:
    """Вернуть (errors, warnings, scanned). Каждая строка — готовое сообщение."""
    r = Resolver(root, personal)
    errors: list[str] = []
    warnings: list[str] = []
    scanned = 0

    def resolve(kind: str, name: str, where: str, field: str) -> None:
        found = getattr(r, kind)(name)
        if found == "project":
            return
        rel = os.path.relpath(where, root)
        if found == "personal":
            warnings.append(f"WARN  {rel}: {field} → `{name}` есть только в ~/.claude — на других машинах не будет")
        else:
            errors.append(f"ERROR {rel}: {field} → `{name}` не найден")

    # 1. Агенты → скиллы
    for agent in sorted((root / ".claude/agents").glob("*.md")):
        scanned += 1
        fm = read_frontmatter(agent)
        if fm is None:
            errors.append(f"ERROR {agent.relative_to(root)}: frontmatter не разобрался")
            continue
        for name in as_list(fm.get("skills")):
            resolve("skill", name, str(agent), "skills")

    # 2. Карточки задач → скиллы, ревьюеры
    for card in sorted(root.glob("work/*/tasks/*.md")):
        fm = read_frontmatter(card)
        if fm is None:
            # карточка без frontmatter — легаси, не наш предмет; но пустой разбор при наличии
            # `status:` в тексте — это сломанный YAML, его надо показать
            if re.search(r"^status:", card.read_text(encoding="utf-8", errors="replace"), re.M):
                errors.append(f"ERROR {card.relative_to(root)}: frontmatter не разобрался")
                scanned += 1
            continue
        if fm.get("status") == "done" and not include_done:
            continue
        scanned += 1
        for name in as_list(fm.get("skills")):
            resolve("skill", name, str(card), "skills")
        for name in as_list(fm.get("reviewers")):
            resolve("reviewer", name, str(card), "reviewers")

    # 3. CLAUDE.md → команды
    claude_md = root / "CLAUDE.md"
    if claude_md.exists():
        scanned += 1
        text = claude_md.read_text(encoding="utf-8")
        names = sorted(set(re.findall(r"`/([a-z][a-z0-9-]*)", text)))
        for name in names:
            if name in BUILTIN_COMMANDS:
                continue
            resolve("command", name, str(claude_md), "/" + name)

    return errors, warnings, scanned


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=None, help="корень репозитория (по умолчанию — от расположения скрипта)")
    ap.add_argument("--include-done", action="store_true", help="проверять и карточки со status: done")
    ap.add_argument("--no-personal", action="store_true", help="не смотреть в ~/.claude (как на чужой машине)")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parents[2]
    personal = None if args.no_personal else Path.home() / ".claude"
    errors, warnings, scanned = check(root, personal, args.include_done)

    for line in warnings:
        print(line)
    for line in errors:
        print(line)
    if scanned == 0:
        print("NOT CHECKED: не найдено ни агентов, ни карточек, ни CLAUDE.md — проверь --root")
        return 2
    print(f"check-refs: проверено {scanned} файлов, ошибок {len(errors)}, предупреждений {len(warnings)}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
