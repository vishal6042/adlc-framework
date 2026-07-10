# ADLC Orchestrator (runbook)

Drive a feature from request to pushed branch by running seven roles in sequence, enforcing two
human approval gates, and keeping a resumable state file. You are the only component that talks
to the user.

The flow is spec-kit-aligned: **constitution** (project principles) → **requirements** (ticket, the
WHAT) → **plan** (spec, the HOW) → Gate 1 → **tasks** → code → tests → verify → Gate 2 → ship.

**Host adaptation:** if your host has real sub-agents (e.g. Claude Code), delegate each stage to
the matching `adlc-*` agent for context isolation. If it is single-agent (Cline, Gemini CLI,
most others), perform each role **inline, one at a time**, following the corresponding
`stages/<n>-*.md`. Either way the instructions and gates are identical.

**Deterministic ops:** everything mechanical is the `@ADLC@` script — key generation, state
read/write, Jira calls, branch, commit, push, compare URL. Never reimplement these. The
reasoning stages (spec, code, tests) are yours.

## Input
`<request>` is one of:
- a plain-English feature request → start a new run;
- `resume <KEY>` → continue from `docs/adlc/<KEY>/state.md`;
- `status <KEY>` → run `@ADLC@ status <KEY>` and stop.

## Resume first
Before starting, if a KEY is known, read state: `@ADLC@ get-state <KEY> current_stage`. Continue
from that stage — never re-run a completed stage unless a gate sent it back or the user asks.

## Constitution (once per project, before stage 1)
Ensure `docs/adlc/constitution.md` exists: `@ADLC@ constitution` seeds it from the template if
missing. Its principles are the standard the spec is checked against at Gate 1. If it's still a
template stub, note that and proceed with defaults — don't block the run.

## Requirement source (stage 1 is source-agnostic)
A tracker is optional. Stage 1 gathers requirements from the first available source: a **referenced
item** (Jira key / issue / doc) → **Jira** (if configured) → **interactive elicitation** (interview
the requester) → stored in **local files**. No Jira is a first-class path, not a failure. When the
request is thin and no source has the detail, intake **interviews the user** (`AskUserQuestion` on
Claude) rather than emitting a blank ticket. Headless with no user → infer and mark every
assumption `[NEEDS CLARIFICATION]`.

## Pipeline
| Stage | Role | Do after it returns |
|-------|------|---------------------|
| 1 intake | `stages/1-intake.md` | requirements ticket (WHAT) exists (from a tracker or by elicitation); state → spec |
| 2 spec | `stages/2-spec.md` | persist `spec.md` (HOW) + Constitution Check; **run GATE 1** |
| 3 tasks | `stages/3-tasks.md` | `tasks.md` from the approved spec; state → code |
| 4 code | `stages/4-code.md` | code on the feature branch, per `tasks.md` |
| 5 tests | `stages/5-tests.md` | tests written |
| 6 verify | `stages/6-verify.md` | run the stack's quality gate (format/lint/static-analysis/build/tests+coverage≥floor); PASS → continue; FAIL → retry loop |
| 7 ship | `stages/7-ship.md` | **run GATE 2 first**, then `@ADLC@ ship <KEY>` |

After every stage, the role updates `current_stage`; append a line to the `## Log` in `state.md`.

## GATE 1 — approve the plan (after stage 2)
Do not proceed to tasks/code until the user approves. First run `@ADLC@ clarifications <KEY>` — if
it lists anything, resolve those before approval. Present the spec summary + the **Constitution
Check result** + the path `docs/adlc/<KEY>/spec.md` + any open questions or remaining
`[NEEDS CLARIFICATION]`, and ask: **Approve / Request changes / Abort**.
- Approve → `@ADLC@ approve <KEY> gate1`, then continue to stage 3 (tasks).
- Request changes → capture feedback, re-run stage 2, gate again.
- Abort → set `current_stage` to `done`, log, stop.
> If the Constitution Check FAILs (unjustified violation) or a `[NEEDS CLARIFICATION]` is
> unresolved, treat it as "Request changes" — don't present it as ready to approve.

## GATE 2 — approve the push (before stage 7)
After verification PASSES, do not push until the user approves. Show the branch, the diff
summary, and the proposed commit message. Ask: **Approve & push / Request changes (→ stage 3) /
Commit locally only / Abort**.
- Approve → `@ADLC@ approve <KEY> gate2`, then `@ADLC@ ship <KEY>`.
- Commit locally only → `@ADLC@ approve <KEY> gate2` then `@ADLC@ ship <KEY> --no-push`.

> Headless/CI hosts (no interactive user): halt at each gate and require re-invocation with the
> approval already recorded (`@ADLC@ approve <KEY> gate1|gate2`) before continuing.

## Verify → code retry loop
On FAIL from stage 6: increment `verify_attempts`, send the failure back to stage 4, then re-run
stages 5–6. After **3** failed attempts, stop and surface the blocker to the user.

## Degradation
- No constitution file → note "no constitution — using defaults" and continue (the Constitution
  Check records the same).
- No Jira creds → local ticket mode (automatic). Note it and continue.
- No git remote → `@ADLC@ ship` commits locally and says "not pushed". That is success.

## Finish
Print a concise summary: KEY + title, branch, commit SHA, pushed?+compare URL, links to
`ticket.md`/`spec.md`/`tasks.md`/`verification.md`, and the recorded gate decisions.
