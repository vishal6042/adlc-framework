---
name: constitution
description: The project constitution — a set of governing principles and standards that every ADLC design is checked against at the Constitution Check gate. Explains how to author docs/adlc/constitution.md and how the spec stage scores a design against it. Use when creating/amending the constitution or performing a Constitution Check in spec.md.
---
# constitution

The **constitution** is the project's highest-authority standard: a short list of enforceable
principles and constraints that every `spec.md` is scored against before Gate 1. It is the
spec-kit *constitution* concept — the thing that keeps designs consistent across many tickets.

## Where it lives
`docs/adlc/constitution.md` — **project-level, one per repo** (not per ticket). Create or open it
with `@ADLC@ constitution` (seeds it from the template if missing, then edit it in place).

## Authoring principles (keep it enforceable)
1. **Each principle is a testable MUST**, not an aspiration. "The system MUST have a test for every
   public endpoint," not "we value quality."
2. **Few and sharp.** 3–7 principles a reviewer can actually hold in mind. More than that and none
   get enforced.
3. **State the rationale** in one line — reviewers need the *why* to apply it to new cases.
4. **Version it (semver).** MAJOR = a principle removed/redefined, MINOR = added, PATCH = wording.
   Bump the version and *Last amended* on every change.
5. Cover **constraints & standards** too: pinned stack/versions, coding standards (point to the
   linter that enforces them), security/data rules, and the testing bar for "done".

## The Constitution Check (in every spec.md)
The stage-2 spec must include a **Constitution Check** table scoring the design principle-by-
principle (✅/❌ + note) with an overall **PASS / PASS-with-justified-exceptions / FAIL**:
- **PASS** → proceed to Gate 1.
- **Exception** → allowed only if justified in the spec's **Complexity tracking** table (what,
  why necessary, which simpler alternative was rejected and why).
- **FAIL** (unjustified violation) → redesign; do not advance.

No constitution file yet is not a blocker: note "no constitution — using defaults" in the check and
suggest running `@ADLC@ constitution`.

## Output
For authoring: the path to `constitution.md`. For a check: the filled Constitution Check table and
the overall result, surfaced in the Gate 1 summary.
