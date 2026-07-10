# <KEY>: <TITLE>

- **Status:** To Do
- **Type:** Task
- **Mode:** local
- **Created:** <DATE>

> Requirements spec (the **WHAT / WHY**). Technical design (the **HOW**) lives in `spec.md`.
> Mark every unknown inline with **[NEEDS CLARIFICATION: question]** — Gate 1 must have none left.

## Description
<what is being asked and why; the current behavior and the desired outcome>

## User stories (prioritized)
- **US-1 (P1):** As a <role>, I want <capability> so that <benefit>. — *independently testable*
- **US-2 (P2):** As a <role>, I want <capability> so that <benefit>.
> Priorities: P1 = must-have for this ticket, P2/P3 = progressively optional. Each story stands alone.

## Acceptance criteria (Gherkin)
```gherkin
Feature: <short feature name>
  <one-line description of the capability and who it is for>

  Scenario: <criterion 1 — one concrete, observable behavior>
    Given <initial context / preconditions>
    When  <the action or event>
    Then  <the expected, checkable outcome>

  Scenario: <criterion 2 — e.g. the primary error / edge case>
    Given <context>
    When  <action>
    Then  <outcome>
```
> One `Scenario` per criterion; declarative steps; observable `Then`. See the `gherkin-criteria` skill.

## Functional requirements
- **FR-001:** The system MUST <specific, testable capability>.
- **FR-002:** The system MUST <…>.
- **FR-003:** The system MUST be able to <…>.
> Numbered, imperative (MUST / MUST NOT). Each maps to one or more acceptance scenarios.

## Success criteria (measurable, technology-agnostic)
- **SC-001:** <measurable outcome — e.g. "95% of requests complete in <200ms"; no implementation detail>.
- **SC-002:** <e.g. "a new user completes onboarding in under 3 steps">.

## Edge cases
- <boundary / error / concurrency condition> → <expected handling>
- <empty / invalid / unauthorized input> → <expected handling>

## Notes
<links, constraints, out-of-scope, and any remaining [NEEDS CLARIFICATION] context>
