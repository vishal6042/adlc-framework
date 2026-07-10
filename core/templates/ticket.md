# <KEY>: <TITLE>

- **Status:** To Do
- **Type:** Task
- **Mode:** local
- **Created:** <DATE>

## Description
<TITLE>

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

## Notes
<links, constraints, out-of-scope>
