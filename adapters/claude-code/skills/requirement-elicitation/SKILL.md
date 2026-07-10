---
name: requirement-elicitation
description: Actively gather requirements by interviewing the requester when no ticket/tracker supplies them — a structured Q&A that turns a thin one-line request into a complete requirements spec (user stories, Gherkin scenarios, functional/success criteria, edge cases). The universal intake fallback when Jira/GitHub/a doc is not available. Use in stage 1 whenever the request is underspecified.
---

# requirement-elicitation

The universal fallback for requirement gathering. When there is **no Jira ticket, no issue, and no
requirements doc** — or the request is a vague one-liner — don't just stamp out an empty template.
**Interview the requester**, then write a complete `ticket.md`. This is spec-kit's *clarify* step,
applied at intake.

## When to elicit
- The chosen source has no usable detail (local mode, or a tracker item that's just a title), **or**
- the request is underspecified: you cannot write concrete Gherkin scenarios and functional
  requirements from it without guessing.

If the request is already detailed enough to write testable criteria, skip the interview — don't
interrogate the user for its own sake.

## What to ask (cover the gaps, in priority order)
Ask about the dimensions you can't reasonably infer. Lead with the highest-leverage unknowns.
1. **Problem & outcome** — what's broken/missing, and what does "done" look like for the user?
2. **Users & context** — who uses this, and what's the current behavior?
3. **Scope** — the must-haves for *this* change, and explicit **non-goals** / out-of-scope.
4. **Acceptance behavior** — concrete examples of the happy path (these become Gherkin scenarios).
5. **Edge cases & errors** — empty/invalid/unauthorized inputs, limits, concurrency, failure modes.
6. **Constraints** — performance, security/data, compatibility, and any fixed tech choices.
7. **Success criteria** — a measurable, technology-agnostic signal of success (feeds `SC-00N`).

## How to ask (host-adaptive)
- **Claude Code:** use `AskUserQuestion` — batch 2–4 crisp questions with sensible multiple-choice
  options (always leaving room for a free-text answer). Prefer one well-chosen round; ask a second
  round only if answers open a material new gap.
- **Other interactive hosts:** ask a short **numbered list** of questions in one message; parse the
  replies.
- **Few and sharp.** 3–6 questions total. Offer a recommended default per question so the user can
  accept fast. Never block on trivia you can decide yourself — decide it and note the assumption.

## Converge
1. Restate the requirements you now hold as a short **assumptions** summary ("Here's what I'll build
   unless you correct me").
2. Turn the answers into the ticket sections: user stories, the Gherkin `Feature`, functional
   requirements (`FR-00N`), success criteria (`SC-00N`), edge cases.
3. Mark anything still open with `[NEEDS CLARIFICATION: <question>]` — always include the question
   **after the colon** (that colon form is what `adlc clarifications <KEY>` detects; the bare
   `[NEEDS CLARIFICATION]` in template prose is ignored). Gate 1 must have none left.

## Degradation (non-interactive / headless / CI)
No user to interview? Do **not** hard-fail. Infer the most reasonable requirements from the request,
write them, and mark **every** inferred decision with `[NEEDS CLARIFICATION]` so the human resolves
them at Gate 1. Surface the list explicitly in the intake output.

## Output
A completed `ticket.md` (or Jira/issue description) plus the list of any remaining
`[NEEDS CLARIFICATION]` items to carry into the Gate 1 review.
