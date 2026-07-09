---
name: jira-ticket
description: Pick an existing ticket or create a new one for an ADLC run. Dual-mode — uses the Jira Cloud REST API when JIRA_BASE_URL/JIRA_EMAIL/JIRA_API_TOKEN are set, otherwise falls back to local ticket files under docs/adlc/tickets/. Use at the start of an ADLC pipeline (the adlc-jira agent calls this) whenever you need to turn a request into a tracked ticket with a key and acceptance criteria.
---

# jira-ticket

Turn a feature request into a tracked ticket with a **key** (e.g. `ADLC-001`, `PROJ-42`) and
explicit **acceptance criteria**. Works with or without a real Jira instance.

## Step 0 — detect mode

Check whether Jira is configured. In Bash:

```bash
if [ -n "${JIRA_BASE_URL:-}" ] && [ -n "${JIRA_EMAIL:-}" ] && [ -n "${JIRA_API_TOKEN:-}" ]; then
  echo "MODE=jira"
else
  echo "MODE=local"
fi
```

PowerShell:

```powershell
if ($env:JIRA_BASE_URL -and $env:JIRA_EMAIL -and $env:JIRA_API_TOKEN) { "MODE=jira" } else { "MODE=local" }
```

Record the chosen mode in `state.md` as `jira_mode:`.

## Step 1 — pick or create

Always ask/decide: is this request covered by an **existing** ticket, or do we **create** one?
If the user referenced a key (e.g. "PROJ-42"), pick it. Otherwise create.

---

## JIRA mode

Auth is HTTP Basic with `JIRA_EMAIL:JIRA_API_TOKEN`. Use `curl` (portable; present in Git
Bash) or PowerShell `Invoke-RestMethod`.

### Pick — search existing issues

```bash
curl -s -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  -H "Accept: application/json" \
  --get "$JIRA_BASE_URL/rest/api/3/search" \
  --data-urlencode "jql=project=$JIRA_PROJECT_KEY AND statusCategory != Done ORDER BY created DESC" \
  --data-urlencode "maxResults=20" \
  --data-urlencode "fields=summary,status"
```

Show the returned `key` + `summary` list and let the user choose one, or proceed to create.

### Create — new issue

Jira Cloud v3 wants the description as an **ADF** (Atlassian Document Format) object. Write the
payload to a temp file, then POST it:

```bash
cat > /tmp/adlc_issue.json <<'JSON'
{
  "fields": {
    "project":   { "key": "PROJECT_KEY_HERE" },
    "issuetype": { "name": "ISSUE_TYPE_HERE" },
    "summary":   "SUMMARY_HERE",
    "description": {
      "type": "doc", "version": 1,
      "content": [
        { "type": "paragraph", "content": [ { "type": "text", "text": "DESCRIPTION_HERE" } ] }
      ]
    }
  }
}
JSON

curl -s -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  -X POST -H "Content-Type: application/json" \
  --data @/tmp/adlc_issue.json \
  "$JIRA_BASE_URL/rest/api/3/issue"
```

Substitute: `PROJECT_KEY_HERE`=`$JIRA_PROJECT_KEY`, `ISSUE_TYPE_HERE`=`${JIRA_ISSUE_TYPE:-Task}`,
and the summary/description from the request. The response JSON contains the new `key` — capture
it. Put the acceptance criteria into the description text (one bullet per criterion).

PowerShell equivalent for create:

```powershell
$pair = "$($env:JIRA_EMAIL):$($env:JIRA_API_TOKEN)"
$auth = "Basic " + [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes($pair))
$body = @{ fields = @{
    project   = @{ key = $env:JIRA_PROJECT_KEY }
    issuetype = @{ name = ($env:JIRA_ISSUE_TYPE ? $env:JIRA_ISSUE_TYPE : "Task") }
    summary   = "SUMMARY_HERE"
    description = @{ type="doc"; version=1; content=@(@{ type="paragraph"; content=@(@{ type="text"; text="DESCRIPTION_HERE" }) }) }
} } | ConvertTo-Json -Depth 10
Invoke-RestMethod -Method Post -Uri "$($env:JIRA_BASE_URL)/rest/api/3/issue" `
  -Headers @{ Authorization = $auth } -ContentType "application/json" -Body $body
```

> Note: Windows PowerShell 5.1 lacks the `?:` operator — use an `if/else` for `JIRA_ISSUE_TYPE`
> there. PowerShell 7+ supports the ternary shown above.

After creating, also write a local mirror `docs/adlc/<KEY>/ticket.md` (see template below) so
the rest of the pipeline reads one consistent file regardless of mode.

---

## LOCAL mode

No Jira. Generate the next key and write a ticket file.

1. Key generation: scan `docs/adlc/tickets/` for existing `ADLC-*.md`, take the highest number,
   add 1, zero-pad to 3 digits → `ADLC-001`, `ADLC-002`, ...
2. Write both `docs/adlc/tickets/<KEY>.md` and `docs/adlc/<KEY>/ticket.md` with the template.

---

## `ticket.md` template (both modes)

```markdown
# <KEY>: <one-line summary>

- **Status:** To Do
- **Type:** Task
- **Mode:** local            <!-- or: jira (<KEY> at <JIRA_BASE_URL>/browse/<KEY>) -->
- **Created:** <YYYY-MM-DD>

## Description
<what the user asked for, in 2–4 sentences>

## Acceptance criteria
- [ ] <criterion 1 — specific and testable>
- [ ] <criterion 2>
- [ ] <criterion 3>

## Notes
<links, constraints, out-of-scope>
```

## Output contract

Return to the caller: the **ticket key**, the **path to `ticket.md`**, the **mode**, and the
**acceptance criteria list**. The orchestrator writes these into `state.md`.
