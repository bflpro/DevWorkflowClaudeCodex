#!/usr/bin/env python3
"""wave-check — can the tasks of each wave really run in parallel?

Usage: wave-check.py work/<feature> [--json]

Checks, per wave, over task frontmatter (owns_paths / reads / depends_on / wave):
  1. owns_paths of any two tasks in the same wave do not overlap (prefix-aware);
  2. reads of one task do not intersect owns_paths of a wave-mate — that is a
     dependency the wave declaration contradicts;
  3. every depends_on points to a task in a strictly earlier wave.

Exit 0 = clean, 1 = violations found (print them), 2 = usage / unreadable input.
Tasks with no owns_paths are reported as "skipped" and do not fail the check —
old features predate the field.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from taskflow import Task, load_tasks, path_matches, paths_overlap  # noqa: E402


def check(tasks: list[Task]) -> dict:
    by_wave: dict[int, list[Task]] = defaultdict(list)
    for t in tasks:
        by_wave[t.wave].append(t)
    wave_of = {t.number: t.wave for t in tasks}

    violations: list[dict] = []
    skipped = [t.number for t in tasks if not t.owns_paths]

    for wave, members in sorted(by_wave.items()):
        for i, a in enumerate(members):
            for b in members[i + 1:]:
                for pa in a.owns_paths:
                    for pb in b.owns_paths:
                        if paths_overlap(pa, pb):
                            violations.append({
                                "kind": "write/write",
                                "wave": wave, "tasks": [a.number, b.number],
                                "detail": f"task {a.number} owns `{pa}`, task {b.number} owns `{pb}`",
                            })
                for pair in ((a, b), (b, a)):
                    reader, writer = pair
                    for r in reader.reads:
                        for w in writer.owns_paths:
                            if path_matches(r, w) or path_matches(w, r):
                                violations.append({
                                    "kind": "read/write",
                                    "wave": wave, "tasks": [reader.number, writer.number],
                                    "detail": (f"task {reader.number} reads `{r}` which task "
                                               f"{writer.number} owns (`{w}`) — a dependency, "
                                               f"not a wave-mate"),
                                })

    for t in tasks:
        for dep in t.depends_on:
            if dep not in wave_of:
                violations.append({"kind": "depends_on", "wave": t.wave, "tasks": [t.number],
                                   "detail": f"task {t.number} depends on unknown task {dep}"})
            elif wave_of[dep] >= t.wave:
                violations.append({"kind": "depends_on", "wave": t.wave, "tasks": [t.number, dep],
                                   "detail": (f"task {t.number} (wave {t.wave}) depends on task {dep} "
                                              f"(wave {wave_of[dep]}) — dependency must be in an earlier wave")})

    return {"tasks": len(tasks), "waves": sorted(by_wave), "skipped_no_owns_paths": skipped,
            "violations": violations, "ok": not violations}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("feature_dir", type=Path)
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args(argv)

    try:
        tasks = load_tasks(args.feature_dir)
    except (FileNotFoundError, ValueError) as e:
        print(f"wave-check: {e}", file=sys.stderr)
        return 2
    if not tasks:
        print("wave-check: no task files found", file=sys.stderr)
        return 2

    result = check(tasks)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"wave-check: {result['tasks']} tasks, waves {result['waves']}")
        if result["skipped_no_owns_paths"]:
            print(f"  skipped (no owns_paths): {', '.join(result['skipped_no_owns_paths'])}")
        for v in result["violations"]:
            print(f"  ✗ [{v['kind']}] wave {v['wave']}: {v['detail']}")
        print("  OK — waves are parallel-safe" if result["ok"] else f"  {len(result['violations'])} violation(s)")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
