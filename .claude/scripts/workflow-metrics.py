#!/usr/bin/env python3
"""Task-scoped local workflow metrics. No network, raw transcripts or LLM calls."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import tempfile
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / ".claude/shared/workflow-resources/policy.json"
TOKEN_FIELDS = ("input_uncached", "cache_read", "cache_write", "output")


def read_object(path, limit=1048576):
    if path.is_symlink() or path.stat().st_size > limit:
        raise ValueError("unsupported or oversized metrics input")
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise TypeError("expected JSON object")
    return value


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as stream:
        json.dump(value, stream, ensure_ascii=False, separators=(",", ":"))
        stream.write("\n")
        name = stream.name
    try:
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def number(value):
    # Reject bool, negative, NaN and unbounded values, never convert missing to zero.
    return value if type(value) in (int, float) and 0 <= value <= 10**15 else None


def safe_model(value):
    return (
        value
        if isinstance(value, str)
        and re.fullmatch(
            r"gpt-\d+(?:\.\d+)?-(?:sol|terra|luna|astra)(?:-\d{4}-\d{2}-\d{2})?"
            r"|claude-(?:opus|sonnet|haiku)-\d+(?:[-.]\d+){0,2}(?:-\d{8})?"
            r"|opus|sonnet|haiku",
            value,
        )
        else None
    )


def resources(value):
    value = value if isinstance(value, dict) else {}
    return {
        "model": safe_model(value.get("model")),
        "effort": value.get("effort")
        if value.get("effort") in ("low", "medium", "high", "xhigh", "max", "ultra")
        else None,
    }


def run_summary(data, names):
    role = data.get("role")
    if not isinstance(role, str) or role not in names:
        raise ValueError("unclassified run role")
    usage = data.get("usage")
    usage = usage if isinstance(usage, dict) else {}
    return {
        "role": role,
        "runtime": data.get("runtime")
        if data.get("runtime") in ("claude", "codex")
        else "unknown",
        "mode": data.get("mode")
        if data.get("mode") in ("inline", "delegated")
        else "unknown",
        "requested": resources(data.get("requested")),
        "actual": resources(data.get("actual")),
        "usage": {
            key: number(usage.get(key)) if type(usage.get(key)) is int else None
            for key in TOKEN_FIELDS
        },
        "elapsed_seconds": number(data.get("elapsed_seconds")),
        "waiting_seconds": number(data.get("waiting_seconds")),
        "escalated": data.get("escalated") is True,
    }


def finding_route(data):
    # Legacy evidence is heuristic; never infer route or severity from closed alone.
    triage = data.get("triage")
    if isinstance(triage, dict) and triage.get("route") in (
        "patch",
        "false",
        "defer",
        "ask",
        "duplicate",
    ):
        return triage["route"]
    closure = data.get("closed_by")
    text = str(closure.get("evidence", "")).lower() if isinstance(closure, dict) else ""
    matches = [
        name
        for name, pattern in (
            ("patch", r"\bpatch\b|исправлен"),
            ("false", r"\bfalse\b|ложн|не подтверж"),
            ("defer", r"\bdefer\b|отлож"),
        )
        if re.search(pattern, text)
    ]
    return matches[0] if len(matches) == 1 else "unknown"


def summarize_task(feature, task, receipt, policy):
    if not re.fullmatch(r"[0-9]{1,6}", str(task)):
        raise ValueError("numeric task id required")
    limits = policy["collection"]
    record = {
        "accepted": receipt.get("accepted") is True,
        "contract": receipt.get("task_sha256"),
        "task": str(task),
        "feature_id": hashlib.sha256(str(feature.resolve()).encode()).hexdigest()[:12],
        "review_round_max": 0,
        "reviewer_count": 0,
        "findings": {},
        "runs": [],
        "input_errors": 0,
        "runs_truncated": False,
    }
    reviews = receipt.get("reviews", [])
    if isinstance(reviews, list):
        rounds = [r.get("round") for r in reviews if isinstance(r, dict)]
        record["review_round_max"] = max(
            [v for v in rounds if type(v) is int and 0 <= v <= 10000], default=0
        )
        record["reviewer_count"] = len(reviews)
    counts = Counter()
    folder = feature / f"logs/receipts/task-{task}/findings"
    for index, path in enumerate(sorted(folder.glob("*.json"))):
        if index >= 5000:
            record["input_errors"] += 1
            break
        try:
            data = read_object(path, limits["max_json_bytes"])
            counts["records"] += 1
            counts[finding_route(data)] += 1
            if data.get("status") == "open":
                counts["open"] += 1
        except (OSError, ValueError, TypeError):
            record["input_errors"] += 1
    record["findings"] = dict(counts)
    logdir = feature / f"logs/working/task-{task}"
    names = (
        set(policy["roles"])
        | set(policy["lenses"])
        | {"implementation", "specification", "research", "extraction"}
    )
    for index, path in enumerate(sorted(logdir.glob("evidence-workflow-run-*.json"))):
        if index >= limits["max_runs_per_task"]:
            record["runs_truncated"] = True
            break
        try:
            run = run_summary(read_object(path, limits["max_json_bytes"]), names)
            run["run_key"] = hashlib.sha256(path.name.encode()).hexdigest()[:16]
            record["runs"].append(run)
        except (OSError, ValueError, TypeError):
            record["input_errors"] += 1
    return record


def report_text(records, now):
    values = list(records.values())
    findings = Counter()
    runs = []
    for row in values:
        findings.update(row["findings"])
        runs.extend(row["runs"])
    lines = [
        "# Локальная сводка workflow",
        "",
        f"Сформировано: {now.isoformat()}",
        "",
        (f"Контрактов задач: {len(values)}; принято: {sum(v['accepted'] for v in values)}; "
        f"попыток приёмки: {sum(v['attempts'] for v in values)}."),
        (f"Сохранено записей выполнения: {len(runs)}; задач без записей выполнения: "
        f"{sum(not v['runs'] for v in values)}."),
        (f"Ошибок входных данных: {sum(v['input_errors'] for v in values)}; "
        f"задач с обрезанным списком выполнений: {sum(v['runs_truncated'] for v in values)}."),
        "",
        ("Раунд в receipt включает закрытие лидом; это не число независимых аудитов. "
        "Findings могут дублировать одну причину; patch включает документацию и тесты. "
        "Классификация старых закрытий по тексту приблизительна. Пустая выборка не доказывает отсутствие ошибок."),
        "",
        "| Решение по записи finding | Число |",
        "|---|---:|",
    ]
    lines += [
        f"| {name} | {findings[name]} |"
        for name in ("patch", "false", "defer", "ask", "duplicate", "unknown", "open")
    ]
    lines += [
        "",
        "| Токены (сумма только наблюдаемых полей) | Сумма | Записей с измерением |",
        "|---|---:|---:|",
    ]
    for key in TOKEN_FIELDS:
        measured = [r["usage"][key] for r in runs if r["usage"][key] is not None]
        lines.append(
            f"| {key} | {sum(measured) if measured else 'unknown'} | {len(measured)}/{len(runs)} |"
        )
    lines += [
        "",
        ("Наблюдаемые счётчики — переданные task-scoped измерения, не биллинг. "
        "Отсутствие полей остаётся unknown. Cache read/write считаются отдельно от некэшированного входа."),
        "",
        "| Роль | Выполнений | Фактическая модель неизвестна | Усилений |",
        "|---|---:|---:|---:|",
    ]
    for role in sorted({r["role"] for r in runs}):
        group = [r for r in runs if r["role"] == role]
        lines.append(
            f"| {role} | {len(group)} | {sum(r['actual']['model'] is None for r in group)} | {sum(r['escalated'] for r in group)} |"
        )
    lines += [
        "",
        "| Runtime / фактическая модель / effort | Выполнений |",
        "|---|---:|",
    ]
    distribution = Counter(
        (
            r["runtime"],
            r["actual"]["model"] or "unknown",
            r["actual"]["effort"] or "unknown",
        )
        for r in runs
    )
    for (runtime, model, effort), count in sorted(distribution.items()):
        lines.append(f"| {runtime} / {model} / {effort} | {count} |")
    for field in ("elapsed_seconds", "waiting_seconds"):
        measured = [r[field] for r in runs if r[field] is not None]
        lines += [
            "",
            (f"{field}: {sum(measured) if measured else 'unknown'}; измерено {len(measured)}/{len(runs)}. "
            "Сумма по агентам не равна длительности задачи при параллельной работе."),
        ]
    lines += ["", "## Сигналы для разбора", ""]
    signals = []
    if findings["records"] >= 20 and findings["false"] / findings["records"] >= 0.25:
        signals.append(
            "Не менее 25% записей findings помечены false: проверить область и вход ревьюеров до изменения модели."
        )
    if any(v["review_round_max"] > 3 for v in values):
        signals.append(
            "Есть receipt с round > 3: проверить, были ли повторные полные проходы или только закрытия findings."
        )
    if len(runs) >= 10 and sum(r["escalated"] for r in runs) / len(runs) >= 0.3:
        signals.append(
            "Не менее 30% выполнений помечены усилением: проверить исходный выбор модели и качество briefing."
        )
    lines += (
        ["- " + s for s in signals]
        if signals
        else [
            "Недостаточно оснований для автоматического сигнала об изменении workflow."
        ]
    )
    lines += [
        "",
        ("Предложения требуют проверки на сопоставимых задачах. Политика и модели автоматически не меняются. "
        "Периодический LLM-разбор вручную использует эту сводку и выбранные обезличенные примеры; "
        "этот отчёт не запускает модель."),
        "",
    ]
    return "\n".join(lines)


def collect(feature, task, receipt, *, root=ROOT, policy=None, now=None):
    policy = policy or read_object(
        root / ".claude/shared/workflow-resources/policy.json"
    )
    now = now or datetime.now(timezone.utc)
    record = summarize_task(feature, task, receipt, policy)
    if not isinstance(record["contract"], str) or not re.fullmatch(
        r"[a-f0-9]{64}", record["contract"]
    ):
        raise ValueError("receipt contract hash missing")
    directory = root / ".claude/state/workflow-metrics"
    if not directory.resolve().is_relative_to(root.resolve()):
        raise ValueError("metrics directory must stay inside the repository")
    directory.mkdir(parents=True, exist_ok=True)
    if (directory / "lock").is_symlink():
        raise ValueError("metrics lock cannot be a symlink")
    # Directory is ignored; a single repository-level lock covers state and report.
    with (directory / "lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        path = directory / "state.json"
        state = (
            read_object(path, 64 * 1024 * 1024)
            if path.exists()
            else {"version": 1, "records": {}, "last_report": now.isoformat()}
        )
        records = state["records"]
        key = f"{record['feature_id']}:{task}:{record['contract']}"
        old = records.get(key, {})
        receipt_hash = hashlib.sha256(
            json.dumps(receipt, sort_keys=True).encode()
        ).hexdigest()
        record["attempts"] = old.get("attempts", 0) + int(
            receipt_hash != old.get("receipt_hash")
        )
        record["receipt_hash"] = receipt_hash
        merged = {r["run_key"]: r for r in old.get("runs", [])}
        merged.update({r["run_key"]: r for r in record["runs"]})
        record["runs_truncated"] |= (
            old.get("runs_truncated", False)
            or len(merged) > policy["collection"]["max_runs_per_task"]
        )
        record["runs"] = list(merged.values())[
            -policy["collection"]["max_runs_per_task"] :
        ]
        record["updated_at"] = now.isoformat()
        record["accepted_once"] = old.get("accepted_once", False) or record["accepted"]
        record["reported"] = old.get("reported", False)
        # Repeated acceptance refreshes a snapshot; token/run counts are never appended again.
        records[key] = record
        cutoff = (
            now - timedelta(days=policy["collection"]["retention_days"])
        ).isoformat()
        records = {k: v for k, v in records.items() if v["updated_at"] >= cutoff}
        records = dict(
            sorted(records.items(), key=lambda kv: kv[1]["updated_at"])[
                -policy["collection"]["max_tasks"] :
            ]
        )
        pending = sum(
            v["accepted_once"] and not v["reported"] for v in records.values()
        )
        elapsed = now - datetime.fromisoformat(state["last_report"])
        due = pending >= policy["collection"]["report_every_tasks"] or (
            pending > 0
            and elapsed >= timedelta(days=policy["collection"]["report_every_days"])
        )
        state["records"] = records
        if due:
            write_report(directory, records, now)
            state["last_report"] = now.isoformat()
            for value in records.values():
                value["reported"] = value["accepted_once"]
        atomic_json(path, state)
    return {
        "records": len(records),
        "report_updated": due,
        "usage_runs": len(record["runs"]),
        "input_errors": record["input_errors"],
    }


def write_report(directory, records, now):
    text = report_text(records, now)
    with tempfile.NamedTemporaryFile(mode="w", dir=directory, delete=False) as stream:
        stream.write(text)
        name = stream.name
    try:
        os.replace(name, directory / "report.md")
    finally:
        Path(name).unlink(missing_ok=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("command", choices=("collect", "report"))
    ap.add_argument("feature", nargs="?", type=Path)
    ap.add_argument("task", nargs="?")
    ap.add_argument("--root", type=Path, default=ROOT)
    args = ap.parse_args(argv)
    try:
        if args.command == "collect":
            if args.feature is None or args.task is None:
                ap.error("collect requires feature and task")
            receipt = read_object(
                args.feature / f"logs/receipts/task-{args.task}/acceptance.json"
            )
            print(json.dumps(collect(args.feature, args.task, receipt, root=args.root)))
        else:
            directory = args.root / ".claude/state/workflow-metrics"
            if (
                not directory.resolve().is_relative_to(args.root.resolve())
                or (directory / "lock").is_symlink()
            ):
                raise ValueError("unsupported metrics location")
            with (directory / "lock").open("a") as lock:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                state = read_object(directory / "state.json", 64 * 1024 * 1024)
                now = datetime.now(timezone.utc)
                write_report(directory, state["records"], now)
                print(report_text(state["records"], now))
    except (OSError, ValueError, KeyError, TypeError):
        # Do not echo exception text: it may include untrusted source content.
        print(
            "workflow-metrics: incomplete or unavailable input/state; no raw content printed"
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
