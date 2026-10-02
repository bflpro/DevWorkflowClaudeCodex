#!/usr/bin/env python3
"""findings-sync — reviewer findings as canonical files with a closure state.

Usage: findings-sync.py work/<feature> <task-number> [--quiet]

Reads every reviewer report in work/<feature>/logs/working/task-<N>/
({reviewer}-{round}.json or {reviewer}-round{round}.json, any of the shapes
agents actually emit) and maintains:

  logs/receipts/task-<N>/findings/<fingerprint>.json  canonical finding (tracked)
  logs/receipts/task-<N>/FINDINGS.md                  generated projection (tracked)

(reports stay in logs/working/, which is gitignored; the canonical findings
must survive in history, so they live under logs/receipts/)

Rules:
  - fingerprint = sha256(reviewer | file | category | normalised text)[:12];
  - status is `open` or `closed` — nothing in between. "partially" is open;
  - severity is fixed at first sight and never lowered while open;
  - a finding closes ONLY through an explicit closure verdict from the same
    reviewer in a later round:  report.closures[] = {fingerprint, verdict:
    closed|open, evidence}. A later report that simply omits the finding does
    not close it (re-review must search for what should have
    been removed, not re-read the artefact);
  - findings open for more than one round are listed separately (they tend to ride through rounds without a verdict).

Exit 0 = no open critical findings, 1 = open critical findings exist,
2 = usage / nothing to sync.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from taskflow import load_reports, now_iso, read_json, task_log_dir, task_receipts_dir, write_json  # noqa: E402

SEVERITY_RANK = {"critical": 0, "major": 1, "minor": 2}


def sync(reports_dir: Path, receipts_dir: Path | None = None) -> dict:
    """Ingest reviewer reports from reports_dir; maintain findings/ + FINDINGS.md in receipts_dir."""
    receipts_dir = receipts_dir or reports_dir
    reports = load_reports(reports_dir)
    findings_dir = receipts_dir / "findings"
    existing: dict[str, dict] = {}
    if findings_dir.is_dir():
        for p in findings_dir.glob("*.json"):
            data = read_json(p)
            if data and data.get("fingerprint"):
                existing[data["fingerprint"]] = data

    latest_round: dict[str, int] = {}
    for r in reports:
        latest_round[r.reviewer] = max(latest_round.get(r.reviewer, 0), r.round)

    # 1. upsert findings from every report, in round order
    for r in reports:
        for f in r.findings:
            fp = f["fingerprint"]
            cur = existing.get(fp)
            if cur is None:
                existing[fp] = {
                    **f, "status": "open", "first_round": r.round, "last_round": r.round,
                    "closed_by": None, "first_seen": now_iso(), "source": r.path.name,
                }
            else:
                cur["last_round"] = max(cur["last_round"], r.round)
                # severity never drops while open; it may rise
                if SEVERITY_RANK.get(f["severity"], 9) < SEVERITY_RANK.get(cur["severity"], 9):
                    cur["severity"] = f["severity"]
                if cur["status"] == "closed" and r.round > (cur["closed_by"] or {}).get("round", 0):
                    # reported again after closure → it is open again
                    cur["status"] = "open"
                    cur["reopened_in_round"] = r.round
                    cur["closed_by"] = None

    # 2. apply explicit closures (same reviewer, later round)
    for r in reports:
        for c in r.closures:
            fp = str(c.get("fingerprint") or "")
            cur = existing.get(fp)
            if cur is None or cur["reviewer"] != r.reviewer or r.round <= cur["first_round"]:
                continue
            verdict = str(c.get("verdict") or "").strip().lower()
            if verdict == "closed":
                cur["status"] = "closed"
                cur["closed_by"] = {"round": r.round, "evidence": c.get("evidence") or "", "report": r.path.name}
            else:
                cur["status"] = "open"           # "open", "partially", anything else
                cur["closed_by"] = None
                cur["still_open_note"] = c.get("evidence") or c.get("note") or ""

    for fp, f in existing.items():
        f["updated_at"] = now_iso()
        write_json(findings_dir / f"{fp}.json", f)

    open_items = [f for f in existing.values() if f["status"] == "open"]
    stale = [f for f in open_items
             if latest_round.get(f["reviewer"], f["first_round"]) > f["first_round"]]
    open_critical = [f for f in open_items if f["severity"] == "critical"]

    receipts_dir.mkdir(parents=True, exist_ok=True)
    (receipts_dir / "FINDINGS.md").write_text(render(existing, stale, latest_round), encoding="utf-8")
    return {
        "reports": len(reports), "findings": len(existing), "open": len(open_items),
        "open_critical": len(open_critical), "stale_open": len(stale),
        "latest_round": latest_round,
    }


def render(findings: dict[str, dict], stale: list[dict], latest_round: dict[str, int]) -> str:
    def row(f: dict) -> str:
        loc = f"{f['file']}:{f['line']}" if f.get("line") else f.get("file") or "—"
        closed = f"r{f['closed_by']['round']}" if f.get("closed_by") else ""
        return (f"| `{f['fingerprint']}` | {f['severity']} | {f['status']} {closed} | {f['reviewer']} "
                f"| r{f['first_round']} | {loc} | {f['text'][:120]} |")

    ordered = sorted(findings.values(),
                     key=lambda f: (f["status"] != "open", SEVERITY_RANK.get(f["severity"], 9), f["first_round"]))
    lines = ["# Findings — generated by findings-sync, do not edit", "",
             f"Rounds seen: {', '.join(f'{k} r{v}' for k, v in sorted(latest_round.items())) or 'none'}", ""]
    if stale:
        lines += ["## ⚠️ Open for more than one round", "",
                  "Severity is fixed until the finding's question is answered. These have been carried",
                  "through at least one fix round without an explicit `closed` verdict.", ""]
        lines += [f"- `{f['fingerprint']}` **{f['severity']}** ({f['reviewer']}, since r{f['first_round']}): {f['text'][:160]}"
                  for f in stale]
        lines.append("")
    lines += ["## All findings", "",
              "| fp | severity | status | reviewer | first | where | summary |",
              "|---|---|---|---|---|---|---|"]
    lines += [row(f) for f in ordered]
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("feature_dir", type=Path)
    ap.add_argument("task")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    reports_dir = task_log_dir(args.feature_dir, args.task)
    receipts_dir = task_receipts_dir(args.feature_dir, args.task)
    if not reports_dir.is_dir():
        print(f"findings-sync: no reports dir {reports_dir}", file=sys.stderr)
        return 2
    result = sync(reports_dir, receipts_dir)
    if result["reports"] == 0:
        print(f"findings-sync: no reviewer reports in {reports_dir}", file=sys.stderr)
        return 2
    if not args.quiet:
        print(f"findings-sync: task {args.task} — {result['reports']} reports, {result['findings']} findings, "
              f"{result['open']} open ({result['open_critical']} critical), {result['stale_open']} open >1 round")
        print(f"  → {receipts_dir / 'FINDINGS.md'}")
    return 1 if result["open_critical"] else 0


if __name__ == "__main__":
    sys.exit(main())
