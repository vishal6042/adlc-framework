#!/usr/bin/env python3
"""build.py - generate every host adapter from core/ (single source of truth).

Run after any edit to core/ to re-sync all adapters. Idempotent: it wipes and
rewrites adapters/. This is the anti-drift mechanism - never hand-edit adapters/.

    py build.py              # Windows
    python3 build.py         # macOS/Linux
    python3 build.py --check # exit 1 if adapters/ is out of date (use in CI)
    python3 build.py --package  # also write dist/adlc-framework-<version>.zip

Hosts generated: Claude Code (agents/skills/command + optional plugin manifest),
Cline (.clinerules), Gemini CLI (TOML command), and a universal AGENTS.md.
Requires Python 3.8+ and nothing outside the standard library.
"""
import argparse
import filecmp
import json
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CORE = ROOT / "core"
ADAPTERS = ROOT / "adapters"
DIST = ROOT / "dist"

# All hosts call `adlc` on PATH (the installer adds core/scripts to PATH).
ADLC_CMD = "adlc"

STAGE_ORDER = ["1-intake", "2-spec", "3-tasks", "4-code", "5-tests", "6-verify", "7-ship"]
SKILLS = ["adlc-workflow", "adlc-constitution", "adlc-jira-ticket", "adlc-requirement-elicitation",
          "adlc-spec-design", "adlc-gherkin-criteria", "adlc-task-breakdown", "adlc-quality-gates"]
AUTHOR = {"name": "Vishal Bharti", "email": "bharti.vishal4@gmail.com"}
REPO_URL = "https://github.com/vishal6042/adlc-framework"

# Shipped in the release zip (relative to ROOT). Everything else stays out.
PACKAGE_ITEMS = ["core", "adapters", "build.py", "install.py", "install.sh", "install.ps1",
                 "README.md", "LICENSE", "CHANGELOG.md", "SECURITY.md", ".env.example",
                 ".gitattributes"]


def version() -> str:
    return (CORE / "VERSION").read_text(encoding="utf-8").strip()


# --- tiny frontmatter parser / writer -------------------------------------------
def parse(md_path: Path):
    """Return (meta, body). Values are plain strings (no YAML features are used in core/)."""
    text = md_path.read_text(encoding="utf-8").replace("\r\n", "\n")
    meta, body = {}, text
    if text.startswith("---\n"):
        end = text.find("\n---", 3)
        if end != -1:
            for line in text[4:end].splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip()] = v.strip()
            body = text[end + 4:].lstrip("\n")
    return meta, body


def yaml_value(v: str) -> str:
    """Quote a scalar so any YAML parser reads it back verbatim.

    A JSON string is a valid YAML double-quoted scalar, so json.dumps is a safe
    quoter for values containing ':', '#', quotes, '|' and the like.
    """
    plain_ok = v and all(c.isalnum() or c in " ,._-()/" for c in v) and not v[0].isspace()
    return v if plain_ok else json.dumps(v, ensure_ascii=False)


def frontmatter(d: dict) -> str:
    lines = ["---"] + [f"{k}: {yaml_value(str(v))}" for k, v in d.items()] + ["---"]
    return "\n".join(lines) + "\n\n"


def sub(body: str) -> str:
    return body.replace("@ADLC@", ADLC_CMD)


def write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not content.endswith("\n"):
        content += "\n"
    path.write_bytes(content.encode("utf-8"))  # always LF, on every OS
    return path


def read_core(rel: str) -> str:
    return (CORE / rel).read_text(encoding="utf-8").replace("\r\n", "\n")


def inlined_runbook() -> str:
    """Self-contained runbook for single-agent / doc hosts: orchestrator + every
    stage body + skill bodies, all @ADLC@-substituted."""
    parts = [sub(read_core("orchestrator.md")).rstrip("\n")]
    parts.append("\n---\n\n# Stage playbooks")
    for stem in STAGE_ORDER:
        _, body = parse(CORE / "stages" / f"{stem}.md")
        parts.append(sub(body).rstrip("\n"))
    parts.append("\n---\n\n# Reference skills")
    for name in SKILLS:
        _, body = parse(CORE / "skills" / f"{name}.md")
        parts.append(sub(body).rstrip("\n"))
    return "\n\n".join(parts) + "\n"


# --- adapter generators ------------------------------------------------------------
def build_claude(out: Path):
    ver = version()
    write(out / ".claude-plugin" / "plugin.json", json.dumps({
        "name": "adlc-framework",
        "version": ver,
        "description": "Agentic Development Life Cycle: ticket -> spec -> approval -> code -> "
                       "tests -> verify -> approval -> git push, as orchestrated specialized agents.",
        "author": AUTHOR,
        "homepage": REPO_URL,
        "repository": REPO_URL,
        "license": "MIT",
        "keywords": ["adlc", "agentic", "workflow", "pipeline", "jira", "sdlc"],
    }, indent=2))
    write(out / ".claude-plugin" / "marketplace.json", json.dumps({
        "name": "adlc-framework-marketplace",
        "owner": AUTHOR,
        "plugins": [{
            "name": "adlc-framework", "source": "./", "version": ver,
            "description": "ADLC pipeline: ticket -> spec -> approval -> code -> tests -> verify -> push.",
        }],
    }, indent=2))
    for stem in STAGE_ORDER:
        meta, body = parse(CORE / "stages" / f"{stem}.md")
        fm = frontmatter({
            "name": meta["role"],
            "description": meta["description"],
            "tools": meta.get("claude_tools", "Read, Bash"),
            "model": "inherit",
        })
        write(out / "agents" / f"{meta['role']}.md", fm + sub(body))
    for name in SKILLS:
        meta, body = parse(CORE / "skills" / f"{name}.md")
        if meta.get("name") != name:
            raise SystemExit(f"core/skills/{name}.md: frontmatter name must be '{name}'")
        fm = frontmatter({"name": meta["name"], "description": meta["description"]})
        write(out / "skills" / name / "SKILL.md", fm + sub(body))
    cmd_fm = frontmatter({
        "description": "Run the Agentic Development Life Cycle: ticket -> spec -> approval -> "
                       "code -> tests -> verify -> approval -> git push. Resumable.",
        "argument-hint": '"<feature request>" | resume <KEY> | status <KEY>',
    })
    orch = sub(read_core("orchestrator.md")).rstrip("\n")
    write(out / "commands" / "adlc.md",
          cmd_fm + orch + "\n\n---\n\n## Your task\nRun the ADLC pipeline for: $ARGUMENTS\n")


def build_cline(out: Path):
    rule = (
        "# ADLC framework (rules)\n\n"
        "This project can run the Agentic Development Life Cycle. To start it, invoke the "
        "`adlc` workflow (`adlc.md` in your Cline workflows) with a feature request.\n\n"
        "Deterministic operations (ticket keys, state, templates, Jira, git, compare URLs) are "
        "the `adlc` command — call it, do not reimplement it. If `adlc` is not on PATH, use "
        "`$ADLC_HOME/scripts/adlc` (or `adlc doctor` to diagnose). Artifacts live in "
        "`docs/adlc/<KEY>/`.\n"
    )
    write(out / ".clinerules" / "adlc.md", rule)
    write(out / ".clinerules" / "workflows" / "adlc.md", inlined_runbook())


def toml_multiline(s: str) -> str:
    """Body of a TOML multi-line basic string: escape backslashes and quote runs."""
    return s.replace("\\", "\\\\").replace('"""', '\\"\\"\\"')


def build_gemini(out: Path):
    prompt = inlined_runbook() + "\n---\n\n# Your task\nRun the ADLC pipeline for this request:\n{{args}}\n"
    toml = (
        'description = "Run the Agentic Development Life Cycle (ticket -> spec -> approval -> '
        'code -> tests -> verify -> push)."\n\n'
        'prompt = """\n' + toml_multiline(prompt) + '"""\n'
    )
    write(out / ".gemini" / "commands" / "adlc.toml", toml)
    write(out / "GEMINI.md",
          "# ADLC\n\nThis machine has the Agentic Development Life Cycle installed. Run `/adlc "
          '"<feature request>"` to execute it (ticket -> spec -> approval -> code -> tests -> '
          "verify -> push). Deterministic steps use the `adlc` command (on PATH; `adlc doctor` "
          "diagnoses problems). Artifacts land in `docs/adlc/<KEY>/`.\n")


def build_universal(out: Path):
    header = (
        "# ADLC Framework\n\n"
        "This repository supports the **Agentic Development Life Cycle (ADLC)**: a request is "
        "taken from ticket to pushed branch through six stages with two human approval gates. "
        "Any AGENTS.md-aware agent can run it by following the runbook below.\n\n"
        "## Setup\n"
        "- Install the framework once (`install.sh` / `install.ps1`) so `adlc` is on PATH, or "
        "call `$ADLC_HOME/scripts/adlc`. Check with `adlc doctor`.\n"
        "- Optional Jira: set `JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`, `JIRA_PROJECT_KEY` "
        "(environment or `.env`). Without them the pipeline uses local ticket files.\n"
        "- Artifacts are written under `docs/adlc/<KEY>/`.\n\n"
        "---\n\n"
    )
    write(out / "AGENTS.md", header + inlined_runbook())


BUILDERS = {
    "claude-code": build_claude,
    "cline": build_cline,
    "gemini": build_gemini,
    "universal": build_universal,
}


def build_all(dest: Path, quiet=False):
    for name, fn in BUILDERS.items():
        out = dest / name
        if out.exists():
            shutil.rmtree(out)
        fn(out)
        if not quiet:
            n = sum(1 for p in out.rglob("*") if p.is_file())
            print(f"  [ok] {name:12s} -> {out.relative_to(dest.parent)}  ({n} files)")


def diff_trees(a: Path, b: Path):
    """Return relative paths that differ between two directory trees."""
    files_a = {p.relative_to(a).as_posix() for p in a.rglob("*") if p.is_file()} if a.exists() else set()
    files_b = {p.relative_to(b).as_posix() for p in b.rglob("*") if p.is_file()}
    changed = sorted(files_a ^ files_b)
    for rel in sorted(files_a & files_b):
        pa, pb = a / rel, b / rel
        if pa.read_bytes().replace(b"\r\n", b"\n") != pb.read_bytes():
            changed.append(rel)
    return changed


def check() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        fresh = Path(tmp) / "adapters"
        build_all(fresh, quiet=True)
        changed = diff_trees(ADAPTERS, fresh)
    if changed:
        print("adapters/ is out of date with core/. Run `python3 build.py` and commit. Differences:")
        for rel in changed:
            print(f"  {rel}")
        return 1
    print("adapters/ is up to date.")
    return 0


def package() -> Path:
    DIST.mkdir(exist_ok=True)
    name = f"adlc-framework-{version()}"
    zpath = DIST / f"{name}.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for item in PACKAGE_ITEMS:
            src = ROOT / item
            if not src.exists():
                raise SystemExit(f"package: missing {item}")
            paths = [src] if src.is_file() else sorted(p for p in src.rglob("*") if p.is_file())
            for p in paths:
                if "__pycache__" in p.parts:
                    continue
                rel = p.relative_to(ROOT).as_posix()
                info = zipfile.ZipInfo(f"{name}/{rel}", date_time=(2020, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                executable = rel in ("core/scripts/adlc", "install.sh", "build.py", "install.py")
                info.external_attr = (0o100755 if executable else 0o100644) << 16
                z.writestr(info, p.read_bytes())
    return zpath


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Generate host adapters from core/.")
    ap.add_argument("--check", action="store_true", help="fail if adapters/ is out of date")
    ap.add_argument("--package", action="store_true", help="also build dist/<name>-<version>.zip")
    args = ap.parse_args(argv)
    if sys.version_info < (3, 8):
        print("build.py needs Python 3.8+", file=sys.stderr)
        return 1
    if args.check:
        return check()
    print(f"Generating adapters from core/ (v{version()}) ...")
    build_all(ADAPTERS)
    print("Done. (adapters/ is generated - do not hand-edit.)")
    if args.package:
        print(f"Packaged {package().relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
