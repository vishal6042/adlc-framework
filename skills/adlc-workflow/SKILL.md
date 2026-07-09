---
name: adlc-workflow
description: The ADLC lifecycle state machine — stage order, the state.md schema, the two human approval gates, resume logic, and the verify→code retry loop. Load this when running or reasoning about an ADLC pipeline (the /adlc command and every adlc-* agent share these rules).
---

# ADLC lifecycle rules

This skill is the single source of truth for how an ADLC run progresses. The `/adlc`
orchestrator and the six `adlc-*` agents all follow it.

## Artifacts directory

All run state and artifacts live in the **target project** (never in the plugin), under:

```
docs/adlc/<KEY>/
├── state.md          # the state machine below
├── ticket.md         # from adlc-jira
├── spec.md           # from adlc-spec (reviewed at Gate 1)
└── verification.md   # from adlc-verifier
```

`<KEY>` is the ticket key (e.g. `ADLC-001`, `PROJ-42`). Local-mode tickets also get a copy
under `docs/adlc/tickets/<KEY>.md` (see the `jira-ticket` skill).

## Stage order

| # | Stage | Agent | Advances to next when |
|---|-------|-------|-----------------------|
| 1 | intake | `adlc-jira` | `ticket.md` written with acceptance criteria |
| 2 | spec | `adlc-spec` | `spec.md` written → **GATE 1** |
| 3 | code | `adlc-coder` | changes implemented on the feature branch |
| 4 | tests | `adlc-tester` | tests written per the spec test-plan |
| 5 | verify | `adlc-verifier` | `verification.md` says PASS (else loop to stage 3) |
| 6 | ship | `adlc-shipper` | **GATE 2** approved, then commit + push |

## The two gates (never skip)

- **GATE 1 — after spec (stage 2):** the human must approve `spec.md` before any code is
  written. Offer: **Approve** / **Request changes** / **Abort**. On "request changes", record
  the feedback and re-run stage 2. Nothing downstream runs until approved.
- **GATE 2 — before push (stage 6):** the human must approve before anything is pushed to a
  remote. Show the branch name, the file diff summary, and the commit message. Offer:
  **Approve & push** / **Request changes** (loop to stage 3) / **Commit locally only** /
  **Abort**.

Gates are enforced by the orchestrator via `AskUserQuestion`. Agents never push or write code
past a gate on their own.

## `state.md` schema

The orchestrator creates and maintains this file. Example:

```markdown
# ADLC state — ADLC-001

- key: ADLC-001
- title: Add a health endpoint
- created: 2026-07-09
- branch: adlc/ADLC-001-add-health-endpoint
- jira_mode: local        # local | jira
- current_stage: verify   # intake|spec|code|tests|verify|ship|done
- gate1_spec_approved: true
- gate2_push_approved: false
- verify_attempts: 1

## Log
- 2026-07-09 intake: ticket ADLC-001 created (local)
- 2026-07-09 spec: spec.md written
- 2026-07-09 gate1: approved by user
- 2026-07-09 code: implemented 2 files
- 2026-07-09 tests: added tests/test_health.py
- 2026-07-09 verify: PASS (attempt 1)
```

## Resume logic

Re-running `/adlc` on an existing ticket must **read `state.md` first** and continue from
`current_stage` rather than starting over. Never re-run a completed stage unless the user asks
or a gate sent it back. Update `current_stage` and append to `## Log` after every stage.

## Verify → code retry loop

If stage 5 reports FAIL:
1. Increment `verify_attempts` in `state.md`.
2. Send the failure details back to `adlc-coder` (stage 3) to fix, then re-run tests + verify.
3. After **3 failed attempts**, stop and surface the problem to the human instead of looping
   forever.

## Degradation rules

- **No Jira creds** → `jira_mode: local`; tickets are local files. Pipeline is otherwise identical.
- **No git remote** → stage 6 commits to a local branch and clearly says "not pushed (no remote)".
- Always keep going as far as possible without external services rather than hard-failing.
