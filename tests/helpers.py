"""Shared helpers for the ADLC test suite (stdlib only)."""
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "core" / "scripts"
IS_WINDOWS = os.name == "nt"


def find_bash():
    """Git Bash on Windows (never WSL's System32 bash), plain bash elsewhere.

    ADLC_TEST_BASH overrides, e.g. /bin/bash on macOS to test bash 3.2.
    """
    if os.environ.get("ADLC_TEST_BASH"):
        return os.environ["ADLC_TEST_BASH"]
    if IS_WINDOWS:
        try:
            exec_path = subprocess.run(["git", "--exec-path"], capture_output=True, text=True).stdout.strip()
        except OSError:
            return None
        # .../Git/mingw64/libexec/git-core -> .../Git/bin/bash.exe
        cand = Path(exec_path).parents[2] / "bin" / "bash.exe"
        return str(cand) if cand.exists() else None
    return shutil.which("bash")


def find_powershell():
    if os.environ.get("ADLC_TEST_PWSH"):
        return os.environ["ADLC_TEST_PWSH"]
    if IS_WINDOWS:
        return shutil.which("powershell") or shutil.which("pwsh")
    return shutil.which("pwsh")


BASH = find_bash()
PWSH = find_powershell()


def ps_quote(s):
    return "'" + str(s).replace("'", "''") + "'"


class Runner:
    """Runs one implementation of the adlc CLI."""

    name = "?"

    def __init__(self, exe):
        self.exe = exe

    def run(self, cwd, *args, env=None):
        raise NotImplementedError


class BashRunner(Runner):
    name = "bash"

    def run(self, cwd, *args, env=None):
        cmd = [self.exe, (SCRIPTS / "adlc").as_posix(), *[str(a) for a in args]]
        return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8",
                              env=env, timeout=120)


class PwshRunner(Runner):
    name = "powershell"

    def run(self, cwd, *args, env=None):
        script = "& " + ps_quote(SCRIPTS / "adlc.ps1") + " " + " ".join(ps_quote(a) for a in args)
        script += "; exit $LASTEXITCODE"
        cmd = [self.exe, "-NoLogo", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
               "-Command", script]
        return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", env=env, timeout=120)


def runners():
    out = []
    if BASH:
        out.append(BashRunner(BASH))
    if PWSH:
        out.append(PwshRunner(PWSH))
    return out


def git(cwd, *args, check=True):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=check)


class TempRepo:
    """A throwaway git repository with one commit on main."""

    def __init__(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name) / "proj"
        self.path.mkdir()
        git(self.path, "init", "-q")
        git(self.path, "checkout", "-q", "-b", "main")
        git(self.path, "config", "user.email", "test@example.com")
        git(self.path, "config", "user.name", "ADLC Test")
        git(self.path, "config", "core.autocrlf", "false")
        git(self.path, "commit", "-q", "--allow-empty", "-m", "init")

    def file(self, rel):
        return self.path / rel

    def read(self, rel):
        return (self.path / rel).read_text(encoding="utf-8")

    def write(self, rel, text):
        p = self.path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(text.encode("utf-8"))

    def cleanup(self):
        self._tmp.cleanup()


def clean_env(**extra):
    """Environment without JIRA_/ADLC_ settings from the developer's machine."""
    env = {k: v for k, v in os.environ.items() if not k.startswith(("JIRA_", "ADLC_"))}
    env.update(extra)
    return env


def skip_unless(cond, why):
    return unittest.skipUnless(cond, why)
