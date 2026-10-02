"""Exercise hook protocols and the canonical local workflow in isolated repositories."""

import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch


REPO = Path(__file__).resolve().parent.parent
HOOK = REPO / ".codex/hooks/workflow-hooks.py"


class HookTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.put(".codex/workflow.md", "Shared workflow adapter.\n")
        engine = self.root / ".claude/scripts/reflex-check.mjs"
        engine.parent.mkdir(parents=True)
        shutil.copyfile(REPO / ".claude/scripts/reflex-check.mjs", engine)
        self.put(".claude/reflexes/restart.md", "---\nuse-when:\n  - bash:/pm2 restart/i\n---\nReview production gates before restart.\n")
        self.put(".claude/reflexes/schema.md", "---\nuse-when:\n  - edit:src/db/**\n---\nCheck schema compatibility.\n")
        self.put(".claude/reflexes/runtime.md", "---\nuse-when:\n  - edit:**/data/**\n---\nKeep runtime data outside git.\n")
        self.put(".claude/reflexes/vcs.md", "---\nuse-when:\n  - bash:/git add/i\n---\nReview staged paths.\n")
        spec = importlib.util.spec_from_file_location("workflow_hooks", HOOK)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        self.payload = {"session_id": str(self.root), "cwd": str(self.root)}

    def put(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def context(self, result):
        return result.get("hookSpecificOutput", {}).get("additionalContext", "")

    def test_bash_uses_the_actual_reflex_engine_and_deduplicates(self):
        payload = {**self.payload, "tool_name": "Bash", "tool_input": {"command": "pm2 restart service"}}
        result = self.module.pre_tool_use(payload, self.root)
        self.assertIn("Review production gates", self.context(result))
        self.assertEqual(self.module.pre_tool_use(payload, self.root), {})

    def test_apply_patch_checks_every_changed_path_including_move_target(self):
        command = "*** Begin Patch\n*** Update File: src/index.py\n*** Move to: src/db/index.py\n@@\n+x\n*** Add File: service/data/state.json\n+{}\n*** End Patch"
        result = self.module.pre_tool_use({**self.payload, "tool_name": "apply_patch", "tool_input": {"command": command}}, self.root)
        self.assertIn("schema compatibility", self.context(result))
        self.assertIn("runtime data outside git", self.context(result))

    def test_patch_content_is_not_interpreted_as_a_shell_command(self):
        command = "*** Begin Patch\n*** Add File: docs/note.md\n+git add production-secret\n*** End Patch"
        result = self.module.pre_tool_use({**self.payload, "tool_name": "apply_patch", "tool_input": {"command": command}}, self.root)
        self.assertEqual(result, {})

    def test_nested_cwd_path_is_resolved_relative_to_the_repository(self):
        nested = self.root / "src"
        nested.mkdir()
        command = "*** Begin Patch\n*** Add File: db/schema.py\n+x\n*** End Patch"
        payload = {**self.payload, "cwd": str(nested), "tool_name": "apply_patch", "tool_input": {"command": command}}
        self.assertIn("schema compatibility", self.context(self.module.pre_tool_use(payload, self.root)))

    def test_timeout_is_visible_without_exposing_payload(self):
        payload = {**self.payload, "tool_name": "Bash", "tool_input": {"command": "private command"}}
        with patch.object(self.module.subprocess, "run", side_effect=subprocess.TimeoutExpired("node", 3)):
            with patch("sys.stderr") as stderr:
                self.assertEqual(self.module.pre_tool_use(payload, self.root), {})
        text = " ".join(str(call) for call in stderr.write.call_args_list)
        self.assertIn("TimeoutExpired", text)
        self.assertNotIn("private command", text)

    def test_recovery_lists_multiple_active_features_without_selecting_one(self):
        for name in ["alpha", "beta"]:
            self.put(f"work/{name}/tasks/1.md", "---\nstatus: in_progress\n---\nTask\n")
            self.put(f"work/{name}/logs/checkpoint.yml", "team_name: old-team\nsecret: should-not-be-injected\n")
        self.put("work/completed/archived/tasks/1.md", "---\nstatus: in_progress\n---\nOld\n")
        result = self.module.session_start({**self.payload, "source": "compact"}, self.root)
        self.assertEqual(result["hookSpecificOutput"]["hookEventName"], "SessionStart")
        context = self.context(result)
        self.assertIn("work/alpha", context)
        self.assertIn("work/beta", context)
        self.assertNotIn("archived", context)
        self.assertNotIn("should-not-be-injected", context)

    def test_completed_task_does_not_become_active_due_to_old_checkpoint(self):
        self.put("work/old/tasks/1.md", "---\nstatus: done\n---\nDone\n")
        self.put("work/old/logs/checkpoint.yml", "team_name: old\n")
        context = self.context(self.module.session_start(self.payload, self.root))
        self.assertNotIn("work/old", context)
        self.assertIn(".codex/workflow.md", context)

    def test_malformed_stdin_does_not_break_the_session_or_echo_input(self):
        result = subprocess.run(["python3", str(HOOK), "pre-tool-use"], input="private malformed payload", capture_output=True, text=True, timeout=10, check=False)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertIn("JSONDecodeError", result.stderr)
        self.assertNotIn("private malformed payload", result.stderr)

    def test_oversized_payload_is_rejected_with_a_diagnostic(self):
        result = subprocess.run(["python3", str(HOOK), "pre-tool-use"], input="x" * (1024 * 1024 + 1), capture_output=True, text=True, timeout=10, check=False)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertIn("payload limit", result.stderr)


class LifecycleSmokeTests(unittest.TestCase):
    def test_template_wave_check_and_acceptance_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            subprocess.run(["bash", str(REPO / ".claude/shared/scripts/init-feature-folder.sh"), "smoke"], cwd=root, check=True, capture_output=True)
            feature = root / "work/smoke"
            self.assertTrue((feature / "tech-spec.md").exists())
            self.assertTrue((feature / "logs/userspec/interview.yml").exists())
            scripts = root / "scripts"
            scripts.mkdir()
            (scripts / "fixture.py").write_text('print("before")\n')
            subprocess.run(["git", "add", "."], cwd=root, check=True)
            subprocess.run(["git", "-c", "core.hooksPath=/dev/null", "-c", "user.name=Workflow Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "Synthetic baseline"], cwd=root, check=True)
            sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
            tasks = feature / "tasks"
            tasks.mkdir(exist_ok=True)
            (tasks / "1.md").write_text(
                "---\nstatus: in_progress\nwave: 1\ndepends_on: []\n"
                "owns_paths: [scripts/fixture.py]\nreads: []\nproduces: []\n"
                f"authored_by: human:fixture\nreviewers: [none]\nverify_cwd: .\nstart_commit: {sha}\n---\n"
                "# Task 1\n\n## Verification Steps\n\n### Automated\n"
                "- `python3 scripts/fixture.py` → exit 0\n"
            )
            (scripts / "fixture.py").write_text('print("verified fixture")\n')
            wave = subprocess.run(["python3", str(REPO / ".claude/scripts/wave-check.py"), str(feature)], capture_output=True, text=True, check=False)
            self.assertEqual(wave.returncode, 0, wave.stdout + wave.stderr)
            accepted = subprocess.run(["python3", str(REPO / ".claude/scripts/task-accept.py"), str(feature), "1"], capture_output=True, text=True, check=False)
            self.assertEqual(accepted.returncode, 0, accepted.stdout + accepted.stderr)
            receipt = json.loads((feature / "logs/receipts/task-1/acceptance.json").read_text())
            self.assertTrue(receipt["accepted"])
            self.assertEqual(receipt["owns_check"], "passed")
            self.assertIn("verified fixture", receipt["verification"][0]["output_tail"])


if __name__ == "__main__":
    unittest.main()
