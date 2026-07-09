---
name: jira-ticket
description: Pick an existing ticket or create a new one for an ADLC run. Dual-mode — Jira Cloud REST when JIRA_BASE_URL/JIRA_EMAIL/JIRA_API_TOKEN are set, otherwise local ticket files. Use at the start of an ADLC pipeline.
---

# jira-ticket

Turn a request into a tracked ticket with a **key** and explicit **acceptance criteria**. All the
mechanics are in the `${CLAUDE_PLUGIN_ROOT}/scripts/adlc` script; this explains the intent and the `ticket.md` shape.

## Mode
`${CLAUDE_PLUGIN_ROOT}/scripts/adlc jira mode` → `jira` (all three `JIRA_*` vars set) or `local`. Record it with
`${CLAUDE_PLUGIN_ROOT}/scripts/adlc set-state <KEY> jira_mode <mode>`.

## Pick vs create
If the user referenced a key, **pick** it; otherwise **create**.
- **Jira mode:**
  - pick: `${CLAUDE_PLUGIN_ROOT}/scripts/adlc jira pick` lists open issues (`KEY  status  summary`); choose one.
  - create: `${CLAUDE_PLUGIN_ROOT}/scripts/adlc jira create "<summary>" "<description>"` prints the new KEY. Put acceptance
    criteria into the description (one bullet per criterion).
  - Then `${CLAUDE_PLUGIN_ROOT}/scripts/adlc init "<request>" <KEY>` seeds the local run dir under that real key.
- **Local mode:** `${CLAUDE_PLUGIN_ROOT}/scripts/adlc init "<request>"` generates the next `ADLC-00N` key and seeds everything.

## ticket.md shape (both modes)
Sections: title line `# <KEY>: <summary>`, a metadata block (Status/Type/Mode/Created), a
**Description**, an **Acceptance criteria** checklist (specific + testable), and **Notes**. The
`init` command writes a stub from the template; fill in the real content.

## Output
Return the **key**, path to `ticket.md`, the **mode**, and the acceptance-criteria list.

## Under the hood (for reference / non-${CLAUDE_PLUGIN_ROOT}/scripts/adlc hosts)
Jira REST v3: `POST /rest/api/3/issue` (ADF description) to create, `GET /rest/api/3/search`
(JQL) to pick, HTTP Basic auth `JIRA_EMAIL:JIRA_API_TOKEN`. Implemented with the Python stdlib in
`scripts/jira_ticket.py` (no pip installs). Run it with a real interpreter (`py` on Windows,
`python3` on macOS/Linux) — the `${CLAUDE_PLUGIN_ROOT}/scripts/adlc jira …` wrapper handles interpreter detection for you.
