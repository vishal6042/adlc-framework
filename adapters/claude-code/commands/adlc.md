---
description: Run the Agentic Development Life Cycle: Jira/ticket -> spec -> approval -> code -> tests -> verify -> approval -> git push. Resumable.
argument-hint: "<feature request>" | resume <KEY> | status <KEY>
---

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

## Constitution (once per project, before stage 1)
Ensure `docs/adlc/constitution.md` exists: `adlc constitution` seeds it from the template if
missing. Its principles are the standard the spec is checked against at Gate 1. If it's still a
template stub, note that and proceed with defaults — don't block the run.

## Pipeline
| Stage | Role | Do after it returns |
|-------|------|---------------------|
| 1 intake | `stages/1-intake.md` | requirements ticket (WHAT) exists; state → spec |
| 2 spec | `stages/2-spec.md` | persist `spec.md` (HOW) + Constitution Check; **run GATE 1** |
| 3 tasks | `stages/3-tasks.md` | `tasks.md` from the approved spec; state → code |
| 4 code | `stages/4-code.md` | code on the feature branch, per `tasks.md` |
| 5 tests | `stages/5-tests.md` | tests written |
| 6 verify | `stages/6-verify.md` | PASS → continue; FAIL → retry loop |
| 7 ship | `stages/7-ship.md` | **run GATE 2 first**, then `adlc ship <KEY>` |

After every stage, the role updates `current_stage`; append a line to the `## Log` in `state.md`.

## GATE 1 — approve the plan (after stage 2)
Do not proceed to tasks/code until the user approves. Present the spec summary + the
**Constitution Check result** + the path `docs/adlc/<KEY>/spec.md` + any open questions or
remaining `[NEEDS CLARIFICATION]`, and ask: **Approve / Request changes / Abort**.
- Approve → `adlc approve <KEY> gate1`, then continue to stage 3 (tasks).
- Request changes → capture feedback, re-run stage 2, gate again.
- Abort → set `current_stage` to `done`, log, stop.
> If the Constitution Check FAILs (unjustified violation) or a `[NEEDS CLARIFICATION]` is
> unresolved, treat it as "Request changes" — don't present it as ready to approve.

## GATE 2 — approve the push (before stage 7)
After verification PASSES, do not push until the user approves. Show the branch, the diff
summary, and the proposed commit message. Ask: **Approve & push / Request changes (→ stage 3) /
Commit locally only / Abort**.
- Approve → `adlc approve <KEY> gate2`, then `adlc ship <KEY>`.
- Commit locally only → `adlc approve <KEY> gate2` then `adlc ship <KEY> --no-push`.

> Headless/CI hosts (no interactive user): halt at each gate and require re-invocation with the
> approval already recorded (`adlc approve <KEY> gate1|gate2`) before continuing.

## Verify → code retry loop
On FAIL from stage 6: increment `verify_attempts`, send the failure back to stage 4, then re-run
stages 5–6. After **3** failed attempts, stop and surface the blocker to the user.

## Degradation
- No constitution file → note "no constitution — using defaults" and continue (the Constitution
  Check records the same).
- No Jira creds → local ticket mode (automatic). Note it and continue.
- No git remote → `adlc ship` commits locally and says "not pushed". That is success.

## Finish
Print a concise summary: KEY + title, branch, commit SHA, pushed?+compare URL, links to
`ticket.md`/`spec.md`/`tasks.md`/`verification.md`, and the recorded gate decisions.
