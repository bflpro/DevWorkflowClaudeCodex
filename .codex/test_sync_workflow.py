"""Behavioral tests for the repository workflow synchronizer."""

import importlib.util
import json
from pathlib import Path
import tempfile
import tomllib
import unittest
import subprocess


SPEC = importlib.util.spec_from_file_location(
    "sync_workflow", Path(__file__).with_name("sync-workflow.py")
)


class SyncTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.put(".claude/skills/planning/SKILL.md", "---\nname: planning\ndescription: |\n  Plan a feature.\n---\nUse references/rules.md.\n")
        self.put(".claude/skills/planning/references/rules.md", "Authoritative rules.\n")
        self.put(".claude/commands/build.md", "---\ndescription: Build a feature\n---\nUse planning.\n")
        self.put(".claude/agents/reviewer.md", "---\nname: reviewer\ndescription: |\n  Review implementation.\nskills: [planning]\n---\nNever edit reviewed code.\n")
        self.put(".codex/workflow.md", "Runtime adaptations.\n")
        self.module = importlib.util.module_from_spec(SPEC)
        SPEC.loader.exec_module(self.module)

    def put(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def test_initial_adoption_preserves_originals_resources_and_agent_settings(self):
        original = "Old locally adapted skill.\n"
        self.put(".agents/skills/planning/SKILL.md", original)
        resource = self.put(".agents/skills/planning/references/local.md", "Local reference.\n")
        self.put(".codex/agents/reviewer.toml", 'name = "reviewer"\nmodel_reasoning_effort = "high"\ndeveloper_instructions = "Old instructions"\n')
        self.module.sync(self.root, write=True, adopt=True)
        backup = self.root / ".codex/data/workflow-backup/.agents/skills/planning/SKILL.md"
        self.assertEqual(backup.read_text(), original)
        self.assertEqual(resource.read_text(), "Local reference.\n")
        role = tomllib.loads((self.root / ".codex/agents/reviewer.toml").read_text())
        self.assertEqual(role["model_reasoning_effort"], "high")
        self.assertIn(".claude/agents/reviewer.md", role["developer_instructions"])
        self.assertEqual(self.module.sync(self.root), [])

    def test_check_is_read_only_and_reports_missing_adapters(self):
        before = sorted(str(p) for p in self.root.rglob("*"))
        self.assertTrue(self.module.sync(self.root))
        self.assertEqual(before, sorted(str(p) for p in self.root.rglob("*")))
        self.module.sync(self.root, write=True)
        path = self.root / ".agents/skills/source-command-build/SKILL.md"
        path.unlink()
        self.assertTrue(any("source-command-build" in d for d in self.module.sync(self.root)))

    def test_discovery_description_preserves_triggers_after_blank_lines(self):
        self.put(".claude/skills/planning/SKILL.md", "---\nname: planning\ndescription: |\n  Plan a feature.\n\n  Use when: create a specification.\ncategory: process\n---\nBody.\n")
        self.module.sync(self.root, write=True)
        wrapper = (self.root / ".agents/skills/planning/SKILL.md").read_text()
        self.assertIn("Use when: create a specification.", wrapper)
        self.assertNotIn("category: process", wrapper)

    def test_long_source_description_is_adapted_without_modifying_source(self):
        source = self.put(".claude/skills/planning/SKILL.md", "---\nname: planning\ndescription: " + "Use <feature>. " * 100 + "\n---\nComplete source.\n")
        original = source.read_bytes()
        self.module.sync(self.root, write=True)
        wrapper = (self.root / ".agents/skills/planning/SKILL.md").read_text()
        description = json.loads(wrapper.split("description: ", 1)[1].splitlines()[0])
        self.assertLessEqual(len(description), 1024)
        self.assertNotIn("<", description)
        self.assertEqual(source.read_bytes(), original)

    def test_source_changes_refresh_entrypoints_without_copying_methodology(self):
        self.module.sync(self.root, write=True)
        source = self.root / ".claude/skills/planning/SKILL.md"
        source.write_text(source.read_text() + "Run wave-check before execution.\n")
        self.assertTrue(self.module.sync(self.root))
        self.module.sync(self.root, write=True)
        wrapper = (self.root / ".agents/skills/planning/SKILL.md").read_text()
        self.assertIn(".claude/skills/planning/SKILL.md", wrapper)
        self.assertNotIn("Run wave-check", wrapper)
        self.assertEqual(self.module.sync(self.root), [])

    def test_local_edit_blocks_all_writes(self):
        self.module.sync(self.root, write=True)
        target = self.root / ".agents/skills/planning/SKILL.md"
        target.write_text(target.read_text() + "Intentional local work.\n")
        command = self.root / ".claude/commands/build.md"
        command.write_text(command.read_text() + "Changed command.\n")
        manifest = (self.root / ".codex/workflow-manifest.json").read_bytes()
        with self.assertRaises(self.module.ConflictError):
            self.module.sync(self.root, write=True)
        self.assertEqual((self.root / ".codex/workflow-manifest.json").read_bytes(), manifest)
        self.assertTrue(target.read_text().endswith("Intentional local work.\n"))

    def test_idempotence_does_not_rewrite_files(self):
        self.module.sync(self.root, write=True)
        manifest = self.root / ".codex/workflow-manifest.json"
        stamp = manifest.stat().st_mtime_ns
        self.module.sync(self.root, write=True)
        self.assertEqual(manifest.stat().st_mtime_ns, stamp)

    def test_removed_source_is_reported_without_deleting_adapter(self):
        self.module.sync(self.root, write=True)
        (self.root / ".claude/commands/build.md").unlink()
        with self.assertRaises(self.module.ConflictError):
            self.module.sync(self.root, write=True)
        self.assertTrue((self.root / ".agents/skills/source-command-build/SKILL.md").exists())

    def test_symlink_target_is_rejected_without_writing_outside_root(self):
        outside = self.root / "outside.md"
        outside.write_text("Preserve this.\n")
        target = self.root / ".agents/skills/planning/SKILL.md"
        target.parent.mkdir(parents=True)
        target.symlink_to(outside)
        with self.assertRaises(self.module.ConflictError):
            self.module.sync(self.root, write=True, adopt=True)
        self.assertEqual(outside.read_text(), "Preserve this.\n")

    def test_manifest_records_source_and_target_provenance(self):
        self.module.sync(self.root, write=True)
        manifest = json.loads((self.root / ".codex/workflow-manifest.json").read_text())
        record = manifest["targets"][".agents/skills/planning/SKILL.md"]
        self.assertEqual(record["source"], ".claude/skills/planning/SKILL.md")
        self.assertEqual(len(record["source_sha256"]), 64)
        self.assertEqual(len(record["target_sha256"]), 64)

    def test_existing_shared_source_is_never_replaced_with_a_wrapper(self):
        source = self.root / ".claude/skills/planning/SKILL.md"
        text = source.read_text()
        target = self.put(".agents/skills/planning/SKILL.md", text)
        source.unlink()
        source.symlink_to(target)
        self.module.sync(self.root, write=True)
        self.assertEqual(target.read_text(), text)
        self.assertEqual(self.module.sync(self.root), [])

    def test_staged_source_cannot_ship_with_unstaged_adapter_updates(self):
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        self.module.sync(self.root, write=True)
        subprocess.run(["git", "add", "."], cwd=self.root, check=True)
        self.assertEqual(self.module.check_staged(self.root), [])

    def test_git_catalog_exposes_adapters_but_keeps_unrelated_resources_private(self):
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        self.put(".gitignore", ".agents/*\n!.agents/.gitignore\n!.agents/skills/\n")
        unrelated = self.put(".agents/skills/personal/SKILL.md", "Local private skill.\n")
        resource = self.put(".agents/skills/planning/scripts/old.py", "print('old')\n")
        self.module.sync(self.root, write=True)
        ignored = subprocess.run(["git", "check-ignore", str(unrelated), str(resource)], cwd=self.root, capture_output=True, text=True, check=False)
        self.assertIn(str(unrelated), ignored.stdout)
        self.assertIn(str(resource), ignored.stdout)
        public = subprocess.run(["git", "check-ignore", str(self.root / ".agents/skills/planning/SKILL.md")], cwd=self.root, capture_output=True, check=False)
        self.assertEqual(public.returncode, 1)
        source = self.root / ".claude/commands/build.md"
        source.write_text(source.read_text() + "Updated source.\n")
        subprocess.run(["git", "add", str(source)], cwd=self.root, check=True)
        self.module.sync(self.root, write=True)
        self.assertTrue(self.module.check_staged(self.root))
        subprocess.run(["git", "add", "."], cwd=self.root, check=True)
        self.assertEqual(self.module.check_staged(self.root), [])


if __name__ == "__main__":
    unittest.main()
