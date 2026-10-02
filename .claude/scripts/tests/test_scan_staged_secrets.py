"""Tests for scan-staged-secrets.py against a real temporary git index.

Run:  python3 -m unittest discover -s .claude/scripts/tests -t .claude/scripts/tests

The scanner is run as a subprocess, the way the pre-commit hook runs it, so every test
exercises the real `git diff --cached` + `git show :<path>` path, not a helper in isolation.
"""
from __future__ import annotations

import os
import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scan-staged-secrets.py"

# Built by concatenation so this test file itself never matches the aws-key rule.
AWS_KEY = "AKIA" + "Z7" * 8
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def clean_env() -> dict[str, str]:
    # A test launched from inside a git hook inherits GIT_INDEX_FILE / GIT_DIR and would
    # read the outer repository's index instead of the temporary one.
    return {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}


class ScanStagedSecrets(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        subprocess.run(["git", "init", "-q"], cwd=self.repo, check=True, env=clean_env())

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def stage(self, name: str, data: bytes) -> None:
        path = self.repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        subprocess.run(["git", "add", "--", name], cwd=self.repo, check=True, env=clean_env())

    def scan(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, str(SCRIPT)], cwd=self.repo, capture_output=True,
                              text=True, timeout=60, check=False, env=clean_env())

    def assertNoCrash(self, res: subprocess.CompletedProcess[str]) -> None:
        self.assertNotIn("Traceback", res.stderr, res.stderr)
        self.assertNotIn("UnicodeDecodeError", res.stderr, res.stderr)

    def png_bytes(self, payload: bytes = b"") -> bytes:
        rnd = random.Random(1983)
        # 0x89 in the signature alone is invalid UTF-8; random bytes add NULs and more.
        return PNG_SIGNATURE + bytes(rnd.randrange(256) for _ in range(4096)) + payload

    def test_binary_png_is_skipped_not_crashed_and_not_flagged(self) -> None:
        # The secret inside the blob proves the file is skipped, not merely scanned clean.
        self.stage("shots/screen.png", self.png_bytes(f"\npassword = {AWS_KEY}\n".encode()))
        res = self.scan()
        self.assertNoCrash(res)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertIn("binary, skipped: shots/screen.png", res.stderr)
        self.assertNotIn("screen.png", res.stdout)

    def test_binary_before_text_secret_does_not_stop_the_scan(self) -> None:
        # git lists paths alphabetically: the PNG is read first, the secret after it.
        self.stage("a.png", self.png_bytes())
        self.stage("z_config.py", f'aws = "{AWS_KEY}"\n'.encode())
        res = self.scan()
        self.assertNoCrash(res)
        self.assertEqual(res.returncode, 1, res.stdout + res.stderr)
        self.assertIn("z_config.py:1 [aws-key]", res.stdout)

    def test_text_secret_is_still_caught(self) -> None:
        self.stage("settings.py", f'x = 1\naws = "{AWS_KEY}"\n'.encode())
        res = self.scan()
        self.assertNoCrash(res)
        self.assertEqual(res.returncode, 1, res.stdout + res.stderr)
        self.assertIn("settings.py:2 [aws-key]", res.stdout)
        self.assertNotIn("binary, skipped", res.stderr)

    def test_invalid_utf8_text_is_decoded_and_still_scanned(self) -> None:
        # cp1251 bytes are invalid UTF-8 but contain no NUL: the file is text and must be
        # scanned, including the secret that sits after the undecodable line.
        data = "Привет, мир\n".encode("cp1251") + f'aws = "{AWS_KEY}"\n'.encode()
        self.stage("notes.txt", data)
        res = self.scan()
        self.assertNoCrash(res)
        self.assertEqual(res.returncode, 1, res.stdout + res.stderr)
        self.assertIn("notes.txt:2 [aws-key]", res.stdout)
        self.assertNotIn("binary, skipped", res.stderr)

    def test_invalid_utf8_text_without_secret_passes(self) -> None:
        self.stage("legacy.txt", "Старый файл в cp1251\n".encode("cp1251"))
        res = self.scan()
        self.assertNoCrash(res)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)

    def test_nul_byte_marks_binary_regardless_of_extension(self) -> None:
        self.stage("blob.dat", b"header\x00\x01\x02" + f"token = {AWS_KEY}".encode())
        res = self.scan()
        self.assertNoCrash(res)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertIn("binary, skipped: blob.dat", res.stderr)

    def test_unreadable_staged_blob_blocks_by_name_instead_of_passing_as_clean(self) -> None:
        # Delete the loose object behind a staged path: `git show :<path>` now fails.
        # A failed read is a failed check, not a clean file — the hook must stop and
        # name the path, without a traceback and without calling it a found secret.
        self.stage("clean.txt", b"nothing here\n")
        sha = subprocess.run(["git", "rev-parse", ":clean.txt"], cwd=self.repo, check=True,
                             capture_output=True, text=True, env=clean_env()).stdout.strip()
        (self.repo / ".git" / "objects" / sha[:2] / sha[2:]).unlink()
        res = self.scan()
        self.assertNoCrash(res)
        self.assertEqual(res.returncode, 1, res.stdout + res.stderr)
        self.assertIn("clean.txt — сканер не смог прочитать файл из индекса", res.stdout)

    def test_failure_message_does_not_recommend_no_verify(self) -> None:
        self.stage("settings.py", f'aws = "{AWS_KEY}"\n'.encode())
        res = self.scan()
        self.assertEqual(res.returncode, 1)
        self.assertNotIn("--no-verify", res.stdout + res.stderr)


if __name__ == "__main__":
    unittest.main()
