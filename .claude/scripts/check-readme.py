#!/usr/bin/env python3
"""Проверка README проектов: есть ли обязательные разделы (правило «README — часть результата»,
список разделов — `.claude/scripts/README.md`, раздел про check-readme.py).

Зачем: без машинной проверки правило «README — часть результата» тихо деградирует — разделы
«инварианты» и «как понять, что сломалось» пропускают чаще всего. Проверяется наличие раздела
по заголовку, а не качество текста: зелёный результат значит «вопрос задавали», а не «ответ верный».

Что считается README проекта: `projects/<проект>/README.md` (на один уровень под `projects/`).

Запуск (из корня репозитория):
    python3 .claude/scripts/check-readme.py --changed          # в гейте: README, тронутые в рабочем дереве против HEAD
    python3 .claude/scripts/check-readme.py projects/X/README.md [...]
    python3 .claude/scripts/check-readme.py --all              # все README проектов (легаси даст пробелы)

`--changed` — режим для гейта: смотрит только `projects/` — README, изменённые против HEAD
(без удалённых) и новые неотслеживаемые. Старые README чинятся, когда к проекту возвращаются
(ENGINEERING.md §4d про ужесточение шаблона над непустым корпусом), а не одной кампанией.

README папки, которая сама ничего не исполняет (индекс, база знаний), помечается строкой
`<!-- readme-check: skip — <причина> -->`: пропуск печатается и считается в итоге отдельно.

Коды возврата: 0 — все проверенные README полные; 1 — есть пробелы; 2 — файл не найден или
ошибка вызова. Размер больше 800 строк — предупреждение, код не меняет.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPLIT_THRESHOLD = 800

# (ключ, человеческое имя, регулярка по тексту заголовка в нижнем регистре).
# Формулировки заголовков в наших README разные, поэтому ищем по основам слов.
REQUIRED = [
    ("flow", "поток данных по шагам",
     r"поток|схем|как (это |оно )?(работает|устроен)|по шагам|внутри|архитектур|flow|pipeline"),
    ("why", "почему так: решения и отвергнутые варианты",
     r"почему|решени|зачем так|why|отвергнут"),
    ("external", "что трогает снаружи (поля, id, каналы, координаты доступа)",
     r"снаружи|внешн|интеграц|каналы|что трогает|откуда (берутся|приходят)|touches|external"),
    ("invariants", "инварианты: идемпотентность, что не перезаписывается",
     r"инвариант|идемпотент|invariant|гаранти"),
    ("run", "запуск, проверка, деплой",
     r"запуск|запустить|деплой|выкладк|установк|run|deploy|тест"),
    ("broken", "как понять, что сломалось",
     r"сломал|наблюдаем|мониторинг|инцидент|алерт|диагност|troubleshoot|observab"),
]

SKIP = re.compile(r"<!--\s*readme-check:\s*skip\s*[—:-]?\s*(.+?)\s*-->")
HEADING = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
FENCE = re.compile(r"^\s*(```|~~~)")


def headings_and_intro(text: str) -> tuple[list[str], bool]:
    """Заголовки вне блоков кода и признак непустого вступления между H1 и первым H2."""
    heads: list[str] = []
    in_fence = False
    seen_h1 = False
    seen_h2 = False
    intro = False
    for line in text.splitlines():
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = HEADING.match(line)
        if m:
            level = len(m.group(1))
            heads.append(m.group(2).lower())
            if level == 1:
                seen_h1 = True
            elif level >= 2:
                seen_h2 = True
            continue
        if seen_h1 and not seen_h2 and line.strip() and not line.lstrip().startswith(("|", ">", "---")):
            intro = True
    return heads, intro


def skip_reason(text: str) -> str | None:
    """Индексный или не-программный README помечается явно, с причиной — пропуск виден в файле и в итоге."""
    m = SKIP.search(text)
    return m.group(1) if m else None


def check(path: Path) -> tuple[list[str], list[str]]:
    """Возвращает (пробелы, предупреждения)."""
    text = path.read_text(encoding="utf-8")
    heads, intro = headings_and_intro(text)
    gaps: list[str] = []
    if not intro:
        gaps.append("что делает: нет вступительного абзаца между заголовком H1 и первым разделом")
    for _key, name, pattern in REQUIRED:
        rx = re.compile(pattern)
        if not any(rx.search(h) for h in heads):
            gaps.append(name)
    warnings: list[str] = []
    lines = text.count("\n") + 1
    if lines > SPLIT_THRESHOLD:
        warnings.append(f"{lines} строк > {SPLIT_THRESHOLD}: разбить на части в docs/ с оглавлением в README")
    return gaps, warnings


def is_project_readme(rel: str) -> bool:
    parts = rel.split("/")
    if parts[-1] != "README.md" or parts[0] != "projects":
        return False
    return len(parts) == 3  # projects/<проект>/README.md


def git_lines(*args: str) -> list[str]:
    out = subprocess.run(
        ["git", "-c", "core.quotePath=false", *args],
        cwd=ROOT, capture_output=True, text=True, check=True,
    ).stdout
    return [line for line in out.splitlines() if line.strip()]


def changed_readmes() -> list[Path]:
    names = set(git_lines("diff", "--name-only", "--diff-filter=d", "HEAD", "--", "projects"))
    names |= set(git_lines("ls-files", "--others", "--exclude-standard", "--", "projects"))
    return [ROOT / n for n in sorted(names) if is_project_readme(n)]


def all_readmes() -> list[Path]:
    return sorted((ROOT / "projects").glob("*/README.md"))


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__.strip().split("\n\n")[2])
        return 2
    if argv == ["--changed"]:
        targets, scope = changed_readmes(), "изменённых README проектов"
    elif argv == ["--all"]:
        targets, scope = all_readmes(), "README проектов"
    else:
        targets, scope = [Path(a) if Path(a).is_absolute() else Path.cwd() / a for a in argv], "указанных файлов"
        missing = [t for t in targets if not t.is_file()]
        if missing:
            for t in missing:
                print(f"✗ файл не найден: {t}")
            return 2

    failed = 0
    skipped = 0
    for path in targets:
        rel = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
        reason = skip_reason(path.read_text(encoding="utf-8"))
        if reason:
            skipped += 1
            print(f"— {rel}: пропущен по пометке ({reason})")
            continue
        gaps, warnings = check(path)
        if gaps:
            failed += 1
            print(f"✗ {rel}")
            for g in gaps:
                print(f"    нет раздела: {g}")
        else:
            print(f"✓ {rel}")
        for w in warnings:
            print(f"    ⚠ {w}")

    # Вердикт над размером выборки: «0 проверено» не должно выглядеть как «всё хорошо».
    checked = len(targets) - skipped
    if checked == 0:
        print(f"— {scope}: проверено 0 (найдено {len(targets)}, пропущено по пометке {skipped}); "
              "это пустая выборка, а не зелёный результат")
        return 0
    print(f"Итог: {checked - failed} из {checked} {scope} полные"
          + (f"; с пробелами — {failed}" if failed else "")
          + (f"; пропущено по пометке — {skipped}" if skipped else ""))
    if failed:
        print("  Список обязательных разделов: .claude/scripts/README.md, раздел check-readme.py.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
