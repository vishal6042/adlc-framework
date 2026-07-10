# Verification — <KEY>  (attempt <N>)

- Result: PASS | FAIL
- Stack: <detected stack, e.g. java-maven / react / android / vue / python>
- Ran: <exact commands>
- Date: <DATE>

## Quality gates
| Gate | Result | Command | Note |
|------|--------|---------|------|
| Format | PASS / FAIL / SKIPPED | `<formatter --check>` | <…> |
| Lint | PASS / FAIL / SKIPPED | `<linter>` | <…> |
| Static analysis | PASS / FAIL / SKIPPED | `<analyzer>` | <…> |
| Build / typecheck | PASS / FAIL / SKIPPED | `<build>` | <…> |
| Tests | PASS / FAIL | `<test runner>` | <n passed> |
| Coverage ≥ <threshold>% | PASS / FAIL | `<coverage tool>` | **measured: <NN>%** |

> Overall PASS only if every gate is PASS (SKIPPED tools noted, not counted as PASS) **and**
> coverage ≥ the floor. A missing/unmeasurable coverage number is a FAIL.

## Output
<key excerpts of the actual test/build/gate output, especially failures — verbatim>

## Coverage vs acceptance criteria (Gherkin scenarios)
- <scenario name> → <passing test> ✅
- <scenario name> → ❌ <why>
