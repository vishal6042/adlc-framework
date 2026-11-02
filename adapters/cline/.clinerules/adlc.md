# ADLC framework (rules)

This project can run the Agentic Development Life Cycle. To start it, invoke the `adlc` workflow (`adlc.md` in your Cline workflows) with a feature request.

Deterministic operations (ticket keys, state, templates, Jira, git, compare URLs) are the `adlc` command — call it, do not reimplement it. If `adlc` is not on PATH, use `$ADLC_HOME/scripts/adlc` (or `adlc doctor` to diagnose). Artifacts live in `docs/adlc/<KEY>/`.
