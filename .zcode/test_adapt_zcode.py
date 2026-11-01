"""Invariants of the .zcode/ runtime generation from .claude/ sources."""

import importlib.util
import json
import re
import subprocess
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
ADAPTER = REPO / ".zcode/adapt-zcode.py"

spec = importlib.util.spec_from_file_location("adapt_zcode", ADAPTER)
adapt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapt)

FORBIDDEN = [
    r"\bopus\b", r"\bsonnet\b", r"\bhaiku\b",
    r"TeamCreate", r"\bTask tool\b",
    r"\bteammates\b", r"\bteammate\b(?!\w*_name)",
]
ALLOWED_LINE_MARKERS = (".claude/", "~/.claude/")  # source paths stay authoritative


class GenerationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.generated = adapt.generate(REPO)

    def test_catalog_sizes_match_the_claude_sources(self):
        skills = {k for k in self.generated if k.startswith(".zcode/skills/") and k.endswith("/SKILL.md")}
        commands = {k for k in self.generated if k.startswith(".zcode/commands/")}
        agents = {k for k in self.generated if k.startswith(".zcode/agents/")}
        self.assertEqual(len(skills), len(list((REPO / ".claude/skills").glob("*/SKILL.md"))))
        self.assertEqual(len(commands), 18)
        self.assertEqual(len(agents), 24)

    def test_no_claude_runtime_vocabulary_survives(self):
        for target, data in self.generated.items():
            if not target.endswith(".md"):
                continue
            for line in data.decode().splitlines():
                if line.startswith(ALLOWED_LINE_MARKERS) or ".claude/" in line:
                    continue
                for pattern in FORBIDDEN:
                    self.assertIsNone(
                        re.search(pattern, line),
                        f"{target}: {pattern!r} survived in: {line[:100]!r}",
                    )

    def test_agents_carry_policy_models_and_single_line_descriptions(self):
        policy = json.loads((REPO / ".claude/shared/workflow-resources/policy.json").read_text())
        tiers = {tier: settings["zcode"] for tier, settings in policy["tiers"].items()}
        for target, data in self.generated.items():
            if not target.startswith(".zcode/agents/"):
                continue
            fm = re.match(r"\A---\n(.*?)\n---", data.decode(), re.S).group(1)
            model = re.search(r"^model: (\S+)$", fm, re.M).group(1)
            level = re.search(r"^thoughtLevel: (\S+)$", fm, re.M).group(1)
            self.assertIn(
                {"model": model, "thoughtLevel": level}, tiers.values(),
                f"{target}: model/thoughtLevel not from policy",
            )
            for line in fm.splitlines():
                self.assertFalse(line.startswith((" ", "\t")), f"{target}: indented frontmatter line: {line!r}")

    def test_tier_assignments_for_flagship_roles(self):
        security = self.generated[".zcode/agents/security-auditor.md"].decode()
        self.assertIn("model: GLM-5.3", security)
        self.assertIn("thoughtLevel: max", security)
        extractor = self.generated[".zcode/agents/workflow-extractor.md"].decode()
        self.assertIn("model: GLM-5.3-Flash", extractor)
        self.assertIn("thoughtLevel: low", extractor)
        self.assertIn("tools: [Read, Glob, Grep, Write]", extractor)

    def test_commands_have_flat_frontmatter(self):
        for target, data in self.generated.items():
            if not target.startswith(".zcode/commands/"):
                continue
            text = data.decode()
            fm_match = re.match(r"\A---\n(.*?)\n---", text, re.S)
            if fm_match is None:
                continue  # a command without frontmatter is valid (body/description rules apply)
            fm = fm_match.group(1)
            self.assertIsNotNone(re.search(r"^description: \S", fm, re.M), f"{target}: no single-line description")
            for line in fm.splitlines():
                self.assertFalse(line.startswith((" ", "\t")), f"{target}: indented frontmatter line: {line!r}")

    def test_feature_execution_adapts_team_mechanics(self):
        text = self.generated[".zcode/skills/feature-execution/SKILL.md"].decode()
        self.assertIn("run_in_background: true", text)
        self.assertIn("glm-max → GLM-5.3/max", text)
        self.assertIn("TaskStop", text)
        self.assertNotIn("team_name", text)

    def test_executor_catalog_is_zcode_native(self):
        text = self.generated[".zcode/skills/tech-spec-planning/references/skills-and-reviewers.md"].decode()
        self.assertIn("`glm-max`", text)
        self.assertIn("`glm-flash`", text)
        self.assertNotIn("`antigravity`", text)

    def test_generation_is_deterministic(self):
        self.assertEqual(self.generated, adapt.generate(REPO))

    def test_check_mode_confirms_the_committed_tree(self):
        result = subprocess.run(
            ["python3", str(ADAPTER), "--check"], capture_output=True, text=True, timeout=60, check=False
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("in sync", result.stdout)


if __name__ == "__main__":
    unittest.main()
