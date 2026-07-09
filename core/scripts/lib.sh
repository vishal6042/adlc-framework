#!/usr/bin/env bash
# ADLC shared shell helpers. Sourced by `adlc`. Provider-independent.
# No Claude/host specifics here — pure git + POSIX tooling.

set -euo pipefail

# --- locations -------------------------------------------------------------
# Directory this library lives in (…/core/scripts). Templates sit alongside.
adlc_script_dir() { cd "$(dirname "${BASH_SOURCE[0]}")" && pwd; }
adlc_templates_dir() { echo "$(adlc_script_dir)/../templates"; }

# Artifacts always live under the *current project* (cwd), never the framework.
adlc_dir()   { echo "docs/adlc"; }
key_dir()    { echo "docs/adlc/$1"; }
state_file() { echo "docs/adlc/$1/state.md"; }

# --- python interpreter detection -----------------------------------------
# Sidesteps the Windows Store `python`/`python3` stubs by verifying output.
adlc_python() {
  local c
  for c in python3 py python; do
    if command -v "$c" >/dev/null 2>&1 && "$c" -c "import sys" >/dev/null 2>&1; then
      echo "$c"; return 0
    fi
  done
  return 1
}

# --- state.md get/set ------------------------------------------------------
# State lines look like:  - <field>: <value>
get_state() { # key field
  local sf; sf="$(state_file "$1")"
  [ -f "$sf" ] || { echo ""; return 0; }
  sed -n "s/^- $2:[[:space:]]*//p" "$sf" | head -n1
}

set_state() { # key field value
  local sf; sf="$(state_file "$1")"
  [ -f "$sf" ] || die "no state file for $1 (run: adlc init)"
  if grep -q "^- $2:" "$sf"; then
    # portable in-place edit (BSD/GNU sed differ on -i; use a temp file)
    sed "s|^- $2:.*|- $2: $3|" "$sf" > "$sf.tmp" && mv "$sf.tmp" "$sf"
  else
    printf -- "- %s: %s\n" "$2" "$3" >> "$sf"
  fi
}

log_state() { # key message
  local sf; sf="$(state_file "$1")"
  printf -- "- %s %s\n" "$(date +%Y-%m-%d)" "$2" >> "$sf"
}

# --- misc ------------------------------------------------------------------
slugify() { # text -> kebab, max ~6 words
  echo "$1" | tr '[:upper:]' '[:lower:]' \
    | sed -E 's/[^a-z0-9]+/-/g; s/^-+|-+$//g' \
    | cut -d- -f1-6
}

die() { echo "adlc: $*" >&2; exit 1; }
