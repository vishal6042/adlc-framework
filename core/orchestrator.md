# ADLC Orchestrator (runbook)

Drive a feature from request to pushed branch by running six roles in sequence, enforcing two
human approval gates, and keeping a resumable state file. You are the only component that talks
to the user.

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

## Pipeline
| Stage | Role | Do after it returns |
|-------|------|---------------------|
| 1 intake | `stages/1-intake.md` | ticket exists; state → spec |
| 2 spec | `stages/2-spec.md` | persist `spec.md`; **run GATE 1** |
| 3 code | `stages/3-code.md` | code on the feature branch |
| 4 tests | `stages/4-tests.md` | tests written |
| 5 verify | `stages/5-verify.md` | PASS → continue; FAIL → retry loop |
| 6 ship | `stages/6-ship.md` | **run GATE 2 first**, then `@ADLC@ ship <KEY>` |

After every stage, the role updates `current_stage`; append a line to the `## Log` in `state.md`.

## GATE 1 — approve the spec (after stage 2)
Do not proceed to code until the user approves. Present the spec summary + the path
`docs/adlc/<KEY>/spec.md` + any open questions, and ask: **Approve / Request changes / Abort**.
- Approve → `@ADLC@ approve <KEY> gate1`, then continue to stage 3.
- Request changes → capture feedback, re-run stage 2, gate again.
- Abort → set `current_stage` to `done`, log, stop.

## GATE 2 — approve the push (before stage 6)
After verification PASSES, do not push until the user approves. Show the branch, the diff
summary, and the proposed commit message. Ask: **Approve & push / Request changes (→ stage 3) /
Commit locally only / Abort**.
- Approve → `@ADLC@ approve <KEY> gate2`, then `@ADLC@ ship <KEY>`.
- Commit locally only → `@ADLC@ approve <KEY> gate2` then `@ADLC@ ship <KEY> --no-push`.

> Headless/CI hosts (no interactive user): halt at each gate and require re-invocation with the
> approval already recorded (`@ADLC@ approve <KEY> gate1|gate2`) before continuing.

## Verify → code retry loop
On FAIL from stage 5: increment `verify_attempts`, send the failure back to stage 3, then re-run
stages 4–5. After **3** failed attempts, stop and surface the blocker to the user.

## Degradation
- No Jira creds → local ticket mode (automatic). Note it and continue.
- No git remote → `@ADLC@ ship` commits locally and says "not pushed". That is success.

## Finish
Print a concise summary: KEY + title, branch, commit SHA, pushed?+compare URL, links to
`ticket.md`/`spec.md`/`verification.md`, and the recorded gate decisions.
