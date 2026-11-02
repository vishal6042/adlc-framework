"""Run the test suite; in GitHub Actions also emit each failure as an annotation
so it is visible in the run summary without opening the raw log."""
import os
import sys
import unittest
from pathlib import Path

ON_CI = os.environ.get("GITHUB_ACTIONS") == "true"


def _escape(s):
    return s.replace("%", "%25").replace("\r", "").replace("\n", "%0A")


class AnnotatingResult(unittest.TextTestResult):
    def _annotate(self, test, err, kind):
        if not ON_CI:
            return
        lines = self._exc_info_to_string(err, test).strip().splitlines()[-20:]
        print(f"::error title={kind} {test.id()}::{_escape(chr(10).join(lines))}", flush=True)

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self._annotate(test, err, "FAIL")

    def addError(self, test, err):
        super().addError(test, err)
        self._annotate(test, err, "ERROR")


def main():
    here = Path(__file__).resolve().parent
    suite = unittest.defaultTestLoader.discover(str(here), top_level_dir=str(here))
    result = unittest.TextTestRunner(verbosity=2, resultclass=AnnotatingResult).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
