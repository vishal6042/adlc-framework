"""Tests for core/scripts/jira_ticket.py against a local fake Jira server."""
import base64
import contextlib
import io
import json
import os
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from unittest import mock
from urllib.parse import parse_qs, urlparse

from helpers import SCRIPTS

sys.path.insert(0, str(SCRIPTS))
import jira_ticket as jt  # noqa: E402


class FakeJira(BaseHTTPRequestHandler):
    routes = {}      # (method, path) -> (status, body)
    requests = []    # recorded (method, path, query, headers, body)

    def _handle(self, method):
        u = urlparse(self.path)
        length = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(length)) if length else None
        FakeJira.requests.append((method, u.path, parse_qs(u.query), dict(self.headers), body))
        status, payload = FakeJira.routes.get((method, u.path), (404, {"errorMessages": ["nope"]}))
        raw = json.dumps(payload).encode() if not isinstance(payload, bytes) else payload
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):  # noqa: N802
        self._handle("GET")

    def do_POST(self):  # noqa: N802
        self._handle("POST")

    def log_message(self, *args):
        pass


class JiraHelperTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(("127.0.0.1", 0), FakeJira)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f"http://127.0.0.1:{cls.server.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        FakeJira.routes = {}
        FakeJira.requests = []
        env = {k: v for k, v in os.environ.items() if not k.startswith(("JIRA_", "ADLC_"))}
        env.update(JIRA_BASE_URL=self.url, JIRA_EMAIL="me@example.com", JIRA_API_TOKEN="tok123",
                   JIRA_ALLOW_HTTP="1", JIRA_PROJECT_KEY="PROJ")
        self.env = mock.patch.dict(os.environ, env, clear=True)
        self.env.start()
        self.dotenv = mock.patch.object(jt, "load_dotenv", lambda *a, **k: None)
        self.dotenv.start()

    def tearDown(self):
        self.dotenv.stop()
        self.env.stop()

    def run_main(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = jt.main(list(args))
        return code, out.getvalue(), err.getvalue()

    # --- mode / configuration --------------------------------------------------
    def test_mode(self):
        self.assertEqual(self.run_main("mode")[1].strip(), "jira")
        del os.environ["JIRA_API_TOKEN"]
        self.assertEqual(self.run_main("mode")[1].strip(), "local")
        code, _, err = self.run_main("pick")
        self.assertEqual(code, 2)
        self.assertIn("JIRA_API_TOKEN", err)

    def test_refuses_plain_http(self):
        del os.environ["JIRA_ALLOW_HTTP"]
        code, _, err = self.run_main("pick")
        self.assertEqual(code, 1)
        self.assertIn("https://", err)
        self.assertEqual(FakeJira.requests, [], "nothing may be sent over http")

    def test_rejects_bad_project_key(self):
        os.environ["JIRA_PROJECT_KEY"] = 'X" OR 1=1'
        code, _, err = self.run_main("pick")
        self.assertEqual(code, 1)
        self.assertIn("not a valid Jira project key", err)

    def test_unknown_action(self):
        self.assertEqual(self.run_main("explode")[0], 2)

    # --- pick ------------------------------------------------------------------
    def test_pick_uses_search_jql_endpoint(self):
        FakeJira.routes[("GET", "/rest/api/3/search/jql")] = (200, {"issues": [
            {"key": "PROJ-2", "fields": {"summary": "Second\nissue", "status": {"name": "To Do"}}},
            {"key": "PROJ-1", "fields": {"summary": "First", "status": {"name": "In Progress"}}},
        ]})
        code, out, _ = self.run_main("pick")
        self.assertEqual(code, 0)
        self.assertEqual(out.splitlines(), ["PROJ-2\tTo Do\tSecond issue", "PROJ-1\tIn Progress\tFirst"])
        method, path, query, headers, _ = FakeJira.requests[0]
        self.assertEqual(path, "/rest/api/3/search/jql")
        self.assertIn('project = "PROJ"', query["jql"][0])
        expected = "Basic " + base64.b64encode(b"me@example.com:tok123").decode()
        self.assertEqual(headers.get("Authorization"), expected)

    def test_pick_falls_back_to_legacy_search(self):
        FakeJira.routes[("GET", "/rest/api/3/search")] = (200, {"issues": []})
        code, _, _ = self.run_main("pick")
        self.assertEqual(code, 0)
        self.assertEqual([r[1] for r in FakeJira.requests],
                         ["/rest/api/3/search/jql", "/rest/api/3/search"])

    def test_pick_auth_error_is_readable(self):
        FakeJira.routes[("GET", "/rest/api/3/search/jql")] = (401, {"errorMessages": ["bad"]})
        code, _, err = self.run_main("pick")
        self.assertEqual(code, 1)
        self.assertIn("401 Unauthorized", err)
        self.assertNotIn("tok123", err)

    def test_network_error_is_readable(self):
        os.environ["JIRA_BASE_URL"] = "http://127.0.0.1:9"  # discard port: connection refused
        code, _, err = self.run_main("pick")
        self.assertEqual(code, 1)
        self.assertIn("cannot reach Jira", err)

    # --- create / get --------------------------------------------------------------
    def test_create_sends_adf_and_prints_key(self):
        FakeJira.routes[("POST", "/rest/api/3/issue")] = (201, {"key": "PROJ-7"})
        code, out, _ = self.run_main("create", "Add  health\nendpoint",
                                     "Why it matters.\n\n- returns 200\n- has a test")
        self.assertEqual((code, out.strip()), (0, "PROJ-7"))
        fields = FakeJira.requests[0][4]["fields"]
        self.assertEqual(fields["summary"], "Add health endpoint")
        self.assertEqual(fields["project"], {"key": "PROJ"})
        self.assertEqual(fields["issuetype"], {"name": "Task"})
        kinds = [n["type"] for n in fields["description"]["content"]]
        self.assertEqual(kinds, ["paragraph", "bulletList"])

    def test_create_validation_error(self):
        FakeJira.routes[("POST", "/rest/api/3/issue")] = (400, {"errors": {"issuetype": "invalid"}})
        code, _, err = self.run_main("create", "s", "d")
        self.assertEqual(code, 1)
        self.assertIn("issuetype: invalid", err)

    def test_create_usage(self):
        self.assertEqual(self.run_main("create", "only summary")[0], 2)

    def test_get(self):
        FakeJira.routes[("GET", "/rest/api/3/issue/PROJ-3")] = (200, {"fields": {
            "summary": "Do it", "status": {"name": "To Do"},
            "description": jt.text_to_adf("Line one\nline two\n\n- crit A\n- crit B")}})
        code, out, _ = self.run_main("get", "PROJ-3")
        self.assertEqual(code, 0)
        self.assertIn("PROJ-3: Do it", out)
        self.assertIn("- crit A", out)
        self.assertEqual(self.run_main("get", "../etc")[0], 1)


class PureFunctionTest(unittest.TestCase):
    def test_text_to_adf_round_trip(self):
        adf = jt.text_to_adf("Para one\ncontinued\n\n- a\n- b\n\nEnd")
        self.assertEqual([n["type"] for n in adf["content"]], ["paragraph", "bulletList", "paragraph"])
        text = jt.adf_to_text(adf)
        self.assertIn("Para one\ncontinued", text)
        self.assertIn("- a\n- b", text)

    def test_text_to_adf_empty(self):
        self.assertEqual(jt.text_to_adf("")["content"], [])

    def test_load_dotenv(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / ".env"
            p.write_text('JIRA_EMAIL="a@b.c"\nexport JIRA_PROJECT_KEY=XY\nOTHER=1\n# JIRA_X=no\n'
                         "JIRA_API_TOKEN='t'\n", encoding="utf-8")
            environ = {"JIRA_PROJECT_KEY": "KEEP"}
            jt.load_dotenv([str(p), str(Path(d) / "missing.env")], environ)
        self.assertEqual(environ, {"JIRA_EMAIL": "a@b.c", "JIRA_PROJECT_KEY": "KEEP", "JIRA_API_TOKEN": "t"})


if __name__ == "__main__":
    unittest.main()
