"""Unit tests for the task-level receipts toolchain.

Run:  python3 -m unittest discover -s .claude/scripts/tests -t .claude/scripts/tests
"""
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import taskflow  # noqa: E402


def load_script(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


wave_check = load_script("wave-check")
findings_sync = load_script("findings-sync")
task_accept = load_script("task-accept")
owns_check = load_script("owns-check")


def task_text(num: str, wave: int, owns=(), reads=(), deps=(), status="planned", body="## Description\nx\n"):
    fm = [f"status: {status}", f"depends_on: [{', '.join(deps)}]", f"wave: {wave}",
          f"owns_paths: [{', '.join(owns)}]", f"reads: [{', '.join(reads)}]"]
    return "---\n" + "\n".join(fm) + "\n---\n" + f"# Task {num}\n\n" + body


class FrontmatterAndHash(unittest.TestCase):
    def test_body_hash_ignores_frontmatter_changes(self):
        a = taskflow.split_frontmatter(task_text("1", 1, status="planned"))
        b = taskflow.split_frontmatter(task_text("1", 1, status="done"))
        self.assertNotEqual(a[0]["status"], b[0]["status"])
        self.assertEqual(a[1], b[1])

    def test_body_hash_changes_when_body_changes(self):
        t1 = taskflow.Task("1", Path("x"), {}, "body A")
        t2 = taskflow.Task("1", Path("x"), {}, "body B")
        self.assertNotEqual(t1.body_sha256, t2.body_sha256)

    def test_inline_comments_are_tolerated(self):
        fm, _ = taskflow.split_frontmatter("---\nwave: 2   # волна\nowns_paths: [a/b.py]\n---\nbody")
        self.assertEqual(fm["wave"], 2)
        self.assertEqual(fm["owns_paths"], ["a/b.py"])


class PathOwnership(unittest.TestCase):
    def test_prefix_overlap(self):
        self.assertTrue(taskflow.paths_overlap("src/api", "src/api/users.ts"))
        self.assertTrue(taskflow.paths_overlap("src/api/users.ts", "src/api"))
        self.assertFalse(taskflow.paths_overlap("src/api", "src/apiary/x.ts"))
        self.assertFalse(taskflow.paths_overlap("src/a.ts", "src/b.ts"))

    def test_glob_patterns(self):
        self.assertTrue(taskflow.path_matches(".env.local", ".env*"))
        self.assertTrue(taskflow.path_matches("projects/x/data/state.json", "**/data/**"))
        self.assertTrue(taskflow.path_matches("data/state.json", "**/data/**"))
        self.assertTrue(taskflow.path_matches("src/a/b.ts", "src/**"))
        self.assertFalse(taskflow.path_matches("srcx/a.ts", "src/**"))

    def test_owns_check_classification(self):
        buckets = owns_check.classify(
            files=["src/a.py", "src/b.py", "work/f/decisions.md", ".env", "other/c.py"],
            owns=["src/a.py"], never=[".env*"], feature_rel="work/f")
        self.assertEqual(buckets["inside"], ["src/a.py"])
        self.assertEqual(buckets["ignored"], ["work/f/decisions.md"])
        self.assertEqual(buckets["forbidden"], [".env"])
        self.assertEqual(buckets["leaks"], ["src/b.py", "other/c.py"])


class WaveCheck(unittest.TestCase):
    def _tasks(self, *specs):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "tasks").mkdir()
            for num, kw in specs:
                (Path(d) / "tasks" / f"{num}.md").write_text(task_text(num, **kw), encoding="utf-8")
            return wave_check.check(taskflow.load_tasks(Path(d)))

    def test_clean_wave(self):
        r = self._tasks(("1", dict(wave=1, owns=["src/a.py"])), ("2", dict(wave=1, owns=["src/b.py"])))
        self.assertTrue(r["ok"])

    def test_write_write_collision(self):
        r = self._tasks(("1", dict(wave=1, owns=["src/api"])), ("2", dict(wave=1, owns=["src/api/x.py"])))
        self.assertFalse(r["ok"])
        self.assertEqual(r["violations"][0]["kind"], "write/write")

    def test_read_write_dependency_in_same_wave(self):
        # task 2 reads what task 1 creates, both in wave 1
        r = self._tasks(("1", dict(wave=1, owns=["src/db.py"])),
                        ("2", dict(wave=1, owns=["src/plan.py"], reads=["src/db.py"])))
        self.assertFalse(r["ok"])
        self.assertEqual(r["violations"][0]["kind"], "read/write")

    def test_read_write_ok_across_waves(self):
        r = self._tasks(("1", dict(wave=1, owns=["src/db.py"])),
                        ("2", dict(wave=2, owns=["src/plan.py"], reads=["src/db.py"], deps=["1"])))
        self.assertTrue(r["ok"])

    def test_depends_on_must_be_earlier_wave(self):
        r = self._tasks(("1", dict(wave=1, owns=["a"])), ("2", dict(wave=1, owns=["b"], deps=["1"])))
        self.assertFalse(r["ok"])
        self.assertEqual(r["violations"][0]["kind"], "depends_on")

    def test_no_owns_paths_is_skipped_not_failed(self):
        r = self._tasks(("1", dict(wave=1)), ("2", dict(wave=1)))
        self.assertTrue(r["ok"])
        self.assertEqual(r["skipped_no_owns_paths"], ["1", "2"])


class ReportNormalisation(unittest.TestCase):
    def test_status_vocabulary(self):
        self.assertEqual(taskflow.normalise_status("approve"), "approved")
        self.assertEqual(taskflow.normalise_status("approved_with_suggestions"), "approved_with_suggestions")
        self.assertEqual(taskflow.normalise_status("changes_required"), "changes_required")
        self.assertEqual(taskflow.normalise_status("REJECT"), "changes_required")
        self.assertEqual(taskflow.normalise_status("PASS"), "approved")
        self.assertEqual(taskflow.normalise_status(None), "unknown")

    def test_triaged_is_its_own_status(self):
        # build-route шаг 6: лид закрывает находки отчётом round 2 со status "triaged".
        self.assertEqual(taskflow.normalise_status("triaged"), "triaged")
        self.assertEqual(taskflow.normalise_status("Triaged"), "triaged")


class ReviewReasons(unittest.TestCase):
    @staticmethod
    def _rv(status):
        return [{"reviewer": "quick", "round": 2, "status": status, "report": "quick-2.json"}]

    def test_triaged_accepts_only_without_open_findings(self):
        self.assertEqual(task_accept.review_reasons(self._rv("triaged"), {"open": 0}), [])
        reasons = task_accept.review_reasons(self._rv("triaged"), {"open": 1})
        self.assertEqual(len(reasons), 1)
        self.assertIn("1 open", reasons[0])

    def test_other_statuses_unchanged(self):
        self.assertEqual(task_accept.review_reasons(self._rv("approved"), {"open": 3}), [])
        self.assertIn("changes_required", task_accept.review_reasons(self._rv("changes_required"), {"open": 0})[0])
        self.assertIn("unreadable", task_accept.review_reasons(self._rv("unknown"), {"open": 0})[0])

    def test_report_filename_variants(self):
        for name in ("code-reviewer-1.json", "code-reviewer-round2.json", "security-auditor-round1-groupC.json"):
            self.assertIsNotNone(taskflow.REPORT_NAME_RE.match(name), name)
        self.assertIsNone(taskflow.REPORT_NAME_RE.match("acceptance.json"))
        self.assertIsNone(taskflow.REPORT_NAME_RE.match("owns-check.json"))

    def test_both_report_shapes_yield_findings(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "code-reviewer-1.json"
            p.write_text(json.dumps({"status": "changes_required",
                                     "criticalIssues": [{"file": "a.py", "line": 3, "category": "security", "issue": "SQL injection"}],
                                     "suggestions": [{"file": "a.py", "suggestion": "rename", "optional": True}]}))
            r = taskflow.parse_report(p)
            self.assertEqual(r.status, "changes_required")
            self.assertEqual({f["severity"] for f in r.findings}, {"critical", "minor"})
            q = Path(d) / "test-reviewer-round1.json"
            q.write_text(json.dumps({"verdict": "approve", "findings": [{"severity": "major", "summary": "flaky"}]}))
            r2 = taskflow.parse_report(q)
            self.assertEqual((r2.reviewer, r2.round, r2.status), ("test-reviewer", 1, "approved"))
            self.assertEqual(r2.findings[0]["severity"], "major")


class FindingsLifecycle(unittest.TestCase):
    def _write(self, d: Path, name: str, data: dict):
        (d / name).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def test_omission_does_not_close_partially_is_open_closed_needs_verdict(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            crit = {"file": "a.py", "category": "security", "issue": "no timeout on HTTP call"}
            self._write(d, "code-reviewer-1.json", {"status": "changes_required", "criticalIssues": [crit]})
            s1 = findings_sync.sync(d)
            self.assertEqual((s1["open"], s1["open_critical"]), (1, 1))
            fp = next(iter((d / "findings").glob("*.json"))).stem

            # round 2 silently omits the finding → still open, and now stale
            self._write(d, "code-reviewer-2.json", {"status": "approved", "criticalIssues": []})
            s2 = findings_sync.sync(d)
            self.assertEqual((s2["open"], s2["stale_open"]), (1, 1))

            # round 3 says "partially" → still open
            self._write(d, "code-reviewer-3.json", {"status": "approved", "criticalIssues": [],
                                                    "closures": [{"fingerprint": fp, "verdict": "partially"}]})
            self.assertEqual(findings_sync.sync(d)["open"], 1)

            # round 4 explicit closed with evidence → closed
            self._write(d, "code-reviewer-4.json", {"status": "approved", "criticalIssues": [],
                                                    "closures": [{"fingerprint": fp, "verdict": "closed",
                                                                  "evidence": "timeout=30 at a.py:12"}]})
            s4 = findings_sync.sync(d)
            self.assertEqual(s4["open"], 0)
            data = json.loads((d / "findings" / f"{fp}.json").read_text())
            self.assertEqual(data["status"], "closed")
            self.assertEqual(data["closed_by"]["round"], 4)
            self.assertIn("Open for more than one round", (d / "FINDINGS.md").read_text()) if s4["stale_open"] else None

    def test_other_reviewer_cannot_close(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            self._write(d, "security-auditor-1.json", {"status": "changes_required",
                                                       "findings": [{"severity": "critical", "summary": "secret in log"}]})
            findings_sync.sync(d)
            fp = next(iter((d / "findings").glob("*.json"))).stem
            self._write(d, "code-reviewer-2.json", {"status": "approved", "criticalIssues": [],
                                                    "closures": [{"fingerprint": fp, "verdict": "closed"}]})
            self.assertEqual(findings_sync.sync(d)["open_critical"], 1)

    def test_severity_never_drops_while_open(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            f = {"file": "a.py", "category": "x", "summary": "same question"}
            self._write(d, "code-reviewer-1.json", {"status": "changes_required", "findings": [{**f, "severity": "critical"}]})
            self._write(d, "code-reviewer-2.json", {"status": "changes_required", "findings": [{**f, "severity": "minor"}]})
            findings_sync.sync(d)
            data = json.loads(next(iter((d / "findings").glob("*.json"))).read_text())
            self.assertEqual(data["severity"], "critical")


class VerificationParsing(unittest.TestCase):
    def test_extracts_commands_and_expected_exit(self):
        body = ("## Verification Steps\n\n### Automated\n"
                "- `pytest tests/ -v` → all pass\n"
                "- `grep -q foo bar.txt` → exit 1 (marker must be absent)\n"
                "### Smoke\n- `curl -s localhost:3000/health` → 200\n"
                "### User\n- `something manual`\n## Details\n- `not a check`\n")
        t = taskflow.Task("1", Path("x"), {}, body)
        cmds = task_accept.verification_commands(t)
        self.assertEqual([c["command"] for c in cmds],
                         ["pytest tests/ -v", "grep -q foo bar.txt", "curl -s localhost:3000/health"])
        self.assertEqual([c["expected_exit"] for c in cmds], [0, 1, 0])
        self.assertEqual([c["kind"] for c in cmds], ["automated", "automated", "smoke"])

    def test_run_commands_records_exit_codes(self):
        res = task_accept.run_commands([{"command": "true", "expected": "", "expected_exit": 0, "kind": "smoke"},
                                        {"command": "false", "expected": "", "expected_exit": 0, "kind": "smoke"}],
                                       Path("/"), timeout=10)
        self.assertEqual([r["ok"] for r in res], [True, False])


if __name__ == "__main__":
    unittest.main()


class TaskCommitsAttribution(unittest.TestCase):
    """Shared checkout: only `task N` commits count, untracked optional."""

    def _repo(self):
        import tempfile, subprocess
        d = Path(tempfile.mkdtemp())
        run = lambda *a: subprocess.run(["git", "-C", str(d), *a], check=True, capture_output=True, text=True)
        run("init", "-q"); run("config", "user.email", "t@t"); run("config", "user.name", "t")
        (d / "base.txt").write_text("0"); run("add", "."); run("commit", "-qm", "base")
        start = run("rev-parse", "HEAD").stdout.strip()
        (d / "mine.py").write_text("1"); run("add", "."); run("commit", "-qm", "feat: task 7 — mine")
        (d / "theirs.py").write_text("1"); run("add", "."); run("commit", "-qm", "other-lane: unrelated")
        (d / "mine2.py").write_text("1"); run("add", "."); run("commit", "-qm", "fix: address review round 1 for task 7")
        (d / "lead.txt").write_text("1"); run("add", "."); run("commit", "-qm", "chore(tasks): task 7 owns lead.txt")
        (d / "draft.md").write_text("x")  # untracked, someone else's
        return d, start

    def test_scoped_lead_commit_not_attributed(self):
        d, start = self._repo()
        self.assertNotIn("lead.txt", taskflow.changed_files(d, start, task_number=7, ignore_untracked=True))

    def test_only_tagged_commits_count(self):
        d, start = self._repo()
        files = taskflow.changed_files(d, start, task_number=7, ignore_untracked=True)
        self.assertEqual(files, ["mine.py", "mine2.py"])

    def test_task_70_does_not_match_task_7(self):
        d, start = self._repo()
        self.assertEqual(taskflow.changed_files(d, start, task_number=70, ignore_untracked=True), [])

    def test_untracked_counted_unless_ignored(self):
        d, start = self._repo()
        self.assertIn("draft.md", taskflow.changed_files(d, start, task_number=7))

    def test_without_task_number_full_range(self):
        d, start = self._repo()
        self.assertIn("theirs.py", taskflow.changed_files(d, start, ignore_untracked=True))

    def test_non_ascii_paths_are_not_quoted(self):
        """core.quotepath=true (дефолт git) печатает кириллицу как "\\320\\230…" — owns-check
        видел такой путь как утечку."""
        import subprocess
        d, start = self._repo()
        run = lambda *a: subprocess.run(["git", "-C", str(d), *a], check=True, capture_output=True, text=True)
        run("config", "core.quotepath", "true")
        (d / "Инструкция.md").write_text("1", encoding="utf-8")
        run("add", "."); run("commit", "-qm", "docs: task 7 — кириллица")
        files = taskflow.changed_files(d, start, task_number=7, ignore_untracked=True)
        self.assertIn("Инструкция.md", files)
        self.assertFalse(any(f.startswith('"') for f in files), files)
