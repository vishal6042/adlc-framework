#!/usr/bin/env bash
# ADLC Framework installer (macOS / Linux / Git Bash). Thin wrapper around install.py.
#
#   ./install.sh <claude|cline|gemini|universal|all> [target-dir] [--uninstall] [--dry-run] [--no-path]
#
# The framework stays in this folder. Nothing is published to a marketplace.
set -euo pipefail
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

for c in python3 py python; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c "import sys; assert sys.version_info >= (3, 8)" >/dev/null 2>&1; then
    exec "$c" "$repo/install.py" "$@"
  fi
done
echo "ADLC needs Python 3.8+ (tried python3, py, python). Install it and re-run." >&2
exit 1
