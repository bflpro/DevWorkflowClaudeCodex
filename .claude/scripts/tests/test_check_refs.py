#!/usr/bin/env python3
"""Тесты check-refs.py: резолв в проект — тихо, только в ~/.claude — WARN, нигде — ERROR,
done-карточки пропускаются, сломанный frontmatter — ERROR, пустой корень — код 2.

Запуск: python3 .claude/scripts/tests/test_check_refs.py
"""
from __future__ import annotations

import importlib.util
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "check-refs.py"
spec = importlib.util.spec_from_file_location("check_refs", SCRIPT)
cr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cr)


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class Fixture:
    def __init__(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "repo"
        self.personal = Path(self.tmp.name) / "home-claude"
        write(self.root / ".claude/skills/code-writing/SKILL.md", "# cw\n")
        write(self.root / ".claude/agents/code-reviewer.md", "---\nname: code-reviewer\nskills:\n  - code-writing\n---\nbody\n")
        write(self.root / ".claude/commands/build.md", "# build\n")
        write(self.root / ".claude/shared/review-lenses/quick.md", "lens\n")
        write(self.personal / "skills/only-personal/SKILL.md", "# personal\n")

    def card(self, name: str, status: str, skills: str, reviewers: str) -> None:
        write(self.root / f"work/f/tasks/{name}.md",
              f"---\nstatus: {status}\nskills: {skills}\nreviewers: {reviewers}\n---\n# Task\n")


class CheckRefsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fx = Fixture()
        self.addCleanup(self.fx.tmp.cleanup)

    def run_check(self, include_done: bool = False):
        return cr.check(self.fx.root, self.fx.personal, include_done)

    def test_clean_repo_has_no_findings(self) -> None:
        self.fx.card("1", "planned", "[code-writing]", "[quick]")
        write(self.fx.root / "CLAUDE.md", "команда `/build` и встроенная `/clear`\n")
        errors, warnings, scanned = self.run_check()
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])
        self.assertEqual(scanned, 3)  # агент + карточка + CLAUDE.md

    def test_missing_skill_in_card_is_error(self) -> None:
        self.fx.card("1", "planned", "[no-such-skill]", "[thorough]")
        errors, _, _ = self.run_check()
        self.assertEqual(len(errors), 1)
        self.assertIn("no-such-skill", errors[0])

    def test_personal_only_skill_is_warning(self) -> None:
        self.fx.card("1", "in_progress", "[only-personal]", "[none]")
        errors, warnings, _ = self.run_check()
        self.assertEqual(errors, [])
        self.assertEqual(len(warnings), 1)
        self.assertIn("только в ~/.claude", warnings[0])

    def test_personal_only_is_error_without_personal_dir(self) -> None:
        self.fx.card("1", "planned", "[only-personal]", "[none]")
        errors, warnings, _ = cr.check(self.fx.root, None)
        self.assertEqual(len(errors), 1)
        self.assertEqual(warnings, [])

    def test_done_cards_are_skipped_unless_asked(self) -> None:
        self.fx.card("1", "done", "[gone-skill]", "[gone-agent]")
        errors, _, _ = self.run_check()
        self.assertEqual(errors, [])
        errors, _, _ = self.run_check(include_done=True)
        self.assertEqual(len(errors), 2)

    def test_reviewer_resolves_to_set_lens_or_legacy_agent(self) -> None:
        self.fx.card("1", "planned", "[]", "[thorough, quick, code-reviewer, none]")
        errors, _, _ = self.run_check()
        self.assertEqual(errors, [])
        self.fx.card("2", "planned", "[]", "none")  # голый скаляр — резолвится как набор
        errors, _, _ = self.run_check()
        self.assertEqual(errors, [])

    def test_agent_with_missing_skill_is_error(self) -> None:
        write(self.fx.root / ".claude/agents/lonely.md", "---\nname: lonely\nskills: [vanished]\n---\n")
        errors, _, _ = self.run_check()
        self.assertEqual(len(errors), 1)
        self.assertIn("vanished", errors[0])

    def test_broken_frontmatter_is_error_not_silence(self) -> None:
        write(self.fx.root / "work/f/tasks/9.md", "---\nstatus: planned\nskills: [unclosed\n---\n")
        errors, _, scanned = self.run_check()
        self.assertTrue(any("frontmatter" in e for e in errors))
        self.assertGreaterEqual(scanned, 2)

    def test_claude_md_command_missing_is_error(self) -> None:
        write(self.fx.root / "CLAUDE.md", "`/build` ok, `/vanished-cmd` нет, `/compact` встроенная\n")
        errors, _, _ = self.run_check()
        self.assertEqual(len(errors), 1)
        self.assertIn("/vanished-cmd", errors[0])

    def test_empty_root_exits_2(self) -> None:
        empty = Path(self.fx.tmp.name) / "empty"
        empty.mkdir()
        out = io.StringIO()
        with redirect_stdout(out):
            code = cr.main(["--root", str(empty), "--no-personal"])
        self.assertEqual(code, 2)
        self.assertIn("NOT CHECKED", out.getvalue())

    def test_main_exit_codes(self) -> None:
        self.fx.card("1", "planned", "[code-writing]", "[quick]")
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(cr.main(["--root", str(self.fx.root), "--no-personal"]), 0)
        self.fx.card("2", "planned", "[missing]", "[quick]")
        with redirect_stdout(out):
            self.assertEqual(cr.main(["--root", str(self.fx.root), "--no-personal"]), 1)


if __name__ == "__main__":
    unittest.main(verbosity=1)
