#!/usr/bin/env bash
# ADLC Framework installer (macOS / Linux / Git Bash)
#
#   ./install.sh <host> [target-project-dir]
#     host = claude | cline | gemini | universal | all
#     target-project-dir defaults to the current directory (for project-scoped hosts)
#
# Always regenerates adapters from core/ first (single source of truth).

set -euo pipefail
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
host="${1:-}"; target="${2:-$PWD}"

pick_python() { for c in python3 py python; do command -v "$c" >/dev/null 2>&1 && "$c" -c "import sys" >/dev/null 2>&1 && { echo "$c"; return; }; done; echo ""; }

usage() { echo "usage: ./install.sh <claude|cline|gemini|universal|all> [target-dir]"; exit 1; }
[ -n "$host" ] || usage

PY="$(pick_python)"; [ -n "$PY" ] || { echo "No working python found (need python3/py)."; exit 1; }
echo "Regenerating adapters from core/ ..."; ( cd "$repo" && "$PY" build.py )

path_hint() {
  echo ">> Add the ADLC scripts to your PATH so 'adlc' resolves, e.g.:"
  echo "     export ADLC_HOME=\"$repo/core\""
  echo "     export PATH=\"\$ADLC_HOME/scripts:\$PATH\""
}

install_claude() {
  if command -v claude >/dev/null 2>&1; then
    claude plugin marketplace add "$repo/adapters/claude-code"
    claude plugin install "adlc-framework@adlc-framework-marketplace"
    echo "Claude Code plugin installed (scripts travel inside the plugin)."
  else
    echo "'claude' CLI not found — manual copy into ~/.claude/ :"
    mkdir -p "$HOME/.claude"
    cp -R "$repo/adapters/claude-code/agents"   "$HOME/.claude/" 2>/dev/null || true
    cp -R "$repo/adapters/claude-code/skills"   "$HOME/.claude/" 2>/dev/null || true
    cp -R "$repo/adapters/claude-code/commands" "$HOME/.claude/" 2>/dev/null || true
    echo "Copied agents/skills/commands to ~/.claude/. Restart Claude Code."
    path_hint
  fi
}

copy_into_project() { # src-subdir...
  local a="$1"; shift
  for item in "$@"; do
    cp -R "$repo/adapters/$a/$item" "$target/" && echo "  copied $item -> $target/"
  done
}

case "$host" in
  claude)    install_claude ;;
  cline)     copy_into_project cline .clinerules;             path_hint ;;
  gemini)    copy_into_project gemini .gemini GEMINI.md;      path_hint ;;
  universal) copy_into_project universal AGENTS.md;           path_hint ;;
  all)       install_claude; copy_into_project cline .clinerules; \
             copy_into_project gemini .gemini GEMINI.md; \
             copy_into_project universal AGENTS.md; path_hint ;;
  *) usage ;;
esac

echo ""
echo "Done. Optional Jira: cp .env.example .env (or export JIRA_* vars)."
echo 'Quick start:  in your project, run the ADLC command/workflow with  "add a health endpoint"'
