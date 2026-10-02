#!/usr/bin/env python3
"""task-accept — the only technical definition of "task done".

Usage: task-accept.py work/<feature> <task-number> [--skip-verification] [--quiet]

Builds work/<feature>/logs/receipts/task-<N>/acceptance.json (tracked by git;
reviewer reports in logs/working/ are not) from evidence the script gathers
itself — never from the executor's narrative:

  task_sha256      hash of the task body (after frontmatter) — the contract
  start/end commit from frontmatter start_commit and git HEAD
  attempt          number of review rounds seen (max round across reviewers)
  verification[]   every command under "## Verification Steps" → Automated /
                   Smoke is RUN here (cwd = frontmatter verify_cwd or repo root,
                   timeout 900 s) and its exit code recorded
  owns_check       from owns-check.json (owns-check.py is run if missing)
  reviews[]        latest-round status per reviewer (findings-sync is run first)
  findings         open / open_critical counts from the canonical finding files

  accepted = all verification exit codes match ∧ owns_check ∈ {passed, skipped}
             ∧ no reviewer's latest status is changes_required or unreadable
             ∧ a latest status "triaged" (lead closure) leaves open == 0
             ∧ open_critical == 0

Exit 0 = accepted, 1 = not accepted (reasons printed), 2 = usage.
A task whose status is set to `done` without an accepted receipt has bypassed
the flow — that is the signal to look for.
"""
from __future__ import annotations

import argparse
import importlib.util
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from taskflow import (  # noqa: E402
    DEFAULT_TIMEOUT_SEC, Task, find_task, head_commit, load_reports, now_iso,
    read_json, repo_root, task_log_dir, task_receipts_dir, write_json,
)

SCRIPTS = Path(__file__).resolve().parent
CMD_LINE_RE = re.compile(r"^\s*-\s+`(?P<cmd>[^`]+)`\s*(?:→|->)?\s*(?P<expected>.*)$")
EXIT_RE = re.compile(r"exit\s+(?:code\s+)?(\d+)", re.IGNORECASE)


def _load_module(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def verification_commands(task: Task) -> list[dict]:
    """Bullet commands under '## Verification Steps' → '### Automated' / '### Smoke'."""
    lines = task.body.splitlines()
    in_section = False
    sub = ""
    out: list[dict] = []
    for line in lines:
        if line.startswith("## "):
            in_section = line.strip().lower().startswith("## verification steps")
            sub = ""
            continue
        if not in_section:
            continue
        if line.startswith("### "):
            sub = line[4:].strip().lower()
            continue
        if sub not in ("automated", "smoke"):
            continue
        m = CMD_LINE_RE.match(line)
        if not m:
            continue
        expected = m.group("expected").strip()
        exit_m = EXIT_RE.search(expected)
        out.append({"kind": sub, "command": m.group("cmd").strip(),
                    "expected": expected, "expected_exit": int(exit_m.group(1)) if exit_m else 0})
    return out


def run_commands(cmds: list[dict], cwd: Path, timeout: int) -> list[dict]:
    results = []
    for c in cmds:
        try:
            proc = subprocess.run(c["command"], shell=True, cwd=str(cwd), capture_output=True,
                                  text=True, timeout=timeout)
            exit_code, output = proc.returncode, (proc.stdout + proc.stderr)[-2000:]
        except subprocess.TimeoutExpired:
            exit_code, output = None, f"timeout after {timeout}s"
        results.append({**c, "cwd": str(cwd), "exit_code": exit_code, "output_tail": output,
                        "ok": exit_code == c["expected_exit"], "ran_at": now_iso()})
    return results


def review_reasons(reviews: list[dict], fsum: dict) -> list[str]:
    """Why the latest review round of each reviewer blocks acceptance.

    `triaged` is the lead closing findings (build-route step 6), not a reviewer
    verdict, so it only passes when no finding is left open (an `ask` closure
    keeps its finding open until the human answers).
    """
    reasons: list[str] = []
    for rv in reviews:
        where = f"reviewer {rv['reviewer']} round {rv['round']}"
        if rv["status"] == "changes_required":
            reasons.append(f"{where}: changes_required")
        elif rv["status"] == "triaged" and fsum.get("open"):
            reasons.append(f"{where}: triaged with {fsum['open']} open finding(s) — see FINDINGS.md")
        elif rv["status"] == "unknown":
            reasons.append(f"{where}: status unreadable in {rv['report']}")
    return reasons


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("feature_dir", type=Path)
    ap.add_argument("task")
    ap.add_argument("--skip-verification", action="store_true",
                    help="do not run verification commands (receipt records them as not_run → not accepted)")
    ap.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SEC)
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--ignore-untracked", action="store_true",
                    help="passed to owns-check: skip untracked files (shared checkout)")
    ap.add_argument("--ignore", action="append", default=[], metavar="PATH",
                    help="passed to owns-check: another lane's uncommitted file (recorded as ignored_by_lead)")
    args = ap.parse_args(argv)

    try:
        task = find_task(args.feature_dir, args.task)
    except (FileNotFoundError, ValueError) as e:
        print(f"task-accept: {e}", file=sys.stderr)
        return 2

    repo = repo_root(args.feature_dir.resolve())
    log_dir = task_log_dir(args.feature_dir, task.number)          # reviewer reports (gitignored)
    receipts_dir = task_receipts_dir(args.feature_dir, task.number)  # receipts (tracked)
    receipts_dir.mkdir(parents=True, exist_ok=True)
    reasons: list[str] = []

    # --- verification -------------------------------------------------------
    cmds = verification_commands(task)
    verify_cwd = repo / str(task.frontmatter.get("verify_cwd") or ".")
    if args.skip_verification:
        verification = [{**c, "exit_code": None, "ok": False, "output_tail": "not_run"} for c in cmds]
        if cmds:
            reasons.append("verification skipped (--skip-verification)")
    else:
        verification = run_commands(cmds, verify_cwd, args.timeout)
        for v in verification:
            if not v["ok"]:
                reasons.append(f"verification failed: `{v['command']}` → exit {v['exit_code']} "
                               f"(expected {v['expected_exit']})")
    if not cmds:
        reasons_note = "no verification commands in task (verify: none?)"
    else:
        reasons_note = ""

    # --- owns check ---------------------------------------------------------
    owns_path = receipts_dir / "owns-check.json"
    owns_mod = _load_module("owns-check")
    owns_args = [str(args.feature_dir), task.number, "--quiet"]
    if args.ignore_untracked:
        owns_args.append("--ignore-untracked")
    for path in args.ignore:
        owns_args += ["--ignore", path]
    owns_rc = owns_mod.main(owns_args)
    owns = read_json(owns_path) or {}
    owns_result = owns.get("result", "missing")
    if owns_rc == 2:
        owns_result = "missing"
        reasons.append("owns-check could not run (no start_commit?)")
    elif owns_result == "failed":
        reasons.append(f"owns-check failed: {len(owns.get('leaks', []))} leak(s), "
                       f"{len(owns.get('forbidden', []))} never_touch hit(s)")

    # --- findings + reviews -------------------------------------------------
    findings_mod = _load_module("findings-sync")
    fsum = (findings_mod.sync(log_dir, receipts_dir) if log_dir.is_dir()
            else {"open": 0, "open_critical": 0, "latest_round": {}})
    reports = load_reports(log_dir)
    latest: dict[str, dict] = {}
    for r in reports:
        if r.reviewer not in latest or r.round > latest[r.reviewer]["round"]:
            latest[r.reviewer] = {"reviewer": r.reviewer, "round": r.round, "status": r.status,
                                  "report": r.path.name}
    reviews = sorted(latest.values(), key=lambda x: x["reviewer"])
    reasons += review_reasons(reviews, fsum)
    if fsum["open_critical"]:
        reasons.append(f"{fsum['open_critical']} open critical finding(s) — see FINDINGS.md")
    attempt = max([rv["round"] for rv in reviews], default=0) or 1

    accepted = not reasons
    receipt = {
        "schema_version": 1,
        "feature": args.feature_dir.name,
        "task": task.number,
        "task_sha256": task.body_sha256,
        "start_commit": task.frontmatter.get("start_commit"),
        "end_commit": head_commit(repo),
        "attempt": attempt,
        "verification": verification,
        "verification_note": reasons_note,
        "owns_check": owns_result,
        "owns_check_file": owns_path.name if owns_path.exists() else None,
        "reviews": reviews,
        "findings": {"open": fsum["open"], "open_critical": fsum["open_critical"]},
        "accepted": accepted,
        "reasons": reasons,
        "accepted_at": now_iso() if accepted else None,
        "generated_at": now_iso(),
    }
    write_json(receipts_dir / "acceptance.json", receipt)

    if not args.quiet:
        verdict = "ACCEPTED" if accepted else "NOT ACCEPTED"
        print(f"task-accept: task {task.number} — {verdict} "
              f"(attempt {attempt}, {sum(1 for v in verification if v['ok'])}/{len(verification)} checks ok, "
              f"owns {owns_result}, {len(reviews)} reviewer(s), {fsum['open_critical']} open critical)")
        for r in reasons:
            print(f"  ✗ {r}")
        if reasons_note:
            print(f"  ℹ {reasons_note}")
        print(f"  → {receipts_dir / 'acceptance.json'}")
    return 0 if accepted else 1


if __name__ == "__main__":
    sys.exit(main())
