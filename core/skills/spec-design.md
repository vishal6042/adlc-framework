---
name: spec-design
description: Author the technical plan (spec.md) for an ADLC ticket — the HOW — after the requirements (WHAT) are fixed in ticket.md and before any code. Provides the required sections, the Constitution Check gate, and the rule that every acceptance scenario maps to at least one planned test. Use when producing docs/adlc/<KEY>/spec.md — the doc humans review at Gate 1.
---
# spec-design

Produce a concise, reviewable **technical plan** — complete enough to approve, short enough to
read. This is the spec-kit *plan* step: the requirements are already fixed in `ticket.md` (the
WHAT); the spec decides the HOW.

## Rules
1. **Requirements are frozen.** Read `ticket.md` (user stories, Gherkin scenarios, functional &
   success criteria); design to satisfy them. Don't reword them — a wrong requirement is Gate-1
   feedback.
2. **Ground it in the real codebase.** Read the relevant files first; name actual files,
   functions, and patterns to reuse. Fill **Technical context** from what you find, not assumptions.
3. **Constitution Check (gate).** Score the design against every principle in
   `docs/adlc/constitution.md` (see the `constitution` skill). It must PASS; any exception goes in
   **Complexity tracking** with a justification. No constitution file → note defaults and proceed.
4. **Traceability:** every `Scenario` maps to at least one Test-plan row. Call out any scenario you
   cannot test and why.
5. **Minimal surface:** prefer extending existing code; justify each new file/dependency in one line.
6. **No code yet** — describe the change; small signatures/snippets are fine.
7. **Be honest about risk** — what could break, and how to roll back. Keep it to ~one screen.

## Sections (write to `docs/adlc/<KEY>/spec.md`)
1. **Summary** — the primary requirement + chosen approach in 2–3 sentences.
2. **Constitution Check** — principle-by-principle PASS/FAIL table; overall result.
3. **Technical context** — language/version, deps, storage, test framework, platform, constraints.
4. **Proposed approach** — the design in prose, referencing concrete files/functions; key
   decisions and rejected alternatives in one line each.
5. **Project structure & files to change** — a table of file → change (mark new files).
6. **Test plan** — a table mapping each `Scenario` → test → type (unit/integration/manual).
7. **Complexity tracking** — justify any constitution/simplicity exception (empty is good).
8. **Risks & rollback** — risks → mitigations; rollback = revert the branch.
9. **Open questions** — remaining `[NEEDS CLARIFICATION]` for Gate 1 (empty if none).

## Output
Return the path to `spec.md`, a 2–3 sentence approach summary, and the Constitution Check result
for the Gate 1 prompt.
