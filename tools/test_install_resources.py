"""Portable installation smoke tests, including an existing customized project."""

import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

import tomllib

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "configure_resources", ROOT / "tools/configure-resources.py"
)
CONFIG = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CONFIG)


class InstallTests(unittest.TestCase):
    def test_policy_append_and_config_merge_are_idempotent_and_preserve_user_content(
        self,
    ):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / ".codex").mkdir()
            rules = "# My project\nCustom business rules.\n"
            (root / "CLAUDE.md").write_text(rules)
            (root / ".codex/config.toml").write_text(
                'model = "my-parent-model"\n[mcp_servers.local]\ncommand = "local-tool"\n[agents]\nmax_threads = 2\n'
            )
            CONFIG.configure(root, codex=True)
            self.assertTrue((root / "CLAUDE.md").read_text().startswith(rules))
            config = tomllib.loads((root / ".codex/config.toml").read_text())
            self.assertEqual(config["model"], "my-parent-model")
            self.assertEqual(config["mcp_servers"]["local"]["command"], "local-tool")
            self.assertEqual(config["agents"]["max_threads"], 2)
            self.assertEqual(
                config["agents"]["default_subagent_model"], "gpt-6.1-terra"
            )
            self.assertEqual(CONFIG.configure(root, codex=True), 0)

    def test_existing_explicit_defaults_survive_and_dry_run_writes_nothing(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / ".codex").mkdir()
            path = root / ".codex/config.toml"
            path.write_text('[agents]\ndefault_subagent_model = "my-custom-model"\n')
            before = path.read_bytes()
            CONFIG.configure(root, codex=True, dry=True)
            self.assertEqual(path.read_bytes(), before)
            self.assertFalse((root / "CLAUDE.md").exists())
            CONFIG.configure(root, codex=True)
            self.assertEqual(
                tomllib.loads(path.read_text())["agents"]["default_subagent_model"],
                "my-custom-model",
            )

    def test_full_install_and_second_install_produce_consistent_models_and_ignore_metrics(
        self,
    ):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            for _ in range(2):
                result = subprocess.run(
                    [
                        "bash",
                        str(ROOT / "install.sh"),
                        "--target",
                        str(root),
                        "--codex",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=90,
                    check=False,
                )
                self.assertEqual(
                    result.returncode, 0, result.stdout[-3000:] + result.stderr[-1000:]
                )
            self.assertIn("added 0,", result.stdout)
            policy = json.loads(
                (root / ".claude/shared/workflow-resources/policy.json").read_text()
            )
            for name, tier in policy["roles"].items():
                role = tomllib.loads((root / f".codex/agents/{name}.toml").read_text())
                for key, value in policy["tiers"][tier]["codex"].items():
                    self.assertEqual(role[key], value, name)
            result = subprocess.run(
                ["git", "check-ignore", ".claude/state/workflow-metrics/state.json"],
                cwd=root,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0)
            self.assertEqual(
                subprocess.run(
                    ["python3", ".codex/sync-workflow.py", "--check"],
                    cwd=root,
                    capture_output=True,
                    check=False,
                ).returncode,
                0,
            )

    def test_zcode_install_generates_runtime_and_merges_user_config(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            (root / ".zcode").mkdir()
            (root / ".zcode/config.json").write_text(
                json.dumps({"mcp": {"servers": {"mine": {"type": "stdio", "command": "mine"}}}})
            )
            (root / "AGENTS.md").write_text("# Project rules\nKeep mine.\n")
            for _ in range(2):
                result = subprocess.run(
                    ["bash", str(ROOT / "install.sh"), "--target", str(root), "--zcode"],
                    capture_output=True, text=True, timeout=90, check=False,
                )
                self.assertEqual(
                    result.returncode, 0, result.stdout[-3000:] + result.stderr[-1000:]
                )
            self.assertIn("added 0,", result.stdout)
            self.assertTrue((root / ".zcode/skills/build-route/SKILL.md").exists())
            self.assertTrue((root / ".zcode/commands/build.md").exists())
            reviewer = (root / ".zcode/agents/code-reviewer.md").read_text()
            self.assertIn("model: GLM-5.3", reviewer)
            self.assertIn("thoughtLevel: high", reviewer)
            agents_md = (root / "AGENTS.md").read_text()
            self.assertIn(agents_md.splitlines()[0], "# Project rules")
            self.assertIn("<!-- workflow-zcode -->", agents_md)
            config = json.loads((root / ".zcode/config.json").read_text())
            self.assertEqual(config["mcp"]["servers"]["mine"]["command"], "mine")
            self.assertTrue(config["hooks"]["enabled"])
            self.assertIn("PreToolUse", config["hooks"]["events"])
            self.assertEqual(
                subprocess.run(
                    ["python3", ".zcode/adapt-zcode.py", "--check"],
                    cwd=root, capture_output=True, check=False,
                ).returncode,
                0,
            )


if __name__ == "__main__":
    unittest.main()
