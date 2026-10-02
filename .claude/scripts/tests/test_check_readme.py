#!/usr/bin/env python3
"""Тесты check-readme.py: полный README проходит, неполный падает, ложно-зелёные случаи ловятся.

Запуск: python3 .claude/scripts/tests/test_check_readme.py
"""
from __future__ import annotations

import importlib.util
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "check-readme.py"
spec = importlib.util.spec_from_file_location("check_readme", SCRIPT)
cr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cr)

FULL = """# demo-worker — демо-обработчик

Агент берёт сделку и отправляет клиенту сообщение.

## Поток данных
1. вебхук → 2. очередь → 3. отправка

## Почему так
Очередь, а не прямой вызов: переживает рестарт.

## Что трогает снаружи
Поле CRM custom_field_x, канал мессенджера, токен сервисной учётки.

## Инварианты
Повтор вебхука не создаёт второе сообщение.

## Запуск и деплой
pm2 restart demo-worker

## Как понять, что сломалось
Пуш в монитор аптайма молчит больше 10 минут.
"""


def run(argv):
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = cr.main(argv)
    return code, buf.getvalue()


class CheckReadmeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, text: str) -> str:
        p = self.dir / "README.md"
        p.write_text(text, encoding="utf-8")
        return str(p)

    def test_full_readme_passes(self):
        code, out = run([self.write(FULL)])
        self.assertEqual(code, 0, out)
        self.assertIn("1 из 1", out)

    def test_each_missing_section_fails(self):
        for heading in ["## Поток данных", "## Почему так", "## Что трогает снаружи",
                        "## Инварианты", "## Запуск и деплой", "## Как понять, что сломалось"]:
            with self.subTest(heading=heading):
                code, out = run([self.write(FULL.replace(heading, "## Прочее"))])
                self.assertEqual(code, 1, out)

    def test_missing_intro_fails(self):
        text = FULL.replace("Агент берёт сделку и отправляет клиенту сообщение.\n", "")
        code, out = run([self.write(text)])
        self.assertEqual(code, 1)
        self.assertIn("вступительного абзаца", out)

    def test_heading_inside_code_fence_does_not_count(self):
        text = FULL.replace("## Инварианты\n", "```\n## Инварианты\n```\n")
        code, out = run([self.write(text)])
        self.assertEqual(code, 1, out)
        self.assertIn("инварианты", out)

    def test_skip_marker_is_reported_not_silent(self):
        code, out = run([self.write("# Индекс\n<!-- readme-check: skip — индекс агентов -->\n")])
        self.assertEqual(code, 0)
        self.assertIn("пропущен по пометке (индекс агентов)", out)
        self.assertIn("проверено 0", out)

    def test_long_readme_warns_without_failing(self):
        code, out = run([self.write(FULL + "строка\n" * 900)])
        self.assertEqual(code, 0, out)
        self.assertIn("> 800", out)

    def test_missing_file_is_usage_error(self):
        code, _ = run([str(self.dir / "nope.md")])
        self.assertEqual(code, 2)

    def test_project_readme_paths(self):
        self.assertTrue(cr.is_project_readme("projects/X/README.md"))
        self.assertTrue(cr.is_project_readme("projects/Аналитика продаж/README.md"))
        self.assertFalse(cr.is_project_readme("projects/group/sub/README.md"))
        self.assertFalse(cr.is_project_readme("projects/X/docs/README.md"))
        self.assertFalse(cr.is_project_readme("sandbox/README.md"))


if __name__ == "__main__":
    unittest.main(verbosity=1)
