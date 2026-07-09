#!/usr/bin/env python3
"""Dual-mode ticket helper for ADLC — pick or create a ticket.

JIRA mode  (JIRA_BASE_URL + JIRA_EMAIL + JIRA_API_TOKEN set): talk to Jira Cloud
           REST v3 with the stdlib only (no pip installs, fully portable).
LOCAL mode (creds missing): the caller uses `adlc init` instead; this script
           only handles the Jira path but degrades gracefully with a clear message.

Usage:
    python jira_ticket.py mode
    python jira_ticket.py pick                       # list open issues (JQL)
    python jira_ticket.py create "<summary>" "<description>"

Run it with a real interpreter. On Windows the Store `python`/`python3` are stubs;
use `py jira_ticket.py ...`. On macOS/Linux use `python3`.
"""
import base64
import json
import os
import sys
import urllib.request
import urllib.error
import urllib.parse


def env(name, default=None):
    v = os.environ.get(name)
    return v if v not in (None, "") else default


def jira_configured():
    return all(env(k) for k in ("JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_API_TOKEN"))


def _auth_header():
    pair = f"{env('JIRA_EMAIL')}:{env('JIRA_API_TOKEN')}".encode()
    return "Basic " + base64.b64encode(pair).decode()


def _request(method, path, payload=None, query=""):
    url = env("JIRA_BASE_URL").rstrip("/") + path + query
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", _auth_header())
    req.add_header("Accept", "application/json")
    if data:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            body = r.read().decode()
            return r.status, (json.loads(body) if body else {})
    except urllib.error.HTTPError as e:
        return e.code, {"error": e.read().decode()}


def pick():
    project = env("JIRA_PROJECT_KEY", "ADLC")
    jql = f"project={project} AND statusCategory != Done ORDER BY created DESC"
    q = "?jql=" + urllib.parse.quote(jql) + "&maxResults=20&fields=summary,status"
    status, body = _request("GET", "/rest/api/3/search", query=q)
    if status >= 300:
        print(f"jira pick failed ({status}): {body.get('error','')}", file=sys.stderr)
        sys.exit(1)
    for issue in body.get("issues", []):
        f = issue.get("fields", {})
        st = f.get("status", {}).get("name", "?")
        print(f"{issue['key']}\t{st}\t{f.get('summary','')}")


def create(summary, description):
    payload = {
        "fields": {
            "project": {"key": env("JIRA_PROJECT_KEY", "ADLC")},
            "issuetype": {"name": env("JIRA_ISSUE_TYPE", "Task")},
            "summary": summary,
            "description": {
                "type": "doc", "version": 1,
                "content": [{"type": "paragraph",
                             "content": [{"type": "text", "text": description}]}],
            },
        }
    }
    status, body = _request("POST", "/rest/api/3/issue", payload=payload)
    if status >= 300:
        print(f"jira create failed ({status}): {body.get('error','')}", file=sys.stderr)
        sys.exit(1)
    print(body["key"])  # the caller captures this key


def main():
    args = sys.argv[1:]
    action = args[0] if args else "mode"

    if action == "mode":
        print("jira" if jira_configured() else "local")
        return
    if not jira_configured():
        print("local", file=sys.stderr)
        print("Jira not configured (JIRA_* env vars missing) — use `adlc init` for local mode.",
              file=sys.stderr)
        sys.exit(2)
    if action == "pick":
        pick()
    elif action == "create":
        if len(args) < 3:
            print('usage: jira_ticket.py create "<summary>" "<description>"', file=sys.stderr)
            sys.exit(2)
        create(args[1], args[2])
    else:
        print(f"unknown action: {action}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
