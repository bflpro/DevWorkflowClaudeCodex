#!/usr/bin/env python3
"""Behavioral tests using temporary task receipts; no provider/session access."""

import copy
import fcntl
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))


def module(name):
    spec = importlib.util.spec_from_file_location(
        name.replace("-", "_"), SCRIPTS / f"{name}.py"
    )
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


metrics = module("workflow-metrics")
route = module("workflow-route")
accept = module("task-accept")
POLICY = json.loads(metrics.POLICY.read_text())


class MetricsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.feature = self.root / "work/example"
        self.now = datetime(2026, 10, 30, tzinfo=timezone.utc)
        self.policy = copy.deepcopy(POLICY)
        self.receipt = {
            "task_sha256": "a" * 64,
            "accepted": True,
            "generated_at": self.now.isoformat(),
            "reviews": [{"reviewer": "quick", "round": 2}],
        }
        self.put(
            self.root / ".claude/shared/workflow-resources/policy.json", self.policy
        )

    def put(self, path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data))

    def collect(self, task="1", receipt=None, now=None):
        return metrics.collect(
            self.feature,
            task,
            receipt or self.receipt,
            root=self.root,
            policy=self.policy,
            now=now or self.now,
        )

    def state(self):
        return json.loads(
            (self.root / ".claude/state/workflow-metrics/state.json").read_text()
        )

    def add_run(self, name="1", **extra):
        data = {
            "role": "code-reviewer",
            "runtime": "codex",
            "mode": "delegated",
            "requested": {"model": "gpt-6.1-terra", "effort": "medium"},
            "actual": {"model": "gpt-6.1-terra", "effort": "medium"},
            "usage": {
                "input_uncached": 5,
                "cache_read": 100,
                "cache_write": 20,
                "output": 3,
            },
        }
        data.update(extra)
        path = self.feature / f"logs/working/task-1/evidence-workflow-run-{name}.json"
        self.put(path, data)
        return path

    def test_idempotent_collection_and_counter_refresh(self):
        path = self.add_run()
        self.collect()
        self.collect()
        row = next(iter(self.state()["records"].values()))
        self.assertEqual(row["attempts"], 1)
        self.assertEqual(len(row["runs"]), 1)
        self.assertEqual(row["runs"][0]["usage"]["cache_read"], 100)
        data = json.loads(path.read_text())
        data["usage"]["cache_read"] = 200
        self.put(path, data)
        self.collect()
        row = next(iter(self.state()["records"].values()))
        self.assertEqual(row["runs"][0]["usage"]["cache_read"], 200)

    def test_failed_then_accepted_counts_one_contract_and_two_attempts(self):
        self.collect(receipt={**self.receipt, "accepted": False})
        self.collect()
        row = next(iter(self.state()["records"].values()))
        self.assertTrue(row["accepted"])
        self.assertEqual(row["attempts"], 2)
        self.assertEqual(len(self.state()["records"]), 1)

    def test_missing_usage_model_and_elapsed_stay_unknown(self):
        self.add_run(actual={}, usage={})
        self.collect()
        row = next(iter(self.state()["records"].values()))
        self.assertIsNone(row["runs"][0]["usage"]["cache_read"])
        text = metrics.report_text(self.state()["records"], self.now)
        self.assertIn("cache_read | unknown", text)
        self.assertIn("codex / unknown / unknown", text)
        self.assertIn("elapsed_seconds: unknown", text)

    def test_allowlist_drops_raw_customer_text_and_invalid_counters(self):
        self.add_run(
            prompt="PRIVATE_CUSTOMER_TEXT",
            token="SECRET_TOKEN",
            actual={"model": "SECRET_TOKEN", "effort": "PRIVATE_CUSTOMER_TEXT"},
            usage={
                "input_uncached": True,
                "cache_read": -1,
                "cache_write": 1.5,
                "output": float("nan"),
            },
        )
        self.put(
            self.feature / "logs/receipts/task-1/findings/a.json",
            {
                "status": "closed",
                "text": "PRIVATE_CUSTOMER_TEXT",
                "closed_by": {"evidence": "patch SECRET_TOKEN"},
            },
        )
        self.collect()
        text = json.dumps(self.state()) + metrics.report_text(
            self.state()["records"], self.now
        )
        self.assertNotIn("PRIVATE_CUSTOMER_TEXT", text)
        self.assertNotIn("SECRET_TOKEN", text)
        row = next(iter(self.state()["records"].values()))
        self.assertEqual(set(row["runs"][0]["usage"].values()), {None})

    def test_corrupt_oversized_and_symlink_evidence_is_visible(self):
        path = self.add_run()
        path.write_text("{broken")
        self.add_run("2").write_text("x" * (1048576 + 1))
        target = self.root / "private.json"
        self.put(target, {"prompt": "SECRET"})
        (path.parent / "evidence-workflow-run-3.json").symlink_to(target)
        self.assertEqual(self.collect()["input_errors"], 3)

    def test_closed_does_not_imply_patch_and_legacy_mixed_is_unknown(self):
        self.assertEqual(metrics.finding_route({"status": "closed"}), "unknown")
        self.assertEqual(
            metrics.finding_route({"closed_by": {"evidence": "false → defer"}}),
            "unknown",
        )
        self.assertEqual(
            metrics.finding_route({"triage": {"route": "duplicate"}}), "duplicate"
        )

    def test_count_cadence_counts_new_accepted_contracts_only(self):
        self.policy["collection"]["report_every_tasks"] = 2
        self.assertFalse(self.collect()["report_updated"])
        self.assertFalse(self.collect()["report_updated"])
        self.assertFalse(
            self.collect("2", {**self.receipt, "accepted": False})["report_updated"]
        )
        self.assertTrue(self.collect("2")["report_updated"])
        self.assertFalse(self.collect("2")["report_updated"])
        self.assertTrue(
            (self.root / ".claude/state/workflow-metrics/report.md").exists()
        )

    def test_week_cadence_requires_new_accepted_data(self):
        self.collect()
        later = self.now + timedelta(days=7)
        self.assertTrue(self.collect(now=later)["report_updated"])
        self.assertFalse(self.collect(now=later + timedelta(days=7))["report_updated"])

    def test_explicit_report_saves_snapshot_without_resetting_periodic_cadence(self):
        self.collect()
        before = self.state()["last_report"]
        with redirect_stdout(io.StringIO()):
            self.assertEqual(metrics.main(["report", "--root", str(self.root)]), 0)
        self.assertTrue(
            (self.root / ".claude/state/workflow-metrics/report.md").exists()
        )
        self.assertEqual(self.state()["last_report"], before)

    def test_retention_run_and_task_bounds(self):
        self.policy["collection"].update(
            max_tasks=2, max_runs_per_task=1, retention_days=2
        )
        self.add_run("1")
        self.add_run("2")
        self.collect()
        self.assertTrue(next(iter(self.state()["records"].values()))["runs_truncated"])
        self.collect("2")
        self.collect("3")
        self.assertEqual(len(self.state()["records"]), 2)
        self.collect("4", now=self.now + timedelta(days=3))
        self.assertEqual(len(self.state()["records"]), 1)

    def test_removed_working_evidence_does_not_erase_observed_history(self):
        path = self.add_run()
        self.collect()
        path.unlink()
        self.collect()
        self.assertEqual(len(next(iter(self.state()["records"].values()))["runs"]), 1)

    def test_lock_contention_is_nonblocking_and_corruption_is_not_reset(self):
        self.collect()
        directory = self.root / ".claude/state/workflow-metrics"
        with (directory / "lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaises(BlockingIOError):
                self.collect()
        path = directory / "state.json"
        path.write_text("{broken")
        with self.assertRaises(ValueError):
            self.collect()
        self.assertEqual(path.read_text(), "{broken")

    def test_state_directory_cannot_redirect_writes_outside_repo(self):
        outside = self.root / "outside"
        outside.mkdir()
        parent = self.root / ".claude"
        parent.mkdir(exist_ok=True)
        (parent / "state").symlink_to(outside)
        # root-relative outside directory is allowed; an actually external target is not.
        with tempfile.TemporaryDirectory() as external:
            (parent / "state").unlink()
            (parent / "state").symlink_to(external)
            with self.assertRaises(ValueError):
                self.collect()
            self.assertEqual(list(Path(external).iterdir()), [])

    def test_real_acceptance_entrypoint_collects_and_telemetry_failure_keeps_verdict(
        self,
    ):
        card = self.feature / "tasks/1.md"
        card.parent.mkdir(parents=True)
        card.write_text("---\nstart_commit: abcdef\n---\n# Test\n")
        self.put(
            self.feature / "logs/receipts/task-1/owns-check.json", {"result": "passed"}
        )
        original_loader = accept._load_module

        def load(name):
            if name == "owns-check":
                return SimpleNamespace(main=lambda args: 0)
            if name == "findings-sync":
                return SimpleNamespace(sync=lambda *a: {"open": 0, "open_critical": 0})
            return original_loader(name)

        with (
            patch.object(accept, "repo_root", return_value=self.root),
            patch.object(accept, "head_commit", return_value="abcdef"),
            patch.object(accept, "_load_module", side_effect=load),
            redirect_stdout(io.StringIO()),
            redirect_stderr(io.StringIO()),
        ):
            self.assertEqual(accept.main([str(self.feature), "1", "--quiet"]), 0)
            self.assertEqual(len(self.state()["records"]), 1)
            # Break telemetry; acceptance still reports rejection from a verification failure.
            (self.root / ".claude/state/workflow-metrics/state.json").write_text(
                "{broken"
            )
            card.write_text(
                card.read_text()
                + '\n## Verification Steps\n### Automated\n- `python3 -c "raise SystemExit(1)"` → exit 0\n'
            )
            self.assertEqual(accept.main([str(self.feature), "1", "--quiet"]), 1)
            result = json.loads(
                (self.feature / "logs/receipts/task-1/acceptance.json").read_text()
            )
            self.assertFalse(result["accepted"])
            card.write_text("---\nstart_commit: abcdef\n---\n# Test\n")
            self.assertEqual(accept.main([str(self.feature), "1", "--quiet"]), 0)


class RoutingTests(unittest.TestCase):
    def test_routine_critical_and_extraction_are_explicit_in_both_runtimes(self):
        self.assertEqual(
            route.resolve("task-validator", "codex")["requested"]["model"],
            "gpt-6.1-terra",
        )
        self.assertEqual(
            route.resolve("task-validator", "claude")["requested"]["model"], "sonnet"
        )
        escalated = route.resolve("code-reviewer", "codex", ["money"])
        self.assertEqual(escalated["agent_type"], "workflow-escalation")
        self.assertEqual(escalated["requested"]["model_reasoning_effort"], "high")
        self.assertEqual(
            route.resolve("workflow-extractor", "codex")["requested"]["model"],
            "gpt-6-luna",
        )

    def test_unknown_risks_roles_and_critical_extraction_fail(self):
        for role, risks in [
            ("not-a-role", []),
            ("code-reviewer", ["not-a-risk"]),
            ("extraction", ["security"]),
        ]:
            with self.assertRaises(ValueError):
                route.resolve(role, "codex", risks)

    def test_policy_covers_actual_claude_roles_and_frontmatter(self):
        import re

        for path in (SCRIPTS.parent / "agents").glob("*.md"):
            tier = POLICY["roles"][path.stem]
            model = re.search(r"^model: (.+)$", path.read_text(), re.MULTILINE).group(1)
            self.assertEqual(model, POLICY["tiers"][tier]["claude"]["model"], path.name)


if __name__ == "__main__":
    unittest.main()
