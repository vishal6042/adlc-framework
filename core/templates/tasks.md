# Tasks: <KEY> — <TITLE>

> Ordered, dependency-aware breakdown of the **approved** `spec.md` (generated after Gate 1).
> Drives stage 4 (code). IDs are `T001…`; `[P]` marks tasks that can run in parallel (no shared
> files / no ordering dependency). Each task is small enough to do and verify in one sitting.

- Spec: docs/adlc/<KEY>/spec.md · Ticket: docs/adlc/<KEY>/ticket.md
- Generated after: Gate 1 approval

## Setup / prerequisites
- [ ] T001 — <scaffolding, deps, config the rest depend on>

## Tasks by user story
Ordered so each story becomes independently testable as early as possible.

### US-1 (P1) — <story name>
- [ ] T002 — <implementation task> · files: `path/to/file` · covers: FR-001, Scenario "<name>"
- [ ] T003 [P] — <task with no dependency on T002> · files: `other/file`
- [ ] T004 — write/adjust tests for Scenario "<name>" · files: `tests/...`

### US-2 (P2) — <story name>
- [ ] T005 — <task> · deps: T002 · covers: FR-002, Scenario "<name>"

## Polish / cross-cutting
- [ ] T00N [P] — <docs, logging, cleanup, perf per success criterion SC-00N>

## Dependency notes
- <T005 depends on T002 (shared module)>; everything marked `[P]` is independent.

## Coverage check (must hold before stage 4 completes)
- Every `Scenario` in the spec → at least one task. Every `FR-00N` → at least one task.
- Any gap or unresolved `[NEEDS CLARIFICATION]` → stop and return to Gate 1.
