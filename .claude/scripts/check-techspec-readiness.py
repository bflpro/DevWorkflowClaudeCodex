#!/usr/bin/env python3
"""Проверка техспека: уровень объявлен и таблица Prod-readiness заполнена.

Зачем: правило «пустых строк в Prod-readiness быть не должно» (ENGINEERING.md §2) держалось на
дисциплине модели. Шаблон техспека к тому же существует в двух копиях (проектной и личной),
и личная перекрывает проектную — поэтому проверять надо результат, а не шаблон.

Запуск:
    python3 .claude/scripts/check-techspec-readiness.py work/<feature>/tech-spec.md
    python3 .claude/scripts/check-techspec-readiness.py --changed    # только изменённые против main
    python3 .claude/scripts/check-techspec-readiness.py --all        # все техспеки в work/ (у легаси будут пробелы)

Таблица Prod-readiness могла появиться в шаблоне позже части техспеков, и старые её не проходят.
Поэтому в гейтах используется `--changed` — правило применяется к новому,
а старое чинится по мере возвращения к фиче.

Коды возврата: 0 — годен, 1 — есть незаполненное, 2 — файл не найден/не техспек.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

LEVELS = ("L0", "L1", "L2", "L3")
# строки, которые обязаны быть в таблице (сокращённые ключи для устойчивости к формулировкам)
REQUIRED_ROWS = [
    ("идемпотент", "идемпотентность записей наружу"),
    ("ретра", "ретраи и таймауты внешних вызовов"),
    ("вебхук", "повторная доставка вебхука / лок cron"),
    ("состояни", "где хранится состояние перехода"),
    ("наблюдаем", "наблюдаемость: метрика или алерт"),
    ("откат", "план отката"),
]
LLM_MARKERS = ("llm", "промпт", "prompt", "модел", "openai", "anthropic", "deepseek", "агент")


def check(path: Path) -> list[str]:
    problems: list[str] = []
    text = path.read_text()

    m = re.search(r"^level:\s*(\S+)", text, re.M)
    if not m:
        problems.append("нет `level:` во frontmatter — уровень зрелости не объявлен (ENGINEERING.md §0)")
    elif m.group(1).strip().rstrip(":").upper() not in LEVELS:
        problems.append(f"level: {m.group(1)} — допустимы {', '.join(LEVELS)}")

    block = re.search(r"Prod-readiness.*?\n((?:\|.*\n)+)", text, re.S)
    if not block:
        problems.append("нет таблицы Prod-readiness в разделе Risks (ENGINEERING.md §2)")
        return problems

    rows = [r for r in block.group(1).splitlines() if r.strip().startswith("|")]
    empty, present = [], []
    for row in rows:
        cells = [c.strip() for c in row.strip().strip("|").split("|")]
        if len(cells) < 2 or set("".join(cells)) <= set("-: "):
            continue  # разделитель таблицы
        aspect, answer = cells[0], cells[1]
        if aspect.lower().startswith(("аспект", "as of")):
            continue
        present.append(aspect.lower())
        if not answer:
            empty.append(aspect)

    for row in empty:
        problems.append(f"пустая ячейка: «{row}» — пустая строка означает, что вопрос не задавали")

    for key, human in REQUIRED_ROWS:
        if not any(key in a for a in present):
            problems.append(f"нет строки про {human}")

    low = text.lower()
    if any(k in low for k in LLM_MARKERS):
        if not any("стоимост" in a or "гейт" in a for a in present):
            problems.append("фича трогает LLM, но в Prod-readiness нет строки про лимит стоимости и гейт автозапуска")
        if "eval" not in low:
            problems.append("фича трогает LLM, но в Testing Strategy нет раздела Evals (критерии, набор, порог регресса)")
    return problems


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    targets: list[Path]
    if argv[0] == "--all":
        targets = sorted(Path("work").glob("*/tech-spec.md"))
    elif argv[0] == "--changed":
        import subprocess

        base = argv[1] if len(argv) > 1 else "main"
        try:
            out = subprocess.run(
                ["git", "diff", "--name-only", f"{base}...HEAD"],
                capture_output=True, text=True, timeout=30, check=True,
            ).stdout
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as exc:
            print(f"не смог получить дифф против {base}: {exc}")
            return 2
        changed = [Path(l) for l in out.split() if l.endswith("tech-spec.md")]
        if not changed:
            print(f"техспеки против {base} не менялись — проверять нечего")
            return 0
        targets = changed
    else:
        targets = [Path(a) for a in argv]

    bad = 0
    for t in targets:
        if not t.exists():
            print(f"❌ {t}: файла нет")
            bad += 1
            continue
        problems = check(t)
        if problems:
            bad += 1
            print(f"❌ {t}")
            for pr in problems:
                print(f"     - {pr}")
        else:
            print(f"✅ {t}")
    if bad:
        print(f"\nтехспеков с пробелами: {bad} из {len(targets)}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
