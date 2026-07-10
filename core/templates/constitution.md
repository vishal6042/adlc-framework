# Project Constitution

> The project's governing principles and standards. Authored once (evolve deliberately), it is the
> highest authority in an ADLC run: every `spec.md` is scored against it at the **Constitution
> Check** gate, and no design proceeds past Gate 1 while an unjustified violation stands.
> Create/edit via `adlc constitution`; keep it short and enforceable.

- **Version:** 1.0.0
- **Ratified:** <DATE>
- **Last amended:** <DATE>

## Principles
Each principle is a testable rule, not an aspiration. State it as a MUST, with a one-line rationale.

### P1 — <principle name, e.g. "Test-first">
The project MUST <enforceable rule>. Rationale: <why>.

### P2 — <principle name, e.g. "Minimal dependencies">
The project MUST <enforceable rule>. Rationale: <why>.

### P3 — <principle name, e.g. "Backward compatibility">
The project MUST <enforceable rule>. Rationale: <why>.

## Constraints & standards
- **Tech stack / versions:** <pinned languages, frameworks, tools — or "n/a">
- **Coding standards:** <style, linters, naming — point to the config that enforces them>
- **Security & data:** <secrets handling, PII rules, authz baseline>
- **Testing:** <coverage floor, required test types, what "done" means>

## Governance
- This constitution supersedes ad-hoc preferences. Conflicts resolve in its favor.
- **Amendments** bump the version (semver: MAJOR = principle removed/redefined, MINOR = principle
  added, PATCH = wording) and update *Last amended*.
- A `spec.md` may take an exception only by justifying it in the spec's **Complexity tracking**
  table; unjustified violations fail the Constitution Check.
