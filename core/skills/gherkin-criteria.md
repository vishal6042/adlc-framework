---
name: gherkin-criteria
description: Write acceptance criteria as Gherkin (BDD) scenarios — Feature / Scenario / Given-When-Then — so criteria are unambiguous, testable, and traceable straight into the spec and the tests. Use whenever authoring or reviewing the Acceptance criteria of an ADLC ticket or spec.
---
# gherkin-criteria

The ADLC standard for acceptance criteria is **Gherkin**, the plain-language BDD
notation. Every criterion is a `Scenario` under one `Feature`, described only in terms of
observable behavior (`Given` context → `When` action → `Then` outcome). This makes each
criterion unambiguous, independently testable, and traceable one-to-one into the spec's Test
plan and into stage-4 tests.

## The grammar (keep to this exact subset)
```gherkin
Feature: <short feature name>
  <one-line description of the capability and who it is for>

  Background:            # optional — Given steps shared by every scenario
    Given <shared precondition>

  Scenario: <one concrete behavior, phrased as an outcome>
    Given <initial context / preconditions>
    When  <the action or event that triggers the behavior>
    Then  <the single, observable expected outcome>
    And   <a further outcome, if needed>

  Scenario Outline: <behavior that varies by data>   # optional
    Given <context with a <placeholder>>
    When  <action with a <placeholder>>
    Then  <outcome with a <placeholder>>
    Examples:
      | placeholder | outcome |
      | value-1     | ...     |
      | value-2     | ...     |
```

Keywords: `Feature`, `Background`, `Scenario`, `Scenario Outline` / `Examples`, and the steps
`Given` / `When` / `Then` / `And` / `But`. Nothing else.

## Rules for good scenarios
1. **One behavior per scenario.** If a scenario needs two unrelated `When`s, split it.
2. **Declarative, not imperative.** Describe *what* the system does, not UI click-by-click steps
   (`When the user submits an invalid email`, not `When the user types … and clicks the button`).
3. **Observable outcomes only.** Every `Then` must be checkable from outside the system —
   a response, a value, a stored record, a raised error. No "Then it works".
4. **Concrete, not vague.** Prefer real values (`Then the response status is 200 and body is
   {"status":"ok"}`) over adjectives ("Then it responds correctly").
5. **Cover the unhappy paths.** Include at least the primary error/edge scenario, not only the
   happy path.
6. **Independent scenarios.** Each stands alone; don't rely on a previous scenario's side effects
   (use `Background` for shared setup instead).
7. **3–6 scenarios** for a typical ticket. If you need many more, the ticket is too big — note it.

## How it flows through the pipeline
- **Stage 1 (intake):** write the `Feature` + scenarios into `ticket.md` under *Acceptance criteria*.
- **Stage 2 (spec):** copy the same `Feature` block into `spec.md` verbatim (the standard,
  frozen contract), then map **each Scenario → at least one Test-plan row**.
- **Stage 4 (tests):** implement one test per scenario (BDD runner if the project already uses one
  — `behave`, `pytest-bdd`, `cucumber`, `godog`, …; otherwise a plainly-named test per scenario).
- **Stage 5 (verify):** report coverage as *Scenario → passing test*.

Traceability rule: a Scenario with no test is a gap; a test with no Scenario is scope creep.

## Output
The `Feature` block (valid Gherkin) plus a one-line note on any scenario that can only be
verified manually and why.
