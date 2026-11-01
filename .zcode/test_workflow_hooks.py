"""Exercise the ZCode hook adapter: reflex reuse, payload limits, recovery context."""

import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch


REPO = Path(__file__).resolve().parent.parent
HOOK = REPO / ".zcode/hooks/workflow-hooks.py"


class HookTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.put(".zcode/workflow.md", "Shared workflow adapter.\n")
        engine = self.root / ".claude/scripts/reflex-check.mjs"
        engine.parent.mkdir(parents=True)
        shutil.copyfile(REPO / ".claude/scripts/reflex-check.mjs", engine)
        self.put(".claude/reflexes/restart.md", "---\nuse-when:\n  - bash:/pm2 restart/i\n---\nReview production gates before restart.\n")
        self.put(".claude/reflexes/schema.md", "---\nuse-when:\n  - edit:src/db/**\n---\nCheck schema compatibility.\n")
        self.put(".claude/reflexes/runtime.md", "---\nuse-when:\n  - edit:**/data/**\n---\nKeep runtime data outside git.\n")
        spec = importlib.util.spec_from_file_location("zcode_workflow_hooks", HOOK)
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

    def test_apply_patch_alias_checks_every_changed_path(self):
        command = "*** Begin Patch\n*** Update File: src/index.py\n*** Move to: src/db/index.py\n@@\n+x\n*** Add File: service/data/state.json\n+{}\n*** End Patch"
        for index, tool in enumerate(("apply_patch", "ApplyPatch")):
            # separate session_id per iteration: the reflex engine deduplicates per session
            payload = {**self.payload, "session_id": f"{self.root}:{index}", "tool_name": tool, "tool_input": {"command": command}}
            result = self.module.pre_tool_use(payload, self.root)
            self.assertIn("schema compatibility", self.context(result))
            self.assertIn("runtime data outside git", self.context(result))

    def test_patch_content_is_not_interpreted_as_a_shell_command(self):
        command = "*** Begin Patch\n*** Add File: docs/note.md\n+git add production-secret\n*** End Patch"
        result = self.module.pre_tool_use({**self.payload, "tool_name": "ApplyPatch", "tool_input": {"command": command}}, self.root)
        self.assertEqual(result, {})

    def test_edit_paths_outside_the_repository_are_dropped(self):
        payload = {**self.payload, "tool_name": "Edit", "tool_input": {"file_path": "/tmp/elsewhere/x.py"}}
        self.assertEqual(self.module.tool_inputs(payload, self.root), [])

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

    def test_recovery_points_to_the_zcode_adapter(self):
        context = self.context(self.module.session_start(self.payload, self.root))
        self.assertIn(".zcode/workflow.md", context)

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

    def test_config_json_wires_both_hooks_and_enables_the_runner(self):
        config = json.loads((REPO / ".zcode/config.json").read_text())
        self.assertTrue(config["hooks"]["enabled"])
        self.assertIn("PreToolUse", config["hooks"]["events"])
        self.assertIn("SessionStart", config["hooks"]["events"])
        self.assertIn("compact", config["hooks"]["events"]["SessionStart"][0]["matcher"])
        for group in config["hooks"]["events"].values():
            for hook in group[0]["hooks"]:
                self.assertIn("${ZCODE_PROJECT_DIR}", hook["command"])


if __name__ == "__main__":
    unittest.main()
