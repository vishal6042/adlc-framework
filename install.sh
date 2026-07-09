#!/usr/bin/env bash
# ADLC Framework installer (macOS / Linux / Git Bash)
# Registers this repo as a local plugin marketplace and installs the plugin,
# so /adlc and the ADLC agents/skills are available in every project.
#
# Usage:  ./install.sh
# Re-runnable (idempotent).

set -euo pipefail
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "ADLC Framework — installing from: $repo"

if ! command -v claude >/dev/null 2>&1; then
  echo "WARNING: the 'claude' CLI was not found on PATH."
  echo "Falling back to manual copy into ~/.claude/ ..."
  dest="$HOME/.claude"
  for d in agents skills commands; do
    if [ -d "$repo/$d" ]; then
      mkdir -p "$dest/$d"
      cp -R "$repo/$d/." "$dest/$d/"
      echo "  copied $d -> ~/.claude/$d"
    fi
  done
  echo "Manual install complete. Restart Claude Code to pick up the components."
  exit 0
fi

# Preferred path: install as a plugin from this repo-as-marketplace.
claude plugin marketplace add "$repo"
claude plugin install "adlc-framework@adlc-framework-marketplace"

echo ""
echo "Installed. Next steps:"
echo "  1. (optional) cp .env.example .env and add your Jira creds, or export JIRA_* vars."
echo '  2. Open any project and run:  /adlc "add a health endpoint"'
