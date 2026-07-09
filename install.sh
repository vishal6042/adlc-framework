#!/usr/bin/env bash
# ADLC Framework installer (macOS / Linux / Git Bash) — LOCAL, NO MARKETPLACE.
#
#   ./install.sh <host> [target-project-dir]
#     host = claude | cline | gemini | universal | all
#
# Model: the framework stays put in THIS folder (the common place). We add its
# scripts to PATH once, then drop each host's small instruction files into that
# host's USER-GLOBAL config dir, so every project can use it. Nothing is
# published to a marketplace or plugin registry — not even for Claude Code.

set -euo pipefail
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
host="${1:-}"; target="${2:-$PWD}"
scripts_dir="$repo/core/scripts"

usage() { echo "usage: ./install.sh <claude|cline|gemini|universal|all> [target-dir]"; exit 1; }
[ -n "$host" ] || usage
pick_python() { for c in python3 py python; do command -v "$c" >/dev/null 2>&1 && "$c" -c "import sys" >/dev/null 2>&1 && { echo "$c"; return; }; done; echo ""; }
PY="$(pick_python)"; [ -n "$PY" ] || { echo "No working python found (need python3/py)."; exit 1; }

echo "1) Regenerating adapters from core/ ..."; ( cd "$repo" && "$PY" build.py )

# Persist ADLC_HOME + PATH via a small profile snippet (idempotent).
profile="$HOME/.adlc_env"
cat > "$profile" <<EOF
# ADLC Framework — added by install.sh
export ADLC_HOME="$repo/core"
case ":\$PATH:" in *":$scripts_dir:"*) ;; *) export PATH="$scripts_dir:\$PATH";; esac
EOF
for rc in "$HOME/.bashrc" "$HOME/.zshrc" "$HOME/.profile"; do
  [ -f "$rc" ] || continue
  grep -q 'source .*/.adlc_env' "$rc" 2>/dev/null || echo "[ -f \"\$HOME/.adlc_env\" ] && source \"\$HOME/.adlc_env\"" >> "$rc"
done
# shellcheck disable=SC1090
. "$profile"
echo "2) Registered common place: ADLC_HOME=$repo/core ; scripts on PATH (new shells)."

ensure() { mkdir -p "$1"; echo "$1"; }

install_claude() { # user-global Claude config; all projects; no plugin/marketplace
  base="$(ensure "$HOME/.claude")"
  for d in agents skills commands; do
    mkdir -p "$base/$d"; cp -R "$repo/adapters/claude-code/$d/." "$base/$d/"
  done
  echo "  Claude: copied agents/skills/commands into ~/.claude/  (/adlc in every project)"
}
install_cline() {
  rules="$(ensure "$HOME/Documents/Cline/Rules")"; flows="$(ensure "$HOME/Documents/Cline/Workflows")"
  cp -f "$repo/adapters/cline/.clinerules/adlc.md" "$rules/"
  cp -f "$repo/adapters/cline/.clinerules/workflows/adlc.md" "$flows/adlc.md"
  echo "  Cline: installed global rule + workflow under ~/Documents/Cline/"
}
install_gemini() {
  cmds="$(ensure "$HOME/.gemini/commands")"
  cp -f "$repo/adapters/gemini/.gemini/commands/adlc.toml" "$cmds/"
  cp -f "$repo/adapters/gemini/GEMINI.md" "$(ensure "$HOME/.gemini")/"
  echo "  Gemini: installed user command ~/.gemini/commands/adlc.toml"
}
install_universal() { # AGENTS.md is per-repo by nature
  cp -f "$repo/adapters/universal/AGENTS.md" "$target/"
  echo "  Universal: copied AGENTS.md into $target"
}

echo "3) Installing host instruction files (no marketplace)"
case "$host" in
  claude)    install_claude ;;
  cline)     install_cline ;;
  gemini)    install_gemini ;;
  universal) install_universal ;;
  all)       install_claude; install_cline; install_gemini; install_universal ;;
  *) usage ;;
esac

echo ""
echo "Done. Open a new terminal so PATH + ADLC_HOME take effect."
echo "Optional Jira: cp .env.example .env (or export JIRA_* vars)."
echo 'Then in ANY project, run the ADLC command with:  "add a health endpoint"'
