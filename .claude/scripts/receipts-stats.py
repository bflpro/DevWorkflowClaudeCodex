#!/usr/bin/env python3
"""receipts-stats.py — сводка по квитанциям приёмки: сколько задач прошло с первого раза,
сколько раундов ревью стоит задача, какие линзы находят, а какие молчат.

Читает `work/*/logs/receipts/task-*/acceptance.json` (пишет их `task-accept.py`).

Запуск:  python3 .claude/scripts/receipts-stats.py [--root <репо>] [--by-feature] [--since YYYY-MM-DD]
Коды:    0 — сводка напечатана; 1 — часть квитанций не прочиталась (список в выводе);
         2 — квитанций нет.

Определения:
  принята         — `accepted: true`
  с первого раза  — принята, `attempt` = 1 и у всех ревью `round` = 1
  раундов         — максимальный `round` среди ревью квитанции
  по ревьюерам    — сколько квитанций видел ревьюер (линза или агент) и в скольких его
                    последний раунд закончился не `approved` / `triaged`

Идея — отчёт оркестратора «first-pass QA rate, retries per task» из
`msitarzewski/agency-agents` @ `f99f6aa` (MIT), strategy/coordination; у нас эти цифры уже
лежат в квитанциях, скрипт их только складывает. Код свой.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

CLOSED_STATUSES = {"approved", "triaged"}


def load_receipts(root: Path) -> tuple[list[dict], list[str]]:
    """Вернуть (квитанции, пути нечитаемых). Счётчик файлов — независимо от разбора."""
    paths = sorted(root.glob("work/*/logs/receipts/task-*/acceptance.json"))
    receipts: list[dict] = []
    broken: list[str] = []
    for p in paths:
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            broken.append(str(p.relative_to(root)))
            continue
        if not isinstance(data, dict) or "accepted" not in data:
            broken.append(str(p.relative_to(root)))
            continue
        data.setdefault("feature", p.parents[3].name)
        data.setdefault("task", p.parent.name.removeprefix("task-"))
        receipts.append(data)
    assert len(receipts) + len(broken) == len(paths), "счётчик файлов разошёлся с разбором"
    return receipts, broken


def max_round(r: dict) -> int:
    rounds = [int(x.get("round", 1)) for x in r.get("reviews", []) if isinstance(x, dict)]
    return max(rounds) if rounds else 0


def first_pass(r: dict) -> bool:
    return bool(r.get("accepted")) and int(r.get("attempt", 1)) == 1 and max_round(r) <= 1


def summarize(receipts: list[dict]) -> dict:
    total = len(receipts)
    accepted = sum(1 for r in receipts if r.get("accepted"))
    fp = sum(1 for r in receipts if first_pass(r))
    rounds = Counter(max_round(r) for r in receipts)
    by_reviewer: dict[str, dict] = defaultdict(lambda: {"seen": 0, "not_closed": 0})
    for r in receipts:
        last: dict[str, dict] = {}
        for rev in r.get("reviews", []):
            if not isinstance(rev, dict) or "reviewer" not in rev:
                continue
            name = str(rev["reviewer"])
            if name not in last or int(rev.get("round", 1)) >= int(last[name].get("round", 1)):
                last[name] = rev
        for name, rev in last.items():
            by_reviewer[name]["seen"] += 1
            if str(rev.get("status", "")) not in CLOSED_STATUSES:
                by_reviewer[name]["not_closed"] += 1
    return {
        "total": total,
        "accepted": accepted,
        "first_pass": fp,
        "rounds": dict(sorted(rounds.items())),
        "by_reviewer": dict(sorted(by_reviewer.items())),
    }


def pct(n: int, d: int) -> str:
    return f"{100 * n / d:.0f}%" if d else "—"


def print_summary(s: dict, title: str = "Все квитанции") -> None:
    print(f"## {title}")
    print(f"квитанций: {s['total']}   принято: {s['accepted']} ({pct(s['accepted'], s['total'])})   "
          f"с первого раза: {s['first_pass']} ({pct(s['first_pass'], s['total'])})")
    if s["rounds"]:
        print("раундов ревью → задач: " + ", ".join(f"{k}: {v}" for k, v in s["rounds"].items()))
    if s["by_reviewer"]:
        print("| ревьюер | квитанций | не закрыл |")
        print("|---|---|---|")
        for name, v in s["by_reviewer"].items():
            print(f"| {name} | {v['seen']} | {v['not_closed']} |")
    print()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=None, help="корень репозитория (по умолчанию — от расположения скрипта)")
    ap.add_argument("--by-feature", action="store_true", help="отдельная сводка по каждой фиче")
    ap.add_argument("--since", default=None, help="только квитанции с accepted_at/generated_at ≥ даты (YYYY-MM-DD)")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parents[2]
    receipts, broken = load_receipts(root)
    if args.since:
        receipts = [r for r in receipts
                    if str(r.get("accepted_at") or r.get("generated_at") or "")[:10] >= args.since]
    if not receipts and not broken:
        print("NOT CHECKED: квитанций не найдено — проверь --root и --since")
        return 2

    print_summary(summarize(receipts))
    if args.by_feature:
        by_feature: dict[str, list[dict]] = defaultdict(list)
        for r in receipts:
            by_feature[str(r["feature"])].append(r)
        for feature, items in sorted(by_feature.items()):
            print_summary(summarize(items), feature)
    for b in broken:
        print(f"ERROR не прочиталась квитанция: {b}")
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
