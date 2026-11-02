"""Tests for build.py (adapter generation) and install.py (install/uninstall)."""
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from helpers import ROOT

sys.path.insert(0, str(ROOT))
import build  # noqa: E402
import install  # noqa: E402


def read_frontmatter(path):
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), path
    block = text[4:text.index("\n---", 3)]
    meta = {}
    for line in block.splitlines():
        k, v = line.split(":", 1)
        v = v.strip()
        meta[k.strip()] = json.loads(v) if v.startswith('"') else v
    return meta


class BuildTest(unittest.TestCase):
    def test_adapters_are_up_to_date(self):
        r = subprocess.run([sys.executable, str(ROOT / "build.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_check_detects_drift(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = Path(d) / "a", Path(d) / "b"
            build.build_all(a, quiet=True)
            build.build_all(b, quiet=True)
            self.assertEqual(build.diff_trees(a, b), [])
            (a / "cline" / ".clinerules" / "adlc.md").write_text("edited", encoding="utf-8")
            self.assertEqual(build.diff_trees(a, b), ["cline/.clinerules/adlc.md"])

    def test_claude_frontmatter(self):
        base = ROOT / "adapters" / "claude-code"
        agents = sorted((base / "agents").glob("*.md"))
        self.assertEqual(len(agents), 7)
        for p in agents:
            meta = read_frontmatter(p)
            self.assertEqual(meta["name"], p.stem)
            self.assertTrue(meta["description"])
            self.assertEqual(meta["model"], "inherit")
        for p in (base / "skills").glob("*/SKILL.md"):
            meta = read_frontmatter(p)
            self.assertEqual(meta["name"], p.parent.name)
            self.assertTrue(meta["name"].startswith("adlc-"), "skills are namespaced to avoid collisions")
        cmd = read_frontmatter(base / "commands" / "adlc.md")
        self.assertEqual(cmd["argument-hint"], '"<feature request>" | resume <KEY> | status <KEY>')
        self.assertIn("$ARGUMENTS", (base / "commands" / "adlc.md").read_text(encoding="utf-8"))

    def test_no_placeholders_left(self):
        for p in (ROOT / "adapters").rglob("*"):
            if p.is_file():
                self.assertNotIn("@ADLC@", p.read_text(encoding="utf-8"), p)

    def test_manifest_version_matches(self):
        plugin = json.loads((ROOT / "adapters/claude-code/.claude-plugin/plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(plugin["version"], build.version())
        self.assertRegex(build.version(), r"^\d+\.\d+\.\d+$")

    @unittest.skipUnless(sys.version_info >= (3, 11), "tomllib needs Python 3.11")
    def test_gemini_toml_parses(self):
        import tomllib
        data = tomllib.loads((ROOT / "adapters/gemini/.gemini/commands/adlc.toml").read_text(encoding="utf-8"))
        self.assertIn("{{args}}", data["prompt"])
        self.assertIn("Stage 1", data["prompt"])

    def test_generated_files_use_lf(self):
        for p in (ROOT / "adapters").rglob("*"):
            if p.is_file():
                self.assertNotIn(b"\r\n", p.read_bytes(), p)

    def test_package(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(build, "DIST", Path(d)):
            z = build.package()
            with zipfile.ZipFile(z) as zf:
                names = zf.namelist()
                prefix = f"adlc-framework-{build.version()}/"
                self.assertIn(prefix + "core/scripts/adlc", names)
                self.assertIn(prefix + "LICENSE", names)
                self.assertFalse(any("/tests/" in n or ".git/" in n for n in names))
                mode = (zf.getinfo(prefix + "core/scripts/adlc").external_attr >> 16) & 0o777
                self.assertEqual(mode, 0o755)


class CoreConsistencyTest(unittest.TestCase):
    def test_every_core_skill_is_built(self):
        on_disk = sorted(p.stem for p in (ROOT / "core" / "skills").glob("*.md"))
        self.assertEqual(on_disk, sorted(build.SKILLS))

    def test_powershell_scripts_are_ascii(self):
        # Windows PowerShell 5.1 reads BOM-less files as ANSI; non-ASCII breaks parsing.
        for p in list((ROOT / "core" / "scripts").glob("*.ps1")) + [ROOT / "install.ps1"]:
            p.read_bytes().decode("ascii")

    def test_cli_usage_lists_every_command(self):
        bash = (ROOT / "core/scripts/adlc").read_text(encoding="utf-8")
        ps = (ROOT / "core/scripts/adlc.ps1").read_text(encoding="utf-8")
        commands = re.findall(r"^  adlc ([a-z-]+)", bash, re.M)
        self.assertGreaterEqual(len(commands), 12)
        for c in commands:
            self.assertIn(f"  adlc {c}", ps, f"adlc.ps1 usage is missing '{c}'")


class InstallTest(unittest.TestCase):
    def setUp(self):
        self._home = tempfile.TemporaryDirectory()
        self._proj = tempfile.TemporaryDirectory()
        self.home = Path(self._home.name)
        self.proj = Path(self._proj.name)
        self.env = mock.patch.dict(os.environ, {"ADLC_INSTALL_HOME": str(self.home)})
        self.env.start()
        os.environ.pop("CLAUDE_CONFIG_DIR", None)

    def tearDown(self):
        self.env.stop()
        self._home.cleanup()
        self._proj.cleanup()

    def install(self, *args):
        with mock.patch("sys.stdout"):
            return install.main(list(args))

    def files(self):
        return sorted(p.relative_to(self.home).as_posix() for p in self.home.rglob("*") if p.is_file())

    def test_install_and_uninstall_all(self):
        (self.home / ".gemini").mkdir()
        (self.home / ".gemini" / "GEMINI.md").write_text("# mine\n", encoding="utf-8")
        (self.proj / "AGENTS.md").write_text("# project rules\n", encoding="utf-8")
        self.assertEqual(self.install("all", str(self.proj), "--no-path"), 0)
        got = self.files()
        self.assertIn(".claude/commands/adlc.md", got)
        self.assertIn(".claude/skills/adlc-workflow/SKILL.md", got)
        self.assertIn(".gemini/commands/adlc.toml", got)
        self.assertIn("Documents/Cline/Workflows/adlc.md", got)
        gemini = (self.home / ".gemini" / "GEMINI.md").read_text(encoding="utf-8")
        self.assertTrue(gemini.startswith("# mine\n"))
        self.assertEqual(gemini.count(install.END), 1)

        self.install("all", str(self.proj), "--no-path")  # idempotent
        agents = (self.proj / "AGENTS.md").read_text(encoding="utf-8")
        self.assertEqual(agents.count(install.END), 1)

        self.assertEqual(self.install("all", str(self.proj), "--no-path", "--uninstall"), 0)
        self.assertEqual(self.files(), [".gemini/GEMINI.md"])
        self.assertEqual((self.home / ".gemini" / "GEMINI.md").read_text(encoding="utf-8"), "# mine\n")
        self.assertEqual((self.proj / "AGENTS.md").read_text(encoding="utf-8"), "# project rules\n")

    def test_dry_run_changes_nothing(self):
        self.install("all", str(self.proj), "--no-path", "--dry-run")
        self.assertEqual(self.files(), [])
        self.assertFalse((self.proj / "AGENTS.md").exists())

    def test_upgrade_from_v03(self):
        legacy = self.home / ".claude" / "skills" / "jira-ticket"
        legacy.mkdir(parents=True)
        (legacy / "SKILL.md").write_text("---\nname: jira-ticket\n---\n# ADLC\n", encoding="utf-8")
        foreign = self.home / ".claude" / "skills" / "spec-design"
        foreign.mkdir(parents=True)
        (foreign / "SKILL.md").write_text("someone else's skill\n", encoding="utf-8")
        (self.proj / "AGENTS.md").write_text("# AGENTS.md — ADLC Framework\n\nold whole file\n", encoding="utf-8")
        self.install("claude", "--no-path")
        self.install("universal", str(self.proj), "--no-path")
        self.assertFalse(legacy.exists(), "old ADLC skill is removed")
        self.assertTrue(foreign.exists(), "unrelated skill with the same name is kept")
        agents = (self.proj / "AGENTS.md").read_text(encoding="utf-8")
        self.assertNotIn("old whole file", agents)
        self.assertTrue(agents.startswith(install.BEGIN_PREFIX))

    def test_claude_config_dir_is_respected(self):
        custom = self.home / "custom-claude"
        with mock.patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": str(custom)}):
            self.install("claude", "--no-path")
        self.assertTrue((custom / "commands" / "adlc.md").exists())

    @unittest.skipIf(os.name == "nt", "shell rc files are only used on macOS/Linux")
    def test_unix_path_registration(self):
        (self.home / ".bashrc").write_text("# existing\n", encoding="utf-8")
        inst = install.Installer()
        with mock.patch.dict(os.environ, {"SHELL": "/bin/zsh"}), mock.patch("sys.stdout"):
            inst.register_path()
            inst.register_path()
        bashrc = (self.home / ".bashrc").read_text(encoding="utf-8")
        self.assertEqual(bashrc.count(install.RC_LINE), 1, "hook line added exactly once")
        self.assertTrue((self.home / ".zshrc").exists())
        env_file = (self.home / ".adlc_env").read_text(encoding="utf-8")
        self.assertIn(str(install.SCRIPTS), env_file)
        with mock.patch("sys.stdout"):
            inst.unregister_path()
        self.assertEqual((self.home / ".bashrc").read_text(encoding="utf-8"), "# existing\n")
        self.assertFalse((self.home / ".adlc_env").exists())

    def test_block_helpers(self):
        merged = install.Installer.merge_block("# top\n", "body")
        self.assertEqual(install.Installer.merge_block(merged, "new body").count("new body"), 1)
        self.assertEqual(install.Installer.strip_block(merged), "# top\n")
        self.assertEqual(install.Installer.strip_block(install.Installer.merge_block("", "x")), "")


if __name__ == "__main__":
    unittest.main()
