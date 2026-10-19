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

    def test_rules_tried_and_their_deflated_sharpe(self):
        T = self.R["trials"]
        f = T["families"]
        self.assertIn(f"{T['total']} distinct rules** ({f['A']} in Strategy A's grid, {f['methods']} research methods, {f['B']} more for B, {f['C']} in C", FLAT)
        b = next(r for r in T["rows"] if r["strategy"] == "B")
        self.assertIn(f"deflated Sharpe ratio of {round(100 * b['dsr_all'])}% ({round(100 * b['dsr_own'])}% against its own {b['own_trials']} settings alone)", FLAT)
        self.assertIn(f"best of {T['total']} tries", FLAT)
        if f.get("checks"):
            self.assertIn(f"{f['C']} in C, {f['checks']} later check without the carry adjustment", FLAT)

    def test_each_sealed_result_deflated_alone(self):
        """The rules scored before each window was opened, and the fair-price model's score in each window"""
        T = self.R["trials"]
        oc = T["opened_counts"]
        self.assertIn(f"({oc['test']} before the first test, {oc['holdout']} before the holdout, {oc['test3']} before 2016–2023", FLAT)
        b = {r["test"]: round(100 * r["dsr_opened"]) for r in T["per_result"] if r["strategy"] == "B"}
        self.assertIn(f"the fair-price model scores {b['holdout']}% on the holdout, {b['test3']}% on 2016–2019 and {b['test2']}% on 2020–2023", FLAT)
        if all(v < 50 for v in b.values()):
            self.assertIn("below 50% every time", FLAT)

    def test_first_test_against_its_measured_spread(self):
        r = next(x for x in self.R["breakeven"]["rows"] if x["test"] == "test" and x["strategy"] == "A")
        self.assertIn(f"Strategy A's first test broke even at {r['breakeven_bp']:.1f} bp against a measured {r['est_slip_bp']:.1f} bp", FLAT)
        self.assertGreater(r["est_slip_bp"], r["breakeven_bp"])          # "even its profit before slippage sat inside the spread"

    def test_sealed_spreads_under_the_stated_ceiling(self):
        """"under 3 bp per order even at the top of its 95% range" in both sealed windows, and below every positive break-even"""
        top = max(v["hi"] for w in ("test3", "test2") for v in self.R["costs"]["windows"][w].values() if isinstance(v, dict))
        self.assertLess(top, 3)
        self.assertIn("under 3 bp per order even at the top of its 95% range", FLAT)
        be = [r["breakeven_bp"] for r in self.R["breakeven"]["rows"] if r["breakeven_bp"] is not None]
        self.assertLess(top, min(be))

    def test_half_lives(self):
        """Half-lives move a little as each trading day is added, so the README rounds them: within a day of today's"""
        st = {r["symbol"]: r for r in self.R["stationarity"]["rows"]}
        m = re.search(r"GOLDTEN and GOLDGUINEA gaps halve in about (\d+) and (\d+) market days", FLAT)
        self.assertTrue(m)
        self.assertLessEqual(abs(int(m.group(1)) - st["GOLDTEN"]["half_life_days"]), 1)
        self.assertLessEqual(abs(int(m.group(2)) - st["GOLDGUINEA"]["half_life_days"]), 1)


class Licence(unittest.TestCase):
    def test_licence_present_and_referenced(self):
        self.assertTrue(os.path.exists(LICENSE))
        self.assertIn("All rights reserved", open(LICENSE).read())
        self.assertIn("(LICENSE)", FLAT)


if __name__ == "__main__":
    unittest.main()
