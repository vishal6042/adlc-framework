# ADLC framework (rules)

This project can run the Agentic Development Life Cycle. To start it, invoke the `adlc` workflow (`.clinerules/workflows/adlc.md`) with a feature request.

Deterministic operations (ticket keys, state, Jira, git, compare URLs) are the `adlc` script — call it, do not reimplement. Ensure `adlc` is on PATH (or use `$ADLC_HOME/scripts/adlc`). Artifacts live in `docs/adlc/<KEY>/`.
