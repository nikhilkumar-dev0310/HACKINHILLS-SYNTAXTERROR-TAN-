"""Run the whole test suite and record the outcome for the site (results/test_report.json).

    python tools/run_tests.py          (from commodity/; exit code 1 if any test fails)

Used by the Tests workflow on every push and by the daily data job before it may publish. The site's Data
quality page shows the latest report: how many tests ran, what each file proves, and that all passed.
"""
import datetime as dt
import glob
import json
import os
import re
import subprocess
import sys
import time
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "results", "test_report.json")


def first_line(doc):
    return " ".join((doc or "").strip().split("\n\n")[0].split())


class Recorder(unittest.TextTestResult):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.passed = []

    def addSuccess(self, test):
        super().addSuccess(test)
        self.passed.append(test)


def main():
    os.chdir(HERE)
    sys.path[:0] = [HERE, os.path.join(HERE, "tests")]     # project modules, then the test helpers
    suite = unittest.defaultTestLoader.discover("tests")
    t0 = time.time()
    with open(os.devnull, "w") as quiet:
        res = unittest.TextTestRunner(stream=quiet, resultclass=Recorder, verbosity=0).run(suite)
    secs = time.time() - t0

    def file_of(test):
        i = test.id()
        return i.split(".")[-1] if i.startswith("unittest.loader") else i.split(".")[0]   # a module that failed to import

    files = {}
    for path in sorted(glob.glob("tests/test_*.py")):
        name = os.path.basename(path)[:-3]
        src = open(path, encoding="utf-8").read()
        mod = sys.modules.get(name)
        files[name] = {"file": f"tests/{name}.py", "about": first_line(getattr(mod, "__doc__", None)),
                       "checks": len(re.findall(r"^\s+def (?:test_|check_)", src, re.M)),
                       "tests": 0, "passed": 0, "failed": 0, "skipped": 0}
    for t in res.passed:
        files[file_of(t)]["tests"] += 1; files[file_of(t)]["passed"] += 1
    for t, _ in res.failures + res.errors:
        files.setdefault(file_of(t), {"file": "", "about": "", "checks": 0, "tests": 0, "passed": 0, "failed": 0, "skipped": 0})
        files[file_of(t)]["tests"] += 1; files[file_of(t)]["failed"] += 1
    for t, _ in res.skipped:
        files[file_of(t)]["tests"] += 1; files[file_of(t)]["skipped"] += 1

    try:
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip() or None
    except OSError:
        commit = None
    ist = dt.timezone(dt.timedelta(hours=5, minutes=30))
    report = {"run_at": dt.datetime.now(ist).strftime("%Y-%m-%d %H:%M IST"), "commit": commit,
              "tests": res.testsRun, "passed": len(res.passed), "failed": len(res.failures) + len(res.errors),
              "skipped": len(res.skipped), "seconds": round(secs, 1),
              "checks": sum(f.get("checks", 0) for f in files.values()), "files": [dict(name=k, **v) for k, v in files.items()],
              "where": os.environ.get("GITHUB_WORKFLOW") or "local"}
    with open(OUT, "w") as f:
        json.dump(report, f, indent=2)
    print(f"{report['tests']} tests ({report['checks']} checks in {len(files)} files): {report['passed']} passed, "
          f"{report['failed']} failed, {report['skipped']} skipped, {secs:.0f} s")
    for t, tb in (res.failures + res.errors)[:20]:
        print("FAILED", t.id(), "\n", tb.strip().splitlines()[-1])
    return 0 if report["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
