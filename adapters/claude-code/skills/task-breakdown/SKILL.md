---
name: task-breakdown
description: Decompose an approved ADLC spec into an ordered, dependency-aware tasks.md — grouped by user story, with stable IDs, parallel [P] markers, and full Scenario/FR coverage. Use when producing docs/adlc/<KEY>/tasks.md after Gate 1 and before code.
---

# task-breakdown

Turn the approved `spec.md` into an executable checklist that drives implementation — the spec-kit
*tasks* step. It runs **after Gate 1** and produces `docs/adlc/<KEY>/tasks.md`.

## Rules
1. **Approved spec is the only input.** No redesign. A blocking gap or unresolved
   `[NEEDS CLARIFICATION]` → return to Gate 1, don't guess.
2. **Stable IDs.** Number tasks `T001, T002, …`; never renumber once code references them.
3. **Small and verifiable.** One task = one change a coder can do and check in one sitting. Split
   anything larger.
4. **Order by story, earliest-testable-first.** Group tasks under their user story (US-1/P1 first)
   so a working slice appears early. Setup/prerequisite tasks come first.
5. **Parallel markers.** Tag `[P]` only when a task shares no files and has no ordering dependency
   with others in flight. State real dependencies explicitly (`deps: T00N`).
6. **Traceability both ways.** Each task names the file(s) it touches and what it covers
   (`covers: FR-002, Scenario "…"`). Every `Scenario`, every `FR-00N`, and every success criterion
   (`SC-00N`) in the spec maps to at least one task — that is the Coverage check.

## Sections (write to `docs/adlc/<KEY>/tasks.md`)
1. **Setup / prerequisites** — scaffolding/deps the rest depend on.
2. **Tasks by user story** — ordered, with IDs, `[P]`, `deps:`, and `covers:` notes.
3. **Polish / cross-cutting** — docs, logging, cleanup, perf toward success criteria.
4. **Dependency notes** — the ordering constraints in one place.
5. **Coverage check** — the assertion that every Scenario + FR has a task (gap → back to Gate 1).

## Output
Return the path to `tasks.md`, the task count, the `[P]` groups, and any coverage gap/blocker.
