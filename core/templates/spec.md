# Spec: <KEY> — <TITLE>

> Technical plan (the **HOW**). Requirements (the WHAT/WHY) live in `docs/adlc/<KEY>/ticket.md`.
> Ticket: docs/adlc/<KEY>/ticket.md · Constitution: docs/adlc/constitution.md · Status: DRAFT (awaiting Gate 1)

## 1. Summary
<2–3 sentences: the primary requirement from the ticket + the chosen technical approach.>

## 2. Constitution Check  (gate — must PASS before Gate 1)
Evaluate this design against every principle in `docs/adlc/constitution.md`.
| Principle | Complies? | Note |
|-----------|-----------|------|
| <principle 1> | ✅ / ❌ | <how the design honors it, or why it can't> |
| <principle 2> | ✅ / ❌ | <…> |

**Result:** PASS / PASS-with-justified-exceptions (see §7) / FAIL.
> No constitution file yet? Note "no constitution — using defaults" and proceed (suggest `@ADLC@ constitution`).

## 3. Technical context
- **Language / version:** <…>  · **Primary deps:** <…>  · **Storage:** <…>
- **Test framework:** <detected>  · **Platform / project type:** <…>
- **Constraints:** <performance, compatibility, security — or `[NEEDS CLARIFICATION]`>

## 4. Proposed approach
<the design in prose; reference concrete files/functions to reuse; note key decisions and
rejected alternatives (one line each).>

## 5. Project structure & files to change
| File | New? | Change |
|------|------|--------|
| `path/to/file` | no | <what and why> |

## 6. Test plan  (each Scenario → at least one test)
| Scenario (from ticket) | Test | Type |
|------------------------|------|------|
| <scenario 1 name> | <test name / assertion> | unit / integration / manual |
| <scenario 2 name> | <test name / assertion> | unit / integration / manual |

## 7. Complexity tracking  (justify any constitution/simplicity exception)
| Exception | Why it's necessary | Simpler alternative rejected because |
|-----------|--------------------|--------------------------------------|
| <e.g. new dependency X> | <…> | <…> |
> Empty is good — an empty table means the design stays within the constitution.

## 8. Risks & rollback
- <risk> → <mitigation>
- **Rollback:** revert the branch

## 9. Open questions
- <remaining [NEEDS CLARIFICATION] needing a human decision at Gate 1; empty if none>
