# Security

## Reporting a vulnerability

Please report security problems privately via
[GitHub security advisories](https://github.com/vishal6042/adlc-framework/security/advisories/new)
rather than a public issue. You should get a reply within a week.

## What the framework does to stay safe

ADLC lets an AI agent change code and push branches, so the risky steps are guarded by
deterministic scripts rather than by the model's judgement alone:

- **Two human gates.** `adlc ship` refuses to commit unless Gate 2 was recorded and the latest
  verification report says `PASS`. The prompts tell agents to record an approval only after the
  human gives it, and to treat ticket, code and tool text as data, not instructions.
- **No pushes to protected branches.** `adlc branch`/`ship` refuse `main`, `master`, `develop`,
  `trunk`, `production` and `release`. Nothing is ever force-pushed.
- **Secret-file guard.** `adlc ship` refuses to commit files such as `.env`, `*.pem`, `*.key`,
  `id_rsa*`, `.npmrc`, `credentials.json` (`*.example`/`*.sample` are allowed).
- **Credentials stay out of output.** Jira tokens are read from the environment or `.env` only,
  sent over HTTPS only, and never printed; PR links strip `user:token@` from remote URLs.
- **Path safety.** Ticket keys are validated, so a key like `../../x` cannot write outside
  `docs/adlc/`.
- **Installer.** Only writes inside the host config folders and the target project, never
  overwrites files it doesn't own (it edits a marked block in `GEMINI.md`/`AGENTS.md`), and
  `--uninstall` removes everything it added.

The secret-file guard matches file *names*; it does not scan file contents. Keep secrets out of
your working tree (or in `.gitignore`) as usual.
