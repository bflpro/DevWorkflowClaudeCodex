#!/usr/bin/env python3
"""owns-check — did the task stay inside its declared file ownership?

Usage: owns-check.py work/<feature> <task-number> [--start-commit SHA] [--quiet]

Reads owns_paths / never_touch / start_commit from the task frontmatter, lists
every file changed since start_commit (committed, staged, unstaged, untracked),
and classifies:
  - inside owns_paths                       → ok
  - inside work/<feature>/                  → ignored (logs, decisions, receipts)
  - matches never_touch                     → violation (always, even if owned)
  - anything else                           → violation (leak outside ownership)

Writes work/<feature>/logs/receipts/task-<N>/owns-check.json (tracked by git —
logs/working/ is ignored, receipts must not be).
Exit 0 = passed, 1 = failed, 3 = skipped (no owns_paths declared), 2 = usage.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from taskflow import (  # noqa: E402
    changed_files, find_task, head_commit, now_iso, owned_by, path_matches,
    repo_root, task_receipts_dir, write_json,
)


def classify(files: list[str], owns: list[str], never: list[str], feature_rel: str) -> dict:
    inside, ignored, leaks, forbidden = [], [], [], []
    for f in files:
        if any(path_matches(f, n) for n in never):
            forbidden.append(f)
        elif path_matches(f, feature_rel):
            ignored.append(f)
        elif owned_by(f, owns):
            inside.append(f)
        else:
            leaks.append(f)
    return {"inside": inside, "ignored": ignored, "leaks": leaks, "forbidden": forbidden}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("feature_dir", type=Path)
    ap.add_argument("task")
    ap.add_argument("--start-commit", help="override start_commit from frontmatter")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--ignore-untracked", action="store_true",
                    help="shared checkout: skip files git does not track (other lanes' drafts)")
    ap.add_argument("--ignore", action="append", default=[], metavar="PATH",
                    help="shared checkout: another lane's uncommitted file; recorded in the receipt as ignored_by_lead")
    args = ap.parse_args(argv)

    try:
        task = find_task(args.feature_dir, args.task)
    except (FileNotFoundError, ValueError) as e:
        print(f"owns-check: {e}", file=sys.stderr)
        return 2

    repo = repo_root(args.feature_dir.resolve())
    feature_rel = str(args.feature_dir.resolve().relative_to(repo))
    out_path = task_receipts_dir(args.feature_dir, task.number) / "owns-check.json"

    if not task.owns_paths:
        result = {"task": task.number, "result": "skipped", "reason": "no owns_paths in frontmatter",
                  "checked_at": now_iso()}
        write_json(out_path, result)
        if not args.quiet:
            print(f"owns-check: task {task.number} skipped — no owns_paths declared")
        return 3

    start = args.start_commit or task.frontmatter.get("start_commit")
    if not start:
        print(f"owns-check: task {task.number} has no start_commit (set when status → in_progress)",
              file=sys.stderr)
        return 2

    files = changed_files(repo, str(start), task_number=task.number,
                          ignore_untracked=args.ignore_untracked)
    ignored_by_lead = [f for f in files if f in set(args.ignore)]
    files = [f for f in files if f not in set(args.ignore)]
    buckets = classify(files, task.owns_paths, task.never_touch, feature_rel)
    passed = not buckets["leaks"] and not buckets["forbidden"]
    result = {
        "task": task.number,
        "task_sha256": task.body_sha256,
        "start_commit": str(start),
        "ignored_by_lead": ignored_by_lead,
        "head_commit": head_commit(repo),
        "owns_paths": task.owns_paths,
        "never_touch": task.never_touch,
        "files_changed": files,
        **buckets,
        "result": "passed" if passed else "failed",
        "checked_at": now_iso(),
    }
    write_json(out_path, result)

    if not args.quiet:
        print(f"owns-check: task {task.number} — {result['result']} "
              f"({len(buckets['inside'])} inside, {len(buckets['ignored'])} ignored)")
        for f in buckets["forbidden"]:
            print(f"  ✗ never_touch: {f}")
        for f in buckets["leaks"]:
            print(f"  ✗ outside owns_paths: {f}")
        print(f"  → {out_path}")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
