---
name: spec-design
description: Author a spec / design document for an ADLC ticket before any code is written. Provides the required section template and the rule that every acceptance criterion maps to at least one planned test. Use when producing docs/adlc/<KEY>/spec.md (the adlc-spec agent calls this) — the doc humans review at Gate 1.
---

# spec-design

Produce a concise, reviewable design doc for a ticket. This is what the human reads at
**Gate 1**, so it must be complete enough to approve but short enough to actually read.

## Rules

1. **Ground it in the real codebase.** Before writing, read the relevant files (Grep/Glob/Read).
   Name actual files, functions, and patterns to reuse — do not invent structure.
2. **Traceability:** every acceptance criterion in `ticket.md` must map to at least one item in
   the Test plan. Call out any criterion you cannot test and why.
3. **Minimal surface:** prefer extending existing code over new files/abstractions. If you add a
   new file, justify it in one line.
4. **No code yet.** Describe the change; don't write the implementation. Small illustrative
   snippets/signatures are fine.
5. **Be honest about risk.** List what could break and how to roll back.
6. Keep it to roughly one screen. Link out for detail rather than inlining everything.

## Template — write to `docs/adlc/<KEY>/spec.md`

```markdown
# Spec: <KEY> — <title>

> Ticket: docs/adlc/<KEY>/ticket.md · Status: DRAFT (awaiting Gate 1)

## 1. Problem & context
<what's being asked and why; the current behavior>

## 2. Goals / non-goals
- **Goals:** <bullet list tied to acceptance criteria>
- **Non-goals:** <explicitly out of scope>

## 3. Proposed approach
<the design in prose. Reference concrete files/functions, e.g. `app/api/routes.py:120`.
Note key decisions and the alternatives rejected in one line each.>

## 4. Files to change
| File | Change |
|------|--------|
| `path/to/file` | <what and why> |
| `path/to/new_file` (new) | <why a new file is needed> |

## 5. Test plan  (each acceptance criterion → at least one test)
| Acceptance criterion | Test | Type |
|----------------------|------|------|
| <criterion 1> | <test name/what it asserts> | unit / integration / manual |
| <criterion 2> | ... | ... |

## 6. Risks & rollback
- <risk> → <mitigation>
- **Rollback:** <how to undo — usually "revert the branch">

## 7. Open questions
- <anything needing a human decision at Gate 1; empty if none>
```

## Output contract

Return the path to `spec.md` and a 2–3 sentence summary of the approach for the Gate 1 prompt.
