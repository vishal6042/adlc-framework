---
name: adlc-workflow
description: The ADLC lifecycle state machine — stage order, the state.md schema, the two human approval gates, resume logic, and the verify→code retry loop. Reference when running or reasoning about an ADLC pipeline.
---
# ADLC lifecycle rules

Single source of truth for how an ADLC run progresses. The orchestrator and every stage follow it.

## Artifacts (in the target project, never the framework)
```
docs/adlc/<KEY>/
├── state.md          # the state machine below (managed via `@ADLC@ get-state/set-state`)
├── ticket.md         # stage 1
├── spec.md           # stage 2 (reviewed at Gate 1)
└── verification.md   # stage 5
docs/adlc/tickets/<KEY>.md   # local-mode ticket mirror
```

## Stage order
`intake → spec → [GATE 1] → code → tests → verify → [GATE 2] → ship`

| Stage | Advances when |
|-------|---------------|
| intake | `ticket.md` has Gherkin acceptance scenarios |
| spec | `spec.md` written → Gate 1 |
| code | change implemented on the feature branch |
| tests | tests written per the spec Test plan |
| verify | `verification.md` = PASS (else loop to code) |
| ship | Gate 2 approved, then commit + push |

## The two gates (never skip)
- **GATE 1 — after spec:** human approves `spec.md` before any code. Approve / Request changes / Abort.
- **GATE 2 — before push:** human approves before anything is pushed. Approve & push / Request
  changes / Commit locally only / Abort.

Record approvals with `@ADLC@ approve <KEY> gate1|gate2`.

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
