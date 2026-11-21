"""Tests for the [INTO-SKILL] hook and installer. Run: python3 -m unittest -v (from this folder)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import install  # noqa: E402
import into_skill  # noqa: E402

TEMPLATE = (HERE / "instructions.md").read_text(encoding="utf-8")


def run_hook(payload, env_extra=None):
    env = {**os.environ, **(env_extra or {})}
    return subprocess.run(
        [sys.executable, str(HERE / "into_skill.py")],
        input=payload if isinstance(payload, str) else json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


class TagTests(unittest.TestCase):
    def test_detects_variants(self):
        for prompt in ["[INTO-SKILL] x", "x [into-skill]", "[ Into_Skill ]", "[INTOSKILL]", "[into skill]"]:
            self.assertTrue(into_skill.has_tag(prompt), prompt)

    def test_ignores_other_text(self):
        for prompt in ["", "into-skill", "make this into a skill", "[INTO-SKILLS]"]:
            self.assertFalse(into_skill.has_tag(prompt), prompt)

    def test_strip(self):
        self.assertEqual(into_skill.strip_tag("[INTO-SKILL]  always use uv "), "always use uv")


class ContextTests(unittest.TestCase):
    payload = {"prompt": "[INTO-SKILL] run tests with -x", "session_id": "s1", "transcript_path": "/t.jsonl", "cwd": "/w"}

    def test_no_tag_returns_none(self):
        self.assertIsNone(into_skill.build_context({"prompt": "hi"}, {}, TEMPLATE))

    def test_defaults_rendered(self):
        ctx = into_skill.build_context(self.payload, {}, TEMPLATE, which=lambda _: "/bin/x")
        self.assertIn("run tests with -x", ctx)
        self.assertIn("wadidaww/mcp", ctx)
        self.assertIn("`claude/`", ctx)
        self.assertIn("/t.jsonl", ctx)
        self.assertNotIn("{{", ctx)
        self.assertIn("- none", ctx)

    def test_env_overrides(self):
        env = {"INTO_SKILL_REPO": "me/agents", "INTO_SKILL_BASE": "dev", "INTO_SKILL_ROOT": "/cfg/"}
        ctx = into_skill.build_context(self.payload, env, TEMPLATE, which=lambda _: "/bin/x")
        self.assertIn("me/agents", ctx)
        self.assertIn("origin/dev", ctx)
        self.assertIn("`cfg/skills/", ctx)

    def test_missing_gh_warns(self):
        ctx = into_skill.build_context(self.payload, {}, TEMPLATE, which=lambda t: None if t == "gh" else "/bin/x")
        self.assertIn("`gh` was not found", ctx)

    def test_empty_note(self):
        ctx = into_skill.build_context({"prompt": "[INTO-SKILL]"}, {}, TEMPLATE, which=lambda _: "/bin/x")
        self.assertIn("infer the lesson", ctx)


class ScriptTests(unittest.TestCase):
    def test_passthrough_without_tag(self):
        res = run_hook({"prompt": "hello"})
        self.assertEqual(res.returncode, 0)
        self.assertEqual(res.stdout, "")

    def test_bad_json_never_blocks(self):
        res = run_hook("not json")
        self.assertEqual(res.returncode, 0)
        self.assertEqual(res.stdout, "")

    def test_emits_additional_context(self):
        res = run_hook({"prompt": "[INTO-SKILL] note", "session_id": "s"})
        self.assertEqual(res.returncode, 0, res.stderr)
        out = json.loads(res.stdout)
        self.assertEqual(out["hookSpecificOutput"]["hookEventName"], "UserPromptSubmit")
        self.assertIn("<into-skill-request>", out["hookSpecificOutput"]["additionalContext"])

    def test_custom_template(self):
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as fh:
            fh.write("custom {{REPO}} {{NOTE}}")
        try:
            res = run_hook({"prompt": "[INTO-SKILL] n"}, {"INTO_SKILL_TEMPLATE": fh.name, "INTO_SKILL_REPO": "a/b"})
            self.assertEqual(json.loads(res.stdout)["hookSpecificOutput"]["additionalContext"], "custom a/b n")
        finally:
            os.unlink(fh.name)


class InstallTests(unittest.TestCase):
    def test_merge_settings_idempotent_and_preserving(self):
        settings = {"model": "x", "hooks": {"UserPromptSubmit": [{"hooks": [{"type": "command", "command": "other"}]}]}}
        settings, changed = install.merge_settings(settings, "python3 /a/hooks/into-skill/into_skill.py")
        self.assertTrue(changed)
        settings, changed = install.merge_settings(settings, "python3 /a/hooks/into-skill/into_skill.py")
        self.assertFalse(changed)
        self.assertEqual(settings["model"], "x")
        commands = [h["command"] for g in settings["hooks"]["UserPromptSubmit"] for h in g["hooks"]]
        self.assertEqual(commands, ["other", "python3 /a/hooks/into-skill/into_skill.py"])

    def test_install_and_link(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            claude_dir = tmp / "dotclaude"
            clone = tmp / "clone"
            (clone / ".git").mkdir(parents=True)
            (clone / "claude" / "skills" / "demo").mkdir(parents=True)
            (clone / "claude" / "skills" / "demo" / "SKILL.md").write_text("---\nname: demo\n---\n")
            (clone / "claude" / "skills" / "README.md").write_text("x")
            (clone / "claude" / "rules").mkdir()
            (clone / "claude" / "rules" / "testing.md").write_text("x")
            (clone / "claude" / "rules" / "README.md").write_text("x")

            old = os.environ.get("INTO_SKILL_CLONE")
            os.environ["INTO_SKILL_CLONE"] = str(clone)
            try:
                self.assertEqual(install.main(["--claude-dir", str(claude_dir), "--link"]), 0)
                self.assertEqual(install.main(["--claude-dir", str(claude_dir), "--link"]), 0)
            finally:
                if old is None:
                    del os.environ["INTO_SKILL_CLONE"]
                else:
                    os.environ["INTO_SKILL_CLONE"] = old

            self.assertTrue((claude_dir / "hooks" / "into-skill" / "into_skill.py").exists())
            settings = json.loads((claude_dir / "settings.json").read_text())
            self.assertEqual(len(settings["hooks"]["UserPromptSubmit"]), 1)
            self.assertTrue((claude_dir / "skills" / "demo").is_symlink())
            self.assertFalse((claude_dir / "skills" / "README.md").exists())
            self.assertTrue((claude_dir / "rules" / "testing.md").is_symlink())
            self.assertFalse((claude_dir / "rules" / "README.md").exists())

            # Installed hook runs from its new location.
            cmd = settings["hooks"]["UserPromptSubmit"][0]["hooks"][0]["command"]
            res = subprocess.run(cmd, shell=True, input=json.dumps({"prompt": "[INTO-SKILL] hi"}),
                                 capture_output=True, text=True, check=False)
            self.assertIn("into-skill-request", res.stdout, res.stderr)


if __name__ == "__main__":
    unittest.main()
