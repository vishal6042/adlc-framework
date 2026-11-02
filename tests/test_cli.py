"""Behavioural tests for the `adlc` CLI. Every test runs against each available
implementation (bash `adlc` and PowerShell `adlc.ps1`) so the twins stay in sync."""
import datetime
import re
import unittest

from helpers import BASH, PWSH, TempRepo, clean_env, git, runners

TRICKY_TITLE = 'Add A & B | C/D \\ "quoted" $HOME `x` feature'


class CliContract:
    """Mixin: the test body. Subclasses set `runner`."""

    runner = None

    def setUp(self):
        self.repo = TempRepo()
        self.env = clean_env()

    def tearDown(self):
        self.repo.cleanup()

    def adlc(self, *args, ok=True, env=None):
        r = self.runner.run(self.repo.path, *args, env=env or self.env)
        if ok is True:
            self.assertEqual(r.returncode, 0, f"{self.runner.name} {args}: {r.stdout}\n{r.stderr}")
        elif ok is not None:
            self.assertEqual(r.returncode, ok, f"{self.runner.name} {args}: {r.stdout}\n{r.stderr}")
        return r

    def init_run(self, title="add a health endpoint", key=None):
        args = ["init", title] + ([key] if key else [])
        return self.adlc(*args).stdout.strip()

    def make_shippable(self, key):
        self.adlc("approve", key, "gate2")
        self.adlc("scaffold", key, "verification")
        path = f"docs/adlc/{key}/verification.md"
        text = self.repo.read(path).replace("- Result: PASS | FAIL", "- **Result:** PASS")
        self.repo.write(path, text)

    # --- basics ---------------------------------------------------------------
    def test_help_and_version(self):
        self.assertIn("Usage:", self.adlc("help").stdout)
        self.assertRegex(self.adlc("version").stdout.strip(), r"^adlc \d+\.\d+\.\d+$")

    def test_unknown_command_is_usage_error(self):
        r = self.adlc("frobnicate", ok=2)
        self.assertIn("unknown command", r.stderr)

    def test_missing_arguments_are_usage_errors(self):
        for args in (["init"], ["status"], ["get-state", "ADLC-001"], ["set-state", "ADLC-001", "x"],
                     ["approve", "ADLC-001"], ["ship"]):
            self.adlc(*args, ok=2)

    # --- init / keys ------------------------------------------------------------
    def test_init_creates_run(self):
        key = self.init_run()
        self.assertEqual(key, "ADLC-001")
        state = self.repo.read("docs/adlc/ADLC-001/state.md")
        self.assertIn("- current_stage: intake", state)
        self.assertIn("- branch: adlc/ADLC-001-add-a-health-endpoint", state)
        self.assertIn(f"- created: {datetime.date.today():%Y-%m-%d}", state)
        self.assertEqual(self.repo.read("docs/adlc/ADLC-001/ticket.md"),
                         self.repo.read("docs/adlc/tickets/ADLC-001.md"))
        self.assertEqual(self.adlc("next-key").stdout.strip(), "ADLC-002")

    def test_init_writes_lf_without_bom(self):
        self.init_run()
        raw = self.repo.file("docs/adlc/ADLC-001/state.md").read_bytes()
        self.assertFalse(raw.startswith(b"\xef\xbb\xbf"), "state.md must not have a BOM")
        self.assertNotIn(b"\r\n", raw)

    def test_init_keeps_special_characters_literal(self):
        key = self.init_run(TRICKY_TITLE)
        self.assertEqual(self.adlc("get-state", key, "title").stdout.strip(), TRICKY_TITLE)
        self.assertIn(TRICKY_TITLE, self.repo.read(f"docs/adlc/{key}/ticket.md"))

    def test_init_refuses_to_overwrite(self):
        self.init_run()
        r = self.adlc("init", "again", "ADLC-001", ok=1)
        self.assertIn("already exists", r.stderr)

    def test_init_with_jira_key(self):
        self.assertEqual(self.init_run("x", "PROJ-42"), "PROJ-42")
        self.assertTrue(self.repo.file("docs/adlc/PROJ-42/state.md").exists())

    def test_invalid_keys_are_rejected(self):
        for bad in ("../../etc-1", "ADLC", "ADLC-1/x", "-1", "AD LC-1"):
            r = self.adlc("init", "x", bad, ok=1)
            self.assertIn("invalid KEY", r.stderr)
        self.assertFalse(self.repo.file("etc-1").exists())

    def test_slug_fallback_for_non_ascii_title(self):
        key = self.init_run("修复 bug")
        self.assertEqual(self.adlc("get-state", key, "branch").stdout.strip(), f"adlc/{key}-bug")
        key = self.init_run("修复")
        self.assertEqual(self.adlc("get-state", key, "branch").stdout.strip(), f"adlc/{key}-change")

    def test_branch_prefix_from_env_and_dotenv(self):
        self.adlc("init", "first", env=clean_env(ADLC_BRANCH_PREFIX="feat"))
        self.assertIn("- branch: feat/ADLC-001-first", self.repo.read("docs/adlc/ADLC-001/state.md"))
        self.repo.write(".env", 'ADLC_BRANCH_PREFIX="team"\nOTHER=ignored\n')
        self.adlc("init", "second")
        self.assertIn("- branch: team/ADLC-002-second", self.repo.read("docs/adlc/ADLC-002/state.md"))
        # a real environment variable wins over .env
        self.adlc("init", "third", env=clean_env(ADLC_BRANCH_PREFIX="env"))
        self.assertIn("- branch: env/ADLC-003-third", self.repo.read("docs/adlc/ADLC-003/state.md"))

    def test_runs_anchor_at_git_root_from_subdirectory(self):
        sub = self.repo.path / "src" / "pkg"
        sub.mkdir(parents=True)
        r = self.runner.run(sub, "init", "from a subdir", env=self.env)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(self.repo.file("docs/adlc/ADLC-001/state.md").exists())
        self.assertFalse((sub / "docs").exists())

    # --- state ------------------------------------------------------------------
    def test_state_round_trip_with_special_characters(self):
        key = self.init_run()
        for value in ("a|b&c/d\\e", "$1 $HOME", "100%", "x: y"):
            self.adlc("set-state", key, "notes", value)
            self.assertEqual(self.adlc("get-state", key, "notes").stdout.strip(), value)

    def test_new_field_is_inserted_above_log(self):
        key = self.init_run()
        self.adlc("set-state", key, "reviewer", "sam")
        state = self.repo.read(f"docs/adlc/{key}/state.md")
        self.assertLess(state.index("- reviewer: sam"), state.index("## Log"))
        self.assertIn("- verify_attempts: 0\n- reviewer: sam\n\n## Log", state)

    def test_get_state_ignores_log_lines(self):
        key = self.init_run()
        self.adlc("approve", key, "gate1")
        self.assertEqual(self.adlc("get-state", key, "gate1_spec_approved").stdout.strip(), "true")
        self.assertEqual(self.adlc("get-state", key, "no_such_field").stdout.strip(), "")

    def test_set_state_validates_field_and_run(self):
        key = self.init_run()
        self.adlc("set-state", key, "Bad-Field", "x", ok=1)
        self.adlc("set-state", "ADLC-099", "notes", "x", ok=1)

    def test_newlines_in_values_are_flattened(self):
        key = self.init_run()
        # (a space keeps Windows' argv quoting from splitting the value at the newline)
        self.adlc("set-state", key, "notes", "line 1\nline 2")
        self.assertEqual(self.adlc("get-state", key, "notes").stdout.strip(), "line 1 line 2")

    def test_approve_records_gate_and_log(self):
        key = self.init_run()
        self.assertIn("recorded gate1", self.adlc("approve", key, "gate1").stdout)
        self.adlc("approve", key, "gate3", ok=2)
        state = self.repo.read(f"docs/adlc/{key}/state.md")
        self.assertIn("- gate1_spec_approved: true", state)
        self.assertIn("gate1: approved by user", state)

    def test_status_of_missing_run_fails(self):
        r = self.adlc("status", "ADLC-404", ok=1)
        self.assertIn("no ADLC run", r.stderr)

    # --- scaffold -----------------------------------------------------------------
    def test_scaffold_spec_and_verification(self):
        key = self.init_run("title here")
        self.adlc("scaffold", key, "spec")
        spec = self.repo.read(f"docs/adlc/{key}/spec.md")
        self.assertIn(f"# Spec: {key}", spec)
        self.assertIn("title here", spec)
        self.repo.write(f"docs/adlc/{key}/spec.md", "edited\n")
        self.assertIn("exists", self.adlc("scaffold", key, "spec").stdout)
        self.assertEqual(self.repo.read(f"docs/adlc/{key}/spec.md"), "edited\n")
        self.adlc("set-state", key, "verify_attempts", "2")
        self.adlc("scaffold", key, "verification", "--force")
        self.assertIn("(attempt 3)", self.repo.read(f"docs/adlc/{key}/verification.md"))
        self.adlc("scaffold", key, "readme", ok=2)

    # --- branch -------------------------------------------------------------------
    def test_branch_creates_and_reuses(self):
        key = self.init_run()
        b = self.adlc("branch", key).stdout.strip()
        self.assertEqual(git(self.repo.path, "branch", "--show-current").stdout.strip(), b)
        git(self.repo.path, "checkout", "-q", "main")
        self.assertEqual(self.adlc("branch", key).stdout.strip(), b)

    def test_branch_refuses_protected(self):
        key = self.init_run()
        self.adlc("set-state", key, "branch", "main")
        r = self.adlc("branch", key, ok=1)
        self.assertIn("protected", r.stderr)

    # --- ship ---------------------------------------------------------------------
    def test_ship_requires_gate2(self):
        key = self.init_run()
        self.assertIn("gate2 not approved", self.adlc("ship", key, ok=1).stderr)

    def test_ship_requires_pass(self):
        key = self.init_run()
        self.adlc("approve", key, "gate2")
        self.assertIn("no verification report", self.adlc("ship", key, ok=1).stderr)
        self.adlc("scaffold", key, "verification")
        self.assertIn("not PASS", self.adlc("ship", key, ok=1).stderr)
        path = f"docs/adlc/{key}/verification.md"
        self.repo.write(path, self.repo.read(path).replace("- Result: PASS | FAIL", "- Result: FAIL"))
        self.assertIn("not PASS", self.adlc("ship", key, ok=1).stderr)

    def test_ship_blocks_secrets(self):
        key = self.init_run()
        self.make_shippable(key)
        self.repo.write(".env", "TOKEN=1\n")
        self.repo.write("config/.env.example", "TOKEN=\n")
        self.repo.write("certs/server.pem", "x\n")
        r = self.adlc("ship", key, "--no-push", ok=1)
        self.assertIn(".env", r.stderr)
        self.assertIn("certs/server.pem", r.stderr)
        self.assertNotIn(".env.example", r.stderr)
        self.assertEqual(git(self.repo.path, "log", "--oneline").stdout.count("\n"), 1, "nothing committed")

    def test_ship_local_commit(self):
        key = self.init_run(TRICKY_TITLE)
        self.make_shippable(key)
        self.repo.write("app.txt", "hello\n")
        r = self.adlc("ship", key, "--no-push")
        self.assertIn("committed locally only", r.stdout)
        msg = git(self.repo.path, "log", "-1", "--format=%B").stdout
        self.assertTrue(msg.startswith(f"{key}: {TRICKY_TITLE}\n"), msg)
        self.assertIn(f"Refs: docs/adlc/{key}/spec.md", msg)
        self.assertEqual(self.adlc("get-state", key, "current_stage").stdout.strip(), "done")
        self.assertNotEqual(git(self.repo.path, "branch", "--show-current").stdout.strip(), "main")
        self.assertEqual(git(self.repo.path, "status", "--porcelain").stdout, "")

    def test_ship_pushes_to_remote(self):
        key = self.init_run()
        self.make_shippable(key)
        bare = self.repo.path.parent / "remote.git"
        git(self.repo.path.parent, "init", "-q", "--bare", str(bare))
        git(self.repo.path, "remote", "add", "origin", bare.as_posix())
        self.repo.write("app.txt", "hello\n")
        r = self.adlc("ship", key)
        self.assertIn("pushed", r.stdout)
        branch = self.adlc("get-state", key, "branch").stdout.strip()
        self.assertIn(branch, git(bare, "branch").stdout)
        self.assertEqual(self.adlc("get-state", key, "current_stage").stdout.strip(), "done")

    def test_ship_push_failure_keeps_commit_and_stage(self):
        key = self.init_run()
        self.make_shippable(key)
        git(self.repo.path, "remote", "add", "origin", (self.repo.path.parent / "missing.git").as_posix())
        self.repo.write("app.txt", "hello\n")
        r = self.adlc("ship", key, ok=3)
        self.assertIn("push FAILED", r.stderr)
        self.assertIn(key, git(self.repo.path, "log", "-1", "--format=%s").stdout)
        self.assertNotEqual(self.adlc("get-state", key, "current_stage").stdout.strip(), "done")

    def test_ship_reports_commit_failure(self):
        key = self.init_run()
        self.make_shippable(key)
        hook = self.repo.path / ".git" / "hooks" / "pre-commit"
        hook.write_bytes(b"#!/bin/sh\necho 'hook says no' >&2\nexit 1\n")
        hook.chmod(0o755)
        self.repo.write("app.txt", "hello\n")
        r = self.adlc("ship", key, "--no-push", ok=1)
        self.assertIn("commit failed", r.stderr)
        self.assertNotEqual(self.adlc("get-state", key, "current_stage").stdout.strip(), "done")

    def test_ship_rejects_unknown_option(self):
        key = self.init_run()
        self.adlc("ship", key, "--force", ok=2)

    # --- compare-url ----------------------------------------------------------------
    def test_compare_url_forms(self):
        cases = {
            "git@github.com:o/r.git": "https://github.com/o/r/compare/b/1?expand=1",
            "https://user:s3cret@github.com/o/r.git": "https://github.com/o/r/compare/b/1?expand=1",
            "ssh://git@gitlab.example.com:2222/g/r.git":
                "https://gitlab.example.com/g/r/-/merge_requests/new?merge_request%5Bsource_branch%5D=b/1",
            "https://bitbucket.org/o/r": "https://bitbucket.org/o/r/pull-requests/new?source=b/1",
            "https://git.corp.example:8443/o/r.git": "https://git.corp.example:8443/o/r/compare/b/1?expand=1",
        }
        for remote, expected in cases.items():
            git(self.repo.path, "remote", "remove", "origin", check=False)
            git(self.repo.path, "remote", "add", "origin", remote)
            out = self.adlc("compare-url", "b/1").stdout.strip()
            self.assertEqual(out, expected, remote)
            self.assertNotIn("s3cret", out)
        git(self.repo.path, "remote", "remove", "origin")
        self.assertEqual(self.adlc("compare-url", "b/1").stdout.strip(), "")

    # --- spec-kit helpers ----------------------------------------------------------
    def test_scaffold_tasks(self):
        key = self.init_run("make tasks")
        self.adlc("scaffold", key, "tasks")
        self.assertIn(f"# Tasks: {key}", self.repo.read(f"docs/adlc/{key}/tasks.md"))

    def test_constitution_created_once(self):
        r = self.adlc("constitution")
        path = r.stdout.strip()
        self.assertTrue(path.replace("\\", "/").endswith("docs/adlc/constitution.md"), path)
        self.assertIn("created", r.stderr)
        text = self.repo.read("docs/adlc/constitution.md")
        self.assertIn(f"{datetime.date.today():%Y-%m-%d}", text)
        self.repo.write("docs/adlc/constitution.md", "mine\n")
        r = self.adlc("constitution")
        self.assertEqual(r.stderr.strip(), "")
        self.assertEqual(self.repo.read("docs/adlc/constitution.md"), "mine\n")

    def test_clarifications(self):
        key = self.init_run()
        self.repo.write(f"docs/adlc/{key}/ticket.md", "Mark unknowns with [NEEDS CLARIFICATION].\n")
        self.assertIn("no open clarifications", self.adlc("clarifications", key).stdout)
        self.repo.write(f"docs/adlc/{key}/spec.md", "a\n- Auth? [NEEDS CLARIFICATION: which IdP?]\n")
        r = self.adlc("clarifications", key, ok=1)
        self.assertRegex(r.stdout.strip(), r"spec\.md:2:- Auth\? \[NEEDS CLARIFICATION: which IdP\?\]$")
        self.adlc("clarifications", "ADLC-404", ok=1)
        self.adlc("clarifications", ok=2)

    def test_detect_stack(self):
        self.assertEqual(self.adlc("detect-stack").stdout.strip(), "unknown")
        self.repo.write("package.json", '{"dependencies": {"react": "18"}}\n')
        self.repo.write("pyproject.toml", "[project]\n")
        self.repo.write("build.gradle", "plugins {}\n")
        self.repo.write("app/src/main/AndroidManifest.xml", "<manifest/>\n")
        self.assertEqual(self.adlc("detect-stack").stdout.strip(), "android react python")
        sub = self.repo.path / "app"
        r = self.runner.run(sub, "detect-stack", env=self.env)
        self.assertEqual(r.stdout.strip(), "android react python", "detects from the repo root")

    def test_min_coverage(self):
        self.assertEqual(self.adlc("min-coverage").stdout.strip(), "90")
        self.assertEqual(self.adlc("min-coverage", env=clean_env(ADLC_MIN_COVERAGE="75")).stdout.strip(), "75")
        r = self.adlc("min-coverage", env=clean_env(ADLC_MIN_COVERAGE="150"))
        self.assertEqual(r.stdout.strip(), "90")
        self.assertIn("ignoring", r.stderr)
        self.assertEqual(self.adlc("min-coverage", env=clean_env(ADLC_MIN_COVERAGE="abc")).stdout.strip(), "90")

    # --- doctor / jira passthrough ---------------------------------------------------
    def test_doctor(self):
        out = self.adlc("doctor").stdout
        self.assertIn("git", out)
        self.assertIn("local ticket mode", out)

    def test_jira_mode_local(self):
        r = self.adlc("jira", "mode")
        self.assertEqual(r.stdout.strip(), "local")
        self.adlc("jira", "pick", ok=2)


@unittest.skipUnless(BASH, "bash not available")
class BashCliTest(CliContract, unittest.TestCase):
    from helpers import BashRunner
    runner = BashRunner(BASH) if BASH else None


@unittest.skipUnless(PWSH, "PowerShell not available")
class PowerShellCliTest(CliContract, unittest.TestCase):
    from helpers import PwshRunner
    runner = PwshRunner(PWSH) if PWSH else None


@unittest.skipUnless(len(runners()) == 2, "needs both bash and PowerShell")
class ParityTest(unittest.TestCase):
    """Same commands -> byte-identical artifacts from both implementations."""

    def test_identical_artifacts(self):
        outputs = []
        for r in runners():
            repo = TempRepo()
            try:
                env = clean_env()
                for args in (["init", TRICKY_TITLE], ["set-state", "ADLC-001", "jira_mode", "local"],
                             ["set-state", "ADLC-001", "extra", "a|b"], ["approve", "ADLC-001", "gate1"],
                             ["scaffold", "ADLC-001", "spec"], ["scaffold", "ADLC-001", "tasks"],
                             ["constitution"]):
                    res = r.run(repo.path, *args, env=env)
                    self.assertEqual(res.returncode, 0, f"{r.name} {args}: {res.stderr}")
                outputs.append({p: repo.file(p).read_bytes() for p in (
                    "docs/adlc/ADLC-001/state.md", "docs/adlc/ADLC-001/ticket.md",
                    "docs/adlc/ADLC-001/spec.md", "docs/adlc/ADLC-001/tasks.md",
                    "docs/adlc/tickets/ADLC-001.md", "docs/adlc/constitution.md")})
            finally:
                repo.cleanup()
        self.assertEqual(outputs[0], outputs[1])

    def test_identical_help(self):
        texts = []
        for r in runners():
            repo = TempRepo()
            try:
                texts.append(re.sub(r"\r\n", "\n", r.run(repo.path, "help").stdout).strip())
            finally:
                repo.cleanup()
        self.assertEqual(texts[0], texts[1])


if __name__ == "__main__":
    unittest.main()
