#!/usr/bin/env python3
"""Тесты receipts-stats.py: «с первого раза» считается строго, раунды — по максимуму,
ревьюер с незакрытым последним раундом учитывается, битая квитанция — ERROR и код 1,
пустой корень — код 2.

Запуск: python3 .claude/scripts/tests/test_receipts_stats.py
"""
from __future__ import annotations

import importlib.util
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "receipts-stats.py"
spec = importlib.util.spec_from_file_location("receipts_stats", SCRIPT)
rs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rs)


def receipt(root: Path, feature: str, task: str, accepted: bool, attempt: int, reviews: list, when: str = "2026-10-01") -> None:
    p = root / f"work/{feature}/logs/receipts/task-{task}/acceptance.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({
        "feature": feature, "task": task, "accepted": accepted, "attempt": attempt,
        "reviews": reviews, "accepted_at": f"{when}T10:00:00+00:00",
    }), encoding="utf-8")


R = lambda name, rnd, status: {"reviewer": name, "round": rnd, "status": status}  # noqa: E731


class ReceiptsStatsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_first_pass_requires_attempt_one_and_single_round(self) -> None:
        receipt(self.root, "a", "1", True, 1, [R("quick", 1, "approved")])
        receipt(self.root, "a", "2", True, 1, [R("quick", 1, "changes_required"), R("quick", 2, "triaged")])
        receipt(self.root, "a", "3", True, 2, [R("quick", 1, "approved")])
        receipt(self.root, "a", "4", False, 1, [R("quick", 1, "approved")])
        receipts, broken = rs.load_receipts(self.root)
        self.assertEqual(broken, [])
        s = rs.summarize(receipts)
        self.assertEqual(s["total"], 4)
        self.assertEqual(s["accepted"], 3)
        self.assertEqual(s["first_pass"], 1)
        self.assertEqual(s["rounds"], {1: 3, 2: 1})

    def test_reviewer_counted_once_per_receipt_by_last_round(self) -> None:
        receipt(self.root, "a", "1", True, 1, [R("blind-hunter", 1, "changes_required"), R("blind-hunter", 2, "triaged"),
                                               R("security", 1, "no_verdict")])
        receipts, _ = rs.load_receipts(self.root)
        s = rs.summarize(receipts)
        self.assertEqual(s["by_reviewer"]["blind-hunter"], {"seen": 1, "not_closed": 0})
        self.assertEqual(s["by_reviewer"]["security"], {"seen": 1, "not_closed": 1})

    def test_broken_receipt_is_reported_and_exit_1(self) -> None:
        receipt(self.root, "a", "1", True, 1, [])
        bad = self.root / "work/a/logs/receipts/task-2/acceptance.json"
        bad.parent.mkdir(parents=True)
        bad.write_text("{not json", encoding="utf-8")
        out = io.StringIO()
        with redirect_stdout(out):
            code = rs.main(["--root", str(self.root)])
        self.assertEqual(code, 1)
        self.assertIn("ERROR не прочиталась", out.getvalue())
        self.assertIn("квитанций: 1", out.getvalue())

    def test_since_filters_and_by_feature_prints_sections(self) -> None:
        receipt(self.root, "old", "1", True, 1, [], when="2026-09-01")
        receipt(self.root, "new", "1", True, 1, [], when="2026-10-05")
        out = io.StringIO()
        with redirect_stdout(out):
            code = rs.main(["--root", str(self.root), "--since", "2026-10-01", "--by-feature"])
        text = out.getvalue()
        self.assertEqual(code, 0)
        self.assertIn("## new", text)
        self.assertNotIn("## old", text)

    def test_no_receipts_exit_2(self) -> None:
        out = io.StringIO()
        with redirect_stdout(out):
            code = rs.main(["--root", str(self.root)])
        self.assertEqual(code, 2)
        self.assertIn("NOT CHECKED", out.getvalue())


if __name__ == "__main__":
    unittest.main(verbosity=1)
