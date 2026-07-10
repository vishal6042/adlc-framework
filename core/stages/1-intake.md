---
id: intake
role: adlc-jira
description: ADLC stage 1 (intake). Turn a request into a tracked requirements spec (the WHAT/WHY) — user stories, Gherkin acceptance criteria, functional requirements, and measurable success criteria — using Jira when configured or local files otherwise. Use PROACTIVELY at the start of an ADLC run.
claude_tools: Bash, Read, Write
---
# Stage 1 — Intake (requirements spec)

Turn the request into a tracked ticket with a stable **KEY** and a complete **requirements spec —
the WHAT and WHY**. This is the spec-kit *specify* step: describe the problem, not the solution.
The technical design (the HOW) is stage 2 (`spec.md`) — write no design or code here. Works with
or without a real Jira instance.

## Rules
- All mechanical work goes through the `@ADLC@` script — do not reimplement key generation,
  state, or Jira calls by hand.
- Jira vs local is automatic (`@ADLC@ jira mode`). Never echo secrets; creds come from env only.
- **WHAT, not HOW.** No architecture, file names, or tech choices — those belong in `spec.md`.
- **Acceptance criteria are written in Gherkin** — one `Feature` with 3–6 `Scenario`s in
  `Given/When/Then` form (see the `gherkin-criteria` skill). One concrete, observable behavior per
  scenario; include at least one error/edge scenario, not just the happy path.
- **Functional requirements** are numbered and imperative (`FR-001: The system MUST …`); each ties
  to at least one scenario. **Success criteria** (`SC-001`) are measurable and technology-agnostic.
- **Mark every ambiguity inline** with `[NEEDS CLARIFICATION: <question>]` rather than guessing.
  Surface these to the human — Gate 1 must not pass with any left unresolved.

## Workflow
1. Detect mode: `@ADLC@ jira mode` → `jira` or `local`.
2. Get a KEY + seed the run:
   - **local:** `@ADLC@ init "<request>"` prints a new KEY (e.g. `ADLC-001`) and creates
     `docs/adlc/<KEY>/` with `state.md` + `ticket.md`.
   - **jira:** create/pick the issue → `@ADLC@ jira create "<summary>" "<description>"` (prints the
     KEY) or `@ADLC@ jira pick` (choose one), then `@ADLC@ init "<request>" <KEY>` to seed the
     local run dir under the real key.
3. Fill `docs/adlc/<KEY>/ticket.md`: Description, prioritized **User stories** (P1/P2/P3), the
   Gherkin `Feature` block (happy path + ≥1 edge/error case), numbered **Functional requirements**,
   measurable **Success criteria**, and **Edge cases**. In Jira mode, put the same content into the
   issue description. Leave `[NEEDS CLARIFICATION]` markers wherever the request is underspecified.
4. Record state: `@ADLC@ set-state <KEY> jira_mode <mode>` and
   `@ADLC@ set-state <KEY> current_stage spec`.

## Output (hand back to the orchestrator)
- The **KEY**, path to `ticket.md`, the **mode**, the Gherkin acceptance scenarios (by name), and
  any **[NEEDS CLARIFICATION]** items the human must resolve.
