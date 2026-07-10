#!/usr/bin/env python3
"""build.py — generate every host adapter from core/ (single source of truth).

Run after any edit to core/ to re-sync all adapters. Idempotent: it wipes and
rewrites adapters/. This is the anti-drift mechanism — never hand-edit adapters/.

    py build.py          # Windows
    python3 build.py     # macOS/Linux

Hosts generated: Claude Code (plugin), Cline (.clinerules), Gemini CLI (TOML
command), and a universal AGENTS.md.
"""
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CORE = ROOT / "core"
ADAPTERS = ROOT / "adapters"

# How the deterministic entrypoint is invoked. All hosts call `adlc` on PATH
# (install.* adds $ADLC_HOME/core/scripts to PATH). No marketplace/plugin path
# is required, so the same mechanism works for every host including Claude Code.
ADLC_CLAUDE = "adlc"
ADLC_PATH = "adlc"  # on PATH via ADLC_HOME

STAGE_ORDER = ["1-intake", "2-spec", "3-tasks", "4-code", "5-tests", "6-verify", "7-ship"]
SKILLS = ["adlc-workflow", "constitution", "jira-ticket", "spec-design",
          "gherkin-criteria", "task-breakdown"]


# --- tiny frontmatter parser ----------------------------------------------
def parse(md_path: Path):
    text = md_path.read_text(encoding="utf-8")
    meta, body = {}, text
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            fm = text[3:end].strip("\n")
            body = text[end + 4:].lstrip("\n")
            for line in fm.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip()] = v.strip()
    return meta, body


def sub(body: str, adlc: str) -> str:
    return body.replace("@ADLC@", adlc)


def frontmatter(d: dict) -> str:
    lines = ["---"]
    for k, v in d.items():
        lines.append(f"{k}: {v}")
    lines.append("---")
    return "\n".join(lines) + "\n\n"


def write(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def inlined_runbook(adlc: str) -> str:
    """Full self-contained runbook for single-agent / doc hosts: orchestrator +
    every stage body + skill summaries, all @ADLC@-substituted."""
    parts = [sub((CORE / "orchestrator.md").read_text(encoding="utf-8"), adlc)]
    parts.append("\n\n---\n\n# Stage playbooks\n")
    for stem in STAGE_ORDER:
        _, body = parse(CORE / "stages" / f"{stem}.md")
        parts.append("\n" + sub(body, adlc))
    parts.append("\n\n---\n\n# Reference skills\n")
    for name in SKILLS:
        _, body = parse(CORE / "skills" / f"{name}.md")
        parts.append("\n" + sub(body, adlc))
    return "\n".join(parts)


# --- adapter generators ----------------------------------------------------
def build_claude():
    out = ADAPTERS / "claude-code"
    if out.exists():
        shutil.rmtree(out)
    # manifest + marketplace
    write(out / ".claude-plugin" / "plugin.json", json.dumps({
        "name": "adlc-framework",
        "displayName": "ADLC Framework",
        "version": "0.3.0",
        "description": "Agentic Development Life Cycle: Jira -> spec -> approval -> code -> tests -> verify -> git push, as orchestrated specialized agents. Generated from core/.",
        "author": {"name": "Vishal Bharti", "email": "bharti.vishal4@gmail.com"},
        "keywords": ["adlc", "agentic", "workflow", "pipeline", "jira", "sdlc"],
        "license": "MIT",
    }, indent=2) + "\n")
    write(out / ".claude-plugin" / "marketplace.json", json.dumps({
        "name": "adlc-framework-marketplace",
        "owner": {"name": "Vishal Bharti", "email": "bharti.vishal4@gmail.com"},
        "plugins": [{
            "name": "adlc-framework", "source": "./",
            "description": "ADLC pipeline: Jira -> spec -> approval -> code -> tests -> verify -> push.",
        }],
    }, indent=2) + "\n")
    # one subagent per stage
    for stem in STAGE_ORDER:
        meta, body = parse(CORE / "stages" / f"{stem}.md")
        fm = frontmatter({
            "name": meta["role"],
            "description": meta["description"],
            "tools": meta.get("claude_tools", "Read, Bash"),
            "model": "inherit",
        })
        write(out / "agents" / f"{meta['role']}.md", fm + sub(body, ADLC_CLAUDE))
    # skills
    for name in SKILLS:
        meta, body = parse(CORE / "skills" / f"{name}.md")
        fm = frontmatter({"name": meta["name"], "description": meta["description"]})
        write(out / "skills" / name / "SKILL.md", fm + sub(body, ADLC_CLAUDE))
    # orchestrator command
    _, orch = parse_or_raw(CORE / "orchestrator.md")
    cmd_fm = frontmatter({
        "description": "Run the Agentic Development Life Cycle: Jira/ticket -> spec -> approval -> code -> tests -> verify -> approval -> git push. Resumable.",
        "argument-hint": '"<feature request>" | resume <KEY> | status <KEY>',
    })
    write(out / "commands" / "adlc.md", cmd_fm + sub(orch, ADLC_CLAUDE))
    return out


def parse_or_raw(path: Path):
    """orchestrator.md has no frontmatter — return ({}, full text)."""
    meta, body = parse(path)
    if not meta:
        return {}, path.read_text(encoding="utf-8")
    return meta, body


def build_cline():
    out = ADAPTERS / "cline"
    if out.exists():
        shutil.rmtree(out)
    # always-on rule: short pointer
    rule = (
        "# ADLC framework (rules)\n\n"
        "This project can run the Agentic Development Life Cycle. To start it, invoke the "
        "`adlc` workflow (`.clinerules/workflows/adlc.md`) with a feature request.\n\n"
        "Deterministic operations (ticket keys, state, Jira, git, compare URLs) are the `adlc` "
        "script — call it, do not reimplement. Ensure `adlc` is on PATH (or use "
        "`$ADLC_HOME/scripts/adlc`). Artifacts live in `docs/adlc/<KEY>/`.\n"
    )
    write(out / ".clinerules" / "adlc.md", rule)
    # the workflow: full self-contained runbook
    write(out / ".clinerules" / "workflows" / "adlc.md", inlined_runbook(ADLC_PATH))
    return out


def toml_escape_multiline(s: str) -> str:
    # TOML multiline basic string: escape backslashes and any triple-quote runs.
    s = s.replace("\\", "\\\\").replace('"""', '\\"\\"\\"')
    return s


def build_gemini():
    out = ADAPTERS / "gemini"
    if out.exists():
        shutil.rmtree(out)
    runbook = inlined_runbook(ADLC_PATH)
    prompt = runbook + "\n\n---\n\n# Your task\nRun the ADLC pipeline for this request:\n{{args}}\n"
    toml = (
        'description = "Run the Agentic Development Life Cycle (Jira -> spec -> approval -> code '
        '-> tests -> verify -> push)."\n\n'
        'prompt = """\n' + toml_escape_multiline(prompt) + '\n"""\n'
    )
    write(out / ".gemini" / "commands" / "adlc.toml", toml)
    # GEMINI.md pointer
    write(out / "GEMINI.md",
          "# ADLC\n\nThis project supports the Agentic Development Life Cycle. Run `/adlc "
          '"<feature request>"` to execute it (Jira -> spec -> approval -> code -> tests -> '
          "verify -> push). Deterministic steps use the `adlc` script (keep it on PATH). "
          "Artifacts land in `docs/adlc/<KEY>/`.\n")
    return out


def build_universal():
    out = ADAPTERS / "universal"
    if out.exists():
        shutil.rmtree(out)
    header = (
        "# AGENTS.md — ADLC Framework\n\n"
        "This repository supports the **Agentic Development Life Cycle (ADLC)**: a request is "
        "taken from ticket to pushed branch through six stages with two human approval gates. "
        "Any AGENTS.md-aware agent can run it by following the runbook below.\n\n"
        "## Setup\n"
        "- Put the framework's `scripts/` directory on your PATH (so `adlc` resolves), or call "
        "`$ADLC_HOME/scripts/adlc`.\n"
        "- Optional Jira: set `JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`, `JIRA_PROJECT_KEY`. "
        "Without them the pipeline uses local ticket files.\n"
        "- Artifacts are written under `docs/adlc/<KEY>/`.\n\n"
        "---\n\n"
    )
    write(out / "AGENTS.md", header + inlined_runbook(ADLC_PATH))
    return out


def main():
    builders = [build_claude, build_cline, build_gemini, build_universal]
    print("Generating adapters from core/ ...")
    for b in builders:
        path = b()
        n = sum(1 for _ in path.rglob("*") if _.is_file())
        print(f"  [ok] {b.__name__[6:]:9s} -> {path.relative_to(ROOT)}  ({n} files)")
    print("Done. (adapters/ is generated - do not hand-edit.)")


if __name__ == "__main__":
    main()
