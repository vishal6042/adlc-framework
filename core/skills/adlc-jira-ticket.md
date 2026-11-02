---
name: adlc-jira-ticket
description: Store an ADLC run's ticket in a tracker or local files, and get its key. Dual-mode — Jira Cloud REST when JIRA_BASE_URL/JIRA_EMAIL/JIRA_API_TOKEN are set, otherwise local ticket files. This is the storage/keying step; requirement *content* comes from the source chain in stage 1 (see adlc-requirement-elicitation). Use at the start of an ADLC pipeline.
---
# adlc-jira-ticket

Store the run's ticket and get a **key**. A tracker is **one source, not a prerequisite** — Jira is
optional and local files always work. This skill covers *where the ticket lives and how it's keyed*;
the *requirement content* (Gherkin criteria, FRs, success criteria) is gathered by the stage-1
source chain — a referenced item, Jira, or by interviewing the requester
(`adlc-requirement-elicitation`) when nothing else supplies it. All mechanics are in the `@ADLC@`
script.

## Mode
`@ADLC@ jira mode` → `jira` (all three `JIRA_*` vars set, in the environment or a `.env`) or
`local`. Record it with `@ADLC@ set-state <KEY> jira_mode <mode>`. No Jira is not a blocker —
local mode is a first-class path, not a degraded one.

## Pick vs create
If the user referenced a key, **pick** it; otherwise **create**.
- **Jira mode:**
  - pick: `@ADLC@ jira pick` lists open issues (`KEY<TAB>status<TAB>summary`); choose one, then
    `@ADLC@ jira get <KEY>` prints its summary and description to start `ticket.md` from.
  - create: `@ADLC@ jira create "<summary>" "<description>"` prints the new KEY. Put the Gherkin
    `Feature` + `Scenario` block into the description.
  - Then `@ADLC@ init "<request>" <KEY>` seeds the local run dir under that real key.
- **Local mode:** `@ADLC@ init "<request>"` generates the next `ADLC-00N` key and seeds everything.
- `init` refuses to overwrite an existing run. If the KEY already has a run, resume it instead.

If the request is too thin to fill the criteria, **elicit first** (`adlc-requirement-elicitation`),
then create/seed the ticket with the gathered content.

## ticket.md shape (both modes)
Sections: title line `# <KEY>: <summary>`, a metadata block (Status/Type/Mode/Created), a
**Description**, an **Acceptance criteria (Gherkin)** block — one `Feature` with `Scenario`s in
`Given/When/Then` form — and **Notes**. The `init` command writes a stub from the template; fill in
the real content.

## Errors
`@ADLC@ jira ...` exits 1 on a Jira or network error (the message says why: bad credentials,
missing permission, unreachable host) and 2 when Jira is not configured. On either, tell the user
and offer to continue in local mode — do not retry in a loop. Never print or log the API token.

## Output
Return the **key**, path to `ticket.md`, the **mode**, and the Gherkin acceptance scenarios.

## Under the hood (for reference)
Jira Cloud REST v3: `POST /rest/api/3/issue` (ADF description) to create,
`GET /rest/api/3/search/jql` (JQL) to pick, `GET /rest/api/3/issue/<KEY>` to read; HTTP Basic auth
`JIRA_EMAIL:JIRA_API_TOKEN` over HTTPS only. Implemented with the Python standard library in
`scripts/jira_ticket.py` (no pip installs); the `@ADLC@ jira …` wrapper finds a working interpreter.
