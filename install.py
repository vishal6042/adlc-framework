#!/usr/bin/env python3
"""ADLC Framework installer - one implementation for Windows, macOS and Linux.

    python3 install.py <host> [target-project-dir] [--uninstall] [--dry-run] [--no-path]
      host = claude | cline | gemini | universal | all

The framework stays in THIS folder (the "common place"). The installer:
  1. regenerates adapters/ from core/ (build.py),
  2. puts core/scripts on your PATH and sets ADLC_HOME (skip with --no-path),
  3. copies each host's instruction files into that host's user-global config.

Files it does not own are never overwritten: for GEMINI.md and AGENTS.md it
manages only a marked block (<!-- adlc:begin --> ... <!-- adlc:end -->) and
leaves the rest of the file alone. --uninstall reverses every step.

install.sh / install.ps1 are thin wrappers that find Python and call this file.
"""
import argparse
import os
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
CORE = REPO / "core"
SCRIPTS = CORE / "scripts"
ADAPTERS = REPO / "adapters"
HOSTS = ["claude", "cline", "gemini", "universal"]
BEGIN = "<!-- adlc:begin (managed by adlc-framework; edits inside this block are replaced) -->"
END = "<!-- adlc:end -->"
BEGIN_PREFIX = "<!-- adlc:begin"
ENV_FILE_NAME = ".adlc_env"
RC_LINE = '[ -f "$HOME/.adlc_env" ] && . "$HOME/.adlc_env"  # adlc-framework'
# Skill folders installed by earlier versions, before names were prefixed.
LEGACY_SKILLS = ["jira-ticket", "spec-design", "constitution", "gherkin-criteria", "quality-gates",
                 "requirement-elicitation", "task-breakdown"]
IS_WINDOWS = os.name == "nt"


def home() -> Path:
    return Path(os.environ.get("ADLC_INSTALL_HOME") or Path.home())


def claude_dir() -> Path:
    return Path(os.environ["CLAUDE_CONFIG_DIR"]) if os.environ.get("CLAUDE_CONFIG_DIR") else home() / ".claude"


class Installer:
    def __init__(self, dry_run=False):
        self.dry = dry_run

    def say(self, msg):
        print(("[dry-run] " if self.dry else "") + msg)

    # --- file primitives -----------------------------------------------------------
    def copy(self, src: Path, dst: Path):
        self.say(f"  copy {dst}")
        if not self.dry:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)

    def remove(self, path: Path):
        if path.is_dir():
            self.say(f"  remove {path}{os.sep}")
            if not self.dry:
                shutil.rmtree(path)
        elif path.exists():
            self.say(f"  remove {path}")
            if not self.dry:
                path.unlink()

    def write_text(self, path: Path, text: str):
        if not self.dry:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(text.encode("utf-8"))

    # --- managed block in a user-owned file ------------------------------------------
    @staticmethod
    def merge_block(existing: str, block: str) -> str:
        wrapped = f"{BEGIN}\n{block.strip()}\n{END}\n"
        start = existing.find(BEGIN_PREFIX)
        end = existing.find(END, start if start != -1 else 0)
        if start != -1 and end != -1:
            return existing[:start] + wrapped + existing[end + len(END):].lstrip("\n")
        if not existing.strip():
            return wrapped
        return existing.rstrip("\n") + "\n\n" + wrapped

    @staticmethod
    def strip_block(existing: str) -> str:
        start = existing.find(BEGIN_PREFIX)
        end = existing.find(END, start if start != -1 else 0)
        if start == -1 or end == -1:
            return existing
        out = existing[:start].rstrip("\n") + "\n" + existing[end + len(END):].lstrip("\n")
        return "" if not out.strip() else out.rstrip("\n") + "\n"

    @staticmethod
    def is_legacy_whole_file(text: str) -> bool:
        """v0.3 wrote GEMINI.md / AGENTS.md as whole files; recognise them for upgrade."""
        head = text.lstrip()[:200]
        return BEGIN_PREFIX not in text and (
            head.startswith("# AGENTS.md — ADLC Framework")
            or head.startswith("# ADLC\n\nThis project supports the Agentic Development Life Cycle"))

    def upsert_block(self, path: Path, block: str):
        existing = path.read_text(encoding="utf-8") if path.exists() else ""
        if self.is_legacy_whole_file(existing):
            existing = ""
        self.say(f"  update ADLC block in {path}")
        self.write_text(path, self.merge_block(existing, block))

    def drop_block(self, path: Path):
        if not path.exists():
            return
        text = path.read_text(encoding="utf-8")
        if self.is_legacy_whole_file(text):
            self.remove(path)
            return
        new = self.strip_block(text)
        if new == text:
            return
        if not new:
            self.remove(path)
        else:
            self.say(f"  remove ADLC block from {path}")
            self.write_text(path, new)

    # --- hosts -------------------------------------------------------------------------
    def claude_files(self):
        src = ADAPTERS / "claude-code"
        base = claude_dir()
        pairs = [(p, base / "agents" / p.name) for p in sorted((src / "agents").glob("*.md"))]
        pairs += [(p, base / "skills" / p.parent.name / "SKILL.md")
                  for p in sorted((src / "skills").glob("*/SKILL.md"))]
        pairs.append((src / "commands" / "adlc.md", base / "commands" / "adlc.md"))
        return pairs

    def remove_legacy_claude_skills(self):
        for name in LEGACY_SKILLS:
            d = claude_dir() / "skills" / name
            skill = d / "SKILL.md"
            if skill.exists() and "ADLC" in skill.read_text(encoding="utf-8", errors="replace"):
                self.remove(d)

    def install_claude(self, _target):
        for src, dst in self.claude_files():
            self.copy(src, dst)
        self.remove_legacy_claude_skills()
        print(f"  Claude Code: /adlc is available in every project ({claude_dir()})")

    def uninstall_claude(self, _target):
        for _src, dst in self.claude_files():
            self.remove(dst)
            if dst.name == "SKILL.md":
                self.remove(dst.parent)
        self.remove_legacy_claude_skills()

    def cline_files(self):
        src = ADAPTERS / "cline" / ".clinerules"
        base = home() / "Documents" / "Cline"
        return [(src / "adlc.md", base / "Rules" / "adlc.md"),
                (src / "workflows" / "adlc.md", base / "Workflows" / "adlc.md")]

    def install_cline(self, _target):
        for src, dst in self.cline_files():
            self.copy(src, dst)
        print("  Cline: global rule + workflow installed under ~/Documents/Cline/")

    def uninstall_cline(self, _target):
        for _src, dst in self.cline_files():
            self.remove(dst)

    def install_gemini(self, _target):
        src = ADAPTERS / "gemini"
        self.copy(src / ".gemini" / "commands" / "adlc.toml", home() / ".gemini" / "commands" / "adlc.toml")
        self.upsert_block(home() / ".gemini" / "GEMINI.md", (src / "GEMINI.md").read_text(encoding="utf-8"))
        print("  Gemini CLI: /adlc installed (~/.gemini/commands/adlc.toml)")

    def uninstall_gemini(self, _target):
        self.remove(home() / ".gemini" / "commands" / "adlc.toml")
        self.drop_block(home() / ".gemini" / "GEMINI.md")

    def install_universal(self, target: Path):
        block = (ADAPTERS / "universal" / "AGENTS.md").read_text(encoding="utf-8")
        self.upsert_block(target / "AGENTS.md", block)
        print(f"  Universal: ADLC section added to {target / 'AGENTS.md'}")

    def uninstall_universal(self, target: Path):
        self.drop_block(target / "AGENTS.md")

    # --- PATH + ADLC_HOME --------------------------------------------------------------
    def register_path(self):
        if IS_WINDOWS:
            self._windows_env(add=True)
        else:
            env_file = home() / ENV_FILE_NAME
            self.say(f"  write {env_file}")
            self.write_text(env_file, (
                "# ADLC Framework - written by install.py; removed by install.py --uninstall\n"
                f'export ADLC_HOME="{CORE}"\n'
                f'case ":$PATH:" in *":{SCRIPTS}:"*) ;; *) export PATH="{SCRIPTS}:$PATH" ;; esac\n'))
            for rc in self._rc_files(create=True):
                text = rc.read_text(encoding="utf-8") if rc.exists() else ""
                if ".adlc_env" not in text:
                    self.say(f"  hook {rc}")
                    self.write_text(rc, text.rstrip("\n") + ("\n" if text.strip() else "") + RC_LINE + "\n")
        print(f"  PATH: {SCRIPTS}   ADLC_HOME: {CORE}   (open a new terminal to pick them up)")

    def unregister_path(self):
        if IS_WINDOWS:
            self._windows_env(add=False)
            return
        self.remove(home() / ENV_FILE_NAME)
        for rc in self._rc_files(create=False):
            text = rc.read_text(encoding="utf-8")
            lines = text.splitlines()
            kept = [ln for ln in lines if ".adlc_env" not in ln]
            if len(kept) != len(lines):
                self.say(f"  unhook {rc}")
                self.write_text(rc, "\n".join(kept) + ("\n" if kept else ""))

    def _rc_files(self, create):
        h = home()
        rcs = [h / n for n in (".bashrc", ".bash_profile", ".zshrc", ".profile") if (h / n).exists()]
        if create:
            shell = os.path.basename(os.environ.get("SHELL", ""))
            preferred = {"zsh": h / ".zshrc", "bash": h / ".bashrc"}.get(shell, h / ".profile")
            if preferred not in rcs:
                rcs.append(preferred)
        return rcs

    def _windows_env(self, add):
        import winreg  # Windows only
        scripts = str(SCRIPTS)

        def norm(p):
            return os.path.normcase(os.path.normpath(os.path.expandvars(p.strip()))) if p.strip() else ""

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0,
                            winreg.KEY_READ | winreg.KEY_WRITE) as key:
            try:
                value, kind = winreg.QueryValueEx(key, "Path")
            except FileNotFoundError:
                value, kind = "", winreg.REG_EXPAND_SZ
            parts = [p for p in value.split(";") if p.strip()]
            present = norm(scripts) in {norm(p) for p in parts}
            if add and not present:
                parts.append(scripts)
            elif not add:
                parts = [p for p in parts if norm(p) != norm(scripts)]
            new_value = ";".join(parts)
            if new_value != value:
                self.say(f"  {'add' if add else 'remove'} user PATH entry {scripts}")
                if not self.dry:
                    # Keep the original value type so %VARS% in PATH keep expanding.
                    winreg.SetValueEx(key, "Path", 0, kind, new_value)
            if add:
                self.say(f"  set user ADLC_HOME={CORE}")
                if not self.dry:
                    winreg.SetValueEx(key, "ADLC_HOME", 0, winreg.REG_SZ, str(CORE))
            else:
                try:
                    winreg.QueryValueEx(key, "ADLC_HOME")
                    self.say("  remove user ADLC_HOME")
                    if not self.dry:
                        winreg.DeleteValue(key, "ADLC_HOME")
                except FileNotFoundError:
                    pass
        if not self.dry:
            try:  # tell Explorer/new terminals that the environment changed
                import ctypes
                result = ctypes.c_ulong()
                ctypes.windll.user32.SendMessageTimeoutW(0xFFFF, 0x001A, 0, "Environment", 0x0002,
                                                         5000, ctypes.byref(result))
            except Exception:  # noqa: BLE001 - cosmetic; a new login picks it up anyway
                pass

    def unblock_windows_scripts(self):
        """Drop the 'downloaded from the internet' mark so PowerShell will run adlc.ps1."""
        if not IS_WINDOWS or self.dry:
            return
        for p in list(SCRIPTS.glob("*.ps1")) + [REPO / "install.ps1"]:
            try:
                os.remove(str(p) + ":Zone.Identifier")
            except OSError:
                pass


def build_adapters():
    sys.path.insert(0, str(REPO))
    try:
        import build  # noqa: WPS433 - local module
        build.build_all(ADAPTERS, quiet=True)
        print(f"  adapters regenerated from core/ (v{build.version()})")
    finally:
        sys.path.pop(0)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Install or remove the ADLC framework for an agent host.")
    ap.add_argument("host", choices=HOSTS + ["all"])
    ap.add_argument("target", nargs="?", default=os.getcwd(),
                    help="project directory for the universal AGENTS.md (default: current dir)")
    ap.add_argument("--uninstall", action="store_true", help="remove what install added")
    ap.add_argument("--dry-run", action="store_true", help="show what would change, change nothing")
    ap.add_argument("--no-path", action="store_true", help="do not touch PATH / ADLC_HOME")
    args = ap.parse_args(argv)

    if sys.version_info < (3, 8):
        print("ADLC needs Python 3.8+", file=sys.stderr)
        return 1
    target = Path(args.target).resolve()
    hosts = HOSTS if args.host == "all" else [args.host]
    inst = Installer(dry_run=args.dry_run)

    if args.uninstall:
        print(f"Uninstalling ADLC ({', '.join(hosts)})")
        for h in hosts:
            getattr(inst, f"uninstall_{h}")(target)
        if args.host == "all" and not args.no_path:
            inst.unregister_path()
        print("Done.")
        return 0

    if "universal" in hosts and not target.is_dir():
        print(f"target directory does not exist: {target}", file=sys.stderr)
        return 1
    print("1) Regenerating adapters from core/ ...")
    if not args.dry_run:
        build_adapters()
    if not args.no_path:
        print("2) Registering the shared framework on PATH")
        inst.register_path()
        inst.unblock_windows_scripts()
    print("3) Installing host instruction files")
    for h in hosts:
        getattr(inst, f"install_{h}")(target)
    print("\nDone. Open a new terminal, then check the setup with:  adlc doctor")
    print('Optional Jira: copy .env.example to .env (or export JIRA_* variables).')
    print('Then in any project:  /adlc "add a health endpoint"')
    return 0


if __name__ == "__main__":
    sys.exit(main())
