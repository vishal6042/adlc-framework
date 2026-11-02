# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [1.0.0] - 2026-11-02

First production release.

### Fixed
- **Windows PowerShell:** `adlc.ps1` failed to parse at all (invalid `$var:` references and
  a non-ASCII character read as a quote), so `adlc` was broken in every PowerShell window.
  Rewritten with full command parity and an ASCII-only rule enforced by tests.
- **Windows cmd:** `adlc.cmd` launched whatever `bash` was first on PATH — usually WSL's — and
  now runs the PowerShell implementation instead.
- **Jira `pick`:** used `GET /rest/api/3/search`, which Atlassian removed from Jira Cloud in
  2025. Now uses `/rest/api/3/search/jql` (falls back to the old endpoint on 404/410).
- Titles or state values containing `|`, `&`, `/` or `\` corrupted `state.md`/`ticket.md`
  (unescaped `sed` substitution).
- `adlc init` silently overwrote an existing run; it now refuses.
- `adlc ship` could report "nothing to commit" when the commit had actually failed (hooks,
  missing identity) and then mark the run done; it now stops with a clear error.
- `adlc ship` marked the run `done` even when the push failed, so `resume` never retried it.
- `adlc ship` left `state.md` modified after every successful run; the final state is now
  part of the commit.
- Compare URLs printed any credentials embedded in an HTTPS remote (`https://user:token@…`).
- Unknown commands printed help and exited 0; they now exit 2.
- The Claude Code command's `argument-hint` was invalid YAML and the user's request was never
  passed in (`$ARGUMENTS` was missing).
- The installers overwrote `~/.gemini/GEMINI.md` and the project's `AGENTS.md`; they now
  manage only a marked block and keep the rest of the file.
- `install.ps1` rewrote the user PATH as `REG_SZ`, which breaks entries such as
  `%USERPROFILE%\bin`; the type is now preserved.
- `.env` was documented but never read; `JIRA_*`/`ADLC_*` values are now loaded from
  `<project>/.env` and `<framework>/.env` (environment variables still win).
- Docs said a spec template was seeded automatically; it now is (`adlc scaffold`).
- The verify counter could be bumped twice per failure (verifier and orchestrator).

### Added
- `adlc scaffold <KEY> spec|verification`, `adlc doctor`, `adlc version`, `adlc jira get <KEY>`.
- `ship` safety checks: refuses without a `PASS` verification report, refuses protected
  branches (`main`, `master`, …), and refuses to commit files that look like secrets.
- KEY validation (blocks path traversal), git-root anchoring of `docs/adlc/`, GitLab and
  Bitbucket PR links, `ADLC_REMOTE` and `ADLC_DOCS_DIR` settings.
- Jira: HTTPS-only by default, readable error messages, network-error handling, ADF bullet
  lists, project-key validation.
- `install.py`: one cross-platform installer with `--uninstall`, `--dry-run`, `--no-path`,
  `CLAUDE_CONFIG_DIR` support and clean upgrades from v0.3.
- `build.py --check` (detects stale adapters) and `build.py --package` (release zip).
- Prompt hardening: agents may record an approval only after the human gives it, and treat
  ticket/code/tool text as data rather than instructions.
- Test suite (bash, PowerShell, parity, Jira, build, installer) and CI on Linux, macOS
  (bash 3.2) and Windows.
- LICENSE, SECURITY.md, this changelog.

### Changed
- Skills renamed `jira-ticket` → `adlc-jira-ticket` and `spec-design` → `adlc-spec-design`
  so they cannot collide with other skills. The installer removes the old copies.
- Version is read from `core/VERSION` everywhere.

## [0.3.0]
- Shared, no-marketplace install (including Claude Code via `~/.claude`).

## [0.2.0]
- Provider-neutral `core/` with generated multi-host adapters.

## [0.1.0]
- Initial Claude Code plugin.
