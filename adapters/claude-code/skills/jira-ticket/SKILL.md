---
name: jira-ticket
description: Store an ADLC run's ticket in a tracker or local files, and get its key. Dual-mode — Jira Cloud REST when JIRA_BASE_URL/JIRA_EMAIL/JIRA_API_TOKEN are set, otherwise local ticket files. This is the storage/keying step; requirement *content* comes from the source chain in stage 1 (see requirement-elicitation). Use at the start of an ADLC pipeline.
---

# jira-ticket

Store the run's ticket and get a **key**. A tracker is **one source, not a prerequisite** — Jira is
optional and local files always work. This skill covers *where the ticket lives and how it's keyed*;
the *requirement content* (Gherkin criteria, FRs, success criteria) is gathered by the stage-1
source chain — a referenced item, Jira, or by interviewing the requester
(`requirement-elicitation`) when nothing else supplies it. All mechanics are in the `adlc` script.

## Mode
`adlc jira mode` → `jira` (all three `JIRA_*` vars set) or `local`. Record it with
`adlc set-state <KEY> jira_mode <mode>`. No Jira is not a blocker — local mode is a first-class
path, not a degraded one.

## Pick vs create
If the user referenced a key, **pick** it; otherwise **create**.
- **Jira mode:**
  - pick: `adlc jira pick` lists open issues (`KEY  status  summary`); choose one.
  - create: `adlc jira create "<summary>" "<description>"` prints the new KEY. Put the Gherkin
    `Feature` + `Scenario` block into the description.
  - Then `adlc init "<request>" <KEY>` seeds the local run dir under that real key.
- **Local mode:** `adlc init "<request>"` generates the next `ADLC-00N` key and seeds everything.

If the request is too thin to fill the criteria, **elicit first** (`requirement-elicitation`), then
create/seed the ticket with the gathered content.

## ticket.md shape (both modes)
Sections: title line `# <KEY>: <summary>`, a metadata block (Status/Type/Mode/Created), a
**Description**, an **Acceptance criteria (Gherkin)** block — one `Feature` with `Scenario`s in
`Given/When/Then` form — and **Notes**. The `init` command writes a stub from the template; fill in
the real content.

## Output
Return the **key**, path to `ticket.md`, the **mode**, and the Gherkin acceptance scenarios.

## Under the hood (for reference / non-adlc hosts)
Jira REST v3: `POST /rest/api/3/issue` (ADF description) to create, `GET /rest/api/3/search`
(JQL) to pick, HTTP Basic auth `JIRA_EMAIL:JIRA_API_TOKEN`. Implemented with the Python stdlib in
`scripts/jira_ticket.py` (no pip installs). Run it with a real interpreter (`py` on Windows,
`python3` on macOS/Linux) — the `adlc jira …` wrapper handles interpreter detection for you.
