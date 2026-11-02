#!/usr/bin/env bash
# ADLC shared shell helpers. Sourced by `adlc`. Provider-independent.
# Pure git + POSIX tooling. Must stay compatible with bash 3.2 (macOS /bin/bash):
# no mapfile, no ${var,,}, no associative arrays, no `local -n`.

set -euo pipefail

# --- locations -------------------------------------------------------------
ADLC_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
adlc_script_dir()    { echo "$ADLC_LIB_DIR"; }
adlc_templates_dir() { echo "$ADLC_LIB_DIR/../templates"; }
adlc_version()       { tr -d '[:space:]' < "$ADLC_LIB_DIR/../VERSION" 2>/dev/null || echo unknown; }

die()  { echo "adlc: $*" >&2; exit 1; }
warn() { echo "adlc: $*" >&2; }

# Artifacts live in the *current project*, never in the framework. Anchor them at
# the git top-level so running from a subdirectory doesn't scatter runs around.
# Override with ADLC_DOCS_DIR.
adlc_project_root() {
  git rev-parse --show-toplevel 2>/dev/null || pwd
}
adlc_dir() {
  if [ -n "${ADLC_DOCS_DIR:-}" ]; then echo "$ADLC_DOCS_DIR"; else echo "$(adlc_project_root)/docs/adlc"; fi
}
key_dir()    { echo "$(adlc_dir)/$1"; }
state_file() { echo "$(adlc_dir)/$1/state.md"; }

# --- validation --------------------------------------------------------------
# KEYs become directory names and branch names, so keep them strict
# (also blocks path traversal such as "../../etc").
ADLC_KEY_RE='^[A-Za-z][A-Za-z0-9_]*-[0-9]+$'
ADLC_FIELD_RE='^[a-z][a-z0-9_]*$'
ADLC_DOTENV_RE='^[[:space:]]*(JIRA_[A-Z0-9_]+|ADLC_[A-Z0-9_]+)[[:space:]]*=(.*)$'
valid_key()   { [[ "$1" =~ $ADLC_KEY_RE ]]; }
require_key() { valid_key "${1:-}" || die "invalid KEY '${1:-}' (expected e.g. ADLC-001 or PROJ-123)"; }
valid_field() { [[ "$1" =~ $ADLC_FIELD_RE ]]; }
require_run() { # key -> the run must exist
  require_key "$1"
  [ -f "$(state_file "$1")" ] || die "no ADLC run for $1 (expected $(state_file "$1")); start one with: adlc init \"<request>\""
}
one_line() { printf '%s' "$1" | tr '\r\n\t' '   '; }

# --- optional .env -----------------------------------------------------------
# Read JIRA_* / ADLC_* keys from <project>/.env, then <framework>/.env. Never
# overrides variables already set in the environment. Never evaluates the file.
adlc_load_dotenv() {
  local f line k v isset
  for f in "$(adlc_project_root)/.env" "$ADLC_LIB_DIR/../../.env"; do
    [ -f "$f" ] || continue
    while IFS= read -r line || [ -n "$line" ]; do
      line="${line%$'\r'}"
      line="${line#export }"
      [[ "$line" =~ $ADLC_DOTENV_RE ]] || continue
      k="${BASH_REMATCH[1]}"; v="${BASH_REMATCH[2]}"
      v="${v#"${v%%[![:space:]]*}"}"; v="${v%"${v##*[![:space:]]}"}"   # trim
      case "$v" in \"*\") v="${v#\"}"; v="${v%\"}" ;; \'*\') v="${v#\'}"; v="${v%\'}" ;; esac
      # $k matched a strict [A-Z0-9_] pattern above, so this eval is safe.
      eval "isset=\${$k+x}"
      if [ -z "$isset" ]; then export "$k=$v"; fi
    done < "$f"
  done
}

# --- python interpreter detection -----------------------------------------
# Skips the Windows Store `python`/`python3` stubs by actually running them.
adlc_python() {
  local c
  for c in python3 py python; do
    if command -v "$c" >/dev/null 2>&1 && "$c" -c "import sys; assert sys.version_info >= (3, 8)" >/dev/null 2>&1; then
      echo "$c"; return 0
    fi
  done
  return 1
}

# --- templates -------------------------------------------------------------
# render_template <file> <placeholder> <value> [<placeholder> <value> ...]
# Pure bash substitution: safe for values containing | & / \ (unlike sed).
render_template() {
  local tpl; tpl="$(cat "$1")"; shift
  while [ $# -ge 2 ]; do
    tpl=${tpl//"$1"/"$2"}
    shift 2
  done
  printf '%s\n' "$tpl"
}

# --- state.md get/set ------------------------------------------------------
# Field lines look like "- <field>: <value>" and sit above "## Log".
get_state() { # key field
  local sf; sf="$(state_file "$1")"
  valid_field "$2" || die "invalid state field '$2'"
  [ -f "$sf" ] || { echo ""; return 0; }
  ADLC_F="$2" awk '
    BEGIN { p = "- " ENVIRON["ADLC_F"] ":" }
    /^## / { exit }
    { sub(/\r$/, "") }
    index($0, p) == 1 { v = substr($0, length(p) + 1); sub(/^[ \t]+/, "", v); print v; exit }
  ' "$sf"
}

set_state() { # key field value
  local sf; sf="$(state_file "$1")"
  [ -f "$sf" ] || die "no state file for $1 (run: adlc init)"
  valid_field "$2" || die "invalid state field '$2' (use lowercase letters, digits, _)"
  # awk, not sed: values may contain | & / \ without breaking anything.
  ADLC_F="$2" ADLC_V="$(one_line "$3")" awk '
    BEGIN { p = "- " ENVIRON["ADLC_F"] ":"; v = ENVIRON["ADLC_V"] }
    NR == FNR {                        # pass 1: find the field, or the last field line
      if ($0 ~ /^## /) hdr = 1
      if (!hdr && index($0, p) == 1) found = FNR
      if (!hdr && $0 ~ /^- [a-z0-9_]+:/) last = FNR
      next
    }
    found && FNR == found { print p " " v; next }
    { print }
    !found && FNR == last { print p " " v; added = 1 }
    END { if (!found && !added) print p " " v }
  ' "$sf" "$sf" > "$sf.tmp.$$" && mv "$sf.tmp.$$" "$sf"
}

log_state() { # key message
  printf -- "- %s %s\n" "$(date +%Y-%m-%d)" "$(one_line "$2")" >> "$(state_file "$1")"
}

# --- git -------------------------------------------------------------------
require_git_repo() {
  git rev-parse --is-inside-work-tree >/dev/null 2>&1 || die "not inside a git repository (run: git init)"
}
current_branch() { git symbolic-ref --quiet --short HEAD 2>/dev/null || true; }
is_protected_branch() {
  case "$1" in main|master|develop|trunk|production|release) return 0 ;; *) return 1 ;; esac
}
switch_to_branch() { # branch: check it out, creating it from HEAD if needed
  local b="$1"
  git check-ref-format --branch "$b" >/dev/null 2>&1 || die "invalid branch name '$b'"
  is_protected_branch "$b" && die "refusing to use protected branch '$b' as a feature branch"
  [ "$(current_branch)" = "$b" ] && return 0
  if git show-ref --verify --quiet "refs/heads/$b"; then
    git checkout -q "$b" -- || die "could not switch to $b (uncommitted changes in the way?)"
  else
    git checkout -q -b "$b" || die "could not create branch $b"
  fi
}

# --- misc ------------------------------------------------------------------
slugify() { # text -> kebab-case, max 6 words / 50 chars, never empty
  local s
  s="$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]' \
      | sed -E 's/[^a-z0-9]+/-/g; s/^-+//; s/-+$//' \
      | cut -d- -f1-6 | cut -c1-50 | sed -E 's/-+$//')"
  [ -n "$s" ] || s="change"
  printf '%s\n' "$s"
}
