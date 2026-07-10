---
name: spec-design
description: Author a spec/design document for an ADLC ticket before any code. Provides the required sections and the rule that every acceptance criterion maps to at least one planned test. Use when producing docs/adlc/<KEY>/spec.md — the doc humans review at Gate 1.
---

# spec-design

Produce a concise, reviewable design doc — complete enough to approve, short enough to read.

## Rules
1. **Ground it in the real codebase.** Read the relevant files first; name actual files,
   functions, and patterns to reuse. Don't invent structure.
2. **Gherkin contract:** copy the `Feature` + `Scenario` block from `ticket.md` into the spec
   verbatim (the `gherkin-criteria` skill defines the format); it is the frozen standard.
3. **Traceability:** every `Scenario` maps to at least one Test-plan row. Call out any scenario you
   cannot test and why.
4. **Minimal surface:** prefer extending existing code; justify each new file in one line.
5. **No code yet** — describe the change; small signatures/snippets are fine.
6. **Be honest about risk** — what could break, and how to roll back.
7. Keep it to ~one screen.

## Sections (write to `docs/adlc/<KEY>/spec.md`)
1. **Problem & context** — what's asked and why; current behavior.
2. **Goals / non-goals** — goals tied to the acceptance scenarios; explicit out-of-scope.
3. **Acceptance criteria (Gherkin)** — the `Feature` + `Scenario` block, copied verbatim from the
   ticket; the frozen contract.
4. **Proposed approach** — the design in prose, referencing concrete files/functions; note key
   decisions and rejected alternatives in one line each.
5. **Files to change** — a table of file → change (mark new files).
6. **Test plan** — a table mapping each `Scenario` → test → type (unit/integration/manual).
7. **Risks & rollback** — risks → mitigations; rollback = revert the branch.
8. **Open questions** — anything needing a human decision at Gate 1 (empty if none).

A template with these sections is seeded at `docs/adlc/<KEY>/` by the framework; fill it in.

## Output
Return the path to `spec.md` and a 2–3 sentence approach summary for the Gate 1 prompt.
