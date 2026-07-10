# ADLC Framework
### Agentic Development Life Cycle — from a one-line request to a reviewed pull request, automatically

> A pipeline of specialized AI agents that takes a plain-English feature request through
> **ticket → design spec → human approval → code → tests → verification → human approval → git push** —
> and runs the *same* pipeline on **Claude Code, Cline, Gemini CLI**, or any `AGENTS.md`-aware tool,
> from one provider-neutral source of truth.

---

## 1. The problem

Modern "AI coding" is powerful but **unstructured**:

- A single chat agent jumps straight from a vague ask to code — **no ticket, no design, no approval trail.**
- There's **no gate** for a human to catch a wrong plan *before* code is written (expensive to fix later).
- Tests and verification are ad-hoc; "it works" is asserted, not proven.
- The whole setup is **locked to one tool** (e.g. only Claude Code). Move to Gemini or Cline and you rebuild everything.
- Nothing is **portable** — configs, prompts, and credentials are scattered and machine-specific.

**In one line:** teams get AI speed but lose the discipline of a real Software Development Life Cycle.

---

## 2. The idea: an *Agentic* Development Life Cycle

Take the classic SDLC and assign each stage to a **specialized agent** with its own rules, tools,
and workflow — with **humans kept in the loop at the two decisions that matter** (approve the
design, approve the release).

| Classic SDLC | ADLC agent |
|--------------|-----------|
| Requirement / ticket | `adlc-jira` |
| Design / spec | `adlc-spec` |
| Implementation | `adlc-coder` |
| Testing | `adlc-tester` |
| QA / verification | `adlc-verifier` |
| Release | `adlc-shipper` |
| Project management | `/adlc` orchestrator |

---

## 3. Solution at a glance

```
  "add a /health endpoint that returns {status:'ok'} and a test"
        │
        ▼
 ┌───────────┐   ┌───────────┐   ╔═══════════╗   ┌───────────┐   ┌───────────┐   ┌───────────┐   ╔═══════════╗   ┌───────────┐
 │ 1. Ticket │──▶│ 2. Spec   │──▶║  GATE 1   ║──▶│ 3. Code   │──▶│ 4. Tests  │──▶│ 5. Verify │──▶║  GATE 2   ║──▶│ 6. Ship   │
 │ adlc-jira │   │ adlc-spec │   ║  approve  ║   │adlc-coder │   │adlc-tester│   │ verifier  │   ║ pre-push  ║   │  shipper  │
 └───────────┘   └───────────┘   ╚═══════════╝   └───────────┘   └───────────┘   └─────┬─────┘   ╚═══════════╝   └───────────┘
   ticket.md        spec.md         (human)                                      verification.md    (human)      commit+push+PR URL
                                                       ▲                               │
                                                       └────────── fail: retry ×3 ─────┘
```

- **6 specialist agents** + **1 orchestrator**.
- **2 human approval gates** (design, release).
- **1 automatic retry loop** (verify → fix → re-verify).
- All artifacts saved under the target project's `docs/adlc/<KEY>/` (a full audit trail).

---

## 4. The agents (who does what)

On Claude Code these are **6 isolated sub-agents**, each with a **least-privilege tool set**.
On single-agent hosts the same 6 roles run inline, one at a time.

| # | Agent | Role | Tools (least privilege) | Produces |
|---|-------|------|-------------------------|----------|
| — | **`/adlc`** | **Orchestrator** — runs the pipeline, owns state, enforces gates | delegation + `AskUserQuestion` | `state.md` |
| 1 | `adlc-jira` | Intake → ticket with **Gherkin** acceptance criteria (Jira or local) | `Bash, Read, Write` | `ticket.md` |
| 2 | `adlc-spec` | Design/spec doc carrying the Gherkin contract; **read-only on code** | `Read, Grep, Glob, Write` | `spec.md` |
| 3 | `adlc-coder` | Implement the approved spec | `Read, Edit, Write, Grep, Glob, Bash` | code on a branch |
| 4 | `adlc-tester` | Tests for every acceptance criterion | `Read, Edit, Write, Grep, Glob, Bash` | test files |
| 5 | `adlc-verifier` | Run tests/build; **can't edit code** | `Read, Bash, Grep, Glob` | `verification.md` |
| 6 | `adlc-shipper` | Commit + push; **git only** | `Bash, Read` | commit + PR compare URL |

**Why 6 and not 1?** Each agent gets a *clean context* and *restricted powers* — the spec and
verifier agents literally **cannot modify source**; the shipper can **only run git**. This
containment is the core safety property.

---

## 5. The two human gates

| Gate | When | You see | Choices |
|------|------|---------|---------|
| **Gate 1 — Design** | after the spec | `spec.md` summary + open questions | Approve / Request changes / Abort |
| **Gate 2 — Release** | before the push | branch, diff summary, commit message | Approve & push / Commit locally / Request changes / Abort |

Gate 1 is the highest-leverage moment: fixing the *plan* is far cheaper than fixing code.

---

## 6. Architecture — one source of truth, many hosts

The pipeline's "intelligence" is only four **provider-neutral** things; only the *packaging*
differs per tool. So a generator turns one `core/` into a thin adapter per host.

```
core/  ── SINGLE SOURCE OF TRUTH (edit here) ─────────────────────────────
│  orchestrator.md      the runbook (6 roles, 2 gates, retry loop)
│  stages/*.md          one instruction file per agent
│  skills/*.md          reusable know-how (jira, spec-design, gherkin-criteria, lifecycle)
│  templates/*.md       ticket / spec / state / verification
│  scripts/             DETERMINISTIC engine: adlc (bash), adlc.ps1, adlc.cmd, jira_ticket.py
│
▼  build.py  (generates, never hand-edit adapters) ───────────────────────
│
adapters/
│  claude-code/    .claude-plugin/ + agents/ + skills/ + commands/   (real sub-agents)
│  cline/          .clinerules/ + workflows/adlc.md                   (single-agent workflow)
│  gemini/         .gemini/commands/adlc.toml + GEMINI.md             (TOML slash command)
│  universal/      AGENTS.md                                          (cross-tool: Cursor, Copilot, Codex, Windsurf, Aider, Zed…)
```

**Anti-drift:** edit `core/`, run `build.py`, and every host re-syncs. Adapters are generated
output — you never edit them by hand.

---

## 7. Why it isn't locked to one LLM

Two design moves make it provider-independent:

1. **Roles, not sub-agents, are the portable unit.** Only Claude Code has real sub-agents. The
   runbook defines 6 self-contained roles → mapped to sub-agents on Claude, followed inline on
   single-agent hosts. Same instructions, graceful degradation.
2. **Determinism lives in scripts, reasoning lives in markdown.** Everything mechanical (ticket
   keys, state, Jira calls, branching, commit/push, PR URL) runs in `core/scripts/adlc` and is
   **identical under any model**. The LLM only does the *reasoning* stages (spec, code, tests).

| Host | How you launch it | Config location (shared install) |
|------|-------------------|----------------------------------|
| Claude Code | `/adlc "..."` | `~/.claude/{agents,skills,commands}` |
| Cline | run the `adlc` workflow | `~/Documents/Cline/{Rules,Workflows}` |
| Gemini CLI | `/adlc "..."` | `~/.gemini/commands/adlc.toml` |
| Cursor/Copilot/Codex/… | "run the ADLC pipeline for: …" | `AGENTS.md` in the repo |

---

## 8. The deterministic engine (works with zero LLM)

All mechanical work is a plain script — testable, reproducible, model-independent:

```bash
adlc init "add a health endpoint"     # -> ADLC-001, seeds docs/adlc/ADLC-001/
adlc next-key                          # next local ticket key
adlc jira mode | pick | create ...     # dual-mode ticketing (Jira REST or local)
adlc get-state <KEY> <field>           # read pipeline state
adlc set-state <KEY> <field> <value>   # advance pipeline state
adlc approve <KEY> gate1|gate2         # record a human approval
adlc compare-url <branch>              # PR compare URL from the git remote
adlc ship  <KEY> [--no-push]           # commit (+push) + print compare URL
```

- **Jira** uses the Python **standard library** only (no pip installs) — portable everywhere.
- **Git** only — no dependency on the `gh` CLI.
- Cross-shell: `adlc` (Git Bash / Unix), `adlc.cmd` (cmd/PowerShell), `adlc.ps1` (subset).

---

## 9. Artifacts produced (the audit trail)

Everything lands in the **target project**, never in the framework:

```
docs/adlc/<KEY>/
├── ticket.md          request + Gherkin acceptance criteria    (agent 1)
├── spec.md            design doc (carries the Gherkin contract) reviewed at Gate 1  (agent 2)
├── state.md           pipeline state + gate approvals (resumable)
└── verification.md    test/build results                      (agent 5)
docs/adlc/tickets/<KEY>.md   local-mode ticket mirror
```

`state.md` makes any run **resumable** — re-run with `resume <KEY>` to continue where you stopped.

---

## 10. Portability guarantees

1. **One shared copy, no marketplace** — the framework lives in one place; every project uses it.
2. **No hardcoded paths** — artifacts are written relative to the current project.
3. **No secrets in the repo** — only `.env.example`; real tokens stay in your `.env`/shell.
4. **Cross-OS** — `.gitattributes` forces LF on scripts (a CRLF bash script breaks on Linux);
   scripts are marked executable in git; PowerShell + cmd + bash all covered.
5. **`model: inherit`** — no assumption about the host's default model.
6. **Graceful degradation** — no Jira creds → local tickets; no git remote → local commit; a
   failed push keeps the commit and reports it.

---

## 11. Install — shared, no marketplace (incl. Claude)

```bash
git clone <repo-url> adlc-framework     # keep this folder — it IS the install
cd adlc-framework
./install.ps1 <host> [target]           # Windows PowerShell
./install.sh  <host> [target]           # macOS/Linux/Git Bash
#   host = claude | cline | gemini | universal | all
```

The installer: runs `build.py`, sets `ADLC_HOME` + adds `core/scripts` to PATH once, and copies
the host's instruction files into its **user-global** config. **No plugin, no marketplace —
even for Claude.** Open a new terminal afterward so PATH takes effect.

**Optional Jira:** copy `.env.example` → `.env`, or export `JIRA_BASE_URL`, `JIRA_EMAIL`,
`JIRA_API_TOKEN`, `JIRA_PROJECT_KEY`. Without them, the pipeline uses local ticket files.

---

## 12. Usage — step by step

1. Open your project and run `/adlc "add a /health endpoint and a test"`.
2. **Agent 1** creates the ticket → `docs/adlc/ADLC-001/`.
3. **Agent 2** writes `spec.md`.
4. **🚦 Gate 1** — you read the spec and Approve.
5. **Agents 3→4→5** implement, test, and verify (auto-retry on failure).
6. **🚦 Gate 2** — you Approve the push.
7. **Agent 6** commits, pushes, prints a **PR compare URL** — you open the PR.
8. Resume anytime with `/adlc resume ADLC-001`; check `/adlc status ADLC-001`.

---

## 13. Worked example (what you'd see)

```
> /adlc "add a /health endpoint that returns {status:'ok'} and a test"

[1/6 intake ] created ADLC-001  (local mode) — docs/adlc/ADLC-001/ticket.md
[2/6 spec   ] wrote docs/adlc/ADLC-001/spec.md
     GATE 1 → review the spec.  [Approve] [Request changes] [Abort]
> Approve
[3/6 code   ] branch adlc/ADLC-001-add-health-endpoint ; edited app/main.py
[4/6 tests  ] added tests/test_health.py (1 test → scenario "Health check returns ok")
[5/6 verify ] PASS — pytest: 1 passed in 0.12s
     GATE 2 → push?  [Approve & push] [Commit locally] [Request changes] [Abort]
> Approve & push
[6/6 ship   ] committed 8f2c1a9 ; pushed adlc/ADLC-001-add-health-endpoint
     PR: https://github.com/you/my-app/compare/adlc/ADLC-001-add-health-endpoint?expand=1
```

---

## 14. Technology stack

| Layer | Tech |
|-------|------|
| Agents / skills / commands | Markdown with YAML frontmatter |
| Deterministic engine | Bash + Windows `.cmd`/`.ps1` shims |
| Jira integration | Python **standard library** (`urllib`) — Jira Cloud REST v3 |
| VCS | Git (branch / commit / push / compare URL) |
| Generator | `build.py` (Python 3, stdlib) |
| Hosts | Claude Code, Cline, Gemini CLI, `AGENTS.md` ecosystem |
| Config | Env vars (`JIRA_*`, `ADLC_HOME`), `.env` (gitignored) |

---

## 15. Key design decisions

- **Gherkin acceptance criteria** — every criterion is a `Given/When/Then` scenario, authored once
  at intake, frozen into the spec, and mapped one-to-one to a test. Unambiguous, testable, traceable.
- **Human-in-the-loop at 2 gates**, not 0 and not every step — safety without friction.
- **Least-privilege tools per agent** — containment by construction.
- **Deterministic core in scripts** — reproducible, cheap, and model-independent.
- **Generate adapters from one core** — no drift across hosts.
- **Plain git, no `gh`** — fewer dependencies; PR opened via a printed compare URL.
- **Local-first** — runs fully with no Jira and no remote.

---

## 16. Roadmap / out of scope (today)

- Automated GitHub **PR creation** (currently prints the compare URL).
- **MCP server** wrapping `core/scripts` for MCP-capable hosts (structure is ready).
- Dedicated **Cursor/Windsurf** adapters (covered via `AGENTS.md` for now).
- **CI wiring** (run the verifier on push).

---

## 17. Repository structure

```
adlc-framework/
├── core/              # single source of truth (edit here)
│   ├── orchestrator.md
│   ├── stages/{1-intake,2-spec,3-code,4-tests,5-verify,6-ship}.md
│   ├── skills/{adlc-workflow,jira-ticket,spec-design,gherkin-criteria}.md
│   ├── templates/{ticket,spec,state,verification}.md
│   └── scripts/{adlc, adlc.ps1, adlc.cmd, jira_ticket.py, lib.sh}
├── adapters/          # GENERATED by build.py — do not hand-edit
│   ├── claude-code/  cline/  gemini/  universal/
├── build.py           # regenerates adapters from core/
├── install.sh / install.ps1
├── .env.example  .gitattributes  README.md
```

---

## Appendix — Suggested slide outline (for the deck)

| Slide | Title | Key content |
|-------|-------|-------------|
| 1 | Title | "ADLC — Agentic Development Life Cycle" + one-line pitch |
| 2 | The problem | §1 — AI speed, no SDLC discipline |
| 3 | The idea | §2 — SDLC stage → agent table |
| 4 | Solution at a glance | §3 — the pipeline diagram |
| 5 | Meet the agents | §4 — agent table + "why 6" |
| 6 | Human-in-the-loop | §5 — the two gates |
| 7 | Architecture | §6 — core + generated adapters diagram |
| 8 | Not locked to one LLM | §7 — roles-not-subagents + host table |
| 9 | Deterministic engine | §8 — the `adlc` commands |
| 10 | Audit trail | §9 — artifacts produced |
| 11 | Portability | §10 — the 6 guarantees |
| 12 | Install & use | §11–12 — shared no-marketplace install + steps |
| 13 | Demo | §13 — the worked example transcript |
| 14 | Tech stack | §14 |
| 15 | Design decisions | §15 |
| 16 | Roadmap | §16 |
| 17 | Q&A | — |
