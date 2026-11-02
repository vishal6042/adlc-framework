---
name: adlc-jira-ticket
description: Pick an existing ticket or create a new one for an ADLC run. Dual-mode — Jira Cloud REST when JIRA_BASE_URL/JIRA_EMAIL/JIRA_API_TOKEN are set, otherwise local ticket files. Use at the start of an ADLC pipeline.
---
# adlc-jira-ticket

Turn a request into a tracked ticket with a **key** and explicit **acceptance criteria**. All the
mechanics are in the `@ADLC@` script; this explains the intent and the `ticket.md` shape.

## Mode
`@ADLC@ jira mode` → `jira` (all three `JIRA_*` vars set, in the environment or a `.env`) or
`local`. Record it with `@ADLC@ set-state <KEY> jira_mode <mode>`.

## Pick vs create
If the user referenced a key, **pick** it; otherwise **create**.
- **Jira mode:**
  - pick: `@ADLC@ jira pick` lists open issues (`KEY<TAB>status<TAB>summary`); choose one, then
    `@ADLC@ jira get <KEY>` prints its summary and description to copy into `ticket.md`.
  - create: `@ADLC@ jira create "<summary>" "<description>"` prints the new KEY. Put acceptance
    criteria into the description, one `- ` bullet per criterion (they become a Jira bullet list).
  - Then `@ADLC@ init "<request>" <KEY>` seeds the local run dir under that real key.
- **Local mode:** `@ADLC@ init "<request>"` generates the next `ADLC-00N` key and seeds everything.
- `init` refuses to overwrite an existing run. If the KEY already has a run, resume it instead.

## ticket.md shape (both modes)
Sections: title line `# <KEY>: <summary>`, a metadata block (Status/Type/Mode/Created), a
**Description**, an **Acceptance criteria** checklist (specific + testable), and **Notes**. The
`init` command writes a stub from the template; fill in the real content.

## Errors
`@ADLC@ jira ...` exits 1 on a Jira or network error (the message says why: bad credentials,
missing permission, unreachable host) and 2 when Jira is not configured. On either, tell the user
and offer to continue in local mode — do not retry in a loop. Never print or log the API token.

## Output
Return the **key**, path to `ticket.md`, the **mode**, and the acceptance-criteria list.

## Under the hood (for reference)
Jira Cloud REST v3: `POST /rest/api/3/issue` (ADF description) to create,
`GET /rest/api/3/search/jql` (JQL) to pick, `GET /rest/api/3/issue/<KEY>` to read; HTTP Basic auth
`JIRA_EMAIL:JIRA_API_TOKEN` over HTTPS only. Implemented with the Python standard library in
`scripts/jira_ticket.py` (no pip installs); the `@ADLC@ jira …` wrapper finds a working interpreter.
