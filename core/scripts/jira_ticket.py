#!/usr/bin/env python3
"""Jira Cloud helper for ADLC: detect mode, pick, get or create a ticket.

JIRA mode  (JIRA_BASE_URL + JIRA_EMAIL + JIRA_API_TOKEN set): talks to Jira Cloud
           REST v3 using only the Python standard library (no pip installs).
LOCAL mode (any of those missing): the pipeline uses `adlc init` instead; this
           script reports "local" and exits 2 for Jira-only actions.

Usage:
    jira_ticket.py mode
    jira_ticket.py pick [--max N]                 # open issues: KEY<TAB>status<TAB>summary
    jira_ticket.py get <KEY>                      # summary + plain-text description
    jira_ticket.py create "<summary>" "<description>"   # prints the new KEY

Settings are read from the environment, then from JIRA_*/ADLC_* lines in
<project>/.env and <framework>/.env (never overriding the environment).
Exit codes: 0 ok, 1 Jira/network error, 2 bad usage or Jira not configured.

Usually called through `adlc jira ...`, which finds a working interpreter.
"""
import base64
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

TIMEOUT = 30
REQUIRED = ("JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_API_TOKEN")
KEY_RE = re.compile(r"^[A-Z][A-Z0-9_]*-[0-9]+$")
PROJECT_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")
DOTENV_RE = re.compile(r"^\s*(?:export\s+)?((?:JIRA|ADLC)_[A-Z0-9_]+)\s*=(.*)$")


class JiraError(Exception):
    """A Jira request failed; the message is safe to show (no credentials)."""


# --- configuration -----------------------------------------------------------
def _project_root():
    try:
        out = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True,
                             text=True, timeout=10)
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return os.getcwd()


def load_dotenv(paths=None, environ=None):
    """Copy JIRA_*/ADLC_* values from .env files into environ without overriding."""
    environ = os.environ if environ is None else environ
    if paths is None:
        here = os.path.dirname(os.path.abspath(__file__))
        paths = [os.path.join(_project_root(), ".env"),
                 os.path.normpath(os.path.join(here, "..", "..", ".env"))]
    for path in paths:
        try:
            with open(path, encoding="utf-8") as fh:
                lines = fh.read().splitlines()
        except OSError:
            continue
        for line in lines:
            m = DOTENV_RE.match(line)
            if not m:
                continue
            key, value = m.group(1), m.group(2).strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            environ.setdefault(key, value)


def env(name, default=None):
    v = os.environ.get(name)
    return v if v not in (None, "") else default


def jira_configured():
    return all(env(k) for k in REQUIRED)


def base_url():
    url = env("JIRA_BASE_URL").rstrip("/")
    if not url.startswith("https://") and env("JIRA_ALLOW_HTTP") != "1":
        raise JiraError("JIRA_BASE_URL must start with https:// (the API token would be sent "
                        "in clear text). Set JIRA_ALLOW_HTTP=1 only for a local test server.")
    return url


def project_key():
    key = env("JIRA_PROJECT_KEY", "ADLC").strip().upper()
    if not PROJECT_RE.match(key):
        raise JiraError(f"JIRA_PROJECT_KEY '{key}' is not a valid Jira project key")
    return key


# --- HTTP ----------------------------------------------------------------------
def _auth_header():
    pair = f"{env('JIRA_EMAIL')}:{env('JIRA_API_TOKEN')}".encode()
    return "Basic " + base64.b64encode(pair).decode()


def _error_text(status, raw):
    """Turn a Jira error body into one readable line."""
    try:
        body = json.loads(raw)
    except ValueError:
        return raw.strip()[:300] or f"HTTP {status}"
    parts = list(body.get("errorMessages") or [])
    parts += [f"{k}: {v}" for k, v in (body.get("errors") or {}).items()]
    return "; ".join(parts) or raw.strip()[:300]


def request(method, path, payload=None, query=None):
    url = base_url() + path
    if query:
        url += "?" + urllib.parse.urlencode(query)
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", _auth_header())
    req.add_header("Accept", "application/json")
    req.add_header("User-Agent", "adlc-framework")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            raw = r.read().decode("utf-8", "replace")
            return r.status, (json.loads(raw) if raw.strip() else {})
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        return e.code, {"_error": _error_text(e.code, raw)}
    except urllib.error.URLError as e:
        raise JiraError(f"cannot reach Jira at {base_url()}: {e.reason}") from None
    except (TimeoutError, OSError) as e:
        raise JiraError(f"cannot reach Jira at {base_url()}: {e}") from None
    except ValueError:
        raise JiraError("Jira returned a response that is not JSON") from None


def _check(status, body, what):
    if status == 401:
        raise JiraError(f"{what} failed: 401 Unauthorized - check JIRA_EMAIL and JIRA_API_TOKEN")
    if status == 403:
        raise JiraError(f"{what} failed: 403 Forbidden - the account lacks permission")
    if status >= 300:
        raise JiraError(f"{what} failed ({status}): {body.get('_error', '')}")


# --- Atlassian Document Format ---------------------------------------------------
def text_to_adf(text):
    """Plain text -> ADF. Blank lines split paragraphs; '- '/'* ' lines become bullets."""
    content, para, bullets = [], [], []

    def flush_para():
        if para:
            nodes = []
            for i, line in enumerate(para):
                if i:
                    nodes.append({"type": "hardBreak"})
                nodes.append({"type": "text", "text": line})
            content.append({"type": "paragraph", "content": nodes})
            para.clear()

    def flush_bullets():
        if bullets:
            content.append({"type": "bulletList", "content": [
                {"type": "listItem", "content": [
                    {"type": "paragraph", "content": [{"type": "text", "text": b}]}]}
                for b in bullets]})
            bullets.clear()

    for raw in (text or "").replace("\r\n", "\n").split("\n"):
        line = raw.rstrip()
        m = re.match(r"^\s*(?:[-*]|\[ \]|- \[ \])\s+(.*)$", line)
        if m and m.group(1).strip():
            flush_para()
            bullets.append(m.group(1).strip())
        elif not line.strip():
            flush_para()
            flush_bullets()
        else:
            flush_bullets()
            para.append(line)
    flush_para()
    flush_bullets()
    return {"type": "doc", "version": 1, "content": content}


def adf_to_text(node):
    """Best-effort ADF -> plain text (for `get`)."""
    if not isinstance(node, dict):
        return ""
    t = node.get("type")
    if t == "text":
        return node.get("text", "")
    if t == "hardBreak":
        return "\n"
    inner = "".join(adf_to_text(c) for c in node.get("content", []) or [])
    if t == "listItem":
        return "- " + inner.strip() + "\n"
    if t in ("paragraph", "heading", "codeBlock", "blockquote"):
        return inner + "\n\n"
    return inner


# --- actions -----------------------------------------------------------------------
def pick(limit=20):
    jql = f'project = "{project_key()}" AND statusCategory != Done ORDER BY created DESC'
    query = {"jql": jql, "maxResults": str(limit), "fields": "summary,status"}
    # /search/jql is the current endpoint; /search was removed from Jira Cloud in 2025.
    status, body = request("GET", "/rest/api/3/search/jql", query=query)
    if status in (404, 410):
        status, body = request("GET", "/rest/api/3/search", query=query)
    _check(status, body, "jira pick")
    lines = []
    for issue in body.get("issues", []):
        f = issue.get("fields") or {}
        st = (f.get("status") or {}).get("name", "?")
        summary = " ".join(str(f.get("summary", "")).split())
        lines.append(f"{issue.get('key', '?')}\t{st}\t{summary}")
    return lines


def get(key):
    if not KEY_RE.match(key):
        raise JiraError(f"invalid issue key '{key}'")
    status, body = request("GET", f"/rest/api/3/issue/{key}",
                           query={"fields": "summary,status,description"})
    _check(status, body, "jira get")
    f = body.get("fields") or {}
    desc = adf_to_text(f.get("description") or {}).strip()
    return f"{key}: {f.get('summary', '')}\nStatus: {(f.get('status') or {}).get('name', '?')}\n\n{desc}\n"


def create(summary, description):
    summary = " ".join(summary.split())
    if not summary:
        raise JiraError("summary must not be empty")
    payload = {"fields": {
        "project": {"key": project_key()},
        "issuetype": {"name": env("JIRA_ISSUE_TYPE", "Task")},
        "summary": summary[:255],
        "description": text_to_adf(description),
    }}
    status, body = request("POST", "/rest/api/3/issue", payload=payload)
    _check(status, body, "jira create")
    key = body.get("key")
    if not key:
        raise JiraError("jira create succeeded but returned no issue key")
    return key


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    action = args[0] if args else "mode"
    if action in ("-h", "--help", "help"):
        print(__doc__.strip())
        return 0
    load_dotenv()

    if action == "mode":
        print("jira" if jira_configured() else "local")
        return 0
    if action not in ("pick", "get", "create"):
        print(f"jira_ticket: unknown action '{action}' (use mode|pick|get|create)", file=sys.stderr)
        return 2
    if not jira_configured():
        missing = ", ".join(k for k in REQUIRED if not env(k))
        print(f"Jira not configured (missing {missing}); use `adlc init` for local mode.",
              file=sys.stderr)
        return 2
    try:
        if action == "pick":
            limit = 20
            if len(args) >= 3 and args[1] == "--max" and args[2].isdigit():
                limit = max(1, min(100, int(args[2])))
            for line in pick(limit):
                print(line)
        elif action == "get":
            if len(args) < 2:
                print("usage: jira_ticket.py get <KEY>", file=sys.stderr)
                return 2
            sys.stdout.write(get(args[1]))
        else:
            if len(args) < 3:
                print('usage: jira_ticket.py create "<summary>" "<description>"', file=sys.stderr)
                return 2
            print(create(args[1], args[2]))  # the caller captures this key
    except JiraError as e:
        print(f"jira: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
