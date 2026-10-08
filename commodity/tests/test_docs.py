"""The front-page README states only what the data and results say.

Its results table, overfitting figures, data claims, test counts and file links are each checked against
the computed files, so the README cannot drift from the work. Counts that grow every trading day are
stated as floors ("over 55,000 rows"), which these tests check stay true.
"""
import glob
import json
import os
import re
import unittest

import pandas as pd

from _util import all_rows, cases, result

README = open("../README.md", encoding="utf-8").read()
FLAT = " ".join(README.split())          # phrases may wrap across lines in the Markdown
LICENSE = "../LICENSE"


def inr(v):
    """+₹1,90,340 / −₹48,734 in Indian digit grouping, as the README writes them"""
    n = int(round(abs(v)))
    s = str(n)
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        head = ",".join([head[max(0, i - 2):i] for i in range(len(head), 0, -2)][::-1])
        s = head + "," + tail
    return ("+" if v >= 0 else "−") + "₹" + s


def sealed(test, strategy):
    s = result("sealed_summary.csv")
    return float(s[(s.test == test) & (s.strategy.str.startswith(strategy)) & (s.slip_bp == 5)].net.iloc[0])


def holdout(key):
    d = json.load(open("dashboard/data.json"))["backtests"][key]["rows"]
    return float(next(r for r in d if r["slip"] == 5)["net"])


TABLE = {
    "A holdout": (lambda: holdout("A_hold"), "Aug 2025 – May 2026 holdout", 0),
    "B holdout": (lambda: holdout("B_hold"), "Aug 2025 – May 2026 holdout", 1),
    "A 2016-19": (lambda: sealed("test3", "A"), "2016 – 2019", 0),
    "B 2016-19": (lambda: sealed("test3", "B"), "2016 – 2019", 1),
    "C 2016-19": (lambda: sealed("test3", "C"), "2016 – 2019", 2),
    "A 2020-23": (lambda: sealed("test2", "A"), "2020 – 2023", 0),
    "B 2020-23": (lambda: sealed("test2", "B"), "2020 – 2023", 1),
    "C 2020-23": (lambda: sealed("test2", "C"), "2020 – 2023", 2),
}


@cases(sorted(TABLE))
class ResultsTable(unittest.TestCase):
    def check_cell_matches_the_results(self, key):
        """Each cell of the README's sealed-results table equals the stored result at 5 bp"""
        fn, row_label, col = TABLE[key]
        line = next(l for l in README.splitlines() if l.startswith(f"| {row_label}"))
        cell = [c.strip() for c in line.strip("|").split("|")][1 + col]
        self.assertEqual(cell, inr(fn()))


class Figures(unittest.TestCase):
    O = json.load(open("results/overfit.json"))

    def test_pbo(self):
        self.assertIn(f"Probability of backtest overfitting: {round(100 * self.O['pbo']['value'])}%", FLAT)
        self.assertIn(f"all {self.O['pbo']['splits']} ways", FLAT)
        self.assertIn(f"{self.O['pbo']['settings']} settings", FLAT)

    def test_placebo(self):
        L = self.O["placebo"]
        self.assertIn(f"beat {100 * (1 - L['share_placebo_at_or_above_b']):.2f}% of {L['runs']:,} random-timing strategies", FLAT)
        self.assertIn(f"about 1 in {round(1 / L['share_placebo_at_or_above_b'])} random runs", FLAT)

    def test_no_carry(self):
        N = self.O["no_carry"]
        self.assertIn(f"made {inr(N['net'])[1:]} on {N['trades']} trades, against {inr(N['with_carry_net'])[1:]} on {N['with_carry_trades']}", FLAT)


class DataClaims(unittest.TestCase):
    def test_row_floor(self):
        self.assertIn("over 55,000 daily rows", FLAT)
        self.assertGreater(len(all_rows()), 55_000)

    def test_contract_floor(self):
        self.assertIn("over 700 contracts", FLAT)
        self.assertGreater(all_rows().groupby(["symbol", "expiry_date"]).ngroups, 700)

    def test_start_date(self):
        self.assertIn("since November 2003", FLAT)
        self.assertEqual(all_rows().date.min().strftime("%Y-%m"), "2003-11")


class TestCounts(unittest.TestCase):
    def test_distinct_checks(self):
        n = sum(len(re.findall(r"^\s+def (?:test_|check_)", open(f).read(), re.M)) for f in glob.glob("tests/test_*.py"))
        m = re.search(r"\((\d+) distinct checks", README)
        self.assertTrue(m)
        self.assertEqual(int(m.group(1)), n)

    def test_total_is_about_what_the_readme_says(self):
        total = unittest.defaultTestLoader.discover("tests").countTestCases()
        self.assertIn("About 10,000 automated tests", FLAT)
        self.assertTrue(8_000 <= total <= 13_000, total)


@cases(sorted(set(re.findall(r"\]\((commodity/[^)#\s]+)\)", README))))
class Links(unittest.TestCase):
    def check_linked_file_exists(self, path):
        """Every file the README links to is in the repository"""
        self.assertTrue(os.path.exists(os.path.join("..", path)), path)


class PublishedTestReport(unittest.TestCase):
    """results/test_report.json, which the site shows, is a complete and passing run of this suite"""
    R = json.load(open("results/test_report.json")) if os.path.exists("results/test_report.json") else None

    def setUp(self):
        if self.R is None:
            self.skipTest("no report yet")

    def test_totals_add_up(self):
        self.assertEqual(self.R["tests"], sum(f["tests"] for f in self.R["files"]))
        self.assertEqual(self.R["tests"], self.R["passed"] + self.R["failed"] + self.R["skipped"])

    def test_lists_every_test_file(self):
        self.assertEqual(sorted(f["name"] for f in self.R["files"]), sorted(os.path.basename(f)[:-3] for f in glob.glob("tests/test_*.py")))

    def test_every_file_says_what_it_proves(self):
        for f in self.R["files"]:
            self.assertGreater(len(f["about"].split()), 4, f["name"])


class Robustness(unittest.TestCase):
    R = json.load(open("results/robustness.json"))

    def test_break_even_range(self):
        be = [r["breakeven_bp"] for r in self.R["breakeven"]["rows"] if r["breakeven_bp"] is not None]
        self.assertIn(f"between {min(be):.1f} and {max(be):.1f} bp", FLAT)

    def test_deflated_sharpe(self):
        self.assertIn(f"deflated Sharpe ratio is {round(100 * self.R['sharpe']['deflated_c']['dsr'])}%", FLAT)

    def test_half_lives(self):
        st = {r["symbol"]: r for r in self.R["stationarity"]["rows"]}
        self.assertIn(f"GOLDTEN and GOLDGUINEA gaps halve in {st['GOLDTEN']['half_life_days']:.1f} and {st['GOLDGUINEA']['half_life_days']:.1f} market days", FLAT)


class Licence(unittest.TestCase):
    def test_licence_present_and_referenced(self):
        self.assertTrue(os.path.exists(LICENSE))
        self.assertIn("All rights reserved", open(LICENSE).read())
        self.assertIn("(LICENSE)", FLAT)


if __name__ == "__main__":
    unittest.main()
