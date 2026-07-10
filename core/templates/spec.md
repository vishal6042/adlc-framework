# Spec: <KEY> — <TITLE>

> Ticket: docs/adlc/<KEY>/ticket.md · Status: DRAFT (awaiting Gate 1)

## 1. Problem & context
<what's being asked and why; the current behavior>

## 2. Goals / non-goals
- **Goals:** <tied to the acceptance scenarios below>
- **Non-goals:** <explicitly out of scope>

## 3. Acceptance criteria (Gherkin — the frozen contract)
Copied verbatim from `ticket.md`; this is the standard the implementation and tests must satisfy.
```gherkin
Feature: <short feature name>
  <one-line description>

  Scenario: <criterion 1>
    Given <context>
    When  <action>
    Then  <outcome>

  Scenario: <criterion 2>
    Given <context>
    When  <action>
    Then  <outcome>
```

## 4. Proposed approach
<the design in prose; reference concrete files/functions; note key decisions>

## 5. Files to change
| File | Change |
|------|--------|
| `path/to/file` | <what and why> |

## 6. Test plan  (each Scenario → at least one test)
| Scenario | Test | Type |
|----------|------|------|
| <scenario 1 name> | <test name / assertion> | unit / integration / manual |
| <scenario 2 name> | <test name / assertion> | unit / integration / manual |

## 7. Risks & rollback
- <risk> → <mitigation>
- **Rollback:** revert the branch

## 8. Open questions
- <anything needing a human decision at Gate 1; empty if none>
