# ADLC Framework

**Agentic Development Life Cycle** for Claude Code — a pipeline of specialized agents that
takes a plain-English request all the way to a pushed branch, pausing only for the two
approvals that matter.

```
/adlc "add a health endpoint"
      │
      ▼
┌───────────┐   ┌───────────┐   ╔═══════════╗   ┌───────────┐   ┌───────────┐   ┌───────────┐   ╔═══════════╗   ┌───────────┐
│ 1. Jira   │──▶│ 2. Spec   │──▶║  GATE 1   ║──▶│ 3. Code   │──▶│ 4. Tests  │──▶│ 5. Verify │──▶║  GATE 2   ║──▶│ 6. Ship   │
│  ticket   │   │  design   │   ║ approve   ║   │           │   │           │   │  run test │   ║ pre-push  ║   │ git push  │
└───────────┘   └───────────┘   ╚═══════════╝   └───────────┘   └───────────┘   └─────┬─────┘   ╚═══════════╝   └───────────┘
 adlc-jira       adlc-spec        (you)          adlc-coder      adlc-tester    adlc-verifier      (you)         adlc-shipper
                                                      ▲                               │
                                                      └────────── fail: loop ─────────┘
```

Each stage is a **separate subagent** with its own least-privilege tools, rules, and
workflow. The `/adlc` **orchestrator** is the only thing that talks to you: it runs the
agents in sequence, carries artifacts between them, enforces the two human gates, and keeps
a resumable state file.

## What it produces

Everything lands in the **target project** (not in this plugin), under `docs/adlc/<KEY>/`:

| File | Written by | Purpose |
|------|-----------|---------|
| `ticket.md` | adlc-jira | Ticket details + acceptance criteria |
| `spec.md` | adlc-spec | Design doc reviewed at **Gate 1** |
| `state.md` | orchestrator | Pipeline state + which gates are approved (makes runs resumable) |
| `verification.md` | adlc-verifier | Test/build results |

## Install

### Option A — as a plugin (recommended, portable)

```bash
git clone <this-repo-url> adlc-framework
cd adlc-framework
./install.sh          # macOS/Linux/Git Bash
# or, on Windows PowerShell:
./install.ps1
```

The installer registers this repo as a local plugin marketplace and installs the plugin.
Equivalent manual commands:

```bash
claude plugin marketplace add /path/to/adlc-framework
claude plugin install adlc-framework@adlc-framework-marketplace
```

### Option B — manual copy

If you don't want to use the plugin system, copy the component folders into your user config:

```bash
cp -R agents skills commands ~/.claude/
```

(The install scripts fall back to this automatically if the `claude` CLI isn't found.)

## Configure (optional)

Jira is **optional**. With no config, the framework runs in **local-ticket mode** and writes
`docs/adlc/tickets/<KEY>.md` instead of calling Jira — the rest of the pipeline is identical.

To use real Jira Cloud, copy `.env.example` to `.env` and fill it in, or export the vars:

```bash
export JIRA_BASE_URL="https://your-domain.atlassian.net"
export JIRA_EMAIL="you@example.com"
export JIRA_API_TOKEN="..."        # https://id.atlassian.com/manage-profile/security/api-tokens
export JIRA_PROJECT_KEY="ADLC"
```

## Use

From inside any git project:

```
/adlc "let users reset their password by email"
```

Then follow the two prompts (approve the spec, approve the push). Re-run `/adlc` at any time
to resume an in-progress ticket from `state.md`.

## Portability

- **One git repo = the whole framework.** Clone it on any machine, run `install.*`, done.
- **No hardcoded paths** — artifacts are written relative to the current project.
- **No secrets in the repo** — only `.env.example`; real tokens stay in your `.env`/shell.
- **Cross-platform** — uses only `git` + `curl` (no `gh` CLI dependency); commands are given
  in both Bash and PowerShell forms.
- **`model: inherit`** on every agent — no assumption about the host's default model.
- **Graceful degradation** — with no Jira creds and no git remote, it still runs end-to-end
  (local tickets, local branch).

## Components

```
adlc-framework/
├── .claude-plugin/{plugin.json, marketplace.json}
├── commands/adlc.md                 # orchestrator (/adlc)
├── agents/adlc-{jira,spec,coder,tester,verifier,shipper}.md
└── skills/{jira-ticket,spec-design,adlc-workflow}/SKILL.md
```

## Out of scope (for now)

- Automated GitHub **PR creation** — the shipper pushes and prints a ready-to-click compare
  URL; you open the PR. (Add `gh` or a GitHub MCP later to automate this.)
- CI wiring and MCP-based Jira/GitHub (the Jira skill is written so these can drop in).
