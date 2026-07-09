# AGENTS.md — ADLC Framework

This repository supports the **Agentic Development Life Cycle (ADLC)**: a request is taken from ticket to pushed branch through six stages with two human approval gates. Any AGENTS.md-aware agent can run it by following the runbook below.

## Setup
- Put the framework's `scripts/` directory on your PATH (so `adlc` resolves), or call `$ADLC_HOME/scripts/adlc`.
- Optional Jira: set `JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`, `JIRA_PROJECT_KEY`. Without them the pipeline uses local ticket files.
- Artifacts are written under `docs/adlc/<KEY>/`.

---

# ADLC Orchestrator (runbook)

Drive a feature from request to pushed branch by running six roles in sequence, enforcing two
human approval gates, and keeping a resumable state file. You are the only component that talks
to the user.

**Host adaptation:** if your host has real sub-agents (e.g. Claude Code), delegate each stage to
the matching `adlc-*` agent for context isolation. If it is single-agent (Cline, Gemini CLI,
most others), perform each role **inline, one at a time**, following the corresponding
`stages/<n>-*.md`. Either way the instructions and gates are identical.

**Deterministic ops:** everything mechanical is the `adlc` script — key generation, state
read/write, Jira calls, branch, commit, push, compare URL. Never reimplement these. The
reasoning stages (spec, code, tests) are yours.

## Input
`<request>` is one of:
- a plain-English feature request → start a new run;
- `resume <KEY>` → continue from `docs/adlc/<KEY>/state.md`;
- `status <KEY>` → run `adlc status <KEY>` and stop.

## Resume first
Before starting, if a KEY is known, read state: `adlc get-state <KEY> current_stage`. Continue
from that stage — never re-run a completed stage unless a gate sent it back or the user asks.

## Pipeline
| Stage | Role | Do after it returns |
|-------|------|---------------------|
| 1 intake | `stages/1-intake.md` | ticket exists; state → spec |
| 2 spec | `stages/2-spec.md` | persist `spec.md`; **run GATE 1** |
| 3 code | `stages/3-code.md` | code on the feature branch |
| 4 tests | `stages/4-tests.md` | tests written |
| 5 verify | `stages/5-verify.md` | PASS → continue; FAIL → retry loop |
| 6 ship | `stages/6-ship.md` | **run GATE 2 first**, then `adlc ship <KEY>` |

After every stage, the role updates `current_stage`; append a line to the `## Log` in `state.md`.

## GATE 1 — approve the spec (after stage 2)
Do not proceed to code until the user approves. Present the spec summary + the path
`docs/adlc/<KEY>/spec.md` + any open questions, and ask: **Approve / Request changes / Abort**.
- Approve → `adlc approve <KEY> gate1`, then continue to stage 3.
- Request changes → capture feedback, re-run stage 2, gate again.
- Abort → set `current_stage` to `done`, log, stop.

## GATE 2 — approve the push (before stage 6)
After verification PASSES, do not push until the user approves. Show the branch, the diff
summary, and the proposed commit message. Ask: **Approve & push / Request changes (→ stage 3) /
Commit locally only / Abort**.
- Approve → `adlc approve <KEY> gate2`, then `adlc ship <KEY>`.
- Commit locally only → `adlc approve <KEY> gate2` then `adlc ship <KEY> --no-push`.

> Headless/CI hosts (no interactive user): halt at each gate and require re-invocation with the
> approval already recorded (`adlc approve <KEY> gate1|gate2`) before continuing.

## Verify → code retry loop
On FAIL from stage 5: increment `verify_attempts`, send the failure back to stage 3, then re-run
stages 4–5. After **3** failed attempts, stop and surface the blocker to the user.

## Degradation
- No Jira creds → local ticket mode (automatic). Note it and continue.
- No git remote → `adlc ship` commits locally and says "not pushed". That is success.

## Finish
Print a concise summary: KEY + title, branch, commit SHA, pushed?+compare URL, links to
`ticket.md`/`spec.md`/`verification.md`, and the recorded gate decisions.



---

# Stage playbooks


# Stage 1 — Intake (ticket)

Turn the request into a tracked ticket with a stable **KEY** and clear, testable **acceptance
criteria**. Works with or without a real Jira instance.

## Rules
- All mechanical work goes through the `adlc` script — do not reimplement key generation,
  state, or Jira calls by hand.
- Jira vs local is automatic (`adlc jira mode`). Never echo secrets; creds come from env only.
- Do NOT design or write code here. Stop once the ticket exists.
- Acceptance criteria must be specific and testable. If the request is ambiguous, write the most
  reasonable criteria and note the ambiguity under `## Notes`.

## Workflow
1. Detect mode: `adlc jira mode` → `jira` or `local`.
2. Get a KEY + seed the run:
   - **local:** `adlc init "<request>"` prints a new KEY (e.g. `ADLC-001`) and creates
     `docs/adlc/<KEY>/` with `state.md` + `ticket.md`.
   - **jira:** create/pick the issue → `adlc jira create "<summary>" "<description>"` (prints the
     KEY) or `adlc jira pick` (choose one), then `adlc init "<request>" <KEY>` to seed the
     local run dir under the real key.
3. Edit `docs/adlc/<KEY>/ticket.md`: fill the Description and 3–6 acceptance criteria.
4. Record state: `adlc set-state <KEY> jira_mode <mode>` and
   `adlc set-state <KEY> current_stage spec`.

## Output (hand back to the orchestrator)
- The **KEY**, path to `ticket.md`, the **mode**, and the acceptance-criteria list.


# Stage 2 — Design / Spec  (→ GATE 1)

Turn the ticket into a reviewable design document. Do NOT write implementation code — a human
must approve this spec (Gate 1) before coding starts.

## Rules
- **Ground the design in the real codebase**: search and read first, then reference concrete
  files/functions/patterns to reuse. Do not invent structure or propose new code where something
  suitable already exists.
- **Traceability:** every acceptance criterion in `ticket.md` maps to at least one row in the
  spec's Test plan. Flag any criterion you cannot test and why.
- Prefer the minimal change; justify each new file in one line.
- Write ONLY `docs/adlc/<KEY>/spec.md` — touch no source files.
- Keep it to about one screen. Put genuine decisions under `## Open questions`.

## Workflow
1. Read `docs/adlc/<KEY>/ticket.md` (request + acceptance criteria).
2. Explore the target codebase for structure, conventions, and reuse candidates.
3. Write `docs/adlc/<KEY>/spec.md` following the template in
   `docs/adlc/<KEY>/` seed / the spec template (sections: Problem, Goals/Non-goals, Approach,
   Files to change, Test plan, Risks/rollback, Open questions).
4. Verify the Test-plan table covers every acceptance criterion.
5. `adlc set-state <KEY> current_stage code` is done by the orchestrator only *after* Gate 1.

## Output (hand back to the orchestrator)
- Path to `spec.md`, a 2–3 sentence summary of the approach (for the Gate 1 prompt), and any
  open questions for the human.


# Stage 3 — Implement

Write the code for an already-approved spec.

## Preconditions
- Gate 1 must be approved: `adlc get-state <KEY> gate1_spec_approved` must be `true`.
  If not, STOP and report — never write code past an unapproved spec.

## Rules
- Implement exactly what `docs/adlc/<KEY>/spec.md` describes — no scope creep. If the spec is
  wrong or insufficient, STOP and report rather than redesigning on the fly.
- **Match the surrounding code**: naming, structure, error handling, imports, comment density.
  Read neighboring files before writing.
- Keep the diff minimal; reuse the utilities the spec identified.
- Work on the feature branch: `adlc branch <KEY>` checks it out (creating it if needed).
- Do NOT commit or push — that's stage 6, behind Gate 2. Do NOT write tests — that's stage 4
  (during a fix cycle you may adjust code to satisfy existing tests).

## Workflow
1. Confirm Gate 1, then `adlc branch <KEY>`.
2. Read `spec.md` and the files it lists; implement file by file in house style.
3. Fix cycle (verification failed): read `docs/adlc/<KEY>/verification.md` and make the smallest
   change that addresses the failure.
4. `adlc set-state <KEY> current_stage tests`.

## Output (hand back to the orchestrator)
- Files created/modified with a one-line reason each; the active branch; anything that deviated
  from the spec (should be nothing — flag loudly if so).


# Stage 4 — Tests

Write tests that prove the acceptance criteria hold.

## Rules
- Cover the **Test plan** in `docs/adlc/<KEY>/spec.md`; every acceptance criterion gets at least
  one test.
- Use the project's **existing** test framework and layout — detect it, don't impose a new one
  (`pytest`/`tests/`, `jest`/`vitest`/`*.test.*`, `go test`, `cargo test`, JUnit, …). Match the
  file locations and naming already present.
- Write meaningful assertions (behavior, edge cases, error paths) — not `assert True`.
- Don't modify product code to make tests pass; if a test reveals a bug, report it for stage 3.
  You may add small fixtures/helpers.

## Workflow
1. Read `spec.md` (Test plan) and `ticket.md` (acceptance criteria).
2. Detect the framework and existing conventions (search config + sample tests).
3. Write tests in the right location with matching style.
4. Optionally do a quick syntax/collection check of just the new tests.
5. `adlc set-state <KEY> current_stage verify`.

## Output (hand back to the orchestrator)
- Test files created/modified; a criterion → test mapping (show full coverage); any criterion that
  can only be verified manually, and why.


# Stage 5 — Verify

Run the checks and report the truth. Never claim PASS without having actually run something and
seen it succeed.

## Rules
- **Auto-detect** how the project verifies itself, in priority order:
  1. A project-specific verify/run command if one exists — prefer it.
  2. Test runner: `pytest`/`python -m pytest`, `npm|pnpm|yarn test`, `go test ./...`,
     `cargo test`, `mvn test`, `make test`, …
  3. Build/typecheck/lint if fast: `npm run build`, `tsc --noEmit`, `ruff`/`flake8`, …
- Run the narrowest relevant checks first (the new tests), then a broader run if quick.
- Report failures **verbatim** — copy the real error output into the report. If you cannot find
  any way to run tests, say so explicitly (do NOT PASS). Do not edit product code.

## Workflow
1. Read `spec.md` to know what "done" means and which tests matter.
2. Detect the toolchain (look for `package.json`, `pyproject.toml`, `go.mod`, `Makefile`, …).
3. Run the tests (and a quick build/lint if fast); capture stdout/stderr and exit codes.
4. Write `docs/adlc/<KEY>/verification.md` (Result: PASS|FAIL, exact commands, output excerpts,
   coverage-vs-criteria). Bump the attempt counter:
   `adlc set-state <KEY> verify_attempts <n>`.
5. On PASS: `adlc set-state <KEY> current_stage ship`. On FAIL: leave stage at `verify`; the
   orchestrator loops to stage 3.

## Output (hand back to the orchestrator)
- **PASS** or **FAIL** (unambiguous); the exact commands run; on FAIL the specific failing
  tests/errors so stage 3 can fix them.


# Stage 6 — Ship  (after GATE 2)

Commit and push — but only after the human approved at Gate 2.

## Preconditions (verify first; if either fails, STOP and report)
- `adlc get-state <KEY> gate2_push_approved` is `true`.
- The latest `docs/adlc/<KEY>/verification.md` says **PASS**.

## Rules
- Plain **git only** (no `gh`). Never force-push. Never touch `main`/`master` directly.
- The `adlc ship` command does the mechanical part: checks Gate 2, checks out the branch,
  `git add -A`, commits (`<KEY>: <title>` + `Refs: spec.md`), pushes if a remote exists, and
  prints the compare URL. With no remote it commits locally and says so — that is success.
- Do not commit secrets or `.env`.

## Workflow
1. Confirm preconditions.
2. Run `adlc ship <KEY>` (add `--no-push` if the user chose "commit locally only").
3. Report the commit SHA, whether it pushed, and the compare URL.

## Output (hand back to the orchestrator)
- Commit SHA + message; pushed (and to which branch) or local-only; the **compare URL** for
  opening the PR manually (if a GitHub remote exists).



---

# Reference skills


# ADLC lifecycle rules

Single source of truth for how an ADLC run progresses. The orchestrator and every stage follow it.

## Artifacts (in the target project, never the framework)
```
docs/adlc/<KEY>/
├── state.md          # the state machine below (managed via `adlc get-state/set-state`)
├── ticket.md         # stage 1
├── spec.md           # stage 2 (reviewed at Gate 1)
└── verification.md   # stage 5
docs/adlc/tickets/<KEY>.md   # local-mode ticket mirror
```

## Stage order
`intake → spec → [GATE 1] → code → tests → verify → [GATE 2] → ship`

| Stage | Advances when |
|-------|---------------|
| intake | `ticket.md` has acceptance criteria |
| spec | `spec.md` written → Gate 1 |
| code | change implemented on the feature branch |
| tests | tests written per the spec Test plan |
| verify | `verification.md` = PASS (else loop to code) |
| ship | Gate 2 approved, then commit + push |

## The two gates (never skip)
- **GATE 1 — after spec:** human approves `spec.md` before any code. Approve / Request changes / Abort.
- **GATE 2 — before push:** human approves before anything is pushed. Approve & push / Request
  changes / Commit locally only / Abort.

Record approvals with `adlc approve <KEY> gate1|gate2`.

## state.md fields
`key · title · created · branch · jira_mode(local|jira) · current_stage(intake|spec|code|tests|verify|ship|done) · gate1_spec_approved · gate2_push_approved · verify_attempts` plus a `## Log`.

## Resume logic
Re-running the pipeline reads `current_stage` first and continues from there. Never re-run a
completed stage unless a gate sent it back or the user asks. Update `current_stage` + append to
`## Log` after every stage.

## Verify → code retry loop
FAIL → bump `verify_attempts`, fix in stage 3, re-run tests + verify. After 3 failures, stop and
surface the blocker to the human.

## Degradation
No Jira creds → local tickets. No remote → local commit only. Always progress as far as possible
rather than hard-failing.


# jira-ticket

Turn a request into a tracked ticket with a **key** and explicit **acceptance criteria**. All the
mechanics are in the `adlc` script; this explains the intent and the `ticket.md` shape.

## Mode
`adlc jira mode` → `jira` (all three `JIRA_*` vars set) or `local`. Record it with
`adlc set-state <KEY> jira_mode <mode>`.

## Pick vs create
If the user referenced a key, **pick** it; otherwise **create**.
- **Jira mode:**
  - pick: `adlc jira pick` lists open issues (`KEY  status  summary`); choose one.
  - create: `adlc jira create "<summary>" "<description>"` prints the new KEY. Put acceptance
    criteria into the description (one bullet per criterion).
  - Then `adlc init "<request>" <KEY>` seeds the local run dir under that real key.
- **Local mode:** `adlc init "<request>"` generates the next `ADLC-00N` key and seeds everything.

## ticket.md shape (both modes)
Sections: title line `# <KEY>: <summary>`, a metadata block (Status/Type/Mode/Created), a
**Description**, an **Acceptance criteria** checklist (specific + testable), and **Notes**. The
`init` command writes a stub from the template; fill in the real content.

## Output
Return the **key**, path to `ticket.md`, the **mode**, and the acceptance-criteria list.

## Under the hood (for reference / non-adlc hosts)
Jira REST v3: `POST /rest/api/3/issue` (ADF description) to create, `GET /rest/api/3/search`
(JQL) to pick, HTTP Basic auth `JIRA_EMAIL:JIRA_API_TOKEN`. Implemented with the Python stdlib in
`scripts/jira_ticket.py` (no pip installs). Run it with a real interpreter (`py` on Windows,
`python3` on macOS/Linux) — the `adlc jira …` wrapper handles interpreter detection for you.


# spec-design

Produce a concise, reviewable design doc — complete enough to approve, short enough to read.

## Rules
1. **Ground it in the real codebase.** Read the relevant files first; name actual files,
   functions, and patterns to reuse. Don't invent structure.
2. **Traceability:** every acceptance criterion in `ticket.md` maps to at least one Test-plan row.
   Call out any criterion you cannot test and why.
3. **Minimal surface:** prefer extending existing code; justify each new file in one line.
4. **No code yet** — describe the change; small signatures/snippets are fine.
5. **Be honest about risk** — what could break, and how to roll back.
6. Keep it to ~one screen.

## Sections (write to `docs/adlc/<KEY>/spec.md`)
1. **Problem & context** — what's asked and why; current behavior.
2. **Goals / non-goals** — goals tied to acceptance criteria; explicit out-of-scope.
3. **Proposed approach** — the design in prose, referencing concrete files/functions; note key
   decisions and rejected alternatives in one line each.
4. **Files to change** — a table of file → change (mark new files).
5. **Test plan** — a table mapping each acceptance criterion → test → type (unit/integration/manual).
6. **Risks & rollback** — risks → mitigations; rollback = revert the branch.
7. **Open questions** — anything needing a human decision at Gate 1 (empty if none).

A template with these sections is seeded at `docs/adlc/<KEY>/` by the framework; fill it in.

## Output
Return the path to `spec.md` and a 2–3 sentence approach summary for the Gate 1 prompt.
