---
name: quality-gates
description: Stack-independent quality gate for the verify stage — auto-detect the project's toolchain and run the industry-standard format, lint, static-analysis (automated code review), and test-with-coverage checks for it, enforcing a coverage floor (default 90%). Prefers the project's own configured commands; degrades honestly when a tool is absent. Use in stage 6 (verify), and to know what "done" means in stage 5 (tests).
---
# quality-gates

Verification is not "did the tests pass" — it's **did the change clear the project's standard
quality bar**. This gate is **project-independent**: it reads the project, detects the stack, and
runs the *recognized standard tools* for that stack. Nothing is hardcoded to one language.

## The gates (run all; overall PASS only if each PASS)
1. **Format** — the code matches the project's formatter (check mode, no writes).
2. **Lint** — style/correctness linter is clean.
3. **Static analysis / automated code review** — bug-pattern / smell scanner is clean.
4. **Build / typecheck** — compiles / type-checks.
5. **Tests + coverage** — the suite passes **and line coverage ≥ threshold** (default **90%**).

## How to run it
1. **Detect the stack** — `@ADLC@ detect-stack` prints the detected stack(s) from marker files
   (`pom.xml`, `build.gradle`, `package.json`, `go.mod`, `pyproject.toml`, …).
2. **Prefer the project's own commands.** If the project already defines them, use those — they are
   the source of truth:
   - `package.json` scripts (`lint`, `format:check`, `test:coverage`), a `Makefile` (`make lint
     test`), `pre-commit`, or a CI workflow. Mirror what CI runs.
3. **Otherwise fall back to the stack's standard tools** (table below).
4. **Enforce coverage** ≥ the threshold (`ADLC_MIN_COVERAGE`, else the constitution's Testing floor,
   else 90). Read the actual % from the coverage report; a run with no coverage measurement is a
   FAIL, not a pass.
5. Record each gate's result + the coverage number in `verification.md`.

## Standard tools by stack (fallback defaults)
| Stack (detected by) | Format | Lint | Static analysis | Tests + coverage (≥ threshold) |
|---------------------|--------|------|-----------------|-------------------------------|
| **Java / Spring Boot — Maven** (`pom.xml`) | `mvn spotless:check` | `mvn checkstyle:check` | `mvn spotbugs:check` / PMD | `mvn verify` + **JaCoCo** (`jacoco:check` rule) |
| **Java/Kotlin — Gradle** (`build.gradle[.kts]`) | `./gradlew spotlessCheck` | `./gradlew checkstyleMain` / `ktlintCheck` | `./gradlew spotbugsMain` / `detekt` | `./gradlew test jacocoTestCoverageVerification` |
| **Android** (`build.gradle` + `AndroidManifest.xml`) | `./gradlew spotlessCheck` / `ktlintCheck` | `./gradlew lint` (Android Lint) | `detekt` | `./gradlew testDebugUnitTest` + **JaCoCo** report |
| **React / Node (JS/TS)** (`package.json` + `react`) | `npx prettier --check .` | `npx eslint .` | `eslint` (typescript-eslint) / `tsc --noEmit` | `npm test -- --coverage` (**Jest/Vitest** `coverageThreshold`) |
| **Vue** (`package.json` + `vue`) | `npx prettier --check .` | `npx eslint .` (eslint-plugin-vue) | `vue-tsc --noEmit` | `vitest run --coverage` |
| **Angular** (`angular.json`) | `npx prettier --check .` | `ng lint` | `tsc --noEmit` | `ng test --code-coverage --watch=false` |
| **Python** (`pyproject.toml`/`setup.py`) | `black --check .` / `ruff format --check` | `ruff check .` / `flake8` | `mypy` / `bandit` | `pytest --cov --cov-fail-under=<threshold>` |
| **Go** (`go.mod`) | `gofmt -l .` | `golangci-lint run` | `go vet ./...` | `go test -cover ./...` (parse coverage) |
| **Rust** (`Cargo.toml`) | `cargo fmt --check` | `cargo clippy -- -D warnings` | `clippy` | `cargo test` + `cargo llvm-cov` |
| **.NET** (`*.csproj`/`*.sln`) | `dotnet format --verify-no-changes` | analyzers | Roslyn analyzers | `dotnet test /p:CollectCoverage=true` (**Coverlet**) |
| **Ruby** (`Gemfile`) | `rubocop` | `rubocop` | `brakeman` | `rspec` + **SimpleCov** |

> Tools optional per project. Prefer whatever the project actually has configured; the table is the
> default only when the project specifies nothing.

## Enforcement & the retry loop
- Coverage below the floor, or any gate failing, makes stage 6 **FAIL** → the orchestrator loops
  back to stage 4 (fix) / stage 5 (add tests). Stage 5 should target the floor from the start.
- Thresholds and any tool skips are **governed by the constitution** (Testing section) — keep the
  floor there so it's a project decision, not a hidden default.

## Degradation (be honest — never silently pass)
- A required tool isn't installed → report it as **SKIPPED (tool absent)** in `verification.md` and
  do **not** count it as PASS; if coverage can't be measured at all, the result is FAIL.
- No test framework found → FAIL with "no way to measure coverage", not a green check.

## Output
Per-gate PASS/FAIL/SKIPPED, the measured **coverage %** vs the threshold, exact commands run, and
verbatim failures — written to `verification.md`.
